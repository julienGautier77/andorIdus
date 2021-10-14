# -*- coding: utf-8 -*-
"""
Created on Wed Oct  6 15:24:40 2021

@author: Salle-Jaune
"""

import ctypes
import platform
import numpy as np
import sys
import time
from pyqtgraph.Qt import QtCore


ERROR_CODE = {
    20001: "DRV_ERROR_CODES",
    20002: "DRV_SUCCESS",
    20003: "DRV_VXNOTINSTALLED",
    20006: "DRV_ERROR_FILELOAD",
    20007: "DRV_ERROR_VXD_INIT",
    20010: "DRV_ERROR_PAGELOCK",
    20011: "DRV_ERROR_PAGE_UNLOCK",
    20013: "DRV_ERROR_ACK",
    20024: "DRV_NO_NEW_DATA",
    20026: "DRV_SPOOLERROR",
    20034: "DRV_TEMP_OFF",
    20035: "DRV_TEMP_NOT_STABILIZED",
    20036: "DRV_TEMP_STABILIZED",
    20037: "DRV_TEMP_NOT_REACHED",
    20038: "DRV_TEMP_OUT_RANGE",
    20039: "DRV_TEMP_NOT_SUPPORTED",
    20040: "DRV_TEMP_DRIFT",
    20050: "DRV_COF_NOTLOADED",
    20053: "DRV_FLEXERROR",
    20066: "DRV_P1INVALID",
    20067: "DRV_P2INVALID",
    20068: "DRV_P3INVALID",
    20069: "DRV_P4INVALID",
    20070: "DRV_INIERROR",
    20071: "DRV_COERROR",
    20072: "DRV_ACQUIRING",
    20073: "DRV_IDLE",
    20074: "DRV_TEMPCYCLE",
    20075: "DRV_NOT_INITIALIZED",
    20076: "DRV_P5INVALID",
    20077: "DRV_P6INVALID",
    20083: "P7_INVALID",
    20089: "DRV_USBERROR",
    20091: "DRV_NOT_SUPPORTED",
    20095: "DRV_INVALID_TRIGGER_MODE",
    20099: "DRV_BINNING_ERROR",
    20990: "DRV_NOCAMERA",
    20991: "DRV_NOT_SUPPORTED",
    20992: "DRV_NOT_AVAILABLE"
}



