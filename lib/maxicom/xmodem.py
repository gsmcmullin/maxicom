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

from gi.repository import GObject, Gtk
import serial
import struct
from urllib2 import urlopen
import gtkextra

crctab = (
    0x0000,  0x1021,  0x2042,  0x3063,  0x4084,  0x50a5,  0x60c6,  0x70e7,
    0x8108,  0x9129,  0xa14a,  0xb16b,  0xc18c,  0xd1ad,  0xe1ce,  0xf1ef,
    0x1231,  0x0210,  0x3273,  0x2252,  0x52b5,  0x4294,  0x72f7,  0x62d6,
    0x9339,  0x8318,  0xb37b,  0xa35a,  0xd3bd,  0xc39c,  0xf3ff,  0xe3de,
    0x2462,  0x3443,  0x0420,  0x1401,  0x64e6,  0x74c7,  0x44a4,  0x5485,
    0xa56a,  0xb54b,  0x8528,  0x9509,  0xe5ee,  0xf5cf,  0xc5ac,  0xd58d,
    0x3653,  0x2672,  0x1611,  0x0630,  0x76d7,  0x66f6,  0x5695,  0x46b4,
    0xb75b,  0xa77a,  0x9719,  0x8738,  0xf7df,  0xe7fe,  0xd79d,  0xc7bc,
    0x48c4,  0x58e5,  0x6886,  0x78a7,  0x0840,  0x1861,  0x2802,  0x3823,
    0xc9cc,  0xd9ed,  0xe98e,  0xf9af,  0x8948,  0x9969,  0xa90a,  0xb92b,
    0x5af5,  0x4ad4,  0x7ab7,  0x6a96,  0x1a71,  0x0a50,  0x3a33,  0x2a12,
    0xdbfd,  0xcbdc,  0xfbbf,  0xeb9e,  0x9b79,  0x8b58,  0xbb3b,  0xab1a,
    0x6ca6,  0x7c87,  0x4ce4,  0x5cc5,  0x2c22,  0x3c03,  0x0c60,  0x1c41,
    0xedae,  0xfd8f,  0xcdec,  0xddcd,  0xad2a,  0xbd0b,  0x8d68,  0x9d49,
    0x7e97,  0x6eb6,  0x5ed5,  0x4ef4,  0x3e13,  0x2e32,  0x1e51,  0x0e70,
    0xff9f,  0xefbe,  0xdfdd,  0xcffc,  0xbf1b,  0xaf3a,  0x9f59,  0x8f78,
    0x9188,  0x81a9,  0xb1ca,  0xa1eb,  0xd10c,  0xc12d,  0xf14e,  0xe16f,
    0x1080,  0x00a1,  0x30c2,  0x20e3,  0x5004,  0x4025,  0x7046,  0x6067,
    0x83b9,  0x9398,  0xa3fb,  0xb3da,  0xc33d,  0xd31c,  0xe37f,  0xf35e,
    0x02b1,  0x1290,  0x22f3,  0x32d2,  0x4235,  0x5214,  0x6277,  0x7256,
    0xb5ea,  0xa5cb,  0x95a8,  0x8589,  0xf56e,  0xe54f,  0xd52c,  0xc50d,
    0x34e2,  0x24c3,  0x14a0,  0x0481,  0x7466,  0x6447,  0x5424,  0x4405,
    0xa7db,  0xb7fa,  0x8799,  0x97b8,  0xe75f,  0xf77e,  0xc71d,  0xd73c,
    0x26d3,  0x36f2,  0x0691,  0x16b0,  0x6657,  0x7676,  0x4615,  0x5634,
    0xd94c,  0xc96d,  0xf90e,  0xe92f,  0x99c8,  0x89e9,  0xb98a,  0xa9ab,
    0x5844,  0x4865,  0x7806,  0x6827,  0x18c0,  0x08e1,  0x3882,  0x28a3,
    0xcb7d,  0xdb5c,  0xeb3f,  0xfb1e,  0x8bf9,  0x9bd8,  0xabbb,  0xbb9a,
    0x4a75,  0x5a54,  0x6a37,  0x7a16,  0x0af1,  0x1ad0,  0x2ab3,  0x3a92,
    0xfd2e,  0xed0f,  0xdd6c,  0xcd4d,  0xbdaa,  0xad8b,  0x9de8,  0x8dc9,
    0x7c26,  0x6c07,  0x5c64,  0x4c45,  0x3ca2,  0x2c83,  0x1ce0,  0x0cc1,
    0xef1f,  0xff3e,  0xcf5d,  0xdf7c,  0xaf9b,  0xbfba,  0x8fd9,  0x9ff8,
    0x6e17,  0x7e36,  0x4e55,  0x5e74,  0x2e93,  0x3eb2,  0x0ed1,  0x1ef0
)
updcrc = lambda cp, crc: (crctab[((crc >> 8) & 255)] ^ (crc << 8) ^ cp) & 0xffff
def calccrc(data):
    crc = 0
    for b in data: crc = updcrc(ord(b), crc)
    return struct.pack(">H", crc)

