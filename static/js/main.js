document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('fileInput');
    const fileName = document.getElementById('fileName');
    const uploadForm = document.getElementById('uploadForm');
    const submitBtn = document.getElementById('submitBtn');
    const loader = document.getElementById('loader');
    const resultSection = document.getElementById('resultSection');
    const resultBox = document.getElementById('resultBox');
    const errorBox = document.getElementById('errorBox');
    const resultMessage = document.getElementById('resultMessage');
    const fileInfo = document.getElementById('fileInfo');
    const downloadJsonLink = document.getElementById('downloadJsonLink');
    const downloadExcelLink = document.getElementById('downloadExcelLink');
    const errorMessage = document.getElementById('errorMessage');
    const progressSteps = document.getElementById('progressSteps');
    const usageInfo = document.getElementById('usageInfo');

    // Обновление имени файла при выборе
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            fileName.textContent = file.name;
            fileName.style.color = '#667eea';
            fileName.style.fontWeight = 'bold';
        } else {
            fileName.textContent = 'Файл не выбран';
            fileName.style.color = '#666';
            fileName.style.fontWeight = 'normal';
        }
        
        // Скрываем предыдущие результаты
        resultSection.style.display = 'none';
        errorBox.style.display = 'none';
    });

    // Обработка отправки формы
    uploadForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const file = fileInput.files[0];
        if (!file) {
            showError('Пожалуйста, выберите файл');
            return;
        }

        // Показываем загрузку и прогресс
        submitBtn.disabled = true;
        loader.style.display = 'inline';
        document.querySelector('.btn-text').textContent = 'Обработка...';
        resultSection.style.display = 'none';
        errorBox.style.display = 'none';
        progressSteps.style.display = 'block';
        
        // Активируем первый шаг
        updateProgressStep(1);

        // Создаем FormData
        const formData = new FormData();
        formData.append('file', file);
        
        // Добавляем выбранный AI провайдер
        const aiProvider = document.getElementById('aiProvider').value;
        formData.append('ai_provider', aiProvider);

        try {
            // Симулируем прогресс (так как запрос долгий)
            setTimeout(() => updateProgressStep(2), 1000);
            setTimeout(() => updateProgressStep(3), 2000);
            
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            // Проверяем Content-Type перед парсингом JSON
            const contentType = response.headers.get('content-type');
            let data;
            
            if (contentType && contentType.includes('application/json')) {
                // Пытаемся распарсить JSON
                try {
                    data = await response.json();
                } catch (jsonError) {
                    // Если не удалось распарсить JSON, читаем как текст
                    const text = await response.text();
                    console.error('Ошибка парсинга JSON:', jsonError);
                    console.error('Ответ сервера:', text);
                    showError('Ошибка сервера: получен неверный формат ответа. Проверьте консоль браузера для деталей.');
                    return;
                }
            } else {
                // Если ответ не JSON, читаем как текст
                const text = await response.text();
                console.error('Сервер вернул не JSON ответ:', text.substring(0, 500));
                
                // Пытаемся извлечь информацию об ошибке из HTML
                let errorMsg = 'Ошибка сервера';
                if (response.status === 500) {
                    errorMsg = 'Внутренняя ошибка сервера. Проверьте логи на сервере.';
                } else if (response.status === 404) {
                    errorMsg = 'Маршрут не найден. Возможно, сервер не запущен.';
                } else if (response.status === 413) {
                    errorMsg = 'Файл слишком большой. Максимальный размер: 50 МБ.';
                } else if (response.status >= 400) {
                    errorMsg = `Ошибка ${response.status}: ${response.statusText}`;
                }
                
                showError(errorMsg);
                return;
            }

            if (response.ok && data.success) {
                // Завершаем все шаги
                completeAllSteps();
                showSuccess(data);
            } else {
                // Обрабатываем ошибку из JSON ответа
                const errorMsg = data.error || data.message || 'Произошла ошибка при обработке';
                showError(errorMsg);
            }
        } catch (error) {
            // Обрабатываем сетевые ошибки и ошибки парсинга
            let errorMsg = 'Ошибка сети: ' + error.message;
            
            if (error.message.includes('JSON')) {
                errorMsg = 'Ошибка парсинга ответа сервера. Возможно, сервер вернул HTML вместо JSON. Проверьте консоль браузера.';
            } else if (error.message.includes('Failed to fetch')) {
                errorMsg = 'Не удалось подключиться к серверу. Убедитесь, что сервер запущен.';
            }
            
            console.error('Ошибка запроса:', error);
            showError(errorMsg);
        } finally {
            // Восстанавливаем кнопку
            submitBtn.disabled = false;
            loader.style.display = 'none';
            document.querySelector('.btn-text').textContent = 'Обработать с помощью ИИ';
            progressSteps.style.display = 'none';
        }
    });

    function updateProgressStep(stepNumber) {
        // Деактивируем все шаги
        for (let i = 1; i <= 3; i++) {
            const step = document.getElementById(`step${i}`);
            if (step) {
                step.classList.remove('active', 'completed');
            }
        }
        
        // Активируем текущий шаг
        const currentStep = document.getElementById(`step${stepNumber}`);
        if (currentStep) {
            currentStep.classList.add('active');
        }
        
        // Отмечаем предыдущие как завершенные
        for (let i = 1; i < stepNumber; i++) {
            const step = document.getElementById(`step${i}`);
            if (step) {
                step.classList.remove('active');
                step.classList.add('completed');
            }
        }
    }
    
    function completeAllSteps() {
        for (let i = 1; i <= 3; i++) {
            const step = document.getElementById(`step${i}`);
            if (step) {
                step.classList.remove('active');
                step.classList.add('completed');
            }
        }
    }
    
    function showSuccess(data) {
        resultMessage.textContent = data.message;
        
        // Форматируем размер файла
        const sizeKB = (data.size / 1024).toFixed(2);
        const sizeMB = (data.size / (1024 * 1024)).toFixed(2);
        const sizeText = data.size > 1024 * 1024 ? `${sizeMB} МБ` : `${sizeKB} КБ`;
        
        // Форматируем размер Excel файла (если есть)
        let excelSizeText = '';
        if (data.excel_size && data.excel_size > 0) {
            const excelSizeKB = (data.excel_size / 1024).toFixed(2);
            const excelSizeMB = (data.excel_size / (1024 * 1024)).toFixed(2);
            excelSizeText = data.excel_size > 1024 * 1024 ? `${excelSizeMB} МБ` : `${excelSizeKB} КБ`;
        }
        
        fileInfo.innerHTML = `
            <p><strong>JSON файл:</strong> ${data.filename} (${sizeText})</p>
            ${data.excel_filename ? `<p><strong>Excel файл:</strong> ${data.excel_filename} (${excelSizeText})</p>` : ''}
        `;
        
        // Показываем информацию об использовании токенов
        if (data.usage) {
            usageInfo.style.display = 'block';
            usageInfo.innerHTML = `
                <h4>📊 Использование токенов:</h4>
                <p><strong>Промпт:</strong> ${data.usage.prompt_tokens || 0} токенов</p>
                <p><strong>Ответ:</strong> ${data.usage.completion_tokens || 0} токенов</p>
                <p><strong>Всего:</strong> ${data.usage.total_tokens || 0} токенов</p>
            `;
        } else {
            usageInfo.style.display = 'none';
        }
        
        // Настраиваем ссылку на JSON
        downloadJsonLink.href = data.download_url;
        downloadJsonLink.download = data.filename;
        
        // Настраиваем ссылку на Excel (если есть)
        if (data.excel_download_url && data.excel_filename) {
            downloadExcelLink.href = data.excel_download_url;
            downloadExcelLink.download = data.excel_filename;
            downloadExcelLink.style.display = 'inline-block';
        } else {
            downloadExcelLink.style.display = 'none';
        }
        
        resultSection.style.display = 'block';
        errorBox.style.display = 'none';
        
        // Прокручиваем к результату
        resultSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    function showError(message) {
        errorMessage.textContent = message;
        errorBox.style.display = 'block';
        resultSection.style.display = 'none';
        
        // Прокручиваем к ошибке
        errorBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
});

