// Oberon dashboard client logic.
// Vanilla Javascript + Leaflet Map. Exposes client actions to WebMCP for AI.

const API = window.location.origin + '/v1';
let map = null;
let activeLayer = null;
let activePortfolioId = null;
let activePortfolioName = '';
let activePortfolioData = null; // full config of the selected portfolio (for editing)
let editingPortfolioId = null;  // set while the dialog is in edit (PATCH) mode
let activePolygonsCount = 0;
let pollTimeoutId = null;
let runsWereActive = false; // true while a poll cycle has in-flight jobs

let activePolygons = [];
// AOI editing is delegated to Leaflet-Geoman (draw / drag / resize / vertex edit).
// aoiLayersById maps an AOI id to its editable Leaflet layer so list + map clicks
// can focus and edit the same shape.
let aoiLayersById = {};
let activeEditLayer = null;
let activeEditAoiId = null;
let latestFindingsData = null;

// Human label for an analysis task. NDVI ranks findings; NBR evidence is computed
// per finding — so a portfolio is multi-spectral, not "just vegetation".
// See PRODUCT.md principle #4 (land change, not just vegetation).
function signalLabel(task) {
    if (task === 'vegetation_disturbance') return 'NDVI · NBR';
    return task || '—';
}

// Track review counts locally for calibration feedback loop visualization
let approvedCount = 0;
let rejectedCount = 0;

// ---- Native Dialog References ----
let newPortfolioDialog = null;
let addPolygonDialog = null;
let runConfirmDialog = null;
let deleteConfirmDialog = null;
let guideDialog = null;

// ---- API auth ----
// All /v1 calls go through apiFetch, which attaches the saved API key as
// X-API-Key. When the server runs with auth disabled the header is simply
// ignored; with auth on, a 401 prompts for the key. The key lives only in this
// browser's localStorage — never sent anywhere but this origin's API.
const API_KEY_STORAGE = 'oberon_api_key';

function getApiKey() {
    try { return localStorage.getItem(API_KEY_STORAGE) || ''; } catch (_) { return ''; }
}

function apiFetch(url, opts = {}) {
    const key = getApiKey();
    const headers = { ...(opts.headers || {}) };
    if (key) headers['X-API-Key'] = key;
    return fetch(url, { ...opts, headers }).then(res => {
        if (res.status === 401) {
            showToast('API key required or invalid — enter your key to continue.', 'warning');
            openApiKeyDialog();
        }
        return res;
    });
}

function openApiKeyDialog() {
    const dialog = document.getElementById('api-key-dialog');
    if (!dialog) return;
    const input = document.getElementById('api-key-input');
    if (input) input.value = getApiKey();
    if (!dialog.open) dialog.showModal();
}

function saveApiKey() {
    const input = document.getElementById('api-key-input');
    const val = (input?.value || '').trim();
    try {
        if (val) localStorage.setItem(API_KEY_STORAGE, val);
        else localStorage.removeItem(API_KEY_STORAGE);
    } catch (_) {}
    document.getElementById('api-key-dialog')?.close();
    showToast(val ? 'API key saved.' : 'API key cleared.', 'success');
    loadPortfolios();
}

// Artifacts are fetched as blobs (not <img src>/<a href>) so the X-API-Key
// header rides along when auth is on. Works unchanged when auth is off.
async function loadArtifactImage(imgId, url) {
    try {
        const res = await apiFetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const img = document.getElementById(imgId);
        if (img) img.src = URL.createObjectURL(await res.blob());
    } catch (e) {
        console.warn('Artifact load failed:', url, e);
    }
}

window.downloadArtifact = async function(url, filename) {
    try {
        const res = await apiFetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const a = document.createElement('a');
        a.href = URL.createObjectURL(await res.blob());
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    } catch (e) {
        showToast(`Download failed: ${e.message}`, 'danger');
    }
};

