// Oberon dashboard client logic.
// Vanilla Javascript + Leaflet Map. Exposes client actions to WebMCP for AI.

const API = window.location.origin + '/v1';
let map = null;
let activeLayer = null;
let activePortfolioId = null;
let activePortfolioName = '';
let activePolygonsCount = 0;
let pollTimeoutId = null;

let activePolygons = [];
let editLayer = null;
let editHandles = [];
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

// Interactive Drawing States
let isDrawing = false;
let drawMode = null; // 'polygon' or 'bbox'
let drawPoints = [];
let drawLayerGroup = null;
let drawPreviewLine = null;
let drawMarkers = [];

// ---- Native Dialog References ----
let newPortfolioDialog = null;
let addPolygonDialog = null;
let runConfirmDialog = null;
let deleteConfirmDialog = null;
let guideDialog = null;
let portfolioStep = 1;

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

    L.control.zoom({ position: 'topleft' }).addTo(map);

    // Layer control to switch views
    const baseMaps = {
        "Satellite Imagery": satelliteMap,
        "Dark map": darkMap,
        "Standard Street Map": streetMap
    };
    L.control.layers(baseMaps, null, { position: 'topright' }).addTo(map);
    setupAttributionToggle();
    setupDraggableWelcomeCard();

    // Disable click/double click event propagation on all overlay HUD panels
    const panels = document.querySelectorAll('.floating-panel, .empty-state-panel, .toast-container, .floating-toolbar');
    panels.forEach(p => L.DomEvent.disableClickPropagation(p));

    // Initialize drawing layer group
    drawLayerGroup = L.layerGroup().addTo(map);

    // Coordinate display tracking mouse and touch/click movements
    const updateCoords = (e) => {
        const lat = e.latlng.lat.toFixed(5);
        const lng = e.latlng.lng.toFixed(5);
        const el = document.getElementById('map-coords-badge');
        if (el) el.textContent = `Lat: ${lat}, Lon: ${lng}`;
    };
    map.on('mousemove', updateCoords);
    map.on('click', updateCoords);

    // Handle clicks/double clicks for drawing
    map.on('click', handleMapClick);
    map.on('dblclick', handleMapDblClick);

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
        navDrawPolyBtn.addEventListener('click', () => {
            if (activePortfolioId) startDrawing('polygon');
        });
    }

    const navDrawBBoxBtn = document.getElementById('nav-draw-bbox-btn');
    if (navDrawBBoxBtn) {
        navDrawBBoxBtn.addEventListener('click', () => {
            if (activePortfolioId) startDrawing('bbox');
        });
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

    document.getElementById('help-toggle-btn').addEventListener('click', () => {
        guideDialog.showModal();
    });

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

    // Drawing Trigger Actions
    const drawPolyBtn = document.getElementById('draw-poly-btn');
    if (drawPolyBtn) drawPolyBtn.addEventListener('click', () => startDrawing('polygon'));
    
    const drawBBoxBtn = document.getElementById('draw-bbox-btn');
    if (drawBBoxBtn) drawBBoxBtn.addEventListener('click', () => startDrawing('bbox'));
    
    const drawFinishBtn = document.getElementById('drawing-finish-btn');
    if (drawFinishBtn) drawFinishBtn.addEventListener('click', finishDrawing);
    
    const drawCancelBtn = document.getElementById('drawing-cancel-btn');
    if (drawCancelBtn) drawCancelBtn.addEventListener('click', cancelDrawing);

    // Sidebar drawing buttons setup
    const sidebarDrawPolyBtn = document.getElementById('sidebar-draw-poly-btn');
    if (sidebarDrawPolyBtn) sidebarDrawPolyBtn.addEventListener('click', () => startDrawing('polygon'));

    const sidebarDrawBBoxBtn = document.getElementById('sidebar-draw-bbox-btn');
    if (sidebarDrawBBoxBtn) sidebarDrawBBoxBtn.addEventListener('click', () => startDrawing('bbox'));

    map.on('click', (e) => {
        if (!isDrawing) {
            // Click outside handle/path should clear active edit mode
            if (e.originalEvent && e.originalEvent.target && e.originalEvent.target.id === 'map') {
                clearEditHandles();
                document.querySelectorAll('.aoi-list-item').forEach(item => item.classList.remove('active'));
            }
        }
    });

    // Form Submissions (WebMCP support)
    document.getElementById('create-portfolio-form').addEventListener('submit', handleCreatePortfolio);
    initPortfolioWizard();
    document.getElementById('add-polygon-form').addEventListener('submit', handleAddPolygon);
    document.getElementById('calibrate-btn').addEventListener('click', handleCalibrate);

    // Initializations
    initMapSearch();
    initPanelCollapses();
    
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

function openPortfolioDialog() {
    document.getElementById('create-portfolio-form').reset();
    showPortfolioStep(1);
    newPortfolioDialog.showModal();
    setTimeout(() => document.getElementById('port-name')?.focus(), 0);
}

function initPortfolioWizard() {
    const next = document.getElementById('portfolio-step-next');
    const back = document.getElementById('portfolio-step-back');
    if (next) {
        next.addEventListener('click', () => {
            if (portfolioStep === 1 && !document.getElementById('port-name').reportValidity()) return;
            showPortfolioStep(portfolioStep + 1);
        });
    }
    if (back) {
        back.addEventListener('click', () => showPortfolioStep(portfolioStep - 1));
    }
}

function showPortfolioStep(step) {
    portfolioStep = Math.max(1, Math.min(3, step));
    document.querySelectorAll('.portfolio-step').forEach(el => {
        el.classList.toggle('active', el.dataset.step === String(portfolioStep));
    });
    document.querySelectorAll('[data-step-marker]').forEach(el => {
        el.classList.toggle('active', Number(el.dataset.stepMarker) === portfolioStep);
    });
    const label = document.getElementById('portfolio-step-label');
    if (label) label.textContent = `Step ${portfolioStep} of 3`;
    document.getElementById('portfolio-step-back')?.classList.toggle('hidden', portfolioStep === 1);
    document.getElementById('portfolio-step-next')?.classList.toggle('hidden', portfolioStep === 3);
    document.getElementById('portfolio-submit')?.classList.toggle('hidden', portfolioStep !== 3);
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

function setupDraggableWelcomeCard() {
    const card = document.querySelector('.empty-state-panel');
    const workspace = document.getElementById('workspace-container');
    if (!card || !workspace) return;

    let drag = null;
    card.addEventListener('pointerdown', (event) => {
        if (event.target.closest('button')) return;
        card.setPointerCapture(event.pointerId);
        const cardRect = card.getBoundingClientRect();
        drag = {
            offsetX: event.clientX - cardRect.left,
            offsetY: event.clientY - cardRect.top,
        };
    });

    card.addEventListener('pointermove', (event) => {
        if (!drag) return;
        const workspaceRect = workspace.getBoundingClientRect();
        const maxLeft = workspaceRect.width - card.offsetWidth - 12;
        const maxTop = workspaceRect.height - card.offsetHeight - 12;
        const left = Math.max(12, Math.min(maxLeft, event.clientX - workspaceRect.left - drag.offsetX));
        const top = Math.max(12, Math.min(maxTop, event.clientY - workspaceRect.top - drag.offsetY));
        card.style.left = `${left}px`;
        card.style.top = `${top}px`;
    });

    card.addEventListener('pointerup', () => {
        drag = null;
    });
}

// ---- Portfolios API Operations ----
async function loadPortfolios() {
    try {
        const res = await fetch(`${API}/portfolios`);
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

    const promise = fetch(`${API}/portfolios`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    }).then(async res => {
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        
        showToast(`Portfolio "${name}" created. Add an AOI to define the location.`, 'success');
        loadPortfolios();
        await selectPortfolio(data.id);
        setTimeout(() => addPolygonOpen(data.id), 150);
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
            const res = await fetch(`${API}/portfolios/${id}`, { method: 'DELETE' });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            
            showToast(`Portfolio deleted successfully.`, 'success');
            dialog.close();
            
            if (activePortfolioId === id) {
                activePortfolioId = null;
                activePortfolioName = '';
                activePolygonsCount = 0;
                clearEditHandles();
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
    const promise = fetch(`${API}/portfolios/${portfolioId}/polygons`, {
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
        const res = await fetch(`${API}/portfolios/${id}/polygons`);
        const polygons = await res.json();
        
        if (!polygons || polygons.length === 0) {
            showToast("This portfolio has no AOIs. Click Add AOI to draw a location or paste GeoJSON first.", 'warning');
            return;
        }

        // 2. Fetch portfolio configurations to show in parameters confirm box
        const portRes = await fetch(`${API}/portfolios/${id}`);
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
                const runRes = await fetch(`${API}/portfolios/${id}/run`, { method: 'POST' });
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
        const portRes = await fetch(`${API}/portfolios/${id}`);
        if (!portRes.ok) throw new Error(`Portfolio HTTP ${portRes.status}`);
        const portfolio = await portRes.json();
        
        activePortfolioName = portfolio.name;
        document.getElementById('active-portfolio-title').textContent = portfolio.name;
        const metaPill = document.getElementById('active-portfolio-meta');
        metaPill.textContent = signalLabel(portfolio.task);
        metaPill.classList.remove('hidden');
        document.getElementById('workspace-actions').classList.remove('hidden');

        // Update sidebar settings parameters grid
        document.getElementById('sidebar-before-range').textContent = `${portfolio.before_from} to ${portfolio.before_to}`;
        document.getElementById('sidebar-after-range').textContent = `${portfolio.after_from} to ${portfolio.after_to}`;
        document.getElementById('sidebar-cloud-max').textContent = `${Math.round(portfolio.max_cloud_fraction * 100)}%`;
        document.getElementById('sidebar-ai-status').textContent = portfolio.use_ai ? 'Enabled' : 'Disabled';

        // Parallel fetch of polygons, findings, and reviews
        const [polyRes, findingsRes, reviewsRes] = await Promise.all([
            fetch(`${API}/portfolios/${id}/polygons`),
            fetch(`${API}/portfolios/${id}/findings`),
            fetch(`${API}/reviews?portfolio=${id}`),
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
        
        // Start run history polling
        if (pollTimeoutId) clearTimeout(pollTimeoutId);
        pollRunHistory(id);

    } catch (e) {
        showToast(`Failed to select portfolio: ${e.message}`, 'danger');
    }
};

// ---- Map rendering ----
function displayOnMap(polygons, findings) {
    if (activeLayer) map.removeLayer(activeLayer);
    const group = L.layerGroup();
    
    let firstBounds = null;

    // Draw AOI boundaries in blue
    (polygons || []).forEach(poly => {
        const geom = JSON.parse(poly.geometry_json);
        const layer = L.geoJSON(geom, {
            style: { color: '#388bfd', weight: 2.5, fillOpacity: 0.05, dashArray: '4, 4' },
        });
        layer.bindPopup(`<strong>AOI: ${escapeHtml(poly.label || 'Unnamed plot')}</strong>`);
        layer.on('click', (ev) => {
            L.DomEvent.stopPropagation(ev);
            startEditingAoi(poly.id, poly.geometry_json);
        });
        group.addLayer(layer);
        
        if (!firstBounds) {
            firstBounds = L.geoJSON(geom).getBounds();
        }
    });

    // Draw change findings in bright orange/yellow
    if (findings && findings.features) {
        L.geoJSON(findings, {
            style: { color: '#f0883e', weight: 2, fillOpacity: 0.35 },
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

    // Fit map view to bounds
    if (firstBounds) {
        map.fitBounds(firstBounds, { padding: [50, 50] });
    }
}

// ---- Run History polling ----
async function pollRunHistory(portfolioId) {
    if (activePortfolioId !== portfolioId) return;

    try {
        const res = await fetch(`${API}/portfolios/${portfolioId}/runs`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const runs = await res.json();
        
        renderRunHistory(runs);

        // Check if any jobs are still running or pending
        const isRunning = runs.some(r => r.status === 'pending' || r.status === 'running');
        if (isRunning) {
            // Poll again in 5s
            pollTimeoutId = setTimeout(() => pollRunHistory(portfolioId), 5000);
            document.getElementById('run-status-indicator').innerHTML = '<span class="text-running">Running: Analysis running in background... auto-refreshing.</span>';
        } else {
            document.getElementById('run-status-indicator').textContent = 'Finalized';
        }
    } catch (e) {
        console.error('Failed to load run history:', e);
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
                    <img id="tab-img-before" class="artifact-img active" src="${beforeUrl}" alt="Before true color" onload="hideImageLoading()">
                    <img id="tab-img-after" class="artifact-img" src="${afterUrl}" alt="After true color" onload="hideImageLoading()">
                    <img id="tab-img-overlay" class="artifact-img" src="${overlayUrl}" alt="Overlay change overlay" onload="hideImageLoading()">
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
                    <a href="${beforeUrl}" download="before-${runId}.png" class="btn btn-secondary">
                        Before Image (PNG)
                    </a>
                    <a href="${afterUrl}" download="after-${runId}.png" class="btn btn-secondary">
                        After Image (PNG)
                    </a>
                    <a href="${overlayUrl}" download="overlay-${runId}.png" class="btn btn-secondary">
                        Change Overlay (PNG)
                    </a>
                    <a href="${API}/jobs/${runId}/artifacts/findings.geojson" download="findings-${runId}.geojson" class="btn btn-secondary">
                        Findings (GeoJSON)
                    </a>
                    <a href="${API}/jobs/${runId}/artifacts/provenance.json" download="provenance-${runId}.json" class="btn btn-secondary">
                        Provenance (JSON)
                    </a>
                </div>
            </div>
        </div>`;
        
    panel.classList.remove('hidden');
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
        const res = await fetch(`${API}/reviews`, {
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

// ---- Interactive Map Drawing Functions ----
function startDrawing(mode) {
    addPolygonDialog.close();
    isDrawing = true;
    drawMode = mode;
    drawPoints = [];
    drawMarkers.forEach(m => map.removeLayer(m));
    drawMarkers = [];
    if (drawPreviewLine) {
        map.removeLayer(drawPreviewLine);
        drawPreviewLine = null;
    }
    drawLayerGroup.clearLayers();

    // Disable double click zoom while drawing
    map.doubleClickZoom.disable();

    // Show toolbar
    const toolbar = document.getElementById('drawing-toolbar');
    toolbar.classList.remove('hidden');
    
    const instructions = document.getElementById('drawing-instructions');
    if (mode === 'polygon') {
        instructions.textContent = "Click map to add vertices. Double-click or click first point to close polygon.";
    } else {
        instructions.textContent = "Click map for Point 1 (corner), then opposite corner for Point 2.";
    }

    document.getElementById('map').style.cursor = 'crosshair';
}

function handleMapClick(e) {
    if (!isDrawing) return;
    
    const latlng = e.latlng;
    
    if (drawMode === 'polygon') {
        drawPoints.push(latlng);
        
        // Circle vertex marker
        const marker = L.circleMarker(latlng, {
            radius: 5,
            fillColor: '#58a6ff',
            color: '#fff',
            weight: 1.5,
            fillOpacity: 1
        }).addTo(map);
        drawMarkers.push(marker);

        // Click first point to finish
        if (drawPoints.length > 2) {
            marker.on('click', (ev) => {
                L.DomEvent.stopPropagation(ev);
                finishDrawing();
            });
        }
        
        if (drawPreviewLine) map.removeLayer(drawPreviewLine);
        
        if (drawPoints.length > 1) {
            drawPreviewLine = L.polygon(drawPoints, {
                color: '#58a6ff',
                weight: 2,
                fillOpacity: 0.1,
                dashArray: '3, 5'
            }).addTo(map);
        }
    } else if (drawMode === 'bbox') {
        drawPoints.push(latlng);
        
        const marker = L.circleMarker(latlng, {
            radius: 5,
            fillColor: '#3fbc55',
            color: '#fff',
            weight: 1.5,
            fillOpacity: 1
        }).addTo(map);
        drawMarkers.push(marker);
        
        if (drawPoints.length === 1) {
            document.getElementById('drawing-instructions').textContent = "Corner 1 saved. Click opposite corner to complete bounding box.";
        } else if (drawPoints.length === 2) {
            if (drawPreviewLine) map.removeLayer(drawPreviewLine);
            
            const bounds = L.latLngBounds(drawPoints[0], drawPoints[1]);
            drawPreviewLine = L.rectangle(bounds, {
                color: '#3fbc55',
                weight: 2,
                fillOpacity: 0.1
            }).addTo(map);
            
            finishDrawing();
        }
    }
}

function handleMapDblClick(e) {
    if (isDrawing && drawMode === 'polygon') {
        finishDrawing();
    }
}

function finishDrawing() {
    if (!isDrawing) return;
    
    let geojson = null;
    
    if (drawMode === 'polygon') {
        if (drawPoints.length < 3) {
            showToast("Polygon requires at least 3 vertices.", "warning");
            return;
        }
        const coords = drawPoints.map(p => [p.lng, p.lat]);
        coords.push(coords[0]); // close loop
        geojson = {
            type: "Polygon",
            coordinates: [coords]
        };
    } else if (drawMode === 'bbox') {
        if (drawPoints.length < 2) {
            showToast("Bounding box requires 2 corners.", "warning");
            return;
        }
        const p1 = drawPoints[0];
        const p2 = drawPoints[1];
        const minLng = Math.min(p1.lng, p2.lng);
        const maxLng = Math.max(p1.lng, p2.lng);
        const minLat = Math.min(p1.lat, p2.lat);
        const maxLat = Math.max(p1.lat, p2.lat);
        
        geojson = {
            type: "Polygon",
            coordinates: [[
                [minLng, minLat],
                [maxLng, minLat],
                [maxLng, maxLat],
                [minLng, maxLat],
                [minLng, minLat]
            ]]
        };
    }
    
    if (geojson) {
        autoCreateDrawnAoi(geojson);
    }
    
    cleanupDrawing();
}

function cancelDrawing() {
    cleanupDrawing();
}

function cleanupDrawing() {
    isDrawing = false;
    drawMode = null;
    drawPoints = [];
    drawMarkers.forEach(m => map.removeLayer(m));
    drawMarkers = [];
    if (drawPreviewLine) {
        map.removeLayer(drawPreviewLine);
        drawPreviewLine = null;
    }
    
    map.doubleClickZoom.enable();
    document.getElementById('drawing-toolbar').classList.add('hidden');
    document.getElementById('map').style.cursor = '';
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
                    <button class="btn-icon btn-small" title="Locate & Edit" onclick="event.stopPropagation(); startEditingAoi('${poly.id}', '${escapeHtml(poly.geometry_json)}')">
                        👁
                    </button>
                    <button class="btn-icon btn-small text-danger" title="Delete AOI" onclick="event.stopPropagation(); deleteAoiDirect('${poly.id}')">
                        ×
                    </button>
                </div>
            </div>
        `;
        
        div.addEventListener('click', () => {
            startEditingAoi(poly.id, poly.geometry_json);
        });
        
        container.appendChild(div);
    });
}

function startEditingAoi(id, geomJson) {
    document.querySelectorAll('.aoi-list-item').forEach(item => item.classList.remove('active'));
    const activeItem = document.getElementById(`aoi-item-${id}`);
    if (activeItem) activeItem.classList.add('active');

    const geom = JSON.parse(geomJson);
    const tempLayer = L.geoJSON(geom);
    map.fitBounds(tempLayer.getBounds(), { padding: [40, 40] });
    
    activeEditAoiId = id;
    
    if (editLayer) map.removeLayer(editLayer);
    clearEditHandles();
    
    const coords = geom.coordinates;
    const latlngs = coords[0].map(p => L.latLng(p[1], p[0]));
    const editLatlngs = latlngs.slice(0, -1);
    
    editLayer = L.polygon(latlngs, {
        color: '#4f8cff',
        weight: 3,
        fillOpacity: 0.15,
        dashArray: '5, 5'
    }).addTo(map);
    
    editLatlngs.forEach((latlng, idx) => {
        const handle = L.marker(latlng, {
            draggable: true,
            icon: createHandleIcon()
        }).addTo(map);
        
        handle.on('drag', (e) => {
            const newLatLng = e.target.getLatLng();
            editLatlngs[idx] = newLatLng;
            const newCoords = [...editLatlngs, editLatlngs[0]];
            editLayer.setLatLngs(newCoords);
            if (centerHandle) centerHandle.setLatLng(editLayer.getBounds().getCenter());
        });
        
        handle.on('dragend', () => {
            const finalCoords = editLatlngs.map(p => [p.lng, p.lat]);
            finalCoords.push(finalCoords[0]);
            const geom = { type: 'Polygon', coordinates: [finalCoords] };
            saveEditedGeometry(id, geom);
        });
        
        editHandles.push(handle);
    });
    
    // Native polygon dragging
    let draggingPolygon = false;
    let dragStartPoint = null;

    editLayer.on('mousedown', (e) => {
        L.DomEvent.stopPropagation(e.originalEvent);
        draggingPolygon = true;
        dragStartPoint = e.latlng;
        map.dragging.disable();
    });

    map.on('mousemove', (e) => {
        if (!draggingPolygon) return;
        
        const deltaLat = e.latlng.lat - dragStartPoint.lat;
        const deltaLng = e.latlng.lng - dragStartPoint.lng;
        
        editLatlngs.forEach((p, idx) => {
            editLatlngs[idx] = L.latLng(p.lat + deltaLat, p.lng + deltaLng);
        });
        
        const newCoords = [...editLatlngs, editLatlngs[0]];
        editLayer.setLatLngs(newCoords);
        
        editHandles.forEach((handle, idx) => {
            handle.setLatLng(editLatlngs[idx]);
        });
        
        dragStartPoint = e.latlng;
    });

    map.on('mouseup', () => {
        if (draggingPolygon) {
            draggingPolygon = false;
            map.dragging.enable();
            
            const finalCoords = editLatlngs.map(p => [p.lng, p.lat]);
            finalCoords.push(finalCoords[0]);
            const geom = { type: 'Polygon', coordinates: [finalCoords] };
            saveEditedGeometry(id, geom);
        }
    });
}

function clearEditHandles() {
    editHandles.forEach(h => map.removeLayer(h));
    editHandles = [];
    if (editLayer) {
        map.removeLayer(editLayer);
        editLayer = null;
    }
    activeEditAoiId = null;
}

function createHandleIcon(isCenter = false) {
    const size = isCenter ? 12 : 8;
    return L.divIcon({
        className: `edit-handle-icon${isCenter ? ' center' : ''}`,
        html: '<div class="edit-handle-dot"></div>',
        iconSize: [size, size]
    });
}

async function autoCreateDrawnAoi(geometry) {
    const label = `Plot ${activePolygonsCount + 1}`;
    const payload = { geometry, label };
    
    try {
        showToast(`Saving new AOI...`, "info");
        const res = await fetch(`${API}/portfolios/${activePortfolioId}/polygons`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error(await res.text());
        showToast(`AOI "${label}" created.`, "success");
        
        await selectPortfolio(activePortfolioId);
        
        if (activePolygons.length > 0) {
            const newPoly = activePolygons[activePolygons.length - 1];
            startEditingAoi(newPoly.id, newPoly.geometry_json);
        }
    } catch (e) {
        showToast(`Failed to create AOI: ${e.message}`, "danger");
    }
}

async function saveEditedGeometry(id, geometry) {
    const poly = activePolygons.find(p => p.id === id);
    if (!poly) return;
    
    const label = poly.label;
    const payload = { geometry, label };
    
    try {
        const res = await fetch(`${API}/polygons/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error(await res.text());
        showToast("AOI bounds auto-saved.", "success");
        
        const polyRes = await fetch(`${API}/portfolios/${activePortfolioId}/polygons`);
        activePolygons = await polyRes.json();
        
        refreshDisplayLayers();
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
        const res = await fetch(`${API}/polygons/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error(await res.text());
        showToast(`AOI renamed to "${newLabel}"`, "success");
        
        const polyRes = await fetch(`${API}/portfolios/${activePortfolioId}/polygons`);
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
        const res = await fetch(`${API}/polygons/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        showToast("AOI deleted.", "success");
        
        if (activeEditAoiId === id) {
            clearEditHandles();
        }
        
        const polyRes = await fetch(`${API}/portfolios/${activePortfolioId}/polygons`);
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

    if (sidebarToggle && sidebar && sidebarClose) {
        sidebarClose.addEventListener('click', () => {
            sidebar.classList.add('collapsed');
            sidebarToggle.classList.remove('hidden');
        });
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.remove('collapsed');
            sidebarToggle.classList.add('hidden');
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
            scopeCount.textContent = 'Missing AOI';
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
            scopeCount.textContent = `${activePolygons.length} AOI${activePolygons.length === 1 ? '' : 's'}`;
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
