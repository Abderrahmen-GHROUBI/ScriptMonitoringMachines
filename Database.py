from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import time
from config import config

Base = declarative_base()

# Define the database models
class Machine(Base):
    __tablename__ = 'Machines'
    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String(45), unique=True, index=True)
    port = Column(Integer)  # Port number used by the machine
    availability = Column(Boolean, default=False)  # Indicates if the machine is available
    Emmergency = Column(Boolean, default=False)
    toolLengthMeasurement = Column(Boolean, default=False)  # Tool length measurement status
    inAutomaticOperationModeRun = Column(Boolean, default=False)  # Status of automatic operation mode
    automaticOperationStart = Column(Boolean, default=False)  # Indicates if automatic operation has started
    autumaticOperationPause = Column(Boolean, default=False)
    purcentageSpindlespeed =Column (Integer,default = None)#a ajouter
    Alarm = Column (String(80))
    Status = Column (Integer,default = None)# a ajouter 
class MachinePerDay(Base):
    __tablename__ = 'Machine_per_day'
    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(Integer, ForeignKey('Machines.id'))  # Foreign key to the Machines table
    start_time = Column(DateTime)  # Start time of the machine's operation
    end_time = Column(DateTime, default=None)  # End time of the machine's operation
    totalAutomaticOperationTimeFromStartM02OrM30OrReset=Column(String(30), default=None)
    totalPowerOnTimeFromTheControllerPowerONtoOFF=Column(String(30), default=None)
    TotaltimeControlledByTheProgrammableControllerFull=Column(String(30), default=None)
    numberOfStartsStops = Column (Integer,default = None)
    numberOfPrograms = Column (Integer,default = None)
    numberOfOperations = Column (Integer,default = None)
    numberOfAlarms = Column (Integer,default = None)
    
class Program(Base):
    __tablename__ = 'Programs'
    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(Integer, ForeignKey('Machines.id'))  # Foreign key to the Machines table
    program_number = Column(String(50))  # Identifier for the program
    start_time = Column(DateTime)  # Start time of the program
    end_time = Column(DateTime, default=None)  # End time of the program
    executionTime = Column(String, default=None) 
    millingTime = Column(String, default=None) 

class Operation(Base):
    __tablename__ = 'Operations'
    id = Column(Integer, primary_key=True, index=True)
    program_id = Column(Integer, ForeignKey('Programs.id'))  # Foreign key to the Programs table
    operation_number = Column(String(50))  # Identifier for the operation
    start_time = Column(DateTime)  # Start time of the operation
    end_time = Column(DateTime, default=None)  # End time of the operation

    
class ManuelEffectiveFeedSpeed(Base):
    __tablename__ = 'Manueleffectivefeedspeed'
    id = Column(Integer, primary_key=True, index=True)
    operation_id = Column (Integer, ForeignKey('Operations.id'))
    Manueleffectivefeedspeed = Column (Integer)
    start_time = Column(DateTime)
    end_time = Column(DateTime, default = None)

class FCommandFeedSpeed(Base):
    __tablename__ = 'Fcommandfeedspeed'
    id = Column(Integer, primary_key=True, index=True)
    operation_id = Column (Integer, ForeignKey('Operations.id'))
    Fcommandfeedspeed = Column (Integer)
    start_time = Column(DateTime)
    end_time = Column(DateTime, default = None)
    
    
class SynchronizationFeedSpeed(Base):
    __tablename__ = 'Synchronizationfeedspeed'
    id = Column(Integer, primary_key=True, index=True)
    operation_id = Column (Integer, ForeignKey('Operations.id'))
    Synchronizationfeedspeed = Column (Integer)
    start_time = Column(DateTime)
    end_time = Column(DateTime, default = None)

class AutomaticEffectiveFeedSpeed(Base):
    __tablename__ = 'Automaticeffectivefeedspeed'
    id = Column(Integer, primary_key=True, index=True)
    operation_id = Column (Integer, ForeignKey('Operations.id'))
    Automaticeffectivefeedspeed = Column (Integer)
    start_time = Column(DateTime)
    end_time = Column(DateTime, default = None)

class ScrewLeadFeedSpeed(Base):
    __tablename__ = 'Screwleadfeedspeed'
    id = Column(Integer, primary_key=True, index=True)
    operation_id = Column (Integer, ForeignKey('Operations.id'))
    Screwleadfeedspeed = Column (Integer)
    start_time = Column(DateTime)
    end_time = Column(DateTime, default = None)
    
