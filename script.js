const baseReplitUrl = "https://astrum-web.vercel.app"; // ВАШ БАЗОВЫЙ URL REPLIT БЕЗ ПОРТА
const apiUrl = `${baseReplitUrl}`; // Убран /api для Vercel Serverless Functions
const keyDisplay = document.getElementById('key');
const generateBtn = document.getElementById('generate-key-btn');
const copyBtn = document.getElementById('copy-key-btn');
let currentKey = '';

async function getKey() {
    try {
        keyDisplay.textContent = 'Генерация...';
        const res = await fetch(`${apiUrl}/generate-new-key`);
        const newKey = await res.text(); 
        currentKey = newKey;
        
        keyDisplay.textContent = currentKey;
        keyDisplay.classList.add('copied');
        copyBtn.style.display = 'inline-block';
        
        setTimeout(() => {
            keyDisplay.classList.remove('copied');
        }, 500);
    } catch (error) {
        keyDisplay.textContent = 'Ошибка генерации ключа';
        console.error('Ошибка:', error);
    }
}

function copyKey() {
    if (!currentKey) return;

    navigator.clipboard.writeText(currentKey).then(() => {
        copyBtn.textContent = 'Скопировано!';
        copyBtn.style.background = 'rgba(78, 140, 255, 0.2)';
        
        setTimeout(() => {
            copyBtn.textContent = 'Копировать ключ';
            copyBtn.style.background = 'transparent';
        }, 1500);
    });
}

generateBtn.addEventListener('click', getKey);
copyBtn.addEventListener('click', copyKey);