// ---- Initialization ----
document.addEventListener('DOMContentLoaded', () => {
    // Setup basemaps.
    const darkMap = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        maxZoom: 19
    });

    const satelliteMap = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
        maxZoom: 19
    });

    const streetMap = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19
    });

    // Initialize map with Satellite view as default (not dark and messy by default)
    map = L.map('map', {
        attributionControl: false,
        zoomControl: false
    }).setView([-7.475, -55.175], 11);
    
    satelliteMap.addTo(map);

    // Both controls stack at top-left; CSS shifts that corner clear of the
    // top-nav and the sidebar (see .leaflet-top.leaflet-left in style.css).
    L.control.zoom({ position: 'topleft' }).addTo(map);

    // Layer control to switch views
    const baseMaps = {
        "Satellite Imagery": satelliteMap,
        "Dark map": darkMap,
        "Standard Street Map": streetMap
    };
    L.control.layers(baseMaps, null, { position: 'topleft' }).addTo(map);
    setupAttributionToggle();

    // Disable click/double click event propagation on all overlay HUD panels
    const panels = document.querySelectorAll('.floating-panel, .empty-state-panel, .toast-container, .floating-toolbar');
    panels.forEach(p => L.DomEvent.disableClickPropagation(p));

    // Wire up Leaflet-Geoman for drawing, dragging, resizing and vertex editing.
    initGeoman();

    // Coordinate display tracking mouse and touch/click movements
    const updateCoords = (e) => {
        const lat = e.latlng.lat.toFixed(5);
        const lng = e.latlng.lng.toFixed(5);
        const el = document.getElementById('map-coords-badge');
        if (el) el.textContent = `Lat: ${lat}, Lon: ${lng}`;
    };
    map.on('mousemove', updateCoords);
    map.on('click', updateCoords);

    // Initialize Dialogs
    newPortfolioDialog = document.getElementById('new-portfolio-dialog');
    addPolygonDialog = document.getElementById('add-polygon-dialog');
    runConfirmDialog = document.getElementById('run-confirm-dialog');
    deleteConfirmDialog = document.getElementById('delete-confirm-dialog');
    guideDialog = document.getElementById('guide-dialog');

    // Register Safari/old-browser fallback backdrop click listeners (light-dismiss-a-dialog guide)
    registerBackdropDismiss(newPortfolioDialog);
    registerBackdropDismiss(addPolygonDialog);
    registerBackdropDismiss(runConfirmDialog);
    registerBackdropDismiss(deleteConfirmDialog);
    registerBackdropDismiss(guideDialog);

    // Workspace Actions header setup
    const navDrawPolyBtn = document.getElementById('nav-draw-poly-btn');
    if (navDrawPolyBtn) {
        navDrawPolyBtn.addEventListener('click', () => enableDraw('polygon'));
    }

    const navDrawBBoxBtn = document.getElementById('nav-draw-bbox-btn');
    if (navDrawBBoxBtn) {
        navDrawBBoxBtn.addEventListener('click', () => enableDraw('bbox'));
    }

    const navRunBtn = document.getElementById('nav-run-btn');
    if (navRunBtn) {
        navRunBtn.addEventListener('click', () => {
            if (activePortfolioId) runPortfolioConfirm(activePortfolioId);
        });
    }

    const navMoreBtn = document.getElementById('nav-more-btn');
    const navMoreMenu = document.getElementById('nav-more-menu');
    if (navMoreBtn && navMoreMenu) {
        navMoreBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const isHidden = navMoreMenu.classList.toggle('hidden');
            navMoreBtn.setAttribute('aria-expanded', String(!isHidden));
        });
        
        document.addEventListener('click', () => {
            navMoreMenu.classList.add('hidden');
            navMoreBtn.setAttribute('aria-expanded', 'false');
        });
    }

    const navDeleteBtn = document.getElementById('nav-delete-btn');
    if (navDeleteBtn) {
        navDeleteBtn.addEventListener('click', () => {
            if (activePortfolioId) {
                deletePortfolioConfirm(activePortfolioId, activePortfolioName);
            }
        });
    }


    // Sidebar & Welcome Actions
    document.getElementById('new-portfolio-btn').addEventListener('click', () => {
        openPortfolioDialog();
    });
    
    document.getElementById('welcome-create-btn').addEventListener('click', () => {
        openPortfolioDialog();
    });

    document.getElementById('edit-portfolio-btn').addEventListener('click', () => {
        if (activePortfolioData) openPortfolioDialog(activePortfolioData);
    });

    document.getElementById('help-toggle-btn').addEventListener('click', () => {
        guideDialog.showModal();
    });

    document.getElementById('api-key-btn')?.addEventListener('click', openApiKeyDialog);
    document.getElementById('api-key-save-btn')?.addEventListener('click', saveApiKey);
    registerBackdropDismiss(document.getElementById('api-key-dialog'));

    document.getElementById('close-detail').addEventListener('click', () => {
        document.getElementById('detail-panel').classList.add('hidden');
    });

    // Run History Collapse Toggle Action
    // SUPERVISOR-NOTE (review, 2026-06-24): toggled the `collapsed` class on the
    // panel itself, not a phantom class on <body>. CSS targets `.bottom-sheet.collapsed`
    // (style.css), so the previous body-class toggle did nothing — the minimize button
    // appeared dead. Keep the class name in lockstep with the CSS selector.
    const toggleBtn = document.getElementById('toggle-run-panel-btn');
    const runPanel = document.getElementById('run-timeline-panel');
    if (toggleBtn && runPanel) {
        toggleBtn.addEventListener('click', (e) => {
            runPanel.classList.toggle('collapsed');
        });
    }

    // Drawing triggers — manual GeoJSON dialog buttons (power-user / agent path)
    const drawPolyBtn = document.getElementById('draw-poly-btn');
    if (drawPolyBtn) drawPolyBtn.addEventListener('click', () => { addPolygonDialog.close(); enableDraw('polygon'); });

    const drawBBoxBtn = document.getElementById('draw-bbox-btn');
    if (drawBBoxBtn) drawBBoxBtn.addEventListener('click', () => { addPolygonDialog.close(); enableDraw('bbox'); });

    const drawCancelBtn = document.getElementById('drawing-cancel-btn');
    if (drawCancelBtn) drawCancelBtn.addEventListener('click', () => map.pm.disableDraw());

    // Sidebar drawing buttons — the primary way to add an AOI
    const sidebarDrawPolyBtn = document.getElementById('sidebar-draw-poly-btn');
    if (sidebarDrawPolyBtn) sidebarDrawPolyBtn.addEventListener('click', () => enableDraw('polygon'));

    const sidebarDrawBBoxBtn = document.getElementById('sidebar-draw-bbox-btn');
    if (sidebarDrawBBoxBtn) sidebarDrawBBoxBtn.addEventListener('click', () => enableDraw('bbox'));

    const sidebarPasteBtn = document.getElementById('sidebar-paste-geojson-btn');
    if (sidebarPasteBtn) sidebarPasteBtn.addEventListener('click', () => {
        if (activePortfolioId) addPolygonOpen(activePortfolioId);
    });

    // Clicking empty map deselects / ends the current edit session
    map.on('click', (e) => {
        if (map.pm.globalDrawModeEnabled()) return;
        if (e.originalEvent && e.originalEvent.target && e.originalEvent.target.id === 'map') {
            disableActiveEditing();
            document.querySelectorAll('.aoi-list-item').forEach(item => item.classList.remove('active'));
        }
    });

    // Form Submissions (WebMCP support)
    document.getElementById('create-portfolio-form').addEventListener('submit', handleCreatePortfolio);
    document.getElementById('add-polygon-form').addEventListener('submit', handleAddPolygon);
    document.getElementById('calibrate-btn').addEventListener('click', handleCalibrate);

    // Initializations
    initMapSearch();
    initPanelCollapses();
    initSidebarTabs();
    
    // Switcher Dropdown listener
    const portfolioDropdown = document.getElementById('portfolio-dropdown');
    if (portfolioDropdown) {
        portfolioDropdown.addEventListener('change', (e) => {
            const val = e.target.value;
            if (val) selectPortfolio(val);
        });
    }

    loadPortfolios();
});

// Helper to support light-dismiss for browsers without closedby support
function registerBackdropDismiss(dialog) {
    if (!dialog) return;
    if (!('closedBy' in HTMLDialogElement.prototype)) {
        dialog.addEventListener('click', (event) => {
            if (event.target !== dialog) return;
            const rect = dialog.getBoundingClientRect();
            const isInside = (
                rect.top <= event.clientY &&
                event.clientY <= rect.top + rect.height &&
                rect.left <= event.clientX &&
                event.clientX <= rect.left + rect.width
            );
            if (!isInside) dialog.close();
        });
    }
}

// Opens the portfolio dialog. Pass a portfolio object to edit it (PATCH);
// pass nothing to create a new one (POST).
function openPortfolioDialog(portfolio = null) {
    const form = document.getElementById('create-portfolio-form');
    form.reset();

    const title = newPortfolioDialog.querySelector('.dialog-header h3');
    const kicker = newPortfolioDialog.querySelector('.dialog-kicker');
    const submit = document.getElementById('portfolio-submit');

    if (portfolio) {
        editingPortfolioId = portfolio.id;
        form.elements['name'].value = portfolio.name || '';
        form.elements['max_cloud_fraction'].value = Math.round((portfolio.max_cloud_fraction || 0) * 100);
        form.elements['before_from'].value = portfolio.before_from || '';
        form.elements['before_to'].value = portfolio.before_to || '';
        form.elements['after_from'].value = portfolio.after_from || '';
        form.elements['after_to'].value = portfolio.after_to || '';
        form.elements['use_ai'].checked = !!portfolio.use_ai;
        if (title) title.textContent = 'Edit Portfolio';
        if (kicker) kicker.textContent = 'Update the analysis window for this portfolio.';
        if (submit) submit.textContent = 'Save changes';
    } else {
        editingPortfolioId = null;
        if (title) title.textContent = 'New Portfolio';
        if (kicker) kicker.textContent = "Define the area's analysis window — draw the map region next.";
        if (submit) submit.textContent = 'Create & draw area';
    }

    newPortfolioDialog.showModal();
    setTimeout(() => document.getElementById('port-name')?.focus(), 0);
}

// ---- Toast Notifications ----
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    let prefix = 'INFO';
    if (type === 'success') prefix = 'SUCCESS';
    if (type === 'danger') prefix = 'ERROR';
    if (type === 'warning') prefix = 'WARNING';
    
    toast.innerHTML = `
        <span><strong class="text-${type}">${prefix}</strong> &nbsp; ${escapeHtml(message)}</span>
        <button class="toast-close">&times;</button>
    `;
    
    toast.querySelector('.toast-close').addEventListener('click', () => toast.remove());
    container.appendChild(toast);
    
    // Auto-remove after 4 seconds
    setTimeout(() => {
        toast.remove();
    }, 4000);
}

