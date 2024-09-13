
import time
import logging
import re
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from M700 import M700  # Ensure M700 library is correctly imported



state = {
    'inAutomaticOperationRunPreviousState': 0,
    'previousautomaticOperationStart': 0,
    'previousautomaticOperationPause': 0,
    'previouscurrent_program_full':"",
    'previous_pause_time': None,
    'previous_start_time': None,
    'previous_program': "",
    'previous_operation': "",
    'previous_program_full': "",
    'previous_invalid_status': None,
    'machine_on_logged': False,
    'machine_off_logged': False,
    'start_program_inserted': False,
    'start_operation_inserted': False,
    'end_program_inserted': False,
    'previous_invalid_status' : None,
    'previous_timeControlledByTheProgrammableControllerFull' : None,
    'previous_TotaltimeControlledByTheProgrammableControllerFull' : None,
    'previous_totalAutomaticOperationTimeFromStartToFeedHoldOrBlockStopOrReset' : None,
    'previous_totalAutomaticOperationTimeFromStartM02OrM30OrReset' : None,
    'previous_totalPowerOnTimeFromTheControllerPowerONtoOFF' : None,
    'previous_Fcommandfeedspeed' : None,
    'previous_Manualeffectivefeedspeed' : None,
    'previous_Synchronizationfeedspeed' : None,
    'previous_Automaticeffectivefeedspeed' : None,
    'previous_Screwleadfeedspeed' : None,
    'previous_tool' : "" , 
    'previous_Alarm' : "",
    'previous_CommandStatus' : None,
    'previous_ToolContactPositionSpeed' : None,
    'previous_purcentagespindlespeed' : None,
    'spindlespeedNormal' : 1,
}







