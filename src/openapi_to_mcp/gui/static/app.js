/**
 * OpenAPI to MCP Generator - Frontend Application
 */

// ================================
// Theme Management
// ================================

const ThemeManager = {
    STORAGE_KEY: 'openapi-mcp-theme',
    DARK: 'dark',
    LIGHT: 'light',

    init() {
        // Get saved theme or detect system preference
        const savedTheme = localStorage.getItem(this.STORAGE_KEY);
        const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

        const theme = savedTheme || (systemPrefersDark ? this.DARK : this.LIGHT);
        this.setTheme(theme);

        // Listen for system theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem(this.STORAGE_KEY)) {
                // Only auto-switch if user hasn't manually set a preference
                this.setTheme(e.matches ? this.DARK : this.LIGHT);
            }
        });

        // Setup toggle button
        const toggleBtn = document.getElementById('themeToggle');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => this.toggle());
        }
    },

    setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem(this.STORAGE_KEY, theme);

        // Update toggle button title
        const toggleBtn = document.getElementById('themeToggle');
        if (toggleBtn) {
            toggleBtn.title = theme === this.DARK ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro';
        }
    },

    toggle() {
        const currentTheme = document.documentElement.getAttribute('data-theme') || this.LIGHT;
        const newTheme = currentTheme === this.DARK ? this.LIGHT : this.DARK;
        this.setTheme(newTheme);
    },

    getCurrentTheme() {
        return document.documentElement.getAttribute('data-theme') || this.LIGHT;
    }
};

// ================================
// Validation Manager
// ================================