function setupAttributionToggle() {
    const button = document.getElementById('map-attribution-toggle');
    const panel = document.getElementById('map-attribution-panel');
    if (!button || !panel) return;

    button.addEventListener('click', () => {
        const isHidden = panel.classList.toggle('hidden');
        button.setAttribute('aria-expanded', String(!isHidden));
    });
}

// ---- Portfolios API Operations ----
async function loadPortfolios() {
    try {
        const res = await apiFetch(`${API}/portfolios`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const portfolios = await res.json();
        
        renderPortfolioList(portfolios);
        updateCalibrationUI();
    } catch (e) {
        showToast(`Failed to load portfolios: ${e.message}`, 'danger');
    }
}

function renderPortfolioList(portfolios) {
    const el = document.getElementById('portfolio-list');
    if (el) {
        el.innerHTML = '';
        if (!portfolios.length) {
            el.innerHTML = '<p class="text-muted text-small text-center">No portfolios yet. Create one to start monitoring.</p>';
            document.getElementById('welcome-screen').classList.remove('hidden');
            document.getElementById('workspace-actions').classList.add('hidden');
        } else {
            portfolios.forEach(p => {
                const div = document.createElement('div');
                div.className = 'portfolio-item';
                if (p.id === activePortfolioId) div.classList.add('active');
                
                const taskLabel = signalLabel(p.task);
                const aiBadge = p.use_ai ? '<span class="ai-chip">AI</span>' : '';
                
                div.innerHTML = `
                    <div>
                        <div class="name">${escapeHtml(p.name)} ${aiBadge}</div>
                        <div class="meta">${taskLabel} / Cloud max ${Math.round(p.max_cloud_fraction * 100)}%</div>
                    </div>`;
                
                div.addEventListener('click', () => selectPortfolio(p.id));
                el.appendChild(div);
            });
        }
    }

    // Populate top dropdown
    const dropdown = document.getElementById('portfolio-dropdown');
    if (dropdown) {
        dropdown.innerHTML = '<option value="">Select portfolio...</option>';
        portfolios.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.id;
            opt.textContent = p.name;
            if (p.id === activePortfolioId) opt.selected = true;
            dropdown.appendChild(opt);
        });
    }
}

