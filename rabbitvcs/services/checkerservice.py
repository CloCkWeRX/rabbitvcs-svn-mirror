#
# Copyright (C) 2009 Jason Heeris <jason.heeris@gmail.com>
# Copyright (C) 2009 by Bruce van der Kooij <brucevdkooij@gmail.com>
# Copyright (C) 2009 by Adam Plumb <adamplumb@gmail.com>#
#
# RabbitVCS is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# RabbitVCS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with RabbitVCS;  If not, see <http://www.gnu.org/licenses/>.
#

""" The checker service for RabbitVCS background status checks.

This file can be run as a Python script, in which case it starts a background
VCS status checking service that can be called via DBUS. It also contains class
definitions to call these methods from within a separate Python process.

This currently works like so:

    1. Nautilus loads our extension, RabbitVCS
    2. RabbitVCS creates a StatusCheckerStub
    3. StatusCheckerStub calls start(), which is a wrapper for a more general
       service starter convenience method
    4. The service starter method looks for a DBUS object with the given service
       name and object path; if none is found, it creates it by running this
       script

RabbitVCS can then call the stub methods, getting status info via the
CheckStatus method itself, or more likely from a callback upon completion of a
status check.

NOTE: as a general rule, the data piped between processes or sent over DBUS
should be kept to a minimum. Use convenience methods to condense and summarise
data wherever possible (this is the case in the actual status cache and checker
code).
"""

import os, os.path
import sys
import simplejson

import gobject
try:
    # Older distributions will not have a glib module.  For them, they must
    # still use the gobject module
    import glib
    HAS_GLIB = True
except ImportError:
    HAS_GLIB = False

import dbus
import dbus.glib # FIXME: this might actually already set the default loop
try:
    import dbus.mainloop.glib
except ImportError, e:
    # Older distributions do not have this module
    pass
    
import dbus.service

import rabbitvcs.util._locale
import rabbitvcs.util.helper
import rabbitvcs.services.service
from rabbitvcs.services.statuscheckerplus import StatusCheckerPlus

import rabbitvcs.vcs.status

from rabbitvcs.util.log import Log
log = Log("rabbitvcs.services.checkerservice")

INTERFACE = "org.google.code.rabbitvcs.StatusChecker"
OBJECT_PATH = "/org/google/code/rabbitvcs/StatusChecker"
SERVICE = "org.google.code.rabbitvcs.RabbitVCS.Checker"
TIMEOUT = 60*15*100 # seconds

def idle_add(callback, *args, **kwargs):
    if HAS_GLIB:
        glib.idle_add(callback, *args, **kwargs)
    else:
        gobject.idle_add(callback, *args, **kwargs)

def find_class(module, name):
    """ Given a module name and a class name, return the actual type object.
    """
    # From Python stdlib pickle module source
    __import__(module)
    mod = sys.modules[module]
    klass = getattr(mod, name)
    return klass

def encode_status(status):
    """ Before encoding a status object to JSON, we need to turn it into
    something simpler.
    """
    return status.__getstate__()

def decode_status(json_dict):
    """ Once we get a JSON encoded string out the other side of DBUS, we need to
    reconstitute the original object. This method is based on the pickle module
    in the Python stdlib.
    """
    cl = find_class(json_dict['__module__'], json_dict['__type__'])
    st = None
    if cl in rabbitvcs.vcs.status.STATUS_TYPES:
        st = cl.__new__(cl)
        st.__setstate__(json_dict)
    elif json_dict.has_key('path'):
        log.warning("Could not deduce status class: %s" % json_dict['__type__'])
        st = rabbitvcs.vcs.status.Status.status_error(json_dict['path'])
    else:
        raise TypeError("RabbitVCS status object has no path")
    return st

