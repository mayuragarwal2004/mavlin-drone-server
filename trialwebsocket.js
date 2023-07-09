
const net = require('net');

// Server configuration
// const HOST = 'localhost';
const HOST = '127.0.0.1';
const PORT = 4000;

// Create a new socket
const client = new net.Socket();

// Connect to the server
client.connect(PORT, HOST);

client.write(JSON.stringify({x:"Hello World"}))

// Handle data received from the server
client.on('data', (data) => {
  console.log(`Received data: ${data}`);
});

// Handle connection close
client.on('close', () => {
  console.log('Connection closed');
});