import traceback

import gobject


import dbus
import dbus.glib
import dbus.service
import dbus.mainloop.glib

INTERFACE = "org.google.code.nautilussvn.StatusMonitor"
OBJECT_PATH = "/org/google/code/nautilussvn/ThreadingTest"
SERVICE = "org.google.code.nautilussvn.NautilusSvn"

class ThreadingTest(dbus.service.Object):
    
    def __init__(self, connection):
        gobject.threads_init()
        dbus.glib.threads_init()
        def asynchronous_function():
            import time
            while True:
                print "SLEEEEPERRR"
                time.sleep(1)
            
        import thread
        thread.start_new_thread(asynchronous_function, ())
        
    @dbus.service.signal(INTERFACE)
    def service_signal(self, message):
        pass
    
    @dbus.service.method(INTERFACE)
    def service_method(self, message):
        self.service_signal(message)
        
    @dbus.service.method(INTERFACE, in_signature="", out_signature="")
    def exit(self):
        loop.quit()
        
if __name__ == "__main__":
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    session_bus = dbus.SessionBus()
    name = dbus.service.BusName(SERVICE, session_bus)
    status_monitor = ThreadingTest(session_bus)
    
    loop = gobject.MainLoop()
    loop.run()
