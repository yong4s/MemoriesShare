const express = require('express');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// Головна сторінка
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// API endpoint для отримання токена (заглушка)
app.get('/api/get-token', (req, res) => {
    res.json({
        message: 'Use the web interface to get your JWT token',
        url: `http://localhost:${PORT}`
    });
});

// Запуск сервера
app.listen(PORT, () => {
    console.log('🚀 Clerk Token Server запущено!');
    console.log(`📱 Відкрийте: http://localhost:${PORT}`);
    console.log('🔑 Отримайте JWT токен через веб-інтерфейс');
    console.log('');
    console.log('Інструкція:');
    console.log('1. Відкрийте http://localhost:3000 у браузері');
    console.log('2. Введіть ваш Clerk Publishable Key');
    console.log('3. Увійдіть в систему');
    console.log('4. Скопіюйте JWT токен для Postman');
});