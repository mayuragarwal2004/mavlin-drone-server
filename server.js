const net = require("net");
const express = require("express");
const app = express();
const bodyParser = require("body-parser");
const port = process.env.PORT || 5000;

const HOST = "127.0.0.1";
const PORT = 4000;
const client = new net.Socket();

app.use(bodyParser.json());

// This displays message that the server running and listening to specified port
app.listen(port, () => console.log(`Listening on port ${port}`));

// create a GET route
app.get("/api", (req, res) => {
  res.send({ express: "YOUR EXPRESS BACKEND IS CONNECTED TO REACT" });
  console.log("HI");
});

// Write Mission
app.post("/api/writemission", (req, res) => {
  console.log(req.body);

  client.connect(PORT, HOST);
  client.write(JSON.stringify({ purpose: "MissionWrite", data:req.body.pathFull }));

  client.on('data', (data) => {
    console.log(`Received data: ${data}`);
  });

  client.on('close', () => {
    console.log('Connection closed');
  });

  res.send({ express: "YOUR EXPRESS BACKEND IS CONNECTED TO REACT" });
  console.log("Write Mission Requested");
});


// Write Mission
app.post("/api/arm", (req, res) => {
  console.log(req.body);

  client.connect(PORT, HOST);
  client.write(JSON.stringify({ purpose: "Arm" }));

  client.on('data', (data) => {
    console.log(`Received data: ${data}`);
  });

  client.on('close', () => {
    console.log('Connection closed');
  });

  res.send({ express: "YOUR EXPRESS BACKEND IS CONNECTED TO REACT" });
  console.log("Arm Requested");
});

// Write Mission
app.post("/api/disarm", (req, res) => {
  console.log(req.body);

  client.connect(PORT, HOST);
  client.write(JSON.stringify({ purpose: "Disarm" }));

  client.on('data', (data) => {
    console.log(`Received data: ${data}`);
  });

  client.on('close', () => {
    console.log('Connection closed');
  });

  res.send({ express: "YOUR EXPRESS BACKEND IS CONNECTED TO REACT" });
  console.log("Disarm Requested");
});