class Tools(Base):
    __tablename__ = 'Tools'
    id = Column(Integer, primary_key=True, index=True)
    operation_id = Column (Integer, ForeignKey('Operations.id'))
    Tool = Column (Integer)
    start_time = Column(DateTime)
    end_time = Column(DateTime, default = None)
    
class Alarms(Base):
    __tablename__ = 'Alarms'
    id = Column(Integer, primary_key=True, index=True)
    operation_id = Column (Integer, ForeignKey('Operations.id'))
    Alarm = Column (String(80))
    Time = Column(DateTime)
    
class Commandstatus(Base):
    __tablename__ = 'Commandstatus'
    id = Column(Integer, primary_key=True, index=True)
    operation_id = Column (Integer, ForeignKey('Operations.id'))
    Commandsts = Column (Integer)
    start_time = Column(DateTime)
    end_time = Column(DateTime, default = None)    
    
config = config()
connection_url = (
    f"mssql+pyodbc://{config['database']['username']}:{config['database']['password']}@"
    f"{config['database']['server']}/{config['database']['database']}?driver={config['database']['driver']}"
)

# Create the database engine
engine = create_engine(connection_url)
Base.metadata.create_all(engine)  # Create tables in the database

Session = sessionmaker(bind=engine)

# Functions for interacting with the database
def set_machine_availability(ip, port, availability):
    """Update or add a machine's availability status."""
    session = Session()
    try:
        machine = session.query(Machine).filter_by(ip=ip, port=port).first()
        if not machine:
            machine = Machine(ip=ip, port=port, availability=availability)
            session.add(machine)
        else:
            machine.availability = availability
        session.commit()
    finally:
        session.close()

def insert_machine_per_day_starttime(ip, port):
    """Insert a new record for the machine's daily operation start time."""
    session = Session()
    try:
        machine = session.query(Machine).filter_by(ip=ip, port=port).first()
        if machine:
            machine_per_day = MachinePerDay(machine_id=machine.id, start_time=datetime.now())
            session.add(machine_per_day)
            session.commit()
            return machine_per_day.id  
    finally:
        session.close()

def set_machine_per_day_endtime(machineperday_id):
    """Update the machine's end time for a specific day."""
    session = Session()
    try:
        machine_per_day = session.query(MachinePerDay).filter_by(id=machineperday_id).first()
        if machine_per_day:
            machine_per_day.end_time = datetime.now()
            session.commit()
    finally:
        session.close()

def set_machine_tool_length_measurement(ip, port, tool_length_measurement):
    """Update the tool length measurement status for a machine."""
    session = Session()
    try:
        machine = session.query(Machine).filter_by(ip=ip, port=port).first()
        if machine:
            machine.toolLengthMeasurement = tool_length_measurement
            session.commit()
    finally:
        session.close()
      
def set_machine_autumaticOperationPause(ip, port, autumatiOperationPause):
    """Update the tool length measurement status for a machine."""
    session = Session()
    try:
        machine = session.query(Machine).filter_by(ip=ip, port=port).first()
        if machine:
            machine.autumaticOperationPause = autumatiOperationPause
            session.commit()
    finally:
        session.close()  
def set_machine_Emmergency(ip, port, emg):
    """Update the tool length measurement status for a machine."""
    session = Session()
    try:
        machine = session.query(Machine).filter_by(ip=ip, port=port).first()
        if machine:
            machine.Emmergency = emg
            session.commit()
    finally:
        session.close() 
def insert_program_starttime(ip, port, program_number):
    """Insert a new program with its start time."""
    session = Session()
    try:
        machine = session.query(Machine).filter_by(ip=ip, port=port).first()
        if machine:
            program = Program(machine_id=machine.id, program_number=program_number, start_time=datetime.now())
            session.add(program)
            session.commit()
            return program.id  
    finally:
        session.close()
def set_program_endtime(program_id):
    """Set the end time for a program."""
    session = Session()
    try:
        program = session.query(Program).filter_by(id=program_id).first()
        if program:
            program.end_time = datetime.now()
            session.commit()
    finally:
        session.close()