# Control Codes
SOH = chr(0x01)
STX = chr(0x02)
EOT = chr(0x04)
ACK = chr(0x06)
NAK = chr(0x15)
CAN = chr(0x18)

class FileTransfer(Gtk.Dialog):
    """Superclass for file transfers: Provides user interface functionality"""
    def __init__(self, text):
        Gtk.Dialog.__init__(self, flags=Gtk.DIALOG_MODAL, 
                buttons=(Gtk.STOCK_CANCEL, Gtk.RESPONSE_CANCEL))
        self.connect("response", self.do_close)
        self.connect("delete-event", self.do_close)
        self.set_title("File Transfer")

        vbox = Gtk.VBox(False,8)
        vbox.set_border_width(8)
        self.text = Gtk.Label()
        self.text.set_markup(text)
        self.text.set_alignment(0, 0.5)
        vbox.pack_start(self.text, False, False)
        self._progress = Gtk.ProgressBar()
        vbox.pack_start(self._progress, False, False)
        self.status = Gtk.Label()
        self.status.set_alignment(0, 0.5)
        vbox.pack_start(self.status, False, False)
        self.vbox.pack_start(vbox)
        self.show_all()

    def set_progress(self, fraction, text=None):
        if fraction == -1:
            self._progress.pulse()
        else:
            self._progress.set_fraction(fraction)
        if text: self.status.set_text("Status: " + text)

    def set_text(self, text):
        self.text.set_markup(text)

    def do_close(self, widget, response):
        self.hide()


class Sender(FileTransfer):
    def __init__(self, tty, use1k=True):
        FileTransfer.__init__(self, "<big><b>Transmission in progress...</b></big>")
        self.tty = tty
        self.use1k = use1k
        self.blocksize = 1024 if use1k else 128
        self.usecrc = False
        self.source = GObject.io_add_watch(tty, GObject.IO_IN, self._in_cb)
        self.set_progress(0, "Waiting for receiver...")
        self.next_file()
        self.block, self.packet = self.next_packet()
        self.sent_eot = False

    def _in_cb(self, source, cond):
        ack = source.read(1)

        if ack == CAN and source.read(1) == CAN:
            self.hide()
            gtkextra.QuickDialog("Transmission failed!", "Transmission cancelled by peer!").run()
            self.do_close()

        if (ack != ACK) and (ack != NAK) and (ack != 'C'):
            return True

        if ack == 'C': self.usecrc = True

        if ack == ACK:
            if self.sent_eot:
                if self.next_file():
                    self.block, self.packet = self.next_packet()
                    return True
                else:
                    return False

            self.block, self.packet = self.next_packet()

        if not self.packet:
            self.tty.write(EOT)
            self.sent_eot = True
            self.set_progress(1, "Sent EOT")
            return True

        packet = STX if self.use1k else SOH
        packet += chr(self.block & 0xFF) + chr(255-(self.block & 0xFF))
        if self.usecrc:
            packet += self.packet + calccrc(self.packet + "\0\0")
        else:
            packet += self.packet + chr(sum(ord(i) for i in self.packet) & 0xff)

        source.write(packet)
        return True


class XModemSender(Sender):
    def __init__(self, tty, uris, use1k=True):
        if len(uris) != 1:
            raise Exception("XMODEM only supports transfer of a single file")
        self.block = 0
        self.data = urlopen(uris[0]).read()
        Sender.__init__(self, tty, use1k)
        self.blockcount = (len(self.data) + self.blocksize - 1) / self.blocksize
        self.set_text("<big><b>XMODEM Transmission in progress...</b></big>\n\nSending: %s" % uris[0])
        Gtk.main()

    def next_packet(self):
        if not self.data: return 0, None
        if self.block:
            self.set_progress(float(self.block) / self.blockcount, 
                              "Sending block %d" % self.block)
        payload = self.data[:self.blocksize].ljust(self.blocksize, EOT)
        self.data = self.data[self.blocksize:]
        return self.block + 1, payload

    def next_file(self):
	if self.data: return True
        self.do_close()
        return False

    def do_close(self, widget=None, response=None):
        if self.data: self.tty.write(CAN+CAN)
        GObject.source_remove(self.source)
        FileTransfer.do_close(self, widget, response)
        Gtk.main_quit()


