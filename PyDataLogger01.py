"""
Created on Sun Apr 12 15:41:15 2015

@author: Jeong-whan
--------------------------------------------------------------
 Modified ABC-protocol: Currently for 3 channel data...
     z,devid_string,a,123.4,b,-345.345,c,3434...

"""
# Import necessary modules
import sys
import time
import logging
import serial
import Queue
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.QtNetwork import *
import numpy as np
import pyqtgraph as pg

import PyDataLogger01GUI
from signal_gen import *

PACKETS = Queue.Queue()
MSGQUE = Queue.Queue()
BUFFER_SIZE = 500
PORT = 12345
COMFLAG = False

#----------------------------------------------------------------------------------------


#----------------------------------------------------------------------------------------

class Thread(QThread):

    lock = QReadWriteLock()

    def __init__(self, socketId, parent):
        super(Thread, self).__init__(parent)
        self.socketId = socketId

    def run(self):
        global PACKETS
        socket = QTcpSocket()
        if not socket.setSocketDescriptor(self.socketId):
            self.emit(SIGNAL("error(int)"), socket.error())
            return
        #stream = QDataStream(socket)
        #stream.setVersion(QDataStream.Qt_4_2)
        packet = str()

        # socket.write("Hello!...\n\r")
        myPeerAddress = socket.peerAddress().toString()
        myPeerPort =  socket.peerPort()
        self.putGlobalStatusMsg("[%s:%d]Connected..." % (myPeerAddress, myPeerPort))

        while socket.state() == QAbstractSocket.ConnectedState:
            if socket.waitForReadyRead() and socket.bytesAvailable() > 0:
                packet = socket.readLineData(100)
            else:
                self.sendError(socket, "Cannot read client request")
                break
            #  Echo test....
            #self.sendReply(socket, packet)
            #socket.write(packet)
            #print packet.__len__(), packet

            try:
                Thread.lock.lockForWrite()
                #  Echo test....
                self.sendReply(socket, packet)
                # PCKAETS.put_nowait((aa, bb, cc))  # Queuing as a Tuple data type...
                PACKETS.put_nowait((self.socketId, packet))
            finally:
                Thread.lock.unlock()

        self.putGlobalStatusMsg("[%s:%d]Disconnected..." % (myPeerAddress, myPeerPort))


    def sendError(self, socket, msg):
        socket.write("[Err] %s \r\n" % msg)


    def sendReply(self, socket, msg):
        #reply = QByteArray()
        #stream = QDataStream(reply, QIODevice.WriteOnly)
        #stream.setVersion(QDataStream.Qt_4_2)
        #stream.writeUInt16(0)
        #stream << msg
        #stream.device().seek(0)
        #stream.writeUInt16(reply.size() - 2)  # SIZEOF_UINT16
        socket.write(msg)

    def putGlobalStatusMsg(self,msg):
        try:
            Thread.lock.lockForWrite()
            MSGQUE.put_nowait(msg)
        finally:
            Thread.lock.unlock()

#----------------------------------------------------------------------------------------

class ComThread(QThread):

    lock = QReadWriteLock()

    def __init__(self, port, baud, parent):
        super(ComThread, self).__init__(parent)
        self.port = port
        self.baud = baud
        self.serial = serial.Serial()
        # Get a Serial instance and configure/open it later:
        # port=None, baudrate=9600, bytesize=EIGHTBITS, parity=PARITY_NONE, stopbits=STOPBITS_ONE,
        # timeout=None, xonxoff=False, rtscts=False, writeTimeout=None, dsrdtr=False, interCharTimeout=None

    def run(self):
        global COMFLAG
        self.serial.port = self.port
        self.serial.baudrate = self.baud
        try:
            self.serial.open()
        except serial.SerialException:
            COMFLAG = False
        self.serial.flushInput()
        text = str("")

        while COMFLAG:
            ch = self.serial.read(1)
            text += str(ch)
            if ch == '\r':
                try:
                    Thread.lock.lockForWrite()
                    PACKETS.put_nowait((0, text))   # previous socketID legacy...
                finally:
                    Thread.lock.unlock()
                    text = str("")

        self.serial.close()



#----------------------------------------------------------------------------------------