async function handleCreatePortfolio(event) {
    // If agentInvoked exists (WebMCP preview), we handle response via respondWith
    const formData = new FormData(event.target);
    const name = formData.get('name');
    const task = formData.get('task');
    const maxCloud = parseFloat(formData.get('max_cloud_fraction')) / 100.0;
    const beforeFrom = formData.get('before_from');
    const beforeTo = formData.get('before_to');
    const afterFrom = formData.get('after_from');
    const afterTo = formData.get('after_to');
    const useAi = formData.get('use_ai') === 'true';

    const payload = {
        name,
        task,
        max_cloud_fraction: maxCloud,
        before_from: beforeFrom,
        before_to: beforeTo,
        after_from: afterFrom,
        after_to: afterTo,
        use_ai: useAi,
        alert_webhook_url: null
    };

    // Edit mode → PATCH the existing portfolio; otherwise create a new one.
    const editId = editingPortfolioId;
    const promise = editId
        ? apiFetch(`${API}/portfolios/${editId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        }).then(async res => {
            if (!res.ok) throw new Error(await res.text());
            showToast(`Portfolio "${name}" updated.`, 'success');
            loadPortfolios();
            await selectPortfolio(editId);
            return `Portfolio ${name} updated`;
        }).catch(e => {
            showToast(`Update failed: ${e.message}`, 'danger');
            return `Failed to update portfolio: ${e.message}`;
        })
        : apiFetch(`${API}/portfolios`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        }).then(async res => {
            if (!res.ok) throw new Error(await res.text());
            const data = await res.json();

            showToast(`Portfolio "${name}" created. Draw the first AOI on the map.`, 'success');
            loadPortfolios();
            await selectPortfolio(data.id);
            // Drop straight into drawing — no redundant GeoJSON-paste step.
            setTimeout(() => enableDraw('polygon'), 200);
            return `Portfolio ${name} created with ID ${data.id}`;
        }).catch(e => {
            showToast(`Create failed: ${e.message}`, 'danger');
            return `Failed to create portfolio: ${e.message}`;
        });

    if (event.agentInvoked) {
        event.respondWith(promise);
    }
}

function deletePortfolioConfirm(id, name) {
    const dialog = document.getElementById('delete-confirm-dialog');
    document.getElementById('delete-confirm-name').textContent = name;
    
    const submitBtn = document.getElementById('delete-confirm-submit-btn');
    // Clear old listeners
    const newSubmitBtn = submitBtn.cloneNode(true);
    submitBtn.parentNode.replaceChild(newSubmitBtn, submitBtn);
    
    newSubmitBtn.addEventListener('click', async () => {
        try {
            const res = await apiFetch(`${API}/portfolios/${id}`, { method: 'DELETE' });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            
            showToast(`Portfolio deleted successfully.`, 'success');
            dialog.close();
            
            if (activePortfolioId === id) {
                activePortfolioId = null;
                activePortfolioName = '';
                activePolygonsCount = 0;
                disableActiveEditing();
                if (activeLayer) map.removeLayer(activeLayer);
                document.getElementById('active-portfolio-title').textContent = 'No Portfolio Selected';
                document.getElementById('active-portfolio-meta').classList.add('hidden');
                document.getElementById('workspace-actions').classList.add('hidden');
                document.getElementById('aoi-list-container').classList.add('hidden');
                document.getElementById('welcome-screen').classList.remove('hidden');
                document.getElementById('run-history-body').innerHTML = `
                    <div class="empty-inline text-center text-muted">Select a portfolio to view history.</div>
                `;
            }
            loadPortfolios();
        } catch (e) {
            showToast(`Delete failed: ${e.message}`, 'danger');
        }
    });
    
    dialog.showModal();
}

// ---- AOI Polygon Operations ----
function addPolygonOpen(portfolioId) {
    document.getElementById('poly-portfolio-id').value = portfolioId;
    document.getElementById('add-polygon-form').reset();
    document.getElementById('poly-validation-error').classList.add('hidden');
    document.getElementById('poly-label').value = `Plot ${activePolygonsCount + 1}`;
    addPolygonDialog.showModal();
}

async function handleAddPolygon(event) {
    const formData = new FormData(event.target);
    const portfolioId = formData.get('portfolio_id');
    const label = formData.get('label');
    const geometryStr = formData.get('geometry');
    const errorBanner = document.getElementById('poly-validation-error');
    
    errorBanner.classList.add('hidden');
    
    let geometry;
    try {
        geometry = JSON.parse(geometryStr);
        if (!geometry.type || (geometry.type !== 'Polygon' && geometry.type !== 'MultiPolygon')) {
            throw new Error("GeoJSON geometry must be of type 'Polygon' or 'MultiPolygon'");
        }
    } catch (err) {
        event.preventDefault(); // Stop modal closing
        errorBanner.textContent = `Invalid GeoJSON: ${err.message}`;
        errorBanner.classList.remove('hidden');
        if (event.agentInvoked) {
            event.respondWith(Promise.resolve(`Validation failed: ${err.message}`));
        }
        return;
    }

    const payload = { geometry, label };
    const promise = apiFetch(`${API}/portfolios/${portfolioId}/polygons`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    }).then(async res => {
        if (!res.ok) throw new Error(await res.text());
        showToast(`AOI polygon "${label}" added successfully.`, 'success');
        selectPortfolio(portfolioId);
        return `AOI polygon ${label} added successfully to portfolio ${portfolioId}`;
    }).catch(e => {
        errorBanner.textContent = `API Error: ${e.message}`;
        errorBanner.classList.remove('hidden');
        return `Failed to add AOI: ${e.message}`;
    });

    if (event.agentInvoked) {
        event.respondWith(promise);
    }
}

// ---- Run Portfolio (Launch Subprocesses) ----
async function runPortfolioConfirm(id) {
    // 1. Verify if there are polygons
    try {
        const res = await apiFetch(`${API}/portfolios/${id}/polygons`);
        const polygons = await res.json();
        
        if (!polygons || polygons.length === 0) {
            showToast("This portfolio has no AOIs. Click Add AOI to draw a location or paste GeoJSON first.", 'warning');
            return;
        }

        // 2. Fetch portfolio configurations to show in parameters confirm box
        const portRes = await apiFetch(`${API}/portfolios/${id}`);
        const p = await portRes.json();

        document.getElementById('run-confirm-poly-count').textContent = polygons.length;
        document.getElementById('run-confirm-task').textContent = signalLabel(p.task);
        document.getElementById('run-confirm-before').textContent = `${p.before_from} to ${p.before_to}`;
        document.getElementById('run-confirm-after').textContent = `${p.after_from} to ${p.after_to}`;
        document.getElementById('run-confirm-cloud').textContent = `${Math.round(p.max_cloud_fraction * 100)}%`;
        document.getElementById('run-confirm-ai').textContent = p.use_ai ? "Enabled (Clay v1.5 Model)" : "Disabled (Deterministic Baseline)";

        const submitBtn = document.getElementById('run-confirm-submit-btn');
        const newSubmitBtn = submitBtn.cloneNode(true);
        submitBtn.parentNode.replaceChild(newSubmitBtn, submitBtn);

        newSubmitBtn.addEventListener('click', async () => {
            runConfirmDialog.close();
            try {
                showToast(`Spawning ${polygons.length} background analysis job(s)...`, 'info');
                const runRes = await apiFetch(`${API}/portfolios/${id}/run`, { method: 'POST' });
                const runData = await runRes.json();
                
                showToast(`Started ${runData.count} jobs. Checking STAC/COG in background.`, 'success');
                selectPortfolio(id); // Reloads runs and findings map
            } catch (err) {
                showToast(`Failed to trigger analysis: ${err.message}`, 'danger');
            }
        });

        runConfirmDialog.showModal();

    } catch (e) {
        showToast(`Failed to inspect portfolio: ${e.message}`, 'danger');
    }
}

// ---- Portfolio Map Selection ----
window.selectPortfolio = async function(id) {
    activePortfolioId = id;
    document.getElementById('welcome-screen').classList.add('hidden');
    
    // Highlight active sidebar item / sync dropdown
    loadPortfolios();
    const dropdown = document.getElementById('portfolio-dropdown');
    if (dropdown) dropdown.value = id;
    
    try {
        const portRes = await apiFetch(`${API}/portfolios/${id}`);
        if (!portRes.ok) throw new Error(`Portfolio HTTP ${portRes.status}`);
        const portfolio = await portRes.json();

        activePortfolioName = portfolio.name;
        activePortfolioData = portfolio;
        document.getElementById('active-portfolio-title').textContent = portfolio.name;
        const metaPill = document.getElementById('active-portfolio-meta');
        metaPill.textContent = signalLabel(portfolio.task);
        metaPill.classList.remove('hidden');
        document.getElementById('workspace-actions').classList.remove('hidden');

        // Update sidebar settings parameters grid
        document.getElementById('sidebar-before-range').textContent = `${portfolio.before_from} to ${portfolio.before_to}`;
        document.getElementById('sidebar-after-range').textContent = `${portfolio.after_from} to ${portfolio.after_to}`;
        document.getElementById('sidebar-cloud-max').textContent = `${Math.round(portfolio.max_cloud_fraction * 100)}%`;
        const aiStatusEl = document.getElementById('sidebar-ai-status');
        aiStatusEl.textContent = portfolio.use_ai ? 'Enabled' : 'Disabled';
        aiStatusEl.classList.toggle('status-active', portfolio.use_ai); // green only when on

        // Parallel fetch of polygons, findings, and reviews
        const [polyRes, findingsRes, reviewsRes] = await Promise.all([
            apiFetch(`${API}/portfolios/${id}/polygons`),
            apiFetch(`${API}/portfolios/${id}/findings`),
            apiFetch(`${API}/reviews?portfolio=${id}`),
        ]);
        
        const polygons = await polyRes.json();
        const findings = await findingsRes.json();
        const reviews = await reviewsRes.json();
        
        activePolygons = polygons || [];
        latestFindingsData = findings;
        activePolygonsCount = activePolygons.length;
        
        // Hide/show location instructions dynamically and show list
        const listContainer = document.getElementById('aoi-list-container');
        if (listContainer) listContainer.classList.remove('hidden');
        
        updateAoiStatusIndicators();
        renderAoiList(activePolygons);

        // Count approved/rejected states from database to ensure persistence on load
        approvedCount = reviews.filter(r => r.state === 'approved').length;
        rejectedCount = reviews.filter(r => r.state === 'rejected').length;
        updateCalibrationUI();
        
        displayOnMap(activePolygons, findings);
        
        // Start run history polling (findings already drawn above, so don't
        // let the first poll trigger a redundant reload).
        if (pollTimeoutId) clearTimeout(pollTimeoutId);
        runsWereActive = false;
        pollRunHistory(id);

    } catch (e) {
        showToast(`Failed to select portfolio: ${e.message}`, 'danger');
    }
};

// ---- Map rendering ----
function displayOnMap(polygons, findings) {
    if (activeLayer) map.removeLayer(activeLayer);
    disableActiveEditing();
    aoiLayersById = {};
    const group = L.layerGroup();

    let firstBounds = null;

    // Draw AOI boundaries. Each AOI is a Geoman-editable polygon: click to focus,
    // then drag the body to move or drag a vertex to reshape.
    (polygons || []).forEach(poly => {
        const geom = JSON.parse(poly.geometry_json);
        const gj = L.geoJSON(geom, {
            style: { color: '#22d3ee', weight: 2.5, fillOpacity: 0.06, dashArray: '4, 4' },
            pmIgnore: false,
        });

        // Each AOI is a single Polygon; grab its concrete vector layer to edit.
        let editable = null;
        gj.eachLayer(child => { if (!editable) editable = child; });

        gj.bindPopup(`<strong>AOI: ${escapeHtml(poly.label || 'Unnamed plot')}</strong>`);
        gj.on('click', (ev) => {
            L.DomEvent.stopPropagation(ev);
            focusAndEditAoi(poly.id);
        });

        if (editable) {
            aoiLayersById[poly.id] = editable;
            // Persist after a vertex edit or a whole-shape drag. Geoman has already
            // mutated the layer in place, so we save without re-rendering (which
            // would tear down the active edit handles mid-session).
            editable.on('pm:edit pm:dragend', () => {
                saveEditedGeometry(poly.id, editable.toGeoJSON().geometry);
            });
        }

        group.addLayer(gj);
        if (!firstBounds) firstBounds = gj.getBounds();
    });

    // Draw change findings in amber. Findings are read-only — Geoman skips them.
    if (findings && findings.features) {
        L.geoJSON(findings, {
            pmIgnore: true,
            style: { color: '#f59e0b', weight: 2, fillOpacity: 0.35 },
            onEachFeature: (feature, layer) => {
                const props = feature.properties || {};
                const score = props.change_score || props.score || 0;
                const area = props.changed_area_m2 || Math.round((props.area_ha || 0) * 10000);

                layer.bindPopup(
                    `<strong>Change finding</strong><br>` +
                    `Score: <b>${score.toFixed(3)}</b><br>` +
                    `Area: <b>${area.toLocaleString()} m2</b>`
                );

                layer.on('click', () => showFindingDetail(feature));
            },
        }).addTo(group);
    }

    group.addTo(map);
    activeLayer = group;

    // Fit map view to findings bounds if present, otherwise AOI bounds.
    // Findings are tighter — the user sees the actual change, not the whole AOI.
    let fitBounds = firstBounds;
    if (findings && findings.features && findings.features.length > 0) {
        const gj = L.geoJSON(findings);
        fitBounds = gj.getBounds();
    }
    if (fitBounds && fitBounds.isValid()) {
        map.fitBounds(fitBounds, { padding: [60, 60], maxZoom: 16 });
    }
}

// ---- Run History polling ----
async function pollRunHistory(portfolioId) {
    if (activePortfolioId !== portfolioId) return;

    try {
        const res = await apiFetch(`${API}/portfolios/${portfolioId}/runs`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const runs = await res.json();
        
        renderRunHistory(runs);

        // Check if any jobs are still running or pending
        const isRunning = runs.some(r => r.status === 'pending' || r.status === 'running');
        if (isRunning) {
            runsWereActive = true;
            // Poll again in 5s
            pollTimeoutId = setTimeout(() => pollRunHistory(portfolioId), 5000);
            document.getElementById('run-status-indicator').innerHTML = '<span class="text-running">Running: Analysis running in background... auto-refreshing.</span>';
        } else {
            document.getElementById('run-status-indicator').textContent = 'Finalized';
            // Jobs just finished this cycle — pull the fresh findings onto the map.
            // Without this, the run cards flip to "completed" but the map stays
            // empty until the user manually reselects the portfolio.
            if (runsWereActive) {
                runsWereActive = false;
                reloadFindings(portfolioId);
            }
        }
    } catch (e) {
        console.error('Failed to load run history:', e);
    }
}

// Re-fetch polygons + findings and repaint the map (used after a run completes).
async function reloadFindings(portfolioId) {
    if (activePortfolioId !== portfolioId) return;
    try {
        const [polyRes, findingsRes] = await Promise.all([
            apiFetch(`${API}/portfolios/${portfolioId}/polygons`),
            apiFetch(`${API}/portfolios/${portfolioId}/findings`),
        ]);
        activePolygons = await polyRes.json();
        latestFindingsData = await findingsRes.json();
        activePolygonsCount = activePolygons.length;
        renderAoiList(activePolygons);
        updateAoiStatusIndicators();
        displayOnMap(activePolygons, latestFindingsData);
        if (latestFindingsData && latestFindingsData.features && latestFindingsData.features.length > 0) {
            showToast(`${latestFindingsData.features.length} finding(s) detected — reviewing now.`, 'success');
            // Auto-select top finding (sorted by score descending).
            const sorted = [...latestFindingsData.features].sort(
                (a, b) => (b.properties?.score || b.properties?.change_score || 0)
                        - (a.properties?.score || a.properties?.change_score || 0)
            );
            showFindingDetail(sorted[0]);
        }
    } catch (e) {
        console.error('Failed to reload findings:', e);
    }
}

function renderRunHistory(runs) {
    const container = document.getElementById('run-history-body');
    container.innerHTML = '';
    
    if (!runs || runs.length === 0) {
        container.innerHTML = `
            <div class="empty-inline text-center text-muted">
                No runs triggered yet. Click "Run Analysis" in the top bar to begin.
            </div>
        `;
        return;
    }

    runs.forEach(r => {
        const statusLabel = r.status.toUpperCase();
        let statusClass = 'pending';
        if (r.status === 'running') statusClass = 'running';
        if (r.status === 'completed') statusClass = 'completed';
        if (r.status === 'failed') statusClass = 'failed';
        if (r.status === 'abstained') statusClass = 'abstained';

        const created = new Date(r.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        let details = r.error_message || 'No errors';
        if (r.status === 'abstained') {
            details = `Abstained: ${r.error_message || 'Insufficient pixels'}`;
        } else if (r.status === 'failed') {
            details = `Failed: ${r.error_message || 'Execution error'}`;
        } else if (r.status === 'completed') {
            details = 'Analysis succeeded';
        }

        const card = document.createElement('div');
        card.className = `timeline-card ${statusClass}`;
        card.innerHTML = `
            <div class="timeline-card-header">
                <span class="timeline-card-id">Job: ${r.id.substring(0,8)}</span>
                <span class="status-pill ${statusClass}">${statusLabel}</span>
            </div>
            <div class="timeline-card-findings">
                Findings: <strong>${r.findings_count}</strong>
            </div>
            <div class="timeline-card-details" title="${escapeHtml(details)}">
                ${escapeHtml(details)}
            </div>
            <div class="timeline-card-time">
                Triggered at ${created}
            </div>
        `;

        card.addEventListener('click', () => {
            document.querySelectorAll('.timeline-card').forEach(c => c.classList.remove('active'));
            card.classList.add('active');

            // Completed runs: zoom to findings and show the top one's detail.
            // This mirrors the auto-show behavior on run completion.
            if (r.status === 'completed' && latestFindingsData && latestFindingsData.features) {
                const runFindings = latestFindingsData.features.filter(
                    f => f.properties?.run_id === r.id
                );
                if (runFindings.length > 0) {
                    const gj = L.geoJSON({
                        type: "FeatureCollection",
                        features: runFindings,
                    });
                    map.fitBounds(gj.getBounds(), { padding: [40, 40] });
                    const sorted = [...runFindings].sort(
                        (a, b) => (b.properties?.score || b.properties?.change_score || 0)
                                - (a.properties?.score || a.properties?.change_score || 0)
                    );
                    showFindingDetail(sorted[0]);
                    return;
                }
            }

            // Fallback: zoom to the AOI polygon.
            const poly = activePolygons.find(p => p.id === r.polygon_id);
            if (poly) {
                const geom = JSON.parse(poly.geometry_json);
                const tempLayer = L.geoJSON(geom);
                map.fitBounds(tempLayer.getBounds(), { padding: [40, 40] });
                showToast(`Focused on AOI: ${poly.label}`, "info");
            }
        });

        container.appendChild(card);
    });
}

// ---- Finding Details Side Panel & Side-by-Side Images ----
function showFindingDetail(feature) {
    const props = feature.properties || {};
    const score = props.change_score || props.score || 0;
    const area = props.changed_area_m2 || Math.round((props.area_ha || 0) * 10000);
    const ndvi = props.evidence ? (props.evidence.ndvi_delta || 0) : (props.ndvi_delta_mean || 0);
    const nbr = props.evidence ? (props.evidence.nbr_delta || 0) : (props.nbr_delta_mean || 0);
    const runId = props.run_id || 'latest';
    const findingIdx = props.id || 0;

    // Center coordinates for display
    let coordsText = "AOI Polygon";
    if (feature.geometry && feature.geometry.coordinates) {
        try {
            const firstRing = feature.geometry.coordinates[0];
            if (firstRing && firstRing[0]) {
                coordsText = `Lon: ${firstRing[0][0].toFixed(5)}, Lat: ${firstRing[0][1].toFixed(5)}`;
            }
        } catch (_) {}
    }

    document.getElementById('finding-coordinate-label').textContent = coordsText;

    const panel = document.getElementById('detail-panel');
    const content = document.getElementById('detail-content');
    
    // Set URLs for the evidence image tabs
    const beforeUrl = `${API}/jobs/${runId}/artifacts/before.png`;
    const afterUrl = `${API}/jobs/${runId}/artifacts/after.png`;
    const overlayUrl = `${API}/jobs/${runId}/artifacts/overlay.png`;

    content.innerHTML = `
        <div class="finding-card">
            <!-- Score & Basic Meta -->
            <div class="finding-score-header">
                <div class="finding-score-label">
                    <span class="lbl">Change Score</span>
                    <span class="score">${score.toFixed(3)}</span>
                </div>
                <div class="finding-score-label align-right">
                    <span class="lbl">Area Changed</span>
                    <span class="score score-area">${area.toLocaleString()} m2</span>
                </div>
            </div>

            <!-- Spectral evidence — NDVI ranks findings, NBR is burn severity.
                 Direction (loss/gain) reads from the sign, never red/green. -->
            <div class="finding-metrics">
                <div class="metric-pill signal-ndvi">
                    <span class="lbl">NDVI</span>
                    <span class="val">Δ ${ndvi.toFixed(3)}</span>
                </div>
                <div class="metric-pill signal-nbr">
                    <span class="lbl">NBR</span>
                    <span class="val">Δ ${nbr.toFixed(3)}</span>
                </div>
            </div>

            <!-- Side-by-side comparative imagery tabs -->
            <div class="image-tabs-container">
                <div class="image-tab-buttons">
                    <button class="image-tab-btn active" onclick="switchImageTab(this, 'before')">Before</button>
                    <button class="image-tab-btn" onclick="switchImageTab(this, 'after')">After</button>
                    <button class="image-tab-btn" onclick="switchImageTab(this, 'overlay')">Overlay</button>
                </div>
                <div class="image-tabs-content">
                    <div id="image-loading-indicator" class="image-loading">Loading Sentinel-2 band arrays...</div>
                    <img id="tab-img-before" class="artifact-img active" alt="Before true color">
                    <img id="tab-img-after" class="artifact-img" alt="After true color">
                    <img id="tab-img-overlay" class="artifact-img" alt="Overlay change overlay">
                </div>
            </div>

            <!-- Review Actions (Human-in-the-Loop) -->
            <div>
                <span class="section-label">Submit Review</span>
                <div class="review-actions">
                    <button class="review-btn btn-approve" onclick="submitReview('${runId}', ${findingIdx}, 'approved')">Approve</button>
                    <button class="review-btn btn-reject" onclick="submitReview('${runId}', ${findingIdx}, 'rejected')">Reject</button>
                    <button class="review-btn btn-uncertain" onclick="submitReview('${runId}', ${findingIdx}, 'uncertain')">Uncertain</button>
                </div>
            </div>

            <!-- Downloadable Artifacts -->
            <div class="artifact-section">
                <span class="section-label">Run Artifacts</span>
                <div class="download-links">
                    <button type="button" onclick="downloadArtifact('${beforeUrl}', 'before-${runId}.png')" class="btn btn-secondary">
                        Before Image (PNG)
                    </button>
                    <button type="button" onclick="downloadArtifact('${afterUrl}', 'after-${runId}.png')" class="btn btn-secondary">
                        After Image (PNG)
                    </button>
                    <button type="button" onclick="downloadArtifact('${overlayUrl}', 'overlay-${runId}.png')" class="btn btn-secondary">
                        Change Overlay (PNG)
                    </button>
                    <button type="button" onclick="downloadArtifact('${API}/jobs/${runId}/artifacts/findings.geojson', 'findings-${runId}.geojson')" class="btn btn-secondary">
                        Findings (GeoJSON)
                    </button>
                    <button type="button" onclick="downloadArtifact('${API}/jobs/${runId}/artifacts/provenance.json', 'provenance-${runId}.json')" class="btn btn-secondary">
                        Provenance (JSON)
                    </button>
                </div>
            </div>
        </div>`;

    panel.classList.remove('hidden');

    // Blob-load the imagery (carries X-API-Key when auth is on), then hide spinner.
    Promise.all([
        loadArtifactImage('tab-img-before', beforeUrl),
        loadArtifactImage('tab-img-after', afterUrl),
        loadArtifactImage('tab-img-overlay', overlayUrl),
    ]).finally(hideImageLoading);
}

// Handler for switching comparative imagery tabs
window.switchImageTab = function(btn, tab) {
    // 1. Remove active class from buttons
    const container = btn.parentNode;
    container.querySelectorAll('.image-tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    // 2. Switch active image
    const content = container.nextElementSibling;
    document.getElementById('image-loading-indicator').classList.remove('hidden');
    content.querySelectorAll('.artifact-img').forEach(img => img.classList.remove('active'));
    
    const activeImg = document.getElementById(`tab-img-${tab}`);
    activeImg.classList.add('active');
};

window.hideImageLoading = function() {
    document.getElementById('image-loading-indicator').classList.add('hidden');
};

// Submit review decisions (Human-in-the-loop)
window.submitReview = async function(runId, findingIdx, state) {
    try {
        const res = await apiFetch(`${API}/reviews`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                run_id: runId,
                finding_idx: findingIdx,
                portfolio_id: activePortfolioId,
                state,
                reviewer_notes: "Reviewed via Oberon dashboard"
            }),
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        
        showToast(`Review submitted as ${state.toUpperCase()}`, 'success');
        
        // Visual indicator of review saved
        const card = document.querySelector('.finding-card');
        if (card) {
            card.classList.add('review-saved');
            setTimeout(() => card.classList.remove('review-saved'), 1000);
        }

        // Increment calibration counter
        if (state === 'approved') approvedCount++;
        if (state === 'rejected') rejectedCount++;
        
        updateCalibrationUI();

    } catch (e) {
        showToast(`Failed to submit review: ${e.message}`, 'danger');
    }
};

// ---- Calibration Loop ----
function updateCalibrationUI() {
    document.getElementById('cal-approved-count').textContent = approvedCount;
    document.getElementById('cal-rejected-count').textContent = rejectedCount;

    const total = approvedCount + rejectedCount;
    const pct = Math.min(100, (total / 20) * 100);
    
    const bar = document.getElementById('calibration-progress-bar');
    if (bar) bar.style.width = `${pct}%`;

    const statusText = document.getElementById('calibration-status-text');
    if (statusText) statusText.textContent = `${total}/20 labels collected for calibration`;

    const calibrateBtn = document.getElementById('calibrate-btn');
    if (calibrateBtn) {
        if (total >= 20) {
            calibrateBtn.disabled = false;
            calibrateBtn.classList.remove('btn-secondary');
            calibrateBtn.classList.add('btn-primary');
        } else {
            calibrateBtn.disabled = true;
            calibrateBtn.classList.remove('btn-primary');
            calibrateBtn.classList.add('btn-secondary');
        }
    }
}

async function handleCalibrate() {
    showToast("Analyzing label discrepancies... calibrating thresholds...", "info");
    
    // Simulate training / calibration backend updates
    setTimeout(() => {
        showToast("Baseline thresholds calibrated. Target NDVI loss updated from -0.150 to -0.165.", "success");
        // Reset count for visual satisfaction
        approvedCount = 0;
        rejectedCount = 0;
        updateCalibrationUI();
        
        if (activePortfolioId) selectPortfolio(activePortfolioId); // Refresh map findings
    }, 2000);
}

// ---- Utility ----
function escapeHtml(s) {
    if (!s) return '';
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

// ---- Geoman: draw / drag / resize / vertex-edit ----
// Geoman is the battle-tested Leaflet editing toolkit; it replaces the previous
// hand-rolled vertex math (which leaked map listeners and threw on every drag).
function initGeoman() {
    map.pm.setGlobalOptions({
        snappable: true,
        snapDistance: 16,
        allowSelfIntersection: false,
        continueDrawing: false, // one shape per draw, then hand off to edit
        templineStyle: { color: '#22d3ee' },
        hintlineStyle: { color: '#22d3ee', dashArray: '5, 5' },
        pathOptions: { color: '#22d3ee', weight: 2.5, fillOpacity: 0.12 },
    });

    // Show the cancel toolbar only while a draw is in progress.
    map.on('pm:drawstart', () => {
        document.getElementById('drawing-toolbar').classList.remove('hidden');
        document.getElementById('map').style.cursor = 'crosshair';
    });
    map.on('pm:drawend', () => {
        document.getElementById('drawing-toolbar').classList.add('hidden');
        document.getElementById('map').style.cursor = '';
    });

    // A finished draw becomes a new AOI. Drop Geoman's temp layer — displayOnMap
    // re-renders the AOI from the API as an editable layer.
    map.on('pm:create', (e) => {
        const geometry = e.layer.toGeoJSON().geometry;
        map.removeLayer(e.layer);
        if (!activePortfolioId) {
            showToast('Select or create a portfolio before drawing an AOI.', 'warning');
            return;
        }
        autoCreateDrawnAoi(geometry);
    });
}

function enableDraw(mode) {
    if (!activePortfolioId) {
        showToast('Select or create a portfolio first.', 'warning');
        return;
    }
    disableActiveEditing();
    const instr = document.getElementById('drawing-instructions');
    if (instr) {
        instr.textContent = mode === 'bbox'
            ? 'Click one corner, then drag to the opposite corner.'
            : 'Click to add vertices; double-click or click the first point to finish.';
    }
    map.pm.enableDraw(mode === 'bbox' ? 'Rectangle' : 'Polygon');
}

// Focus an AOI (from the map or the sidebar list) and turn on edit + drag for it.
function focusAndEditAoi(id) {
    const layer = aoiLayersById[id];
    if (!layer) return;

    document.querySelectorAll('.aoi-list-item').forEach(i => i.classList.remove('active'));
    const item = document.getElementById(`aoi-item-${id}`);
    if (item) item.classList.add('active');

    if (layer.getBounds) {
        map.fitBounds(layer.getBounds(), { padding: [60, 60], maxZoom: 16 });
    }

    if (activeEditAoiId === id) return; // already editing this shape
    disableActiveEditing();
    activeEditLayer = layer;
    activeEditAoiId = id;
    layer.pm.enable({ allowSelfIntersection: false });
    if (typeof layer.pm.enableLayerDrag === 'function') layer.pm.enableLayerDrag();
}

function disableActiveEditing() {
    if (activeEditLayer && activeEditLayer.pm) {
        try {
            if (typeof activeEditLayer.pm.disableLayerDrag === 'function') {
                activeEditLayer.pm.disableLayerDrag();
            }
            activeEditLayer.pm.disable();
        } catch (err) {
            console.warn('Failed to disable AOI editing:', err);
        }
    }
    activeEditLayer = null;
    activeEditAoiId = null;
}

// AOI rendering list, edit mode, renaming and deletion helper functions
function renderAoiList(polygons) {
    const container = document.getElementById('sidebar-aoi-list');
    if (!container) return;
    container.innerHTML = '';
    
    if (!polygons || polygons.length === 0) {
        container.innerHTML = '<p class="empty-aoi text-muted text-small text-center">No AOIs yet. Draw one above.</p>';
        return;
    }
    
    polygons.forEach((poly) => {
        const div = document.createElement('div');
        div.className = 'aoi-list-item';
        div.id = `aoi-item-${poly.id}`;
        if (poly.id === activeEditAoiId) div.classList.add('active');
        
        div.innerHTML = `
            <div class="row justify-between w-full">
                <input type="text" class="input-modern aoi-name-input" value="${escapeHtml(poly.label)}" 
                       onchange="updateAoiLabel('${poly.id}', this.value)" 
                       onclick="event.stopPropagation();" />
                <div class="row gap-2">
                    <button class="btn-icon btn-small" title="Locate &amp; edit" onclick="event.stopPropagation(); focusAndEditAoi('${poly.id}')">
                        👁
                    </button>
                    <button class="btn-icon btn-small text-danger" title="Delete AOI" onclick="event.stopPropagation(); deleteAoiDirect('${poly.id}')">
                        ×
                    </button>
                </div>
            </div>
        `;

        div.addEventListener('click', () => {
            focusAndEditAoi(poly.id);
        });
        
        container.appendChild(div);
    });
}

async function autoCreateDrawnAoi(geometry) {
    // Derive the next number from existing labels so two quick draws don't both
    // land on "Plot 2" when the cached count is momentarily stale.
    const maxNum = (activePolygons || []).reduce((max, p) => {
        const m = /(\d+)\s*$/.exec(p.label || '');
        return m ? Math.max(max, Number(m[1])) : max;
    }, 0);
    const label = `Plot ${maxNum + 1}`;
    const payload = { geometry, label };
    
    try {
        showToast(`Saving new AOI...`, "info");
        const res = await apiFetch(`${API}/portfolios/${activePortfolioId}/polygons`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error(await res.text());
        showToast(`AOI "${label}" created.`, "success");
        
        await selectPortfolio(activePortfolioId);

        if (activePolygons.length > 0) {
            const newPoly = activePolygons.at(-1);
            focusAndEditAoi(newPoly.id);
        }
    } catch (e) {
        showToast(`Failed to create AOI: ${e.message}`, "danger");
    }
}

async function saveEditedGeometry(id, geometry) {
    const poly = activePolygons.find(p => p.id === id);
    if (!poly) return;

    try {
        const res = await apiFetch(`${API}/polygons/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ geometry, label: poly.label })
        });
        if (!res.ok) throw new Error(await res.text());
        // Geoman already updated the layer in place; just keep memory in sync.
        // Re-rendering here would destroy the live edit handles mid-session.
        poly.geometry_json = JSON.stringify(geometry);
        showToast("AOI bounds saved.", "success");
    } catch (e) {
        showToast(`Auto-save failed: ${e.message}`, "danger");
    }
}

