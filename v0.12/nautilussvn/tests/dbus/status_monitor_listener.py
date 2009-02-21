import gobject

import dbus
import dbus.service
import dbus.mainloop.glib

INTERFACE = "org.google.code.nautilussvn.StatusMonitor"
OBJECT_PATH = "/org/google/code/nautilussvn/StatusMonitor"
SERVICE = "org.google.code.nautilussvn.NautilusSvn"

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
bus = dbus.SessionBus()
object = bus.get_object(SERVICE, OBJECT_PATH)

def cb_status(path, status):
    print path, status
    
object.connect_to_signal("StatusChanged", cb_status, dbus_interface=INTERFACE)

loop = gobject.MainLoop()
loop.run()
