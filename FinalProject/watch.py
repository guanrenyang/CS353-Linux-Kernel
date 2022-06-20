from PyQt5 import QtCore
from PyQt5.QtCore import QProcess, QTimer, QObject
from PyQt5.QtWidgets import QWidget, QApplication
import sys

def tick():
    # label.setText('Tick! The time is: %s' % datetime.now())
    print("here")
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

        
        

        
if __name__ == '__main__':
    app = QApplication(sys.argv)
    watchProcessControl  = WatchProcessControl()
    watchProcessControl.start_testbench('sysbench', ['memory', 'run'])


    # testProcess = QProcess(app)
    # testProcess.setStandardOutputFile('/proc/watch')
    # testProcess.start('echo', ['1'])
    # testProcess.waitForFinished()
    # print(eval(str(readStatProcess.readAll(), 'utf-8')))
    app.exec_()
    