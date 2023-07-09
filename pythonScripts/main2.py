from pymavlink.dialects.v10 import ardupilotmega
import asyncio
import json
import websockets
from pymavlink import mavutil
from mission import *
from threading import Thread
import time
import serial.tools.list_ports
ports = serial.tools.list_ports.comports()


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
            10,  # Request rate (Hz)
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


# Server configuration
HOST = 'localhost'  # Use '0.0.0.0' to accept connections from all available interfaces
PORT = 4000

connector = None

data = {
    "ports": [],
    "GPS_RAW_INT": {"lat": None, "lng": None, "alt": None, "eph": None, "epv": None, "satellites_visible": None, "fix_type": None},
    "GLOBAL_POSITION_INT": {"lat": None, "lng": None, "alt": None, "vx": None, "vy": None, "vz": None},
    "ATTITUDE": {"roll": 0, "pitch": 0, "yaw": 0, "rollspeed": 0, "pitchspeed": 0, "yawspeed": 0},
    "Battery": {"current": 0, "level": 0, "voltage": 0},
    "SYS_STATUS": {"current": None, "level": None, "voltage": None},
    "EKF_STATUS_REPORT": {"ekf_poshorizabs": False, "ekf_constposmode": False, "ekf_predposhorizabs": False},
    "HEARTBEAT": {"flightmode": "AUTO", "armed": False, "system_status": None, "autopilot_type": None, "vehicle_type": None},
    "VFR_HUD": {"heading": None, "groundspeed": None, "airspeed": None},
    "RANGEFINDER": {"rngfnd_voltage": None, "rngfnd_distance": None},
    "MOUNT_STATUS": {"mount_pitch": None, "mount_roll": None, "mount_yaw": None},
    "AUTOPILOT_VERSION": {"capabilities": None, "raw_version": None, "autopilot_version_msg_count": 0},
    # "AutopilotFirmwareVersion" : vehicle.version,
    # "MajorVersionNumber" : vehicle.version.major,
    # "MinorVersionNumber" : vehicle.version.minor,
    # "PatchVersionNumber" : vehicle.version.patch,
    # "ReleaseType" : vehicle.version.release_type(),
    # "ReleaseVersion" : vehicle.version.release_version(),
    # "StableRelease?" : vehicle.version.is_stable(),
    # "SupportsMISSION_FLOATMessageType" : vehicle.capabilities.mission_float,
    # "SupportsPARAM_FLOATMessageType" : vehicle.capabilities.param_float,
    # "SupportsMISSION_INTMessageType" : vehicle.capabilities.mission_int,
    # "SupportsCOMMAND_INTMessageType" : vehicle.capabilities.command_int,
    # "SupportsPARAM_UNIONMessageType" : vehicle.capabilities.param_union,
    # "SupportsFTPForFileTransfers" : vehicle.capabilities.ftp,
    # "SupportsCommandingAttitudeOffBoard" : vehicle.capabilities.set_attitude_target,
    # "SupportsCommandingPositionAndVelocityTargetsInLocalNEDFrame" : vehicle.capabilities.set_attitude_target_local_ned,
    # "SupportsSetPositionVelocityTargetsInGlobalScaledIntegers" : vehicle.capabilities.set_altitude_target_global_int,
    # "SupportsTerrainProtocol/DataHandling" : vehicle.capabilities.terrain,
    # "SupportsDirectActuatorControl" : vehicle.capabilities.set_actuator_target,
    # "SupportsTheFlightTerminationCommand" : vehicle.capabilities.flight_termination,
    # "SupportsMission_floatMessageType" : vehicle.capabilities.mission_float,
    # "SupportsOnBoardCompassCalibration" : vehicle.capabilities.compass_calibration,
    # "GlobalLocation" : {"lat":vehicle.location.global_frame.lat, "lng":vehicle.location.global_frame.lon, "alt":vehicle.location.global_frame.alt},
    # "ArmStatus": {"set_to_arm": False,
    #               "set_to_disarm": False,
    #               "isArm": False},
    # "GlobalLocationRelativeAltitude" : {"lat":vehicle.location.global_relative_frame.lat, "lng":vehicle.location.global_relative_frame.lon, "alt":vehicle.location.global_relative_frame.alt},
    # "LocalLocation" : {"down":vehicle.location.local_frame.down, "east":vehicle.location.local_frame.east, "north":vehicle.location.local_frame.north, "distance_home":vehicle.location.local_frame.distance_home()},
    # "Velocity" : vehicle.velocity,
    # "GPS" : {"eph":vehicle.gps_0.eph, "epv":vehicle.gps_0.epv, "fix_type":vehicle.gps_0.fix_type, "satellites_visible":vehicle.gps_0.satellites_visible},
    # "Gimbal status" : vehicle.gimbal,
    # "EKFOK?" : vehicle.ekf_ok,
    # "LastHeartbeat" : vehicle.last_heartbeat,
    # "Rangefinder" : {"RangefinderDistance" : vehicle.rangefinder.distance, "RangefinderVoltage" : vehicle.rangefinder.voltage},
    # "Heading" : vehicle.heading,
    # "IsArmable?" : vehicle.is_armable,
    # "SystemStatus" : vehicle.system_status.state,
    # "RC_CHANNELS_RAW": {"capabilities": None, "raw_version": None, "autopilot_version_msg_count": 0},
    # "Airspeed" : vehicle.airspeed,
    # "Mode" : vehicle.mode.name,
    # "Armed" : vehicle.armed,
}


