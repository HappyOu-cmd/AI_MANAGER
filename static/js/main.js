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
    
    // Глобальная переменная для интервала polling
    let statusPollInterval = null;
    let currentTaskId = null; // Текущий task_id
    
    // Управление боковой панелью на мобильных
    const menuToggle = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');
    
    if (menuToggle && sidebar) {
        menuToggle.addEventListener('click', function() {
            sidebar.classList.toggle('open');
        });
        
        // Закрываем при клике вне панели
        document.addEventListener('click', function(e) {
            if (window.innerWidth <= 1024 && 
                sidebar.classList.contains('open') && 
                !sidebar.contains(e.target) && 
                !menuToggle.contains(e.target)) {
                sidebar.classList.remove('open');
            }
        });
    }

    // Drag and drop для загрузки файлов
    const uploadArea = document.getElementById('uploadArea');
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, () => {
            uploadArea.style.borderColor = 'var(--primary-red)';
            uploadArea.style.background = 'var(--primary-red-lighter)';
            uploadArea.style.transform = 'scale(1.02)';
        }, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, () => {
            uploadArea.style.borderColor = 'var(--gray-300)';
            uploadArea.style.background = 'var(--gray-50)';
            uploadArea.style.transform = 'scale(1)';
        }, false);
    });
    
    uploadArea.addEventListener('drop', handleDrop, false);
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            fileInput.files = files;
            updateFileName(files[0]);
        }
    }
    
    // Обновление имени файла при выборе
    function updateFileName(file) {
        if (file) {
            fileName.textContent = file.name;
            fileName.style.color = 'var(--primary-red)';
            fileName.style.fontWeight = '600';
        } else {
            fileName.textContent = 'Файл не выбран';
            fileName.style.color = 'var(--text-light)';
            fileName.style.fontWeight = 'normal';
        }
        
        // Скрываем предыдущие результаты
        resultSection.style.display = 'none';
        errorBox.style.display = 'none';
    }
    
    fileInput.addEventListener('change', function(e) {
        updateFileName(e.target.files[0]);
    });
    
    // Восстановление прогресса при загрузке страницы
    async function restoreProgress() {
        const savedTaskId = localStorage.getItem('currentTaskId');
        if (savedTaskId) {
            console.log('🔄 Проверка сохраненной задачи:', savedTaskId);
            currentTaskId = savedTaskId;
            
            // Проверяем статус задачи на сервере
            try {
                const response = await fetch(`/api/status/${savedTaskId}`);
                if (response.ok) {
                    const status = await response.json();
                    console.log('✅ Задача найдена, статус:', status.status);
                    
                    // Если задача завершена, отменена или с ошибкой, очищаем
                    if (status.status === 'completed' || status.status === 'error' || status.status === 'cancelled') {
                        console.log('ℹ️ Задача уже завершена, очищаем localStorage');
                        localStorage.removeItem('currentTaskId');
                        localStorage.removeItem('taskStartTime');
                        currentTaskId = null;
                        return;
                    }
                    
                    // Если задача активна, показываем UI и запускаем polling
                    console.log('🔄 Восстановление прогресса для активной задачи');
                    submitBtn.disabled = true;
                    loader.style.display = 'inline';
                    document.querySelector('.btn-text').textContent = 'Обработка...';
                    progressSteps.style.display = 'block';
                    
                    // Показываем кнопку остановки
                    const cancelBtn = document.getElementById('cancelBtn');
                    if (cancelBtn) {
                        cancelBtn.style.display = 'inline-block';
                    }
                    
                    // Запускаем polling для восстановления статуса
                    startStatusPolling(savedTaskId);
                } else if (response.status === 404) {
                    // Задача не найдена - очищаем localStorage
                    console.log('ℹ️ Задача не найдена на сервере, очищаем localStorage');
                    localStorage.removeItem('currentTaskId');
                    localStorage.removeItem('taskStartTime');
                    currentTaskId = null;
                } else {
                    console.warn('⚠️ Ошибка проверки статуса:', response.status);
                    // При ошибке тоже очищаем, чтобы не показывать ложный прогресс
                    localStorage.removeItem('currentTaskId');
                    localStorage.removeItem('taskStartTime');
                    currentTaskId = null;
                }
            } catch (error) {
                console.warn('⚠️ Ошибка при проверке статуса задачи:', error);
                // При ошибке очищаем localStorage
                localStorage.removeItem('currentTaskId');
                localStorage.removeItem('taskStartTime');
                currentTaskId = null;
            }
        }
    }
    
    // Вызываем восстановление при загрузке
    restoreProgress();
    
    // Обработчик кнопки остановки
    const cancelBtn = document.getElementById('cancelBtn');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', async function() {
            if (!currentTaskId) {
                console.warn('⚠️ Нет активной задачи для остановки');
                return;
            }
            
            if (!confirm('Вы уверены, что хотите остановить обработку?')) {
                return;
            }
            
            try {
                console.log('🛑 Отправка запроса на остановку для task_id:', currentTaskId);
                const response = await fetch(`/api/status/${currentTaskId}/cancel`, {
                    method: 'POST'
                });
                
                if (response.ok) {
                    const result = await response.json();
                    console.log('✅ Обработка остановлена:', result);
                    showError('Обработка остановлена пользователем');
                    
                    // Очищаем сохраненный task_id
                    localStorage.removeItem('currentTaskId');
                    localStorage.removeItem('taskStartTime');
                    currentTaskId = null;
                    
                    // Скрываем кнопку остановки
                    cancelBtn.style.display = 'none';
                    
                    // Останавливаем polling
                    if (statusPollInterval) {
                        clearInterval(statusPollInterval);
                        statusPollInterval = null;
                    }
                } else {
                    console.error('❌ Ошибка остановки обработки:', response.status);
                    alert('Не удалось остановить обработку. Попробуйте обновить страницу.');
                }
            } catch (error) {
                console.error('❌ Ошибка при остановке обработки:', error);
                alert('Ошибка при остановке обработки: ' + error.message);
            }
        });
    }

    // Обработка отправки формы
    uploadForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        console.log('📝 Форма отправлена');
        
        const file = fileInput.files[0];
        if (!file) {
            console.error('❌ Файл не выбран');
            showError('Пожалуйста, выберите файл');
            return;
        }
        
        console.log('✅ Файл выбран:', file.name, file.size, 'байт');

        // Показываем загрузку и прогресс
        submitBtn.disabled = true;
        loader.style.display = 'inline';
        document.querySelector('.btn-text').textContent = 'Обработка...';
        resultSection.style.display = 'none';
        errorBox.style.display = 'none';
        progressSteps.style.display = 'block';
        
        // Сбрасываем все шаги
        resetProgressSteps();
        
        // Активируем первый шаг (конвертация)
        updateProgressStep('conversion');
        console.log('✅ Прогресс инициализирован');

        // Генерируем task_id на клиенте для немедленного запуска polling
        const taskId = 'task_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        currentTaskId = taskId;
        
        // Сохраняем task_id в localStorage
        localStorage.setItem('currentTaskId', taskId);
        localStorage.setItem('taskStartTime', Date.now().toString());
        
        // Очищаем предыдущий интервал если есть
        if (statusPollInterval) {
            clearInterval(statusPollInterval);
            statusPollInterval = null;
        }
        console.log('🆔 Task ID сгенерирован:', taskId);
        
        // Создаем FormData
        const formData = new FormData();
        formData.append('file', file);
        formData.append('task_id', taskId);  // Отправляем task_id с запросом
        
        // Добавляем выбранный сценарий
        const scenarioId = document.getElementById('scenarioSelect').value;
        formData.append('scenario_id', scenarioId);
        console.log('📋 Сценарий выбран:', scenarioId);
        
        // Добавляем выбранный AI провайдер
        const aiProvider = document.getElementById('aiProvider').value;
        formData.append('ai_provider', aiProvider);
        console.log('🤖 AI провайдер выбран:', aiProvider);
        
        // Загружаем информацию о сценарии для показа правильных шагов (не блокируем отправку)
        loadScenarioSteps(scenarioId).catch(err => {
            console.warn('⚠️ Не удалось загрузить информацию о сценарии:', err);
        });
        
        // Запускаем polling сразу, до отправки запроса
        console.log('🔄 Запуск polling...');
        startStatusPolling(taskId);
        
        try {
            console.log('📤 Отправка запроса на /upload...');
            console.log('📤 Параметры:', {
                file: file.name,
                file_size: file.size,
                task_id: taskId,
                scenario_id: scenarioId,
                ai_provider: aiProvider
            });
            
            // Запускаем запрос
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            
            console.log('📥 Получен ответ:', response.status, response.statusText);
            
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
            
            // Останавливаем polling после получения результата
            if (statusPollInterval) {
                clearInterval(statusPollInterval);
                statusPollInterval = null;
                console.log('✅ Polling остановлен после получения ответа от /upload');
            }
            
            // Очищаем сохраненный task_id при успехе
            if (response.ok && data.success) {
                localStorage.removeItem('currentTaskId');
                localStorage.removeItem('taskStartTime');
                currentTaskId = null;
                
                // Скрываем кнопку остановки
                const cancelBtn = document.getElementById('cancelBtn');
                if (cancelBtn) {
                    cancelBtn.style.display = 'none';
                }
                
                // Завершаем все шаги
                completeAllProgressSteps();
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
            // Кнопка будет восстановлена после завершения обработки через polling
            // или в showSuccess/showError
        }
    });
    
    function startStatusPolling(taskId) {
        console.log('🔄 Запуск polling для task_id:', taskId);
        
        // Очищаем предыдущий интервал если есть (используем глобальную переменную)
        if (statusPollInterval) {
            clearInterval(statusPollInterval);
            statusPollInterval = null;
        }
        
        // Показываем блок метрик
        const metricsBox = document.getElementById('metricsBox');
        if (metricsBox) {
            metricsBox.style.display = 'block';
        }
        
        // Показываем прогресс-шаги
        const progressSteps = document.getElementById('progressSteps');
        if (progressSteps) {
            progressSteps.style.display = 'block';
        }
        
        // Показываем кнопку остановки
        const cancelBtn = document.getElementById('cancelBtn');
        if (cancelBtn) {
            cancelBtn.style.display = 'inline-block';
        }
        
        // Функция для обновления статуса
        const updateStatus = async () => {
            try {
                const response = await fetch(`/api/status/${taskId}`);
                if (response.ok) {
                    const status = await response.json();
                    console.log('📊 Статус обновлен:', status.stage, status.message, status.progress + '%');
                    updateProgressFromStatus(status);
                    
                    // Если обработка завершена или ошибка, останавливаем polling
                    if (status.status === 'completed' || status.status === 'error' || status.status === 'cancelled') {
                        console.log('✅ Обработка завершена, останавливаем polling');
                        if (statusPollInterval) {
                            clearInterval(statusPollInterval);
                            statusPollInterval = null;
                        }
                        
                        // Очищаем сохраненный task_id
                        localStorage.removeItem('currentTaskId');
                        localStorage.removeItem('taskStartTime');
                        currentTaskId = null;
                        
                        // Скрываем кнопку остановки
                        const cancelBtn = document.getElementById('cancelBtn');
                        if (cancelBtn) {
                            cancelBtn.style.display = 'none';
                        }
                        
                        // Восстанавливаем кнопку
                        submitBtn.disabled = false;
                        loader.style.display = 'none';
                        const btnText = document.querySelector('.btn-text');
                        if (btnText) {
                            btnText.textContent = 'Обработать с помощью ИИ';
                        }
                        
                        if (status.status === 'error') {
                            showError(status.message || 'Произошла ошибка при обработке');
                        } else if (status.status === 'cancelled') {
                            showError('Обработка отменена пользователем');
                        }
                    }
                } else if (response.status === 404) {
                    // Если задача не найдена, но мы уже видели статус "processing" или "completed",
                    // значит задача завершилась и статус был удален
                    // Проверяем, не завершилась ли обработка (если прошло больше 30 секунд с начала)
                    const taskStartTime = localStorage.getItem('taskStartTime');
                    if (taskStartTime) {
                        const elapsed = (Date.now() - parseInt(taskStartTime)) / 1000;
                        if (elapsed > 30) {
                            // Задача, вероятно, завершилась, но статус удален
                            // Пытаемся получить результат через основной endpoint
                            console.log('⏳ Задача не найдена, но прошло достаточно времени. Проверяем результаты...');
                            // Не останавливаем polling сразу, продолжаем попытки еще немного
                        } else {
                            console.log('⏳ Задача еще не создана на сервере, ожидание...');
                        }
                    } else {
                        console.log('⏳ Задача еще не создана на сервере, ожидание...');
                    }
                } else {
                    console.warn('⚠️ Ошибка получения статуса:', response.status, response.statusText);
                }
            } catch (error) {
                console.warn('⚠️ Ошибка получения статуса:', error);
            }
        };
        
        // Обновляем сразу
        updateStatus();
        
        // Затем каждые 1 секунду для более быстрого обновления
        statusPollInterval = setInterval(updateStatus, 1000);
        console.log('✅ Polling запущен, интервал: 1 секунда');
    }
    
    function updateProgressFromStatus(status) {
        // Обновляем прогресс шагов
        const stage = status.stage || '';
        
        // Маппинг стадий на шаги
        const stageMap = {
            'conversion': 'conversion',
            'main_prompt': 'main',
            'instrument_prompt': 'instrument',
            'tooling_prompt': 'tooling',
            'services_prompt': 'services',
            'spare_parts_prompt': 'spare_parts'
        };
        
        // Обновляем текущий шаг
        if (stage in stageMap) {
            const stepId = stageMap[stage];
            updateProgressStep(stepId);
        }
        
        // Обновляем прогресс-бар если есть
        const progressBar = document.getElementById('progressBar');
        if (progressBar && status.progress !== undefined) {
            progressBar.style.width = `${status.progress}%`;
            // Убираем textContent, так как прогресс-бар теперь без текста
        }
        
        // Обновляем сообщение
        const statusMessage = document.getElementById('statusMessage');
        if (statusMessage) {
            statusMessage.textContent = status.message || 'Обработка...';
        }
        
        // Обновляем метрики
        updateMetrics(status.metrics || {});
        
        // Если обработка завершена, останавливаем polling
        if (status.status === 'completed' || status.status === 'error') {
            if (statusPollInterval) {
                clearInterval(statusPollInterval);
                statusPollInterval = null;
            }
            
            if (status.status === 'completed') {
                completeAllProgressSteps();
            }
        }
    }
    
    function updateMetrics(metrics) {
        const metricsContainer = document.getElementById('metricsContainer');
        if (!metricsContainer) return;
        
        let html = '';
        
        if (metrics.prompt_size) {
            const sizeKB = (metrics.prompt_size / 1024).toFixed(1);
            html += `<div class="metric-item">
                <span class="metric-label">Размер промпта</span>
                <span class="metric-value">${sizeKB} КБ (${metrics.prompt_size.toLocaleString()} символов)</span>
            </div>`;
        }
        
        if (metrics.tokens_used) {
            html += `<div class="metric-item">
                <span class="metric-label">Токенов использовано</span>
                <span class="metric-value">${metrics.tokens_used.toLocaleString()}</span>
            </div>`;
        }
        
        if (metrics.prompt_tokens) {
            html += `<div class="metric-item">
                <span class="metric-label">Токенов в промпте</span>
                <span class="metric-value">${metrics.prompt_tokens.toLocaleString()}</span>
            </div>`;
        }
        
        if (metrics.completion_tokens) {
            html += `<div class="metric-item">
                <span class="metric-label">Токенов в ответе</span>
                <span class="metric-value">${metrics.completion_tokens.toLocaleString()}</span>
            </div>`;
        }
        
        if (metrics.time_elapsed) {
            const minutes = Math.floor(metrics.time_elapsed / 60);
            const seconds = Math.floor(metrics.time_elapsed % 60);
            html += `<div class="metric-item">
                <span class="metric-label">Время обработки</span>
                <span class="metric-value">${minutes}м ${seconds}с</span>
            </div>`;
        }
        
        metricsContainer.innerHTML = html;
    }

    function resetProgressSteps() {
        const stepIds = ['conversion', 'main', 'instrument', 'tooling', 'services', 'spare_parts'];
        stepIds.forEach(stepId => {
            const step = document.getElementById(`step_${stepId}`);
            if (step) {
                step.classList.remove('active', 'completed');
            }
        });
    }
    
    function updateProgressStep(stepId) {
        const step = document.getElementById(`step_${stepId}`);
        if (step) {
            // Показываем шаг если он скрыт
            step.style.display = 'block';
            // Отмечаем как активный
            step.classList.add('active');
            step.classList.remove('completed');
        }
        
        // Отмечаем предыдущие шаги как завершенные
        const stepOrder = ['conversion', 'main', 'instrument', 'tooling', 'services', 'spare_parts'];
        const currentIndex = stepOrder.indexOf(stepId);
        
        for (let i = 0; i < currentIndex; i++) {
            const prevStep = document.getElementById(`step_${stepOrder[i]}`);
            if (prevStep) {
                prevStep.classList.remove('active');
                prevStep.classList.add('completed');
            }
        }
    }
    
    function completeProgressStep(stepId) {
        const step = document.getElementById(`step_${stepId}`);
        if (step) {
            step.classList.remove('active');
            step.classList.add('completed');
        }
    }
    
    function completeAllProgressSteps() {
        const stepIds = ['conversion', 'main', 'instrument', 'tooling', 'services', 'spare_parts'];
        stepIds.forEach(stepId => {
            const step = document.getElementById(`step_${stepId}`);
            if (step && step.style.display !== 'none') {
                step.classList.remove('active');
                step.classList.add('completed');
            }
        });
    }
    
    async function loadScenarioSteps(scenarioId) {
        try {
            const response = await fetch(`/api/scenarios/${scenarioId}`);
            if (response.ok) {
                const scenario = await response.json();
                
                // Показываем/скрываем шаги на основе включенных промптов
                const stepMap = {
                    'main': 'main',
                    'instrument': 'instrument',
                    'tooling': 'tooling',
                    'services': 'services',
                    'spare_parts': 'spare_parts'
                };
                
                // Всегда показываем конвертацию и основной промпт
                document.getElementById('step_conversion').style.display = 'block';
                document.getElementById('step_main').style.display = 'block';
                
                // Показываем дополнительные шаги только если промпты включены
                for (const [promptType, stepId] of Object.entries(stepMap)) {
                    if (promptType === 'main') continue; // Уже показали
                    
                    const step = document.getElementById(`step_${stepId}`);
                    if (step) {
                        const isEnabled = scenario.prompts && 
                                        scenario.prompts[promptType] && 
                                        scenario.prompts[promptType].enabled;
                        step.style.display = isEnabled ? 'block' : 'none';
                    }
                }
            }
        } catch (error) {
            console.warn('Не удалось загрузить информацию о сценарии:', error);
            // В случае ошибки показываем все шаги
            const stepIds = ['conversion', 'main', 'instrument', 'tooling', 'services', 'spare_parts'];
            stepIds.forEach(stepId => {
                const step = document.getElementById(`step_${stepId}`);
                if (step) {
                    step.style.display = 'block';
                }
            });
        }
    }
    
    function showSuccess(data) {
        // Восстанавливаем кнопку
        submitBtn.disabled = false;
        loader.style.display = 'none';
        const btnText = document.querySelector('.btn-text');
        if (btnText) {
            btnText.textContent = 'Обработать с помощью ИИ';
        }
        
        if (resultMessage) {
            resultMessage.textContent = data.message;
        }
        
        // Формируем информацию о файлах
        let fileInfoHTML = '';
        let downloadButtonsHTML = '';
        
        // Основной результат (JSON + Excel)
        if (data.results && data.results.main) {
            const main = data.results.main;
            const jsonSizeKB = (main.json_size / 1024).toFixed(2);
            const jsonSizeMB = (main.json_size / (1024 * 1024)).toFixed(2);
            const jsonSizeText = main.json_size > 1024 * 1024 ? `${jsonSizeMB} МБ` : `${jsonSizeKB} КБ`;
            
            fileInfoHTML += `<div class="file-info-item">
                <span class="file-info-label">JSON файл</span>
                <span class="file-info-value">${main.json_file} (${jsonSizeText})</span>
            </div>`;
            downloadButtonsHTML += `<a href="${main.json_url}" class="btn btn-success" download>📥 Скачать JSON</a>`;
            
            if (main.excel_file) {
                const excelSizeKB = (main.excel_size / 1024).toFixed(2);
                const excelSizeMB = (main.excel_size / (1024 * 1024)).toFixed(2);
                const excelSizeText = main.excel_size > 1024 * 1024 ? `${excelSizeMB} МБ` : `${excelSizeKB} КБ`;
                
                fileInfoHTML += `<div class="file-info-item">
                    <span class="file-info-label">Excel файл</span>
                    <span class="file-info-value">${main.excel_file} (${excelSizeText})</span>
                </div>`;
                
                // Показываем информацию о листах
                if (main.sheets && main.sheets.length > 0) {
                    fileInfoHTML += `<div class="file-info-item">
                        <span class="file-info-label">Листы</span>
                        <span class="file-info-value">${main.sheets.join(', ')}</span>
                    </div>`;
                }
                
                downloadButtonsHTML += `<a href="${main.excel_url}" class="btn btn-success" download>📊 Скачать Excel</a>`;
            }
        }
        
        if (fileInfo) {
            fileInfo.innerHTML = fileInfoHTML || '<div class="file-info-item"><span class="file-info-label">Нет информации о файлах</span></div>';
        }
        
        // Обновляем кнопки скачивания
        const downloadButtons = document.getElementById('downloadButtons');
        if (downloadButtons) {
            downloadButtons.innerHTML = downloadButtonsHTML;
        }
        
        resultSection.style.display = 'block';
        errorBox.style.display = 'none';
        
        // Прокручиваем к результату
        resultSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    function showError(message) {
        // Восстанавливаем кнопку
        submitBtn.disabled = false;
        loader.style.display = 'none';
        const btnText = document.querySelector('.btn-text');
        if (btnText) {
            btnText.textContent = 'Обработать с помощью ИИ';
        }
        
        if (errorMessage) {
            errorMessage.textContent = message;
        }
        errorBox.style.display = 'block';
        resultSection.style.display = 'none';
        
        // Прокручиваем к ошибке
        errorBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
});

