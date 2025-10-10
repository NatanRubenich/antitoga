// Configuração da API
const API_BASE_URL = 'http://localhost:8001';

// Função para alternar entre painéis
function showPanel(panelName) {
    // Fade out do painel atual
    const currentPanel = document.querySelector('.panel-content:not(.hidden)');
    if (currentPanel) {
        currentPanel.style.opacity = '0';
        currentPanel.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            currentPanel.classList.add('hidden');
            currentPanel.style.opacity = '';
            currentPanel.style.transform = '';
        }, 200);
    }
    
    // Remover classe active de todos os botões de navegação
    document.querySelectorAll('[id^="btn-nav-"]').forEach(btn => {
        btn.classList.remove('bg-primary', 'text-white', 'font-bold', 'shadow-lg', 'shadow-primary/30', 'active-nav');
        btn.classList.add('hover:bg-primary/20', 'dark:hover:bg-primary/20', 'text-gray-700', 'dark:text-gray-300', 'font-medium');
    });
    
    // Mostrar novo painel com delay para animação
    setTimeout(() => {
        const newPanel = document.getElementById(`panel-${panelName}`);
        newPanel.classList.remove('hidden');
        
        // Trigger reflow para garantir que a animação funcione
        void newPanel.offsetWidth;
        
        // Adicionar classe active ao botão clicado
        const activeBtn = document.getElementById(`btn-nav-${panelName}`);
        activeBtn.classList.add('bg-primary', 'text-white', 'font-bold', 'shadow-lg', 'shadow-primary/30', 'active-nav');
        activeBtn.classList.remove('hover:bg-primary/20', 'dark:hover:bg-primary/20', 'text-gray-700', 'dark:text-gray-300', 'font-medium');
    }, 250);
}

// Executar Lançar Pareceres (STREAMING EM TEMPO REAL - NOVO, não altera o existente)
function executePareceresStream() {
    const logId = 'logs-pareceres';
    const btnId = 'btn-pareceres';

    const username = document.getElementById('pareceres-username').value;
    const password = document.getElementById('pareceres-password').value;
    const codigo_turma = document.getElementById('pareceres-turma').value;
    const trimestre_referencia = document.getElementById('pareceres-trimestre').value;

    if (!username || !password || !codigo_turma) {
        addLog(logId, 'Por favor, preencha todos os campos obrigatórios!', 'error');
        return;
    }

    clearLogs(logId);
    setButtonState(btnId, true);
    addLog(logId, '🔗 Conectando ao servidor (pareceres) para streaming...', 'info');

    const params = new URLSearchParams({
        username,
        password,
        codigo_turma,
        trimestre_referencia,
    });

    const url = `${API_BASE_URL}/lancar-pareceres-por-nota-stream?${params}`;

    const eventSource = new EventSource(url);

    eventSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'log') {
                let type = 'info';
                if (data.message.includes('✅') || data.message.includes('sucesso')) type = 'success';
                else if (data.message.includes('❌') || data.message.includes('Erro')) type = 'error';
                else if (data.message.includes('⚠️') || data.message.includes('Aviso')) type = 'warning';
                addLog(logId, data.message, type);
            } else if (data.type === 'done') {
                addLog(logId, data.message, data.success ? 'success' : 'error');
                if (data.success) addLog(logId, '✅ Processo concluído com sucesso!', 'success');
                eventSource.close();
                setButtonState(btnId, false);
            }
        } catch (e) {
            console.error('Erro ao parsear JSON (pareceres stream):', e);
        }
    };

    eventSource.onerror = (error) => {
        console.error('EventSource error (pareceres):', error);
        addLog(logId, '❌ Erro de conexão com o servidor (pareceres)', 'error');
        addLog(logId, 'Verifique se a API está rodando em http://localhost:8001', 'warning');
        eventSource.close();
        setButtonState(btnId, false);
    };

    eventSource.onopen = () => {
        addLog(logId, '✅ Conexão estabelecida, aguardando logs (pareceres)...', 'success');
    };
}

// Função para adicionar log
function addLog(logElementId, message, type = 'info') {
    const logContainer = document.getElementById(logElementId);
    const timestamp = new Date().toLocaleTimeString('pt-BR');
    
    let color = 'text-gray-700';
    let icon = '•';
    
    if (type === 'success') {
        color = 'text-green-600';
        icon = '✓';
    } else if (type === 'error') {
        color = 'text-red-600';
        icon = '✗';
    } else if (type === 'warning') {
        color = 'text-yellow-600';
        icon = '⚠';
    }
    
    const logEntry = document.createElement('div');
    logEntry.className = `mb-1 ${color} log-entry`;
    logEntry.innerHTML = `<span class="text-gray-400">[${timestamp}]</span> ${icon} ${message}`;
    
    // Remover mensagem placeholder se existir
    const placeholder = logContainer.querySelector('.text-gray-400');
    if (placeholder && placeholder.textContent.includes('Logs serão exibidos aqui')) {
        logContainer.innerHTML = '';
    }
    
    logContainer.appendChild(logEntry);
    
    // Scroll suave para o final
    logContainer.scrollTo({
        top: logContainer.scrollHeight,
        behavior: 'smooth'
    });
}

