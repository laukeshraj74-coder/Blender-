/**
 * Main Renderer Process for AI Video Generator
 * Handles UI rendering, navigation, and user interactions
 */

// State management
const state = {
    currentPage: 'workspace',
    sidebarCollapsed: false,
    currentProject: null,
    attachments: [],
    isGenerating: false,
    generationStatus: null,
    config: null,
    backendConnected: false
};

// DOM Elements
const elements = {
    sidebar: document.getElementById('sidebar'),
    sidebarCollapseBtn: document.getElementById('sidebarCollapseBtn'),
    newVideoBtn: document.getElementById('newVideoBtn'),
    workspaceContent: document.getElementById('workspaceContent'),
    workspaceFooter: document.getElementById('workspaceFooter'),
    workspaceTitle: document.getElementById('workspaceTitle'),
    backendStatus: document.getElementById('backendStatus'),
    aiStatus: document.getElementById('aiStatus'),
    workspaceStatus: document.getElementById('workspaceStatus')
};

// Initialize application
async function init() {
    console.log('[Renderer] Initializing...');
    
    // Setup event listeners
    setupEventListeners();
    
    // Check backend connection
    await checkBackendConnection();
    
    // Load configuration
    await loadConfiguration();
    
    // Render initial page
    renderPage('workspace');
    
    console.log('[Renderer] Initialization complete');
}

function setupEventListeners() {
    // Sidebar collapse
    elements.sidebarCollapseBtn.addEventListener('click', toggleSidebar);
    
    // New video button
    elements.newVideoBtn.addEventListener('click', () => navigateTo('workspace'));
    
    // Navigation items
    document.querySelectorAll('.sidebar-nav-item').forEach(item => {
        item.addEventListener('click', () => {
            const page = item.dataset.page;
            navigateTo(page);
        });
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + N for new video
        if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
            e.preventDefault();
            navigateTo('workspace');
        }
    });
}

function toggleSidebar() {
    state.sidebarCollapsed = !state.sidebarCollapsed;
    elements.sidebar.classList.toggle('collapsed', state.sidebarCollapsed);
}

function navigateTo(page) {
    state.currentPage = page;
    
    // Update active nav item
    document.querySelectorAll('.sidebar-nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.page === page);
    });
    
    // Render page
    renderPage(page);
}

async function checkBackendConnection() {
    try {
        const health = await window.api.healthCheck();
        state.backendConnected = true;
        updateBackendStatus('ready', 'Connected');
    } catch (error) {
        state.backendConnected = false;
        updateBackendStatus('error', 'Disconnected');
        console.error('[Renderer] Backend connection failed:', error);
    }
}

function updateBackendStatus(status, text) {
    const statusClass = status === 'ready' ? 'status-ready' : status === 'error' ? 'status-error' : 'status-busy';
    elements.backendStatus.innerHTML = `
        <span class="status-indicator ${statusClass}">
            <span class="status-dot"></span>
            ${text}
        </span>
    `;
}

async function loadConfiguration() {
    try {
        state.config = await window.api.getConfig();
        updateAIStatus();
    } catch (error) {
        console.error('[Renderer] Failed to load config:', error);
    }
}

function updateAIStatus() {
    const hasApiKey = state.config?.ai?.api_key && state.config.ai.api_key !== '****';
    const statusClass = hasApiKey ? 'status-ready' : 'status-busy';
    const statusText = hasApiKey ? 'Configured' : 'Not configured';
    
    elements.aiStatus.innerHTML = `
        <span class="status-indicator ${statusClass}">
            <span class="status-dot"></span>
            ${statusText}
        </span>
    `;
}

// Page rendering
function renderPage(page) {
    elements.workspaceContent.innerHTML = '';
    elements.workspaceFooter.innerHTML = '';
    
    switch (page) {
        case 'workspace':
            renderWorkspace();
            break;
        case 'history':
            renderHistory();
            break;
        case 'projects':
            renderProjects();
            break;
        case 'settings':
            renderSettings();
            break;
        default:
            renderWorkspace();
    }
}