class TcpServer(QTcpServer):

    def __init__(self, parent=None):
        super(TcpServer, self).__init__(parent)

    def incomingConnection(self, socketId):
        thread = Thread(socketId, self)
        self.connect(thread, SIGNAL("finished()"), thread, SLOT("deleteLater()"))
        thread.start()


#----------------------------------------------------------------------------------------


class MyMainWindow(QMainWindow, PyDataLogger01GUI.Ui_MainWindow):
    # Constructor function
    def __init__(self, parent=None):
        super(MyMainWindow, self).__init__(parent)
        self.setupUi(self)
        self.statusMsg("Ready for Temporary Mission ^_^;;")

        self.dataView.setTitle('Sampled Signals graph...')
        self.dataView.setLabel('left', 'Value', units='V')
        self.dataView.setLabel('bottom', 'Time', units='sec')
        self.dataView.showGrid(True, True)      # showGrid(x=None, y=None, alpha=None)
        #self.dataView.setXRange(0, 2)
        #self.dataView.setYRange(0, 1e-10)
        self.plotdata = self.dataView.plot()
        self.plotdata2 = self.dataView.plot()
        self.plotdata3 = self.dataView.plot()
        #self.plotdata.setPen((200, 10, 10))
        self.plotdata.setPen('r')
        self.plotdata2.setPen('g')
        self.plotdata3.setPen('b')

        self.yd1 = np.zeros(BUFFER_SIZE)
        self.yd2 = np.zeros(BUFFER_SIZE)
        self.yd3 = np.zeros(BUFFER_SIZE)

        self.plotdata.setData(self.yd1)
        self.plotdata2.setData(self.yd2 + 1)
        self.plotdata3.setData(self.yd3 + 2)

        self.actionAbout.triggered.connect(self.aboutHelp)
        self.actionExit.triggered.connect(qApp.quit)

        self.connect(self.lineEditCMD, SIGNAL("returnPressed()"), self.updateTerm)
        self.connect(self.btnClear, SIGNAL("clicked()"), self.textEditTerminal.clear)
        self.connect(self.btnRescan, SIGNAL("clicked()"), self.serialportScan)
        self.connect(self.btnSerialStart, SIGNAL("clicked()"), self.serialStart)
        self.btnPlot.clicked.connect(self.changePlotFlag)

        self.t = QTimer()
        self.t.timeout.connect(self.updateData)
        self.t.start(50)

        self.plotFlag = False
        self.serialFlag = False
        self.comthread = None
        self.sg1 = SignalGen(5)
        self.sg2 = SignalGen(3)
        self.sg3 = SignalGen(7)

        self.tcpServer = TcpServer(self)
        if not self.tcpServer.listen(QHostAddress("0.0.0.0"), PORT):
            QMessageBox.critical(self, "Data Logging Server",
                    "Failed to start server: %s" % (self.tcpServer.errorString()))
            self.close()
            return
        self.statusMsg("DataLogging Server(Listening)@ %s..." % PORT)
        self.lineEditCMD.setFocus()
        self.tabControl.setCurrentIndex(0)

    # Function reimplementing Key Press, Mouse Click and Resize Events
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

    def mouseDoubleClickEvent(self, event):
        self.close()

    def statusMsg(self, message):
         self.statusBar().showMessage(message)

    def terminalMsg(self, message):
        self.textEditTerminal.append(message)

    def updateData(self):
        global PACKETS

        aa, bb, cc = (0.0, 0.0, 0.0)
        val = PACKETS.qsize()
        if val != 0:
            for i in range(val):
                try:
                    Thread.lock.lockForRead()
                    (sockID, datastr) = PACKETS.get_nowait()
                    PACKETS.task_done()
                    aa, bb, cc = self.protocol_parse(datastr)
                    self.yd1[:-1] = self.yd1[1:]   # shift data in the array one sample left
                    self.yd1[-1] = aa   #self.sg1.forward()
                    self.yd2[:-1] = self.yd2[1:]
                    self.yd2[-1] = bb   #self.sg2.forward()
                    self.yd3[:-1] = self.yd3[1:]
                    self.yd3[-1] = cc   #self.sg3.forward()
                    if self.plotFlag:
                        self.plotdata.setData(self.yd1)
                        self.plotdata2.setData(self.yd2 + 1)
                        self.plotdata3.setData(self.yd3 + 2)
                    else:
                        self.terminalMsg("[%d]%s" % (sockID, datastr))
                finally:
                    Thread.lock.unlock()

        val2 = MSGQUE.qsize()
        if val2 != 0:
            self.statusMsg(self.getGlobalStatusMsg())


    def updateTerm(self):
        text = self.lineEditCMD.text()
        self.textEditTerminal.append("<font color=red> %s</font>" % text)
        self.lineEditCMD.setText('')
        self.check_keyword(text)

    def changePlotFlag(self):
        if self.plotFlag:
            self.plotFlag = False
        else:
            self.plotFlag = True

    def aboutHelp(self):
        QMessageBox.about(self,  "About Python DataLogger Terminal -KKU-BIMSRL",
                          "A Simple Data Logging Terminal Program based on PyQt4",)

    def exitFile(self):
        self.close()

    def getGlobalStatusMsg(self):
        msg = str()
        try:
            Thread.lock.lockForRead()
            msg = MSGQUE.get_nowait()
            MSGQUE.task_done()
        finally:
            Thread.lock.unlock()
        return msg


    def check_keyword(self, msg):
        #if msg.startsWith('!q'):
        #    self.close()
        pass

    def protocol_parse(self, pdata):  # pdata is str()...
        parts = pdata.split(',')
        if parts.__len__() == 6:
            a = float(parts[1])
            b = float(parts[3])
            c = float(parts[5])
        else:
            a = 0.0
            b = 0.0
            c = 0.0
        return a, b, c

    def serialportScan(self):
        global COMFLAG
        """scan for available ports. return a list of tuples (num, name)"""
        available = []      # Initialize available port list object...
        self.statusMsg("Available Serial ports Scanning.....")
        for i in range(128):
            try:
                s = serial.Serial(i)
                available.append(s.portstr)
                s.close()   # explicit close 'cause of delayed GC in java
            except serial.SerialException:
                pass
        if available.__len__() > 0:
            n = available.__len__()
            self.btnSerialStart.setEnabled(True)
            #for i in range(n):
            self.cbPorts.addItems(available)
            self.statusMsg("%d serial ports found....." % n)
        else:
            self.btnSerialStart.setEnabled(False)

    def serialStart(self):
        global COMFLAG
        if not COMFLAG:
            COMFLAG = True
            self.btnSerialStart.setText("Stop")
            self.comthread = ComThread(str(self.cbPorts.currentText()), str(self.cbBaudrate.currentText()), self)
            self.comthread.start()
        else:
            COMFLAG = False
            while self.comthread.isRunning():
                pass
            self.btnSerialStart.setText("Start")