from Database import set_program_MillingTime,set_program_executionTime,set_MachinePerDay_TotaltimeControlledByTheProgrammableControllerFull,set_MachinePerDay_totalPowerOnTimeFromTheControllerPowerONtoOFF,set_MachinePerDay_totalAutomaticOperationTimeFromStartM02OrM30OrReset,set_machine_autumaticOperationPause,set_machine_per_day_endtime,set_machine_Emmergency,insert_Alarm,set_Machine_Status,set_machine_per_day_endtime,insert_Tool,set_endtime_Tool,insert_feed_speed,set_feed_speed_endtime,set_Machine_purcentage_spindlespeed,insert_CommandStatus,set_endtime_CommandStatus,set_machine_availability,set_program_endtime,set_operation_endtime,insert_operation_starttime,set_machine_automatic_operation_start,set_machine_in_automatic_operation_mode_run,insert_program_starttime,insert_machine_per_day_starttime,set_machine_tool_length_measurement
ip="192.168.1.1"
port=683
while True:
    try:
        try:
            machine_connection = M700.get_connection(f"{ip}:{port}")
            Availability = machine_connection.Availability()
        except Exception:
            Availability = "Not Available"

        if Availability == "Available":
            if not state['machine_on_logged']:
                set_machine_availability(ip, port, True)
                machine_per_day_id = insert_machine_per_day_starttime(ip, port)
                state['machine_on_logged'] = True
                state['machine_off_logged'] = False

            while Availability == "Available":
                try:
                    Availability = machine_connection.Availability()
                    toolLengthMeasurement, inAutomaticOperationRun, automaticOperationStart, automaticOperationPause = machine_connection.GetRunStatus()
                except Exception:
                    toolLengthMeasurement, inAutomaticOperationRun, automaticOperationStart, automaticOperationPause = (0, 0, 0, 0)
                    Availability = "Not Available"
                    
                if toolLengthMeasurement != state['previous_toolLengthMeasurement'] :
                    set_machine_tool_length_measurement(ip, port, toolLengthMeasurement)
                    state['previous_toolLengthMeasurement'] = toolLengthMeasurement


                current_program_full = machine_connection.get_program_number(M700.ProgramType.MAIN)
                current_program=  current_program_full[:10]
                current_operation=current_program_full[10:]
                                    
                
                if inAutomaticOperationRun == 1 and state['inAutomaticOperationRunPreviousState'] == 0 :       
                    if state['previous_program'] != current_program:
                        
                        program_id = insert_program_starttime(ip, port, current_program)
                        state['previous_program'] = current_program
                        state['start_program_inserted'] = True
                        state['end_program_inserted'] = False
                        state['start_operation_inserted'] = False
                        
                    state['inAutomaticOperationRunPreviousState'] = 1
                    set_machine_in_automatic_operation_mode_run(ip, port, True)                
                elif inAutomaticOperationRun == 0 and state['inAutomaticOperationRunPreviousState'] == 1  :
    
                    set_machine_in_automatic_operation_mode_run(ip, port, False)
                    if state['start_program_inserted'] and not state['start_operation_inserted']:
                        set_program_endtime(program_id=program_id)
                        set_program_MillingTime(program_id,state['previous_totalAutomaticOperationTimeFromStartToFeedHoldOrBlockStopOrReset'])
                        set_program_executionTime(program_id,state['previous_timeControlledByTheProgrammableControllerFull'])
                        state['end_program_inserted'] = False
                        program_id=0
                           
                    state['inAutomaticOperationRunPreviousState'] = 0
                    
                if automaticOperationStart == 1 and state['previousautomaticOperationStart'] == 0 :
                    set_machine_automatic_operation_start(ip, port, True)

                    if state['start_program_inserted']:
                        current_operation = current_program_full[10:]
                        if state['previous_operation'] != current_operation:
                            operation_id = insert_operation_starttime(program_id, current_operation)
                            state['previous_operation'] = current_operation
                            state['start_operation_inserted'] = True
                    state['previousautomaticOperationStart'] = 1
                    
                    
                elif automaticOperationStart == 0 and state['previousautomaticOperationStart'] == 1  :
                    if state['start_program_inserted'] and state['start_operation_inserted']:
                        set_operation_endtime(operation_id)
                        state['end_operation_inserted'] = True
                        operation_id=0
                    set_machine_automatic_operation_start(ip, port, False)
                    
                    
                    
                    
                    
                if automaticOperationPause == 1 and state['previousautomaticOperationPause'] == 0 and inAutomaticOperationRun == 1 :
                    set_machine_autumaticOperationPause( ip, port, True)
                    state['previousautomaticOperationPause'] = 1
                    
                elif automaticOperationPause == 0 and state['previousautomaticOperationPause'] == 1 and inAutomaticOperationRun == 1  :
                    set_machine_autumaticOperationPause( ip, port, False)
                    state['previousautomaticOperationPause'] = 0
                    
                    
                    
                timeControlledByTheProgrammableControllerFull,TotaltimeControlledByTheProgrammableControllerFull,totalAutomaticOperationTimeFromStartToFeedHoldOrBlockStopOrReset,totalAutomaticOperationTimeFromStartM02OrM30OrReset,totalPowerOnTimeFromTheControllerPowerONtoOFF=machine_connection.Time()

                             
                if timeControlledByTheProgrammableControllerFull != state['previous_timeControlledByTheProgrammableControllerFull'] and timeControlledByTheProgrammableControllerFull !=None and timeControlledByTheProgrammableControllerFull != "00:00:00" :
                        state['previous_timeControlledByTheProgrammableControllerFull'] = timeControlledByTheProgrammableControllerFull
                   

                if totalAutomaticOperationTimeFromStartToFeedHoldOrBlockStopOrReset != state['previous_totalAutomaticOperationTimeFromStartToFeedHoldOrBlockStopOrReset'] and  totalAutomaticOperationTimeFromStartToFeedHoldOrBlockStopOrReset!=None and totalAutomaticOperationTimeFromStartToFeedHoldOrBlockStopOrReset != "00:00:00":
                        state['previous_totalAutomaticOperationTimeFromStartToFeedHoldOrBlockStopOrReset'] = totalAutomaticOperationTimeFromStartToFeedHoldOrBlockStopOrReset


                if(automaticOperationStart==1):
                    CommandStatus = machine_connection.GetCommandStatus()
                    if state['previous_CommandStatus']!= CommandStatus and CommandStatus!=None :
                        if CommandStatusid !=None:
                           set_endtime_CommandStatus(CommandStatusId=CommandStatusid)
                        CommandStatusid = insert_CommandStatus(operationId=operation_id, Commandsts=CommandStatus)             
                        state['previous_CommandStatus'] = CommandStatus
                       
                    purcentagespindlespeed = (machine_connection.get_rpm()/state["spindlespeedNormal"])*100
                    if (purcentagespindlespeed!=state['previous_purcentagespindlespeed']):
                        set_Machine_purcentage_spindlespeed(ip=ip, port=port, purcentage_spindlespeed=purcentagespindlespeed)       
                        state['previous_purcentagespindlespeed']=purcentagespindlespeed
                    
                    Fcommandfeedspeed = machine_connection.purcentageFAfeed(0)
                    Manualeffectivefeedspeed = machine_connection.purcentageFAfeed(1)
                    Synchronizationfeedspeed = machine_connection.purcentageFAfeed(2)
                    Automaticeffectivefeedspeed = machine_connection.purcentageFAfeed(3)
                    Screwleadfeedspeed = machine_connection.purcentageFAfeed(4)
                    
                        
                    if Fcommandfeedspeed != ['previous_Fcommandfeedspeed']:
                        
                        FCommandFeedSpeedid = insert_feed_speed(operation_id=operation_id, type_feed_speed="FCommandFeedSpeed", valeur=100)
                        state['previous_Fcommandfeedspeed'] = Fcommandfeedspeed
                        set_feed_speed_endtime(FeedSpeedId=FCommandFeedSpeedid, typeFeedSpeed="FCommandFeedSpeed")

                    if Manualeffectivefeedspeed != ['previous_Manualeffectivefeedspeed']:
                        ManuelEffectiveFeedSpeedid = insert_feed_speed(operation_id=operation_id, type_feed_speed="ManuelEffectiveFeedSpeed", valeur=100)
                        state['previous_Manualeffectivefeedspeed'] = Manualeffectivefeedspeed
                        set_feed_speed_endtime(FeedSpeedId=ManuelEffectiveFeedSpeedid, typeFeedSpeed="ManuelEffectiveFeedSpeed")

                    if Synchronizationfeedspeed != ['previous_Synchronizationfeedspeed']:
                        SynchronizationFeedSpeedid = insert_feed_speed(operation_id=operation_id, type_feed_speed="SynchronizationFeedSpeed", valeur=100)
                        state['previous_Synchronizationfeedspeed'] = Synchronizationfeedspeed
                        set_feed_speed_endtime(FeedSpeedId=SynchronizationFeedSpeedid, typeFeedSpeed="SynchronizationFeedSpeed")
                
                    if Automaticeffectivefeedspeed != ['previous_Automaticeffectivefeedspeed']:
                        AutomaticEffectiveFeedSpeedid = insert_feed_speed(operation_id=operation_id, type_feed_speed="AutomaticEffectiveFeedSpeed", valeur=100)
                        state['previous_Automaticeffectivefeedspeed'] = Automaticeffectivefeedspeed
                        set_feed_speed_endtime(FeedSpeedId=AutomaticEffectiveFeedSpeedid, typeFeedSpeed="AutomaticEffectiveFeedSpeed")

                    if Screwleadfeedspeed != ['previous_Screwleadfeedspeed']:
                        ScrewLeadFeedSpeedid = insert_feed_speed(operation_id=operation_id, type_feed_speed="ScrewLeadFeedSpeed", valeur=100)
                        state['previous_Screwleadfeedspeed'] = Screwleadfeedspeed
                        set_feed_speed_endtime(FeedSpeedId=ScrewLeadFeedSpeedid, typeFeedSpeed="ScrewLeadFeedSpeed")
                    current_tool=machine_connection.get_mgn_ready()
                    if current_tool != ['previous_tool'] :
                         
                        Toolid = insert_Tool(operationId=operation_id, valeurTool=current_tool)

                        set_endtime_Tool(ToolId=Toolid)
                        
                        state['previous_tool'] = current_tool

                       
                current_alarm = machine_connection.get_alarm()
               
                
                if current_alarm != ['previous_Alarm']  and current_alarm != None:

                    if "EMG" in current_alarm:
                        set_machine_Emmergency(ip, port, True)
                    else:
                        set_machine_Emmergency(ip, port, False)
                    
                    
                    insert_Alarm(operationId=operation_id, message="test message")
                    state['previous_Alarm'] = current_alarm
                    
                        


                current_invalid_status = machine_connection.GetInvalidStatus()   
                if current_invalid_status != ['previous_invalid_status']:
                   set_Machine_Status(ip,port,current_invalid_status)
                   state['previous_invalid_status'] = current_invalid_status











                if totalAutomaticOperationTimeFromStartM02OrM30OrReset != state['previous_totalAutomaticOperationTimeFromStartM02OrM30OrReset'] and  totalAutomaticOperationTimeFromStartM02OrM30OrReset!=None:
                   state['previous_totalAutomaticOperationTimeFromStartM02OrM30OrReset'] = totalAutomaticOperationTimeFromStartM02OrM30OrReset
                   

                if totalPowerOnTimeFromTheControllerPowerONtoOFF != state['previous_totalPowerOnTimeFromTheControllerPowerONtoOFF'] and   totalPowerOnTimeFromTheControllerPowerONtoOFF != None:
                   state['previous_totalPowerOnTimeFromTheControllerPowerONtoOFF'] = totalPowerOnTimeFromTheControllerPowerONtoOFF
                   
                if TotaltimeControlledByTheProgrammableControllerFull != state['previous_TotaltimeControlledByTheProgrammableControllerFull'] and  TotaltimeControlledByTheProgrammableControllerFull != None:
                   state['previous_TotaltimeControlledByTheProgrammableControllerFull'] = TotaltimeControlledByTheProgrammableControllerFull
                        
        else:
            if not state['machine_off_logged']:
                set_machine_per_day_endtime(machine_per_day_id)
                set_MachinePerDay_TotaltimeControlledByTheProgrammableControllerFull(machine_per_day_id,state['previous_TotaltimeControlledByTheProgrammableControllerFull'])
                set_MachinePerDay_totalPowerOnTimeFromTheControllerPowerONtoOFF(machine_per_day_id,state['previous_totalPowerOnTimeFromTheControllerPowerONtoOFF'])
                set_MachinePerDay_totalAutomaticOperationTimeFromStartM02OrM30OrReset(machine_per_day_id,state['previous_totalAutomaticOperationTimeFromStartM02OrM30OrReset'])
                set_machine_availability(ip, port, False)
                set_machine_in_automatic_operation_mode_run(ip, port, False)
                set_machine_automatic_operation_start(ip, port, False)
                set_machine_tool_length_measurement(ip, port, False)
                set_Machine_purcentage_spindlespeed(ip,port,purcentage_spindlespeed=0)
                set_machine_Emmergency(ip, port, False)
                if program_id !=0 :
                    set_program_endtime(program_id)
                if operation_id !=0:
                    set_operation_endtime(operation_id)
                

                state['machine_on_logged'] = False
                state['machine_off_logged'] = True

    except Exception as e:
        logging.error(f"Error: {e}")