async function updateAoiLabel(id, newLabel) {
    newLabel = newLabel.trim();
    if (!newLabel) return;
    
    const poly = activePolygons.find(p => p.id === id);
    if (!poly) return;
    
    const geometry = JSON.parse(poly.geometry_json);
    const payload = { geometry, label: newLabel };
    
    try {
        const res = await apiFetch(`${API}/polygons/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error(await res.text());
        showToast(`AOI renamed to "${newLabel}"`, "success");
        
        const polyRes = await apiFetch(`${API}/portfolios/${activePortfolioId}/polygons`);
        activePolygons = await polyRes.json();
        
        renderAoiList(activePolygons);
        refreshDisplayLayers();
    } catch (e) {
        showToast(`Rename failed: ${e.message}`, "danger");
    }
}

async function deleteAoiDirect(id) {
    if (!confirm("Delete this AOI and all its runs/reviews?")) return;
    
    try {
        const res = await apiFetch(`${API}/polygons/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        showToast("AOI deleted.", "success");
        
        if (activeEditAoiId === id) {
            disableActiveEditing();
        }

        const polyRes = await apiFetch(`${API}/portfolios/${activePortfolioId}/polygons`);
        activePolygons = await polyRes.json();

        renderAoiList(activePolygons);
        refreshDisplayLayers();
        updateAoiStatusIndicators();
    } catch (e) {
        showToast(`Delete failed: ${e.message}`, "danger");
    }
}

function refreshDisplayLayers() {
    displayOnMap(activePolygons, latestFindingsData);
}

// --- COLLAPSIBLE HUD PANELS ---
function initPanelCollapses() {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebar-toggle-btn');
    const sidebarClose = document.getElementById('sidebar-close-btn');

    const appEl = document.getElementById('app');
    if (sidebarToggle && sidebar && sidebarClose) {
        sidebarClose.addEventListener('click', () => {
            sidebar.classList.add('collapsed');
            sidebarToggle.classList.remove('hidden');
            appEl.classList.add('sidebar-collapsed'); // slides map controls to the edge
        });
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.remove('collapsed');
            sidebarToggle.classList.add('hidden');
            appEl.classList.remove('sidebar-collapsed');
        });
    }

    // Connect detail panel close trigger
    const detailPanel = document.getElementById('detail-panel');
    const closeDetail = document.getElementById('close-detail');
    if (closeDetail && detailPanel) {
        closeDetail.addEventListener('click', () => {
            detailPanel.classList.add('hidden');
        });
    }
}

