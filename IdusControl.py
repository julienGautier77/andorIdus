# -*- coding: utf-8 -*-
"""
Andor IDUS camera



@author: juliengautier
version : 2021.10
"""

__author__='julien Gautier'
__version__='2022.09'


from PyQt6.QtWidgets import QApplication,QVBoxLayout,QHBoxLayout,QWidget,QPushButton,QLayout
from PyQt6.QtWidgets import QComboBox,QSlider,QLabel,QSpinBox,QToolButton,QMenu,QInputDialog,QDockWidget,QDoubleSpinBox
from pyqtgraph.Qt import QtCore
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6 import QtGui,QtCore
import sys,time
import pathlib,os
import qdarkstyle

import andorIdiusSDK2


version=str(__version__)

class CAMERA(QWidget):
    datareceived=QtCore.pyqtSignal(bool) # signal emited when receive image
    signalData=QtCore.pyqtSignal(object)
    def __init__(self,cam='Default',confFile='confCamera.ini',**kwds):
        '''
        '''
        
        
        super(CAMERA, self).__init__()
        
        p = pathlib.Path(__file__)
        self.nbcam=cam
        
        self.kwds=kwds
        if "affLight" in kwds:
            self.light=kwds["affLight"]
        else:
            self.light=True
        if "multi" in kwds:
            self.multi=kwds["multi"]
        else:
            self.multi=False 
        
        if "separate" in kwds:
            self.separate=kwds["separate"]
        else: 
            self.separate=True
            
        if "aff" in kwds: #  affi of Visu
            self.aff=kwds["aff"]
        else: 
            self.aff="right"    
        
        
        
        
        
        
        
        # self.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt6')) # qdarkstyle :  black windows style
        self.confPath=str(p.parent / confFile) # ini file path
        self.conf=QtCore.QSettings(str(p.parent / self.confPath), QtCore.QSettings.Format.IniFormat) # ini file 
        self.kwds["confpath"]=self.confPath
        sepa=os.sep
        
        self.icon=str(p.parent) + sepa+'icons'+sepa
        self.setWindowIcon(QIcon(self.icon+'LOA.png'))
        self.iconPlay=self.icon+'Play.png'
        self.iconSnap=self.icon+'Snap.png'
        self.iconStop=self.icon+'Stop.png'
        self.iconPlay=pathlib.Path(self.iconPlay)
        self.iconPlay=pathlib.PurePosixPath(self.iconPlay)
        self.iconStop=pathlib.Path(self.iconStop)
        self.iconStop=pathlib.PurePosixPath(self.iconStop)
        self.iconSnap=pathlib.Path(self.iconSnap)
        self.iconSnap=pathlib.PurePosixPath(self.iconSnap)
        self.nbShot=1
        self.isConnected=False
        self.version=str(__version__)
        
        self.openCam()
        self.setup()
        self.setCamPara()
        #self.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt6'))
    def openCam(self):
        try : 
            self.CAM=andorIdiusSDK2.ANDOR(cam=self.nbcam,conf=self.conf)
            self.isConnected=True
            print('connect')
        except :
            self.isConnected=False 
        
    def setCamPara(self):
        '''set min max gain and exp value of cam in the widget
        '''
        
        if self.isConnected==True: 
            self.CAM.SetSingleScan()
            
            # if camera is connected we address min and max value  and value to the shutter and gain box
            # print('camshutter',self.CAM.camParameter["exposureTime"])
            if self.CAM.camParameter["expMax"] >1500: # we limit exposure time at 1500ms
                self.hSliderShutter.setMaximum(1500)
                self.exposureBox.setMaximum(1500)
            else :
                self.hSliderShutter.setMaximum(self.CAM.camParameter["expMax"])
                self.exposureBox.setMaximum(self.CAM.camParameter["expMax"])
            self.hSliderShutter.setValue(int(self.CAM.camParameter["exposureTime"]))
            self.exposureBox.setValue(int(self.CAM.camParameter["exposureTime"]))
            self.hSliderShutter.setMinimum(int(self.CAM.camParameter["expMin"]+1))
            self.exposureBox.setMinimum(int(self.CAM.camParameter["expMin"]+1))
            
            self.threadTemp = ThreadTemperature(CAM=self.CAM)
            self.threadTemp.stopTemp=False
            self.threadTemp.TEMP.connect(self.update_temp)
            
            self.threadTemp.start()
            self.tempWidget=TEMPWIDGET(CAM=self.CAM)
            
            self.CAM.GetTemperature()
            print(self.CAM.temperature)
            self.actionButton()
            
        if  self.isConnected==False:
            self.setWindowTitle('Visualization         No camera connected      '   +  'v.  '+ self.version)
            self.runButton.setEnabled(False)
            self.snapButton.setEnabled(False)
            self.trigg.setEnabled(False)
            self.hSliderShutter.setEnabled(False)
            self.exposureBox.setEnabled(False)
            
            self.runButton.setStyleSheet("QToolButton:!pressed{border-image: url(%s);background-color: gray ;border-color: gray;}""QToolButton:pressed{image: url(%s);background-color: gray ;border-color: gray}"%(self.iconPlay,self.iconPlay))
            self.snapButton.setStyleSheet("QToolButton:!pressed{border-image: url(%s);background-color: gray ;border-color: gray;}""QToolButton:pressed{image: url(%s);background-color: gray ;border-color: gray}"%(self.iconSnap,self.iconSnap))
            
            
            
    def setup(self):  
        
            """ user interface definition 
            """
            # self.setWindowTitle('Visualization    '+ self.cameraType+"   " + self.ccdName+'       v.'+ self.version)
            
            
            hbox1=QHBoxLayout() # horizontal layout pour run snap stop
            self.sizebuttonMax=30
            self.sizebuttonMin=30
            self.runButton=QToolButton(self)
            self.runButton.setMaximumWidth(self.sizebuttonMax)
            self.runButton.setMinimumWidth(self.sizebuttonMax)
            self.runButton.setMaximumHeight(self.sizebuttonMax)
            self.runButton.setMinimumHeight(self.sizebuttonMax)
            self.runButton.setStyleSheet("QToolButton:!pressed{border-image: url(%s);background-color: transparent ;border-color: green;}""QToolButton:pressed{image: url(%s);background-color: gray ;border-color: gray}"% (self.iconPlay,self.iconPlay) )
            
            self.snapButton=QToolButton(self)
            self.snapButton.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
            menu=QMenu()
            #menu.addAction('acq',self.oneImage)
            menu.addAction('set nb of shot',self.nbShotAction)
            self.snapButton.setMenu(menu)
            self.snapButton.setMaximumWidth(self.sizebuttonMax)
            self.snapButton.setMinimumWidth(self.sizebuttonMax)
            self.snapButton.setMaximumHeight(self.sizebuttonMax)
            self.snapButton.setMinimumHeight(self.sizebuttonMax)
            self.snapButton.setStyleSheet("QToolButton:!pressed{border-image: url(%s);background-color: transparent ;border-color: green;}""QToolButton:pressed{image: url(%s);background-color: gray ;border-color: gray}"% (self.iconSnap,self.iconSnap) )
            
            self.stopButton=QToolButton(self)
            
            self.stopButton.setMaximumWidth(self.sizebuttonMax)
            self.stopButton.setMinimumWidth(self.sizebuttonMax)
            self.stopButton.setMaximumHeight(self.sizebuttonMax)
            self.stopButton.setMinimumHeight(self.sizebuttonMax)
            self.stopButton.setStyleSheet("QToolButton:!pressed{border-image: url(%s);background-color: gray ;border-color: gray;}""QToolButton:pressed{image: url(%s);background-color: gray ;border-color: gray}"% (self.iconStop,self.iconStop) )
            self.stopButton.setEnabled(False)
          
            
            hbox1.addWidget(self.runButton)
            hbox1.addWidget(self.snapButton)
            hbox1.addWidget(self.stopButton)
            hbox1.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
            hbox1.setContentsMargins(0, 10, 0, 10)
            self.widgetControl=QWidget(self)
            
            self.widgetControl.setLayout(hbox1)
            self.dockControl=QDockWidget(self)
            self.dockControl.setWidget(self.widgetControl)
            self.dockControl.resize(80,80)
            self.trigg=QComboBox()
            self.trigg.setMaximumWidth(80)
            self.trigg.addItem('OFF')
            self.trigg.addItem('ON')
            self.trigg.setStyleSheet('font :bold  10pt;color: white')
            self.labelTrigger=QLabel('Trigger')
            self.labelTrigger.setMaximumWidth(70)
            self.labelTrigger.setStyleSheet('font :bold  10pt')
            self.itrig=self.trigg.currentIndex()
            hbox2=QHBoxLayout()
            hbox2.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
            hbox2.setContentsMargins(5, 15, 0, 0)
            hbox2.addWidget(self.labelTrigger)
            
            hbox2.addWidget(self.trigg)
            self.widgetTrig=QWidget(self)
            
            self.widgetTrig.setLayout(hbox2)
            self.dockTrig=QDockWidget(self)
            self.dockTrig.setWidget(self.widgetTrig)
            
            self.labelExp=QLabel('Exposure (ms)')
            self.labelExp.setStyleSheet('font :bold  10pt')
            self.labelExp.setMaximumWidth(140)
            self.labelExp.setAlignment(Qt.AlignCenter)
            
            self.hSliderShutter=QSlider(Qt.Orientation.Horizontal)
            self.hSliderShutter.setMaximumWidth(80)
            self.exposureBox=QSpinBox()
            self.exposureBox.setStyleSheet('font :bold  8pt')
            self.exposureBox.setMaximumWidth(120)
            
            hboxExposure=QHBoxLayout()
            hboxExposure.setContentsMargins(5, 0, 0, 0)
            hboxExposure.setSpacing(10)
            vboxExposure=QVBoxLayout()
            vboxExposure.setSpacing(0)
            vboxExposure.addWidget(self.labelExp)#,Qt.AlignLef)
            
            hboxExposure.addWidget(self.hSliderShutter)
            hboxExposure.addWidget(self.exposureBox)
            vboxExposure.addLayout(hboxExposure)
            vboxExposure.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
            vboxExposure.setContentsMargins(5, 5, 0, 0)
            
            self.widgetExposure=QWidget(self)
            
            self.widgetExposure.setLayout(vboxExposure)
            self.dockExposure=QDockWidget(self)
            self.dockExposure.setWidget(self.widgetExposure)
            
            
            
            self.shutterBox=QComboBox()
            self.shutterBox.setMaximumWidth(90)
            self.shutterBox.addItem('Auto')
            self.shutterBox.addItem('Open')
            self.shutterBox.addItem('Close')
            self.shutterBox.setStyleSheet('font :bold  10pt;color: white')
            self.labelShutter=QLabel('Shutter')
            self.labelShutter.setMaximumWidth(70)
            self.labelShutter.setStyleSheet('font :bold  10pt')
            self.iShutter=self.shutterBox.currentIndex()
            hbox2=QHBoxLayout()
            hbox2.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
            hbox2.setContentsMargins(5, 15, 0, 0)
            hbox2.addWidget(self.labelShutter)
            
            hbox2.addWidget(self.shutterBox)
            self.widgetShutter=QWidget(self)
            
            self.widgetShutter.setLayout(hbox2)
            self.dockShutter=QDockWidget(self)
            self.dockShutter.setWidget(self.widgetShutter)
            
            
            
            
            
            
            hboxTemp=QVBoxLayout()
            self.tempButton=QToolButton(self)
            self.tempButton.setMaximumWidth(60)
            # self.tempButton.setAlignment((Qt.AlignmentFlag.AlignCenter)
            self.tempButton.setText('Temp:')
            hboxTemp.addWidget(self.tempButton)
            
            self.tempBox=QLabel()
            self.tempBox.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hboxTemp.addWidget(self.tempBox)
            
            
            
            
            self.widgetTemp=QWidget(self)
            self.widgetTemp.setLayout(hboxTemp)
            self.dockTemp=QDockWidget(self)
            
            
            
            self.dockTemp.setWidget(self.widgetTemp)
            
            # self.TrigSoft=QPushButton('Trig Soft',self)
            # self.TrigSoft.setMaximumWidth(100)
            # self.vbox1.addWidget(self.TrigSoft)
        
            # self.vbox1.addStretch(1)
            # self.cameraWidget.setLayout(self.vbox1)
            # self.cameraWidget.setMinimumSize(150,200)
            # self.cameraWidget.setMaximumSize(200,900)
            
            hMainLayout=QHBoxLayout()
            
            if self.light==False:
                #from visu.visual2 import SEE
                from visu import SEE
                self.visualisation=SEE(parent=self,name=self.nbcam,**self.kwds) ## Widget for visualisation and tools  self.confVisu permet d'avoir plusieurs camera et donc plusieurs fichier ini de visualisation
                # self.visualisation.setWindowTitle('Visualization    '+ self.cameraType+"   " + self.ccdName+'       v.'+ self.version)
                if self.separate==True:
                    # print('ici')
                    self.vbox2=QVBoxLayout() 
                    self.vbox2.addWidget(self.visualisation)
                    if self.aff=='left':
                        hMainLayout.addLayout(self.vbox2)
                        hMainLayout.addWidget(self.cameraWidget)
                    else :
                        hMainLayout.addWidget(self.cameraWidget)
                        hMainLayout.addLayout(self.vbox2)
                else:
                    
                    self.dockControl.setTitleBarWidget(QWidget()) # to avoid tittle
                    
                    #self.dockControl.setFeatures(QDockWidget.DockWidgetMovable)
                    self.visualisation.addDockWidget(Qt.TopDockWidgetArea,self.dockControl)
                    self.dockTrig.setTitleBarWidget(QWidget())
                    self.visualisation.addDockWidget(Qt.TopDockWidgetArea,self.dockTrig)
                    
                    self.dockShutter.setTitleBarWidget(QWidget())
                    self.visualisation.addDockWidget(Qt.TopDockWidgetArea,self.dockShutter)
                    
                    self.dockExposure.setTitleBarWidget(QWidget())
                    self.visualisation.addDockWidget(Qt.TopDockWidgetArea,self.dockExposure)
                   
                    self.dockTemp.setTitleBarWidget(QWidget())
                    self.visualisation.addDockWidget(Qt.TopDockWidgetArea,self.dockTemp)
                    
                    hMainLayout.addWidget(self.visualisation)
                    
                    
                    
                
                
            else:
                from visu import SEELIGHT
                self.visualisation=SEELIGHT(confpath=self.confPath,name=self.nbcam,**self.kwds)
                self.visualisation.hbox0.addWidget(self.cameraWidget)
                hMainLayout.addWidget(self.visualisation)
                
                
            self.setLayout(hMainLayout)
            self.setContentsMargins(0, 0, 0, 0)
            #self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint) # set window on the top 
            #self.activateWindow()
            #self.raise_()
            #self.showNormal()
            
    def actionButton(self): 
        '''action when button are pressed
        '''
        self.runButton.clicked.connect(self.acquireMultiImage)
        self.snapButton.clicked.connect(self.acquireOneImage)
        self.stopButton.clicked.connect(self.stopAcq)      
        self.exposureBox.editingFinished.connect(self.setExposure)    
        self.hSliderShutter.sliderReleased.connect(self.mSliderSetExposure)
        
        
        self.trigg.currentIndexChanged.connect(self.trigger)
        
        self.shutterBox.currentIndexChanged.connect(self.shutterChoice)
        
        self.tempButton.clicked.connect(lambda:self.open_widget(self.tempWidget) )
        
        self.CAM.newData.connect(self.Display)#,QtCore.Qt.DirectConnection)
        # self.TrigSoft.clicked.connect(self.softTrigger)
    
    
    def oneImage(self):
        #self.nbShot=1
        self.acquireOneImage()

    def nbShotAction(self):
        '''
        number of snapShot
        '''
        nbShot, ok=QInputDialog.getInt(self,'Number of SnapShot ','Enter the number of snapShot ')
        if ok:
            self.nbShot=int(nbShot)
            if self.nbShot<=0:
               self.nbShot=1
    
    def wait(self,seconds):
        time_end=time.time()+seconds
        while time.time()<time_end:
            QtGui.QApplication.processEvents()    
    
    def Display(self,data):
        '''Display data with visualisation module
        
        '''
        if self.multi==True:
            self.wait(0.1)
        print('received')
        self.data=data
        self.signalData.emit(self.data)
        # self.visualisation.newDataReceived(self.data)
        self.imageReceived=True
        self.datareceived.emit(True)
        if self.CAM.camIsRunnig==False:
            self.stopAcq()
              
    def setExposure (self):
        '''
        set exposure time 
        '''
        
        sh=self.exposureBox.value() # 
        self.hSliderShutter.setValue(sh) # set value of slider
        time.sleep(0.1)
        self.CAM.setExposure(sh) # Set shutter CCD in ms
        self.conf.setValue(self.nbcam+"/shutter",float(sh))
        self.CAM.camParameter["exposureTime"]=sh
        self.conf.sync()
    
    
    
    def mSliderSetExposure(self): # for shutter slider 
        sh=self.hSliderShutter.value() 
        self.exposureBox.setValue(sh) # 
        self.CAM.setExposure(sh) # Set shutter CCD in ms
        self.conf.setValue(self.nbcam+"/shutter",float(sh))
        self.CAM.camParameter["exposureTime"]=sh
        # self.conf.sync()
        
        
    def trigger(self):
        
        ''' select trigger mode
         trigger on
         trigger off
        '''
        self.itrig=self.trigg.currentIndex()
        
        if self.itrig==1:
            self.CAM.setTrigger("on")
        else :
            self.CAM.setTrigger("off")
                
    def acquireOneImage(self):
        '''Start on acquisition
        '''
        self.imageReceived=False
        self.runButton.setEnabled(False)
        self.runButton.setStyleSheet("QToolButton:!pressed{border-image: url(%s);background-color: gray ;border-color: gray;}""QToolButton:pressed{image: url(%s);background-color: gray ;border-color: gray}"%(self.iconPlay,self.iconPlay))
        self.snapButton.setEnabled(False)
        self.snapButton.setStyleSheet("QToolButton:!pressed{border-image: url(%s);background-color: gray ;border-color: gray;}""QToolButton:pressed{image: url(%s);background-color: gray ;border-color:gray}"%(self.iconSnap,self.iconSnap))
        self.stopButton.setEnabled(True)
        self.stopButton.setStyleSheet("QToolButton:!pressed{border-image: url(%s);background-color: transparent ;border-color: gray;}""QToolButton:pressed{image: url(%s);background-color: gray ;border-color: gray}"%(self.iconStop,self.iconStop) )
        self.trigg.setEnabled(False)
        # print('one acq')
        self.CAM.startOneAcq(self.nbShot)
        
    
    def acquireMultiImage(self):    
        ''' 
            start the acquisition thread
        '''
        
        self.runButton.setEnabled(False)
        self.runButton.setStyleSheet("QToolButton:!pressed{border-image: url(%s);background-color: gray ;border-color: gray;}""QToolButton:pressed{image: url(%s);background-color: gray ;border-color: gray}"%(self.iconPlay,self.iconPlay))
        self.snapButton.setEnabled(False)
        self.snapButton.setStyleSheet("QToolButton:!pressed{border-image: url(%s);background-color: gray ;border-color: gray;}""QToolButton:pressed{image: url(%s);background-color: gray ;border-color: gray}"%(self.iconSnap,self.iconSnap))
        self.stopButton.setEnabled(True)
        self.stopButton.setStyleSheet("QToolButton:!pressed{border-image: url(%s);background-color: transparent ;border-color: gray;}""QToolButton:pressed{image: url(%s);background-color: gray ;border-color: gray}"%(self.iconStop,self.iconStop) )
        self.trigg.setEnabled(False)
        
        self.CAM.startAcq() # start mutli image acquisition thread 
        
        
    def stopAcq(self):
        '''Stop  acquisition
        '''
        
        if self.isConnected==True:
            self.CAM.stopAcq()
        
        self.runButton.setEnabled(True)
        self.runButton.setStyleSheet("QToolButton:!pressed{border-image: url(%s);background-color: transparent ;border-color: gray;}""QToolButton:pressed{image: url(%s);background-color: gray ;border-color: gray}"%(self.iconPlay,self.iconPlay))
        self.snapButton.setEnabled(True)
        self.snapButton.setStyleSheet("QToolButton:!pressed{border-image: url(%s);background-color: transparent ;border-color: gray;}""QToolButton:pressed{image: url(%s);background-color: gray ;border-color: gray}"%(self.iconSnap,self.iconSnap))
        
        self.stopButton.setEnabled(False)
        self.stopButton.setStyleSheet("QToolButton:!pressed{border-image: url(%s);background-color: gray ;border-color: gray;}""QToolButton:pressed{image: url(%s);background-color: gray ;border-color: gray}"%(self.iconStop,self.iconStop) )
        self.trigg.setEnabled(True)  
    
    
    
    
    def update_temp(self, temp=None):
        # if temp == None:
        #     temp = self.mte.GetTemperature()
        # print(temp)
        self.tempBox.setText('%.1f °C' % temp)
    
    
    def shutterChoice(self):
        ''' select shuuter mode
         Auto
         Open
         Closed
         typ,mode,closingtime,openingtime
        '''
        self.iShutter=int(self.shutterBox.currentIndex())
        
        
        self.CAM.SetShutter(typ=int(1),mode=self.iShutter,closingtime=int(50),openingtime=int(50))
       
    
    
    def open_widget(self,fene):
        
        """ open new widget 
        """
        
        if fene.isWinOpen==False:
            #New widget"
            fene.show()
            fene.isWinOpen=True
    
        else:
            #fene.activateWindow()
            fene.raise_()
            fene.showNormal()
            
    def close(self):
        if self.isConnected==True:
            self.threadTemp.stopTemp=True
            self.CAM.CoolerOFF()
            time.sleep(0.1)
            self.CAM.closeCamera()
        
        
    def closeEvent(self,event):
        ''' closing window event (cross button)
        '''
        if self.isConnected==True:
             self.stopAcq()
             time.sleep(0.1)
             self.close()




