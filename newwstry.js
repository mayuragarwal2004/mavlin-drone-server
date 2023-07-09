const express = require("express");
const http = require("http");
const WebSocket = require("websocket");

const app = express();
const server = http.createServer(app);
const wsServer = new WebSocket.server({ httpServer: server });

wsServer.on("request", (request) => {
  let orientationData = "Some orientation data";
  const connection = request.accept(null, request.origin);

  connection.on("message", (message) => {
    // Handle incoming messages from the React app if needed
    console.log(message);
    orientationData = message.utf8Data;
  });

  connection.on("close", (reasonCode, description) => {
    // Handle WebSocket connection close event if needed
    console.log("connection closed: ", reasonCode, " ", description);
  });

  // Simulate sending drone orientation data
  setInterval(() => {
    connection.send(orientationData);
  }, 1000); // Adjust the delay as per your requirements
});

server.listen(8765, () => {
  console.log("WebSocket server is listening on port 8765");
});

server.on("connection", (stream) => {
  console.log("someone connected!");
});

// Add your existing Express routes and middleware below
// ...
