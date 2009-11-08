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

""" The cache service for RabbitVCS background status checks and caching.

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

import gobject, glib

import dbus
import dbus.glib # FIXME: this might actually already set the default loop
import dbus.mainloop.glib
import dbus.service


import rabbitvcs.services.service
from rabbitvcs.services.statuscache import StatusCache

from rabbitvcs.lib.log import Log
log = Log("rabbitvcs.services.cacheservice")

INTERFACE = "org.google.code.rabbitvcs.StatusCache"
OBJECT_PATH = "/org/google/code/rabbitvcs/StatusCache"
SERVICE = "org.google.code.rabbitvcs.RabbitVCS.Cache"
TIMEOUT = 60*15*100 # seconds

class StatusCacheService(dbus.service.Object):
    """ StatusCacheService objects wrap a status_cache instance, exporting
    methods that can be called via DBUS.
    
    There should only be a single such object running in a separate process from
    the GUI (ie. do not create this in the Nautilus extension code, you should
    use a StatusCacheStub there instead).
    """
    
    def __init__(self, connection, mainloop):
        """ Creates a new status cache wrapper service, with the given DBUS
        connection.
        
        The mainloop argument is needed for process management (eg. calling
        Quit() for graceful exiting).
        
        @param connection: the DBUS connection (eg. session bus, system bus)
        @type connection: a DBUS connection object
        
        @param mainloop: the main loop that DBUS is using
        @type mainloop: any main loop with a quit() method
        """
        dbus.service.Object.__init__(self, connection, OBJECT_PATH)
        self.mainloop = mainloop
        
        # Start the status checking daemon so we can do requests in the
        # background
        self.status_cache = StatusCache()
        
    @dbus.service.signal(INTERFACE)
    def CheckFinished(self, path, statuses):
        """ Empty method for connection status check callbacks. This is a DBUS
        signal, and can be "connected" to as per the python DBUS docs.
        """
        pass
        
    @dbus.service.method(INTERFACE)
    def CheckStatus(self, path, recurse=False, invalidate=False,
                      summary=False, callback=False):
        """ Requests a status check from the underlying status cache.
        
        See the status_cache documentation for details of the parameters, but
        note that "callback" behaves differently. The actual callback that is
        given to the status cache is the "CheckFinished" method of this object,
        if callback is True.
        
        Any entity wanting notification of a completed status check should
        connect to the DBUS signal "CheckFinished", and sort out its own
        logic from there.
        
        @param callback: whether or not to notify when a status check is
                         complete 
        @type callback: boolean
        """
        callback = self.CheckFinished if callback else None
        return self.status_cache.check_status(u"" + path, recurse=recurse,
                                              invalidate=invalidate,
                                              summary=summary,
                                              callback=callback)
    
    @dbus.service.method(INTERFACE)
    def Quit(self):
        """ Quits the service, performing any necessary cleanup operations.

        You can call this from the command line with:
        
        dbus-send --print-reply \
        --dest=org.google.code.rabbitvcs.RabbitVCS.Cache \
        /org/google/code/rabbitvcs/StatusCache \
        org.google.code.rabbitvcs.StatusCache.Quit
        """
        log.debug("Quitting main loop...")
        self.status_cache.kill()
        self.mainloop.quit()
        
class StatusCacheStub:
    """ StatusCacheStub objects contain methods that call an actual status cache
    running in another process.
    
    These objects should be created by the GUI as needed (eg. the nautilus
    extension code).
    
    The inter-process communication is via DBUS.
    """
    
    def __init__(self, callback=None):
        """ Creates an object that can call the VCS status cache via DBUS.
        
        If there is not already a DBUS object with the path "OBJECT_PATH", we
        create one by starting a new Python process that runs this file.
        
        @param callback: the function to call when status checks are completed
                         (see the status_cache method documentation for details)
        """
        start()
        
        self.session_bus = dbus.SessionBus()
        self.callback = callback
        
        try:
            self.status_cache = self.session_bus.get_object(SERVICE,
                                                            OBJECT_PATH)
            if self.callback:
                self.status_cache.connect_to_signal("CheckFinished",
                                                    self.status_callback,
                                                    dbus_interface=INTERFACE)
        except dbus.DBusException, ex:
            # There is not much we should do about this...
            log.exception(ex)
            raise
    
    def status_callback(self, *args, **kwargs):
        """ Notifies the callback of a completed status check.
        
        The callback will be performed when the glib main loop is idle. This is
        basically a way of making this a lower priority than direct calls to
        "check_status", which need to return ASAP.
        """
        glib.idle_add(self.callback, *args, **kwargs)
        # Switch to this method to just call it straight from here:
        # self.callback(*args, **kwargs)
    
    def check_status(self, path, recurse=False, invalidate=False,
                       summary=False, callback=True):
        """ Check the cached VCS status of the given path.
        
        This is a pass-through method to the check_status method of the DBUS
        service (which is, in turn, a wrapper around the real status cache). 
        """
        status = None
        try:
            status = self.status_cache.CheckStatus(path, recurse, invalidate,
                                                   summary, callback,
                                                   dbus_interface=INTERFACE,
                                                   timeout=TIMEOUT)
            # Test client error problems :)
            # raise dbus.DBusException("Test")
        except dbus.DBusException, ex:
            log.exception(ex)
            status = {path: {"text_status": "client_error",
                             "prop_status": "client_error"}}
        return status
    
def start():
    """ Starts the cache service, via the utility method in "service.py". """
    rabbitvcs.services.service.start_service(os.path.abspath(__file__), SERVICE,
                                             OBJECT_PATH)

def Main():
    """ The main point of entry for the cache service.
    
    This will set up the DBUS and glib extensions, the gobject/glib main loop,
    and start the service.
    """
    global log
    log = Log("rabbitvcs.services.cacheservice:main")
    log.debug("Cache: starting service: %s (%s)" % (OBJECT_PATH, os.getpid()))
    
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
     
    StatusCacheService(session_bus, mainloop)
    
    # import cProfile
    # import rabbitvcs.lib.helper
    # profile_data_file = os.path.join(
    #                        rabbitvcs.lib.helper.get_home_folder(),
    #                        "rvcs_cache.stats")
    # cProfile.run("mainloop.run()", profile_data_file)
    
    glib.idle_add(sys.stdout.write, "Started cache service\n")
    glib.idle_add(sys.stdout.flush)
    mainloop.run()
    
    log.debug("Cache: ended service: %s (%s)" % (OBJECT_PATH, os.getpid()))

if __name__ == "__main__":
    rabbitvcs.util.locale.initialize_locale()
    Main()