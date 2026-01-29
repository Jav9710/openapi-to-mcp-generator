/**
 * OpenAPI to MCP Generator - Frontend Application
 */

// State
let allEndpoints = [];
let endpointsByTags = {};
let availableEndpoints = [];
let selectedEndpoints = [];
let currentView = 'list'; // 'list' or 'tags'

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
    cancelBtn: document.getElementById('cancelBtn'),
    resultModal: document.getElementById('resultModal'),
    resultTitle: document.getElementById('resultTitle'),
    resultBody: document.getElementById('resultBody'),
    closeModal: document.getElementById('closeModal'),
    loadingOverlay: document.getElementById('loadingOverlay'),
    serviceName: document.getElementById('serviceName'),
    servicePrefix: document.getElementById('servicePrefix'),
    baseUrl: document.getElementById('baseUrl'),
    mcpFramework: document.getElementById('mcpFramework'),
    environment: document.getElementById('environment'),
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadEndpoints();
    setupEventListeners();
});

// Load endpoints from API
async function loadEndpoints() {
    try {
        showLoading(true);
        const response = await fetch('/api/endpoints');
        const data = await response.json();

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
    elements.cancelBtn.addEventListener('click', () => window.close());

    // Modal
    elements.closeModal.addEventListener('click', () => {
        elements.resultModal.style.display = 'none';
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
async function generateServer() {
    if (selectedEndpoints.length === 0) {
        showModal('Error', 'Debes seleccionar al menos un endpoint.', 'error');
        return;
    }

    const config = {
        selected: selectedEndpoints.map(ep => ep.key),
        service_name: elements.serviceName.value || 'api',
        service_prefix: elements.servicePrefix.value || elements.serviceName.value || 'api',
        base_url: elements.baseUrl.value || null,
        mcp_framework: elements.mcpFramework.value,
        environment: elements.environment.value,
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
            showModal(
                'Servidor Generado',
                `<p>El servidor MCP se ha generado correctamente.</p>
                <p><strong>Ubicación:</strong> <code>${result.output_path}</code></p>
                <p><strong>Tools:</strong> ${result.tools_count}</p>
                <p><strong>Resources:</strong> ${result.resources_count}</p>
                ${result.warnings.length > 0
                    ? `<p><strong>Advertencias:</strong> ${result.warnings.join(', ')}</p>`
                    : ''}
                <br>
                <p><strong>Próximos pasos:</strong></p>
                <ol>
                    <li>cd ${result.output_path}</li>
                    <li>cp .env.example .env</li>
                    <li>Edita .env con tus credenciales</li>
                    <li>pip install -r requirements.txt</li>
                    <li>python -m src.server</li>
                </ol>`,
                'success'
            );
        } else {
            showModal(
                'Error',
                `<p>Error generando el servidor:</p>
                <p><code>${result.error || result.errors.join(', ')}</code></p>`,
                'error'
            );
        }
    } catch (error) {
        console.error('Error:', error);
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