async def connect_to_server():
    global data
    global connector
    async with websockets.connect('ws://localhost:9000') as websocket:
        print("Connected to WebSocket server")

        # Prepare data to send
        # data = {
        #     'data': [
        #         {'lat': 10.123, 'lng': 20.456, 'alt': 100.0},
        #         {'lat': 30.789, 'lng': 40.987, 'alt': 200.0}
        #     ]
        # }

        Thread(target=uploadServerData, args=(websocket,)).start()

        while True:
            # Receive data from the client
            received_data = await websocket.recv()
            print(received_data)
            msg = json.loads(received_data)

            if msg:
                if msg['purpose'] == "PortUpdate":
                    print("Port Update requested")
                    ports = serial.tools.list_ports.comports()
                    arr = []
                    for port, desc, hwid in sorted(ports):
                        arr.append({"port": port, "desc": desc, "hwid": hwid})
                        # print("{}: {} [{}]".format(port, desc, hwid))
                    data['ports'] = arr

                if msg['purpose'] == "ConnectVehicle":
                    print("connect to vehicle requested")
                    # continue
                    connector = MavlinkConnector(
                        msg['port'], baud=int(msg['baud']))

                    @connector.add_message_listener('ATTITUDE')
                    def attitude_callback(vehicle, name, message):
                        global data
                        data["ATTITUDE"]["roll"] = message.roll
                        data["ATTITUDE"]["pitch"] = message.pitch
                        data["ATTITUDE"]["yaw"] = message.yaw
                        data["ATTITUDE"]["rollspeed"] = message.rollspeed
                        data["ATTITUDE"]["pitchspeed"] = message.pitchspeed
                        data["ATTITUDE"]["yawspeed"] = message.yawspeed
                        print('Reciving telemtry data')

                    @connector.add_message_listener('GLOBAL_POSITION_INT')
                    def gpspositionint_callback(vehicle, name, message):
                        global data
                        data["GLOBAL_POSITION_INT"]["lat"] = message.lat/1e7
                        data["GLOBAL_POSITION_INT"]["lng"] = message.lon/1e7
                        data["GLOBAL_POSITION_INT"]["alt"] = message.alt/1e3
                        data["GLOBAL_POSITION_INT"]["vx"] = message.vx/1e2
                        data["GLOBAL_POSITION_INT"]["vy"] = message.vy/1e2
                        data["GLOBAL_POSITION_INT"]["vz"] = message.vz/1e2
                        # print('GPS Data:', message)

                    @connector.add_message_listener('VFR_HUD')
                    def vfrhud_callback(vehicle, name, message):
                        global data
                        data["VFR_HUD"]["heading"] = message.heading
                        data["VFR_HUD"]["airspeed"] = message.airspeed
                        data["VFR_HUD"]["groundspeed"] = message.groundspeed
                        # print('VFR_HUD Data:', message)

                    @connector.add_message_listener('RANGEFINDER')
                    def rangefinder_callback(vehicle, name, message):
                        global data
                        data["RANGEFINDER"]["rngfnd_voltage"] = message.distance
                        data["RANGEFINDER"]["rngfnd_distance"] = message.voltage
                        # print('VFR_HUD Data:', message)

                    @connector.add_message_listener('MOUNT_STATUS')
                    def mountstatus_callback(vehicle, name, message):
                        global data
                        data["MOUNT_STATUS"]["mount_roll"] = message.pointing_b / 1e2
                        data["MOUNT_STATUS"]["mount_pitch"] = message.pointing_a / 1e2
                        data["MOUNT_STATUS"]["mount_yaw"] = message.pointing_c / 1e2
                        # print('MOUNT_STATUS Data:', message)

                    @connector.add_message_listener('AUTOPILOT_VERSION')
                    def autopilotversion_callback(vehicle, name, message):
                        global data
                        data["AUTOPILOT_VERSION"]["capabilities"] = message.capabilities
                        data["AUTOPILOT_VERSION"]["raw_version"] = message.flight_sw_version
                        data["AUTOPILOT_VERSION"]["autopilot_version_msg_count"] += data["AUTOPILOT_VERSION"]["autopilot_version_msg_count"]
                        # print('MOUNT_STATUS Data:', message)

                    @connector.add_message_listener("SYS_STATUS")
                    def sysstatus_callback(vehicle, name, message):
                        data["SYS_STATUS"]["current"] = message.current_battery
                        data["SYS_STATUS"]["level"] = message.battery_remaining
                        data["SYS_STATUS"]["voltage"] = message.voltage_battery/1e3
                        # print(
                        #     f"SYS_STATUS: Voltage Battery: {message.voltage_battery}")

                    @connector.add_message_listener('GPS_RAW_INT')
                    def gpsrawint_callback(vehicle, name, message):
                        global data
                        data["GPS_RAW_INT"]["lat"] = message.lat/1e7
                        data["GPS_RAW_INT"]["lng"] = message.lon/1e7
                        data["GPS_RAW_INT"]["alt"] = message.alt/1e3
                        data["GPS_RAW_INT"]["eph"] = message.eph/1e2
                        data["GPS_RAW_INT"]["epv"] = message.epv/1e2
                        data["GPS_RAW_INT"]["satellites_visible"] = message.satellites_visible/1e2
                        data["GPS_RAW_INT"]["fix_type"] = message.fix_type/1e2

                    @connector.add_message_listener("EKF_STATUS_REPORT")
                    def efkstatusreport_callback(vehicle, name, message):
                        data["EKF_STATUS_REPORT"]["ekf_poshorizabs"] = (
                            message.flags & ardupilotmega.EKF_POS_HORIZ_ABS) > 0
                        data["EKF_STATUS_REPORT"]["ekf_constposmode"] = (
                            message.flags & ardupilotmega.EKF_CONST_POS_MODE) > 0
                        data["EKF_STATUS_REPORT"]["ekf_predposhorizabs"] = (
                            message.flags & ardupilotmega.EKF_PRED_POS_HORIZ_ABS) > 0

                    @connector.add_message_listener("HEARTBEAT")
                    def heartbeat_callback(vehicle, name, message):
                        data["HEARTBEAT"]["armed"] = (
                            message.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED) != 0
                        data["HEARTBEAT"]["system_status"] = message.system_status
                        data["HEARTBEAT"]["vehicle_type"] = message.type
                        data["HEARTBEAT"]["autopilot_type"] = message.autopilot
                        # if self._is_mode_available(m.custom_mode, m.base_mode) is False:
                        #     raise APIException("mode (%s, %s) not available on mavlink definition" % (m.custom_mode, m.base_mode))
                        if data["HEARTBEAT"]["autopilot_type"] == mavutil.mavlink.MAV_AUTOPILOT_PX4:
                            data["HEARTBEAT"]["flightmode"] = mavutil.interpret_px4_mode(
                                message.base_mode, message.custom_mode)
                        # else:
                        #     data["HEARTBEAT"]["flightmode"] = self._mode_mapping_bynumber[m.custom_mode]

                    # Start processing received messages
                    # connector.process_messages()
                    Thread(target=connector.process_messages, args=()).start()
                    print("started processing the msgs")

                if connector:
                    print()
                    if msg['purpose'] == "MissionWrite":
                        mission_waypoints = []
                        for index, i in enumerate(msg['data'], start=0):
                            mission_waypoints.append(mission_item(
                                index, i['command'], 0, i['p1'], i['p2'], i['p3'], i['p4'], i['p5'], i['p6'], i['p7']))
                        upload_mission(connector.vehicle, mission_waypoints)
                        await websocket.send("Uploaded")
                    elif msg['purpose'] == "Arm":
                        print("Arm requested")
                        connector.arm_drone()

                    elif msg['purpose'] == "Disarm":
                        print("Disarm requested")
                        connector.disarm_drone()

                    elif msg['purpose'] == "Takeoff":
                        print("Takeoff requested")
                        takeoff(connector.vehicle, msg['data']['alt'])

        # # Prepare data to send
        # data = {
        #     'data': [
        #         {'lat': 10.123, 'lng': 20.456, 'alt': 100.0},
        #         {'lat': 30.789, 'lng': 40.987, 'alt': 200.0}
        #     ]
        # }

        # # Convert data to JSON
        # message = json.dumps(data)

        # await websocket.send(message)
        # print(f"Sent message to server: {message}")

        # response = await websocket.recv()
        # print(f"Received response from server: {response}")

        # print("Closing WebSocket connection")
        # await websocket.close()


