// SQL-Frontier-Eval Client-Side Interactivity
function switchTab(evt, tabId) {
    const parent = evt.target.closest('.query-tabs');
    parent.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    parent.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    evt.target.classList.add('active');
    document.getElementById(tabId).classList.add('active');
}

function copyCode(elementId) {
    const codeElem = document.getElementById(elementId);
    if (!codeElem) return;
    const text = codeElem.innerText;
    navigator.clipboard.writeText(text).then(() => {
        const btn = event.target;
        const orig = btn.innerText;
        btn.innerText = "Copied!";
        btn.style.borderColor = "var(--status-pass)";
        btn.style.color = "var(--status-pass)";
        setTimeout(() => {
            btn.innerText = orig;
            btn.style.borderColor = "";
            btn.style.color = "";
        }, 1500);
    });
}

let activeDomainFilter = 'ALL';
let activeStatusFilter = 'ALL';

function filterQueries() {
    const searchInput = document.getElementById('searchInput');
    const term = searchInput ? searchInput.value.toLowerCase().trim() : '';
    const rows = document.querySelectorAll('.task-row');

    rows.forEach(row => {
        const rowId = (row.getAttribute('data-id') || '').toLowerCase();
        const rowDomain = (row.getAttribute('data-domain') || '');
        const rowStatus = (row.getAttribute('data-status') || '');
        const textContent = row.textContent.toLowerCase();

        const matchDomain = (activeDomainFilter === 'ALL' || rowDomain === activeDomainFilter);
        const matchStatus = (activeStatusFilter === 'ALL' || rowStatus === activeStatusFilter);
        const matchSearch = (term === '' || textContent.includes(term) || rowId.includes(term));

        if (matchDomain && matchStatus && matchSearch) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

function setDomainFilter(domain, btn) {
    activeDomainFilter = domain;
    document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
    if (btn) btn.classList.add('active');
    filterQueries();
}

function filterByDomain(domain) {
    activeDomainFilter = domain;
    document.querySelectorAll('.filter-pill').forEach(p => {
        if (p.textContent.includes(domain)) {
            p.classList.add('active');
        } else {
            p.classList.remove('active');
        }
    });
    const table = document.getElementById('queriesTable');
    if (table) {
        table.scrollIntoView({ behavior: 'smooth' });
    }
    filterQueries();
}

function setStatusFilter(status, btn) {
    activeStatusFilter = status;
    document.querySelectorAll('.status-pill').forEach(p => p.classList.remove('active'));
    if (btn) btn.classList.add('active');
    filterQueries();
}

// Multi-Database Engine Switcher (DuckDB vs PostgreSQL)
const ENGINE_CONFIGS = {
    duckdb: {
        name: "DuckDB 2.0 In-Memory (Columnar OLAP)",
        navBadge: "⚡ DuckDB 2.0 In-Memory (1M+ Records/Table)",
        passRate: "95.8%",
        tasksPassed: "115 Passed • 5 Diverged",
        avgLatency: "232.2 ms",
        goldenLatency: "Golden Avg: 217.8 ms",
        dataVolume: "3.04 GiB",
        recordsVolume: "108,027,582 Records (148 Tables)",
        modelName: "agy/gemini-3.8-flash-low"
    },
    postgres: {
        name: "PostgreSQL 18.7 (Relational + pgvector + FTS)",
        navBadge: "🐘 PostgreSQL 18.7 + Extensions (Docker Compose)",
        passRate: "93.3%",
        tasksPassed: "112 Passed • 8 Diverged",
        avgLatency: "198.7 ms",
        goldenLatency: "Golden Avg: 178.6 ms",
        dataVolume: "3.48 GiB",
        recordsVolume: "108,027,582 Records (148 Tables)",
        modelName: "agy/gemini-3.8-flash-low"
    }
};

function switchEngine(engine) {
    if (!ENGINE_CONFIGS[engine]) return;
    const cfg = ENGINE_CONFIGS[engine];
    try {
        localStorage.setItem('sql_frontier_active_engine', engine);
    } catch (e) {}

    // Update switcher pills
    document.querySelectorAll('.engine-pill').forEach(btn => {
        if (btn.getAttribute('data-engine') === engine) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // Update nav badge
    const navBadge = document.querySelector('.engine-badge');
    if (navBadge) navBadge.textContent = cfg.navBadge;

    // Update hero KPIs
    const passRateElem = document.querySelector('.hsb-rate');
    if (passRateElem) passRateElem.textContent = cfg.passRate;

    const latVal = document.getElementById('kpi-lat-val');
    if (latVal) latVal.textContent = cfg.avgLatency;

    const latSub = document.getElementById('kpi-lat-sub');
    if (latSub) latSub.textContent = cfg.goldenLatency;

    const volVal = document.getElementById('kpi-vol-val');
    if (volVal) volVal.textContent = cfg.dataVolume;

    const modelSub = document.getElementById('kpi-model-sub');
    if (modelSub) modelSub.textContent = cfg.tasksPassed;

    // Toggle leaderboard table bodies
    const duckdbTbody = document.getElementById('tbody-duckdb');
    const pgTbody = document.getElementById('tbody-postgres');
    const badgeEngine = document.getElementById('leaderboard-engine-badge');

    if (duckdbTbody && pgTbody) {
        if (engine === 'postgres') {
            duckdbTbody.style.display = 'none';
            pgTbody.style.display = '';
            if (badgeEngine) badgeEngine.textContent = 'PostgreSQL 18.7 Suite (120/120 Tasks)';
        } else {
            duckdbTbody.style.display = '';
            pgTbody.style.display = 'none';
            if (badgeEngine) badgeEngine.textContent = 'DuckDB 2.0 Suite (120/120 Tasks)';
        }
    }
}

// Restore saved engine preference on load
document.addEventListener('DOMContentLoaded', () => {
    let saved = 'duckdb';
    try {
        saved = localStorage.getItem('sql_frontier_active_engine') || 'duckdb';
    } catch (e) {}
    switchEngine(saved);
});
