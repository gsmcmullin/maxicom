#!/usr/bin/python

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

import os, sys

from gi.repository import GObject, Gtk, Gdk
import gtkextra
import serialvte

import xmodem

def determine_path ():
    """Borrowed from wxglade.py"""
    try:
        root = __file__
        if os.path.islink (root):
            root = os.path.realpath (root)
        return os.path.dirname (os.path.abspath (root))
    except:
        print "I'm sorry, but something is wrong."
        print "There is no __file__ variable. Please contact the author."
        sys.exit ()

devs = ["/dev/ttyS0\n", "/dev/ttyS1\n", "/dev/ttyS2\n", "/dev/ttyS3\n",
    "/dev/ttyUSB0\n", "/dev/ttyUSB1\n", "/dev/ttyUSB2\n", "/dev/ttyUSB3\n",
    "/dev/ttyACM0\n", "/dev/ttyACM1\n", "/dev/ttyACM2\n", "/dev/ttyACM3\n"]

class MaxiCom:
    def __init__(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file(determine_path() + "/glade/maxicom.glade")
        self.builder.connect_signals(self)

	self.window = self.builder.get_object("main")

        self.ttydev = self.builder.get_object("ttydev");

	self.connect_button = self.builder.get_object("connect")
	self.connect_icon = self.builder.get_object("connect_icon")

        self.baudrate = self.builder.get_object("baudrate");
        self.databits = self.builder.get_object("databits");
        self.parity = self.builder.get_object("parity");
        self.stopbits = self.builder.get_object("stopbits");

        self.statusbar = self.builder.get_object("statusbar")
        self.statusid = self.statusbar.get_context_id("message")
        self.status("No open port!")

        hbox = self.builder.get_object("hbox")
        self.term = serialvte.SerialVTE()
        self.term.drag_dest_set(Gtk.DestDefaults.ALL, [],
                Gdk.DragAction.COPY | Gdk.DragAction.MOVE)
        self.term.drag_dest_add_uri_targets()
        self.term.connect("drag-data-received", self.drop_handler)
        self.term.connect("button-press-event", self.term_popup)
        self.term.connect("broken-pipe", self.broken_pipe_callback)
        self.term.set_font_from_string("Monospace 9")
        #self.term.set_colors(self.term.style.white, self.term.style.black, [])
        self.term.grab_focus()
        hbox.pack_start(self.term, True, True, 0)
        scrollbar = Gtk.VScrollbar(self.term.get_vadjustment())
        hbox.pack_end(scrollbar, False, False, 0)
        hbox.show_all()

        ttydev = self.builder.get_object("ttydev")
        self.devlist = Gtk.ListStore(str)
        for dev in devs:
            dev = dev.strip(" \t\r\n")
            if not dev or dev[0] == "#": continue
            try:
                os.stat(dev)
                self.devlist.append((dev,))
            except:
                pass
        sortdevlist = Gtk.TreeModelSort(self.devlist)
        sortdevlist.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        ttydev.set_model(sortdevlist)
        ttydev.set_entry_text_column(0)

	self.setserial(None)

	self.connected_group = Gtk.ActionGroup("connected_group")
	for action in ("paste", "send_files", "recv_files"):
		self.connected_group.add_action(self.builder.get_object(action))
        self.connected_group.set_sensitive(False)

        self.protocol = "xmodem"
        self.use1k = True

    def connect_toggled(self, connect):
        if connect.get_active():
            self.connect_icon.set_from_stock(Gtk.STOCK_DISCONNECT, Gtk.IconSize.BUTTON)
            # check if we're already open, because connect() sets our activeness.
            if not self.term.isOpen(): self.connect()
        else:
            self.connect_icon.set_from_stock(Gtk.STOCK_CONNECT, Gtk.IconSize.BUTTON)
            if self.term.isOpen(): self.disconnect()

    def disconnect(self, msg="Disconnected"):
	self.connect_button.set_active(False)
        self.term.close()
        self.connected_group.set_sensitive(False)
        self.status(msg)
        self.window.set_title("[%s] - MaxiCom" % self.ttydev.get_child().get_text())

    def term_popup(self, widget, event):
	if event.button != 3: return
	self.builder.get_object("term_popup").popup(None, None, None, None, event.button, event.time)

    def clear_buffer(self, widget):
        self.term.reset(True, True)

    def copy_selection(self, action):
	self.term.copy_clipboard()

    def paste_selection(self, action):
	if not self.term.isOpen(): return
	Gtk.clipboard_get().request_text(lambda x, y, z: self.term.write(y if y else ''))

    def status(self, msg):
        self.statusbar.pop(self.statusid)
        self.statusbar.push(self.statusid, msg)

    def broken_pipe_callback(self, term=None):
        self.disconnect("Broken Pipe!")
        gtkextra.QuickDialog("Disconnected", "Broken pipe!", parent=self.window).run()

    def control_handler(self, widget=None):
        if not self.term.isOpen(): return False
        try:
            self.builder.get_object("RI").set_active(self.term.getRI())
            self.builder.get_object("DSR").set_active(self.term.getDSR())
            self.builder.get_object("CD").set_active(self.term.getCD())
            self.builder.get_object("CTS").set_active(self.term.getCTS())
        except:
            self.broken_pipe_callback()
        return True

    def dtr_toggled(self, widget):
        if not self.term.isOpen(): return
        self.term.setDTR(widget.get_active())

    def rts_toggled(self, widget):
        if not self.term.isOpen(): return
        self.term.setRTS(widget.get_active())

    def connect(self):
        # Get info from main window
        port = self.ttydev.get_child().get_text()
        baud = self.baudrate.get_model()[self.baudrate.get_active()][0]
        data = self.databits.get_model()[self.databits.get_active()][0]
        par = self.parity.get_model()[self.parity.get_active()][0]
        stop = self.stopbits.get_model()[self.stopbits.get_active()][0]
        try: # to open the port
            self.disconnect()

            # Refuse to open controlling tty
            if port == "/dev/tty": raise Exception("Refusing to open /dev/tty")

            # Open the port and set parameters
            self.term.setPort(port)
            self.term.open()
            self.term.setDTR(self.builder.get_object("DTR").get_active())
            self.term.setRTS(self.builder.get_object("RTS").get_active())
            self.status("Connected on %s" % port)
            GObject.timeout_add(100, self.control_handler)
            # Add new port to list store
            if not self.ttydev.get_active_iter(): # Not selected from list
                self.devlist.append((port,))
            # Add new port to saved list
            port += "\n"
            if port not in devs:
                devs.append(port)

            # Update user interface
            self.term.grab_focus()
            self.connected_group.set_sensitive(True)
            self.connect_button.set_active(True)
            self.connect_button.set_sensitive(True)
            self.window.set_title("%s - MaxiCom" % port[:-1])

        except Exception as e:
            # Oops, we failed: complain
            self.disconnect("Failed to open %s: %s" % (port, e))

    def dev_changed(self, widget):
        self.connect()

    def setserial(self, widget):
        baud = self.baudrate.get_model()[self.baudrate.get_active()][0]
        data = self.databits.get_model()[self.databits.get_active()][0]
        par = self.parity.get_model()[self.parity.get_active()][0]
        stop = self.stopbits.get_model()[self.stopbits.get_active()][0]

        self.term.setBaudrate(baud)
        self.term.setByteSize(data)
        self.term.setParity(par)
        self.term.setStopbits(stop)

        self.term.grab_focus()

    def protocol_changed(self, widget):
        if not widget.get_active(): return
	self.protocol = widget.get_name()

    def toggle_use1k(self, widget):
        self.use1k = widget.get_active()

    def send_uris(self, uris):
        self.term.stop()
        try:
            xmodem.senders[self.protocol](self.term, uris, self.use1k)
        except Exception as e:
            gtkextra.QuickDialog("Transmission Failed!", str(e), parent=self.window)
        self.term.start()


    def menu_recv_files(self, action):
        if not self.term.isOpen(): return

        dialog = Gtk.FileChooserDialog("Receive File", parent=self.window,
                    action=Gtk.FileChooserAction.SAVE,
                    buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                             Gtk.STOCK_SAVE, Gtk.ResponseType.OK))

        if dialog.run() == Gtk.ResponseType.OK:
            dialog.hide()
            self.term.stop()
            xmodem.XModemReceiver(self.term, dialog.get_filename())
            self.term.start()

	dialog.destroy()


    def menu_send_files(self, action):
        if not self.term.isOpen(): return

        dialog = Gtk.FileChooserDialog("Send Files...", parent=self.window,
                    buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                             Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
	if self.protocol != "xmodem":
            dialog.set_select_multiple(True)

        if dialog.run() == Gtk.ResponseType.OK:
            dialog.hide()
            self.send_uris(dialog.get_uris())

	dialog.destroy()

    def drop_handler(self, widget, drag_context, x, y, selection_data,
                     info, time):
        if not self.term.isOpen():
            drag_context.finish(False, False, time)
            return

        self.send_uris(selection_data.get_uris())

        drag_context.finish(True, False, time)

    def exit(self, widget=None):
        Gtk.main_quit()

    def about(self, action=None):
        gtkextra.AboutBox(parent=self.window).run()

def main():
    global devs
    # Read saved device list
    devsfile = os.path.expanduser("~/.maxicomdevs")
    try:
        devs = open(devsfile).readlines()
    except:
        print "No saved device list, using defaults."

    maxicom = MaxiCom()
    Gtk.main()

    # Save updated device list
    open(devsfile, "w").writelines(devs)

if __name__ == "__main__":
    main()

