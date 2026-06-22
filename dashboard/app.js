// Oberon dashboard — vanilla JS + Leaflet. No build step.
// Under 250 lines total.

const API = window.location.origin + '/v1';
let map = null;
let activeLayer = null;
let activePortfolioId = null;

// ---- Init ----
document.addEventListener('DOMContentLoaded', () => {
    map = L.map('map').setView([10.05, -83.95], 12);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap &copy; CARTO',
        maxZoom: 19,
    }).addTo(map);

    document.getElementById('new-portfolio-btn').addEventListener('click', createPortfolio);
    document.getElementById('close-detail').addEventListener('click', () => {
        document.getElementById('detail-panel').classList.add('hidden');
    });

    loadPortfolios();
});

// ---- Portfolios ----
async function loadPortfolios() {
    try {
        const res = await fetch(`${API}/portfolios`);
        if (!res.ok) return;
        const portfolios = await res.json();
        renderPortfolioList(portfolios);
    } catch (e) {
        console.error('Failed to load portfolios:', e);
    }
}

function renderPortfolioList(portfolios) {
    const el = document.getElementById('portfolio-list');
    el.innerHTML = '';
    if (!portfolios.length) {
        el.innerHTML = '<p class="meta">No portfolios yet. Create one to start monitoring.</p>';
        return;
    }
    portfolios.forEach(p => {
        const div = document.createElement('div');
        div.className = 'portfolio-item';
        if (p.id === activePortfolioId) div.classList.add('active');
        div.innerHTML = `
            <div class="name">${escapeHtml(p.name)}</div>
            <div class="meta">${p.task} · ${new Date(p.created_at).toLocaleDateString()}</div>
            <div class="actions">
                <button onclick="selectPortfolio('${p.id}')">Map</button>
                <button onclick="runPortfolio('${p.id}')">Run</button>
                <button onclick="addPolygon('${p.id}')">+ AOI</button>
                <button onclick="deletePortfolio('${p.id}')">Del</button>
            </div>`;
        el.appendChild(div);
    });
}

async function createPortfolio() {
    const name = prompt('Portfolio name:');
    if (!name) return;
    await fetch(`${API}/portfolios`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
    });
    loadPortfolios();
}

async function deletePortfolio(id) {
    if (!confirm('Delete this portfolio and all its data?')) return;
    await fetch(`${API}/portfolios/${id}`, { method: 'DELETE' });
    if (activePortfolioId === id) {
        activePortfolioId = null;
        if (activeLayer) map.removeLayer(activeLayer);
    }
    loadPortfolios();
}

// ---- Portfolio interactions ----
window.selectPortfolio = async function(id) {
    activePortfolioId = id;
    loadPortfolios();
    const [polyRes, findingsRes] = await Promise.all([
        fetch(`${API}/portfolios/${id}/polygons`),
        fetch(`${API}/portfolios/${id}/findings`),
    ]);
    const polygons = await polyRes.json();
    const findings = await findingsRes.json();
    displayOnMap(polygons, findings);
};

window.runPortfolio = async function(id) {
    const res = await fetch(`${API}/portfolios/${id}/run`, { method: 'POST' });
    const data = await res.json();
    alert(`Started ${data.count} analysis job(s). Check back in a few minutes.`);
};

window.addPolygon = async function(id) {
    const input = prompt('Paste GeoJSON geometry (Polygon or MultiPolygon):');
    if (!input) return;
    try {
        const geometry = JSON.parse(input);
        await fetch(`${API}/portfolios/${id}/polygons`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ geometry, label: 'AOI' }),
        });
        window.selectPortfolio(id);
    } catch (e) {
        alert('Invalid JSON: ' + e.message);
    }
};

// ---- Map ----
function displayOnMap(polygons, findings) {
    if (activeLayer) map.removeLayer(activeLayer);
    const group = L.layerGroup();

    // Draw AOI polygons.
    (polygons || []).forEach(poly => {
        const geom = JSON.parse(poly.geometry_json);
        const layer = L.geoJSON(geom, {
            style: { color: '#58a6ff', weight: 2, fillOpacity: 0.1 },
        });
        layer.bindPopup(`<b>${escapeHtml(poly.label || 'AOI')}</b>`);
        group.addLayer(layer);
    });

    // Draw findings.
    if (findings && findings.features) {
        L.geoJSON(findings, {
            style: { color: '#f0883e', weight: 2, fillOpacity: 0.4 },
            onEachFeature: (feature, layer) => {
                const props = feature.properties || {};
                layer.bindPopup(
                    `<b>Finding</b><br>Score: ${(props.score || 0).toFixed(3)}<br>` +
                    `Area: ${Math.round((props.area_ha || 0) * 10000).toLocaleString()} m²`
                );
                layer.on('click', () => showFindingDetail(feature));
            },
        }).addTo(group);
    }

    group.addTo(map);
    activeLayer = group;

    // Fit bounds.
    if (polygons && polygons.length > 0) {
        const geom = JSON.parse(polygons[0].geometry_json);
        const bounds = L.geoJSON(geom).getBounds();
        map.fitBounds(bounds, { padding: [40, 40] });
    }
}

// ---- Finding detail ----
function showFindingDetail(feature) {
    const props = feature.properties || {};
    const panel = document.getElementById('detail-panel');
    const content = document.getElementById('detail-content');
    document.getElementById('detail-title').textContent = 'Change Finding';
    content.innerHTML = `
        <div class="finding-card">
            <div class="score">${(props.score || 0).toFixed(3)}</div>
            <div class="area">${Math.round((props.area_ha || 0) * 10000).toLocaleString()} m² changed</div>
            <div class="evidence">
                <div><span class="metric">NDVI Δ: </span><span class="value">${((props.metrics || {}).ndvi_delta_mean || 0).toFixed(3)}</span></div>
                <div><span class="metric">NBR Δ: </span><span class="value">${((props.metrics || {}).nbr_delta_mean || 0).toFixed(3)}</span></div>
            </div>
            <div>
                <button class="review-btn" onclick="reviewFinding('approved')">Approve</button>
                <button class="review-btn" onclick="reviewFinding('rejected')">Reject</button>
                <button class="review-btn" onclick="reviewFinding('uncertain')">Uncertain</button>
            </div>
        </div>`;
    panel.classList.remove('hidden');
}

window.reviewFinding = async function(state) {
    // Submit review — needs run_id + finding_idx which we'd track from the map.
    const res = await fetch(`${API}/reviews`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            run_id: 'latest',
            finding_idx: 0,
            portfolio_id: activePortfolioId,
            state,
        }),
    });
    if (res.ok) {
        document.querySelector('#detail-panel .finding-card').style.borderColor = '#238636';
    }
};

// ---- Utils ----
function escapeHtml(s) {
    const d = document.createElement('div');
    d.textContent = s || '';
    return d.innerHTML;
}
