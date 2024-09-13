# coding: utf-8
'''
Communicate with Mitsubishi Electric CNC M700 series using EZSocket.
The object of communication is the machining center Mitsubishi CNC M700 / M700V / M70 / M70V.
'''
from enum import Enum
import threading
import re
import pythoncom
import win32com.client
from win32com.client import VARIANT
import datetime

class M700 ():

    # Use the same instance for the same host connection in the same thread
    # The same thread is because it is complicated to share COM objects with different threads
    __connections = {}
    @classmethod
    def get_connection(cls, host):
        key = str(threading.current_thread(). ident) + "_" + host
        if key not in cls.__connections:
            cls.__connections[key] = M700(host)
        return cls.__connections[key]
    
    #Unique value management for   1-255
    __uno_list = [False] * 255
    @classmethod
    def alloc_unitno(cls):
        # print(cls .__uno_list)
        '''Return an unused unit number in EZSocket.

        Returns:
            int: Unit number
        '''
        for i, v in enumerate(cls .__uno_list):
            if v == False:
                cls .__uno_list[i] = True
                return i + 1
        raise Exception("Unit number exceeds 255. Too many simultaneous connections")
    
    @classmethod
    def release_unitno(cls, uno):
        cls .__uno_list[uno-1] = False
    
    # --- In-class enumeration ---
    
    class RunStatus (Enum):
        '''Operation status (value corresponds to the value returned by M700)'''
        NOT_AUTO_RUN = 0
        AUTO_RUN = 1

    class Position (Enum):
        '''X, Y, Z coordinate specification (value corresponds to the returned value of M700)'''
        X = 1
        Y = 2
        Z = 3

    class ProgramType (Enum):
        '''Main or subprogram (value corresponds to the value returned by M700)'''
        MAIN = 0
        SUB = 1

    class NCProgramFileOpenMode (Enum):
        '''Mode to use when opening program file in NC'''
        READ = 1
        WRITE = 2
        OVER_WRITE = 3

    __ip = None
    __port = None
    __isopen = False
    __ezcom = None
    __lock = threading.RLock()

    def __init__(self, host):
        '''
        Args:
            host: IP address: port number
        '''
        pythoncom.CoInitialize()  # When executing with multiple threads, the COM object must be initialized
        self.__ip, self.__port = host.split(':')

    def __str__(self):
         return self.__ip + ":" + self.__port + "" + ("Open" if self.__isopen else "Close")
    def __open(self):
        '''Open a connection for the IP and unit number given as arguments.
        If it is called again after being opened, nothing is done. '''
        if not self.__isopen:
            self.__ezcom = win32com.client.Dispatch('EZNcAut.DispEZNcCommunication')
            errcd = self.__ezcom.SetTCPIPProtocol(self.__ip, int(self.__port))
            self.__unitno = M700.alloc_unitno()
            self.__raise_error(errcd)
            # Argument: Machine type number (fixed), unit number, timeout 100 milliseconds, COM host name
            # Machine type 6 = EZNC_SYS_MELDAS700M (Machine Center Mitsubishi CNC M700 / M700V / M70 / M70V)
            # The unit number must be unique within 1 ~ 255.
            errcd = self.__ezcom.Open2(6, self.__unitno, 255, 'EZNC_LOCALHOST')
            if(errcd!=0):
                errcd = self.__ezcom.Open2(5, self.__unitno, 255, 'EZNC_LOCALHOST')

            self.__raise_error(errcd)
            self.__isopen = True

    def close(self):
        '''Close the connection.
        No exception is returned to the caller if an internal error occurs
        '''
        try:
            M700.release_unitno(self.__unitno)  # Release unit number
            self.__isopen = False
            self.__ezcom.Close()
        except Exception as es:
            #  print(es)
             pass
        try:
            self.__ezcom.Release()
        except Exception as ex:
            #  print('here',ex)
             pass

    def is_open(self):
        '''After __open () processing, check if the connection is open.
        
        Return:
            bool: True if the connection is open
        '''
        with self.__lock:
            try:
                self.__open()
            except:
                pass
            return self.__isopen
    def Availability(self):
        try:
            A,B,C,D,E,F= self.Time()
            return  "Available" if self.__isopen else "Not Available"
        except Exception as e:
            return "Not Availabled"
    # --- NC information acquisition related ---
    def set_stop (self):
 
        with self.__lock:

            self.__open ()
            errcd = self.__ezcom.Operation_Stop()
            self.__raise_error (errcd)
    def set_start (self):

        with self.__lock:

            self.__open ()
            errcd = self.__ezcom.Operation_Run()
            self.__raise_error (errcd)
    # --- NC information acquisition related ---   
    
    

     
    def GetSystemInformation(self):
        """Gets information regarding the NC system."""
        """Part system enabled/disabled 0: Part system disabled 1: Part system enabled"""
        """Number of axes each part system This will be different for NC systems with 1 [Axis] or more."""
        with self.__lock:
            self.__open()
            errcd1, statePartSystem = self.__ezcom.System_GetSystemInformation(0)
            self.__raise_error(errcd1)
            errcd2, nberofAxePartSystem = self.__ezcom.System_GetSystemInformation(1)
            self.__raise_error(errcd2)
            return statePartSystem, nberofAxePartSystem
        
    # --- Position acquisition related --- 
    def GetWorkPosition(self):
        """Gets the workpiece coordinate position of the set system/axis number
        If 1 is set for the skip on flag, the workpiece coordinate position at the time the skip on signal is
       input will be got."""
        
        with self.__lock:
            self.__open()
            errcd1, Posx = self.Position_GetWorkPosition(1,0)
            self.__raise_error(errcd1)
            errcd2, PosY = self.__ezcom.Position_GetWorkPosition(2,0)
            self.__raise_error(errcd2)
            #errcd3, Posz = self.__ezcom.Position_GetWorkPosition(3,0)
            #self.__raise_error(errcd3)
            return Posx,PosY
    
    def GetMachinePosition(self):
        """Gets the machine coordinate position for the set system/axis number (coordinate position in a
           basic machine coordinate system).
           If 1 is set for the skip on flag, the machine coordinate position at the time the skip on signal is
        input will be got."""
        
        with self.__lock:
            self.__open()
            errcd1, Posx = self.__ezcom.Position_GetMachinePosition2(1,1,1)
            self.__raise_error(errcd1)
            errcd2, PosY = self.__ezcom.Position_GetMachinePosition2(2,1)
            self.__raise_error(errcd2)
            #errcd3, Posz = self.__ezcom.Position_GetMachinePosition2(3)
            #self.__raise_error(errcd3)
            return Posx,PosY
    def GetCurrentPosition(self):
        """Gets the relative position to the position at a completion of the dog type zero point return or to the
         preset position configured by G92/origin set/counter set of the set system/axis number."""
         
        with self.__lock:
            self.__open()
            errcd1, Posx = self.__ezcom.Position_GetMachinePosition(1,0)
            self.__raise_error(errcd1)
            errcd2, PosY = self.__ezcom.Position_GetMachinePosition(2,0)
            self.__raise_error(errcd2)
            #errcd3, Posz = self.__ezcom.Position_GetMachinePosition(3,0)
            #self.__raise_error(errcd3)
            return Posx,PosY
        
        
        
    def GetDistance(self):
        """Gets the remaining command of the travel command being executed for the set part system/axis
        number.
        If 1 is set for the skip on flag, the remaining command of the travel command at the time the skip
        on signal is input will be got.""" 
    
        with self.__lock:
            self.__open()
            errcd1, Posx = self.__ezcom.Position_GetMachinePosition(1)
            self.__raise_error(errcd1)
            errcd2, PosY = self.__ezcom.Position_GetMachinePosition(2)
            self.__raise_error(errcd2)
            #errcd3, Posz = self.__ezcom.Position_GetMachinePosition(3)
            #self.__raise_error(errcd3)
            return Posx,PosY    
    

    def purcentageFAfeed (self,x):
        """Gets the feed speed of the set system."""
        """0 F command feed speed (FA)"""
        """1 Manual effective feed speed (FM)"""
        """2 Synchronization feed speed (FS)"""
        """3 Automatic effective feed speed (Fc)"""
        """4 Screw lead (FE)"""
        
        with self.__lock:
            self.__open()
            errcd1, pFcommandFeedSpeed  = self.__ezcom.Position_GetFeedSpeed(x)
            self.__raise_error(errcd1)
            errcd1, cFcommandFeedSpeed  = self.__ezcom.Command_GetFeedCommand(x)
            self.__raise_error(errcd1)
            if cFcommandFeedSpeed != 0:
                   feedspeed=(pFcommandFeedSpeed/cFcommandFeedSpeed)*100
            else :
                   feedspeed=0      
            return feedspeed      
   
    
    def GetTCPSpeed(self):
        """Gets the tip speed of the set part system.
        If 1 is set for the skip on flag, the workpiece coordinate position at the time the skip on signal is
        input will be got.
        This is valid only for the M700/M800 series.
        This function is not supported with C70."""
        
        
        with self.__lock:
            self.__open()
            errcd1, tcpSpeed  = self.__ezcom.Position_GetTCPSpeed()
            self.__raise_error(errcd1)
            return tcpSpeed
        
        
        
    def GetManualOverlap(self):
        
        """Gets the manual interrupt amount of the set part system/axis."""
        """0 If getting the manual interrupt amount while the manual ABS switch is off"""
        """1 If getting the manual interrupt amount while the manual ABS switch is on"""
        """pdLength: Returns the manual interrupt amount for the set axis No. of the set part system. Data range: -99,999.999 to 99,999.999 [mm]"""
        with self.__lock:
            self.__open()
            errcd1, manualInterruptAmountABSOFFx  = self.__ezcom.Position_GetManualOverlap(1,0)
            self.__raise_error(errcd1)
            errcd2, manualInterruptAmountABSONx  = self.__ezcom.Position_GetManualOverlap(1,1)          
            self.__raise_error(errcd2)
            errcd3, manualInterruptAmountABSOFFY  = self.__ezcom.Position_GetManualOverlap(2,0)           
            self.__raise_error(errcd3)
            errcd4, manualInterruptAmountABSOnY  = self.__ezcom.Position_GetManualOverlap(2,1)            
            self.__raise_error(errcd4)
            #errcd5, manualInterruptAmountABSOFFZ  = self.__ezcom.Position_GetManualOverlap(3,0)
            #self.__raise_error(errcd5)
            #errcd6, manualInterruptAmountABSOnZ  = self.__ezcom.Position_GetManualOverlap(3,1)
            #self.__raise_error(errcd6)
            return manualInterruptAmountABSOFFx,manualInterruptAmountABSONx,manualInterruptAmountABSOFFY,manualInterruptAmountABSOnY
        
    def GetProgramPosition(self):
        """pdPosition: Returns the program position.
            Data range: -99,999.999 to 99,999.999 [mm]"""
    
        with self.__lock:
            self.__open()
            errcd1, Posx = self.__ezcom.Position_GetMachinePosition(1)
            self.__raise_error(errcd1)
            errcd2, PosY = self.__ezcom.Position_GetMachinePosition(2)
            self.__raise_error(errcd2)
            #errcd3, Posz = self.__ezcom.Position_GetMachinePosition(3)
            #self.__raise_error(errcd3)
            return Posx,PosY 
    
    
    
    
    def GetTCPMachinePosition(self):
        """pdPosition: Returns the tip machine position of the set axis No. of the set part system.
               Data range: -99,999.999 to 99,999.999 [mm]"""
        
        with self.__lock:
            self.__open()
            errcd1, Posx = self.__ezcom.Position_GetTCPMachinePosition(1)
            self.__raise_error(errcd1)
            errcd2, PosY = self.__ezcom.Position_GetTCPMachinePosition(2)
            self.__raise_error(errcd2)
            #errcd3, Posz = self.__ezcom.Position_GetTCPMachinePosition(3)
            #self.__raise_error(errcd3)
            return Posx,PosY         
        
        
    def GetFeedbackPosition(self):
        """pdPosition: Returns the feedback position of the set axis of the set part system.
             Data range: -99,999.999 to 99,999.999 [mm]"""
        """Gets the feedback position"""
        with self.__lock:
            self.__open()
            errcd1, Posx = self.__ezcom.Position_GetFeedbackPosition(1)
            self.__raise_error(errcd1)
            errcd2, PosY = self.__ezcom.Position_GetFeedbackPosition(2)
            self.__raise_error(errcd2)
            #errcd3, Posz = self.__ezcom.Position_GetFeedbackPosition(3)
            #self.__raise_error(errcd3)
            return Posx,PosY
        
    def GetWorkInstallationPosition(self):
        """pdPosition: Returns the Gets the workpiece installation coordinate system counter of the set axis of the set part system.
             Data range: -99,999.999 to 99,999.999 [mm]"""
        """Gets the workpiece installation coordinate system counter"""
        with self.__lock:
            self.__open()
            errcd1, Posx = self.__ezcom.Position_GetWorkInstallationPosition(1)
            self.__raise_error(errcd1)
            errcd2, PosY = self.__ezcom.Position_GetWorkInstallationPosition(2)
            self.__raise_error(errcd2)
            #errcd3, Posz = self.__ezcom.Position_GetWorkInstallationPosition(3)
            #self.__raise_error(errcd3)
            return Posx,PosY 
    
    
    def GetInclinedSurfacePosition(self):
        """pdPosition: Returns the feedback position of the set axis of the set part system.
             Data range: -99,999.999 to 99,999.999 [mm]"""
        """Gets the inclined surface coordinate system counter"""
        with self.__lock:
            self.__open()
            errcd1, Posx = self.__ezcom.Position_GetInclinedSurfacePosition(1)
            self.__raise_error(errcd1)
            errcd2, PosY = self.__ezcom.Position_GetInclinedSurfacePosition(2)
            self.__raise_error(errcd2)
            #errcd3, Posz = self.__ezcom.Position_GetInclinedSurfacePosition(3)
            #self.__raise_error(errcd3)
            return Posx,PosY           
    

    # --- AxisMonitor acquisition related --- 
    
    def GetServoMonitorSpeed(self):
        """SPEED. Actual motor speed from 0 rpm """
        with self.__lock:
            self.__open()
            errcd1, SpeedxSPEED, Speedx = self.__ezcom.Monitor_GetServoMonitor(1,2)
            self.__raise_error(errcd1)
            errcd2, SpeedYSPEED, SpeedY = self.__ezcom.Monitor_GetServoMonitor(2,2)
            self.__raise_error(errcd2)
            
            
            SpeedZSPEED=0
            statePartSystem,nbaxe=self.__ezcom.GetSystemInformation()
            if nbaxe>2:
             errcd2, SpeedZSPEED, SpeedY  = self.__ezcom.Monitor_GetServoMonitor(3,2)
             self.__raise_error(errcd2)
            
        
            return SpeedxSPEED,SpeedYSPEED,SpeedZSPEED
    
    def GetServoMonitorOverload(self):
        """OVER LOAD. Overload. Unit: %"""
        with self.__lock:
            self.__open()
            errcd1,OverloadXt, OverloadX = self.__ezcom.Monitor_GetServoMonitor(1,6)
            self.__raise_error(errcd1)
            errcd2,OverloadYt, OverloadY = self.__ezcom.Monitor_GetServoMonitor(2,6)
            
            self.__raise_error(errcd2)
            
            Overloadzt=0
            statePartSystem,nbaxe=self.__ezcom.GetSystemInformation()
            if nbaxe>2:
                errcd3,Overloadzt, Overloadz  = self.__ezcom.Monitor_GetServoMonitor(3,6)
                self.__raise_error(errcd3)
            return OverloadXt,OverloadYt,Overloadzt  
    
    
    def GetServoMonitor(self):
        """Gets information about the auxiliary axis monitor"""
        """rotationSpeed,loadCurrent,regenLoad,rotationSpeed"""
        """make ?Conversion of the Unit"""
        with self.__lock:
            self.__open()
            #errcd11, rotationSpeedX,rotationSpeedXstring = self.__ezcom.Monitor_GetAuxAxisMonitor(1,2)
            #self.__raise_error(errcd11)
            #errcd12, loadCurrentX,loadCurrentXstring = self.__ezcom.Monitor_GetAuxAxisMonitor(1,3)
            #self.__raise_error(errcd12)
            #errcd13, OverLoadX, OverLoadXstring = self.__ezcom.Monitor_GetAuxAxisMonitor(1,6)
            #self.__raise_error(errcd13)
            #errcd14, regenLoadX, regenLoadXstring = self.__ezcom.Monitor_GetAuxAxisMonitor(1,7)
            #self.__raise_error(errcd14)
            #errcd21, rotationSpeedY, rotationSpeedYstring  = self.__ezcom.Monitor_GetAuxAxisMonitor(2,2)
            #self.__raise_error(errcd21)
            #errcd22, loadCurrentY, loadCurrentYstring = self.__ezcom.Monitor_GetAuxAxisMonitor(2,3)
            #self.__raise_error(errcd22)
            #errcd23, motorLoadY, motorLoadYstring = self.__ezcom.Monitor_GetAuxAxisMonitor(2,6)
            #self.__raise_error(errcd23)
            #errcd24, regenLoadY, regenLoadYstring = self.__ezcom.Monitor_GetAuxAxisMonitor(2,7)
            #self.__raise_error(errcd24)
            #errcd31, rotationSpeedz = self.__ezcom.Monitor_GetAuxAxisMonitor(3)
            #errcd33, motorLoadz = self.__ezcom.Monitor_GetAuxAxisMonitor(3)
            #errcd32, loadCurrentz = self.__ezcom.Monitor_GetAuxAxisMonitor(3)
            #errcd34, regenLoadz = self.__ezcom.Monitor_GetAuxAxisMonitor(3)
            #self.__raise_error(errcd3)
            #return rotationSpeedXstring,rotationSpeedX,loadCurrentXstring,loadCurrentX,OverLoadXstring,regenLoadXstring,rotationSpeedYstring,loadCurrentYstring,motorLoadYstring,regenLoadYstring
    
    def GetDowelTime(self):
        """Returns the remaining dwell (G04) time. Unit: Second, output up to second, 1/1000 (second)."""
        with self.__lock:
            self.__open()
            errcd, DowelTime = self.__ezcom.Monitor_GetDowelTime()
            self.__raise_error(errcd)
            return DowelTime
        
        
    def GetPowerConsumption(self):
        """Gets the present consumption of entire drive system as an array.This function is not supported with the C70 or M700 series."""
        """presentConsumptionOfEntireDriveSystem,presentPowerConsumptionOfServoAxis,presentPowerConsumptionOfSpindle"""
        """with self.__lock:
            self.__open()
            errcd1, powerConsumptionX  = self.__ezcom.Monitor_GetDowelTime(1)
            self.__raise_error(errcd1)
            errcd2, powerConsumptionY = self.__ezcom.Monitor_GetDowelTime(2)
            self.__raise_error(errcd2)
            #errcd3, powerConsumptionZ = self.__ezcom.Monitor_GetDowelTime(3)
            
            self.__raise_error(errcd3)
            return powerConsumptionX,powerConsumptionY,powerConsumptionZ"""
        with self.__lock:
            self.__open()
            errcd11,presentConsumptionOfEntireDriveSystemX  = self.__ezcom.GetPowerConsumption(1,0)
            self.__raise_error(errcd11)
            errcd12,presentConsumptionOfEntireDriveSystemX  = self.__ezcom.GetPowerConsumption(1,1)
            self.__raise_error(errcd12)
            errcd13,presentConsumptionOfEntireDriveSystemX  = self.__ezcom.GetPowerConsumption(1,2)
            self.__raise_error(errcd13)
            errcd21,presentConsumptionOfEntireDriveSystemY  = self.__ezcom.GetPowerConsumption(2,0)
            self.__raise_error(errcd21)
            errcd22,presentPowerConsumptionOfServoAxisY  = self.__ezcom.GetPowerConsumption(2,1)
            self.__raise_error(errcd22)
            errcd23,presentPowerConsumptionOfSpindleY  = self.__ezcom.GetPowerConsumption(2,3)
            self.__raise_error(errcd23)
            #errcd21,presentConsumptionOfEntireDriveSystemZ  = self.__ezcom.GetPowerConsumption(3,0)
            #errcd22,presentPowerConsumptionOfServoAxisZ  = self.__ezcom.GetPowerConsumption(3,1)
            #errcd23,presentPowerConsumptionOfSpindleZ  = self.__ezcom.GetPowerConsumption(3,3)
            return presentConsumptionOfEntireDriveSystemX,presentConsumptionOfEntireDriveSystemX,presentConsumptionOfEntireDriveSystemX,presentConsumptionOfEntireDriveSystemY,presentPowerConsumptionOfServoAxisY,presentPowerConsumptionOfSpindleY     
        
    def GetIntegralPower(self):
        """Gets the current total power consumption as an array.This function is not supported with the C70 or M700 series."""
        """accumulatedconsumptionOfEntireDriveSystem,fixedConsumptionCorrectionOfDriveSystem,accumulatedConsumptionOfServoAxisInDriveSystem,accumulatedRegenerationOfServoAxisInDriveSystem,accumulatedConsumptionOfSpindleInDriveSystem,accumulatedRegenerationOfSpindleInDriveSystem"""
        with self.__lock:
            self.__open()
            errcd11,accumulatedconsumptionOfEntireDriveSystemX = self.__ezcom.GetPowerConsumption(1,0)
            self.__raise_error(errcd11)
            errcd12,fixedConsumptionCorrectionOfDriveSystemX  = self.__ezcom.GetPowerConsumption(1,1)
            self.__raise_error(errcd12)
            errcd13,accumulatedConsumptionOfServoAxisInDriveSystemX  = self.__ezcom.GetPowerConsumption(1,2)
            self.__raise_error(errcd13)
            errcd14,accumulatedRegenerationOfServoAxisInDriveSystemX   = self.__ezcom.GetPowerConsumption(1,3)
            self.__raise_error(errcd14)
            errcd15,accumulatedConsumptionOfSpindleInDriveSystemX  = self.__ezcom.GetPowerConsumption(1,4)
            self.__raise_error(errcd15)
            errcd16,accumulatedRegenerationOfSpindleInDriveSystemX   = self.__ezcom.GetPowerConsumption(1,5)
            self.__raise_error(errcd16)
            errcd21,accumulatedconsumptionOfEntireDriveSystemY  = self.__ezcom.GetPowerConsumption(2,0)
            self.__raise_error(errcd21)
            errcd22,fixedConsumptionCorrectionOfDriveSystemY  = self.__ezcom.GetPowerConsumption(2,1)
            self.__raise_error(errcd22)
            errcd23,accumulatedConsumptionOfServoAxisInDriveSystemY  = self.__ezcom.GetPowerConsumption(2,2)
            self.__raise_error(errcd23)
            errcd24,accumulatedRegenerationOfServoAxisInDriveSystemY   = self.__ezcom.GetPowerConsumption(2,3)
            self.__raise_error(errcd24)
            errcd25,accumulatedConsumptionOfSpindleInDriveSystemY  = self.__ezcom.GetPowerConsumption(2,4)
            self.__raise_error(errcd25)
            errcd26,accumulatedRegenerationOfSpindleInDriveSystemY   = self.__ezcom.GetPowerConsumption(2,5)
            self.__raise_error(errcd26)
            #errcd31,accumulatedconsumptionOfEntireDriveSystem  = self.__ezcom.GetPowerConsumption(3,0)
            #errcd32,fixedConsumptionCorrectionOfDriveSystem  = self.__ezcom.GetPowerConsumption(3,1)
            #errcd34,accumulatedRegenerationOfServoAxisInDriveSystem   = self.__ezcom.GetPowerConsumption(3,3)
            #errcd35,accumulatedConsumptionOfSpindleInDriveSystem  = self.__ezcom.GetPowerConsumption(3,4)
            #errcd36,accumulatedRegenerationOfSpindleInDriveSystem   = self.__ezcom.GetPowerConsumption(3,5)
           
            #self.__raise_error(errcd31)
            #self.__raise_error(errcd32)
            #self.__raise_error(errcd33)
            #self.__raise_error(errcd34)
            #self.__raise_error(errcd35)
            #self.__raise_error(errcd36)
            return accumulatedconsumptionOfEntireDriveSystemX,fixedConsumptionCorrectionOfDriveSystemX,accumulatedConsumptionOfServoAxisInDriveSystemX,accumulatedRegenerationOfServoAxisInDriveSystemX,accumulatedConsumptionOfSpindleInDriveSystemX,accumulatedRegenerationOfSpindleInDriveSystemX,accumulatedconsumptionOfEntireDriveSystemY,fixedConsumptionCorrectionOfDriveSystemY,accumulatedConsumptionOfServoAxisInDriveSystemY,accumulatedRegenerationOfServoAxisInDriveSystemY,accumulatedConsumptionOfSpindleInDriveSystemY,accumulatedRegenerationOfSpindleInDriveSystemY
                
    


    def GetInvalidStatus(self):
        """Disabled status"""    
        """0:Disables single block stop"""
        """1:Waits for the MST command completion signal"""
        """2:Disables feed hold"""
        """3:Disables cutting override"""
        """4:Disables G09 block deceleration check"""
        with self.__lock:
            self.__open()
            errcd, disabledBit = self.__ezcom.Status_GetInvalidStatus()
            self.__raise_error(errcd)
            return disabledBit

       
        
        
        
        
        
        
    def GetCommandStatus(self):
        """Returns the operation command status with any of the following numbers"""    
        """0:Positioning (independent axis)"""
        """1:Positioning (linear)"""
        """2:Linear interpolation"""
        """3:Circular interpolation (CW)"""
        """4:Circular interpolation (CCW)"""
        """5:Helical interpolation (CW)"""
        """6:Helical interpolation (CCW)"""
        """7:Reserved"""
        """8:Reserved"""
        """9:Reserved"""
        """10:Reserved"""
        """11:Time command dwell"""
        """12:Reserved"""
        """13:1st reference position verification 2"""
        """14:2nd reference position verification 2"""
        """15:3rd reference position verification"""
        """16:4th reference position verification"""
        """17:Automatic reference position return"""
        """18:Return from the automatic reference position"""
        """19:2nd reference position return"""
        """20:3rd reference position return"""
        """21:4th reference position return"""
        """22:Skip function"""
        """23:Multi-skip function 1"""
        """24:Multi-skip function 2"""
        """25:Multi-skip function 3"""
        """26:Threading"""
        """27:Reserved"""
        """28:Reserved"""
        """29:Coordinate system setting"""

        with self.__lock:
            self.__open()
            errcd, commandStatus = self.__ezcom.Status_GetCommandStatus()
            self.__raise_error(errcd)
            

            return commandStatus
    def GetCurrentBlockByByte (self):
         with self.__lock:
            self.__open ()
            errcd, CurrentBlockByByte = self.__ezcom.Program_GetSequenceNumber(0)
            self.__raise_error (errcd)
            return CurrentBlockByByte            
    def GetCuttingMode(self):
        
        """Gets the cutting mode"""
        """1:In G01, G02, G03, G31, G33, G34, or G35 mode"""
        """0:In any of other modes"""
        with self.__lock:
            self.__open()
            errcd, cuttingMode = self.__ezcom.Status_GetCuttingMode()
            self.__raise_error(errcd)
            return cuttingMode
               
    def GetSubProLevel (self):
         with self.__lock:
            self.__open ()
            errcd, SubProLevel = self.__ezcom.Program_GetSubProLevel ()
            self.__raise_error (errcd)
            return SubProLevel
    def GetRunStatus(self):
        """Gets the operation status"""
        """Automatic operation paused is enabled only for the M700/M800 series"""
        """In reset: 0:In automatic operation "RUN" (OP) ,0:In automatic operation "START" (STL),0:In automatic operation "PAUSE" (SPL)"""
        """ Reset state Automatic operation is stopped because of the reset conditions.(All states in which the system is not operating automatically correspond to this.)"""
        """  Automatic operation stopped state Automatic operation is stopped after executing one block. (Single block stop corresponds to this.)"""
        """  Automatic operation pause state Automatic operation is stopped during the execution of one block. (The automatic operation pause (*SP) signal OFF state corresponds to this.)"""
        """* Automatic operation started state Automatic operation is actually being executed."""
        """Tool length measurement. 0: Tool length not being measured ,1: Tool length being measured"""
        """In automatic operation "run".Gets the status indicating that the system is operating automatically.0: Not operating in automatically 1: Operating automatically"""
        """Automatic operation “start”. Gets the status indicating that the system is operating automatically and that a movement command or M, S, T, B process is being executed. 0: Not starting automatic operation 1: Starting automatic operation"""
        """Automatic operation "pause" Gets the status indicating that automatic operation is paused while executing a movement command or miscellaneous command with automatic operation. 0: Automatic operation not paused 1: Automatic operation paused"""
        with self.__lock:
            self.__open()
            errcd1, toolLengthMeasurement = self.__ezcom.Status_GetRunStatus(0)
            self.__raise_error(errcd1)
            errcd2, inAutomaticOperationRun = self.__ezcom.Status_GetRunStatus(1)
            self.__raise_error(errcd2)
            errcd3, automaticOperationStart = self.__ezcom.Status_GetRunStatus(2)
            self.__raise_error(errcd3)
            errcd4, automaticOperationPause = self.__ezcom.Status_GetRunStatus(3)
            self.__raise_error(errcd4)
            
            
            
            return toolLengthMeasurement,inAutomaticOperationRun,automaticOperationStart,automaticOperationPause
        
        
        
        
        
        
        
    
    def get_drive_infomation(self):
        '''Return available drive names.
        Note: The drive name is originally obtained as "drive name: CRLF drive name: CRLF ... drive name: CRLF \ 0".
        If there are multiple drives, you need to split.
        
        Return:
            str: Drive information
        '''
        with self.__lock:
            self.__open()
            errcd, drive_info = self.__ezcom.File_GetDriveInformation()
            self.__raise_error(errcd)
            return drive_info[0: 4]

    def get_version(self):
        '''Return NC version
        
        Return:
            str: Version information
        '''
        with self.__lock:
            self.__open()
            errcd, version = self.__ezcom.System_GetVersion(1, 0)
            self.__raise_error(errcd)
            return version

    def get_current_position(self, axisno):
        '''Get current coordinate position.

        Args:
            axisno (M700.Position. *): Pass X or Y or Z as an argument.
        
        Return:
            float: Current coordinate position
        '''
        with self.__lock:
            if not isinstance(axisno, M700.Position):
                raise Exception('Specify the enumeration [M700.Position. *]')
            # in_1: The axis you want to get. 1 = x, 2 = y, 3 = z
            # pos: Current position.
            self.__open()
            errcd, pos = self.__ezcom.Position_GetCurrentPosition(axisno.value)
            self.__raise_error(errcd)
            return pos
    
    
    
    def get_run_status(self):
        '''Obtain operating status.

        Return:
            M700.RunStatus: Returns the enumeration [M700.RunStatus].
        '''
        with self.__lock:
            # in_1: Driving type. 1 = Is automatic operation in progress?
            # status: 0 = Not in automatic operation. 1 = automatic driving
            self.__open()
            errcd, status = self.__ezcom.Status_GetRunStatus(1)
            self.__raise_error(errcd)
            if M700.RunStatus.AUTO_RUN.value == status:
                return M700.RunStatus.AUTO_RUN
            else:
                return M700.RunStatus.NOT_AUTO_RUN

    def get_rpm (self):
        '''Obtain rotation speed (0 ~ [rpm]).
        
        Return:
            int: number of rotations
        '''
        with self.__lock:
            # in_1: Specify the parameter number of the specified spindle. 2 = Spindle (SR, SF) rotation speed. 0 ~ [rpm]
            # in_2: Specify the spindle number.
            # data: Returns the spindle status.
            # info: Get spindle information as UNICODE character string.
            self.__open ()
            errcd, data, info = self.__ezcom.Monitor_GetSpindleMonitor (2, 1)
            self.__raise_error (errcd)
            return data

    def get_load (self):
        '''Load (0 ~ [%]) acquisition.
        
        Return:
            int: load
        '''
        with self.__lock:
            # in_1: Specify the parameter number of the specified spindle. 3 = Load. Spindle motor load. 0 ~ [%]
            # in_2: Specify the spindle number.
            # data: Returns the spindle status.
            # info: Get spindle information as UNICODE character string.
            self.__open ()
            errcd, data, info = self.__ezcom.Monitor_GetSpindleMonitor (3, 1)
            self.__raise_error (errcd)
            return data

    def get_cycle_counter (self):
        '''
        
        '''
        with self.__lock:
            # As per docs, IIndex = 10 returns cycle counter
            self.__open ()
            errcd, data, info = self.__ezcom.Monitor_GetSpindleMonitor (10, 1)
            self.__raise_error (errcd)
            return data

    def get_var_name (self, iindex):
        with self.__lock:
            self.__open ()
            errcd, data = self.__ezcom.CommonVarialbe_GetName (iindex)
            self.__raise_error (errcd)
            return data

    def get_mgn_size (self):
        '''Magazine size acquisition.
        
        Return:
            int: magazine size
        '''
        with self.__lock:
            # size: Total number of magazine pots. Value: 0 to 360 (maximum).
            self.__open ()
            errcd, size = self.__ezcom.ATC_GetMGNSize ()
            self.__raise_error (errcd)
            return size

    def get_mgn_ready (self):
        '''Get the number of installed tool.

        Return:
            int: Tool number
        '''
        with self.__lock:
            # in_1: Specify the magazine number. Value: 1 to 2 (In the M700 / M800 series, setting a value has no effect)
            # in_2: Specify the standby state. 0 = Installed tool number, 1 = Standby 1 tool number. Same as 2,3,4 = 1.
            # toolno: Returns the tool number. Value is from 1 to 99999999 (maximum)
            self.__open ()
            errcd, toolno = self.__ezcom.ATC_GetMGNReady2 (1, 0)
            self.__raise_error (errcd)
            return toolno

    def get_toolset_size (self):
        '''Get size of toolset
        Tool set means correction value NO
        
        Return:
            int: Tool set size
        '''
        with self.__lock:
            # plSize: 200 = 200 [set]
            self.__open ()
            errcd, size = self.__ezcom.Tool_GetToolSetSize ()
            self.__raise_error (errcd)
            return size


    def Time (self):

        with self.__lock:
           
            self.__open ()
            errcd0 ,Clock1, ClockTime = self.__ezcom.Time_GetClockData()
            self.__raise_error (errcd0)
            
            """Returns the time (hour, minute, second) controlled by the programmable controller. Starts
counting when the user programmable controller device is turned ON. Refer to the
programmable controller interface manual for each model because the device number differs
depending on models.External integration time 1 (programmable controller device C70: Y314
M700/M800 series: Y704): When counting with the device turned ON"""
            errcd1, timeControlledByTheProgrammableControllerFull = self.__ezcom.Time_GetEstimateTime(0)
            self.__raise_error (errcd1)

            """Returns the time (hour, minute, second) controlled by the programmable controller. Starts
counting when the user programmable controller device is turned ON. Refer to the
programmable controller interface manual for each model because the device number differs
depending on models.External integration time 2 (programmable controller device C70: Y315
M700/M800 series: Y705): When counting with the device turned ON"""
            errcd2, TotaltimeControlledByTheProgrammableControllerFull = self.__ezcom.Time_GetEstimateTime(1)
            self.__raise_error (errcd2)

            """Gets total automatic operation time (hour, minute, second) from the automatic operation start
using memory (tape) or in MDI mode to the termination by feed hold, block stop, or reset."""
            errcd3, totalAutomaticOperationTimeFromStartToFeedHoldOrBlockStopOrReset = self.__ezcom.Time_GetStartTime() 
            self.__raise_error (errcd3)

            """Gets total processing time (hour, minute, second) from the automatic operation start using
memory (tape) or in MDI mode to the termination by M02/M30 or the reset operation.
Stops integration when the value reaches the maximum value, and retains the maximum value."""
            errcd4, totalAutomaticOperationTimeFromStartM02OrM30OrReset = self.__ezcom.Time_GetRunTime() 
            self.__raise_error (errcd4)
            
            """Gets total power-on time (hour, minute, second) from the controller power ON to OFF.
Stops integration when the value reaches the maximum value, and retains the maximum value."""
            errcd5, totalPowerOnTimeFromTheControllerPowerONtoOFF = self.__ezcom.Time_GetAliveTime()
            self.__raise_error (errcd5)
            
            
            
            
            
            return self.timeStr(str(timeControlledByTheProgrammableControllerFull)),self.timeStr(str(TotaltimeControlledByTheProgrammableControllerFull)),self.timeStr(str(totalAutomaticOperationTimeFromStartToFeedHoldOrBlockStopOrReset)),self.timeStr(str(totalAutomaticOperationTimeFromStartM02OrM30OrReset)),self.timeStr(str(totalPowerOnTimeFromTheControllerPowerONtoOFF))
    
        
    def timeStr(self,command):
        seconds=command[-2:]
        minutes=command[-4:-2]
        houres=command[:-4]
        if(minutes==''):
            minutes="00"
        if(houres==''):
            houres="00"
        return houres+":"+minutes+":"+seconds

    
    def get_tool_offset_h (self, toolset_no):
        '''Tool set number long offset value

        Return:
            int: long
        '''
        with self.__lock:
            # lType: Tool offset type 4 = Machining center type II
            # lKind: Offset type 0 = long, 1 = long wear, 2 = diameter, 3 = diameter wear
            # lToolSetNo: Tool set number
            # pdOffset As DOUBLE * (O) Offset amount
            # plNo As LONG * (O) Virtual cutting edge number
            self.__open ()
            errcd, h, plno = self.__ezcom.Tool_GetOffset2 (4, 0, toolset_no)
            self.__raise_error (errcd)
            return h
    
    def get_tool_offset_d (self, toolset_no):
        '''Long offset diameter of tool set number
        
        Return:
            int: Diameter
        '''
        with self.__lock:
            self.__open ()
            errcd, d, plno = self.__ezcom.Tool_GetOffset2 (4, 2, toolset_no)
            self.__raise_error (errcd)
            return d

    def set_tool_offset_h (self, toolset_no, h):
        '''Set tool set number offset length compensation value '''
        with self.__lock:
            # lType: Tool offset type 4 = Machining center type II
            # lKind: Offset type 0 = long, 1 = long wear, 2 = diameter, 3 = diameter wear
            # lToolSetNo: Tool set number
            # pdOffset As DOUBLE * Offset amount
            # plNo As LONG * Virtual cutting edge number
            self.__open ()
            errcd = self.__ezcom.Tool_SetOffset (4, 0, toolset_no, h, 0)
            self.__raise_error (errcd)
            errcd = self.__ezcom.Tool_SetOffset (4, 2, toolset_no, d, 0)
            self.__raise_error (errcd)

    def set_tool_offset_d (self, toolset_no, d):
        '''Set tool set number offset diameter compensation value'''
        with self.__lock:
            self.__open ()
            errcd = self.__ezcom.Tool_SetOffset (4, 2, toolset_no, d, 0)
            self.__raise_error (errcd)

    def get_program_number (self, progtype):
        '''Obtains the program number during search completion or automatic operation.

        Args:
            progtype (M700.ProgramType. *): Pass MAIN or SUB as an argument.

        Return:
            str: Program number
        '''
        with self.__lock:
            if not isinstance (progtype, M700.ProgramType):
                raise Exception ('Please specify enumeration [M700.ProgramType. *]')
            
            # in_1: 0 = Main program, 1 = Sub program
            self.__open ()
            errcd, msg = self.__ezcom.Program_GetProgramNumber2 (progtype.value)
            self.__raise_error (errcd)
            return msg





    def get_alarm (self):
        '''Get alerts.

        Return:
            str: error message
        '''
        def Clean_Alarm(input_string):
         cleaned_string = re.sub(r'/t|/n', ' ', input_string)
         cleaned_string = re.sub(r'\s+', ' ', cleaned_string)
         cleaned_string = cleaned_string.strip()
         return cleaned_string
        with self.__lock:
            # in_1: Number of message lines to retrieve. 1 to 10 (maximum)
            # in_2: Alarm type to be acquired.
            # msg: Error message
            self.__open ()
            errcd, msg = self.__ezcom.System_GetAlarm2 (3, 0)
            self.__raise_error (errcd)
            return Clean_Alarm(str(msg))

    # --- NC program file operation related ---

    def read_file (self, path):
        '''Read the file.

        Args:
            path (str): Absolute path exp) M01: \ PRG \ USER \ 100
        Return:
            bytes: Returns the read byte data.
        '''
        with self.__lock:
            self.__open ()
            try:
                errcd = self.__ezcom.File_OpenFile3 (path, M700.NCProgramFileOpenMode.READ.value)
                self.__raise_error (errcd)
                result = b''
                while True:
                    errcd, data = self.__ezcom.File_ReadFile2 (256) #The size of data to be read at one time in bytes
                    self.__raise_error (errcd)
                    result += data #VARIANT of the read byte data array
                    if len (data) <256:
                        break
                return result
            finally:
                try:
                    self.__ezcom.File_CloseFile2 ()
                except:
                    pass

    def write_file (self, path, data):
        '''Write to file.

        Args:
            path (str): Absolute path exp) M01: \ PRG \ USER \ 100
            data (bytes): Pass the data to be written as byte data
        '''
        with self.__lock:
            self.__open ()
            try:
                errcd = self.__ezcom.File_OpenFile3 (path, M700.NCProgramFileOpenMode.OVER_WRITE.value)
                self.__raise_error (errcd)
                errcd = self.__ezcom.File_WriteFile (memoryview (data)) # Array of byte data to write
                self.__raise_error (errcd)
            finally:
                try:
                    self.__ezcom.File_CloseFile2 ()
                except:
                    pass
    def delete_file (self, path):
        '''Delete the file with the specified path name.

        Args:
            path (str): Absolute path exp) M01: \ PRG \ USER \ 100
        '''
        with self.__lock:
            self.__open ()
            errcd = self.__ezcom.File_Delete2 (path)
            self.__raise_error (errcd)

    # --- NC directory operation related-

    def find_dir (self, path):
        '''Search for a file by path name.

        Args:
            path (str): Directory path exp) M01: \ PRG \ USER \
        Return:
            list: A list of search results. The contents are managed as dictionary data.
                  exp) [{'type': 'file', 'name': '100', 'size': '19', 'comment': 'BY IKEHARA'}, ...]
        '''
        with self.__lock:
            result = []
            
            try:
                self.__open ()
                
                # M01 → M unit number hexadecimal
                path = path.replace ("M01", "M {: 02X}". format (self.__unitno))

                # Get directory information in the specified path (-1 will get the string of 'directory name \ t size')
                errcd, info = self.__ezcom.File_FindDir2 (path, -1)
                self.__raise_error (errcd)
                while True:
                    # Directory information available
                    if errcd> 1:
                        dir_info = info.split ('\ t')
                        data = {
                            'type': 'folder',
                            'name': dir_info [0],
                            'size': '{:,}'. format (int (dir_info [1])),
                            'comment': None
                        }
                        result.append (data)
                    else:
                        break
                    errcd, info = self.__ezcom.File_FindNextDir2 ()
                    self.__raise_error (errcd)
                
                # Reset once
                errcd = self.__ezcom.File_ResetDir ()
                self.__raise_error (errcd)

                # Get the file information in the specified path (Get the string of 'file name \ t size \ t comment' in 5)
                errcd, info = self.__ezcom.File_FindDir2 (path, 5)
                self.__raise_error (errcd)
                while True:
                    # File information available
                    if errcd> 1:
                        dir_info = info.split ('\ t')
                        data = {
                            'type': 'file',
                            'name': dir_info [0],
                            'size': '{:,}'. format (int (dir_info [1])),
                            'comment': dir_info [2]
                        }
                        result.append (data)
                    else:
                        break
                    errcd, info = self.__ezcom.File_FindNextDir2 ()
                    self.__raise_error (errcd)
            finally:
                try:
                    errcd = self.__ezcom.File_ResetDir ()
                    self.__raise_error (errcd)
                except:
                    pass

            return result
                    
    # --- NC device operation related ---

    def __setting_dev (self, dev, data = 0):
        '''Set the device.

        Args:
            dev (str): Device specification. exp) M810, D10
            data (int): value. 1 to raise the bit, 0 to lower it.
                        In the case of read_dev, put an appropriate character as a dummy.
        '''
        data_type = 0 # 1 or 4 or 8 exp) M = 1 (bit type 1bit), D = 4 (word type 16bit)
        if dev [0] == 'M':
            data_type = 1
        elif dev[0] == 'D':
            data_type = 4
        else:
            Exception('Set M device or D device.')
        
        # in_1: Device character string (Specify the device character string array to be set as VARIANT)
        # # in_2: Data type
        # in_3: Device value array
        vDevice = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_BSTR, [dev])
        vDataType = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_I4, [data_type])
        vValue = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_I4, [data]) # 書き込むデータは現在数値のみ
        errcd = self.__ezcom.Device_SetDevice(vDevice, vDataType, vValue)
        self.__raise_error(errcd)

    def __delall_dev(self):
        '''Delete all device settings。'''
        errcd = self.__ezcom.Device_DeleteAll()
        self.__raise_error(errcd)

    def read_dev(self, dev):
        '''Device read. Read the device value set by __setting_dev.
        
        Args:
             dev (str): Device number exp) M900
         Return:
             int: Returns the value of the read data
        '''
        with self.__lock:
            self.__open()
            self.__setting_dev(dev)
            errcd, value = self.__ezcom.Device_Read() # value：デバイス値配列が返ってくる。
            self.__raise_error(errcd)
            self.__delall_dev()
            return value[0]

    def write_dev(self, dev, data):
        '''
        Device write. Write the value to the device set with __setting_dev.
        Args:
            dev (str): Device number exp) M900
            data (int): Value to write
        '''
        with self.__lock:
            self.__open()
            self.__setting_dev(dev, data)
            errcd = self.__ezcom.Device_Write()
            self.__delall_dev()
            self.__raise_error(errcd)

    # --- Error Outputs ---

    def __raise_error(self, errcd):
        '''Return the error contents as an Exception from the error code.

         If there is no error (error code is 0), do nothing.
         Error contents are registered in the dictionary in the form of {'hexadecimal error code': 'error detail message'}.
         Raises:
             Exception: error message
        '''
        __errmap = {
                "0x80a00101": "Communication line not open",
                "0x80a00104": "Double Open Error",
                "0x80a00105": "Incorrect data type of argument",
                "0x80a00106": "Invalid data range of argument",
                "0x80a00107": "Not Supported",
                "0x80a00109": "Can't open communication line",
                "0x80a0010a": "The argument is a null pointer.",
                "0x80a0010b": "Invalid data for argument",
                "0x80a0010c": "COMM port handle error",
                "0x80b00101": "Cannot reserve memory",
                "0x80b00102": "EZSocketPc error can not be obtained",
                "0x80b00201": "Incorrect mode",
                "0x80b00202": "Open file not open",
                "0x80b00203": "File already exists",
                "0x80b00204": "already open file",
                "0x80b00205": "Can't create temporary file",
                "0x80b00206": "File is not open in write mode",
                "0x80b00207": "Incorrect write data size",
                "0x80b00208": "cannot write",
                "0x80b00209": "File not opened in read mode",
                "0x80b0020a": "unreadable state",
                "0x80b0020b": "Can't create temporary file",
                "0x80b0020c": "File does not exist (read mode)",
                "0x80b0020d": "Can't open file",
                "0x80b0020e": "Invalid file path",
                "0x80b0020f": "The read file is invalid",
                "0x80b00210": "Invalid write file",
                "0x80b00301": "Incorrect host name when connecting locally due to automation call",
                "0x80b00302": "TCP / IP communication is not set",
                "0x80b00303": "Cannot set because you are already communicating",
                "0x80b00304": "There is no lower module",
                "0x80b00305": "Can not create EZSocketPc object",
                "0x80b00401": "Data does not exist",
                "0x80b00402": "Data duplication",
                "0x80b00501": "No parameter information file",
                "0x80020190": "NC card number incorrect",
                "0x80020102": "The device has not been opened",
                "0x80020132": "Invalid Command",
                "0x80020133": "Invalid communication parameter data range",
                "0x80030143": "There is a problem with the file system",
                "0x80030191": "The directory does not exist",
                "0x8003019b": "The drive does not exist",
                "0x800301a2": "Directory does not exist",
                "0x800301a8": "The drive does not exist",
                "0x80050d90": "Invalid system / axis specification",
                "0x80050d02": "Incorrect alarm type",
                "0x80050d03": "Error in communication data between NC and PC",
                "0x80041194": "Incorrect specification of life management data type",
                "0x80041195": "Setting data range over",
                "0x80041196": "Setting tool number mismatch",
                "0x80041197": "Specified tool number out of specification",
                "0x80040190": "Invalid system / axis specification",
                "0x80040191": "Blank number incorrect",
                "0x80040192": "Incorrect Subdivision Number",
                "0x80040196": "I can not fit into the buffer prepared by the application",
                "0x80040197": "Invalid data type",
                "0x8004019d": "The data can not be read",
                "0x8004019f": "write only data",
                "0x800401a0": "axis specification invalid",
                "0x800401a1": "Data number invalid",
                "0x800401a3": "No read data",
                "0x8004019a": "Invalid read data range",
                "0x80040290": "Invalid system / axis specification",
                "0x80040291": "Blank number incorrect",
                "0x80040292": "Incorrect Subdivision Number",
                "0x80040296": "I can not fit into the buffer prepared by the application",
                "0x80040297": "Incorrect data type",
                "0x8004029b": "Read only data",
                "0x8004029e": "Data can not be written",
                "0x800402a0": "axis specification invalid",
                "0x8004024d": "Secure Password Locked",
                "0x800402a2": "Format aborted due to invalid SRAM open parameter",
                "0x800402a4": "Can't register edit file (already editing)",
                "0x800402a5": "Can't release edit file",
                "0x800402a3": "No data to write to",
                "0x8004029a": "Invalid write data range",
                "0x800402a6": "Security Password not set",
                "0x800402a7": "Safety Data Integrity Check Error",
                "0x800402a9": "No data type for safety",
                "0x800402a8": "Can not write in tool data sort",
                "0x80040501": "High-speed readout not registered",
                "0x80040402": "priority specified incorrectly",
                "0x80040401": "The number of registrations has been exceeded",
                "0x80040490": "Incorrect Address",
                "0x80040491": "Blank number incorrect",
                "0x80040492": "Incorrect Subdivision Number",
                "0x80040497": "Incorrect data type",
                "0x8004049b": "Read only data",
                "0x8004049d": "The data can not be read",
                "0x8004049f": "write only data",
                "0x800404a0": "Axis specification invalid",
                "0x80040ba3": "No rethreading position set",
                "0x80030101": "Another directory is already open",
                "0x80030103": "Data size over",
                "0x80030148": "Long file name",
                "0x80030198": "Invalid file name format",
                "0x80030190": "Not Opened",
                "0x80030194": "File information read error",
                "0x80030102": "Another directory has already been opened (PC only)",
                "0x800301a0": "not open",
                "0x800301a1": "File does not exist",
                "0x800301a5": "File information read error",
                "0x80030447": "Can not copy (during operation)",
                "0x80030403": "Over registration number",
                "0x80030401": "The destination file already exists",
                "0x80030443": "There is a problem with the file system",
                "0x80030448": "Long file name",
                "0x80030498": "Invalid file name format",
                "0x80030404": "Memory capacity over",
                "0x80030491": "Directory does not exist",
                "0x8003049b": "The drive does not exist",
                "0x80030442": "File does not exist",
                "0x80030446": "Can not copy (PLC in operation)",
                "0x80030494": "The transfer source file can not be read",
                "0x80030495": "Can not write to destination file",
                "0x8003044a": "Can not copy (protect)",
                "0x80030405": "Verification error",
                "0x80030449": "does not support the matching feature",
                "0x8003044c": "Copying files",
                "0x80030490": "file not open",
                "0x8003044d": "Secure Password Locked",
                "0x8003049d": "Invalid file format",
                "0x8003049e": "The password is different",
                "0x800304a4": "File can not be created (PC only)",
                "0x800304a3": "Can't open file (PC only)",
                "0x80030402": "The destination file already exists",
                "0x800304a7": "Invalid file name format",
                "0x800304a2": "Directory does not exist",
                "0x800304a8": "The drive does not exist",
                "0x800304a1": "File does not exist",
                "0x800304a5": "The transfer source file can not be read",
                "0x800304a6": "Can not write to destination file",
                "0x80030406": "Disk capacity over",
                "0x800304a0": "file not open",
                "0x80030201": "Can't delete files",
                "0x80030242": "File does not exist",
                "0x80030243": "There is a problem with the file system",
                "0x80030247": "Can not delete (during operation)",
                "0x80030248": "long file name",
                "0x8003024a": "The file can not be deleted (protected)",
                "0x80030291": "Directory does not exist",
                "0x80030298": "Invalid file name format",
                "0x8003029b": "The drive does not exist",
                "0x80030202": "Can't delete files",
                "0x800302a7": "Invalid file name format",
                "0x800302a2": "Directory does not exist",
                "0x800302a8": "The drive does not exist",
                "0x800302a1": "File does not exist",
                "0x80030301": "New file name already exists",
                "0x80030342": "File does not exist",
                "0x80030343": "There is a problem with the file system",
                "0x80030347": "Can not rename (during operation)",
                "0x80030348": "Long file name",
                "0x8003034a": "Can not rename (Protect)",
                "0x80030391": "The directory does not exist",
                "0x80030398": "Invalid file name format",
                "0x8003039b": "The drive does not exist",
                "0x80030303": "Can't rename",
                "0x80030305": "The new and old file names are the same",
                "0x80030302": "New file name already exists",
                "0x800303a7": "Invalid file name format",
                "0x800303a2": "The directory does not exist",
                "0x800303a8": "The drive does not exist",
                "0x800303a1": "File does not exist",
                "0x80030691": "The directory does not exist",
                "0x8003069b": "The drive does not exist",
                "0x80030643": "There is a problem with the file system",
                "0x80030648": "Long file name or incorrect format",
                "0x800306a2": "Directory does not exist (PC only)",
                "0x800306a8": "Drive does not exist (PC only)",
                "0x80030701": "I can not fit into the buffer prepared by the application",
                "0x80030794": "Drive information read error",
                "0x82020001": "already open",
                "0x82020002": "Not Opened",
                "0x82020004": "card does not exist",
                "0x82020006": "Invalid Channel Number",
                "0x82020007": "The file descriptor is invalid",
                "0x8202000a": "Not Connected",
                "0x8202000b": "not closed",
                "0x82020014": "timeout",
                "0x82020015": "Invalid data",
                "0x82020016": "Canceled due to cancel request",
                "0x82020017": "Incorrect packet size",
                "0x82020018": "Ended by task end",
                "0x82020032": "The command is invalid",
                "0x82020033": "Incorrect setting data",
                "0x80060001": "Data read cache disabled",
                "0x80060090": "Incorrect Address",
                "0x80060091": "Blank number incorrect",
                "0x80060092": "Incorrect Subdivision Number",
                "0x80060097": "Incorrect data type",
                "0x8006009a": "Invalid data range",
                "0x8006009d": "The data can not be read",
                "0x8006009f": "Incorrect data type",
                "0x800600a0": "axis specification invalid",
                "0x80070140": "Can't reserve work area",
                "0x80070142": "Can't open file",
                "0x80070147": "The file can not be opened (during operation)",
                "0x80070148": "long file path",
                "0x80070149": "Not supported (CF not supported)",
                "0x80070192": "already open",
                "0x80070199": "The maximum number of open files has been exceeded",
                "0x8007019f": "Can not open during tool data sorting",
                "0x800701b0": "Security password not certified",
                "0x80070290": "File not open",
                "0x80070340": "Can't reserve work area",
                "0x80070347": "File can not be created (during operation)",
                "0x80070348": "long file path",
                "0x80070349": "Not supported (CF not supported)",
                "0x80070392": "Already generated",
                "0x80070393": "Can't create file",
                "0x80070399": "The maximum number of open files has been exceeded",
                "0x8007039b": "The drive does not exist",
                "0x80070490": "file not open",
                "0x80070494": "File information read error",
                "0x80070549": "Not writable",
                "0x80070590": "File not open",
                "0x80070595": "File write error",
                "0x80070740": "File Delete Error",
                "0x80070742": "File does not exist 3-6",
                "0x80070747": "The file can not be deleted (during operation)",
                "0x80070748": "long file path",
                "0x80070749": "Not supported (CF not supported)",
                "0x80070792": "file is open",
                "0x8007079b": "The drive does not exist",
                "0x80070842": "File does not exist",
                "0x80070843": "File that can not be renamed",
                "0x80070848": "long file path",
                "0x80070849": "Not supported (CF not supported)",
                "0x80070892": "The file is open",
                "0x80070899": "The maximum number of open files has been exceeded",
                "0x8007089b": "The drive does not exist",
                "0x80070944": "Invalid command (not supported)",
                "0x80070990": "Not Opened",
                "0x80070994": "Read error",
                "0x80070995": "Write Error",
                "0x80070996": "I can not fit into the buffer prepared by the application",
                "0x80070997": "Invalid data type",
                "0x80070949": "Not supported (CF not supported)",
                "0x80070a40": "Can't reserve work area",
                "0x80070a47": "The directory can not be opened (during operation)",
                "0x80070a48": "long file path",
                "0x80070a49": "Not supported (CF not supported)",
                "0x80070a91": "Directory does not exist",
                "0x80070a92": "already open",
                "0x80070a99": "The maximum number of open directories has been exceeded",
                "0x80070a9b": "The drive does not exist",
                "0x80070b90": "The directory has not been opened",
                "0x80070b91": "Directory does not exist",
                "0x80070b96": "I can not fit into the buffer prepared by the application",
                "0x80070d90": "The directory has not been opened",
                "0x80070e48": "long file path",
                "0x80070e49": "Supported (CF not supported)",
                "0x80070e94": "Error reading file information",
                "0x80070e99": "The maximum number of open files has been exceeded",
                "0x80070e9b": "The drive does not exist",
                "0x80070f48": "long file path",
                "0x80070f49": "Not supported (CF not supported)",
                "0x80070f94": "Error reading file information",
                "0x80070f90": "The file has not been opened",
                "0x80070f9b": "The drive does not exist",
                "0x8007099c": "Sorry, open format invalid and abort format",
                "0xf00000ff": "Invalid argument",
                "0xffffffff": "data can not be read / written"
        }

        # 0: エラーなし, 1以上: File_FindDir2時にファイル情報ありの時
        if errcd == 0 or errcd >= 1: 
            return
        
        hex_str = '0x' + format(errcd & 0xffffffff, 'x')
        msg = __errmap.get(hex_str, 'Unkown error') # 辞書に無ければUnkown error

        # '通信回線がオープンされてない'or'コネクトされていない'ならclose扱い
        if '0x80a00101' == hex_str or '0x8202000a' == hex_str:
            self.close()
        raise Exception('Error=(IP:' + self.__ip + ') ' + hex_str + ': ' + msg)
