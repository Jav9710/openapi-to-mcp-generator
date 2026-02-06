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

        const libraryStats = (typeof SpecLibrary !== 'undefined') ? SpecLibrary.getStats() : null;
        const avgTime = libraryStats && libraryStats.avg_generation_time != null
            ? this.formatGenTime(libraryStats.avg_generation_time)
            : '--';

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
            <div class="quick-stat">
                <div class="quick-stat-value">${avgTime}</div>
                <div class="quick-stat-label">Tiempo Prom.</div>
            </div>
        `;

        container.innerHTML = html;
    },

    formatGenTime(ms) {
        if (ms < 1000) return `${ms}ms`;
        return `${(ms / 1000).toFixed(1)}s`;
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

    // Initialize MCP Score panel
    MCPScoreManager.init();

    // Initialize Enrichment Manager
    EnrichmentManager.init();

    loadEndpoints();
    setupEventListeners();

    // Load validation results
    ValidationManager.loadValidation();

    // Load stats
    StatsManager.loadStats();

    // Load MCP utility score
    MCPScoreManager.loadScore();
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

// ================================
// MCP Score Manager
// ================================

const MCPScoreManager = {
    panel: null,
    isExpanded: false,
    scoreData: null,

    init() {
        this.panel = document.getElementById('mcpScorePanel');
        if (!this.panel) return;

        const toggleBtn = document.getElementById('scoreToggle');
        const expandBtn = document.getElementById('scoreExpand');
        const enrichBtn = document.getElementById('enrichBtn');

        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => this.toggleExpand());
        }
        if (expandBtn) {
            expandBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleExpand();
            });
        }
        if (enrichBtn) {
            enrichBtn.addEventListener('click', () => EnrichmentManager.start());
        }
    },

    async loadScore() {
        if (!this.panel) return;

        this.panel.style.display = 'block';
        this.setLoading(true);

        try {
            const response = await fetch(apiUrl('/api/mcp-score'));
            const data = await response.json();

            if (data.error) {
                this.setError(data.error);
                return;
            }

            this.scoreData = data;
            this.render(data);
        } catch (error) {
            this.setError('Error al calcular el score');
            console.error('Score error:', error);
        }
    },

    setLoading(loading) {
        const scoreValue = document.getElementById('scoreValue');
        const gradeEl = document.getElementById('scoreGrade');

        if (loading) {
            if (scoreValue) scoreValue.textContent = '...';
            if (gradeEl) {
                gradeEl.textContent = '-';
                gradeEl.className = 'score-grade';
            }
        }
    },

    setError(message) {
        const scoreValue = document.getElementById('scoreValue');
        if (scoreValue) scoreValue.textContent = '?';
        console.error(message);
    },

    render(data) {
        // Update score value and grade
        const scoreValue = document.getElementById('scoreValue');
        const gradeEl = document.getElementById('scoreGrade');

        if (scoreValue) {
            scoreValue.textContent = `${data.overall_score}/100`;
            scoreValue.style.color = this.getScoreColor(data.overall_score);
        }

        if (gradeEl) {
            gradeEl.textContent = data.grade;
            gradeEl.className = `score-grade grade-${data.grade.toLowerCase()}`;
        }

        // Render categories
        this.renderCategories(data.categories);

        // Render recommendations
        this.renderRecommendations(data.recommendations);

        // Update action section
        this.renderAction(data);
    },

    renderCategories(categories) {
        const container = document.getElementById('scoreCategories');
        if (!container || !categories) return;

        const html = Object.entries(categories).map(([key, cat]) => {
            const fillClass = cat.score >= 75 ? 'high' : cat.score >= 50 ? 'medium' : 'low';
            return `
                <div class="category-row">
                    <span class="category-name">${cat.name}</span>
                    <div class="category-bar">
                        <div class="category-fill ${fillClass}" style="width: ${cat.score}%"></div>
                    </div>
                    <span class="category-score">${cat.score}%</span>
                    <span class="category-details">${cat.complete_items}/${cat.total_items}</span>
                </div>
            `;
        }).join('');

        container.innerHTML = html;
    },

    renderRecommendations(recommendations) {
        const container = document.getElementById('scoreRecommendations');
        if (!container) return;

        if (!recommendations || recommendations.length === 0) {
            container.style.display = 'none';
            return;
        }

        container.style.display = 'block';
        const listEl = container.querySelector('.recommendation-list');
        if (listEl) {
            listEl.innerHTML = recommendations.map(rec => `
                <div class="recommendation-item">${this.escapeHtml(rec)}</div>
            `).join('');
        }
    },

    renderAction(data) {
        const attention = document.getElementById('endpointsAttention');
        const enrichBtn = document.getElementById('enrichBtn');

        if (attention) {
            attention.innerHTML = `<strong>${data.endpoints_needing_attention}</strong> endpoints necesitan atención`;
        }

        if (enrichBtn) {
            if (data.endpoints_needing_attention > 0 && data.overall_score < 90) {
                enrichBtn.style.display = 'flex';
            } else {
                enrichBtn.style.display = 'none';
            }
        }
    },

    toggleExpand() {
        this.isExpanded = !this.isExpanded;
        const body = document.getElementById('scoreBody');

        if (this.isExpanded) {
            body.style.display = 'block';
            this.panel.classList.add('expanded');
        } else {
            body.style.display = 'none';
            this.panel.classList.remove('expanded');
        }
    },

    getScoreColor(score) {
        if (score >= 90) return 'var(--success-color)';
        if (score >= 75) return 'var(--primary-color)';
        if (score >= 60) return 'var(--warning-color)';
        if (score >= 40) return '#f97316';
        return 'var(--danger-color)';
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

// ================================
// Enrichment Manager
// ================================

const EnrichmentManager = {
    modal: null,
    endpoints: [],
    currentIndex: 0,
    enrichments: [],
    originalScore: 0,

    init() {
        this.modal = document.getElementById('enrichmentModal');
        if (!this.modal) return;

        // Close button
        const closeBtn = document.getElementById('closeEnrichment');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.hide());
        }

        // Navigation buttons
        const prevBtn = document.getElementById('enrichPrev');
        const nextBtn = document.getElementById('enrichNext');
        const skipBtn = document.getElementById('enrichSkip');
        const finishBtn = document.getElementById('enrichFinish');

        if (prevBtn) prevBtn.addEventListener('click', () => this.prev());
        if (nextBtn) nextBtn.addEventListener('click', () => this.next());
        if (skipBtn) skipBtn.addEventListener('click', () => this.skip());
        if (finishBtn) finishBtn.addEventListener('click', () => this.finish());

        // Close on overlay click
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.hide();
            }
        });
    },

    async start() {
        showLoading(true);

        try {
            const response = await fetch(apiUrl('/api/enrichment/suggestions'));
            const data = await response.json();
            showLoading(false);

            if (data.error) {
                showError(data.error);
                return;
            }

            this.endpoints = data.endpoints;
            this.originalScore = data.overall_score;
            this.currentIndex = 0;
            this.enrichments = [];

            // Initialize enrichments array
            this.endpoints.forEach(ep => {
                this.enrichments.push({
                    method: ep.method,
                    path: ep.path,
                    description: null,
                    summary: null,
                    operation_id: null,
                    tags: [],
                    parameter_descriptions: {}
                });
            });

            this.show();
            this.renderCurrentEndpoint();
        } catch (error) {
            showLoading(false);
            showError('Error cargando sugerencias: ' + error.message);
        }
    },

    show() {
        if (!this.modal) return;
        this.modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    },

    hide() {
        if (!this.modal) return;
        this.modal.style.display = 'none';
        document.body.style.overflow = '';
    },

    renderCurrentEndpoint() {
        if (this.endpoints.length === 0) {
            this.showComplete();
            return;
        }

        const ep = this.endpoints[this.currentIndex];
        const enrichment = this.enrichments[this.currentIndex];

        // Update progress
        const progressFill = document.getElementById('enrichProgressFill');
        const progressText = document.getElementById('enrichProgressText');
        if (progressFill) {
            const percent = ((this.currentIndex + 1) / this.endpoints.length) * 100;
            progressFill.style.width = `${percent}%`;
        }
        if (progressText) {
            progressText.textContent = `${this.currentIndex + 1} de ${this.endpoints.length}`;
        }

        // Update endpoint info
        const methodEl = document.getElementById('enrichMethod');
        const pathEl = document.getElementById('enrichPath');
        const priorityEl = document.getElementById('enrichPriority');

        if (methodEl) {
            methodEl.textContent = ep.method.toUpperCase();
            methodEl.className = `endpoint-method-large method-${ep.method.toLowerCase()}`;
        }
        if (pathEl) pathEl.textContent = ep.path;
        if (priorityEl) {
            priorityEl.textContent = ep.priority;
            priorityEl.className = `endpoint-priority priority-${ep.priority}`;
        }

        // Update missing fields
        const missingEl = document.getElementById('missingFields');
        if (missingEl) {
            missingEl.innerHTML = ep.missing_fields.map(f => `
                <span class="missing-field-badge">${this.formatFieldName(f)}</span>
            `).join('');
        }

        // Render form
        this.renderForm(ep, enrichment);

        // Update buttons
        const prevBtn = document.getElementById('enrichPrev');
        const finishBtn = document.getElementById('enrichFinish');
        const nextBtn = document.getElementById('enrichNext');

        if (prevBtn) prevBtn.disabled = this.currentIndex === 0;
        if (finishBtn) finishBtn.style.display = this.currentIndex === this.endpoints.length - 1 ? 'flex' : 'none';
        if (nextBtn) nextBtn.style.display = this.currentIndex < this.endpoints.length - 1 ? 'flex' : 'none';
    },

    renderForm(ep, enrichment) {
        const formEl = document.getElementById('enrichmentForm');
        if (!formEl) return;

        let html = '';

        // Description field
        if (ep.missing_fields.includes('description')) {
            const suggested = ep.suggested_values?.description || '';
            html += `
                <div class="form-group">
                    <label>
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                            <polyline points="14 2 14 8 20 8"></polyline>
                            <line x1="16" y1="13" x2="8" y2="13"></line>
                            <line x1="16" y1="17" x2="8" y2="17"></line>
                        </svg>
                        Descripción
                    </label>
                    <textarea id="enrichDescription" rows="3" placeholder="Describe qué hace este endpoint...">${enrichment.description || ''}</textarea>
                    <div class="suggested-value">
                        Sugerencia: <code>${this.escapeHtml(suggested)}</code>
                        <button type="button" class="btn-use-suggestion" onclick="EnrichmentManager.useSuggestion('description', '${this.escapeAttr(suggested)}')">Usar</button>
                    </div>
                </div>
            `;
        }

        // OperationId field
        if (ep.missing_fields.includes('operationId')) {
            const suggested = ep.suggested_values?.operationId || '';
            html += `
                <div class="form-group">
                    <label>
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="16 18 22 12 16 6"></polyline>
                            <polyline points="8 6 2 12 8 18"></polyline>
                        </svg>
                        Operation ID
                    </label>
                    <input type="text" id="enrichOperationId" placeholder="ej: getUserById" value="${enrichment.operation_id || ''}">
                    <div class="suggested-value">
                        Sugerencia: <code>${this.escapeHtml(suggested)}</code>
                        <button type="button" class="btn-use-suggestion" onclick="EnrichmentManager.useSuggestion('operationId', '${this.escapeAttr(suggested)}')">Usar</button>
                    </div>
                </div>
            `;
        }

        // Tags field
        if (ep.missing_fields.includes('tags')) {
            const suggestedTags = ep.suggested_values?.tags || [];
            html += `
                <div class="form-group">
                    <label>
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"></path>
                            <line x1="7" y1="7" x2="7.01" y2="7"></line>
                        </svg>
                        Tags
                    </label>
                    <div class="tags-input-container" id="tagsContainer">
                        ${(enrichment.tags || []).map(tag => `
                            <span class="tag-chip">
                                ${this.escapeHtml(tag)}
                                <button type="button" class="tag-chip-remove" onclick="EnrichmentManager.removeTag('${this.escapeAttr(tag)}')">×</button>
                            </span>
                        `).join('')}
                        <input type="text" class="tags-input" id="enrichTagInput" placeholder="Escribe y presiona Enter..." onkeydown="EnrichmentManager.handleTagInput(event)">
                    </div>
                    <div class="suggested-tags">
                        ${suggestedTags.map(tag => `
                            <span class="suggested-tag" onclick="EnrichmentManager.addTag('${this.escapeAttr(tag)}')">${this.escapeHtml(tag)}</span>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        // Parameter descriptions
        if (ep.missing_fields.includes('parameter_descriptions') && ep.suggested_values?.undocumented_parameters?.length > 0) {
            const params = ep.suggested_values.undocumented_parameters;
            html += `
                <div class="params-section">
                    <h4>Descripciones de Parámetros</h4>
                    ${params.map(param => `
                        <div class="param-item">
                            <span class="param-name">${this.escapeHtml(param)}</span>
                            <div class="param-input">
                                <input type="text" id="param_${param}" placeholder="Describe este parámetro..." value="${enrichment.parameter_descriptions[param] || ''}">
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        formEl.innerHTML = html || '<p style="color: var(--text-muted);">Este endpoint está completo.</p>';
    },

    useSuggestion(field, value) {
        if (field === 'description') {
            const el = document.getElementById('enrichDescription');
            if (el) el.value = value;
        } else if (field === 'operationId') {
            const el = document.getElementById('enrichOperationId');
            if (el) el.value = value;
        }
    },

    addTag(tag) {
        const enrichment = this.enrichments[this.currentIndex];
        if (!enrichment.tags.includes(tag)) {
            enrichment.tags.push(tag);
            this.renderCurrentEndpoint();
        }
    },

    removeTag(tag) {
        const enrichment = this.enrichments[this.currentIndex];
        enrichment.tags = enrichment.tags.filter(t => t !== tag);
        this.renderCurrentEndpoint();
    },

    handleTagInput(event) {
        if (event.key === 'Enter' && event.target.value.trim()) {
            this.addTag(event.target.value.trim());
            event.target.value = '';
            event.preventDefault();
        }
    },

    saveCurrentForm() {
        const enrichment = this.enrichments[this.currentIndex];

        const descEl = document.getElementById('enrichDescription');
        const opIdEl = document.getElementById('enrichOperationId');

        if (descEl) enrichment.description = descEl.value.trim() || null;
        if (opIdEl) enrichment.operation_id = opIdEl.value.trim() || null;

        // Save parameter descriptions
        const ep = this.endpoints[this.currentIndex];
        if (ep.suggested_values?.undocumented_parameters) {
            ep.suggested_values.undocumented_parameters.forEach(param => {
                const paramEl = document.getElementById(`param_${param}`);
                if (paramEl && paramEl.value.trim()) {
                    enrichment.parameter_descriptions[param] = paramEl.value.trim();
                }
            });
        }
    },

    prev() {
        if (this.currentIndex > 0) {
            this.saveCurrentForm();
            this.currentIndex--;
            this.renderCurrentEndpoint();
        }
    },

    next() {
        if (this.currentIndex < this.endpoints.length - 1) {
            this.saveCurrentForm();
            this.currentIndex++;
            this.renderCurrentEndpoint();
        }
    },

    skip() {
        // Clear current enrichment
        this.enrichments[this.currentIndex] = {
            method: this.endpoints[this.currentIndex].method,
            path: this.endpoints[this.currentIndex].path,
            description: null,
            summary: null,
            operation_id: null,
            tags: [],
            parameter_descriptions: {}
        };

        if (this.currentIndex < this.endpoints.length - 1) {
            this.currentIndex++;
            this.renderCurrentEndpoint();
        } else {
            this.finish();
        }
    },

    async finish() {
        this.saveCurrentForm();

        // Filter out empty enrichments
        const validEnrichments = this.enrichments.filter(e =>
            e.description || e.summary || e.operation_id || e.tags.length > 0 || Object.keys(e.parameter_descriptions).length > 0
        );

        if (validEnrichments.length === 0) {
            this.showComplete(true);
            return;
        }

        showLoading(true);

        try {
            const response = await fetch(apiUrl('/api/enrichment/apply'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    enrichments: validEnrichments,
                    session_id: SESSION_ID || null
                })
            });

            const data = await response.json();
            showLoading(false);

            if (data.success) {
                this.showComplete(false, data);
            } else {
                showError(data.error || 'Error aplicando enriquecimiento');
            }
        } catch (error) {
            showLoading(false);
            showError('Error: ' + error.message);
        }
    },

    showComplete(skippedAll = false, data = null) {
        const body = document.getElementById('enrichmentBody');
        if (!body) return;

        let html;

        if (skippedAll) {
            html = `
                <div class="enrichment-complete">
                    <div class="complete-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="10"></circle>
                            <line x1="12" y1="16" x2="12" y2="12"></line>
                            <line x1="12" y1="8" x2="12.01" y2="8"></line>
                        </svg>
                    </div>
                    <h3>Sin cambios</h3>
                    <p>No se realizaron modificaciones a la especificación.</p>
                    <div class="complete-actions">
                        <button class="btn btn-primary" onclick="EnrichmentManager.hide()">Cerrar</button>
                    </div>
                </div>
            `;
        } else {
            const newScore = data?.new_score?.overall_score || 0;
            const newGrade = data?.new_score?.grade || '-';

            html = `
                <div class="enrichment-complete">
                    <div class="complete-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                            <polyline points="22 4 12 14.01 9 11.01"></polyline>
                        </svg>
                    </div>
                    <h3>¡Enriquecimiento Completado!</h3>
                    <p>La especificación ha sido actualizada con la nueva información.</p>
                    <div class="score-comparison">
                        <div class="score-before">
                            <div class="score-value-lg">${this.originalScore}</div>
                            <div class="score-label">Score anterior</div>
                        </div>
                        <div class="score-arrow">→</div>
                        <div class="score-after">
                            <div class="score-value-lg">${newScore}</div>
                            <div class="score-label">Score nuevo (${newGrade})</div>
                        </div>
                    </div>
                    <div class="complete-actions">
                        <button class="btn btn-secondary" onclick="EnrichmentManager.exportSpec()">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                <polyline points="7 10 12 15 17 10"></polyline>
                                <line x1="12" y1="15" x2="12" y2="3"></line>
                            </svg>
                            Descargar OpenAPI
                        </button>
                        <button class="btn btn-primary" onclick="EnrichmentManager.continueWithEnriched('${data?.session_id || ''}')">
                            Continuar →
                        </button>
                    </div>
                </div>
            `;
        }

        body.innerHTML = html;

        // Hide footer during complete
        const footer = document.querySelector('.enrichment-footer');
        if (footer) footer.style.display = 'none';
    },

    async exportSpec() {
        try {
            const response = await fetch(apiUrl('/api/enrichment/export'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ format: 'yaml' })
            });

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'openapi_enriched.yaml';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
        } catch (error) {
            showError('Error descargando: ' + error.message);
        }
    },

    continueWithEnriched(newSessionId) {
        this.hide();
        if (newSessionId) {
            window.location.href = `/selector?session=${newSessionId}`;
        } else {
            // Reload current page to refresh data
            window.location.reload();
        }
    },

    formatFieldName(field) {
        const names = {
            'description': 'Descripción',
            'operationId': 'Operation ID',
            'tags': 'Tags',
            'parameter_descriptions': 'Parámetros'
        };
        return names[field] || field;
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    },

    escapeAttr(text) {
        return (text || '').replace(/'/g, "\\'").replace(/"/g, '\\"');
    }
};

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

// ================================
// Configuration Export/Import
// ================================

// Export configuration button
const exportConfigBtn = document.getElementById('exportConfigBtn');
if (exportConfigBtn) {
    exportConfigBtn.addEventListener('click', () => {
        const selected = getSelectedEndpoints();

        if (selected.length === 0) {
            Toast.warning('No hay endpoints seleccionados para exportar');
            return;
        }

        const metadata = {
            spec_title: document.querySelector('.spec-title')?.textContent || 'API',
            spec_version: document.querySelector('.spec-version')?.textContent || '1.0.0',
            total_available: endpoints.length,
            exported_from: 'web-gui'
        };

        try {
            SelectionConfig.exportConfig(selected, metadata);
            Toast.success(`Configuración exportada (${selected.length} endpoints)`);
        } catch (error) {
            Toast.error('Error exportando configuración: ' + error.message);
        }
    });
}

// Import configuration button
const importConfigBtn = document.getElementById('importConfigBtn');
const importConfigInput = document.getElementById('importConfigInput');

if (importConfigBtn && importConfigInput) {
    importConfigBtn.addEventListener('click', () => {
        importConfigInput.click();
    });

    importConfigInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        try {
            const config = await SelectionConfig.importConfig(file);

            // Apply selection
            const importedEndpoints = config.selection.endpoints;

            // Clear current selection
            targetList.innerHTML = '';
            updateSelectedCount();

            // Add imported endpoints
            let applied = 0;
            importedEndpoints.forEach(key => {
                const endpoint = endpoints.find(ep => ep.key === key);
                if (endpoint) {
                    addToTarget(endpoint);
                    applied++;
                }
            });

            if (applied > 0) {
                Toast.success(`Configuración importada: ${applied} endpoints seleccionados`);
            } else {
                Toast.warning('No se encontraron endpoints coincidentes en la especificación actual');
            }

            // Clear input
            importConfigInput.value = '';

        } catch (error) {
            Toast.error('Error importando configuración: ' + error.message);
            importConfigInput.value = '';
        }
    });
}

// ================================
// Presets Management
// ================================

const presetsBtn = document.getElementById('presetsBtn');
const presetsModal = document.getElementById('presetsModal');
const presetsModalClose = document.getElementById('presetsModalClose');
const savePresetBtn = document.getElementById('savePresetBtn');
const presetNameInput = document.getElementById('presetNameInput');
const presetsList = document.getElementById('presetsList');

// Open presets modal
if (presetsBtn && presetsModal) {
    presetsBtn.addEventListener('click', () => {
        presetsModal.style.display = 'flex';
        renderPresets();
    });
}

// Close presets modal
if (presetsModalClose) {
    presetsModalClose.addEventListener('click', () => {
        presetsModal.style.display = 'none';
    });
}

// Close on overlay click
if (presetsModal) {
    presetsModal.addEventListener('click', (e) => {
        if (e.target === presetsModal) {
            presetsModal.style.display = 'none';
        }
    });
}

// Save preset
if (savePresetBtn && presetNameInput) {
    savePresetBtn.addEventListener('click', () => {
        const name = presetNameInput.value.trim();

        if (!name) {
            Toast.warning('Ingresa un nombre para el preset');
            return;
        }

        const selected = getSelectedEndpoints();

        if (selected.length === 0) {
            Toast.warning('Selecciona al menos un endpoint');
            return;
        }

        const metadata = {
            spec_title: document.querySelector('.spec-title')?.textContent || 'API',
            spec_version: document.querySelector('.spec-version')?.textContent || '1.0.0',
            total_selected: selected.length
        };

        try {
            SelectionConfig.savePreset(name, selected, metadata);
            Toast.success(`Preset "${name}" guardado`);
            presetNameInput.value = '';
            renderPresets();
        } catch (error) {
            Toast.error('Error guardando preset: ' + error.message);
        }
    });
}

// Render presets list
function renderPresets() {
    if (!presetsList) return;

    const presets = SelectionConfig.getAllPresets();
    const presetNames = Object.keys(presets);

    if (presetNames.length === 0) {
        presetsList.innerHTML = `
            <div class="preset-empty">
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
                </svg>
                <p>No hay presets guardados</p>
            </div>
        `;
        return;
    }

    const html = presetNames.map(name => {
        const preset = presets[name];
        return `
            <div class="preset-item" data-preset-name="${name}">
                <div class="preset-item-info">
                    <div class="preset-item-name">${name}</div>
                    <div class="preset-item-meta">
                        ${preset.selection.endpoints.length} endpoints •
                        ${SelectionConfig.formatDate(preset.created_at)}
                    </div>
                </div>
                <div class="preset-item-actions">
                    <button class="preset-item-btn load-preset" data-preset-name="${name}" title="Cargar preset">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="7 10 12 15 17 10"></polyline>
                            <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                    </button>
                    <button class="preset-item-btn delete delete-preset" data-preset-name="${name}" title="Eliminar preset">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="3 6 5 6 21 6"></polyline>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                        </svg>
                    </button>
                </div>
            </div>
        `;
    }).join('');

    presetsList.innerHTML = html;

    // Attach event listeners
    presetsList.querySelectorAll('.load-preset').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const name = btn.dataset.presetName;
            loadPreset(name);
        });
    });

    presetsList.querySelectorAll('.delete-preset').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const name = btn.dataset.presetName;
            deletePreset(name);
        });
    });
}

// Load preset
function loadPreset(name) {
    const preset = SelectionConfig.loadPreset(name);
    if (!preset) {
        Toast.error(`Preset "${name}" no encontrado`);
        return;
    }

    // Clear current selection
    targetList.innerHTML = '';
    updateSelectedCount();

    // Add preset endpoints
    const presetEndpoints = preset.selection.endpoints;
    let applied = 0;

    presetEndpoints.forEach(key => {
        const endpoint = endpoints.find(ep => ep.key === key);
        if (endpoint) {
            addToTarget(endpoint);
            applied++;
        }
    });

    if (applied > 0) {
        Toast.success(`Preset "${name}" cargado: ${applied} endpoints`);
        presetsModal.style.display = 'none';
    } else {
        Toast.warning('No se encontraron endpoints coincidentes');
    }
}

// Delete preset
function deletePreset(name) {
    if (!confirm(`¿Eliminar el preset "${name}"?`)) {
        return;
    }

    try {
        SelectionConfig.deletePreset(name);
        Toast.info(`Preset "${name}" eliminado`);
        renderPresets();
    } catch (error) {
        Toast.error('Error eliminando preset: ' + error.message);
    }
}

// Helper: Get selected endpoints
function getSelectedEndpoints() {
    const targetItems = targetList.querySelectorAll('.endpoint-item');
    return Array.from(targetItems).map(item => item.dataset.key);
}
