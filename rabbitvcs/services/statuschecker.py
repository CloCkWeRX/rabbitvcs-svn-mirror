import time
import traceback
import thread

import dbus
import dbus.service

from rabbitvcs.services.statuscache import StatusCache
from rabbitvcs.services.statuschecker_proc import StatusChecker

INTERFACE = "org.google.code.rabbitvcs.StatusCache"
OBJECT_PATH = "/org/google/code/rabbitvcs/StatusCache"
SERVICE = "org.google.code.rabbitvcs.RabbitVCS"
TIMEOUT = 60*15 # seconds

class StatusCacheService(dbus.service.Object):
    
    def __init__(self, connection):
        dbus.service.Object.__init__(self, connection, OBJECT_PATH)
        
        # Start the status checking daemon so we can do requests in the background
        self.status_cache = StatusCache(StatusChecker())
        self.status_cache.start()
        
    @dbus.service.signal(INTERFACE)
    def CheckFinished(self, path, statuses):
        pass
        
    @dbus.service.method(INTERFACE)
    def CheckStatus(self, path, recurse=False, invalidate=False, callback=True):
        callback = self.CheckFinished if callback else None
        return self.status_cache.check_status(u"" + path, recurse=recurse, invalidate=invalidate, callback=callback)
        
class StatusCacheStub:
    def __init__(self, status_callback=None):
        self.session_bus = dbus.SessionBus()
        self.status_callback = status_callback
        
        try:
            self.status_cache = self.session_bus.get_object(SERVICE, OBJECT_PATH)
            if self.status_callback:
                self.status_cache.connect_to_signal("CheckFinished", self.status_callback, dbus_interface=INTERFACE)
        except dbus.DBusException:
            traceback.print_exc()
    
    def check_status(self, path, recurse=False, invalidate=False, callback=True):
        status = None
        try:
            status = self.status_cache.CheckStatus(path, recurse, invalidate, callback, dbus_interface=INTERFACE, timeout=TIMEOUT)
            # Test client error problems :)
            # raise dbus.DBusException("Test")
        except dbus.DBusException, ex:
            # An exception here is probably caused by large amounts of data
            # triggering a timeout. We could make the timeout arbitrarily large,
            # but I don't know if that's wise. -JH
            from rabbitvcs.lib.extensions.nautilus.RabbitVCS import log
            log.exception(ex)
            status = {path: {"text_status": "client_error", "prop_status": "client_error"}}
        return status
            
        
        
