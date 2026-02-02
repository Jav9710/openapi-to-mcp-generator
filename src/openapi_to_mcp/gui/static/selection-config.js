/**
 * Selection Configuration Management
 *
 * Export/Import endpoint selection configurations
 */

const SelectionConfig = {
    /**
     * Export current selection to JSON file
     * @param {Array} selectedEndpoints - List of selected endpoint keys
     * @param {Object} metadata - Additional metadata (spec title, version, etc.)
     */
    exportConfig(selectedEndpoints, metadata = {}) {
        const config = {
            version: '1.0',
            exported_at: new Date().toISOString(),
            metadata: {
                spec_title: metadata.spec_title || 'Unknown API',
                spec_version: metadata.spec_version || '1.0.0',
                total_selected: selectedEndpoints.length,
                ...metadata
            },
            selection: {
                endpoints: selectedEndpoints,
                filters: metadata.filters || {},
            }
        };

        const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;

        const filename = `${this.sanitizeFilename(metadata.spec_title || 'selection')}-config.json`;
        a.download = filename;

        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        return config;
    },

    /**
     * Import configuration from JSON file
     * @param {File} file - JSON file containing configuration
     * @returns {Promise<Object>} Configuration object
     */
    async importConfig(file) {
        return new Promise((resolve, reject) => {
            if (!file) {
                reject(new Error('No file provided'));
                return;
            }

            if (!file.name.endsWith('.json')) {
                reject(new Error('Invalid file type. Please select a JSON file.'));
                return;
            }

            const reader = new FileReader();

            reader.onload = (e) => {
                try {
                    const config = JSON.parse(e.target.result);

                    // Validate config structure
                    if (!config.version || !config.selection) {
                        reject(new Error('Invalid configuration format'));
                        return;
                    }

                    resolve(config);
                } catch (error) {
                    reject(new Error('Failed to parse JSON: ' + error.message));
                }
            };

            reader.onerror = () => {
                reject(new Error('Failed to read file'));
            };

            reader.readAsText(file);
        });
    },

    /**
     * Save configuration to localStorage as a preset
     * @param {String} name - Preset name
     * @param {Array} selectedEndpoints - Selected endpoints
     * @param {Object} metadata - Metadata
     */
    savePreset(name, selectedEndpoints, metadata = {}) {
        const presets = this.getAllPresets();

        const preset = {
            name: name,
            created_at: new Date().toISOString(),
            metadata: metadata,
            selection: {
                endpoints: selectedEndpoints,
            }
        };

        // Add or update preset
        presets[name] = preset;

        try {
            localStorage.setItem('openapi-mcp-presets', JSON.stringify(presets));
            return preset;
        } catch (e) {
            console.error('Error saving preset:', e);
            throw new Error('Failed to save preset. Storage might be full.');
        }
    },

    /**
     * Get all saved presets
     * @returns {Object} All presets
     */
    getAllPresets() {
        try {
            const stored = localStorage.getItem('openapi-mcp-presets');
            return stored ? JSON.parse(stored) : {};
        } catch (e) {
            console.error('Error loading presets:', e);
            return {};
        }
    },

    /**
     * Load a preset by name
     * @param {String} name - Preset name
     * @returns {Object|null} Preset configuration
     */
    loadPreset(name) {
        const presets = this.getAllPresets();
        return presets[name] || null;
    },

    /**
     * Delete a preset
     * @param {String} name - Preset name
     */
    deletePreset(name) {
        const presets = this.getAllPresets();
        delete presets[name];

        try {
            localStorage.setItem('openapi-mcp-presets', JSON.stringify(presets));
        } catch (e) {
            console.error('Error deleting preset:', e);
            throw new Error('Failed to delete preset');
        }
    },

    /**
     * Clear all presets
     */
    clearAllPresets() {
        localStorage.removeItem('openapi-mcp-presets');
    },

    /**
     * Sanitize filename
     */
    sanitizeFilename(name) {
        return name
            .replace(/[^a-z0-9]/gi, '_')
            .replace(/_{2,}/g, '_')
            .toLowerCase();
    },

    /**
     * Format date for display
     */
    formatDate(isoString) {
        const date = new Date(isoString);
        return date.toLocaleString('es-ES', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
};

// Make available globally
window.SelectionConfig = SelectionConfig;
