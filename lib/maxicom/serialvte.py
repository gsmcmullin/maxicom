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

from serial import Serial
import os
import re
import gobject, gtk, vte

class LockingSerial(Serial):
    """Serial class implementing device locking."""

    def open(self):
        self.lockfile = "/var/lock/LCK.." + os.path.basename(self.portstr)
        if os.path.exists(self.lockfile): # if device is locked
            lockpid = int(re.search("\w*[0-9]+", open(self.lockfile).read()).group(0))
            # see if this is a stale lock
            try: os.getpgid(lockpid)
            except: lockpid = 0
            if lockpid: # refuse to connect if valid lock
                self.lockfile = None
                raise Exception("Locked by process %d" % lockpid)

        # claim lock for this process
        lock = open(self.lockfile, "w")
        lock.write("%10d\n" % os.getpid())
        lock.close()

	Serial.open(self)

    def close(self):
	try: os.unlink(self.lockfile)
        except: pass
        Serial.close(self)


class SerialVTE(vte.Terminal, LockingSerial):
    __gsignals__ = {
        'broken-pipe': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ())
    }

    """Virtual terminal emulator class which connects a serial port to a GTK+ widget"""
    def __init__(self):
        self.__gobject_init__()
        vte.Terminal.__init__(self)
        LockingSerial.__init__(self, timeout=0)
        self.set_backspace_binding(1)
        self._output_source = self._input_source = None

    def start(self):
        """Initiate connection between serial instance and vte widget"""
        if self.isOpen():
            self._output_source = self.connect("commit", SerialVTE._output_handler)
            self._input_source = gobject.io_add_watch(self, gobject.IO_IN, self._input_handler)

    def stop(self):
        """Break connection between serial instance and vte widget"""
        if self.isOpen(): 
            if self._input_source: gobject.source_remove(self._input_source)
            if self._output_source: self.disconnect(self._output_source)
        self._output_source = self._input_source = None

    def open(self):
        LockingSerial.open(self)
        self.start()

    def close(self):
        self.stop()
        LockingSerial.close(self)

    def _output_handler(self, data, size):
        if self.isOpen(): self.write(data)

    def _input_handler(self, dev, conf):
        data = self.read(1024)
        if not data:
            self.close()
            self.emit("broken-pipe")
            return False
        self.feed(data)
        return True

    def do_unmap(self):
        self.close()

if __name__ == "__main__":
    window = gtk.Window()
    window.connect("destroy", gtk.main_quit)
    term = SerialVTE()
    term.setPort("/dev/ttyUSB0")
    term.setBaudrate(115200)
    term.open()
    window.add(term)
    window.show_all()
    gtk.main()
    term.close()