def set_program_executionTime(program_id,executiontime):
    """Set the end time for a program."""
    session = Session()
    try:
        program = session.query(Program).filter_by(id=program_id).first()
        if program:
            program.executionTime = executiontime
            session.commit()
    finally:
        session.close()
def set_program_MillingTime(program_id,Millingtime):
    """Set the end time for a program."""
    session = Session()
    try:
        program = session.query(Program).filter_by(id=program_id).first()
        if program:
            program.millingTime = Millingtime
            session.commit()
    finally:
        session.close()
def set_MachinePerDay_TotaltimeControlledByTheProgrammableControllerFull(machine_per_day_id,T):
    """Update the number of start/stop events for a machine."""
    session = Session()
    try:
        machine_per_day = session.query(MachinePerDay).filter_by(id=machine_per_day_id).first()
        if machine_per_day:
            machine_per_day.TotaltimeControlledByTheProgrammableControllerFull = T
            session.commit()
    finally:
        session.close()     
def set_MachinePerDay_totalPowerOnTimeFromTheControllerPowerONtoOFF(machine_per_day_id,M):
    """Update the number of start/stop events for a machine."""
    session = Session()
    try:
        machine_per_day = session.query(MachinePerDay).filter_by(id=machine_per_day_id).first()
        if machine_per_day:
            machine_per_day.totalPowerOnTimeFromTheControllerPowerONtoOFF = M
            session.commit()
    finally:
        session.close()      
def set_MachinePerDay_totalAutomaticOperationTimeFromStartM02OrM30OrReset(machine_per_day_id,N):
    """Update the number of start/stop events for a machine."""
    session = Session()
    try:
        machine_per_day = session.query(MachinePerDay).filter_by(id=machine_per_day_id).first()
        if machine_per_day:
            machine_per_day.totalAutomaticOperationTimeFromStartM02OrM30OrReset = N
            session.commit()
    finally:
        session.close()    
        
def set_machine_in_automatic_operation_mode_run(ip, port, in_automatic_operation_mode_run):
    """Update the automatic operation run status for a machine."""
    session = Session()
    try:
        machine = session.query(Machine).filter_by(ip=ip, port=port).first()
        if machine:
            machine.inAutomaticOperationModeRun = in_automatic_operation_mode_run
            session.commit()
    finally:
        session.close()

def set_machine_automatic_operation_start(ip, port, automatic_operation_start):
    """Update the automatic operation start status for a machine."""
    session = Session()
    try:
        machine = session.query(Machine).filter_by(ip=ip, port=port).first()
        if machine:
            machine.automaticOperationStart = automatic_operation_start
            session.commit()
    finally:
        session.close()

def insert_operation_starttime(program_id, operation_number):
    """Insert a new operation with its start time."""
    session = Session()
    try:
        operation = Operation(program_id=program_id, operation_number=operation_number, start_time=datetime.now())
        session.add(operation)
        session.commit()
        return operation.id 
    finally:
        session.close()

def set_operation_endtime(operation_id):
    """Set the end time for an operation."""
    session = Session()
    try:
        operation = session.query(Operation).filter_by(id=operation_id).first()
        if operation:
            operation.end_time = datetime.now()
            session.commit()
    finally:
        session.close()
        
        
def set_Machine_purcentage_spindlespeed(ip,port,purcentage_spindlespeed):
    """Update the purcentage spindlespeed for a machine."""
    session = Session()
    try:
        machine = session.query(Machine).filter_by(ip=ip, port=port).first()
        if machine:
            machine.purcentageSpindlespeed = purcentage_spindlespeed
            session.commit()
    finally:
        session.close()
def set_Machine_Status(ip,port,Status):
    """Update the Status for a machine."""
    session = Session()
    try:
        machine = session.query(Machine).filter_by(ip=ip, port=port).first()
        if machine:
            machine.Status = Status
            session.commit()
    finally:
        session.close()      
       
        
def set_MachinePerDay_numberOfstartsstops(machine_per_day_id):
    """Update the number of start/stop events for a machine."""
    session = Session()
    try:
        machine_per_day = session.query(MachinePerDay).filter_by(id=machine_per_day_id).first()
        if machine_per_day:
            machine_per_day.numberOfStartsStops = (machine_per_day.numberOfStartsStops or 0) + 1
            session.commit()
    finally:
        session.close()