class YModemSender(Sender):
    def __init__(self, tty, uris, use1k=True):
        self.block = -1
        self.uris = list(uris)
        self.filedata = [urlopen(url).read() for url in uris]
        self.blocksize = 1024 if use1k else 128
	self.sentlast = False
        self.totalsize = sum(1024 + len(data) for data in self.filedata)
	self.sentsize = 0
        Sender.__init__(self, tty, use1k)
        Gtk.main()

    def next_packet(self):
        if not self.data: return 0, None
	self.sentsize += min(len(self.data), self.blocksize)
        if self.block > 0:
            self.set_progress(float(self.sentsize) / self.totalsize, 
                              "Sending block %d of %s" % (self.block, self.filename))
        payload = self.data[:self.blocksize].ljust(self.blocksize, EOT)
        self.data = self.data[self.blocksize:]
        return self.block + 1, payload

    def next_file(self):
	if not self.uris:
            if self.sentlast:
                self.do_close()
                return False
            self.data = str.ljust("", self.blocksize, "\0")
            self.block = -1;
            self.sentlast = True
            return True

        url = self.uris.pop(0)
        print url
        self.set_text("<big><b>YMODEM Transmission in progress...</b></big>\n\nSending: %s" % url)
	_, _, self.filename = url.rpartition('/')
	self.data = self.filedata.pop(0)
	firstpacket = str.ljust((self.filename + "\0" + str(len(self.data))), self.blocksize, "\0")
	self.data = firstpacket + self.data
        self.block = -1
        self.sent_eot = False
        return True

    def do_close(self, widget=None, response=None):
        if self.data: self.tty.write(CAN+CAN)
        GObject.source_remove(self.source)
        FileTransfer.do_close(self, widget, response)
        Gtk.main_quit()


class XModemReceiver(FileTransfer):
    def __init__(self, tty, filename):
        FileTransfer.__init__(self, "<big><b>XMODEM Reception in progress...</b></big>\n\nSaving file: " + filename)
        self.file = open(filename, "w")
        self.tty = tty
        self.block = 1
        self.usecrc = 10
        self.in_source = GObject.io_add_watch(tty, GObject.IO_IN, self._in_cb)
        self.timeout_source = GObject.timeout_add(1000, self._timeout)
        self.set_progress(0, "Waiting for sender...")
        self.tty.write("C")
        self.tty.setTimeout(0.1)
        Gtk.main()

    def _in_cb(self, source, cond):
        # Restart the timer
        GObject.source_remove(self.timeout_source)
        self.timeout_source = GObject.timeout_add(1000, self._timeout)

        start = source.read(1)
	if start == EOT: # End of transmission.
            self.tty.write(ACK)
            self.do_close()
            return False
        if (start != SOH) and (start != STX):
            return True

        blocksize = 1024 if start == STX else 128
        block = ord(source.read(1))
	blockcheck = 255 - ord(source.read(1))

        data = source.read(blocksize)
        if self.usecrc:
            if source.read(2) != calccrc(data + "\0\0"):
                source.write("C")
                return True
        else:
            if source.read(1) != chr(sum(ord(i) for i in data) & 0xff):
                source.write(NAK)
                return True

        if block != blockcheck:
            self.tty.write("C" if self.usecrc else NAK)
            return True

        if block == self.block & 0xFF:
            self.set_progress(-1, "Received block %d" % self.block)
            self.file.write(data)
            self.block += 1
            source.write(ACK)
            return True

        if block == (self.block - 1) & 0xFF:
            source.write(ACK)
            return True


        return True

    def _timeout(self):
        if self.usecrc: self.usecrc -= 1
        self.tty.write("C" if self.usecrc else NAK)
        return True

    def do_close(self, widget=None, response=None):
        self.tty.setTimeout(0)
        self.file.close()
        if response == Gtk.RESPONSE_CANCEL: self.tty.write(CAN+CAN)
        GObject.source_remove(self.in_source)
        GObject.source_remove(self.timeout_source)
        FileTransfer.do_close(self, widget, response)
        Gtk.main_quit()


senders = {
    "xmodem":XModemSender,
    "ymodem":YModemSender,
}

receivers = {
    "xmodem":XModemReceiver,
}

