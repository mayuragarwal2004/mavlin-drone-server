import math
from pymavlink import mavutil


class mission_item:
    def __init__(self, i, command, current, p1, p2, p3, p4, p5, p6, p7):
        self.seq = i
        self.frame = mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT
        self.command = getattr(mavutil.mavlink,command)
        self.current = current
        self.auto = 1
        self.param1 = p1 # value was 0.00
        self.param2 = p2 # value was 2.00
        self.param3 = p3 # value was 20.00
        self.param4 = p4 # value was math.nan
        self.param5 = p5 # value was x
        self.param6 = p6 # value was y
        self.param7 = p7 # value was z
        self.mission_type = 0

# Arm the drone
def arm(the_connection):
    print("-- Arming")

    the_connection.mav.command_long_send(
        the_connection.target_system,
        the_connection.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0,
        1, 0, 0, 0, 0, 0, 0)

    ack(the_connection, "COMMAND_ACK")

# Take Off the Drone
def takeoff(the_connection, alt):
    print("-- Takeoff Initiated")

    the_connection.mav.command_long_send(
        the_connection.target_system,
        the_connection.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        0, 0, 0, 0, math.nan, 0, 0, alt)

    ack(the_connection, "COMMAND_ACK")


def upload_mission(the_connection, mission_items):
    n = len(mission_items)
    print("-- Sending Messages --")

    the_connection.mav.mission_count_send(
        the_connection.target_system, the_connection.target_component, n, 0)

    ack(the_connection, "MISSION_REQUEST")

    for waypoint in mission_items:
        print("-- Creating a waypoint")

        the_connection.mav.mission_item_send(the_connection.target_system,
                                             the_connection.target_component,
                                             waypoint.seq,
                                             waypoint.frame,
                                             waypoint.command,
                                             waypoint.current,
                                             waypoint.auto,
                                             waypoint.param1,
                                             waypoint.param2,
                                             waypoint.param3,
                                             waypoint.param4,
                                             waypoint.param5,
                                             waypoint.param6,
                                             waypoint.param7,
                                             waypoint.mission_type)
    if waypoint != mission_items[n-1]:
        ack(the_connection, "MISSION_REQUEST")

    ack(the_connection, "MISSION_ACK")

# send message for the drone to return to the launch point
def set_return(the_connection):
    print("-- Set Return To Launch")
    the_connection.mav.command_long_send(
        the_connection.target_system,
        the_connection.target_component,
        mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
        0, 0, 0, 0, 0, 0, 0, 0)

    ack(the_connection, "COMMAND_ACK")

# Start mission
def start_mission(the_connection):
    print("-- Mission Start")
    the_connection.amv.command_long_send(
        the_connection.target_system,
        the_connection.target_component,
        mavutil.mavlink.MAV_CMD_MISSION_START,
        0, 0, 0, 0, 0, 0, 0, 0)

# Acknowlegdement from drone
def ack(the_connection, keyword):
    print("-- Message Read " +
          str(the_connection.recv_match(type=keyword, blocking=True)))


# Main function
# if __name__ == '__main__':
#     print('-- Program Started')
#     the_connection = mavutil.mavlink_connection("udpin:localhost:14540")

#     while (the_connection.target_system == 0):
#         print("-- Checking Heartbeat")
#         the_connection.wait_heartbeat()
#         print('-- heartbeat from system %u component %u' %
#               [the_connection.target_system, the_connection.target_component])

#     mission_waypoints = []

#     mission_waypoints.append(mission_item[0, 0, __, __, 10])
#     mission_waypoints.append(mission_item[1, 0, __, __, 10])
#     mission_waypoints.append(mission_item[2, 0, __, __, 10])

#     upload_mission(the_connection, mission_waypoints)

#     arm(the_connection)

#     takeoff(the_connection)

#     start_mission(the_connection)

#     for mission_item in mission_waypoints:
#         print("-- Message Read "+str(the_connection.recv_match(type="MISSION_ITEM_REACHED",
#               condition="MISSION_ITEM_REACHED.seq == {0}".format(mission_item.seq), blocking=True)))

#     set_return(the_connection)