def set_MachinePerDay_numberOfPrograms(machine_per_day_id):
    """Update the number of programs for a machine."""
    session = Session()
    try:
        machine_per_day = session.query(MachinePerDay).filter_by(id=machine_per_day_id).first()
        if machine_per_day:
            machine_per_day.numberOfPrograms = (machine_per_day.numberOfPrograms or 0) + 1
            session.commit()
    finally:
        session.close()


def set_MachinePerDay_numberOfOperations(machine_per_day_id):
    """Update the number of operations for a machine."""
    session = Session()
    try:
        machine_per_day = session.query(MachinePerDay).filter_by(id=machine_per_day_id).first()
        if machine_per_day:
            machine_per_day.numberOfOperations = (machine_per_day.numberOfOperations or 0) + 1
            session.commit()
    finally:
        session.close()

def set_MachinePerDay_numberOfAlarms(machine_per_day_id):
    """Update the number of alarms for a machine."""
    session = Session()
    try:
        machine_per_day = session.query(MachinePerDay).filter_by(id=machine_per_day_id).first()
        if machine_per_day:
            machine_per_day.numberOfAlarms = (machine_per_day.numberOfAlarms or 0) + 1
            session.commit()
    finally:
        session.close()




def insert_feed_speed(operation_id, type_feed_speed, valeur):
    """Insert a new feed speed with its start time."""
    session = Session()
    try:
        operation = session.query(Operation).filter_by(id=operation_id).first()
        if operation:
            feed_speed_entry = None
            if type_feed_speed == "ManuelEffectiveFeedSpeed":
                feed_speed_entry = ManuelEffectiveFeedSpeed(operation_id=operation_id, Manueleffectivefeedspeed=valeur, start_time=datetime.now())
            elif type_feed_speed == "FCommandFeedSpeed":
                feed_speed_entry = FCommandFeedSpeed(operation_id=operation_id, Fcommandfeedspeed=valeur, start_time=datetime.now())
            elif type_feed_speed == "SynchronizationFeedSpeed":
                feed_speed_entry = SynchronizationFeedSpeed(operation_id=operation_id, Synchronizationfeedspeed=valeur, start_time=datetime.now())
            elif type_feed_speed == "AutomaticEffectiveFeedSpeed":
                feed_speed_entry = AutomaticEffectiveFeedSpeed(operation_id=operation_id, Automaticeffectivefeedspeed=valeur, start_time=datetime.now())
            elif type_feed_speed == "ScrewLeadFeedSpeed":
                feed_speed_entry = ScrewLeadFeedSpeed(operation_id=operation_id, Screwleadfeedspeed=valeur, start_time=datetime.now())
            
            if feed_speed_entry:
                session.add(feed_speed_entry)
                session.commit()
                return feed_speed_entry.id
    finally:
        session.close()


def set_feed_speed_endtime(FeedSpeedId,typeFeedSpeed):
    """Set the end time for a feed speed ."""
    session = Session()
    
    try:
        
        
            if typeFeedSpeed == "ManuelEffectiveFeedSpeed" :
                
                Manueleffectivefeedspeed = session.query(ManuelEffectiveFeedSpeed).filter_by(id=FeedSpeedId).first()
                Manueleffectivefeedspeed.end_time = datetime.now()
          
           
            elif typeFeedSpeed == "FCommandFeedSpeed" :  
                
                Fcommandfeedspeed = session.query(FCommandFeedSpeed).filter_by(id=FeedSpeedId).first()
                Fcommandfeedspeed.end_time = datetime.now()
    
          
            elif typeFeedSpeed == "SynchronizationFeedSpeed" :  
                
                Synchronizationfeedspeed = session.query(SynchronizationFeedSpeed).filter_by(id=FeedSpeedId).first()
                Synchronizationfeedspeed.end_time = datetime.now()
    
                       
            elif typeFeedSpeed == "AutomaticEffectiveFeedSpeed" :  
                
                Automaticeffectivefeedspeed = session.query(AutomaticEffectiveFeedSpeed).filter_by(id=FeedSpeedId).first()   
                Automaticeffectivefeedspeed.end_time = datetime.now()
         
                
            elif typeFeedSpeed == "ScrewLeadFeedSpeed" :     
                
                Screwleadfeedspeed = session.query(ScrewLeadFeedSpeed).filter_by(id=FeedSpeedId).first()
                Screwleadfeedspeed.end_time = datetime.now()
                
            
            session.commit()
            
    finally:
        session.close()


