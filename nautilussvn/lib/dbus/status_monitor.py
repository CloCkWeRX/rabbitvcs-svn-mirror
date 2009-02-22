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

import traceback
import thread

import dbus
import dbus.service

from nautilussvn.lib.vcs.svn.status_monitor import StatusMonitor as SVNStatusMonitor

INTERFACE = "org.google.code.nautilussvn.StatusMonitor"
OBJECT_PATH = "/org/google/code/nautilussvn/StatusMonitor"
SERVICE = "org.google.code.nautilussvn.NautilusSvn"

class StatusMonitor(dbus.service.Object):
    """
    We can pretty much do all of this directly on the StatusMonitor itself,
    we'll just have to do make sure we do the type conversion before calling
    anything else. If you pass a dbus.String to PySVN for example it won't
    know what to do (hence the path.encode("utf-8") statements).
    """
    
    def __init__(self, connection):
        dbus.service.Object.__init__(self, connection, OBJECT_PATH)
            
        self.status_monitor = SVNStatusMonitor(self.StatusChanged)
        
    @dbus.service.signal(INTERFACE)
    def StatusChanged(self, path, status):
        pass
    
    @dbus.service.signal(INTERFACE)
    def WatchAdded(self, path):
        pass
    
    @dbus.service.method(INTERFACE)
    def ChangeStatus(self, path, status):
        self.StatusChanged(path, status)
        
    @dbus.service.method(INTERFACE)
    def HasWatch(self, path):
        # FIXME: still doesn't return an actual boolean but 1/0.
        return bool(self.status_monitor.has_watch(path.encode("utf-8")))
        
    @dbus.service.method(INTERFACE)
    def AddWatch(self, path):
        self.status_monitor.add_watch(path.encode("utf-8"))
        self.WatchAdded(path)
        
    @dbus.service.method(INTERFACE)
    def Status(self, path, invalidate=False, bypass=False):
        self.status_monitor.status(path.encode("utf-8"), bool(invalidate), bool(bypass))
        
    @dbus.service.method(INTERFACE, in_signature="", out_signature="")
    def Exit(self):
        self.status_monitor.notifier.stop()
        
class StatusMonitorStub:
    """
    This isn't something from DBus but it looked like a good idea to me to
    make using the StatusMonitor easier. We can probably do this dynamically
    though, maybe request an object path and then get a generated stub back.
    """
    
    def __init__(self, status_callback, watch_added_callback):
        self.session_bus = dbus.SessionBus()
        
        self.status_callback = status_callback
        self.watch_added_callback = watch_added_callback
        
        try:
            self.status_monitor = self.session_bus.get_object(SERVICE, OBJECT_PATH)
            self.status_monitor.connect_to_signal("StatusChanged", self.cb_status, dbus_interface=INTERFACE)
            self.status_monitor.connect_to_signal("WatchAdded", self.cb_watch_added, dbus_interface=INTERFACE)
        except dbus.DBusException:
            traceback.print_exc()
    
    def has_watch(self, path):
        return bool(self.status_monitor.HasWatch(path, dbus_interface=INTERFACE))
        
    def add_watch(self, path):
        self.status_monitor.AddWatch(
            path, 
            dbus_interface=INTERFACE
        )
    
    def status(self, path, invalidate=False, bypass=False):
        self.status_monitor.Status(
            path, 
            invalidate, 
            bypass,
            dbus_interface=INTERFACE
        )
    
    def cb_status(self, path, status):
        self.status_callback(path.encode("utf-8"), status.encode("utf-8"))
        
    def cb_watch_added(self, path):
        self.watch_added_callback(path.encode("utf-8"))
        
    def exit(self):
        self.status_monitor.Exit()
