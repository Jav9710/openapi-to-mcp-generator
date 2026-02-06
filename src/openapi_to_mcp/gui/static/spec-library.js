/**
 * Spec Library - Sistema de gestión de especificaciones OpenAPI
 *
 * Características:
 * - Almacenamiento de especificaciones con versionado
 * - Búsqueda y filtrado
 * - Etiquetado y favoritos
 * - Historial de versiones con diff
 * - Registro de generaciones MCP
 */

const SpecLibrary = {
    STORAGE_KEY: 'openapi-mcp-spec-library',
    VERSIONS_KEY: 'openapi-mcp-spec-versions',
    GENERATIONS_KEY: 'openapi-mcp-generations',

    /**
     * Estructura de datos:
     *
     * Spec: {
     *   id: string,
     *   name: string,
     *   title: string,
     *   version: string,
     *   description: string,
     *   source: 'upload' | 'url',
     *   source_url: string?,
     *   tags: string[],
     *   favorite: boolean,
     *   folder: string?,
     *   created_at: timestamp,
     *   updated_at: timestamp,
     *   current_version_id: string,
     *   versions_count: number
     * }
     *
     * Version: {
     *   id: string,
     *   spec_id: string,
     *   version_number: number,
     *   spec_data: object,  // La especificación OpenAPI completa
     *   note: string?,
     *   created_at: timestamp,
     *   created_by: string?,
     *   endpoints_count: number,
     *   changes_summary: string?
     * }
     *
     * Generation: {
     *   id: string,
     *   version_id: string,
     *   spec_id: string,
     *   config: object,
     *   created_at: timestamp,
     *   stats: {
     *     tools_count: number,
     *     resources_count: number,
     *     generation_time: number?
     *   },
     *   download_url: string?
     * }
     */

    // ========== Gestión de Especificaciones ==========

    /**
     * Obtener todas las especificaciones
     */
    getAllSpecs() {
        const data = localStorage.getItem(this.STORAGE_KEY);
        return data ? JSON.parse(data) : [];
    },

    /**
     * Guardar especificación (crea nueva o actualiza existente)
     */
    saveSpec(specData, note = null, isUpdate = false) {
        const specs = this.getAllSpecs();
        const timestamp = Date.now();

        // Buscar si ya existe una spec con el mismo título y source
        let existingSpec = null;
        if (isUpdate) {
            existingSpec = specs.find(s =>
                s.title === specData.title &&
                (s.source === specData.source ||
                 (specData.source_url && s.source_url === specData.source_url))
            );
        }

        if (existingSpec) {
            // Actualizar spec existente con nueva versión
            existingSpec.updated_at = timestamp;
            existingSpec.description = specData.description || existingSpec.description;
            existingSpec.version = specData.version;
            existingSpec.versions_count++;

            // Crear nueva versión
            const versionId = this._createVersion(existingSpec.id, specData, note);
            existingSpec.current_version_id = versionId;

            this._saveSpecs(specs);
            return { spec: existingSpec, version_id: versionId, is_new: false };
        } else {
            // Crear nueva spec
            const specId = this._generateId();
            const newSpec = {
                id: specId,
                name: this._sanitizeName(specData.title),
                title: specData.title || 'Untitled API',
                version: specData.version || '1.0.0',
                description: specData.description || '',
                source: specData.source || 'upload',
                source_url: specData.source_url || null,
                tags: [],
                favorite: false,
                folder: null,
                created_at: timestamp,
                updated_at: timestamp,
                current_version_id: null,
                versions_count: 1
            };

            // Crear primera versión
            const versionId = this._createVersion(specId, specData, note || 'Versión inicial');
            newSpec.current_version_id = versionId;

            specs.push(newSpec);
            this._saveSpecs(specs);

            return { spec: newSpec, version_id: versionId, is_new: true };
        }
    },

    /**
     * Obtener una especificación por ID
     */
    getSpec(specId) {
        const specs = this.getAllSpecs();
        return specs.find(s => s.id === specId);
    },

    /**
     * Eliminar especificación (y todas sus versiones)
     */
    deleteSpec(specId) {
        const specs = this.getAllSpecs().filter(s => s.id !== specId);
        this._saveSpecs(specs);

        // Eliminar todas las versiones
        const versions = this.getAllVersions().filter(v => v.spec_id !== specId);
        this._saveVersions(versions);

        // Eliminar todas las generaciones
        const generations = this.getAllGenerations().filter(g => g.spec_id !== specId);
        this._saveGenerations(generations);
    },

    /**
     * Actualizar metadatos de especificación
     */
    updateSpecMetadata(specId, updates) {
        const specs = this.getAllSpecs();
        const spec = specs.find(s => s.id === specId);

        if (spec) {
            Object.assign(spec, updates, { updated_at: Date.now() });
            this._saveSpecs(specs);
            return spec;
        }
        return null;
    },

    /**
     * Toggle favorito
     */
    toggleFavorite(specId) {
        const specs = this.getAllSpecs();
        const spec = specs.find(s => s.id === specId);

        if (spec) {
            spec.favorite = !spec.favorite;
            spec.updated_at = Date.now();
            this._saveSpecs(specs);
            return spec.favorite;
        }
        return false;
    },

    /**
     * Agregar/remover tags
     */
    addTag(specId, tag) {
        const spec = this.getSpec(specId);
        if (spec && !spec.tags.includes(tag)) {
            spec.tags.push(tag);
            this.updateSpecMetadata(specId, { tags: spec.tags });
        }
    },

    removeTag(specId, tag) {
        const spec = this.getSpec(specId);
        if (spec) {
            spec.tags = spec.tags.filter(t => t !== tag);
            this.updateSpecMetadata(specId, { tags: spec.tags });
        }
    },

    // ========== Versionado ==========

    /**
     * Crear nueva versión de una especificación
     */
    _createVersion(specId, specData, note = null) {
        const versions = this.getAllVersions();
        const specVersions = versions.filter(v => v.spec_id === specId);
        const versionNumber = specVersions.length + 1;

        const versionId = this._generateId();
        const newVersion = {
            id: versionId,
            spec_id: specId,
            version_number: versionNumber,
            spec_data: specData,
            note: note,
            created_at: Date.now(),
            created_by: 'user',
            endpoints_count: this._countEndpoints(specData),
            changes_summary: versionNumber === 1 ? 'Versión inicial' : this._generateChangesSummary(specVersions[specVersions.length - 1], specData)
        };

        versions.push(newVersion);
        this._saveVersions(versions);

        return versionId;
    },

    /**
     * Obtener todas las versiones
     */
    getAllVersions() {
        const data = localStorage.getItem(this.VERSIONS_KEY);
        return data ? JSON.parse(data) : [];
    },

    /**
     * Obtener versiones de una especificación
     */
    getVersions(specId) {
        return this.getAllVersions()
            .filter(v => v.spec_id === specId)
            .sort((a, b) => b.version_number - a.version_number);
    },

    /**
     * Obtener una versión específica
     */
    getVersion(versionId) {
        const versions = this.getAllVersions();
        return versions.find(v => v.id === versionId);
    },

    /**
     * Restaurar una versión anterior (crea una nueva versión)
     */
    restoreVersion(versionId, note = null) {
        const version = this.getVersion(versionId);
        if (!version) return null;

        const spec = this.getSpec(version.spec_id);
        if (!spec) return null;

        const newNote = note || `Restaurada desde versión ${version.version_number}`;
        return this.saveSpec(version.spec_data, newNote, true);
    },

    /**
     * Comparar dos versiones (genera diff básico)
     */
    compareVersions(versionId1, versionId2) {
        const v1 = this.getVersion(versionId1);
        const v2 = this.getVersion(versionId2);

        if (!v1 || !v2) return null;

        return {
            version1: v1,
            version2: v2,
            endpoints_diff: {
                added: this._getEndpointsDiff(v1.spec_data, v2.spec_data, 'added'),
                removed: this._getEndpointsDiff(v1.spec_data, v2.spec_data, 'removed'),
                modified: this._getEndpointsDiff(v1.spec_data, v2.spec_data, 'modified')
            },
            summary: this._generateDiffSummary(v1.spec_data, v2.spec_data)
        };
    },

    // ========== Generaciones MCP ==========

    /**
     * Registrar una generación MCP
     */
    registerGeneration(versionId, config, stats = {}) {
        const version = this.getVersion(versionId);
        if (!version) return null;

        const generations = this.getAllGenerations();
        const generationId = this._generateId();

        const newGeneration = {
            id: generationId,
            version_id: versionId,
            spec_id: version.spec_id,
            config: config,
            created_at: Date.now(),
            stats: {
                tools_count: stats.tools_count || 0,
                resources_count: stats.resources_count || 0,
                generation_time: stats.generation_time || null
            },
            download_url: stats.download_url || null
        };

        generations.push(newGeneration);
        this._saveGenerations(generations);

        return newGeneration;
    },

    /**
     * Obtener todas las generaciones
     */
    getAllGenerations() {
        const data = localStorage.getItem(this.GENERATIONS_KEY);
        return data ? JSON.parse(data) : [];
    },

    /**
     * Obtener generaciones de una versión
     */
    getGenerations(versionId) {
        return this.getAllGenerations()
            .filter(g => g.version_id === versionId)
            .sort((a, b) => b.created_at - a.created_at);
    },

    /**
     * Obtener generaciones de una especificación
     */
    getSpecGenerations(specId) {
        return this.getAllGenerations()
            .filter(g => g.spec_id === specId)
            .sort((a, b) => b.created_at - a.created_at);
    },

    // ========== Búsqueda y Filtrado ==========

    /**
     * Buscar especificaciones
     */
    search(query, filters = {}) {
        let specs = this.getAllSpecs();

        // Filtrar por texto
        if (query) {
            const lowerQuery = query.toLowerCase();
            specs = specs.filter(spec =>
                spec.title.toLowerCase().includes(lowerQuery) ||
                spec.description.toLowerCase().includes(lowerQuery) ||
                spec.tags.some(tag => tag.toLowerCase().includes(lowerQuery))
            );
        }

        // Filtrar por favoritos
        if (filters.favorites) {
            specs = specs.filter(spec => spec.favorite);
        }

        // Filtrar por tags
        if (filters.tags && filters.tags.length > 0) {
            specs = specs.filter(spec =>
                filters.tags.some(tag => spec.tags.includes(tag))
            );
        }

        // Filtrar por carpeta
        if (filters.folder) {
            specs = specs.filter(spec => spec.folder === filters.folder);
        }

        // Ordenar
        const sortBy = filters.sortBy || 'updated_at';
        const sortOrder = filters.sortOrder || 'desc';

        specs.sort((a, b) => {
            let comparison = 0;
            if (sortBy === 'title') {
                comparison = a.title.localeCompare(b.title);
            } else if (sortBy === 'created_at' || sortBy === 'updated_at') {
                comparison = a[sortBy] - b[sortBy];
            }
            return sortOrder === 'asc' ? comparison : -comparison;
        });

        return specs;
    },

    /**
     * Obtener todos los tags únicos
     */
    getAllTags() {
        const specs = this.getAllSpecs();
        const tagsSet = new Set();
        specs.forEach(spec => {
            spec.tags.forEach(tag => tagsSet.add(tag));
        });
        return Array.from(tagsSet).sort();
    },

    /**
     * Obtener todas las carpetas únicas
     */
    getAllFolders() {
        const specs = this.getAllSpecs();
        const foldersSet = new Set();
        specs.forEach(spec => {
            if (spec.folder) foldersSet.add(spec.folder);
        });
        return Array.from(foldersSet).sort();
    },

    // ========== Estadísticas ==========

    /**
     * Obtener estadísticas de la biblioteca
     */
    getStats() {
        const specs = this.getAllSpecs();
        const versions = this.getAllVersions();
        const generations = this.getAllGenerations();

        const genTimes = generations
            .filter(g => g.stats && g.stats.generation_time != null)
            .map(g => g.stats.generation_time);
        const avgGenTime = genTimes.length > 0
            ? Math.round(genTimes.reduce((a, b) => a + b, 0) / genTimes.length)
            : null;

        return {
            total_specs: specs.length,
            total_versions: versions.length,
            total_generations: generations.length,
            favorites_count: specs.filter(s => s.favorite).length,
            avg_versions_per_spec: specs.length > 0 ? (versions.length / specs.length).toFixed(1) : 0,
            avg_generation_time: avgGenTime,
            most_recent_spec: specs.length > 0 ? specs.reduce((a, b) => a.updated_at > b.updated_at ? a : b) : null,
            most_generated_spec: this._getMostGeneratedSpec(specs, generations)
        };
    },

    // ========== Utilidades Privadas ==========

    _generateId() {
        return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    },

    _sanitizeName(title) {
        return title.toLowerCase()
            .replace(/[^a-z0-9]+/g, '_')
            .replace(/^_+|_+$/g, '');
    },

    _saveSpecs(specs) {
        localStorage.setItem(this.STORAGE_KEY, JSON.stringify(specs));
    },

    _saveVersions(versions) {
        localStorage.setItem(this.VERSIONS_KEY, JSON.stringify(versions));
    },

    _saveGenerations(generations) {
        localStorage.setItem(this.GENERATIONS_KEY, JSON.stringify(generations));
    },

    _countEndpoints(specData) {
        if (!specData || !specData.paths) return 0;
        let count = 0;
        Object.values(specData.paths).forEach(pathItem => {
            const methods = ['get', 'post', 'put', 'patch', 'delete', 'options', 'head'];
            methods.forEach(method => {
                if (pathItem[method]) count++;
            });
        });
        return count;
    },

    _generateChangesSummary(previousVersion, newSpecData) {
        if (!previousVersion) return 'Versión inicial';

        const oldEndpoints = this._countEndpoints(previousVersion.spec_data);
        const newEndpoints = this._countEndpoints(newSpecData);
        const diff = newEndpoints - oldEndpoints;

        if (diff > 0) {
            return `+${diff} endpoints`;
        } else if (diff < 0) {
            return `${diff} endpoints`;
        } else {
            return 'Sin cambios en endpoints';
        }
    },

    _getEndpointsDiff(spec1, spec2, type) {
        const paths1 = Object.keys(spec1.paths || {});
        const paths2 = Object.keys(spec2.paths || {});

        if (type === 'added') {
            return paths2.filter(p => !paths1.includes(p));
        } else if (type === 'removed') {
            return paths1.filter(p => !paths2.includes(p));
        } else if (type === 'modified') {
            return paths1
                .filter(p => paths2.includes(p) &&
                    JSON.stringify(spec1.paths[p]) !== JSON.stringify(spec2.paths[p]))
                .map(p => ({
                    path: p,
                    details: this._getDetailedEndpointDiff(p, spec1, spec2)
                }));
        }
        return [];
    },

    _getDetailedEndpointDiff(path, spec1, spec2) {
        const methods = ['get', 'post', 'put', 'patch', 'delete', 'options', 'head'];
        const pathItem1 = spec1.paths[path] || {};
        const pathItem2 = spec2.paths[path] || {};
        const changes = [];

        methods.forEach(method => {
            const op1 = pathItem1[method];
            const op2 = pathItem2[method];

            if (!op1 && op2) {
                changes.push({ type: 'method_added', method: method.toUpperCase() });
            } else if (op1 && !op2) {
                changes.push({ type: 'method_removed', method: method.toUpperCase() });
            } else if (op1 && op2 && JSON.stringify(op1) !== JSON.stringify(op2)) {
                const propChanges = [];
                if (op1.summary !== op2.summary) propChanges.push('summary');
                if (op1.description !== op2.description) propChanges.push('description');
                if (JSON.stringify(op1.parameters || []) !== JSON.stringify(op2.parameters || [])) propChanges.push('parameters');
                if (JSON.stringify(op1.requestBody) !== JSON.stringify(op2.requestBody)) propChanges.push('requestBody');
                if (JSON.stringify(op1.responses) !== JSON.stringify(op2.responses)) propChanges.push('responses');
                if (JSON.stringify(op1.security) !== JSON.stringify(op2.security)) propChanges.push('security');
                if (op1.deprecated !== op2.deprecated) propChanges.push('deprecated');
                if (JSON.stringify(op1.tags) !== JSON.stringify(op2.tags)) propChanges.push('tags');

                changes.push({
                    type: 'method_modified',
                    method: method.toUpperCase(),
                    properties: propChanges
                });
            }
        });

        return changes;
    },

    _generateDiffSummary(spec1, spec2) {
        const paths1 = Object.keys(spec1.paths || {});
        const paths2 = Object.keys(spec2.paths || {});
        const added = paths2.filter(p => !paths1.includes(p)).length;
        const removed = paths1.filter(p => !paths2.includes(p)).length;
        const modified = paths1.filter(p => paths2.includes(p) &&
            JSON.stringify(spec1.paths[p]) !== JSON.stringify(spec2.paths[p])).length;

        const parts = [];
        if (added > 0) parts.push(`+${added} nuevos`);
        if (removed > 0) parts.push(`-${removed} eliminados`);
        if (modified > 0) parts.push(`~${modified} modificados`);

        return parts.length > 0 ? parts.join(', ') : 'Sin cambios';
    },

    _getMostGeneratedSpec(specs, generations) {
        if (specs.length === 0 || generations.length === 0) return null;

        const genCounts = {};
        generations.forEach(gen => {
            genCounts[gen.spec_id] = (genCounts[gen.spec_id] || 0) + 1;
        });

        const maxSpecId = Object.keys(genCounts).reduce((a, b) =>
            genCounts[a] > genCounts[b] ? a : b
        );

        return specs.find(s => s.id === maxSpecId);
    },

    /**
     * Exportar biblioteca completa
     */
    exportLibrary() {
        return {
            specs: this.getAllSpecs(),
            versions: this.getAllVersions(),
            generations: this.getAllGenerations(),
            exported_at: new Date().toISOString(),
            version: '1.0'
        };
    },

    /**
     * Importar biblioteca completa
     */
    importLibrary(data, merge = false) {
        if (!data || !data.specs) {
            throw new Error('Datos de biblioteca inválidos');
        }

        if (merge) {
            // Merge con datos existentes
            const existingSpecs = this.getAllSpecs();
            const existingVersions = this.getAllVersions();
            const existingGenerations = this.getAllGenerations();

            this._saveSpecs([...existingSpecs, ...data.specs]);
            this._saveVersions([...existingVersions, ...(data.versions || [])]);
            this._saveGenerations([...existingGenerations, ...(data.generations || [])]);
        } else {
            // Reemplazar completamente
            this._saveSpecs(data.specs);
            this._saveVersions(data.versions || []);
            this._saveGenerations(data.generations || []);
        }
    },

    /**
     * Limpiar toda la biblioteca
     */
    clearLibrary() {
        if (confirm('¿Estás seguro de que quieres eliminar toda la biblioteca? Esta acción no se puede deshacer.')) {
            localStorage.removeItem(this.STORAGE_KEY);
            localStorage.removeItem(this.VERSIONS_KEY);
            localStorage.removeItem(this.GENERATIONS_KEY);
            return true;
        }
        return false;
    }
};
