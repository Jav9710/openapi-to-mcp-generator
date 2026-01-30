/**
 * Recent Specs Management
 *
 * Tracks recently loaded OpenAPI specs for quick access
 */

const RecentSpecs = {
    STORAGE_KEY: 'openapi-mcp-recent-specs',
    MAX_RECENT: 10,

    /**
     * Get all recent specs
     */
    getAll() {
        try {
            const stored = localStorage.getItem(this.STORAGE_KEY);
            return stored ? JSON.parse(stored) : [];
        } catch (e) {
            console.error('Error loading recent specs:', e);
            return [];
        }
    },

    /**
     * Add a spec to recent list
     * @param {object} spec - Spec info { title, version, description, endpoints_count, source, timestamp }
     */
    add(spec) {
        const recent = this.getAll();

        // Create spec entry
        const entry = {
            title: spec.title || 'Untitled API',
            version: spec.version || '1.0.0',
            description: spec.description || '',
            endpoints_count: spec.endpoints_count || 0,
            source: spec.source || 'upload', // 'upload' or 'url'
            source_url: spec.source_url || null,
            timestamp: Date.now(),
        };

        // Remove duplicates (same title and version)
        const filtered = recent.filter(item =>
            !(item.title === entry.title && item.version === entry.version)
        );

        // Add to front
        filtered.unshift(entry);

        // Keep only MAX_RECENT
        const trimmed = filtered.slice(0, this.MAX_RECENT);

        // Save
        try {
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(trimmed));
        } catch (e) {
            console.error('Error saving recent specs:', e);
        }
    },

    /**
     * Clear all recent specs
     */
    clear() {
        localStorage.removeItem(this.STORAGE_KEY);
    },

    /**
     * Remove a specific spec by index
     */
    remove(index) {
        const recent = this.getAll();
        recent.splice(index, 1);
        try {
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(recent));
        } catch (e) {
            console.error('Error removing spec:', e);
        }
    },

    /**
     * Format timestamp to relative time
     */
    formatTime(timestamp) {
        const now = Date.now();
        const diff = now - timestamp;

        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);

        if (minutes < 1) return 'Hace un momento';
        if (minutes < 60) return `Hace ${minutes} ${minutes === 1 ? 'minuto' : 'minutos'}`;
        if (hours < 24) return `Hace ${hours} ${hours === 1 ? 'hora' : 'horas'}`;
        if (days < 7) return `Hace ${days} ${days === 1 ? 'día' : 'días'}`;
        if (days < 30) return `Hace ${Math.floor(days / 7)} ${Math.floor(days / 7) === 1 ? 'semana' : 'semanas'}`;
        return `Hace ${Math.floor(days / 30)} ${Math.floor(days / 30) === 1 ? 'mes' : 'meses'}`;
    },

    /**
     * Render recent specs UI
     * @param {string} containerId - ID of container element
     * @param {function} onSelect - Callback when spec is selected
     */
    render(containerId, onSelect) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const recent = this.getAll();

        if (recent.length === 0) {
            container.innerHTML = `
                <div class="empty-recent">
                    <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3">
                        <circle cx="12" cy="12" r="10"></circle>
                        <polyline points="12 6 12 12 16 14"></polyline>
                    </svg>
                    <p>No hay especificaciones recientes</p>
                </div>
            `;
            return;
        }

        const itemsHtml = recent.map((spec, index) => `
            <div class="recent-spec-item" data-index="${index}">
                <div class="recent-spec-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                        <line x1="16" y1="13" x2="8" y2="13"></line>
                        <line x1="16" y1="17" x2="8" y2="17"></line>
                        <line x1="10" y1="9" x2="8" y2="9"></line>
                    </svg>
                </div>
                <div class="recent-spec-info">
                    <div class="recent-spec-title">${this.escapeHtml(spec.title)}</div>
                    <div class="recent-spec-meta">
                        <span class="version-badge">v${this.escapeHtml(spec.version)}</span>
                        <span class="meta-separator">•</span>
                        <span>${spec.endpoints_count} endpoint${spec.endpoints_count !== 1 ? 's' : ''}</span>
                        <span class="meta-separator">•</span>
                        <span class="recent-time">${this.formatTime(spec.timestamp)}</span>
                    </div>
                </div>
                <button class="recent-spec-delete" data-index="${index}" title="Eliminar del historial" aria-label="Eliminar">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                </button>
            </div>
        `).join('');

        container.innerHTML = `
            <div class="recent-specs-list">
                ${itemsHtml}
            </div>
            <button class="clear-recent-btn" id="clearRecentBtn">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
                Limpiar historial
            </button>
        `;

        // Attach event listeners
        container.querySelectorAll('.recent-spec-item').forEach((item, index) => {
            item.addEventListener('click', (e) => {
                // Don't trigger if clicking delete button
                if (e.target.closest('.recent-spec-delete')) return;
                if (onSelect) {
                    onSelect(recent[index], index);
                }
            });
        });

        container.querySelectorAll('.recent-spec-delete').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const index = parseInt(btn.dataset.index);
                this.remove(index);
                this.render(containerId, onSelect);
                Toast.info('Especificación eliminada del historial');
            });
        });

        const clearBtn = document.getElementById('clearRecentBtn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                if (confirm('¿Eliminar todo el historial de especificaciones?')) {
                    this.clear();
                    this.render(containerId, onSelect);
                    Toast.info('Historial limpiado');
                }
            });
        }
    },

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

// Make available globally
window.RecentSpecs = RecentSpecs;
