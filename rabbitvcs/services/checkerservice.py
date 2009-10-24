import time
import os.path
import traceback
import thread

from Queue import Queue

import gobject

import dbus
import dbus.glib # FIXME: this might actually already set the default loop
import dbus.mainloop.glib
import dbus.service


import rabbitvcs.services.service
from rabbitvcs.services.statuschecker import StatusChecker, status_error

from rabbitvcs.lib.log import Log
log = Log("rabbitvcs.services.checkerservice")

INTERFACE = "org.google.code.rabbitvcs.StatusChecker"
OBJECT_PATH = "/org/google/code/rabbitvcs/StatusChecker"
SERVICE = "org.google.code.rabbitvcs.RabbitVCS.Checker"
TIMEOUT = 60*15 # seconds

class StatusCheckerService(dbus.service.Object):
    
    def __init__(self, connection):
        dbus.service.Object.__init__(self, connection, OBJECT_PATH)
        self.status_checker = StatusChecker()
                  
    @dbus.service.method(INTERFACE)
    def CheckStatus(self, path, recurse=False):
        return self.status_checker.check_status(u"" + path, recurse=recurse)
        
class StatusCheckerStub:
    def __init__(self):
        
        start()
        
        self.session_bus = dbus.SessionBus()
        
        self.result_queue = Queue()
        
        try:
            self.status_checker = self.session_bus.get_object(SERVICE, OBJECT_PATH)
        except dbus.DBusException:
            traceback.print_exc()
    
    def check_status(self, path, recurse=False):
        try:
            status = self.status_checker.CheckStatus(path, 
                                                     recurse, 
                                                     dbus_interface=INTERFACE, 
                                                     timeout=TIMEOUT)
        except dbus.DBusException, ex:
            log.exception(ex)
            status = [status_error(path)]
        return status
            
def start():
    rabbitvcs.services.service.start_service(os.path.abspath(__file__), SERVICE, OBJECT_PATH)

if __name__ == "__main__":
    
    import os
    
    log.debug("Checker: starting service: %s (%s)" % (OBJECT_PATH, os.getpid()))
    
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
    service = StatusCheckerService(session_bus)
    
    loop = gobject.MainLoop()
    loop.run()