def insert_Alarm(operationId, message):
    """Insert a new Alarm."""
    session = Session()
    try:
        operation = session.query(Operation).filter_by(id=operationId).first()
        if operation:
            Alarm = Alarms(operation_id=operationId, Alarm=message ,Time=datetime.now())
            session.add(Alarm)
            session.commit()
            
    finally:
        session.close()   
        



def insert_CommandStatus(operationId, Commandsts):
    """Insert a new Command status."""
    session = Session()
    try:
        operation = session.query(Operation).filter_by(id=operationId).first()
        if operation:
            commandstatus = Commandstatus(operation_id=operationId, Commandsts=Commandsts ,start_time=datetime.now())
            session.add(commandstatus)
            session.commit()
            return commandstatus.id
            
    finally:
        session.close()
            
def set_endtime_CommandStatus(CommandStatusId):
    """Set end time commandstatus."""
    session = Session()
    try:
        commandstatus = session.query(Commandstatus).filter_by(id=CommandStatusId).first()
        if commandstatus:
           commandstatus.end_time = datetime.now()
           session.commit()      
    finally:
        session.close()    
        
        
def insert_Tool(operationId, valeurTool):
    """Insert a new Command status."""
    session = Session()
    try:
        operation = session.query(Operation).filter_by(id=operationId).first()
        if operation:
            Tool = Tools(operation_id=operationId, Tool=valeurTool ,start_time=datetime.now())
            session.add(Tool)
            session.commit()
            return Tool.id
            
    finally:
        session.close()
         
def set_endtime_Tool(ToolId):
    """Set end time commandstatus."""
    session = Session()
    try:
        Tool = session.query(Tools).filter_by(id=ToolId).first()
        if Tool:
           Tool.end_time = datetime.now()
           session.commit()      
    finally:
        session.close()    
        
        
from time import sleep

