import time
import logging
import re
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from m700 import M700  # Ensure M700 library is correctly imported
from threading import Lock
from Database import (
    set_program_MillingTime, set_program_executionTime,
    set_MachinePerDay_TotaltimeControlledByTheProgrammableControllerFull,
    set_MachinePerDay_totalPowerOnTimeFromTheControllerPowerONtoOFF,
    set_MachinePerDay_totalAutomaticOperationTimeFromStartM02OrM30OrReset,
    set_machine_autumaticOperationPause, set_machine_per_day_endtime,
    set_machine_Emmergency, insert_Alarm, set_Machine_Status,
    insert_Tool, set_endtime_Tool, insert_feed_speed,
    set_feed_speed_endtime, set_Machine_purcentage_spindlespeed,
    insert_CommandStatus, set_endtime_CommandStatus,
    set_machine_availability, set_program_endtime,
    set_operation_endtime, insert_operation_starttime,
    set_machine_automatic_operation_start,
    set_machine_in_automatic_operation_mode_run,
    insert_program_starttime, insert_machine_per_day_starttime,
    set_machine_tool_length_measurement
)
db_lock = Lock()

state = {
    'inAutomaticOperationRunPreviousState': 0,
    'previousautomaticOperationStart': 0,
    'previousautomaticOperationPause': 0,
    'previouscurrent_program_full': "",
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
    'previous_invalid_status': None,
    'previous_timeControlledByTheProgrammableControllerFull': None,
    'previous_TotaltimeControlledByTheProgrammableControllerFull': None,
    'previous_totalAutomaticOperationTimeFromStartToFeedHoldOrBlockStopOrReset': None,
    'previous_totalAutomaticOperationTimeFromStartM02OrM30OrReset': None,
    'previous_totalPowerOnTimeFromTheControllerPowerONtoOFF': None,
    'previous_Fcommandfeedspeed': None,
    'previous_Manualeffectivefeedspeed': None,
    'previous_Synchronizationfeedspeed': None,
    'previous_Automaticeffectivefeedspeed': None,
    'previous_Screwleadfeedspeed': None,
    'previous_tool': "",
    'previous_Alarm': "",
    'previous_CommandStatus': None,
    'previous_ToolContactPositionSpeed': None,
    'previous_purcentagespindlespeed': None,
    'spindlespeedNormal': 1,
}



ip = "192.168.1.1"
port = 683