const ValidationManager = {
    panel: null,
    isExpanded: false,
    currentFilter: 'all',
    validationData: null,

    init() {
        this.panel = document.getElementById('validationPanel');
        if (!this.panel) return;

        const toggleBtn = document.getElementById('validationToggle');
        const expandBtn = document.getElementById('validationExpand');

        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => this.toggleExpand());
        }
        if (expandBtn) {
            expandBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleExpand();
            });
        }
    },

    async loadValidation() {
        if (!this.panel) return;

        this.panel.style.display = 'block';
        this.setLoading(true);

        try {
            const response = await fetch(apiUrl('/api/validate'));
            const data = await response.json();

            if (data.error) {
                this.setError(data.error);
                return;
            }

            this.validationData = data;
            this.render(data);
        } catch (error) {
            this.setError('Error al validar la especificación');
            console.error('Validation error:', error);
        }
    },

    setLoading(loading) {
        const icon = document.getElementById('validationIcon');
        const title = document.getElementById('validationTitle');

        if (loading) {
            icon.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <path d="M12 6v6l4 2"></path>
            </svg>`;
            icon.className = 'validation-icon loading';
            title.textContent = 'Validando...';
        }
    },

    setError(message) {
        const icon = document.getElementById('validationIcon');
        const title = document.getElementById('validationTitle');

        icon.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="15" y1="9" x2="9" y2="15"></line>
            <line x1="9" y1="9" x2="15" y2="15"></line>
        </svg>`;
        icon.className = 'validation-icon error';
        title.textContent = message;
        this.panel.className = 'validation-panel has-errors';
    },

    render(data) {
        const icon = document.getElementById('validationIcon');
        const title = document.getElementById('validationTitle');
        const errorCount = document.getElementById('errorCount');
        const warningCount = document.getElementById('warningCount');
        const suggestionCount = document.getElementById('suggestionCount');
        const issuesContainer = document.getElementById('validationIssues');

        // Update status icon and title
        if (data.valid && data.warning_count === 0) {
            icon.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                <polyline points="22 4 12 14.01 9 11.01"></polyline>
            </svg>`;
            icon.className = 'validation-icon success';
            title.textContent = 'Especificación válida';
            this.panel.className = 'validation-panel valid';
        } else if (data.error_count > 0) {
            icon.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="15" y1="9" x2="9" y2="15"></line>
                <line x1="9" y1="9" x2="15" y2="15"></line>
            </svg>`;
            icon.className = 'validation-icon error';
            title.textContent = 'Errores encontrados';
            this.panel.className = 'validation-panel has-errors';
        } else if (data.warning_count > 0) {
            icon.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                <line x1="12" y1="9" x2="12" y2="13"></line>
                <line x1="12" y1="17" x2="12.01" y2="17"></line>
            </svg>`;
            icon.className = 'validation-icon warning';
            title.textContent = 'Advertencias encontradas';
            this.panel.className = 'validation-panel has-warnings';
        } else {
            icon.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                <polyline points="22 4 12 14.01 9 11.01"></polyline>
            </svg>`;
            icon.className = 'validation-icon success';
            title.textContent = 'Especificación válida';
            this.panel.className = 'validation-panel valid';
        }

        // Update counts
        if (data.error_count > 0) {
            errorCount.textContent = `${data.error_count} error${data.error_count > 1 ? 'es' : ''}`;
            errorCount.style.display = 'inline';
        } else {
            errorCount.style.display = 'none';
        }

        if (data.warning_count > 0) {
            warningCount.textContent = `${data.warning_count} warning${data.warning_count > 1 ? 's' : ''}`;
            warningCount.style.display = 'inline';
        } else {
            warningCount.style.display = 'none';
        }

        if (data.suggestion_count > 0) {
            suggestionCount.textContent = `${data.suggestion_count} sugerencia${data.suggestion_count > 1 ? 's' : ''}`;
            suggestionCount.style.display = 'inline';
        } else {
            suggestionCount.style.display = 'none';
        }

        // Render issues
        this.renderIssues(data.issues, issuesContainer);
    },

    renderIssues(issues, container) {
        if (!issues || issues.length === 0) {
            container.innerHTML = `
                <div class="validation-empty">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                        <polyline points="22 4 12 14.01 9 11.01"></polyline>
                    </svg>
                    <p>No se encontraron problemas</p>
                </div>
            `;
            return;
        }

        const icons = {
            error: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="15" y1="9" x2="9" y2="15"></line>
                <line x1="9" y1="9" x2="15" y2="15"></line>
            </svg>`,
            warning: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                <line x1="12" y1="9" x2="12" y2="13"></line>
                <line x1="12" y1="17" x2="12.01" y2="17"></line>
            </svg>`,
            suggestion: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
                <line x1="12" y1="17" x2="12.01" y2="17"></line>
            </svg>`,
            info: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="16" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12.01" y2="8"></line>
            </svg>`
        };

        const html = issues.map(issue => `
            <div class="validation-issue ${issue.severity}">
                <div class="issue-icon ${issue.severity}">
                    ${icons[issue.severity] || icons.info}
                </div>
                <div class="issue-content">
                    <div class="issue-message">${this.escapeHtml(issue.message)}</div>
                    ${issue.path ? `<div class="issue-path">${this.escapeHtml(issue.path)}</div>` : ''}
                    ${issue.suggestion ? `<div class="issue-suggestion">${this.escapeHtml(issue.suggestion)}</div>` : ''}
                </div>
            </div>
        `).join('');

        container.innerHTML = html;
    },

    toggleExpand() {
        this.isExpanded = !this.isExpanded;
        const body = document.getElementById('validationBody');

        if (this.isExpanded) {
            body.style.display = 'block';
            this.panel.classList.add('expanded');
        } else {
            body.style.display = 'none';
            this.panel.classList.remove('expanded');
        }
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

// ================================
// Stats Manager
// ================================

const StatsManager = {
    panel: null,
    isExpanded: false,
    statsData: null,

    init() {
        this.panel = document.getElementById('statsPanel');
        if (!this.panel) return;

        const toggleBtn = document.getElementById('statsToggle');
        const expandBtn = document.getElementById('statsExpand');

        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => this.toggleExpand());
        }
        if (expandBtn) {
            expandBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleExpand();
            });
        }
    },

    async loadStats() {
        if (!this.panel) return;

        try {
            const response = await fetch(apiUrl('/api/stats'));
            const data = await response.json();

            if (data.error) {
                console.error('Error loading stats:', data.error);
                return;
            }

            this.statsData = data;
            this.panel.style.display = 'block';
            this.render(data);
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    },

    render(data) {
        // Render method bars
        this.renderMethodBars(data.methods_chart || []);

        // Render tags list
        this.renderTagsList(data.tags_chart || []);

        // Render quick stats
        this.renderQuickStats(data);
    },

    renderMethodBars(methods) {
        const container = document.getElementById('methodBars');
        if (!container) return;

        const maxCount = Math.max(...methods.map(m => m.count), 1);

        const html = methods.map(m => {
            const percentage = (m.count / maxCount) * 100;
            return `
                <div class="method-bar">
                    <span class="method-label">${m.method}</span>
                    <div class="method-bar-track">
                        <div class="method-bar-fill" style="width: ${percentage}%; background-color: ${m.color}"></div>
                    </div>
                    <span class="method-count">${m.count}</span>
                </div>
            `;
        }).join('');

        container.innerHTML = html || '<p style="color: var(--text-muted); font-size: 0.85rem;">Sin datos</p>';
    },

    renderTagsList(tags) {
        const container = document.getElementById('tagsList');
        if (!container) return;

        if (tags.length === 0) {
            container.innerHTML = '<p style="color: var(--text-muted); font-size: 0.85rem;">Sin tags definidos</p>';
            return;
        }

        const html = tags.slice(0, 6).map(t => `
            <div class="tag-item">
                <span class="tag-name">${this.escapeHtml(t.tag)}</span>
                <span class="tag-count">${t.count}</span>
            </div>
        `).join('');

        container.innerHTML = html;
    },

    renderQuickStats(data) {
        const container = document.getElementById('quickStats');
        if (!container) return;

        const html = `
            <div class="quick-stat">
                <div class="quick-stat-value">${data.total_endpoints}</div>
                <div class="quick-stat-label">Endpoints</div>
            </div>
            <div class="quick-stat">
                <div class="quick-stat-value">${data.total_paths}</div>
                <div class="quick-stat-label">Paths</div>
            </div>
            <div class="quick-stat">
                <div class="quick-stat-value">${data.deprecated_count}</div>
                <div class="quick-stat-label">Deprecated</div>
            </div>
            <div class="quick-stat">
                <div class="quick-stat-value">${data.security_schemes.length}</div>
                <div class="quick-stat-label">Security</div>
            </div>
        `;

        container.innerHTML = html;
    },

    toggleExpand() {
        this.isExpanded = !this.isExpanded;
        const body = document.getElementById('statsBody');

        if (this.isExpanded) {
            body.style.display = 'block';
            this.panel.classList.add('expanded');
        } else {
            body.style.display = 'none';
            this.panel.classList.remove('expanded');
        }
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

// ================================
// Preview Manager
// ================================

const PreviewManager = {
    modal: null,
    currentFile: null,
    files: {},

    init() {
        this.modal = document.getElementById('previewModal');
        if (!this.modal) return;

        // Close button
        const closeBtn = document.getElementById('closePreview');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.hide());
        }

        // Copy button
        const copyBtn = document.getElementById('copyCodeBtn');
        if (copyBtn) {
            copyBtn.addEventListener('click', () => this.copyCode());
        }

        // Close on overlay click
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.hide();
            }
        });

        // Close on Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal.style.display !== 'none') {
                this.hide();
            }
        });
    },

    async loadPreview() {
        if (selectedEndpoints.length === 0) {
            alert('Selecciona al menos un endpoint para generar el preview');
            return;
        }

        showLoading(true);

        try {
            const config = getConfig();
            const response = await fetch(apiUrl('/api/preview'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    selected: selectedEndpoints.map(ep => ep.key),
                    ...config
                }),
            });

            const data = await response.json();
            showLoading(false);

            if (!data.success) {
                showError(data.error || 'Error generando preview');
                return;
            }

            this.files = data.files;
            this.show(data);
        } catch (error) {
            showLoading(false);
            showError('Error de conexión: ' + error.message);
        }
    },

    show(data) {
        if (!this.modal) return;

        // Render stats
        const statsEl = document.getElementById('previewStats');
        if (statsEl && data.stats) {
            statsEl.innerHTML = `
                <div class="preview-stat">
                    <strong>${data.stats.tools_count}</strong> Tools
                </div>
                <div class="preview-stat">
                    <strong>${data.stats.resources_count}</strong> Resources
                </div>
                <div class="preview-stat">
                    <strong>${data.stats.files_count}</strong> Archivos
                </div>
            `;
        }

        // Render file list
        this.renderFileList(data.files);

        // Show first file
        const firstFile = Object.keys(data.files)[0];
        if (firstFile) {
            this.selectFile(firstFile);
        }

        this.modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    },

    hide() {
        if (!this.modal) return;
        this.modal.style.display = 'none';
        document.body.style.overflow = '';
    },

    renderFileList(files) {
        const listEl = document.getElementById('previewFileList');
        if (!listEl) return;

        const icons = {
            '.py': `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>`,
            '.txt': `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>`,
            '.md': `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>`,
        };

        const html = Object.keys(files).map(filename => {
            const ext = '.' + filename.split('.').pop();
            const icon = icons[ext] || icons['.txt'];
            const displayName = filename.split('/').pop();

            return `
                <div class="file-item" data-file="${filename}">
                    ${icon}
                    <span>${displayName}</span>
                    <span class="file-ext">${ext}</span>
                </div>
            `;
        }).join('');

        listEl.innerHTML = html;

        // Add click handlers
        listEl.querySelectorAll('.file-item').forEach(item => {
            item.addEventListener('click', () => {
                this.selectFile(item.dataset.file);
            });
        });
    },

    selectFile(filename) {
        this.currentFile = filename;

        // Update active state in file list
        const listEl = document.getElementById('previewFileList');
        if (listEl) {
            listEl.querySelectorAll('.file-item').forEach(item => {
                item.classList.toggle('active', item.dataset.file === filename);
            });
        }

        // Update file name display
        const fileNameEl = document.getElementById('previewFileName');
        if (fileNameEl) {
            fileNameEl.textContent = filename;
        }

        // Update code content
        const codeEl = document.getElementById('previewCode');
        if (codeEl && this.files[filename]) {
            codeEl.textContent = this.files[filename];
        }
    },

    copyCode() {
        if (!this.currentFile || !this.files[this.currentFile]) return;

        navigator.clipboard.writeText(this.files[this.currentFile]).then(() => {
            const copyBtn = document.getElementById('copyCodeBtn');
            if (copyBtn) {
                const originalText = copyBtn.innerHTML;
                copyBtn.innerHTML = `
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="20 6 9 17 4 12"></polyline>
                    </svg>
                    ¡Copiado!
                `;
                setTimeout(() => {
                    copyBtn.innerHTML = originalText;
                }, 2000);
            }
        }).catch(err => {
            console.error('Error copying:', err);
        });
    }
};