class ANDOR(QtCore.QThread):
    
    newData=QtCore.pyqtSignal(object) # signal emited when receive image 
    
    def __init__(self,cam='camDefault',conf=None,**kwds):
        super(ANDOR,self).__init__()
        # Check operating system and load library
        # for Windows
        if platform.system() == "Windows":
            if platform.architecture()[0] == "32bit":
                # self.dll = cdll("C:\\Program Files\\Andor SOLIS\\Drivers\\atmcd32d")
                self.dll=ctypes.windll.LoadLibrary("C:\\Program Files\\Andor SOLIS\\Drivers\\atmcd32d")
                print('load dll 32')
            else:
                self.dll = ctypes.windll.LoadLibrary("C:\\Program Files\\Andor SOLIS\\Drivers\\atmcd64d")
        
        
        self.nbcam=cam
        
        
        if conf==None:
            self.conf=QtCore.QSettings('confCamera.ini', QtCore.QSettings.IniFormat)
        else:
            self.conf=conf
            
        self.camParameter=dict()
        self.verbosity   = True
        self.itrig='off'
        self.Initialize()
        
        cw = ctypes.c_int()
        ch = ctypes.c_int()
        
        self.dll.GetDetector(ctypes.byref(cw),ctypes. byref(ch))
        self.width       = cw.value
        self.height      = ch.value
        print('size',self.width,self.height)
        self.temperature = None
        self.set_T       = None
        self.gain        = None
        self.gainRange   = None
        # self.status      = ERROR_CODE[error]
        
        self.preampgain  = None
        self.channel     = None
        self.outamp      = None
        self.hsspeed     = None
        self.vsspeed     = None
        self.serial      = None
        self.exposure    = None
        self.accumulate  = None
        self.kinetic     = None
        self.ReadMode    = None
        self.AcquisitionMode = None
        self.scans       = 1
        self.hbin        = 1
        self.vbin        = 1
        self.hstart      = 1
        self.hend        = cw
        self.vstart      = 1
        self.vend        = ch
        self.cooler      = None 
        
        self.camIsRunnig=False
        self.nbShot=1
        self.isConnected=False
    
    
    def Initialize(self):
        tekst = ctypes.c_char()  
        error = self.dll.Initialize(ctypes.byref(tekst))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        xpixels = ctypes.c_int()
        ypixels = ctypes.c_int()
        error = self.dll.GetDetector(ctypes.byref(xpixels),ctypes. byref(ypixels))
        if error != 20002:
            raise IOError(ERROR_CODE[error])
        else:
            self.setCamParameter()
        self.width  =xpixels.value
        
        self.height=ypixels.value
        
        return ERROR_CODE[error]
    
    def verbose(self, error, function=''):
        if self.verbosity is True:
            print( "[%s]: %s" %(function, error))

    def SetVerbose(self, state=True):
        self.verbose = state
    
    
    
    
    def setCamParameter(self): 
        """Set initial parameters
        """
               
        self.GetCameraSerialNumber()
        self.camID=self.serial
        print(' connected @ serial : ',self.serial )
                
        
        self.LineTrigger=str('None') # for 
        
        self.SetTriggerMode(0)
        
        
        
        self.camParameter["expMax"]=2000
        self.camParameter["expMin"]=0.1
        
        
        
        print (self.nbcam)
        self.camParameter["exposureTime"]=float(self.conf.value(self.nbcam+"/shutter"))
        
        
        self.threadRunAcq=ThreadRunAcq(self)
        
        
        self.threadRunAcq.newDataRun.connect(self.newImageReceived)
           
            
        self.threadOneAcq=ThreadOneAcq(self)
        self.threadOneAcq.newDataRun.connect(self.newImageReceived)
        self.threadOneAcq.newStateCam.connect(self.stateCam)
    
    
    
    
    
    
    
    
    
    ### Camera info    
    def GetAvailableCameras(self):
        Ncam = ctypes.c_long()
        error = self.dll.GetAvailableCameras(ctypes.byref(Ncam))
        if error != 20002:
            raise IOError(ERROR_CODE[error])
        return Ncam.value

    
    def GetCameraHandle(self, index):
        handle = ctypes.c_long()
        index = ctypes.c_long(index)
        error = self.dll.GetCameraHandle(index, ctypes.byref(handle))
        if error != 20002:
            raise IOError(ERROR_CODE[error])
        return handle.value

    
    def SetCurrentCamera(self, handle):
        handle = ctypes.c_long(handle)
        error = self.dll.SetCurrentCamera(handle)
        if error != 20002:
            raise IOError(ERROR_CODE[error])

    
    def GetCurrentCamera(self):
        handle = ctypes.c_long()
        error = self.dll.GetCurrentCamera(ctypes.byref(handle))
        if error != 20002:
            raise IOError(ERROR_CODE[error])
        return handle.value

    
    def GetCamerasInfo(self):
        cameralist = []
        for ind in range(self.GetAvailableCameras()):
            handle = self.GetCameraHandle(ind)
            self.SetCurrentCamera(handle)
            self.init_camera()
            cameralist.append(dict(handle=handle,
                                   serial=self.GetCameraSerialNumber(),
                                   model=self.GetHeadModel()))
        return cameralist
    
    
    def GetCameraSerialNumber(self):
        serial = ctypes.c_int()
        error = self.dll.GetCameraSerialNumber(ctypes.byref(serial))
        self.serial = serial.value
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]
    
        
    
    
    
    def SetReadMode(self, mode):
        #0: Full vertical binning
        #1: multi track
        #2: random track
        #3: single track
        #4: image
        error = self.dll.SetReadMode(mode)
        self.ReadMode = mode
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]
    
    
    def SetAcquisitionMode(self, mode):
        #1: Single scan
        #3: Kinetic scan
        error = self.dll.SetAcquisitionMode(mode)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        self.AcquisitionMode = mode
        return ERROR_CODE[error]
    
    def SetShutter(self,typ,mode,closingtime,openingtime):
        error = self.dll.SetShutter(typ,mode,closingtime,openingtime)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def SetShutterEx(self, typ, mode, closingtime, openingtime, extmode):
        '''
        Set the configuration for the shutter in external mode
        Input:
            typ         (int) : 0/1 Output TTL low/high signal to open shutter
            mode        (int) : 0/1/2 For Auto/Open/Close
            closingtime (int) : millisecs it takes to close
            openingtime (int) : millisecs it takes to open
            extmode     (int) : 0/1/2 For Auto/Open/Close
        Output:
            None
        '''
        error = self.dll.SetShutterEx(typ, mode, closingtime, openingtime,
                                       extmode)
        if error != 20002:
            raise IOError(ERROR_CODE[error])


    def SetImage(self,hbin,vbin,hstart,hend,vstart,vend):
        self.hbin = hbin
        self.vbin = vbin
        self.hstart = hstart
        self.hend = hend
        self.vstart = vstart
        self.vend = vend
        
        error = self.dll.SetImage(hbin,vbin,hstart,hend,vstart,vend)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]
    
    
    def setExposure(self, time):
        time=time/1000 # in seconds
        error = self.dll.SetExposureTime(ctypes.c_float(time))
        self.exposure = time
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]
    
    
    

    def SetSingleScan(self):
        self.SetReadMode(4)
        self.SetAcquisitionMode(1)
        self.SetImage(1,1,1,self.width,1,self.height)
    
    
    def SetFanMode(self, mode):
        #0: fan on full
        #1: fan on low
        #2: fna off
        error = self.dll.SetFanMode(mode)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]
    
    def CoolerON(self):
        error = self.dll.CoolerON()
        self.cooler = 1
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def CoolerOFF(self):
        error = self.dll.CoolerOFF()
        self.cooler = 0
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]

    def IsCoolerOn(self):
        iCoolerStatus = ctypes.c_int()
        self.cooler = iCoolerStatus
        error = self.dll.IsCoolerOn(ctypes.byref(iCoolerStatus))
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return iCoolerStatus.value

    def GetTemperature(self):
        ctemperature = ctypes.c_int()
        error = self.dll.GetTemperature(ctypes.byref(ctemperature))
        self.temperature = ctemperature.value
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]
    
    def GetTemperatureRange(self):
        '''
        Returns the temperature range in degrees Celcius
        Input:
            None
        Output:
            (int,int) : temperature min and max in degrees Celcius
        '''
        ctemperature_min = ctypes.c_int()
        ctemperature_max = ctypes.c_int()

        error = self.dll.GetTemperatureRange(ctypes.byref(ctemperature_min), ctypes.byref(ctemperature_max))
        if error != 20002:
            raise IOError(ERROR_CODE[error])
        return ERROR_CODE[error], (ctemperature_min.value, ctemperature_max.value)
    
    def SetTemperature(self,temperature):
        #ctemperature = c_int(temperature)
        #error = self.dll.SetTemperature(byref(ctemperature))
        error = self.dll.SetTemperature(int(temperature))
        self.set_T = temperature
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]
    
    
    
    def setTrigger(self,trig='off'):
        '''set trigger mode on/off
        '''
        
        if trig=='on':
            self.SetTriggerMode(int(1))
            self.itrig='on'
        else:
            self.SetTriggerMode(int(0))
            
            self.itrig='off'
    
    
    
    def SetTriggerMode(self, mode):
        '''
        Set the trigger mode
        Input:
            mode (int) : 0 Internal
                         1 External
                         2 External Start (only in Fast Kinetics mode)
        Output:
            None
        '''
        error = self.dll.SetTriggerMode(mode)
        if error != 20002:
            raise IOError(ERROR_CODE[error])
    
    def StartAcquisition(self):
        error = self.dll.StartAcquisition()
        self.dll.WaitForAcquisition()
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]
    
    

    def AbortAcquisition(self):
        '''
        Abort the acquisition
        '''
        error = self.dll.AbortAcquisition()
        if error != 20002:
            raise IOError(ERROR_CODE[error])
            
    def GetAcquiredData(self,imageArray):
        
        if (self.ReadMode==4):
            if (self.AcquisitionMode==1):
                dim = self.width * self.height / self.hbin / self.vbin
            elif (self.AcquisitionMode==3):
                dim = self.width * self.height / self.hbin / self.vbin * self.scans
        elif (self.ReadMode==3 or self.ReadMode==0):
            if (self.AcquisitionMode==1):
                dim = self.width
            elif (self.AcquisitionMode==3):
                dim = self.width * self.scans

        cimageArray = ctypes.c_int32 * int(dim)
        cimage = cimageArray()
        
        numPixel=ctypes.c_ulong(int(dim))
        error = self.dll.GetAcquiredData(ctypes.pointer(cimage),numPixel)
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        print(len(cimage))
        # for i in range(len(cimage)):
        #     imageArray.append(cimage[i])
        # print((imageArray))
        # self.imageArray = imageArray
        self.imageArray=cimage
        #self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]
    
    
    def getImage(self):
        data=[]
        self.GetAcquiredData(data)
        # print(data.dtype)
        # data = np.frombuffer(self.imageArray, dtype=np.int32)
        self.data=np.array(self.imageArray)
        # self.data = np.r_[np.zeros( self.height), self.data]
        # print(self.data.shape)
        
        return self.data.reshape(self.height, self.width)
        # return data.reshape(self.width , self.height)
                          
        
        
        
        
    
    
        
    def GetAcquisitionTimings(self):
        exposure   = ctypes.c_float()
        accumulate = ctypes.c_float()
        kinetic    = ctypes.c_float()
        error = self.dll.GetAcquisitionTimings(ctypes.byref(exposure),ctypes.byref(accumulate),ctypes.byref(kinetic))
        self.exposure = exposure.value
        self.accumulate = accumulate.value
        self.kinetic = kinetic.value
        self.verbose(ERROR_CODE[error], sys._getframe().f_code.co_name)
        return ERROR_CODE[error]
    
    
    
    def ShutDown(self):  # Careful with this one!!
        '''
        Shut down the Andor
        '''
        error = self.dll.ShutDown()
        if error != 20002:
            raise IOError(ERROR_CODE[error])


    def startAcq(self):
        '''Acquistion in live mode
        '''
        
        self.camIsRunnig=True
        self.threadRunAcq.newRun() # to set stopRunAcq=False
        self.threadRunAcq.start()
    
    def startOneAcq(self,nbShot):
        '''Acquisition of a number (nbShot) of image 
        '''
        
        self.nbShot=nbShot 
        self.camIsRunnig=True
        self.threadOneAcq.newRun() # to set stopRunAcq=False
        self.threadOneAcq.start()
        
    def stopAcq(self):
        
        self.threadRunAcq.stopThreadRunAcq()
        # if self.threadRunAcq.isRunning():
        #     self.threadRunAcq.terminate()
        self.threadOneAcq.stopThreadOneAcq()
        self.camIsRunnig=False  
            
    def newImageReceived(self,data):
        '''Emit the data when receive a data from the thread threadRunAcq threadOneAcq
        '''
        
        self.data=data
        self.newData.emit(self.data)
    
        
    def stateCam(self,state):
        '''state of camera : True is running False : is stopped
        '''
        
        self.camIsRunnig=state
    
    def closeCamera(self):
        print('close')
        self.dll.ShutDown()
        
        
        
        