def uploadServerData(websocket):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def send_data():
        while True:
            print("Sending data to server")

            # Convert data to JSON
            message = json.dumps(data)

            # Send data via the WebSocket connection
            await websocket.send(message)

            time.sleep(1)

    loop.run_until_complete(send_data())
    # while websocket:
    #     print("sending data to server")
    #     # Convert data to JSON
    #     message = json.dumps(data)

    #     # websocket.send(message)

    #       # Send data via the WebSocket connection
    #     asyncio.run_coroutine_threadsafe(websocket.send(message), asyncio.get_event_loop())

    #     time.sleep(1)


asyncio.get_event_loop().run_until_complete(connect_to_server())


# async def handle_client(websocket, path):
#     print(f"Accepted connection from {websocket.remote_address[0]}:{websocket.remote_address[1]}")

#     message = "Hello, server!"
#     await websocket.send(message)

#     while True:
#         # Receive data from the client
#         received_data = await websocket.recv()
#         data = json.loads(received_data)

#         if data:
#             if data['purpose'] == "ConnectVehicle":
#                 connector = MavlinkConnector('COM4', baud=57600)
#                 @connector.add_message_listener('ATTITUDE')
#                 def attitude_callback(vehicle, name, message):
#                     print('Attitude:', message)
#                 @connector.add_message_listener('GLOBAL_POSITION_INT')
#                 def gps_callback(vehicle, name, message):
#                     print('GPS Data:', message)
#                 # Start processing received messages
#                 connector.process_messages()

