from pymavlink.dialects.v10 import ardupilotmega
import asyncio
import json
import websockets
from pymavlink import mavutil
from mission import *


class MavlinkConnector:
    def __init__(self, connection_string, baud=115200):
        # self.vehicle = mavutil.mavlink_connection(connection_string)

        # Start SITL if no connection string specified
        if not connection_string:
            import dronekit_sitl
            self.sitl = dronekit_sitl.start_default()
            connection_string = self.sitl.connection_string()

        # Connect to the Vehicle.
        #   Set `wait_ready=True` to ensure default attributes are populated before `connect()` returns.
        print("\nConnecting to vehicle on: %s" % connection_string)
        print(baud)
        self.vehicle = mavutil.mavlink_connection(connection_string, baud)
        self.vehicle.wait_heartbeat()

        self.message_listeners = {}
        
        self.individual_data = {}

        # self.data = {
        #     # "AutopilotFirmwareVersion" : vehicle.version,
        #     # "MajorVersionNumber" : vehicle.version.major,
        #     # "MinorVersionNumber" : vehicle.version.minor,
        #     # "PatchVersionNumber" : vehicle.version.patch,
        #     # "ReleaseType" : vehicle.version.release_type(),
        #     # "ReleaseVersion" : vehicle.version.release_version(),
        #     # "StableRelease?" : vehicle.version.is_stable(),
        #     # "SupportsMISSION_FLOATMessageType" : vehicle.capabilities.mission_float,
        #     # "SupportsPARAM_FLOATMessageType" : vehicle.capabilities.param_float,
        #     # "SupportsMISSION_INTMessageType" : vehicle.capabilities.mission_int,
        #     # "SupportsCOMMAND_INTMessageType" : vehicle.capabilities.command_int,
        #     # "SupportsPARAM_UNIONMessageType" : vehicle.capabilities.param_union,
        #     # "SupportsFTPForFileTransfers" : vehicle.capabilities.ftp,
        #     # "SupportsCommandingAttitudeOffBoard" : vehicle.capabilities.set_attitude_target,
        #     # "SupportsCommandingPositionAndVelocityTargetsInLocalNEDFrame" : vehicle.capabilities.set_attitude_target_local_ned,
        #     # "SupportsSetPositionVelocityTargetsInGlobalScaledIntegers" : vehicle.capabilities.set_altitude_target_global_int,
        #     # "SupportsTerrainProtocol/DataHandling" : vehicle.capabilities.terrain,
        #     # "SupportsDirectActuatorControl" : vehicle.capabilities.set_actuator_target,
        #     # "SupportsTheFlightTerminationCommand" : vehicle.capabilities.flight_termination,
        #     # "SupportsMission_floatMessageType" : vehicle.capabilities.mission_float,
        #     # "SupportsOnBoardCompassCalibration" : vehicle.capabilities.compass_calibration,
        #     # "GlobalLocation" : {"lat":vehicle.location.global_frame.lat, "lng":vehicle.location.global_frame.lon, "alt":vehicle.location.global_frame.alt},
        #     # "ArmStatus": {"set_to_arm": False,
        #     #               "set_to_disarm": False,
        #     #               "isArm": False},
        #     "GPS_RAW_INT": {"lat": 0, "lng": 0, "alt": 0},
        #     # "GlobalLocationRelativeAltitude" : {"lat":vehicle.location.global_relative_frame.lat, "lng":vehicle.location.global_relative_frame.lon, "alt":vehicle.location.global_relative_frame.alt},
        #     # "LocalLocation" : {"down":vehicle.location.local_frame.down, "east":vehicle.location.local_frame.east, "north":vehicle.location.local_frame.north, "distance_home":vehicle.location.local_frame.distance_home()},
        #     "Attitude": {"roll": 0, "yaw": 0, "pitch": 0},
        #     # "Velocity" : vehicle.velocity,
        #     # "GPS" : {"eph":vehicle.gps_0.eph, "epv":vehicle.gps_0.epv, "fix_type":vehicle.gps_0.fix_type, "satellites_visible":vehicle.gps_0.satellites_visible},
        #     # "Gimbal status" : vehicle.gimbal,
        #     "Battery": {"current": 0, "level": 0, "voltage": 0},
        #     # "EKFOK?" : vehicle.ekf_ok,
        #     # "LastHeartbeat" : vehicle.last_heartbeat,
        #     # "Rangefinder" : {"RangefinderDistance" : vehicle.rangefinder.distance, "RangefinderVoltage" : vehicle.rangefinder.voltage},
        #     # "Heading" : vehicle.heading,
        #     # "IsArmable?" : vehicle.is_armable,
        #     # "SystemStatus" : vehicle.system_status.state,
        #     # "Groundspeed" : vehicle.groundspeed,
        #     # "Airspeed" : vehicle.airspeed,
        #     # "Mode" : vehicle.mode.name,
        #     # "Armed" : vehicle.armed,
        # }

        self.request_data_streams()

    def request_data_streams(self):
        # Request all data streams
        self.vehicle.mav.request_data_stream_send(
            self.vehicle.target_system,
            self.vehicle.target_component,
            mavutil.mavlink.MAV_DATA_STREAM_ALL,
            1,  # Request rate (Hz)
            1  # Enable stream
        )

    def add_message_listener(self, message_name):
        def decorator(fn):
            if message_name not in self.message_listeners:
                self.message_listeners[message_name] = []
            self.message_listeners[message_name].append(fn)
            return fn

        return decorator

    def remove_message_listener(self, message_name, callback):
        if message_name in self.message_listeners:
            if callback in self.message_listeners[message_name]:
                self.message_listeners[message_name].remove(callback)
                if len(self.message_listeners[message_name]) == 0:
                    del self.message_listeners[message_name]

    def notify_message_listeners(self, message_name, message):
        listeners = self.message_listeners.get(message_name, [])
        for listener in listeners:
            try:
                listener(self, message_name, message)
            except Exception as e:
                print(f'Exception in message handler for {message_name}: {e}')

    def handle_message(self, message):
        message_name = message.get_type()
        self.notify_message_listeners(message_name, message)

    def process_messages(self):
        while True:
            message = self.vehicle.recv_match(blocking=True)
            if message is not None:
                self.handle_message(message)

    def arm_drone(self):
        self.vehicle.mav.command_long_send(
            self.vehicle.target_system,
            self.vehicle.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,
            1, 0, 0, 0, 0, 0, 0)

        # wait until arming confirmed (can manually check with master.motors_armed())
        print("Waiting for the vehicle to arm")
        self.vehicle.motors_armed_wait()
        print('Armed!')

    def disarm_drone(self):
        self.vehicle.mav.command_long_send(
            self.vehicle.target_system,
            self.vehicle.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,
            0, 0, 0, 0, 0, 0, 0)

        # wait until disarming confirmed
        self.vehicle.motors_disarmed_wait()
        print("Disarmed")
