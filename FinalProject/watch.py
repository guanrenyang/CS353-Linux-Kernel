from ast import arguments
from logging import exception
from time import sleep
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QProcess, QTimer, QObject, QThread, Qt
from PyQt5.QtWidgets import QMainWindow, QApplication, QSizePolicy, QDockWidget
from PyQt5.QtChart import QChartView
from PyQt5.QtGui import QPixmap
import sys
import pyqtgraph
import csv
import time

NANO2MILLI = 1000000
MILLI2SECOND = 1000
MILLI2JEFFIES = 10
class CPUWatchWorker(QObject):
    # for comminucation with other classes
    signal_resultReady = QtCore.pyqtSignal(dict) # 4 time, 1 num page
    signal_cputimeReady = QtCore.pyqtSignal(float, float, float)
    signal_stopWatch = QtCore.pyqtSignal()
    # for inner use
    signal_startReadStat = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(CPUWatchWorker, self).__init__(parent)
        
        self.pid = None
        self.watchInterval = None # in ms
        self.timer = None
        self.testbenchProcess = None

        # last utime and stime from /proc/watch are recorded in kernel module
        
        self.lastUserCputime: float = -1 # ms
        self.lastKernelCputime: float = -1
        self.lastTotalCputime: float = -1

        self.lastUtimeStat: float = -1
        self.lastStimeStat: float = -1        
        
    def start_testbench(self, command: str, arguments: list, watchInterval: int):
        self.watchInterval = watchInterval

        self.testbenchProcess = QProcess()
        self.testbenchProcess.start(command, arguments)
        self.testbenchProcess.finished.connect(self.stop_watch)

        # self.pid = self.testbenchProcess.processId()
        print("DEBUG: ", self.testbenchProcess.processId())
        
        # write in /proc/watch
        echoProcProcess = QProcess()
        echoProcProcess.setStandardOutputFile('/proc/watch')
        echoProcProcess.start('echo',[str(self.testbenchProcess.processId())])
        echoProcProcess.waitForFinished()
        print("DEBUG: `echo` finished")

        # get base cputime
        self.lastUserCputime, self.lastKernelCputime, self.lastTotalCputime = self.get_cputime()

        # get base utime and stime from /proc/pid/stat
        self.lastUtimeStat, self.lastStimeStat = self.read_proc_pid_stat()

        print("DEBUG: update_cputime finished")
        # emit signal
        self.signal_startReadStat.emit()


    def read_stat(self):
        '''read /proc/watch'''
        try:
            # read /proc/watch
            print("LOG: read process stat")
            readWatchProcess = QProcess()
            readWatchProcess.start('cat', ['/proc/watch'])
            readWatchProcess.waitForFinished()
            
            resDict = eval(str(readWatchProcess.readAll(), encoding='utf-8'))# when testbench process is not ready, this clause may throw SyntaxError
            
            # read /proc/pid/stat
            utimeStat, stimeStat = self.read_proc_pid_stat()           
            resDict['utimeProcPidStat'] = utimeStat - self.lastUtimeStat
            resDict['stimeProcPidStat'] = stimeStat - self.lastStimeStat
            self.lastUtimeStat = utimeStat
            self.lastStimeStat = stimeStat

            # get and update cputime
            userCputime, kernelCputime, totalCputime = self.get_cputime()
            resDict['userCputime'] = userCputime - self.lastUserCputime
            resDict['kernelCputime'] = kernelCputime - self.lastKernelCputime
            resDict['totalCputime'] = totalCputime - self.lastTotalCputime
            self.lastUserCputime, self.lastKernelCputime, self.lastTotalCputime = userCputime, kernelCputime, totalCputime

            self.signal_resultReady.emit(resDict)
        except exception as ex:
            if ex==SyntaxError:
                print("DEBUG: Read nothing from /proc")
            else:
                print(ex)

    def get_cputime(self):
        cputimeProcess = QProcess()
        cputimeProcess.start('cat', ['/proc/stat'])
        cputimeProcess.waitForFinished()
        userCputime, kernelCputime, totalCputime = self.tool_parse_cputime(str(cputimeProcess.readAll(), encoding='utf-8')) # time in ms
        return userCputime, kernelCputime, totalCputime
    
    def read_proc_pid_stat(self):
        if self.testbenchProcess is not None:
            stat_file = open('/proc/{pid}/stat'.format(pid=self.testbenchProcess.processId()))
            stat_content = stat_file.read().split()
            utime = (float(stat_content[13])+float(stat_content[15]))*MILLI2JEFFIES
            stime = (float(stat_content[14])+float(stat_content[16]))*MILLI2JEFFIES
            return utime, stime
        return 0, 0
            
    def stop_watch(self):
        self.pid = None
        self.watchInterval = None # in ms
        self.timer = None
        self.testbenchProcess = None
        
        self.lastUserCputime = -1 # ms
        self.lastKernelCputime = -1
        self.lastTotalCputime = -1

        self.signal_stopWatch.emit()

    def tool_parse_cputime(self, content: str):
        line = content.splitlines()[0]
        
        cpuInfoList = line.split()
        # print(cpuInfoList)
        userCputime = float(cpuInfoList[1]) 
        kernelCputime = float(cpuInfoList[3])
        totalCputime = (userCputime+kernelCputime)
        
        return userCputime*MILLI2JEFFIES, kernelCputime*MILLI2JEFFIES, totalCputime*MILLI2JEFFIES

