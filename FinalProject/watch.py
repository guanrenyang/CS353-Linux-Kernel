from time import sleep
from PyQt5 import QtCore

COMMAND = 'sysbench'
ARGUMENTS = ['memory', 'run']
if __name__ == '__main__':
    process = QtCore.QProcess()
    process.start(COMMAND, ARGUMENTS)
    process.waitForFinished(15000)
    print(str(process.readAll(), encoding='u8'))