while True:
    try:
        try:
            machine_connection = M700.get_connection(f"{ip}:{port}")
            Availability = machine_connection.Availability()
        except Exception:
            Availability = "Not Available"

        if Availability == "Available":
            if not state['machine_on_logged']:
                with db_lock:
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

                if toolLengthMeasurement != state['previous_toolLengthMeasurement']:
                    with db_lock:
                        set_machine_tool_length_measurement(ip, port, toolLengthMeasurement)
                    state['previous_toolLengthMeasurement'] = toolLengthMeasurement

                current_program_full = machine_connection.get_program_number(M700.ProgramType.MAIN)

                if current_program_full == "MDI.PRG":
                    with db_lock:
                        program_id = insert_program_starttime(ip, port, current_program_full)
                    while current_program_full == "MDI.PRG":
                        current_program_full = machine_connection.get_program_number(M700.ProgramType.MAIN)
                    with db_lock:
                        set_program_endtime(program_id=program_id)

                else:
                    current_program = current_program_full[:10]
                    current_operation = current_program_full[10:]

                    if inAutomaticOperationRun == 1 and state['inAutomaticOperationRunPreviousState'] == 0:
                        if state['previous_program'] != current_program:
                            with db_lock:
                                program_id = insert_program_starttime(ip, port, current_program)
                            state['previous_program'] = current_program
                            state['start_program_inserted'] = True
                            state['end_program_inserted'] = False
                            state['start_operation_inserted'] = False

                        state['inAutomaticOperationRunPreviousState'] = 1
                        with db_lock:
                            set_machine_in_automatic_operation_mode_run(ip, port, True)

                    elif inAutomaticOperationRun == 0 and state['inAutomaticOperationRunPreviousState'] == 1:
                        with db_lock:
                            set_machine_in_automatic_operation_mode_run(ip, port, False)
                        if state['start_program_inserted'] and not state['start_operation_inserted']:
                            with db_lock:
                                set_program_endtime(program_id=program_id)
                                set_program_MillingTime(program_id, state['previous_totalAutomaticOperationTimeFromStartToFeedHoldOrBlockStopOrReset'])
                                set_program_executionTime(program_id, state['previous_timeControlledByTheProgrammableControllerFull'])
                            state['end_program_inserted'] = False
                            program_id = 0

                        state['inAutomaticOperationRunPreviousState'] = 0

                    if automaticOperationStart == 1 and state['previousautomaticOperationStart'] == 0:
                        with db_lock:
                            set_machine_automatic_operation_start(ip, port, True)

                        if state['start_program_inserted']:
                            current_operation = current_program_full[10:]
                            if state['previous_operation'] != current_operation:
                                with db_lock:
                                    operation_id = insert_operation_starttime(program_id, current_operation)
                                state['previous_operation'] = current_operation
                                state['start_operation_inserted'] = True
                        state['previousautomaticOperationStart'] = 1

                    elif automaticOperationStart == 0 and state['previousautomaticOperationStart'] == 1:
                        if state['start_program_inserted'] and state['start_operation_inserted']:
                            with db_lock:
                                set_operation_endtime(operation_id)
                            state['end_operation_inserted'] = True
                            operation_id = 0
                        with db_lock:
                            set_machine_automatic_operation_start(ip, port, False)

                    if automaticOperationPause == 1 and state['previousautomaticOperationPause'] == 0 and inAutomaticOperationRun == 1:
                        with db_lock:
                            set_machine_autumaticOperationPause(ip, port, True)
                        state['previousautomaticOperationPause'] = 1

                    elif automaticOperationPause == 0 and state['previousautomaticOperationPause'] == 1 and inAutomaticOperationRun == 1:
                        with db_lock:
                            set_machine_autumaticOperationPause(ip, port, False)
                        state['previousautomaticOperationPause'] = 0

                    timeControlledByTheProgrammableControllerFull, TotaltimeControlledByTheProgrammableControllerFull, totalAutomaticOperationTimeFromStartToFeedHoldOrBlockStopOrReset, totalAutomaticOperationTimeFromStartM02OrM30OrReset, totalPowerOnTimeFromTheControllerPowerONtoOFF = machine_connection.Time()

                    if timeControlledByTheProgrammableControllerFull != state['previous_timeControlledByTheProgrammableControllerFull'] and timeControlledByTheProgrammableControllerFull is not None and timeControlledByTheProgrammableControllerFull != "00:00:00":
                        state['previous_timeControlledByTheProgrammableControllerFull'] = timeControlledByTheProgrammableControllerFull

                    if totalAutomaticOperationTimeFromStartToFeedHoldOrBlockStopOrReset != state['previous_totalAutomaticOperationTimeFromStartToFeedHoldOrBlockStopOrReset'] and totalAutomaticOperationTimeFromStartToFeedHoldOrBlockStopOrReset is not None and totalAutomaticOperationTimeFromStartToFeedHoldOrBlockStopOrReset != "00:00:00":
                        state['previous_totalAutomaticOperationTimeFromStartToFeedHoldOrBlockStopOrReset'] = totalAutomaticOperationTimeFromStartToFeedHoldOrBlockStopOrReset

                    if automaticOperationStart == 1:
                        CommandStatus = machine_connection.GetCommandStatus()
                        if state['previous_CommandStatus'] != CommandStatus and CommandStatus is not None:
                            if CommandStatusid is not None:
                                with db_lock:
                                    set_endtime_CommandStatus(CommandStatusId=CommandStatusid)
                            with db_lock:
                                CommandStatusid = insert_CommandStatus(operationId=operation_id, Commandsts=CommandStatus)
                            state['previous_CommandStatus'] = CommandStatus

                        purcentagespindlespeed = (machine_connection.get_rpm() / state["spindlespeedNormal"]) * 100
                        if purcentagespindlespeed != state['previous_purcentagespindlespeed']:
                            with db_lock:
                                set_Machine_purcentage_spindlespeed(ip, port, purcentagespindlespeed)
                            state['previous_purcentagespindlespeed'] = purcentagespindlespeed

                    current_tool=machine_connection.get_mgn_ready()
                    if current_tool != state['previous_tool']:
                        if Toolid is not None:
                            with db_lock:
                                set_endtime_Tool(Toolid)
                        with db_lock:
                            Toolid = insert_Tool(operationId=operation_id, ToolName=current_tool)
                        state['previous_tool'] = toolLengthMeasurement

                    Alarm = machine_connection.Alarm()

                    if Alarm != state['previous_Alarm']:
                        with db_lock:
                            insert_Alarm(ip, port, Alarm)
                        state['previous_Alarm'] = Alarm
                if totalAutomaticOperationTimeFromStartM02OrM30OrReset != state['previous_totalAutomaticOperationTimeFromStartM02OrM30OrReset'] and  totalAutomaticOperationTimeFromStartM02OrM30OrReset!=None:
                   state['previous_totalAutomaticOperationTimeFromStartM02OrM30OrReset'] = totalAutomaticOperationTimeFromStartM02OrM30OrReset
                   

                if totalPowerOnTimeFromTheControllerPowerONtoOFF != state['previous_totalPowerOnTimeFromTheControllerPowerONtoOFF'] and   totalPowerOnTimeFromTheControllerPowerONtoOFF != None:
                   state['previous_totalPowerOnTimeFromTheControllerPowerONtoOFF'] = totalPowerOnTimeFromTheControllerPowerONtoOFF
                   
                if TotaltimeControlledByTheProgrammableControllerFull != state['previous_TotaltimeControlledByTheProgrammableControllerFull'] and  TotaltimeControlledByTheProgrammableControllerFull != None:
                   state['previous_TotaltimeControlledByTheProgrammableControllerFull'] = TotaltimeControlledByTheProgrammableControllerFull
                        
                time.sleep(1)

            with db_lock:
                set_machine_availability(ip, port, False)
                set_machine_per_day_endtime(ip, port)
                set_MachinePerDay_TotaltimeControlledByTheProgrammableControllerFull(machine_per_day_id,state['previous_TotaltimeControlledByTheProgrammableControllerFull'])
                set_MachinePerDay_totalPowerOnTimeFromTheControllerPowerONtoOFF(machine_per_day_id,state['previous_totalPowerOnTimeFromTheControllerPowerONtoOFF'])
                set_MachinePerDay_totalAutomaticOperationTimeFromStartM02OrM30OrReset(machine_per_day_id,state['previous_totalAutomaticOperationTimeFromStartM02OrM30OrReset'])
                set_machine_in_automatic_operation_mode_run(ip, port, False)
                set_machine_automatic_operation_start(ip, port, False)
                set_machine_tool_length_measurement(ip, port, False)
                set_Machine_purcentage_spindlespeed(ip,port,purcentage_spindlespeed=0)
                set_machine_Emmergency(ip, port, False)
                if program_id !=0 :
                    set_program_endtime(program_id)
                if operation_id !=0:
                    set_operation_endtime(operation_id)
            state['machine_off_logged'] = True
            state['machine_on_logged'] = False

        time.sleep(5)
    except Exception as e:
        logging.error(f"Error in monitoring loop: {e}")
        time.sleep(5)