class StatusCheckerService(dbus.service.Object):
    """ StatusCheckerService objects wrap a StatusCheckerPlus instance,
    exporting methods that can be called via DBUS.

    There should only be a single such object running in a separate process from
    the GUI (ie. do not create this in the Nautilus extension code, you should
    use a StatusCheckerStub there instead).
    """

    def __init__(self, connection, mainloop):
        """ Creates a new status checker wrapper service, with the given DBUS
        connection.

        The mainloop argument is needed for process management (eg. calling
        Quit() for graceful exiting).

        @param connection: the DBUS connection (eg. session bus, system bus)
        @type connection: a DBUS connection object

        @param mainloop: the main loop that DBUS is using
        @type mainloop: any main loop with a quit() method
        """
        dbus.service.Object.__init__(self, connection, OBJECT_PATH)
        
        self.encoder = simplejson.JSONEncoder(default=encode_status,
                                              separators=(',', ':'))
        
        self.mainloop = mainloop

        # Start the status checking daemon so we can do requests in the
        # background
        self.status_checker = StatusCheckerPlus()

    @dbus.service.method(INTERFACE)
    def ExtraInformation(self):
        return self.status_checker.extra_info()

    @dbus.service.method(INTERFACE)
    def MemoryUsage(self):
        own_mem = rabbitvcs.util.helper.process_memory(os.getpid())
        checker_mem = self.status_checker.get_memory_usage()

        return own_mem + checker_mem

    @dbus.service.method(INTERFACE)
    def PID(self):
        return os.getpid()

    @dbus.service.method(INTERFACE)
    def CheckerType(self):
        return self.status_checker.CHECKER_NAME

    def CheckFinishedPreprocess(self, status):
        """ We need to render the statuses in a format that can be sent over
        DBUS, and then unconvert them at the other end. (The ONLY reason the
        status objects can't be rendered by DBUS automatically is that they may
        contain "None" values. Grr.)
        """
        self.CheckFinished(self.encoder.encode(status))


    @dbus.service.signal(INTERFACE, signature='s')
    def CheckFinished(self, status):
        """ Empty method for connection status check callbacks. This is a DBUS
        signal, and can be "connected" to as per the python DBUS docs.
        """
        pass

    @dbus.service.method(INTERFACE, in_signature='sbbbb', out_signature='s')
    def CheckStatus(self, path, recurse=False, invalidate=False,
                      summary=False, callback=False):
        """ Requests a status check from the underlying status checker.

        See the StatusCheckerPlus documentation for details of the parameters,
        but note that "callback" behaves differently. The actual callback that
        is given to the status checker is the "CheckFinished" method of this
        object, if callback is True.

        Any entity wanting notification of a completed status check should
        connect to the DBUS signal "CheckFinished", and sort out its own
        logic from there.

        @param callback: whether or not to notify when a status check is
                         complete
        @type callback: boolean
        """
        if callback:
            callback = self.CheckFinishedPreprocess
        else:
            callback = None

        status = self.status_checker.check_status(unicode(path), recurse=recurse,
                                                  invalidate=invalidate,
                                                  summary=summary,
                                                  callback=callback)
        
        return self.encoder.encode(status)

    @dbus.service.method(INTERFACE)
    def Quit(self):
        """ Quits the service, performing any necessary cleanup operations.

        You can call this from the command line with:

        dbus-send --print-reply \
        --dest=org.google.code.rabbitvcs.RabbitVCS.Checker \
        /org/google/code/rabbitvcs/StatusChecker \
        org.google.code.rabbitvcs.StatusChecker.Quit

        If calling this programmatically, then you can do "os.waitpid(pid, 0)"
        on the returned PID to prevent a zombie process.
        """
        self.status_checker.quit()
        log.debug("Quitting main loop...")
        self.mainloop.quit()
        return self.PID()