class ThreadRunAcq(QtCore.QThread):
    '''Second thread for controling continus acquisition independtly
    '''
    newDataRun=QtCore.Signal(object)
    
    def __init__(self, parent):
        
        super(ThreadRunAcq,self).__init__(parent)
        self.parent=parent
        
        self.stopRunAcq=False
        self.itrig= parent.itrig
        self.LineTrigger=parent.LineTrigger
        
        
    def newRun(self):
        self.stopRunAcq=False
        
    def run(self):
        
        while self.stopRunAcq is not True :
            
            try :
                self.parent.StartAcquisition()
                self.data=np.array(self.parent.getImage())
                self.data=np.rot90(self.data,1)
            except :
                self.parent.AbortAcquisition()
                
            # self.data=np.rot90(data,1)
            
            if np.max(self.data)>0: # send data if not zero 
                
                if self.stopRunAcq==True:
                    break
                else :
                    self.newDataRun.emit(self.data)
                    # print(self.cam0.DeviceTemperature.GetValue())
            # self.mutex.unlock()
    def stopThreadRunAcq(self):
        
        self.stopRunAcq=True
        
        try :
            self.parent.AbortAcquisition()
        except :
            pass
        
    def closeCamera(self):
        self.cam0.Close()
        
        
        
class ThreadOneAcq(QtCore.QThread):
    '''Second thread for controling one or anumber of  acquisition independtly
    '''
    newDataRun=QtCore.Signal(object)
    newStateCam=QtCore.Signal(bool) # signal to emit the state (running or not) of the camera
    
    def __init__(self, parent):
        
        super(ThreadOneAcq,self).__init__()
        self.parent=parent
        
        self.stopRunAcq=False
        self.itrig= parent.itrig
        self.LineTrigger=parent.LineTrigger
        
   
    
    def newRun(self):
        self.stopRunAcq=False
        
    def run(self):
        self.newStateCam.emit(True)
        
        for i in range (self.parent.nbShot):
            if self.stopRunAcq is not True :
                self.parent.StartAcquisition()
                self.data=self.parent.getImage()
                self.data=np.rot90(self.data,1)
                if i<self.parent.nbShot-1:
                    self.newStateCam.emit(True)
                else:
                    self.newStateCam.emit(False)
                    time.sleep(0.1)
                    
                 
                self.newDataRun.emit(self.data)
                    
            else:
                break
            
        self.newStateCam.emit(False)
       
    def stopThreadOneAcq(self):
        
        self.stopRunAcq=True
        
        try :
            self.parent.AbortAcquisition()
        except :
            pass      





            
if __name__ == '__main__':
    a= ANDOR()
    a.SetSingleScan()
    a.StartAcquisition()
    data=np.array(a.getImage())
    print(data)
    
    