// Workspace page
function renderWorkspace() {
    elements.workspaceTitle.textContent = 'AI Video Generator';
    
    const content = document.createElement('div');
    content.className = 'workspace-empty';
    content.innerHTML = `
        <div class="empty-state">
            <div class="empty-state-icon">🎬</div>
            <h2 class="empty-state-title">Create your next video</h2>
            <p class="empty-state-description">
                Describe the video you want to create. You can also attach reference media files like images, videos, or audio.
            </p>
        </div>
    `;
    elements.workspaceContent.appendChild(content);
    
    // Render prompt composer in footer
    renderPromptComposer();
}

function renderPromptComposer() {
    const footer = document.createElement('div');
    footer.className = 'prompt-composer';
    footer.innerHTML = `
        <div class="attachments-area" id="attachmentsArea">
            <div class="attachments-empty">No attachments yet</div>
        </div>
        <div class="prompt-input-container">
            <textarea 
                class="prompt-textarea" 
                id="promptInput"
                placeholder="Describe the video you want to create..."
                rows="3"
            ></textarea>
            <div class="prompt-actions">
                <div class="prompt-actions-left">
                    <button class="attach-btn" id="attachBtn" title="Attach files">
                        <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                            <path d="M10 4V16M4 10H16"/>
                        </svg>
                    </button>
                </div>
                <div class="prompt-actions-right">
                    <button class="send-btn" id="sendBtn" disabled>
                        Generate
                        <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor">
                            <path d="M18 10L4 4V7L14 10L4 13V16L18 10Z"/>
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    `;
    elements.workspaceFooter.appendChild(footer);
    
    // Setup event listeners
    const promptInput = document.getElementById('promptInput');
    const sendBtn = document.getElementById('sendBtn');
    const attachBtn = document.getElementById('attachBtn');
    
    promptInput.addEventListener('input', () => {
        sendBtn.disabled = !promptInput.value.trim() || state.isGenerating;
    });
    
    promptInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!sendBtn.disabled) {
                handleGenerate();
            }
        }
    });
    
    sendBtn.addEventListener('click', handleGenerate);
    attachBtn.addEventListener('click', handleAttachFiles);
}

async function handleAttachFiles() {
    try {
        const result = await window.electronAPI.openFileDialog([
            { name: 'Media Files', extensions: ['mp4', 'mov', 'webm', 'avi', 'mp3', 'wav', 'm4a', 'png', 'jpg', 'jpeg', 'webp'] },
            { name: 'Video', extensions: ['mp4', 'mov', 'webm', 'avi'] },
            { name: 'Audio', extensions: ['mp3', 'wav', 'm4a'] },
            { name: 'Images', extensions: ['png', 'jpg', 'jpeg', 'webp'] }
        ]);
        
        if (result.canceled || result.filePaths.length === 0) {
            return;
        }
        
        // Add files to attachments
        for (const filePath of result.filePaths) {
            const fileName = filePath.split(/[\\/]/).pop();
            const ext = fileName.split('.').pop().toLowerCase();
            
            let type = 'other';
            if (['mp4', 'mov', 'webm', 'avi'].includes(ext)) type = 'video';
            else if (['mp3', 'wav', 'm4a'].includes(ext)) type = 'audio';
            else if (['png', 'jpg', 'jpeg', 'webp'].includes(ext)) type = 'image';
            
            state.attachments.push({
                path: filePath,
                name: fileName,
                type: type
            });
        }
        
        renderAttachments();
    } catch (error) {
        console.error('[Renderer] File selection failed:', error);
    }
}

function renderAttachments() {
    const area = document.getElementById('attachmentsArea');
    if (!area) return;
    
    if (state.attachments.length === 0) {
        area.innerHTML = '<div class="attachments-empty">No attachments yet</div>';
        return;
    }
    
    area.innerHTML = state.attachments.map((att, index) => `
        <div class="attachment-chip">
            <div class="attachment-chip-info">
                <span class="attachment-chip-name">${escapeHtml(att.name)}</span>
                <span class="attachment-chip-type">${att.type}</span>
            </div>
            <button class="attachment-chip-remove" data-index="${index}" title="Remove">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
                    <path d="M2 2L12 12M12 2L2 12"/>
                </svg>
            </button>
        </div>
    `).join('');
    
    // Add remove listeners
    area.querySelectorAll('.attachment-chip-remove').forEach(btn => {
        btn.addEventListener('click', () => {
            const index = parseInt(btn.dataset.index);
            state.attachments.splice(index, 1);
            renderAttachments();
        });
    });
}

