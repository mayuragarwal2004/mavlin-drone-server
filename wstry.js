const WebSocket = require('ws');

// Create a WebSocket server
const wss = new WebSocket.Server({ port: 8080 });

// Handle incoming WebSocket connections
wss.on('connection', (ws) => {
  console.log('A client connected');

  // Handle incoming messages from the client
  ws.on('message', (message) => {
    console.log('Received message from client:', message);

    // Send a response back to the client
    ws.send('Server received your message');
  });
});
