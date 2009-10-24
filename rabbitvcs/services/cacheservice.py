import os.path
import sys
import traceback

import gobject, glib

import dbus
import dbus.glib # FIXME: this might actually already set the default loop
import dbus.mainloop.glib
import dbus.service


import rabbitvcs.services.service
from rabbitvcs.services.checkerservice import StatusCheckerStub
from rabbitvcs.services.statuscache import StatusCache
from rabbitvcs.services.statuschecker import StatusChecker

from rabbitvcs.lib.log import Log
log = Log("rabbitvcs.services.cacheservice")

INTERFACE = "org.google.code.rabbitvcs.StatusCache"
OBJECT_PATH = "/org/google/code/rabbitvcs/StatusCache"
SERVICE = "org.google.code.rabbitvcs.RabbitVCS.Cache"
TIMEOUT = 60*15*100 # seconds

class StatusCacheService(dbus.service.Object):
    
    def __init__(self, connection):
        dbus.service.Object.__init__(self, connection, OBJECT_PATH)
        
        # Start the status checking daemon so we can do requests in the background
        self.status_cache = StatusCache()
        
    @dbus.service.signal(INTERFACE)
    def CheckFinished(self, path, statuses):
        pass
        
    @dbus.service.method(INTERFACE)
    def CheckStatus(self, path, recurse=False, invalidate=False, callback=False):
        callback = self.CheckFinished if callback else None
        return self.status_cache.check_status(u"" + path, recurse=recurse, invalidate=invalidate, callback=callback)
        
class StatusCacheStub:
    def __init__(self, status_callback=None):
        
        start()
        
        self.session_bus = dbus.SessionBus()
        self.status_callback = status_callback
        
        try:
            self.status_cache = self.session_bus.get_object(SERVICE, OBJECT_PATH)
            if self.status_callback:
                self.status_cache.connect_to_signal("CheckFinished", self.glib_callback, dbus_interface=INTERFACE)
        except dbus.DBusException:
            traceback.print_exc()
    
    def glib_callback(self, *args, **kwargs):
        glib.idle_add(self.status_callback, *args, **kwargs)
        # Switch to this method to just call it straight from here:
        # self.status_callback(*args, **kwargs)
    
    def check_status(self, path, recurse=False, invalidate=False, callback=True):
        status = None
        try:
            status = self.status_cache.CheckStatus(path, recurse, invalidate, callback, dbus_interface=INTERFACE, timeout=TIMEOUT)
            # Test client error problems :)
            # raise dbus.DBusException("Test")
        except dbus.DBusException, ex:
            log.exception(ex)
            status = {path: {"text_status": "client_error", "prop_status": "client_error"}}
        return status
    
def start():
    rabbitvcs.services.service.start_service(os.path.abspath(__file__), SERVICE, OBJECT_PATH)

if __name__ == "__main__":
    
    import os
    log = Log("rabbitvcs.services.cacheservice:main")
    log.debug("Cache: starting service: %s (%s)" % (OBJECT_PATH, os.getpid()))
        
    rabbitvcs.util.locale.initialize_locale()
    
    # We need this to for the client to be able to do asynchronous calls
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    
    # The following calls are required to make DBus thread-aware and therefor
    # support the ability run threads.
    gobject.threads_init()
    dbus.glib.threads_init()
    
    # This registers our service name with the bus
    session_bus = dbus.SessionBus()
    name = dbus.service.BusName(SERVICE, session_bus) 
    service = StatusCacheService(session_bus)
    
    mainloop = gobject.MainLoop()
    mainloop.run()
    
    log.debug("End of main method!")