"""
        #pg.setConfigOption('background', 'g')
        self.plot = pg.PlotWidget()  # pyqtgraph widget...
        self.plot.setTitle('Sampled Signals graph...')
        self.plot.setLabel('left', 'Value', units='V')
        self.plot.setLabel('bottom', 'Time', units='sec')
        #self.plot.setXRange(0, 2)
        #self.plot.setYRange(0, 1e-10)
        self.plotdata = self.plot.plot()
        self.plotdata.setPen((200, 200, 100))
        yd = np.random.random(1000)
        #yd, xd = self.myRand(1)
        self.plotdata.setData(yd)

    def myRand(self, n):
        data = np.random.random(n)
        data[int(n * 0.1):int(n * 0.13)] += .5
        data[int(n * 0.18)] += 2
        data[int(n * 0.1):int(n * 0.13)] *= 5
        data[int(n * 0.18)] *= 20
        data *= 1e-12
        return data, np.arange(n, n + len(data)) / float(n)

    def resizeEvent(self, event):
        self.infoLabel.setText("Window Resized to QSize(%d, %d)" % (event.size().width(), event.size().height()))
"""
#----------------------------------------------------------------------------------------


if __name__ == '__main__':
    # Exception Handling
    try:
        myApp = QApplication(sys.argv)
        myWin = MyMainWindow()
        myWin.show()
        myApp.exec_()
        sys.exit(0)
    except NameError:
        print("Name Error:", sys.exc_info()[1])
    except SystemExit:
        print("Closing Window...")
    except Exception:
        print(sys.exc_info()[1])
