const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const chokidar = require('chokidar');
const path = require('path');
const fs = require('fs');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

const logFolder = path.join('..', 'logs');
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB — максимум размера файла

const clientFiles = new Map();

// Функция отправки последних строк файла
function sendLastLines(filePath, ws, lines = 100) {
    const stat = fs.statSync(filePath);

    if (stat.size > MAX_FILE_SIZE) {
        ws.send(JSON.stringify({ type: 'error', message: 'Файл слишком большой для отображения' }));
        return;
    }

    const stream = fs.createReadStream(filePath, {
        encoding: 'utf8',
        start: Math.max(0, stat.size - 10000) // Читаем последние примерно 10КБ
    });

    let buffer = '';

    stream.on('data', (chunk) => {
        buffer += chunk;
    });

    stream.on('end', () => {
        const lastLines = buffer.split('\n').slice(-lines).join('\n');
        ws.send(JSON.stringify({ type: 'fileContent', file: path.basename(filePath), content: lastLines }));
    });

    stream.on('error', (err) => {
        console.error('Ошибка при чтении файла:', err);
        ws.send(JSON.stringify({ type: 'error', message: 'Ошибка при чтении файла' }));
    });
}

// Функция трансляции новых данных (как tail -f)
function broadcastFileUpdate(fileName, content) {
    wss.clients.forEach(client => {
        if (client.readyState === WebSocket.OPEN && clientFiles.get(client) === fileName) {
            client.send(JSON.stringify({ file: fileName, content }));
        }
    });
}

// Отслеживаем изменения файлов
const watcher = chokidar.watch(logFolder, { persistent: true });

watcher.on('change', (filePath) => {
    const fileName = path.basename(filePath);
    const stream = fs.createReadStream(filePath, {
        encoding: 'utf8',
        start: fs.statSync(filePath).size - 1000 // Последние 1000 байт — чтобы не перегружать
    });

    stream.on('data', (chunk) => {
        broadcastFileUpdate(fileName, chunk);
    });

    stream.on('error', (err) => {
        console.error('Ошибка при отслеживании файла:', err);
    });
});

// Отдаём статику
app.use(express.static('public'));

// Обработка WebSocket-соединений
wss.on('connection', (ws) => {
    console.log('Клиент подключился');

    fs.readdir(logFolder, (err, files) => {
        if (err) {
            console.error('Ошибка при чтении директории:', err);
            ws.send(JSON.stringify({ type: 'error', message: 'Ошибка при получении списка файлов' }));
            return;
        }
        ws.send(JSON.stringify({ type: 'fileList', files }));
    });

    ws.on('message', (message) => {
        const data = JSON.parse(message);

        if (data.action === 'selectFile') {
            const filePath = path.join(logFolder, data.file);

            if (!fs.existsSync(filePath)) {
                ws.send(JSON.stringify({ type: 'error', message: 'Файл не найден' }));
                return;
            }

            clientFiles.set(ws, data.file);
            sendLastLines(filePath, ws);
        }
    });

    ws.on('close', () => {
        console.log('Клиент отключился');
        clientFiles.delete(ws);
    });
});

// Запуск сервера
server.listen(3001, () => {
    console.log('Сервер запущен на http://localhost:3001');
});