#             if connector:
#                 if data['purpose'] == "MissionWrite":
#                     mission_waypoints = []
#                     for index, i in enumerate(data['data'], start=0):
#                         mission_waypoints.append(mission_item(index, 0, i['lat'], i['lng'], i['alt']))
#                     upload_mission(connector.vehicle, mission_waypoints)
#                     await websocket.send("Uploaded")
#                 elif data['purpose'] == "Arm":
#                     connector.arm_drone()
#                 elif data['purpose'] == "Disarm":
#                     connector.disarm_drone()

#         print(f"Received data: {data}")

# async def start_server():
#     # Create a WebSocket server
#     async with websockets.serve(handle_client, HOST, PORT):
#         print(f"Server listening on {HOST}:{PORT}")

#         # Keep the server running indefinitely
#         await asyncio.Future()

# # Start the WebSocket server
# asyncio.run(start_server())

# # Example usage
# # Replace with your connection details
# connector = MavlinkConnector('COM4', baud=57600)

# # Define callback functions to process attitude and GPS data


# @connector.add_message_listener('ATTITUDE')
# def attitude_callback(vehicle, name, message):
#     print('Attitude:', message)

# @connector.add_message_listener('GLOBAL_POSITION_INT')
# def gps_callback(vehicle, name, message):
#     print('GPS Data:', message)

# connector.disarm_drone()

# # Start processing received messages
# connector.process_messages()