class CPUWatchController(QObject):
    signal_startWatch = QtCore.pyqtSignal(str, list, int)
    signal_resultReady = QtCore.pyqtSignal(dict)
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
        
    def handleResult(self, result: dict):
        self.timer.start(self.watchInterval)
        self.signal_resultReady.emit(result)
        
    def start_watch(self):
        print("LOG: start watching")
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.worker.read_stat)
        self.timer.start(self.watchInterval)
    def stop_watch(self):
        print("LOG: stop watching")
        if self.timer is not None:
            QTimer.killTimer(self.timer, self.timer.timerId())

    def __del__(self):
        self.workerThread.wait()
        self.workerThread.quit()

class WatchUI(QtWidgets.QWidget):
    startTestbench = QtCore.pyqtSignal(str, list)
    def __init__(self, parent=None):
        super(WatchUI, self).__init__(parent)     

        self.watchController = None

        # statistics
        self.pid: int = None
        self.utimeList: list = [] # ms
        self.utimeStatList: list = []
        self.stimeList: list = [] # ms
        self.stimeStatList: list = []
        # self.totalTimeList: list = []
        self.cpuUsageList: list = []
        self.memoryUsageList: list = []
        self.watchTimeList: list = [] # ms
        self.mem2compList: list = []
        self.type: str = None
        self.watchInterval = None

        self.csvFileName = 'statistics_{arguments}.csv'
        self.filenameArguments = None
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
        self.runButton.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.hlayout1_0.addLayout(self.vlayout2_0)
        self.hlayout1_0.addWidget(self.runButton)

        self.flayout2_1 = QtWidgets.QFormLayout()
        self.vlayout2_2 = QtWidgets.QVBoxLayout()
        self.hlayout1_1.addLayout(self.flayout2_1)
        self.hlayout1_1.addLayout(self.vlayout2_2)
        
        # layer 3
        self.inputCommandLabel = QtWidgets.QLabel('Testbench Command (Shell):', self)
        self.inputCommandLineEdit = QtWidgets.QLineEdit(self)
        self.inputCommandLineEdit.setText('sysbench cpu --time=100 --threads=1 run')
        self.testIntervalLabel = QtWidgets.QLabel('Test interval (ms):', self)
        self.testIntervalLineEdit = QtWidgets.QLineEdit(self)
        self.testIntervalLineEdit.setText('10')
        self.vlayout2_0.addWidget(self.inputCommandLabel)
        self.vlayout2_0.addWidget(self.inputCommandLineEdit)
        self.vlayout2_0.addWidget(self.testIntervalLabel)
        self.vlayout2_0.addWidget(self.testIntervalLineEdit)
        
        self.pidLabel = QtWidgets.QLabel("Pid:", self)
        self.pidLineEdit  =QtWidgets.QLineEdit(self)
        self.pidLineEdit.setFocusPolicy(Qt.NoFocus)
        self.cpuTimeLabel = QtWidgets.QLabel("CPU time:", self)
        self.cpuTimeLineEdit = QtWidgets.QLineEdit(self)
        self.cpuTimeLineEdit.setFocusPolicy(Qt.NoFocus)
        self.utimeLabel = QtWidgets.QLabel("User time (ms):", self)
        self.utimeLineEdit = QtWidgets.QLineEdit(self)
        self.utimeLineEdit.setFocusPolicy(Qt.NoFocus)
        self.utimeStatLabel = QtWidgets.QLabel("User time /proc/pid/stat (ms):", self)
        self.utimeStatLineEdit = QtWidgets.QLineEdit(self)
        self.utimeStatLineEdit.setFocusPolicy(Qt.NoFocus)
        self.stimeLabel = QtWidgets.QLabel("Kernel time (ms):", self)
        self.stimeLineEdit = QtWidgets.QLineEdit(self)
        self.stimeLineEdit.setFocusPolicy(Qt.NoFocus)
        self.stimeStatLabel = QtWidgets.QLabel("Kernel time /proc/pid/stat (ms):", self)
        self.stimeStatLineEdit = QtWidgets.QLineEdit(self)
        self.stimeStatLineEdit.setFocusPolicy(Qt.NoFocus)
        self.cpuLabel = QtWidgets.QLabel("CPU Usage(%):", self)
        self.cpuLineEdit = QtWidgets.QLineEdit(self)
        self.cpuLineEdit.setFocusPolicy(Qt.NoFocus)
        self.memoryLabel = QtWidgets.QLabel("Memory usage (Num of pages)", self)
        self.memoryLineEdit = QtWidgets.QLineEdit(self)
        self.memoryLineEdit.setFocusPolicy(Qt.NoFocus)
        self.mem2compLabel = QtWidgets.QLabel("Pages/Second(User Mode):", self)
        self.mem2compLineEdit = QtWidgets.QLineEdit(self)
        self.mem2compLineEdit.setFocusPolicy(Qt.NoFocus)
        self.typeLabel = QtWidgets.QLabel("Type:", self)
        self.typeLineEdit = QtWidgets.QLineEdit(self)
        self.typeLineEdit.setFocusPolicy(Qt.NoFocus)
        self.exportCSVButton = QtWidgets.QPushButton("Export to csv", self)
        self.logoLabel = QtWidgets.QLabel(self)
        self.logoLabel.setPixmap(QPixmap('./LOGO.png').scaled(350,300, Qt.KeepAspectRatio, Qt.SmoothTransformation))# 图片路径

        self.flayout2_1.addRow(self.pidLabel, self.pidLineEdit)
        self.flayout2_1.addRow(self.cpuTimeLabel, self.cpuTimeLineEdit)
        self.flayout2_1.addRow(self.utimeLabel, self.utimeLineEdit)
        self.flayout2_1.addRow(self.utimeStatLabel, self.utimeStatLineEdit)
        self.flayout2_1.addRow(self.stimeLabel, self.stimeLineEdit)
        self.flayout2_1.addRow(self.stimeStatLabel, self.stimeStatLineEdit)
        self.flayout2_1.addRow(self.cpuLabel, self.cpuLineEdit)
        self.flayout2_1.addRow(self.memoryLabel, self.memoryLineEdit)
        self.flayout2_1.addRow(self.mem2compLabel, self.mem2compLineEdit)
        self.flayout2_1.addRow(self.typeLabel, self.typeLineEdit)
        self.flayout2_1.addRow(self.exportCSVButton)
        self.flayout2_1.addRow(self.logoLabel)
        self.flayout2_1.addRow
        self.lineChart = pyqtgraph.PlotWidget(self)
        self.lineChart.setBackground('w')
        self.plotChartLabel = QtWidgets.QLabel("Choose an attribute to plot:")
        self.hlayout3_0 = QtWidgets.QHBoxLayout()
        self.vlayout2_2.addWidget(self.lineChart)
        self.vlayout2_2.addWidget(self.plotChartLabel)
        self.vlayout2_2.addLayout(self.hlayout3_0)

        # layer 4
        self.plotRunTimeButton = QtWidgets.QPushButton("User Mode Time", self)
        self.plotCPUUsageButton = QtWidgets.QPushButton("CPU Usage Ratio", self)
        self.plotMemoryUsageButton = QtWidgets.QPushButton("Memory Usage", self)
        self.plotmem2compButton = QtWidgets.QPushButton("Pages/S", self)
        self.hlayout3_0.addWidget(self.plotRunTimeButton)
        self.hlayout3_0.addWidget(self.plotCPUUsageButton)
        self.hlayout3_0.addWidget(self.plotMemoryUsageButton)
        self.hlayout3_0.addWidget(self.plotmem2compButton)
        
        self.plotRunTimeButton.clicked.connect(lambda: self.plot_line_chart(self.watchTimeList, self.utimeList, 'User Mode Time', 'Execution Time in User Mode (ms)'))
        self.plotCPUUsageButton.clicked.connect(lambda: self.plot_line_chart(self.watchTimeList, self.cpuUsageList, 'CPU Usage Ratio', 'CPU Usage Ratio (%)'))
        self.plotMemoryUsageButton.clicked.connect(lambda: self.plot_line_chart(self.watchTimeList, self.memoryUsageList, 'Memory Usage', 'Number of accessed pages'))
        self.plotmem2compButton.clicked.connect(lambda:self.plot_line_chart(self.watchTimeList, self.mem2compList, 'Number of accessed pages per second in user mode', 'Number of accessed pages per second in user mode (/s'))
        
        self.runButton.clicked.connect(self.start_testbench)

        self.exportCSVButton.clicked.connect(self.to_csv)
    # slot
    def start_testbench(self):

        # clear statistics
        self.pid = None
        self.utimeList = [] # ms
        self.utimeStatList = []
        self.stimeList = [] # ms
        self.stimeStatList = []
        self.cputimeList = []
        self.cpuUsageList = []
        self.memoryUsageList = []
        self.watchTimeList = [] # ms
        self.mem2compList = []
        self.type = None
        self.watchInterval = None
        
        # parse command
        command, arguments, watchInterval = self.tool_parse_command()
        
        self.filenameArguments = '_'.join(arguments)

        # start a new thread to run testbench and watching
        # watchProcessControl = CPUWatchWorker(watchInterval, self)
        # watchProcessControl.moveToThread(self.testbenchThread)
        self.watchInterval = watchInterval
        self.watchController = CPUWatchController(self)
        self.watchController.start(command, arguments, watchInterval)        
        self.watchController.signal_resultReady.connect(self.update_stat)

    def update_stat(self, info_dict: dict):
        
        print(info_dict)
        self.pid = info_dict['pid']

        utime = round((info_dict['utime']+info_dict['cutime'])/NANO2MILLI, 1)
        utimeStat = info_dict['utimeProcPidStat']
        stime = round((info_dict['stime']+info_dict['cstime'])/NANO2MILLI, 1)
        stimeStat = info_dict['stimeProcPidStat']
        cpuTime = float(info_dict['userCputime']) # cputime in this interval, ms, total means user+kernel
        cpuUsage = self.tool_demical_to_fraction(utime/cpuTime) # %
        memoryUsage = info_dict['num_accessed_page']
        watchTime = sum(self.watchTimeList)+self.watchInterval
        numPagePerS = round(memoryUsage/(utime/MILLI2SECOND), 2)

        self.utimeList.append(utime)
        self.utimeStatList.append(utimeStat)
        self.stimeList.append(stime)
        self.stimeStatList.append(stimeStat)
        self.cputimeList.append(cpuTime)
        self.watchTimeList.append(watchTime)
        self.cpuUsageList.append(cpuUsage)
        self.memoryUsageList.append(memoryUsage)
        self.mem2compList.append(numPagePerS)

        '''update UI'''
        self.update_stat_UI(self.pid, cpuTime, utime, utimeStat, stime, stimeStat, cpuUsage, memoryUsage, numPagePerS)
        

    def update_stat_UI(self, pid, cpuTime, utime, utimeStat, stime, stimeStat, cpuUsage, memoryUsage, mem2comp=None, type=None):
        if pid is not None:
            self.pidLineEdit.setText(str(pid))
        if cpuTime is not None:
            self.cpuTimeLineEdit.setText(str(cpuTime))
        if utime is not None:
            self.utimeLineEdit.setText(str(utime))
        if utimeStat is not None:
            self.utimeStatLineEdit.setText(str(utimeStat))
        if stime is not None:
            self.stimeLineEdit.setText(str(stime))
        if stimeStat is not None:
            self.stimeStatLineEdit.setText(str(stimeStat))
        if cpuUsage is not None:
            self.cpuLineEdit.setText(str(cpuUsage))
        if memoryUsage is not None:
            self.memoryLineEdit.setText(str(memoryUsage))
        if mem2comp is not None:
            self.mem2compLineEdit.setText(str(mem2comp))
        if type is not None:
            self.typeLineEdit.setText(str(type))

    def plot_line_chart(self, xData:list, yData:list, title:str, yLabel:str):
        self.lineChart.clear()
        self.lineChart.addLegend()
        # drop the first data
        if len(xData)>1:
            xData = xData[1:] 
        if len(yData)>1:
            yData = yData[1:]
        xData = list(range(1, len(yData)+1))
        print(yData)
        labelStyles = {'color':'black', 'font-size':'15px'}
        self.lineChart.setTitle(title, **{'color':'black', 'font-size':'20px'})
        self.lineChart.setLabel('left', yLabel, **labelStyles)
        self.lineChart.setLabel('bottom', 'Watch Point', **labelStyles)
    
        self.lineChart.plot(xData, yData, pen=(1,1))
        

    def tool_parse_command(self):
        content = self.inputCommandLineEdit.text()
        try:
            watchInterval = int(self.testIntervalLineEdit.text())
            command = content.split()[0]
            arguments = content.split()[1:]
            return command, arguments, watchInterval
        except:
            print("ERROR: command error!")
    def to_csv(self):
        with open(self.csvFileName.format(arguments=self.filenameArguments), 'w') as file:
            writer = csv.writer(file)
            writer.writerow(['watchPoint']+list(range(1, len(self.watchTimeList)+1)))
            writer.writerow(['cpuTime']+self.watchTimeList)
            writer.writerow(['userModeTime']+self.utimeList)
            writer.writerow(['userModeTimeStat']+self.utimeStatList)
            writer.writerow(['cpuUsage']+self.cpuUsageList)
            writer.writerow(['memoryUsage']+self.memoryUsageList)
            writer.writerow(['PagesPerSecond']+self.mem2compList)

    def tool_demical_to_fraction(self, origin:float):
        return round(origin*100, 2)

    def __del__(self):
        if self.watchController is not None:
            self.watchController.deleteLater()
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
        echoProcess.start('echo', [str(testbenchProcess.processId(), encoding='utf-8')])
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
    sys.exit(app.exec_())
    