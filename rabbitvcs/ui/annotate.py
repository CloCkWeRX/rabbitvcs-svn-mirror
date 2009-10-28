#
# This is an extension to the Nautilus file manager to allow better 
# integration with the Subversion source control system.
# 
# Copyright (C) 2006-2008 by Jason Field <jason@jasonfield.com>
# Copyright (C) 2007-2008 by Bruce van der Kooij <brucevdkooij@gmail.com>
# Copyright (C) 2008-2008 by Adam Plumb <adamplumb@gmail.com>
# 
# RabbitVCS is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# RabbitVCS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with RabbitVCS;  If not, see <http://www.gnu.org/licenses/>.
#

import os

import pygtk
import gobject
import gtk

from datetime import datetime
import time

from rabbitvcs.ui import InterfaceView
from rabbitvcs.ui.log import LogDialog
from rabbitvcs.ui.action import VCSAction
import rabbitvcs.ui.widget
from rabbitvcs.ui.dialog import MessageBox
import rabbitvcs.lib.helper
import rabbitvcs.lib.vcs

from rabbitvcs import gettext
_ = gettext.gettext

DATETIME_FORMAT = rabbitvcs.lib.helper.LOCAL_DATETIME_FORMAT

class Annotate(InterfaceView):
    """
    Provides a UI interface to annotate items in the repository or
    working copy.
    
    Pass a single path to the class when initializing
    
    """
    
    def __init__(self, path, revision=None):
        if os.path.isdir(path):
            MessageBox(_("Cannot annotate a directory"))
            raise SystemExit()
            return
            
        InterfaceView.__init__(self, "annotate", "Annotate")

        self.get_widget("Annotate").set_title(_("Annotate - %s") % path)
        
        self.vcs = rabbitvcs.lib.vcs.create_vcs_instance()
        
        if revision is None:
            revision = "HEAD"
        
        self.path = path
        self.get_widget("from").set_text(str(1))
        self.get_widget("to").set_text(str(revision))

        self.table = rabbitvcs.ui.widget.Table(
            self.get_widget("table"),
            [gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, 
                gobject.TYPE_STRING, gobject.TYPE_STRING], 
            [_("Line"), _("Revision"), _("Author"), 
                _("Date"), _("Text")]
        )
        self.table.allow_multiple()
        
        self.load()
        
    def on_destroy(self, widget):
        self.close()
        
    def on_close_clicked(self, widget):
        self.close()

    def on_save_clicked(self, widget):
        self.save()

    def on_refresh_clicked(self, widget):
        self.load()

    def on_from_show_log_clicked(self, widget, data=None):
        LogDialog(self.path, ok_callback=self.on_from_log_closed)
    
    def on_from_log_closed(self, data):
        if data is not None:
            self.get_widget("from").set_text(data)

    def on_to_show_log_clicked(self, widget, data=None):
        LogDialog(self.path, ok_callback=self.on_to_log_closed)
    
    def on_to_log_closed(self, data):
        if data is not None:
            self.get_widget("to").set_text(data)


    #
    # Helper methods
    #
    
    def load(self):
        from_rev_num = self.get_widget("from").get_text().lower()
        to_rev_num = self.get_widget("to").get_text().lower()
        
        if not from_rev_num.isdigit():
            MessageBox(_("The from revision field must be an integer"))
            return
             
        from_rev = self.vcs.revision("number", number=int(from_rev_num))
        
        to_rev = self.vcs.revision("head")
        if to_rev_num.isdigit():
            to_rev = self.vcs.revision("number", number=int(to_rev_num))
        
        self.action = VCSAction(
            self.vcs,
            notification=False
        )    

        self.action.append(
            self.vcs.annotate,
            self.path,
            from_rev,
            to_rev
        )
        self.action.append(self.populate_table)
        self.action.append(self.enable_saveas)
        self.action.start()

    def populate_table(self):
        blamedict = self.action.get_result(0)

        self.table.clear()
        for item in blamedict:            
            # remove fractional seconds and timezone information from 
            # the end of the string provided by pysvn:
            # * timezone should be always "Z" (for UTC), "%Z" is not yet
            #   yet supported by strptime
            # * fractional could be parsed with "%f" since python 2.6 
            #   but this precision is not needed anyway 
            # * the datetime module does not include strptime until python 2.4
            #   so this workaround is required for now
            datestr = item["date"][0:-8]
            date = datetime(*time.strptime(datestr,"%Y-%m-%dT%H:%M:%S")[:-2])
                
            self.table.append([
                item["number"],
                item["revision"].number,
                item["author"],
                datetime.strftime(date,DATETIME_FORMAT),
                item["line"]
            ])
            
    def generate_string_from_result(self):
        blamedict = self.action.get_result(0)
        
        text = ""
        for item in blamedict:
            datestr = item["date"][0:-8]
            date = datetime(*time.strptime(datestr,"%Y-%m-%dT%H:%M:%S")[:-2])
            
            text += "%s\t%s\t%s\t%s\t%s\n" % (
                item["number"],
                item["revision"].number,
                item["author"],
                datetime.strftime(date,DATETIME_FORMAT),
                item["line"]
            )
        
        return text
            
    def enable_saveas(self):
        self.get_widget("save").set_sensitive(True)

    def disable_saveas(self):
        self.get_widget("save").set_sensitive(False)

    def save(self, path=None):
        if path is None:
            from rabbitvcs.ui.dialog import FileSaveAs
            dialog = FileSaveAs()
            path = dialog.run()

        if path is not None:
            fh = open(path, "w")
            fh.write(self.generate_string_from_result())
            fh.close()

if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, args) = main()
    
    pathrev = rabbitvcs.lib.helper.parse_path_revision_string(args.pop(0))

    window = Annotate(pathrev[0], pathrev[1])
    window.register_gtk_quit()
    gtk.main()
