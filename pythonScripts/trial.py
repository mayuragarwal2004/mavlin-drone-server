from MavlinkConnection import * 

connector = MavlinkConnector("com4", baud=57600)

connector.process_messages()