// ================================
// State
// ================================

let allEndpoints = [];
let endpointsByTags = {};
let availableEndpoints = [];
let selectedEndpoints = [];
let currentView = 'list'; // 'list' or 'tags'
let currentDownloadUrl = null;

// Get session ID from page (if any)
const SESSION_ID = window.SESSION_ID || '';

// DOM Elements
const elements = {
    availableList: document.getElementById('availableList'),
    selectedList: document.getElementById('selectedList'),
    availableCount: document.getElementById('availableCount'),
    selectedCount: document.getElementById('selectedCount'),
    searchInput: document.getElementById('searchInput'),
    patternInput: document.getElementById('patternInput'),
    viewList: document.getElementById('viewList'),
    viewTags: document.getElementById('viewTags'),
    moveRight: document.getElementById('moveRight'),
    moveLeft: document.getElementById('moveLeft'),
    selectAll: document.getElementById('selectAll'),
    clearSelection: document.getElementById('clearSelection'),
    addPattern: document.getElementById('addPattern'),
    generateBtn: document.getElementById('generateBtn'),
    previewBtn: document.getElementById('previewBtn'),
    cancelBtn: document.getElementById('cancelBtn'),
    resultModal: document.getElementById('resultModal'),
    resultTitle: document.getElementById('resultTitle'),
    resultBody: document.getElementById('resultBody'),
    closeModal: document.getElementById('closeModal'),
    downloadBtn: document.getElementById('downloadBtn'),
    loadingOverlay: document.getElementById('loadingOverlay'),
    serviceName: document.getElementById('serviceName'),
    servicePrefix: document.getElementById('servicePrefix'),
    baseUrl: document.getElementById('baseUrl'),
    mcpFramework: document.getElementById('mcpFramework'),
    environment: document.getElementById('environment'),
    downloadZip: document.getElementById('downloadZip'),
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Initialize theme first (before content loads)
    ThemeManager.init();

    // Initialize validation panel
    ValidationManager.init();

    // Initialize stats panel
    StatsManager.init();

    // Initialize preview manager
    PreviewManager.init();

    loadEndpoints();
    setupEventListeners();

    // Load validation results
    ValidationManager.loadValidation();

    // Load stats
    StatsManager.loadStats();
});

