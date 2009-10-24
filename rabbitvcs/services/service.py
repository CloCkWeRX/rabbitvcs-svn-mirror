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

from rabbitvcs.lib.log import Log
log = Log("rabbitvcs.services.service")

def start_service(script_file, dbus_service_name, dbus_object_path):
    """
    This function is used to start our service.
    
    @rtype: boolean
    @return: Whether or not the service was successfully started.
    """
    
    try:
        session_bus = dbus.SessionBus()
        obj = session_bus.get_object(dbus_service_name, dbus_object_path)
        return True
    except dbus.DBusException, e:
        # FIXME: there must be a better way
        pid = subprocess.Popen([sys.executable, script_file]).pid
        log.debug("Started process: %s" % pid)
        # FIXME: hangs Nautilus when booting
        time.sleep(1)
        return True
        
    # Uh... unreachable?
    return False

