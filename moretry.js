/* eslint-disable default-case */
const webSocketsServerPortReact = 8000;
const webSocketsServerPortPython = 9000;
const webSocketServer = require("websocket").server;
const http = require("http");
const WebSocket = require("ws");

// Spinning the http server for React WebSocket server.
const serverReact = http.createServer();
serverReact.listen(webSocketsServerPortReact);
console.log(
  "WebSocket server for React listening on port",
  webSocketsServerPortReact
);

const wsServerReact = new webSocketServer({
  httpServer: serverReact,
});

const clientsReact = {};
let clientPython = null;

// This code generates unique userid for every user.
const getUniqueID = () => {
  const s4 = () =>
    Math.floor((1 + Math.random()) * 0x10000)
      .toString(16)
      .substring(1);
  return s4() + s4() + "-" + s4();
};

wsServerReact.on("request", function (request) {
  var userID = getUniqueID();
  console.log(
    new Date() +
      " Received a new connection for React from origin " +
      request.origin +
      "."
  );

  // You can rewrite this part of the code to accept only the requests from allowed origin
  const connection = request.accept(null, request.origin);
  clientsReact[userID] = connection;
  console.log(
    "Connected to React: " +
      userID +
      " in " +
      Object.getOwnPropertyNames(clientsReact)
  );

  connection.on("message", function (message) {
    if (message.type === "utf8") {
      console.log("Received Message for React: ", message.utf8Data);
      message = JSON.parse(message.utf8Data);
      if (clientPython) {
        switch (message.purpose) {
          // connect vehicle
          case "ConnectVehicle":
            clientPython.send(
              JSON.stringify({
                purpose: "ConnectVehicle",
                port: message.port,
                baud: message.baud,
              })
            );
            console.log("Connect Vehicle requested");
            break;

          // Prt Update
          case "PortUpdate":
            clientPython.send(JSON.stringify({ purpose: "PortUpdate" }));
            console.log("Port update requested");
            break;

          // Arm
          case "Arm":
            clientPython.send(JSON.stringify({ purpose: "Arm" }));
            console.log("Arm requested");
            break;

          // Disarm
          case "DisArm":
            clientPython.send(JSON.stringify({ purpose: "Disarm" }));
            console.log("Disarm requested");
            break;

          // Mission Write
          case "MissionWrite":
            clientPython.send(
              JSON.stringify({
                purpose: "MissionWrite",
                data: message.pathfull,
              })
            );
            console.log("Mission Write requested");
            break;

          // Takeoff
          case "Takeoff":
            clientPython.send(
              JSON.stringify({ purpose: "Takeoff", data: message.data })
            );
            console.log("Takeoff requested");
            break;
          // case "purpose":
          //   break;
        }
      }
    }
  });

  connection.on("close", () => {
    console.log("connection closed for ", userID);
    delete clientsReact[userID];
  });
});

// Start WebSocket server for Python
const wssPython = new WebSocket.Server({ port: webSocketsServerPortPython });
console.log(
  "WebSocket server for Python listening on port",
  webSocketsServerPortPython
);

wssPython.on("connection", function connection(ws) {
  console.log("Connected to Python");

  ws.on("message", function incoming(message) {
    console.log("Received Message for Python");

    for (const key in clientsReact) {
      clientsReact[key].sendUTF(message);
      console.log("Sent Message to React: ", key);
    }

    // Process the message received from Python client
    // ...

    // Example: Send a response back to Python client
    // ws.send(JSON.stringify({ purpose: "ConnectVehicle" }));
    // ws.send(JSON.stringify({ purpose: "ConnectVehicle" }));
  });

  ws.on("close", () => {
    console.log("Disconnedcted from Python");
    clientPython = null;
  });

  // ws.send(JSON.stringify({ purpose: "ConnectVehicle" }));

  // Store the WebSocket connection for Python client
  clientPython = ws;
});