// Build API URL with session
function apiUrl(path) {
    const separator = path.includes('?') ? '&' : '?';
    return SESSION_ID ? `${path}${separator}session=${SESSION_ID}` : path;
}

// Load endpoints from API
async function loadEndpoints() {
    try {
        showLoading(true);
        const response = await fetch(apiUrl('/api/endpoints'));
        const data = await response.json();

        if (data.error) {
            showError(data.error);
            return;
        }

        allEndpoints = data.endpoints;
        endpointsByTags = data.by_tags;

        // Initially all endpoints are available
        availableEndpoints = [...allEndpoints];
        selectedEndpoints = [];

        renderEndpoints();
        updateCounts();
    } catch (error) {
        console.error('Error loading endpoints:', error);
        showError('Error cargando endpoints');
    } finally {
        showLoading(false);
    }
}

// Setup event listeners
function setupEventListeners() {
    // View toggle
    elements.viewList.addEventListener('click', () => setView('list'));
    elements.viewTags.addEventListener('click', () => setView('tags'));

    // Search
    elements.searchInput.addEventListener('input', debounce(handleSearch, 300));

    // Pattern
    elements.addPattern.addEventListener('click', handlePattern);
    elements.patternInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handlePattern();
    });

    // Transfer buttons
    elements.moveRight.addEventListener('click', moveToSelected);
    elements.moveLeft.addEventListener('click', moveToAvailable);

    // Bulk actions
    elements.selectAll.addEventListener('click', selectAllAvailable);
    elements.clearSelection.addEventListener('click', clearAllSelected);

    // Generate
    elements.generateBtn.addEventListener('click', generateServer);

    // Preview
    if (elements.previewBtn) {
        elements.previewBtn.addEventListener('click', () => PreviewManager.loadPreview());
    }

    elements.cancelBtn.addEventListener('click', () => {
        if (SESSION_ID) {
            window.location.href = '/';
        } else {
            window.close();
        }
    });

    // Modal
    elements.closeModal.addEventListener('click', () => {
        elements.resultModal.style.display = 'none';
        currentDownloadUrl = null;
    });

    // Download button
    elements.downloadBtn.addEventListener('click', () => {
        if (currentDownloadUrl) {
            window.location.href = currentDownloadUrl;
        }
    });
}