class ThreadTemperature(QtCore.QThread):
    """
    Thread pour la lecture de la temperature toute les 2 secondes
    """
    TEMP =QtCore.pyqtSignal(float) # signal pour afichage temperature

    def __init__(self, parent=None,CAM=None):
        super(ThreadTemperature,self).__init__(parent)
        self.CAM    = CAM
        self.stopTemp=False
        
    def run(self):
        while self.stopTemp is not True:
            err=self.CAM.GetTemperature()
            temp=self.CAM.temperature
            time.sleep(2)
            self.TEMP.emit(float(temp))
            if self.stopTemp:
                break



            
class TEMPWIDGET(QWidget):
    '''
    widget to set the temperature
    '''
    
    def __init__(self, CAM=None,parent=None):
        
        super(TEMPWIDGET, self).__init__(parent)
        self.CAM=CAM
        self.isWinOpen=False
        self.parent=parent
        self.setup()
        self.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt6'))
        self.cooler='off'
    def setup(self) :   
        self.setWindowIcon(QIcon('./icons/LOA.png'))
        self.setWindowTitle('Temperature')
        self.vbox=QVBoxLayout()
        labelT=QLabel('Temperature')
        self.tempVal= QDoubleSpinBox(self)
        self.tempVal.setSuffix(" %s" % '°C')
        self.tempVal.setMaximum(21)
        self.tempVal.setMinimum(-40)
        self.tempVal.setValue(20)
        self.tempSet=QToolButton()
        self.tempSet.setText('Set')
        self.hbox=QHBoxLayout()
        self.hbox.addWidget(labelT)
        self.hbox.addWidget(self.tempVal)
        self.hbox.addWidget(self.tempSet)
        self.vbox.addLayout(self.hbox)
        self.setLayout(self.vbox)
        self.tempSet.clicked.connect(self.SET)
        
    def SET(self):
        temp = self.tempVal.value()
        if self.cooler == 'off':
            self.CAM.CoolerON()
        self.CAM.SetTemperature(temp)
        
    
    def closeEvent(self, event):
        """ when closing the window
        """
        self.isWinOpen=False
        
        time.sleep(0.1)
        event.accept()             
            
if __name__ == "__main__":       
    
    appli = QApplication(sys.argv) 
    appli.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt6'))
    #pathVisu='C:/Users/UPX/Desktop/python/andorIdus/confCamera.ini'
    e = CAMERA(cam='camDefault',fft='off',meas='on',affLight=False,separate=False,multi=False)#,confpath=pathVisu)  
    e.show()
    # x= CAMERA(cam="cam2",fft='off',meas='on',affLight=True,multi=False)  
    # x.show()
    appli.exec_()       