// Função para limpar logs
function clearLogs(logElementId) {
    const logContainer = document.getElementById(logElementId);
    logContainer.innerHTML = '<p class="text-gray-400">Logs serão exibidos aqui...</p>';
}

// Função para desabilitar/habilitar botão
function setButtonState(buttonId, loading) {
    const button = document.getElementById(buttonId);
    
    if (loading) {
        button.disabled = true;
        button.style.transform = 'scale(0.95)';
        button.innerHTML = `
            <div class="spinner"></div>
            <span>Executando...</span>
        `;
        setTimeout(() => {
            button.style.transform = 'scale(1)';
        }, 200);
    } else {
        button.disabled = false;
        button.style.transform = 'scale(0.95)';
        button.innerHTML = `
            <span class="material-symbols-outlined text-3xl">play_arrow</span>
            <span>Executar</span>
        `;
        setTimeout(() => {
            button.style.transform = 'scale(1)';
        }, 200);
    }
}

// Função para converter data para formato DD/MM/YYYY
function formatDate(dateString) {
    const date = new Date(dateString);
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    return `${day}/${month}/${year}`;
}

// Função helper para exibir logs da API
function displayApiLogs(logId, logs) {
    if (logs && logs.length > 0) {
        logs.forEach(log => {
            // Detectar tipo de log baseado no conteúdo
            let type = 'info';
            if (log.includes('✅') || log.includes('sucesso')) type = 'success';
            else if (log.includes('❌') || log.includes('Erro')) type = 'error';
            else if (log.includes('⚠️') || log.includes('Aviso')) type = 'warning';
            
            addLog(logId, log, type);
        });
    }
}

// Executar Lançar Conceito Inteligente (COM STREAMING EM TEMPO REAL)
function executeInteligente() {
    const logId = 'logs-inteligente';
    const btnId = 'btn-inteligente';
    
    // Coletar dados do formulário
    const username = document.getElementById('inteligente-username').value;
    const password = document.getElementById('inteligente-password').value;
    const codigo_turma = document.getElementById('inteligente-turma').value;
    const trimestre_referencia = document.getElementById('inteligente-trimestre').value;
    const atitude_observada = document.getElementById('inteligente-atitude').value;
    
    // Validação
    if (!username || !password || !codigo_turma) {
        addLog(logId, 'Por favor, preencha todos os campos obrigatórios!', 'error');
        return;
    }
    
    clearLogs(logId);
    setButtonState(btnId, true);
    
    addLog(logId, '🔗 Conectando ao servidor para streaming...', 'info');
    
    // Construir URL com query parameters
    const trocarCheckbox = document.getElementById('inteligente-trocar-c-ne');
    const trocar_c_por_ne = trocarCheckbox ? !!trocarCheckbox.checked : false; // fallback seguro = false
    addLog(logId, `Flag 'Trocar C→NE' enviada: ${trocar_c_por_ne}`, 'info');
    const params = new URLSearchParams({
        username,
        password,
        codigo_turma,
        trimestre_referencia,
        atitude_observada,
        conceito_habilidade: 'B',
        trocar_c_por_ne
    });
    
    const url = `${API_BASE_URL}/lancar-conceito-inteligente-stream?${params}`;
    
    // Usar EventSource para SSE (Server-Sent Events)
    const eventSource = new EventSource(url);
    
    eventSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            
            if (data.type === 'log') {
                // Log em tempo real!
                let type = 'info';
                if (data.message.includes('✅') || data.message.includes('sucesso')) type = 'success';
                else if (data.message.includes('❌') || data.message.includes('Erro')) type = 'error';
                else if (data.message.includes('⚠️') || data.message.includes('Aviso')) type = 'warning';
                
                addLog(logId, data.message, type);
            } else if (data.type === 'done') {
                // Processo finalizado
                addLog(logId, data.message, data.success ? 'success' : 'error');
                if (data.success) {
                    addLog(logId, '✅ Processo concluído com sucesso!', 'success');
                }
                eventSource.close();
                setButtonState(btnId, false);
            }
        } catch (e) {
            console.error('Erro ao parsear JSON:', e);
        }
    };
    
    eventSource.onerror = (error) => {
        console.error('EventSource error:', error);
        addLog(logId, '❌ Erro de conexão com o servidor', 'error');
        addLog(logId, 'Verifique se a API está rodando em http://localhost:8001', 'warning');
        eventSource.close();
        setButtonState(btnId, false);
    };
    
    eventSource.onopen = () => {
        addLog(logId, '✅ Conexão estabelecida, aguardando logs...', 'success');
    };
}

