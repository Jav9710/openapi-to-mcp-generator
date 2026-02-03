/**
 * Spec Config - Sistema de configuración avanzada por especificación
 *
 * Características:
 * - Configuraciones personalizadas por especificación
 * - Perfiles de configuración reutilizables
 * - Editor YAML/JSON
 * - Formulario GUI visual
 * - Validación en tiempo real
 * - Import/Export de configuraciones
 */

const SpecConfig = {
    STORAGE_KEY: 'openapi-mcp-spec-configs',
    PROFILES_KEY: 'openapi-mcp-config-profiles',

    /**
     * Estructura de configuración:
     *
     * Config: {
     *   spec_id: string,
     *   service_name: string,
     *   mcp_framework: 'fastmcp' | 'mcp',
     *   service_prefix: string,
     *   base_url: string?,
     *   environment: 'development' | 'staging' | 'production',
     *   generate_resources: boolean,
     *   include_deprecated: boolean,
     *   auth_config: {
     *     type: 'none' | 'api_key' | 'bearer' | 'basic' | 'oauth2',
     *     api_key_name: string?,
     *     header_name: string?,
     *     token_env: string?,
     *     username_env: string?,
     *     password_env: string?
     *   },
     *   endpoint_filters: {
     *     include: string[],
     *     exclude: string[]
     *   },
     *   retry_config: {
     *     max_retries: number,
     *     backoff_factor: number,
     *     retry_statuses: number[]
     *   },
     *   timeout: number,
     *   log_level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR',
     *   created_at: timestamp,
     *   updated_at: timestamp
     * }
     *
     * Profile: {
     *   id: string,
     *   name: string,
     *   description: string,
     *   config: Partial<Config>,
     *   created_at: timestamp,
     *   is_default: boolean
     * }
     */

    // ========== Gestión de Configuraciones ==========

    /**
     * Obtener configuración por spec_id
     */
    getConfig(specId) {
        const configs = this._getAllConfigs();
        return configs[specId] || this._getDefaultConfig(specId);
    },

    /**
     * Guardar configuración
     */
    saveConfig(specId, config) {
        const configs = this._getAllConfigs();
        const timestamp = Date.now();

        configs[specId] = {
            ...this._getDefaultConfig(specId),
            ...config,
            spec_id: specId,
            updated_at: timestamp,
            created_at: configs[specId]?.created_at || timestamp
        };

        this._saveConfigs(configs);
        return configs[specId];
    },

    /**
     * Eliminar configuración
     */
    deleteConfig(specId) {
        const configs = this._getAllConfigs();
        delete configs[specId];
        this._saveConfigs(configs);
    },

    /**
     * Obtener configuración por defecto
     */
    _getDefaultConfig(specId) {
        return {
            spec_id: specId,
            service_name: 'my_service',
            mcp_framework: 'fastmcp',
            service_prefix: 'myservice',
            base_url: '',
            environment: 'development',
            generate_resources: true,
            include_deprecated: false,
            auth_config: {
                type: 'none',
                api_key_name: 'X-API-Key',
                header_name: 'Authorization',
                token_env: 'API_TOKEN',
                username_env: 'API_USERNAME',
                password_env: 'API_PASSWORD'
            },
            endpoint_filters: {
                include: [],
                exclude: []
            },
            retry_config: {
                max_retries: 3,
                backoff_factor: 0.5,
                retry_statuses: [429, 500, 502, 503, 504]
            },
            timeout: 30,
            log_level: 'INFO',
            created_at: Date.now(),
            updated_at: Date.now()
        };
    },

    // ========== Perfiles de Configuración ==========

    /**
     * Obtener todos los perfiles
     */
    getAllProfiles() {
        const data = localStorage.getItem(this.PROFILES_KEY);
        return data ? JSON.parse(data) : this._getDefaultProfiles();
    },

    /**
     * Obtener un perfil por ID
     */
    getProfile(profileId) {
        const profiles = this.getAllProfiles();
        return profiles.find(p => p.id === profileId);
    },

    /**
     * Guardar perfil
     */
    saveProfile(name, description, config, isDefault = false) {
        const profiles = this.getAllProfiles();
        const profileId = this._generateId();

        const newProfile = {
            id: profileId,
            name: name,
            description: description || '',
            config: config,
            created_at: Date.now(),
            is_default: isDefault
        };

        // Si es default, quitar default de otros
        if (isDefault) {
            profiles.forEach(p => p.is_default = false);
        }

        profiles.push(newProfile);
        this._saveProfiles(profiles);

        return newProfile;
    },

    /**
     * Actualizar perfil
     */
    updateProfile(profileId, updates) {
        const profiles = this.getAllProfiles();
        const profileIndex = profiles.findIndex(p => p.id === profileId);

        if (profileIndex === -1) return null;

        profiles[profileIndex] = {
            ...profiles[profileIndex],
            ...updates,
            id: profileId // Mantener ID
        };

        // Si se marca como default, quitar default de otros
        if (updates.is_default) {
            profiles.forEach((p, i) => {
                if (i !== profileIndex) p.is_default = false;
            });
        }

        this._saveProfiles(profiles);
        return profiles[profileIndex];
    },

    /**
     * Eliminar perfil
     */
    deleteProfile(profileId) {
        const profiles = this.getAllProfiles();
        const filtered = profiles.filter(p => p.id !== profileId);
        this._saveProfiles(filtered);
    },

    /**
     * Aplicar perfil a una configuración
     */
    applyProfile(specId, profileId) {
        const profile = this.getProfile(profileId);
        if (!profile) return null;

        const currentConfig = this.getConfig(specId);
        const mergedConfig = {
            ...currentConfig,
            ...profile.config,
            spec_id: specId,
            updated_at: Date.now()
        };

        return this.saveConfig(specId, mergedConfig);
    },

    /**
     * Obtener perfiles por defecto
     */
    _getDefaultProfiles() {
        return [
            {
                id: 'default-dev',
                name: 'Development',
                description: 'Configuración para desarrollo con logs detallados',
                config: {
                    environment: 'development',
                    log_level: 'DEBUG',
                    timeout: 60,
                    retry_config: {
                        max_retries: 5,
                        backoff_factor: 1.0,
                        retry_statuses: [429, 500, 502, 503, 504]
                    }
                },
                created_at: Date.now(),
                is_default: true
            },
            {
                id: 'default-prod',
                name: 'Production',
                description: 'Configuración optimizada para producción',
                config: {
                    environment: 'production',
                    log_level: 'WARNING',
                    timeout: 30,
                    retry_config: {
                        max_retries: 3,
                        backoff_factor: 0.5,
                        retry_statuses: [429, 500, 502, 503, 504]
                    }
                },
                created_at: Date.now(),
                is_default: false
            },
            {
                id: 'default-api-key',
                name: 'API Key Authentication',
                description: 'Configuración con autenticación por API Key',
                config: {
                    auth_config: {
                        type: 'api_key',
                        api_key_name: 'X-API-Key',
                        token_env: 'API_KEY'
                    }
                },
                created_at: Date.now(),
                is_default: false
            },
            {
                id: 'default-bearer',
                name: 'Bearer Token',
                description: 'Configuración con autenticación Bearer',
                config: {
                    auth_config: {
                        type: 'bearer',
                        header_name: 'Authorization',
                        token_env: 'BEARER_TOKEN'
                    }
                },
                created_at: Date.now(),
                is_default: false
            }
        ];
    },

    // ========== Validación ==========

    /**
     * Validar configuración
     */
    validateConfig(config) {
        const errors = [];
        const warnings = [];

        // Validar service_name
        if (!config.service_name || config.service_name.trim() === '') {
            errors.push('El nombre del servicio es requerido');
        } else if (!/^[a-z][a-z0-9_]*$/.test(config.service_name)) {
            errors.push('El nombre del servicio debe comenzar con letra minúscula y solo contener letras, números y guiones bajos');
        }

        // Validar service_prefix
        if (config.service_prefix && !/^[a-z][a-z0-9_]*$/.test(config.service_prefix)) {
            errors.push('El prefijo debe comenzar con letra minúscula y solo contener letras, números y guiones bajos');
        }

        // Validar base_url
        if (config.base_url) {
            try {
                new URL(config.base_url);
            } catch (e) {
                errors.push('La URL base no es válida');
            }
        }

        // Validar timeout
        if (config.timeout <= 0) {
            errors.push('El timeout debe ser mayor a 0');
        } else if (config.timeout > 300) {
            warnings.push('Un timeout mayor a 300 segundos podría causar problemas');
        }

        // Validar retry_config
        if (config.retry_config) {
            if (config.retry_config.max_retries < 0) {
                errors.push('El número de reintentos no puede ser negativo');
            }
            if (config.retry_config.backoff_factor < 0) {
                errors.push('El factor de backoff no puede ser negativo');
            }
        }

        // Validar auth_config
        if (config.auth_config) {
            const authType = config.auth_config.type;
            if (authType === 'api_key' && !config.auth_config.api_key_name) {
                warnings.push('Se recomienda especificar el nombre del header para API Key');
            }
            if (authType === 'bearer' && !config.auth_config.token_env) {
                warnings.push('Se recomienda especificar la variable de entorno para el token');
            }
        }

        return {
            valid: errors.length === 0,
            errors: errors,
            warnings: warnings
        };
    },

    // ========== Conversión YAML/JSON ==========

    /**
     * Convertir configuración a YAML (simplificado sin librería externa)
     */
    configToYAML(config) {
        const indent = (level) => '  '.repeat(level);

        const toYAML = (obj, level = 0) => {
            let yaml = '';
            for (const [key, value] of Object.entries(obj)) {
                if (value === null || value === undefined) continue;

                yaml += `${indent(level)}${key}:`;

                if (typeof value === 'object' && !Array.isArray(value)) {
                    yaml += '\n' + toYAML(value, level + 1);
                } else if (Array.isArray(value)) {
                    if (value.length === 0) {
                        yaml += ' []\n';
                    } else {
                        yaml += '\n';
                        value.forEach(item => {
                            yaml += `${indent(level + 1)}- ${JSON.stringify(item)}\n`;
                        });
                    }
                } else if (typeof value === 'string') {
                    yaml += ` "${value}"\n`;
                } else {
                    yaml += ` ${value}\n`;
                }
            }
            return yaml;
        };

        // Omitir campos de timestamp para mejor legibilidad
        const cleanConfig = { ...config };
        delete cleanConfig.created_at;
        delete cleanConfig.updated_at;
        delete cleanConfig.spec_id;

        return toYAML(cleanConfig);
    },

    /**
     * Parsear YAML simple a JSON (simplificado)
     */
    parseYAML(yamlString) {
        try {
            // Intentar parsear como JSON primero
            return JSON.parse(yamlString);
        } catch (e) {
            // Si falla, intentar parseo YAML básico
            const lines = yamlString.split('\n');
            const result = {};
            let currentObj = result;
            const stack = [result];
            let lastIndent = 0;

            lines.forEach(line => {
                if (!line.trim() || line.trim().startsWith('#')) return;

                const indent = line.search(/\S/);
                const content = line.trim();

                if (content.includes(':')) {
                    const [key, ...valueParts] = content.split(':');
                    const value = valueParts.join(':').trim();

                    if (!value) {
                        // Objeto anidado
                        const newObj = {};
                        currentObj[key.trim()] = newObj;
                        if (indent > lastIndent) {
                            stack.push(currentObj);
                            currentObj = newObj;
                        }
                    } else {
                        // Valor simple
                        currentObj[key.trim()] = this._parseYAMLValue(value);
                    }

                    lastIndent = indent;
                }
            });

            return result;
        }
    },

    _parseYAMLValue(value) {
        // Eliminar comillas
        value = value.replace(/^["']|["']$/g, '');

        // Booleanos
        if (value === 'true') return true;
        if (value === 'false') return false;

        // Null
        if (value === 'null') return null;

        // Números
        if (!isNaN(value) && value !== '') return Number(value);

        // Arrays
        if (value.startsWith('[') && value.endsWith(']')) {
            try {
                return JSON.parse(value);
            } catch (e) {
                return value;
            }
        }

        return value;
    },

    // ========== Import/Export ==========

    /**
     * Exportar configuración
     */
    exportConfig(specId) {
        const config = this.getConfig(specId);
        const yaml = this.configToYAML(config);

        const blob = new Blob([yaml], { type: 'text/yaml' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${config.service_name}_config.yaml`;
        a.click();
        URL.revokeObjectURL(url);
    },

    /**
     * Importar configuración
     */
    async importConfig(file, specId) {
        const text = await file.text();
        const config = this.parseYAML(text);

        // Validar
        const validation = this.validateConfig(config);
        if (!validation.valid) {
            throw new Error(`Configuración inválida: ${validation.errors.join(', ')}`);
        }

        return this.saveConfig(specId, config);
    },

    /**
     * Exportar perfil
     */
    exportProfile(profileId) {
        const profile = this.getProfile(profileId);
        if (!profile) return;

        const blob = new Blob([JSON.stringify(profile, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `profile_${profile.name.toLowerCase().replace(/\s+/g, '_')}.json`;
        a.click();
        URL.revokeObjectURL(url);
    },

    /**
     * Importar perfil
     */
    async importProfile(file) {
        const text = await file.text();
        const profile = JSON.parse(text);

        // Generar nuevo ID
        const newProfileId = this._generateId();
        const newProfile = {
            ...profile,
            id: newProfileId,
            created_at: Date.now(),
            is_default: false
        };

        const profiles = this.getAllProfiles();
        profiles.push(newProfile);
        this._saveProfiles(profiles);

        return newProfile;
    },

    // ========== Utilidades Privadas ==========

    _generateId() {
        return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    },

    _getAllConfigs() {
        const data = localStorage.getItem(this.STORAGE_KEY);
        return data ? JSON.parse(data) : {};
    },

    _saveConfigs(configs) {
        localStorage.setItem(this.STORAGE_KEY, JSON.stringify(configs));
    },

    _saveProfiles(profiles) {
        localStorage.setItem(this.PROFILES_KEY, JSON.stringify(profiles));
    },

    /**
     * Obtener estadísticas
     */
    getStats() {
        const configs = this._getAllConfigs();
        const profiles = this.getAllProfiles();

        const frameworks = {};
        const environments = {};
        const authTypes = {};

        Object.values(configs).forEach(config => {
            frameworks[config.mcp_framework] = (frameworks[config.mcp_framework] || 0) + 1;
            environments[config.environment] = (environments[config.environment] || 0) + 1;
            authTypes[config.auth_config.type] = (authTypes[config.auth_config.type] || 0) + 1;
        });

        return {
            total_configs: Object.keys(configs).length,
            total_profiles: profiles.length,
            custom_profiles: profiles.filter(p => !p.id.startsWith('default-')).length,
            frameworks: frameworks,
            environments: environments,
            auth_types: authTypes
        };
    }
};