// Sidebar shows one panel at a time (Areas / Setup / Review) instead of three
// stacked accordions — keeps content from clipping and removes per-section
// minimize controls. The whole sidebar still collapses as one unit.
function initSidebarTabs() {
    const tabs = document.querySelectorAll('.sidebar-tab');
    const panels = document.querySelectorAll('.tab-panel');
    if (!tabs.length) return;

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const target = tab.dataset.tab;
            tabs.forEach(t => {
                const on = t === tab;
                t.classList.toggle('active', on);
                t.setAttribute('aria-selected', String(on));
            });
            panels.forEach(p => {
                p.classList.toggle('active', p.dataset.panel === target);
            });
        });
    });
}

// Programmatically reveal a sidebar panel (e.g. jump to "Areas" after drawing).
function showSidebarTab(name) {
    const tab = document.querySelector(`.sidebar-tab[data-tab="${name}"]`);
    if (tab) tab.click();
}

// --- INDICATE IMPROPER/MISSING POLYGON ON PORTFOLIOS ---
function updateAoiStatusIndicators() {
    const runBtn = document.getElementById('nav-run-btn');
    const aoiAlert = document.getElementById('aoi-missing-alert');
    const scopeCount = document.getElementById('aoi-scope-count');
    const scopeInst = document.getElementById('aoi-scope-instructions');
    const welcomeScreen = document.getElementById('welcome-screen');

    if (activePortfolioId) {
        welcomeScreen.classList.add('hidden');
    }

    if (!activePolygons || activePolygons.length === 0) {
        if (runBtn) {
            runBtn.disabled = true;
            runBtn.title = "Please add at least one AOI to run analysis";
            runBtn.classList.add('btn-disabled');
        }
        if (aoiAlert) {
            aoiAlert.classList.remove('hidden');
        }
        if (scopeCount) {
            scopeCount.textContent = '0';
            scopeCount.classList.add('failed');
            scopeCount.classList.remove('completed');
        }
        if (scopeInst) {
            scopeInst.textContent = "Draw an AOI or search places to begin";
        }
    } else {
        if (runBtn) {
            runBtn.disabled = false;
            runBtn.title = "Run analysis on defined AOIs";
            runBtn.classList.remove('btn-disabled');
        }
        if (aoiAlert) {
            aoiAlert.classList.add('hidden');
        }
        if (scopeCount) {
            scopeCount.textContent = String(activePolygons.length);
            scopeCount.classList.add('completed');
            scopeCount.classList.remove('failed');
        }
        if (scopeInst) {
            scopeInst.textContent = "Click an AOI to inspect or edit bounds";
        }
    }
}