if __name__ == "__main__":
    ip = "192.168.2.4"
    port = 1234
    program_number = "2024-001-002257"
    operation_number = "OP00133388"

    print("Starting workflow for Machine...")

    set_machine_availability(ip, port, False)
    print(f"Machine with IP {ip} and port {port} set availability to False.")


    set_machine_availability(ip, port, True)
    print(f"Machine with IP {ip} and port {port} set availability to True.")


    machine_per_day_id = insert_machine_per_day_starttime(ip, port)
    print(f"Inserted machine per day start time for machine with IP {ip} and port {port}, ID {machine_per_day_id}.")


    set_machine_in_automatic_operation_mode_run(ip, port, True)
    print(f"Machine with IP {ip} and port {port} set automatic operation mode to True.")


    program_id = insert_program_starttime(ip, port, program_number)
    print(f"Program {program_number} started for machine with IP {ip} and port {port}, Program ID {program_id}.")


    set_machine_automatic_operation_start(ip, port, True)
    print(f"Machine with IP {ip} and port {port} set automatic operation start to True.")


    operation_id = insert_operation_starttime(program_id, operation_number)
    print(f"Operation {operation_number} started under program ID {program_id}, Operation ID {operation_id}.")


    set_Machine_purcentage_spindlespeed(ip=ip, port=port, purcentage_spindlespeed=100)
    print(f"Spindle speed percentage set to 100% for machine with IP {ip} and port {port}.")


    set_Machine_Status(ip=ip, port=port, Status=1)
    print(f"Machine status set to 1 (running) for machine with IP {ip} and port {port}.")


    set_MachinePerDay_numberOfstartsstops(machine_per_day_id=machine_per_day_id)
    print(f"Updated number of starts/stops for machine per day ID {machine_per_day_id}.")


    set_MachinePerDay_numberOfPrograms(machine_per_day_id=machine_per_day_id)
    print(f"Updated number of programs for machine per day ID {machine_per_day_id}.")


    set_MachinePerDay_numberOfOperations(machine_per_day_id=machine_per_day_id)
    print(f"Updated number of operations for machine per day ID {machine_per_day_id}.")


    set_MachinePerDay_numberOfAlarms(machine_per_day_id=machine_per_day_id)
    print(f"Updated number of alarms for machine per day ID {machine_per_day_id}.")


    ManuelEffectiveFeedSpeedid = insert_feed_speed(operation_id=operation_id, type_feed_speed="ManuelEffectiveFeedSpeed", valeur=100)
    print(f"Inserted ManuelEffectiveFeedSpeed with value 100 for operation ID {operation_id}.")


    FCommandFeedSpeedid = insert_feed_speed(operation_id=operation_id, type_feed_speed="FCommandFeedSpeed", valeur=100)
    print(f"Inserted FCommandFeedSpeed with value 100 for operation ID {operation_id}.")


    SynchronizationFeedSpeedid = insert_feed_speed(operation_id=operation_id, type_feed_speed="SynchronizationFeedSpeed", valeur=100)
    print(f"Inserted SynchronizationFeedSpeed with value 100 for operation ID {operation_id}.")
  

    AutomaticEffectiveFeedSpeedid = insert_feed_speed(operation_id=operation_id, type_feed_speed="AutomaticEffectiveFeedSpeed", valeur=100)
    print(f"Inserted AutomaticEffectiveFeedSpeed with value 100 for operation ID {operation_id}.")


    ScrewLeadFeedSpeedid = insert_feed_speed(operation_id=operation_id, type_feed_speed="ScrewLeadFeedSpeed", valeur=100)
    print(f"Inserted ScrewLeadFeedSpeed with value 100 for operation ID {operation_id}.")


    set_feed_speed_endtime(FeedSpeedId=ManuelEffectiveFeedSpeedid, typeFeedSpeed="ManuelEffectiveFeedSpeed")
    print(f"Set end time for ManuelEffectiveFeedSpeed with FeedSpeedId {ManuelEffectiveFeedSpeedid}.")


    set_feed_speed_endtime(FeedSpeedId=FCommandFeedSpeedid, typeFeedSpeed="FCommandFeedSpeed")
    print(f"Set end time for FCommandFeedSpeed with FeedSpeedId {FCommandFeedSpeedid}.")
 

    set_feed_speed_endtime(FeedSpeedId=SynchronizationFeedSpeedid, typeFeedSpeed="SynchronizationFeedSpeed")
    print(f"Set end time for SynchronizationFeedSpeed with FeedSpeedId {SynchronizationFeedSpeedid}.")


    set_feed_speed_endtime(FeedSpeedId=AutomaticEffectiveFeedSpeedid, typeFeedSpeed="AutomaticEffectiveFeedSpeed")
    print(f"Set end time for AutomaticEffectiveFeedSpeed with FeedSpeedId {AutomaticEffectiveFeedSpeedid}.")


    set_feed_speed_endtime(FeedSpeedId=ScrewLeadFeedSpeedid, typeFeedSpeed="ScrewLeadFeedSpeed")
    print(f"Set end time for ScrewLeadFeedSpeed with FeedSpeedId {ScrewLeadFeedSpeedid}.")


    insert_Alarm(operationId=operation_id, message="test message")
    print(f"Inserted alarm with message 'test message' for operation ID {operation_id}.")


    CommandStatusid = insert_CommandStatus(operationId=operation_id, Commandsts=1)
    print(f"Inserted CommandStatus 1 for operation ID {operation_id}.")


    set_endtime_CommandStatus(CommandStatusId=CommandStatusid)
    print(f"Set end time for CommandStatusId {CommandStatusid}.")


    Toolid = insert_Tool(operationId=operation_id, valeurTool=19)
    print(f"Inserted tool with value 19 for operation ID {operation_id}.")


    set_endtime_Tool(ToolId=Toolid)
    print(f"Set end time for ToolId {Toolid}.")


    set_machine_automatic_operation_start(ip, port, False)
    print(f"Machine with IP {ip} and port {port} set automatic operation start to False.")


    set_operation_endtime(operation_id)
    print(f"Operation with ID {operation_id} ended.")


    set_machine_in_automatic_operation_mode_run(ip, port, False)
    print(f"Machine with IP {ip} and port {port} set automatic operation mode to False.")


    set_program_endtime(program_id=program_id)
    print(f"Program {program_number} End for machine with IP {ip} and port {port}.")


    set_machine_per_day_endtime(machine_per_day_id)
    print(f"End time set for machine per day with ID {machine_per_day_id}.")


    set_machine_availability(ip, port, False)
    print(f"Machine with IP {ip} and port {port} set availability to False.")
   

    print("Workflow completed.")