class StatusCheckerStub:
    """ StatusCheckerStub objects contain methods that call an actual status
    checker running in another process.

    These objects should be created by the GUI as needed (eg. the nautilus
    extension code).

    Note that even though the status checker itself takes a callback for each
    call to "check_status", this stub requires it to be provided at
    initialisation. The callback can be triggered (or not) using the boolean
    callback parameter of the "check_status" method.

    The inter-process communication is via DBUS.
    """

    def __init__(self, callback=None):
        """ Creates an object that can call the VCS status checker via DBUS.

        If there is not already a DBUS object with the path "OBJECT_PATH", we
        create one by starting a new Python process that runs this file.

        @param callback: the function to call when status checks are completed
                         (see the StatusCheckerPlus method documentation for
                         details)
        """
        self.session_bus = dbus.SessionBus()
        self.callback = callback

        self.decoder = simplejson.JSONDecoder(object_hook=decode_status)

        self.status_checker = None

        start()
        self._connect_to_checker()

    def _connect_to_checker(self):

        # Start the status checker, if it's not running this should start it up.
        # Otherwise it leaves it alone.
        # start()

        # Try to get a new checker
        try:
            self.status_checker = self.session_bus.get_object(SERVICE,
                                                              OBJECT_PATH)
            if self.callback:
                self.status_checker.connect_to_signal("CheckFinished",
                                                      self._idle_callback,
                                                      dbus_interface=INTERFACE)
        except dbus.DBusException, ex:
            # There is not much we should do about this...
            log.exception(ex)

    def _idle_callback(self, *args, **kwargs):
        """ Notifies the callback of a completed status check.

        The callback will be performed when the glib main loop is idle. This is
        basically a way of making this a lower priority than direct calls to
        "check_status", which need to return ASAP.
        """
        idle_add(self.CheckFinishedDeprocess, *args, **kwargs)
        # Switch to this method to just call it straight from here:
        # self.CheckFinishedDeprocess(*args, **kwargs)

    def CheckFinishedDeprocess(self, json_status):
        """ This undoes the work of CheckFinishedPreprocess, re-creating the
        real status objects from however they were transformed to send them over
        DBUS.
        """
        status = self.decoder.decode(json_status)
        self.callback(status)

    def check_status(self, path, recurse=False, invalidate=False,
                       summary=False, callback=False):
        """ Check the VCS status of the given path.

        This is a pass-through method to the check_status method of the DBUS
        service (which is, in turn, a wrapper around the real status checker).
        """
        status = None
                
        try:
            json_status = self.status_checker.CheckStatus(path,
                                                          recurse, invalidate,
                                                          summary, callback,
                                                          dbus_interface=INTERFACE,
                                                          timeout=TIMEOUT)
            status = self.decoder.decode(json_status)
            # Test client error problems :)
            # raise dbus.DBusException("Test")
        except dbus.DBusException, ex:
            log.exception(ex)

            status = rabbitvcs.vcs.status.Status.status_error(path)

            # Try to reconnect
            self._connect_to_checker()

        return status

def start():
    """ Starts the checker service, via the utility method in "service.py". """
    rabbitvcs.services.service.start_service(os.path.abspath(__file__), SERVICE,
                                             OBJECT_PATH)

def Main():
    """ The main point of entry for the checker service.

    This will set up the DBUS and glib extensions, the gobject/glib main loop,
    and start the service.
    """
    global log
    log = Log("rabbitvcs.services.checkerservice:main")
    log.debug("Checker: starting service: %s (%s)" % (OBJECT_PATH, os.getpid()))

    # We need this to for the client to be able to do asynchronous calls
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    # The following calls are required to make DBus thread-aware and therefore
    # support the ability run threads.
    gobject.threads_init()
    dbus.glib.threads_init()

    # This registers our service name with the bus
    session_bus = dbus.SessionBus()
    service_name = dbus.service.BusName(SERVICE, session_bus)

    mainloop = gobject.MainLoop()

    checker_service = StatusCheckerService(session_bus, mainloop)

    idle_add(sys.stdout.write, "Started status checker service\n")
    idle_add(sys.stdout.flush)

    mainloop.run()

    log.debug("Checker: ended service: %s (%s)" % (OBJECT_PATH, os.getpid()))

if __name__ == "__main__":
    rabbitvcs.util._locale.initialize_locale()

#    import cProfile
#    import rabbitvcs.util.helper
#    profile_data_file = os.path.join(
#                           rabbitvcs.util.helper.get_home_folder(),
#                           "checkerservice.stats")
#    cProfile.run("Main()", profile_data_file)

    Main()