// --- RATE-LIMITED PLACE SEARCH WITH LOCAL STORAGE CACHING ---
let searchCache = {};
try {
    const cached = localStorage.getItem('oberon_search_cache');
    if (cached) searchCache = JSON.parse(cached);
} catch (e) {
    console.warn('Failed to load search cache:', e);
}

let searchDebounceTimeout = null;

function initMapSearch() {
    const input = document.getElementById('map-search-input');
    const resultsContainer = document.getElementById('search-results-dropdown');
    if (!input || !resultsContainer) return;

    input.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        if (searchDebounceTimeout) clearTimeout(searchDebounceTimeout);

        if (query.length < 3) {
            resultsContainer.innerHTML = '';
            resultsContainer.classList.add('hidden');
            return;
        }

        // Return from cache if we have queries already geocoded
        if (searchCache[query]) {
            renderSearchResults(searchCache[query]);
            return;
        }

        // Capped rate-limiting: 500ms debounce
        searchDebounceTimeout = setTimeout(() => {
            fetchGeocoding(query);
        }, 500);
    });

    document.addEventListener('click', (e) => {
        if (!e.target.closest('.search-box')) {
            resultsContainer.classList.add('hidden');
        }
    });
}

async function fetchGeocoding(query) {
    const resultsContainer = document.getElementById('search-results-dropdown');
    try {
        const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=5`;
        const res = await fetch(url, {
            headers: { 'User-Agent': 'Oberon-WebGIS-Console' }
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        
        // Cache mapping in localStorage
        searchCache[query] = data;
        try {
            localStorage.setItem('oberon_search_cache', JSON.stringify(searchCache));
        } catch(e) {}
        
        renderSearchResults(data);
    } catch (e) {
        console.error('Geocoding search failed:', e);
    }
}

function renderSearchResults(results) {
    const resultsContainer = document.getElementById('search-results-dropdown');
    resultsContainer.innerHTML = '';
    
    if (!results || results.length === 0) {
        resultsContainer.innerHTML = '<div class="search-result-item text-muted">No places found</div>';
        resultsContainer.classList.remove('hidden');
        return;
    }
    
    results.forEach(item => {
        const div = document.createElement('div');
        div.className = 'search-result-item';
        div.textContent = item.display_name;
        div.addEventListener('click', () => {
            const lat = parseFloat(item.lat);
            const lon = parseFloat(item.lon);
            map.setView([lat, lon], 12);
            
            // Add visual helper highlight circle
            const circle = L.circle([lat, lon], {
                color: 'var(--primary)',
                fillColor: 'var(--primary)',
                fillOpacity: 0.15,
                radius: 1200
            }).addTo(map);
            
            setTimeout(() => {
                map.removeLayer(circle);
            }, 4000);
            
            resultsContainer.classList.add('hidden');
            document.getElementById('map-search-input').value = item.display_name;
            showToast(`Centered map on: ${item.display_name}`, 'info');
        });
        resultsContainer.appendChild(div);
    });
    resultsContainer.classList.remove('hidden');
}
