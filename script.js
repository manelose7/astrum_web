const baseReplitUrl = "https://34609f2d-8704-4f9c-bdff-92c018f52b1b-00-1wksftejb7gyb.spock.replit.dev"; // ВАШ БАЗОВЫЙ URL REPLIT БЕЗ ПОРТА
const keyDisplay = document.getElementById('key');
const generateBtn = document.getElementById('generate-key-btn');
const copyBtn = document.getElementById('copy-key-btn');
let currentKey = '';

async function getKey() {
    try {
        keyDisplay.textContent = 'Генерация...';
        const res = await fetch(`${baseReplitUrl}/generate-new-key`);
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
