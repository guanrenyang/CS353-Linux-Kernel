
from re import S
from select import select
from signal import signal
from time import sleep
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QProcess, QTimer, QObject, QThread
from PyQt5.QtWidgets import QMainWindow, QApplication
from PyQt5.QtChart import QChartView
import sys

from click import command
from yaml import emit


class CPUWatchWorker(QObject):
    # for comminucation with other classes
    signal_resultReady = QtCore.pyqtSignal(str) # 4 time, 1 num page
    signal_stopWatch = QtCore.pyqtSignal()
    # for inner use
    signal_startReadStat = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(CPUWatchWorker, self).__init__(parent)
        
        self.pid = None
        self.watchInterval = None # in ms
        self.timer = None
        self.testbenchProcess = None
        
        # # connect 
        # self.signal_startReadStat.connect(self.start_watch)
        
    def start_testbench(self, command: str, arguments: list, watchInterval: int):
        self.watchInterval = watchInterval

        self.testbenchProcess = QProcess()
        self.testbenchProcess.start(command, arguments)
        self.testbenchProcess.finished.connect(self.stop_watch)

        # self.pid = self.testbenchProcess.processId()
        print("DEBUG: ", self.testbenchProcess.processId())
        
        echoProcProcess = QProcess()
        echoProcProcess.setStandardOutputFile('/proc/watch')
        echoProcProcess.start('echo',[str(self.testbenchProcess.processId())])
        echoProcProcess.waitForFinished()
        
        print("DEBUG: `echo` finished")
        # emit signal
        self.signal_startReadStat.emit()


    def read_stat(self):
        '''read /proc/watch'''
        print("LOG: read process stat")
        readStatProcess = QProcess()
        readStatProcess.start('cat', ['/proc/watch'])
        readStatProcess.waitForFinished()
        try:
            res = str(readStatProcess.readAll())
            self.signal_resultReady.emit(res)
        except:
            print("ERROR: Kernel Module Error")

    def stop_watch(self):
        self.signal_stopWatch.emit()

class CPUWatchController(QObject):
    signal_startWatch = QtCore.pyqtSignal(str, list, int)
    signal_resultReady = QtCore.pyqtSignal(str)
    def __init__(self, parent = None):
        super(CPUWatchController, self).__init__(parent)
        
        self.timer = None
        self.watchInterval = None
        self.worker = CPUWatchWorker()
        self.workerThread = QThread()
        self.worker.moveToThread(self.workerThread)

        self.workerThread.finished.connect(self.deleteLater)
        self.signal_startWatch.connect(self.worker.start_testbench)
        self.worker.signal_resultReady.connect(self.handleResult)
        self.worker.signal_startReadStat.connect(self.start_watch)
        self.worker.signal_stopWatch.connect(self.stop_watch)

        self.workerThread.start()

    def start(self, command:str, arguments:list, watchInterval:int):
        self.watchInterval = watchInterval
        self.signal_startWatch.emit(command, arguments, watchInterval)
        
    def handleResult(self, result: str):
        self.timer.start(self.watchInterval)
        self.signal_resultReady.emit(result)
        
    def start_watch(self):
        print("LOG: start watching")
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.worker.read_stat)
        self.timer.start(self.watchInterval)
    def stop_watch(self):
        print("LOG: stop watching")
        QTimer.killTimer(self.timer, self.timer.timerId())

    def __del__(self):
        self.workerThread.wait()
        self.workerThread.quit()

class WatchUI(QtWidgets.QWidget):
    startTestbench = QtCore.pyqtSignal(str, list)
    def __init__(self, parent=None):
        super(WatchUI, self).__init__(parent)     

        self.watchController = None

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
        # watchProcessControl = CPUWatchWorker(watchInterval, self)
        # watchProcessControl.moveToThread(self.testbenchThread)
        self.watchController = CPUWatchController(self)
        self.watchController.start(command, arguments, watchInterval)

        self.watchController.signal_resultReady.connect(self.update_stat)

    def update_stat(self, info: str):
        print(info)

    def tool_parse_command(self):
        content = self.inputCommandLineEdit.text()
        try:
            watchInterval = int(self.testIntervalLineEdit.text())
            command = content.split()[0]
            arguments = content.split()[1:]
            return command, arguments, watchInterval
        except:
            print("ERROR: command error!")

''''''
class Worker(QObject):
    resultReady = QtCore.pyqtSignal(str)
    def __init__(self, parent=None):
        super(Worker, self).__init__(parent)
    def do_work(self):
        self.resultReady.emit('do work')

        testbenchProcess = QProcess()
        testbenchProcess.start('sysbench', ['memory', 'run'])
        testbenchProcess.waitForStarted()

        echoProcess = QProcess()
        echoProcess.setStandardOutputFile('/proc/watch')
        echoProcess.start('echo', [str(testbenchProcess.processId())])
        echoProcess.waitForFinished()

        for s in range(10):
            readProcess = QProcess()
            readProcess.start('cat', ['/proc/watch'])
            readProcess.waitForFinished()
            # print(readProcess.readAll())
            self.resultReady.emit(str(readProcess.readAll()))
            sleep(1)
        testbenchProcess.waitForFinished

class Controller(QObject):
    operate = QtCore.pyqtSignal()
    def __init__(self, parent=None):
        super(Controller, self).__init__(parent)
        self.workerThread = QThread()

        self.worker = Worker()
        self.worker.moveToThread(self.workerThread)

        self.workerThread.finished.connect(self.threadOK)
        self.operate.connect(self.worker.do_work)
        self.worker.resultReady.connect(self.result)

        self.workerThread.start()

    def emit(self):
        self.operate.emit()
    def result(self, s):
        print(s)
    def threadOK(self):
        self.workerThread.wait()
        self.workerThread.quit()
    def display(self):
        print(self.workerThread.isRunning())
if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWindow = WatchUI()
    mainWindow.show()
    # watchProcessControl  = WatchProcessControl(1000)
    # watchProcessControl.start_testbench('sysbench', ['memory', 'run'])
    # controller = Controller(app)
    # controller.emit()
    
    
    sys.exit(app.exec_())
    