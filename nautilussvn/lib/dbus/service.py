#
# This is an extension to the Nautilus file manager to allow better 
# integration with the Subversion source control system.
# 
# Copyright (C) 2006-2008 by Jason Field <jason@jasonfield.com>
# Copyright (C) 2007-2008 by Bruce van der Kooij <brucevdkooij@gmail.com>
# Copyright (C) 2008-2008 by Adam Plumb <adamplumb@gmail.com>
# 
# NautilusSvn is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# NautilusSvn is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with NautilusSvn;  If not, see <http://www.gnu.org/licenses/>.
#

"""

This is our DBus service which registers all the objects we expose with the 
sesion bus.

"""

import os.path
import traceback
import subprocess
import time

import gobject

import dbus
import dbus.glib
import dbus.service

from nautilussvn.lib.dbus.status_monitor import StatusMonitor
from nautilussvn.lib.dbus.svn_client import SVNClient
from nautilussvn.lib.log import Log

log = Log("nautilussvn.lib.dbus.service")

INTERFACE = "org.google.code.nautilussvn.Service"
OBJECT_PATH = "/org/google/code/nautilussvn/Service"
SERVICE = "org.google.code.nautilussvn.NautilusSvn"

class Service(dbus.service.Object):
    
    def __init__(self, connection):
        dbus.service.Object.__init__(self, connection, OBJECT_PATH)
                    
        # Register our objects with the session bus by instantiating them
        self.status_monitor = StatusMonitor(connection)
        self.svn_client = SVNClient(connection)
    
    @dbus.service.method(INTERFACE, in_signature="", out_signature="")
    def Exit(self):
        self.status_monitor.Exit()
        loop.quit()

def start():
    """
    This function is used to start our service.
    
    @rtype: boolean
    @return: Whether or not the service was successfully started.
    """
    try:
        session_bus = dbus.SessionBus()
        session_bus.get_object(SERVICE, OBJECT_PATH)
        return True
    except dbus.DBusException:
        log.debug("The D-Bus service doesn't seem to be running, so starting.")
        # FIXME: there must be a better way
        dbus_service_path = os.path.abspath(__file__)
        subprocess.Popen(["/usr/bin/python", dbus_service_path]).pid
        # FIXME: hangs Nautilus when booting
        time.sleep(1)
        return True
        
    # Uh... unreachable?
    return False
    
def exit():
    """
    This function is used to exit a running service.
    """
    session_bus = dbus.SessionBus()
    try:
        service = session_bus.get_object(SERVICE, OBJECT_PATH)
        service.Exit()
    except:
        # Probably not running...
        traceback.print_exc()

if __name__ == "__main__":
    # The following calls are required to make DBus thread-aware and therefor
    # support the ability run threads.
    gobject.threads_init()
    dbus.glib.threads_init()
    
    # This registers our service name with the bus
    session_bus = dbus.SessionBus()
    name = dbus.service.BusName(SERVICE, session_bus) 
    service = Service(session_bus)
    
    loop = gobject.MainLoop()
    loop.run()
