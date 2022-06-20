from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QProcess, QTimer, QObject
from PyQt5.QtWidgets import QMainWindow, QApplication
from PyQt5.QtChart import QChartView
import sys


class WatchProcessControl(QObject):
    # for comminucation with UI
    resultReady = QtCore.pyqtSignal(dict) # 4 time, 1 num page
    
    # for inner use
    startReadProcessStat = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(WatchProcessControl, self).__init__(parent)
        
        self.pid = None
        self.watchPeriod = 1000 # in ms
        self.processRunning = False
        self.timer = None
        self.testbenchProcess = QProcess(self)
        
        # connect 
        self.startReadProcessStat.connect(self.start_watch)
        self.testbenchProcess.finished.connect(self.stop_watch)

        
    def start_testbench(self, command: str, arguments: list):

        self.testbenchProcess.start(command, arguments)
        # self.pid = self.testbenchProcess.processId()
        print("DEBUG: ", self.testbenchProcess.processId())
        
        echoProcProcess = QProcess(self)
        echoProcProcess.setStandardOutputFile('/proc/watch')
        echoProcProcess.start('echo',[str(self.testbenchProcess.processId())])
        echoProcProcess.waitForFinished()
        
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
        

    def start_watch(self):
        print("LOG: start watching")
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.read_process_stat)
        self.timer.start(self.watchPeriod)


    def stop_watch(self):
        print("LOG: stop watching")
        QTimer.killTimer(self.timer, self.timer.timerId())
        self.pid = None

class WatchUI(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(WatchUI, self).__init__(parent)        
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
        self.runButton = QtWidgets.QPushButton(self)
        self.hlayout1_0.addLayout(self.vlayout2_0)
        self.hlayout1_0.addWidget(self.runButton)

        self.flayout2_1 = QtWidgets.QFormLayout()
        self.vlayout2_2 = QtWidgets.QVBoxLayout()
        self.hlayout1_1.addLayout(self.flayout2_1)
        self.hlayout1_1.addLayout(self.vlayout2_2)
        # layer 3
        self.inputCommandLabel = QtWidgets.QLabel(self)
        self.inputCommandLineEdit = QtWidgets.QLineEdit(self)
        self.vlayout2_0.addWidget(self.inputCommandLabel)
        self.vlayout2_0.addWidget(self.inputCommandLineEdit)
        
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
        self.flayout2_1.addRow(self.utimeLabel, self.utimeLineEdit)
        self.flayout2_1.addRow(self.stimeLabel, self.stimeLineEdit)
        self.flayout2_1.addRow(self.cpuLabel, self.cpuLineEdit)
        self.flayout2_1.addRow(self.memoryLabel, self.memoryLineEdit)
        self.flayout2_1.addRow(self.typeLabel, self.typeLineEdit)

        self.charView = QChartView(self)
        self.showButton = QtWidgets.QPushButton(self)
        self.vlayout2_2.addWidget(self.charView)
        self.vlayout2_2.addWidget(self.showButton)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWindow = WatchUI()
    mainWindow.show()
    
    # watchProcessControl  = WatchProcessControl()
    # watchProcessControl.start_testbench('sysbench', ['memory', 'run'])

    # testProcess = QProcess(app)
    # testProcess.setStandardOutputFile('/proc/watch')
    # testProcess.start('echo', ['1'])
    # testProcess.waitForFinished()
    # print(eval(str(readStatProcess.readAll(), 'utf-8')))
    sys.exit(app.exec_())
    