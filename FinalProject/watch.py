from ast import arg, arguments
from sqlite3 import connect
from time import sleep
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QProcess, QTimer, QObject, QThread
from PyQt5.QtWidgets import QMainWindow, QApplication
from PyQt5.QtChart import QChartView
import sys

from click import command


class WatchProcessControl(QObject):
    # for comminucation with UI
    resultReady = QtCore.pyqtSignal(dict) # 4 time, 1 num page
    
    # for inner use
    startReadProcessStat = QtCore.pyqtSignal()

    def __init__(self, watchInterval:int, parent=None):
        super(WatchProcessControl, self).__init__(parent)
        
        self.pid = None
        self.watchInterval = watchInterval # in ms
        self.processRunning = False
        self.timer = None
        self.testbenchProcess = None
        
        # connect 
        self.startReadProcessStat.connect(self.start_watch)

        
    def start_testbench(self, command: str, arguments: list):
        self.testbenchProcess = QProcess()
        self.testbenchProcess.start(command, arguments)
        self.testbenchProcess.finished.connect(self.stop_watch)

        # self.pid = self.testbenchProcess.processId()
        print("DEBUG: ", self.testbenchProcess.processId())
        
        echoProcProcess = QProcess()
        echoProcProcess.setStandardOutputFile('/proc/watch')
        echoProcProcess.start('echo',[str(self.testbenchProcess.processId())])
        # echoProcProcess.start('echo',['1'])
        echoProcProcess.waitForFinished()
        
        print("DEBUG: `echo` finished")
        # emit signal
        self.startReadProcessStat.emit()


    def read_process_stat(self):
        '''read /proc/watch'''
        print("LOG: read process stat")
        readStatProcess = QProcess(self)
        readStatProcess.start('cat', ['/proc/watch'])
        readStatProcess.waitForFinished()
        try:
            res = eval(str(readStatProcess.readAll()))
            self.resultReady.emit(res)
            print(res)
        except:
            print("ERROR: Kernel Module Error")
            print(readStatProcess.readAll())
        

    def start_watch(self):
        print("LOG: start watching")
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.read_process_stat)
        self.timer.start(self.watchInterval)


    def stop_watch(self):
        print("LOG: stop watching")
        QTimer.killTimer(self.timer, self.timer.timerId())
        self.pid = None

class WatchUI(QtWidgets.QWidget):
    startTestbench = QtCore.pyqtSignal(str, list)
    def __init__(self, parent=None):
        super(WatchUI, self).__init__(parent)     

        self.testbenchThread = QThread(self)

        # UI  
        self.resize(800, 500)
        self.setWindowTitle('CPUWatch')
        
        # layer 0
        self.vlayout0 = QtWidgets.QVBoxLayout(self)
        # layer 1
        self.hlayout1_0 = QtWidgets.QHBoxLayout()
        self.hlayout1_1 = QtWidgets.QHBoxLayout()
        self.vlayout0.addLayout(self.hlayout1_0)
        self.vlayout0.addLayout(self.hlayout1_1)

        # layer 2
        self.vlayout2_0 = QtWidgets.QVBoxLayout()
        self.runButton = QtWidgets.QPushButton('RUN',self)
        self.hlayout1_0.addLayout(self.vlayout2_0)
        self.hlayout1_0.addWidget(self.runButton)

        self.flayout2_1 = QtWidgets.QFormLayout()
        self.vlayout2_2 = QtWidgets.QVBoxLayout()
        self.hlayout1_1.addLayout(self.flayout2_1)
        self.hlayout1_1.addLayout(self.vlayout2_2)
        
        # layer 3
        self.inputCommandLabel = QtWidgets.QLabel('Testbench Command (Shell):', self)
        self.inputCommandLineEdit = QtWidgets.QLineEdit(self)
        self.testIntervalLabel = QtWidgets.QLabel('Test interval (s):', self)
        self.testIntervalLineEdit = QtWidgets.QLineEdit(self)
        self.vlayout2_0.addWidget(self.inputCommandLabel)
        self.vlayout2_0.addWidget(self.inputCommandLineEdit)
        self.vlayout2_0.addWidget(self.testIntervalLabel)
        self.vlayout2_0.addWidget(self.testIntervalLineEdit)
        
        self.pidLabel = QtWidgets.QLabel("Pid:", self)
        self.pidLineEdit  =QtWidgets.QLineEdit(self)
        self.utimeLabel = QtWidgets.QLabel("Usert time:", self)
        self.utimeLineEdit = QtWidgets.QLineEdit(self)
        self.stimeLabel = QtWidgets.QLabel("Kernel time:", self)
        self.stimeLineEdit = QtWidgets.QLineEdit(self)
        self.cpuLabel = QtWidgets.QLabel("CPU Usage(%):", self)
        self.cpuLineEdit = QtWidgets.QLineEdit(self)
        self.memoryLabel = QtWidgets.QLabel("Memory usage", self)
        self.memoryLineEdit = QtWidgets.QLineEdit(self)
        self.typeLabel = QtWidgets.QLabel("Type:", self)
        self.typeLineEdit = QtWidgets.QLineEdit(self)
        self.flayout2_1.addRow(self.pidLabel, self.pidLineEdit)
        self.flayout2_1.addRow(self.utimeLabel, self.utimeLineEdit)
        self.flayout2_1.addRow(self.stimeLabel, self.stimeLineEdit)
        self.flayout2_1.addRow(self.cpuLabel, self.cpuLineEdit)
        self.flayout2_1.addRow(self.memoryLabel, self.memoryLineEdit)
        self.flayout2_1.addRow(self.typeLabel, self.typeLineEdit)

        self.charView = QChartView(self)
        self.showButton = QtWidgets.QPushButton('SHOW', self)
        self.vlayout2_2.addWidget(self.charView)
        self.vlayout2_2.addWidget(self.showButton)

        self.runButton.clicked.connect(self.start_testbench)
    # slot
    def start_testbench(self):
        # parse command
        command, arguments, watchInterval = self.tool_parse_command()

        # start a new thread to run testbench and watching
        watchProcessControl = WatchProcessControl(watchInterval, self)
        watchProcessControl.moveToThread(self.testbenchThread)

        self.testbenchThread.finished.connect(watchProcessControl.deleteLater)
        self.startTestbench.connect(watchProcessControl.start_testbench)
        watchProcessControl.resultReady.connect(self.update_stat)
        print(type(arguments))
        self.startTestbench.emit(command, arguments)

    def update_stat(self, info: dict):
        pass

    def tool_parse_command(self):
        content = self.inputCommandLineEdit.text()
        try:
            watchInterval = int(self.testIntervalLineEdit.text())
            command = content.split()[0]
            arguments = content.split()[1:]
            return command, arguments, watchInterval
        except:
            print("ERROR: command error!")




if __name__ == '__main__':
    app = QApplication(sys.argv)
    # mainWindow = WatchUI()
    # mainWindow.show()
    watchProcessControl  = WatchProcessControl(1000)
    watchProcessControl.start_testbench('sysbench', ['memory', 'run'])

    # testProcess = QProcess(app)
    # testProcess.setStandardOutputFile('/proc/watch')
    # testProcess.start('echo', ['1'])
    # testProcess.waitForFinished()
    
    sys.exit(app.exec_())
    