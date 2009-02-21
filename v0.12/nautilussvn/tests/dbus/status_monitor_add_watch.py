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

if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    if len(args) < 1:
        raise SystemExit("Usage: python %s [path1] [path2] ..." % __file__)
    
    for path in args:
        object.add_watch(path)