// Executar Lançar Conceito Simples
async function executeSimples() {
    const logId = 'logs-simples';
    const btnId = 'btn-simples';
    
    // Coletar dados do formulário
    const username = document.getElementById('simples-username').value;
    const password = document.getElementById('simples-password').value;
    const codigo_turma = document.getElementById('simples-turma').value;
    const trimestre_referencia = document.getElementById('simples-trimestre').value;
    const atitude_observada = document.getElementById('simples-atitude').value;
    const conceito_habilidade = document.getElementById('simples-conceito').value;
    
    // Validação
    if (!username || !password || !codigo_turma) {
        addLog(logId, 'Por favor, preencha todos os campos obrigatórios!', 'error');
        return;
    }
    
    clearLogs(logId);
    setButtonState(btnId, true);
    
    addLog(logId, 'Iniciando lançamento de conceito para todos...', 'info');
    
    try {
        const response = await fetch(`${API_BASE_URL}/lancar-conceito-trimestre`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username,
                password,
                codigo_turma,
                trimestre_referencia,
                atitude_observada,
                conceito_habilidade
            })
        });
        
        const data = await response.json();
        
        // Exibir logs da execução
        displayApiLogs(logId, data.logs);
        
        if (data.success) {
            addLog(logId, data.message, 'success');
            addLog(logId, '✅ Processo concluído com sucesso!', 'success');
        } else {
            addLog(logId, `Erro: ${data.message}`, 'error');
        }
    } catch (error) {
        addLog(logId, `Erro de conexão: ${error.message}`, 'error');
        addLog(logId, 'Verifique se a API está rodando em http://localhost:8001', 'warning');
    } finally {
        setButtonState(btnId, false);
    }
}

// Executar Lançar Conceito e RA
async function executeRA() {
    const logId = 'logs-ra';
    const btnId = 'btn-ra';
    
    // Coletar dados do formulário
    const username = document.getElementById('ra-username').value;
    const password = document.getElementById('ra-password').value;
    const codigo_turma = document.getElementById('ra-turma').value;
    const trimestre_referencia = document.getElementById('ra-trimestre').value;
    const atitude_observada = document.getElementById('ra-atitude').value;
    const conceito_habilidade = document.getElementById('ra-conceito').value;
    const inicio_ra = document.getElementById('ra-inicio').value;
    const termino_ra = document.getElementById('ra-termino').value;
    const descricao_ra = document.getElementById('ra-descricao').value;
    const nome_arquivo_ra = document.getElementById('ra-nome-arquivo').value;
    const arquivo_input = document.getElementById('ra-arquivo');
    
    // Validação
    if (!username || !password || !codigo_turma || !inicio_ra || !termino_ra || !descricao_ra || !nome_arquivo_ra) {
        addLog(logId, 'Por favor, preencha todos os campos obrigatórios!', 'error');
        return;
    }
    
    if (!arquivo_input.files || arquivo_input.files.length === 0) {
        addLog(logId, 'Por favor, selecione um arquivo PDF!', 'error');
        return;
    }
    
    clearLogs(logId);
    setButtonState(btnId, true);
    
    addLog(logId, 'Iniciando lançamento de conceitos com RA...', 'info');
    
    try {
        // Criar FormData para enviar arquivo
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);
        formData.append('codigo_turma', codigo_turma);
        formData.append('trimestre_referencia', trimestre_referencia);
        formData.append('atitude_observada', atitude_observada);
        formData.append('conceito_habilidade', conceito_habilidade);
        formData.append('inicio_ra', formatDate(inicio_ra));
        formData.append('termino_ra', formatDate(termino_ra));
        formData.append('descricao_ra', descricao_ra);
        formData.append('nome_arquivo_ra', nome_arquivo_ra);
        formData.append('arquivo_ra', arquivo_input.files[0]);
        
        addLog(logId, 'Enviando dados para a API...', 'info');
        
        const response = await fetch(`${API_BASE_URL}/lancar-conceito-inteligente-RA`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        // Exibir logs da execução
        displayApiLogs(logId, data.logs);
        
        if (data.success) {
            addLog(logId, data.message, 'success');
            addLog(logId, '✅ Processo concluído com sucesso!', 'success');
        } else {
            addLog(logId, `Erro: ${data.message}`, 'error');
        }
    } catch (error) {
        addLog(logId, `Erro de conexão: ${error.message}`, 'error');
        addLog(logId, 'Verifique se a API está rodando em http://localhost:8001', 'warning');
    } finally {
        setButtonState(btnId, false);
    }
}