// Set view mode
function setView(view) {
    currentView = view;
    elements.viewList.classList.toggle('active', view === 'list');
    elements.viewTags.classList.toggle('active', view === 'tags');
    renderEndpoints();
}

// Render endpoints
function renderEndpoints() {
    if (currentView === 'list') {
        renderListView();
    } else {
        renderTagsView();
    }
}

// Render list view
function renderListView() {
    elements.availableList.innerHTML = availableEndpoints
        .map(ep => createEndpointItem(ep, 'available'))
        .join('');

    elements.selectedList.innerHTML = selectedEndpoints
        .map(ep => createEndpointItem(ep, 'selected'))
        .join('');

    // Add click handlers
    addEndpointClickHandlers();
}

// Render tags view
function renderTagsView() {
    // Group available by tags
    const availableByTags = groupByTags(availableEndpoints);
    elements.availableList.innerHTML = Object.entries(availableByTags)
        .map(([tag, eps]) => createTagGroup(tag, eps, 'available'))
        .join('');

    // Selected always as list
    elements.selectedList.innerHTML = selectedEndpoints
        .map(ep => createEndpointItem(ep, 'selected'))
        .join('');

    // Add handlers
    addEndpointClickHandlers();
    addTagToggleHandlers();
}

// Create endpoint item HTML
function createEndpointItem(endpoint, listType) {
    const methodClass = `method-${endpoint.method.toLowerCase()}`;
    const deprecatedBadge = endpoint.deprecated
        ? '<span class="deprecated-badge">DEPRECATED</span>'
        : '';
    const deprecatedClass = endpoint.deprecated ? 'deprecated' : '';

    return `
        <div class="endpoint-item ${deprecatedClass}"
             data-key="${endpoint.key}"
             data-list="${listType}"
             title="${endpoint.description || endpoint.summary}">
            <input type="checkbox" class="endpoint-checkbox" />
            <span class="method-badge ${methodClass}">${endpoint.method}</span>
            <span class="endpoint-path">${endpoint.path}</span>
            <span class="endpoint-summary">${endpoint.summary}</span>
            ${deprecatedBadge}
        </div>
    `;
}