async function handleGenerate() {
    const promptInput = document.getElementById('promptInput');
    const prompt = promptInput.value.trim();
    
    if (!prompt || state.isGenerating) return;
    
    try {
        // Create project
        const project = await window.api.createProject(prompt, state.attachments);
        state.currentProject = project;
        
        // Start generation
        await window.api.startGeneration(project.id, prompt);
        state.isGenerating = true;
        
        // Clear input
        promptInput.value = '';
        state.attachments = [];
        renderAttachments();
        
        // Show generation panel
        renderGenerationPanel();
        
        // Poll for status
        pollGenerationStatus();
        
    } catch (error) {
        console.error('[Renderer] Generation failed:', error);
        showError(error.message);
    }
}

function renderGenerationPanel() {
    elements.workspaceContent.innerHTML = '';
    
    const panel = document.createElement('div');
    panel.className = 'generation-panel';
    panel.id = 'generationPanel';
    panel.innerHTML = `
        <div class="generation-header">
            <h3 class="generation-title">Generating Video</h3>
            <span class="generation-timer" id="generationTimer">00:00</span>
        </div>
        <div class="generation-stages" id="generationStages">
            <!-- Stages will be rendered here -->
        </div>
        <div class="generation-progress-bar">
            <div class="generation-progress-fill" id="progressFill" style="width: 0%"></div>
        </div>
        <div style="margin-top: var(--spacing-md); display: flex; justify-content: flex-end;">
            <button class="generation-cancel-btn" id="cancelBtn">
                Stop Generation
            </button>
        </div>
    `;
    elements.workspaceContent.appendChild(panel);
    
    // Cancel button listener
    document.getElementById('cancelBtn').addEventListener('click', handleCancelGeneration);
    
    // Clear footer during generation
    elements.workspaceFooter.innerHTML = '';
}

async function handleCancelGeneration() {
    try {
        await window.api.cancelGeneration();
    } catch (error) {
        console.error('[Renderer] Cancel failed:', error);
    }
}

async function pollGenerationStatus() {
    const pollInterval = setInterval(async () => {
        try {
            const status = await window.api.getGenerationStatus();
            state.generationStatus = status;
            
            renderGenerationStatus(status);
            
            if (!status.is_generating) {
                clearInterval(pollInterval);
                state.isGenerating = false;
                
                // Show output panel
                setTimeout(() => {
                    renderOutputPanel(status);
                }, 500);
            }
        } catch (error) {
            console.error('[Renderer] Status poll failed:', error);
            clearInterval(pollInterval);
            state.isGenerating = false;
        }
    }, 1000);
    
    // Store interval for cleanup
    state.pollInterval = pollInterval;
}

