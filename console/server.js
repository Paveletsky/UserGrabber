const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const chokidar = require('chokidar');
const path = require('path');
const fs = require('fs');
const { promisify } = require('util');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

const logFolder = path.join('..', 'logs');

const readdir = promisify(fs.readdir);

const clientFiles = new Map();

function broadcastFileUpdate(fileName, content) {
    wss.clients.forEach(client => {
        if (client.readyState === WebSocket.OPEN) {
            const currentFile = clientFiles.get(client);
            if (currentFile === fileName) {
                client.send(JSON.stringify({ file: fileName, content }));
            }
        }
    });
}

const watcher = chokidar.watch(logFolder, { persistent: true });

watcher.on('change', (filePath) => {
    const fileName = path.basename(filePath);
    fs.readFile(filePath, 'utf8', (err, data) => {
        if (err) {
            console.error(err);
            return;
        }
        broadcastFileUpdate(fileName, data);
    });
});

app.use(express.static('public'));


wss.on('connection', (ws) => {
    console.log('Client connected');

    readdir(logFolder).then(files => {
        ws.send(JSON.stringify({ type: 'fileList', files }));
    }).catch(err => {
        console.error(err);
    });

    ws.on('message', (message) => {
        const data = JSON.parse(message);
        
        if (data.action === 'selectFile') {
            const filePath = path.join(logFolder, data.file);
            clientFiles.set(ws, data.file);
            fs.readFile(filePath, 'utf8', (err, fileContent) => {
                if (err) {
                    console.error(err);
                    return;
                }
                ws.send(JSON.stringify({ file: data.file, content: fileContent }));
            });
        }
    });

    ws.on('close', () => {
        console.log('Client disconnected');
        clientFiles.delete(ws);
    });
});

server.listen(3001, () => {
    console.log('Server is running on http://localhost:3000');
});