// Create tag group HTML
function createTagGroup(tag, endpoints, listType) {
    const endpointsHtml = endpoints
        .map(ep => createEndpointItem(ep, listType))
        .join('');

    return `
        <div class="tag-group">
            <div class="tag-header" data-tag="${tag}">
                <span class="arrow">▼</span>
                <span>${tag}</span>
                <span class="count">${endpoints.length}</span>
            </div>
            <div class="tag-endpoints" data-tag="${tag}">
                ${endpointsHtml}
            </div>
        </div>
    `;
}

// Group endpoints by tags
function groupByTags(endpoints) {
    const groups = {};
    endpoints.forEach(ep => {
        const tags = ep.tags.length > 0 ? ep.tags : ['Sin categoría'];
        tags.forEach(tag => {
            if (!groups[tag]) groups[tag] = [];
            if (!groups[tag].find(e => e.key === ep.key)) {
                groups[tag].push(ep);
            }
        });
    });
    return groups;
}

// Add click handlers for endpoint items
function addEndpointClickHandlers() {
    document.querySelectorAll('.endpoint-item').forEach(item => {
        item.addEventListener('click', (e) => {
            if (e.target.classList.contains('endpoint-checkbox')) return;

            const checkbox = item.querySelector('.endpoint-checkbox');
            checkbox.checked = !checkbox.checked;
            item.classList.toggle('selected', checkbox.checked);
        });

        item.addEventListener('dblclick', () => {
            const key = item.dataset.key;
            const list = item.dataset.list;

            if (list === 'available') {
                moveEndpoint(key, 'toSelected');
            } else {
                moveEndpoint(key, 'toAvailable');
            }
        });
    });
}

// Add handlers for tag toggle
function addTagToggleHandlers() {
    document.querySelectorAll('.tag-header').forEach(header => {
        header.addEventListener('click', () => {
            const tag = header.dataset.tag;
            const endpoints = document.querySelector(`.tag-endpoints[data-tag="${tag}"]`);

            header.classList.toggle('collapsed');
            endpoints.classList.toggle('hidden');
        });
    });
}

// Move selected to right panel
function moveToSelected() {
    const selected = getCheckedEndpoints('available');
    selected.forEach(key => moveEndpoint(key, 'toSelected'));
}

// Move selected to left panel
function moveToAvailable() {
    const selected = getCheckedEndpoints('selected');
    selected.forEach(key => moveEndpoint(key, 'toAvailable'));
}

// Get checked endpoint keys
function getCheckedEndpoints(listType) {
    const keys = [];
    document.querySelectorAll(`.endpoint-item[data-list="${listType}"]`).forEach(item => {
        const checkbox = item.querySelector('.endpoint-checkbox');
        if (checkbox.checked) {
            keys.push(item.dataset.key);
        }
    });
    return keys;
}

// Move single endpoint
function moveEndpoint(key, direction) {
    if (direction === 'toSelected') {
        const endpoint = availableEndpoints.find(ep => ep.key === key);
        if (endpoint && !selectedEndpoints.find(ep => ep.key === key)) {
            selectedEndpoints.push(endpoint);
            availableEndpoints = availableEndpoints.filter(ep => ep.key !== key);
        }
    } else {
        const endpoint = selectedEndpoints.find(ep => ep.key === key);
        if (endpoint && !availableEndpoints.find(ep => ep.key === key)) {
            availableEndpoints.push(endpoint);
            selectedEndpoints = selectedEndpoints.filter(ep => ep.key !== key);
        }
    }

    // Sort available
    availableEndpoints.sort((a, b) => a.path.localeCompare(b.path));

    renderEndpoints();
    updateCounts();
}

// Select all available
function selectAllAvailable() {
    selectedEndpoints = [...allEndpoints];
    availableEndpoints = [];
    renderEndpoints();
    updateCounts();
}

// Clear all selected
function clearAllSelected() {
    availableEndpoints = [...allEndpoints];
    selectedEndpoints = [];
    renderEndpoints();
    updateCounts();
}

// Handle search
function handleSearch() {
    const query = elements.searchInput.value.toLowerCase().trim();

    if (!query) {
        // Reset to show all non-selected
        availableEndpoints = allEndpoints.filter(
            ep => !selectedEndpoints.find(s => s.key === ep.key)
        );
    } else {
        availableEndpoints = allEndpoints.filter(ep => {
            const inSelected = selectedEndpoints.find(s => s.key === ep.key);
            if (inSelected) return false;

            return ep.path.toLowerCase().includes(query) ||
                   ep.summary.toLowerCase().includes(query) ||
                   ep.method.toLowerCase().includes(query) ||
                   ep.tags.some(t => t.toLowerCase().includes(query));
        });
    }

    renderEndpoints();
    updateCounts();
}