function renderGenerationStatus(status) {
    const stagesEl = document.getElementById('generationStages');
    const progressFill = document.getElementById('progressFill');
    const timerEl = document.getElementById('generationTimer');
    
    if (!stagesEl || !progressFill) return;
    
    // Update progress bar
    progressFill.style.width = `${status.progress}%`;
    
    // Update timer
    if (timerEl && status.elapsed_time) {
        const minutes = Math.floor(status.elapsed_time / 60);
        const seconds = Math.floor(status.elapsed_time % 60);
        timerEl.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
    
    // Render stages
    if (status.stages && status.stages.length > 0) {
        stagesEl.innerHTML = status.stages.map(stage => {
            let icon = '○';
            let statusClass = 'stage-pending';
            
            if (stage.status === 'completed') {
                icon = '✓';
                statusClass = 'stage-completed';
            } else if (stage.status === 'current') {
                icon = '●';
                statusClass = 'stage-current';
            } else if (stage.status === 'error') {
                icon = '✕';
                statusClass = 'stage-error';
            }
            
            return `
                <div class="generation-stage ${statusClass}">
                    <div class="generation-stage-icon">${icon}</div>
                    <span class="generation-stage-name">${stage.name}</span>
                </div>
            `;
        }).join('');
    }
}

function renderOutputPanel(status) {
    elements.workspaceContent.innerHTML = '';
    
    const isCompleted = status.stage === 'completed';
    const isError = status.stage === 'error';
    const isCancelled = status.stage === 'cancelled';
    
    const panel = document.createElement('div');
    panel.className = 'output-panel';
    panel.innerHTML = `
        <div class="output-header">
            <h3 class="output-title">${isCompleted ? 'Generation Complete' : isError ? 'Generation Failed' : 'Generation Cancelled'}</h3>
            <div class="output-actions">
                <button class="btn btn-secondary" onclick="navigateTo('workspace')">New Video</button>
            </div>
        </div>
        ${isCompleted ? `
            <div class="video-placeholder">
                <div class="empty-state">
                    <div class="empty-state-icon">📹</div>
                    <p>Video will be available here after implementation</p>
                </div>
            </div>
            <div class="video-info">
                <div class="video-info-item">
                    <span class="video-info-label">Duration</span>
                    <span class="video-info-value">--:--</span>
                </div>
                <div class="video-info-item">
                    <span class="video-info-label">Resolution</span>
                    <span class="video-info-value">Not available</span>
                </div>
                <div class="video-info-item">
                    <span class="video-info-label">File Size</span>
                    <span class="video-info-value">--</span>
                </div>
            </div>
        ` : `
            <div class="empty-state" style="padding: var(--spacing-xl);">
                <div class="empty-state-icon">${isError ? '⚠️' : '⏸️'}</div>
                <p class="empty-state-description">${status.message || 'Generation was not completed'}</p>
            </div>
        `}
    `;
    elements.workspaceContent.appendChild(panel);
    
    // Restore footer with new video button
    elements.workspaceFooter.innerHTML = `
        <div class="prompt-composer">
            <div style="text-align: center; color: var(--text-muted);">
                Ready to create another video? Click "New Video" to start again.
            </div>
        </div>
    `;
}

// History page (placeholder)
function renderHistory() {
    elements.workspaceTitle.textContent = 'History';
    
    const content = document.createElement('div');
    content.className = 'card';
    content.innerHTML = `
        <div class="empty-state">
            <div class="empty-state-icon">📜</div>
            <h2 class="empty-state-title">Generation History</h2>
            <p class="empty-state-description">
                Your video generation history will appear here.
            </p>
        </div>
    `;
    elements.workspaceContent.appendChild(content);
    elements.workspaceFooter.innerHTML = '';
}

// Projects page (placeholder)
function renderProjects() {
    elements.workspaceTitle.textContent = 'Projects';
    
    const content = document.createElement('div');
    content.className = 'empty-state';
    content.innerHTML = `
        <div class="empty-state">
            <div class="empty-state-icon">📁</div>
            <h2 class="empty-state-title">Projects</h2>
            <p class="empty-state-description">
                Manage your video projects here.
            </p>
        </div>
    `;
    elements.workspaceContent.appendChild(content);
    elements.workspaceFooter.innerHTML = '';
}

// Settings page
async function renderSettings() {
    elements.workspaceTitle.textContent = 'Settings';
    
    const container = document.createElement('div');
    container.className = 'settings-container';
    container.innerHTML = `
        <div class="settings-header">
            <h2 class="settings-title">Settings</h2>
            <p class="settings-description">Configure your AI Video Generator preferences</p>
        </div>
        
        <!-- AI Settings -->
        <div class="settings-section">
            <div class="settings-section-header">
                <div class="settings-section-icon">🤖</div>
                <h3 class="settings-section-title">AI Provider</h3>
            </div>
            <div class="settings-form-group">
                <label class="settings-form-label">Provider</label>
                <select class="settings-form-input settings-form-select" id="aiProvider">
                    <option value="openai">OpenAI</option>
                    <option value="custom">Custom (OpenAI-compatible)</option>
                </select>
            </div>
            <div class="settings-form-group">
                <label class="settings-form-label">API Key</label>
                <input type="password" class="settings-form-input" id="apiKey" placeholder="sk-...">
                <div class="settings-form-help">Your API key is stored locally and never sent to our servers</div>
            </div>
            <div class="settings-form-group">
                <label class="settings-form-label">Base URL (for custom providers)</label>
                <input type="text" class="settings-form-input" id="baseUrl" placeholder="https://api.example.com/v1">
            </div>
            <div class="settings-form-group">
                <label class="settings-form-label">Model</label>
                <input type="text" class="settings-form-input" id="aiModel" placeholder="auto" value="auto">
                <div class="settings-form-help">Leave as "auto" for automatic model selection</div>
            </div>
            <div class="settings-actions">
                <button class="btn btn-secondary" id="testAiBtn">Test Connection</button>
            </div>
            <div id="aiTestResult"></div>
        </div>
        
        <!-- Blender Settings -->
        <div class="settings-section">
            <div class="settings-section-header">
                <div class="settings-section-icon">🎨</div>
                <h3 class="settings-section-title">Blender</h3>
            </div>
            <div class="settings-form-row">
                <div class="settings-form-group">
                    <label class="settings-form-label">Blender Executable Path</label>
                    <input type="text" class="settings-form-input" id="blenderPath" placeholder="C:\\Program Files\\Blender Foundation\\Blender 4.0\\blender.exe">
                </div>
                <button class="btn btn-secondary" id="detectBlenderBtn" style="margin-top: 28px;">Detect</button>
            </div>
            <div id="blenderDetectionResult"></div>
        </div>
        
        <!-- FFmpeg Settings -->
        <div class="settings-section">
            <div class="settings-section-header">
                <div class="settings-section-icon">🎬</div>
                <h3 class="settings-section-title">FFmpeg</h3>
            </div>
            <div class="settings-form-row">
                <div class="settings-form-group">
                    <label class="settings-form-label">FFmpeg Executable Path</label>
                    <input type="text" class="settings-form-input" id="ffmpegPath" placeholder="C:\\ffmpeg\\bin\\ffmpeg.exe">
                </div>
                <button class="btn btn-secondary" id="detectFFmpegBtn" style="margin-top: 28px;">Detect</button>
            </div>
            <div id="ffmpegDetectionResult"></div>
        </div>
        
        <!-- General Settings -->
        <div class="settings-section">
            <div class="settings-section-header">
                <div class="settings-section-icon">⚙️</div>
                <h3 class="settings-section-title">General</h3>
            </div>
            <div class="settings-form-group">
                <label class="settings-form-label">Theme</label>
                <select class="settings-form-input settings-form-select" id="theme">
                    <option value="dark">Dark</option>
                    <option value="light">Light (coming soon)</option>
                </select>
            </div>
            <div class="settings-form-group">
                <label class="settings-form-label">Default Output Directory</label>
                <input type="text" class="settings-form-input" id="outputDir" placeholder="Leave empty for default location">
            </div>
        </div>
        
        <div class="settings-actions">
            <button class="btn btn-secondary" id="resetSettingsBtn">Reset to Defaults</button>
            <button class="btn btn-primary" id="saveSettingsBtn">Save Settings</button>
        </div>
    `;
    elements.workspaceContent.appendChild(container);
    elements.workspaceFooter.innerHTML = '';
    
    // Populate current values
    populateSettingsForm();
    
    // Setup event listeners
    setupSettingsListeners();
}

function populateSettingsForm() {
    if (!state.config) return;
    
    document.getElementById('aiProvider').value = state.config.ai?.provider || 'openai';
    document.getElementById('apiKey').value = state.config.ai?.api_key || '';
    document.getElementById('baseUrl').value = state.config.ai?.base_url || '';
    document.getElementById('aiModel').value = state.config.ai?.model || 'auto';
    document.getElementById('blenderPath').value = state.config.blender?.executable_path || '';
    document.getElementById('ffmpegPath').value = state.config.ffmpeg?.executable_path || '';
    document.getElementById('theme').value = state.config.general?.theme || 'dark';
    document.getElementById('outputDir').value = state.config.general?.output_directory || '';
}

function setupSettingsListeners() {
    // Test AI connection
    document.getElementById('testAiBtn').addEventListener('click', async () => {
        const resultEl = document.getElementById('aiTestResult');
        resultEl.innerHTML = '<div class="test-result info">Testing...</div>';
        
        try {
            const result = await window.api.testAI();
            resultEl.innerHTML = `
                <div class="test-result ${result.success ? 'success' : 'error'}">
                    ${result.success ? '✓ Connection successful' : `✕ ${result.message}`}
                </div>
            `;
        } catch (error) {
            resultEl.innerHTML = `<div class="test-result error">✕ ${error.message}</div>`;
        }
    });
    
    // Detect Blender
    document.getElementById('detectBlenderBtn').addEventListener('click', async () => {
        const resultEl = document.getElementById('blenderDetectionResult');
        resultEl.innerHTML = '<div class="test-result info">Detecting...</div>';
        
        try {
            const result = await window.api.detectBlender();
            if (result.found) {
                document.getElementById('blenderPath').value = result.path;
                resultEl.innerHTML = `
                    <div class="detection-status">
                        <div class="detection-icon found">✓</div>
                        <div class="detection-info">
                            <div class="detection-label">Blender detected</div>
                            <div class="detection-path">${result.path}</div>
                            <div class="detection-path">${result.version || ''}</div>
                        </div>
                    </div>
                `;
            } else {
                resultEl.innerHTML = `
                    <div class="detection-status">
                        <div class="detection-icon not-found">✕</div>
                        <div class="detection-info">
                            <div class="detection-label">Blender not found</div>
                            <div class="detection-path">Please install Blender or specify the path manually</div>
                        </div>
                    </div>
                `;
            }
        } catch (error) {
            resultEl.innerHTML = `<div class="test-result error">✕ ${error.message}</div>`;
        }
    });
    
    // Detect FFmpeg
    document.getElementById('detectFFmpegBtn').addEventListener('click', async () => {
        const resultEl = document.getElementById('ffmpegDetectionResult');
        resultEl.innerHTML = '<div class="test-result info">Detecting...</div>';
        
        try {
            const result = await window.api.detectFFmpeg();
            if (result.found) {
                document.getElementById('ffmpegPath').value = result.path;
                resultEl.innerHTML = `
                    <div class="detection-status">
                        <div class="detection-icon found">✓</div>
                        <div class="detection-info">
                            <div class="detection-label">FFmpeg detected</div>
                            <div class="detection-path">${result.path}</div>
                            <div class="detection-path">${result.version || ''}</div>
                        </div>
                    </div>
                `;
            } else {
                resultEl.innerHTML = `
                    <div class="detection-status">
                        <div class="detection-icon not-found">✕</div>
                        <div class="detection-info">
                            <div class="detection-label">FFmpeg not found</div>
                            <div class="detection-path">Please install FFmpeg or specify the path manually</div>
                        </div>
                    </div>
                `;
            }
        } catch (error) {
            resultEl.innerHTML = `<div class="test-result error">✕ ${error.message}</div>`;
        }
    });
    
    // Save settings
    document.getElementById('saveSettingsBtn').addEventListener('click', saveSettings);
    
    // Reset settings
    document.getElementById('resetSettingsBtn').addEventListener('click', () => {
        if (confirm('Are you sure you want to reset all settings to defaults?')) {
            populateSettingsForm();
        }
    });
}

async function saveSettings() {
    const config = {
        ai: {
            provider: document.getElementById('aiProvider').value,
            api_key: document.getElementById('apiKey').value,
            base_url: document.getElementById('baseUrl').value,
            model: document.getElementById('aiModel').value
        },
        blender: {
            executable_path: document.getElementById('blenderPath').value
        },
        ffmpeg: {
            executable_path: document.getElementById('ffmpegPath').value
        },
        general: {
            theme: document.getElementById('theme').value,
            output_directory: document.getElementById('outputDir').value
        }
    };
    
    try {
        await window.api.updateConfig(config);
        state.config = await window.api.getConfig();
        updateAIStatus();
        
        // Show success message
        const saveBtn = document.getElementById('saveSettingsBtn');
        const originalText = saveBtn.textContent;
        saveBtn.textContent = 'Saved!';
        saveBtn.disabled = true;
        
        setTimeout(() => {
            saveBtn.textContent = originalText;
            saveBtn.disabled = false;
        }, 2000);
        
    } catch (error) {
        alert(`Failed to save settings: ${error.message}`);
    }
}

// Utility functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showError(message) {
    // Simple error display - can be enhanced later
    console.error('[Renderer] Error:', message);
    alert(`Error: ${message}`);
}

// Make navigateTo available globally for onclick handlers
window.navigateTo = navigateTo;

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', init);