// Executar Lançar Pareceres
async function executePareceres() {
    const logId = 'logs-pareceres';
    const btnId = 'btn-pareceres';
    
    // Coletar dados do formulário
    const username = document.getElementById('pareceres-username').value;
    const password = document.getElementById('pareceres-password').value;
    const codigo_turma = document.getElementById('pareceres-turma').value;
    const trimestre_referencia = document.getElementById('pareceres-trimestre').value;
    
    // Validação
    if (!username || !password || !codigo_turma) {
        addLog(logId, 'Por favor, preencha todos os campos obrigatórios!', 'error');
        return;
    }
    
    clearLogs(logId);
    setButtonState(btnId, true);
    
    addLog(logId, 'Iniciando lançamento de pareceres...', 'info');
    
    try {
        const response = await fetch(`${API_BASE_URL}/lancar-pareceres-por-nota`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username,
                password,
                codigo_turma,
                trimestre_referencia
            })
        });
        
        const data = await response.json();
        
        // Exibir logs da execução
        displayApiLogs(logId, data.logs);
        
        if (data.success) {
            addLog(logId, data.message, 'success');
            addLog(logId, '✅ Processo concluído com sucesso!', 'success');
        } else {
            addLog(logId, `Erro: ${data.message}`, 'error');
        }
    } catch (error) {
        addLog(logId, `Erro de conexão: ${error.message}`, 'error');
        addLog(logId, 'Verifique se a API está rodando em http://localhost:8001', 'warning');
    } finally {
        setButtonState(btnId, false);
    }
}

// Drag and Drop para upload de arquivo
function setupDragAndDrop() {
    const dropzone = document.getElementById('dropzone-ra');
    const fileInput = document.getElementById('ra-arquivo');
    const fileNameDisplay = document.getElementById('file-name-ra');
    
    if (!dropzone || !fileInput) return;
    
    // Prevenir comportamento padrão
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    // Highlight ao arrastar
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, () => {
            dropzone.classList.add('dragover');
        }, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, () => {
            dropzone.classList.remove('dragover');
        }, false);
    });
    
    // Handle drop
    dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
            fileInput.files = files;
            handleFiles(files);
        }
    }, false);
    
    // Handle file input change
    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });
    
    function handleFiles(files) {
        if (files.length > 0) {
            const file = files[0];
            if (file.type === 'application/pdf') {
                fileNameDisplay.textContent = `✓ Arquivo selecionado: ${file.name}`;
                fileNameDisplay.classList.add('text-green-600', 'font-medium');
            } else {
                fileNameDisplay.textContent = `✗ Erro: Apenas arquivos PDF são permitidos`;
                fileNameDisplay.classList.add('text-red-600', 'font-medium');
                fileInput.value = '';
            }
        }
    }
}

// Toggle menu mobile
function toggleMobileMenu() {
    const sidebar = document.querySelector('.sidebar-animate');
    const overlay = document.querySelector('.mobile-overlay');
    
    sidebar.classList.toggle('mobile-open');
    overlay.classList.toggle('active');
}

// Fechar menu ao clicar em um item (mobile)
function closeMobileMenuOnClick() {
    const navButtons = document.querySelectorAll('nav button');
    
    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            if (window.innerWidth <= 768) {
                const sidebar = document.querySelector('.sidebar-animate');
                const overlay = document.querySelector('.mobile-overlay');
                
                sidebar.classList.remove('mobile-open');
                overlay.classList.remove('active');
            }
        });
    });
}

// Ajustar layout em resize
function handleResize() {
    const sidebar = document.querySelector('.sidebar-animate');
    const overlay = document.querySelector('.mobile-overlay');
    
    if (window.innerWidth > 768) {
        sidebar.classList.remove('mobile-open');
        overlay.classList.remove('active');
    }
}

// Inicialização
document.addEventListener('DOMContentLoaded', () => {
    console.log('🤖 Bot de Automação SGN - Frontend carregado!');
    console.log(`📡 API Base URL: ${API_BASE_URL}`);
    
    // Configurar drag and drop
    setupDragAndDrop();
    
    // Configurar menu mobile
    closeMobileMenuOnClick();
    
    // Listener para resize
    window.addEventListener('resize', handleResize);

    // Rebind do botão de Pareceres para usar streaming automaticamente
    const btnPareceres = document.getElementById('btn-pareceres');
    if (btnPareceres) {
        btnPareceres.onclick = () => {
            try {
                executePareceresStream();
            } catch (e) {
                // Fallback para modo antigo se algo falhar
                executePareceres();
            }
        };
    }
});
