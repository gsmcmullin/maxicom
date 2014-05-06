#    MaxiCom -- A serial port terminal emulator for the GNOME desktop.
#    Copyright (C) 2010  Gareth McMullin
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import gtk
from strings import *
from traceback import format_exception

class QuickDialog(gtk.MessageDialog):
        def __init__(self, message, secondary=None, type=gtk.MESSAGE_ERROR, parent=None):
                gtk.MessageDialog.__init__(self, buttons=gtk.BUTTONS_CLOSE,
                                message_format=message, type=type, parent=parent,
                                flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT)
                self.set_title(message)
                if secondary: self.format_secondary_text(secondary)
                self.connect("response", lambda x,y: x.destroy())
                self.show_all()

def QuickWarnDialog(message, secondary=None):
        return QuickDialog(message, secondary, type=gtk.MESSAGE_WARNING)

def QuickInfoDialog(message, secondary=None):
        return QuickDialog(message, secondary, type=gtk.MESSAGE_INFO)

def gtk_excepthook(type, value, traceback):
        sys.__excepthook__(type, value, traceback)
        if globals().has_key("error_on_screen"): return
        global error_on_screen
        error_on_screen = True
        QuickDialog("You've been bitten by a program bug!",
                        "".join(format_exception(type, value, traceback))).run()
        exit(-1)

sys.excepthook = gtk_excepthook

class AboutBox(gtk.AboutDialog):
	def __init__(self, parent=None):
		gtk.AboutDialog.__init__(self)
		self.set_name(PACKAGE)
		self.set_version(VERSION)
		self.set_copyright(COPYRIGHT)
		self.set_comments(DESCRIPTION)
		self.set_license(LICENSE_TEXT)
		self.set_website(URL)
		self.set_authors([AUTHOR])
		self.set_transient_for(parent)
		self.connect("response", lambda x, y: x.destroy())