// Handle pattern
function handlePattern() {
    const pattern = elements.patternInput.value.trim();
    if (!pattern) return;

    // Convert glob to regex
    const regex = new RegExp(
        '^' + pattern.replace(/\*/g, '.*').replace(/\?/g, '.') + '$'
    );

    // Find matching endpoints in available
    const matching = availableEndpoints.filter(ep => regex.test(ep.path));

    // Move to selected
    matching.forEach(ep => {
        if (!selectedEndpoints.find(s => s.key === ep.key)) {
            selectedEndpoints.push(ep);
        }
    });

    // Remove from available
    availableEndpoints = availableEndpoints.filter(
        ep => !selectedEndpoints.find(s => s.key === ep.key)
    );

    elements.patternInput.value = '';
    renderEndpoints();
    updateCounts();
}

// Update counts
function updateCounts() {
    elements.availableCount.textContent = availableEndpoints.length;
    elements.selectedCount.textContent = selectedEndpoints.length;
}

// Generate server
// Get current configuration from form
function getConfig() {
    return {
        service_name: elements.serviceName.value || 'api',
        service_prefix: elements.servicePrefix.value || elements.serviceName.value || 'api',
        base_url: elements.baseUrl.value || null,
        mcp_framework: elements.mcpFramework.value,
        environment: elements.environment.value,
    };
}

async function generateServer() {
    if (selectedEndpoints.length === 0) {
        showModal('Error', 'Debes seleccionar al menos un endpoint.', 'error');
        return;
    }

    const downloadZip = elements.downloadZip.checked;

    const config = {
        selected: selectedEndpoints.map(ep => ep.key),
        ...getConfig(),
        download_zip: downloadZip,
        session_id: SESSION_ID || null,
    };

    try {
        showLoading(true);

        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config),
        });

        const result = await response.json();

        if (result.success) {
            let bodyHtml = `
                <p>El servidor MCP se ha generado correctamente.</p>
                <p><strong>Tools:</strong> ${result.tools_count}</p>
                <p><strong>Resources:</strong> ${result.resources_count}</p>
            `;

            if (result.warnings && result.warnings.length > 0) {
                bodyHtml += `<p><strong>Advertencias:</strong> ${result.warnings.join(', ')}</p>`;
            }

            if (result.download_url) {
                currentDownloadUrl = result.download_url;
                elements.downloadBtn.style.display = 'inline-flex';
                bodyHtml += `
                    <br>
                    <p><strong>Archivo:</strong> ${result.zip_filename}</p>
                    <p>Haz clic en "Descargar ZIP" para obtener el servidor generado.</p>
                `;
            } else {
                elements.downloadBtn.style.display = 'none';
                bodyHtml += `
                    <p><strong>Ubicación:</strong> <code>${result.output_path}</code></p>
                    <br>
                    <p><strong>Próximos pasos:</strong></p>
                    <ol>
                        <li>cd ${result.output_path}</li>
                        <li>cp .env.example .env</li>
                        <li>Edita .env con tus credenciales</li>
                        <li>pip install -r requirements.txt</li>
                        <li>python -m src.server</li>
                    </ol>
                `;
            }

            showModal('Servidor Generado', bodyHtml, 'success');
        } else {
            elements.downloadBtn.style.display = 'none';
            showModal(
                'Error',
                `<p>Error generando el servidor:</p>
                <p><code>${result.error || result.errors.join(', ')}</code></p>`,
                'error'
            );
        }
    } catch (error) {
        console.error('Error:', error);
        elements.downloadBtn.style.display = 'none';
        showModal('Error', `Error de conexión: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

// Show modal
function showModal(title, body, type = 'info') {
    elements.resultTitle.textContent = title;
    elements.resultBody.innerHTML = body;
    elements.resultModal.querySelector('.modal-content').className = `modal-content ${type}`;
    elements.resultModal.style.display = 'flex';
}

// Show/hide loading
function showLoading(show) {
    elements.loadingOverlay.style.display = show ? 'flex' : 'none';
}

// Show error
function showError(message) {
    showModal('Error', message, 'error');
}

// Debounce utility
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
