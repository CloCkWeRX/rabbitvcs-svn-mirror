"""

This is our DBus service which registers all the objects we expose with the 
sesion bus.

"""
import sys
import traceback
import subprocess
import time

import gobject

import dbus
import dbus.glib # FIXME: this might actually already set the default loop
import dbus.mainloop.glib
import dbus.service

import rabbitvcs.util.locale
import rabbitvcs.services.cacheservice
from rabbitvcs.services.cacheservice import StatusCacheService

SERVICE = "org.google.code.rabbitvcs.RabbitVCS"

def start_service(script_file, dbus_object_path):
    """
    This function is used to start our service.
    
    @rtype: boolean
    @return: Whether or not the service was successfully started.
    """
    
    try:
        session_bus = dbus.SessionBus()
        session_bus.get_object(SERVICE, dbus_object_path)
        return True
    except dbus.DBusException:
        # FIXME: there must be a better way
        subprocess.Popen([sys.executable, script_file]).pid
        # FIXME: hangs Nautilus when booting
        time.sleep(1)
        return True
        
    # Uh... unreachable?
    return False

def exit(dbus_object_path):
    """
    This function is used to exit a running service.
    """
    session_bus = dbus.SessionBus()
    try:
        service = session_bus.get_object(SERVICE, dbus_object_path)
        service.Exit()
    except:
        # Probably not running...
        traceback.print_exc()
