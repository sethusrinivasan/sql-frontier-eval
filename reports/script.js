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

function copyCurrentUrl(btn) {
    const url = window.location.href;
    navigator.clipboard.writeText(url).then(() => {
        const origText = btn.innerHTML;
        btn.innerHTML = '<span class="btn-icon">✔</span> Copied!';
        btn.classList.add('btn-success');
        setTimeout(() => {
            btn.innerHTML = origText;
            btn.classList.remove('btn-success');
        }, 2000);
    }).catch(err => {
        alert('Copied URL: ' + url);
    });
}

function exportPDF() {
    window.print();
}

function exportQueryDataAsCSV(taskId) {
    const table = document.querySelector('.result-column table.data-table') || document.querySelector('table.data-table');
    if (!table) {
        alert('No tabular data available to export.');
        return;
    }
    let csv = [];
    const rows = table.querySelectorAll('tr');
    rows.forEach(row => {
        const cols = row.querySelectorAll('th, td');
        let rowData = [];
        cols.forEach(col => {
            let val = col.innerText.replace(/"/g, '""').trim();
            rowData.push('"' + val + '"');
        });
        csv.push(rowData.join(','));
    });
    const blob = new Blob([csv.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = taskId + "_dataset_results.csv";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function exportQueryAsMarkdown(taskId) {
    const title = document.querySelector('.task-title')?.innerText?.replace('#', '')?.trim() || taskId;
    const cat = document.querySelector('.nav-cat')?.innerText || '';
    const desc = document.querySelector('#trap .analysis-item p')?.innerText || '';
    const prompt = document.querySelector('#trap pre.prompt-code')?.innerText || '';
    const candidateSql = document.querySelector('#code-candidate')?.innerText || '';
    const goldenSql = document.querySelector('#code-golden')?.innerText || '';
    const setupSql = document.querySelector('#code-setup')?.innerText || '';

    let md = `# ${taskId}: ${title}\n\n`;
    md += `**Category:** ${cat}\n`;
    md += `**Benchmark:** [SQL-Frontier-Eval](https://sethusrinivasan.github.io/sql-frontier-eval/)\n\n`;
    md += `## Problem Description & Analytical Trap\n${desc}\n\n`;
    md += `## Prompt Given to Model\n\`\`\`\n${prompt}\n\`\`\`\n\n`;
    md += `## Candidate SQL (Evaluated)\n\`\`\`sql\n${candidateSql}\n\`\`\`\n\n`;
    md += `## Golden SQL (Ground Truth)\n\`\`\`sql\n${goldenSql}\n\`\`\`\n\n`;
    md += `## Setup DDL & Data Fixture\n\`\`\`sql\n${setupSql}\n\`\`\`\n\n`;
    md += `---\n*Exported from [SQL-Frontier-Eval Deep-Dive](https://sethusrinivasan.github.io/sql-frontier-eval/queries/${taskId}.html)*\n`;

    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8;' });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = taskId + "_specification.md";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function exportBenchmarkSummaryCSV() {
    const table = document.getElementById('queriesTable');
    if (!table) return;
    let csv = [];
    const rows = table.querySelectorAll('tr');
    rows.forEach(row => {
        if (row.style.display === 'none') return;
        const cols = row.querySelectorAll('th, td');
        let rowData = [];
        cols.forEach((col, idx) => {
            if (idx === cols.length - 1 && row.parentElement.tagName === 'TBODY') return; // skip action button
            let val = col.innerText.replace(/"/g, '""').trim();
            rowData.push('"' + val + '"');
        });
        csv.push(rowData.join(','));
    });
    const blob = new Blob([csv.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "sql_frontier_eval_benchmark_queries.csv";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function exportBenchmarkMarkdown() {
    let md = `# SQL-Frontier-Eval: Benchmark Executive Summary\n\n`;
    md += `Empirical evaluation of Frontier AI models across **120 production-grade analytical SQL tasks** scaled to **108,027,582 records** across DuckDB 2.0, PostgreSQL 19.0, Databricks SQL, and Amazon Aurora Serverless v2.\n\n`;
    md += `## Multi-Model Frontier Standings\n\n`;
    md += `| Model / Baseline | Pass Rate | Correct / Total | Avg Model Latency | Engine Exec Latency (1M) |\n`;
    md += `| :--- | :---: | :---: | :---: | :---: |\n`;
    md += `| **Claude Opus 4.6 (Thinking)** | **98.3%** | 118 / 120 | 14.8s | 219.4 ms |\n`;
    md += `| **Gemini 3.8 Flash (Medium)** | **96.7%** | 116 / 120 | 12.4s | 224.1 ms |\n`;
    md += `| **Gemini 3.8 Flash (Low)** | **95.8%** | 115 / 120 | 4.6s | 232.2 ms |\n`;
    md += `| **Claude Sonnet 4.6 (Thinking)** | **94.2%** | 113 / 120 | 9.1s | 228.6 ms |\n`;
    md += `| **Gemini 3.8 Flash (High)** | **92.5%** | 111 / 120 | 38.6s | 236.4 ms |\n`;
    md += `| **GPT-OSS 120B (Medium)** | **90.8%** | 109 / 120 | 8.2s | 245.8 ms |\n`;
    md += `| **Golden Ground Truth** | **100.0%** | 120 / 120 | N/A | 217.8 ms |\n\n`;
    md += `## Evaluated Database Engines\n`;
    md += `- **DuckDB 2.0 In-Memory Engine**: Columnar OLAP with SIMD AVX2 vector execution chunks.\n`;
    md += `- **PostgreSQL 19.0 + Extensions**: Relational row-store with pgvector, pg_trgm, btree_gist.\n`;
    md += `- **Databricks Serverless SQL Warehouse**: Cloud Lakehouse with Unity Catalog and Photon.\n`;
    md += `- **Amazon Aurora Serverless v2 PostgreSQL**: AWS Serverless cluster with IAM DB authentication and 15 isolated category schemas.\n\n`;
    md += `Explore all interactive query plans and deep dives at: https://sethusrinivasan.github.io/sql-frontier-eval/\n`;

    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8;' });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "sql_frontier_eval_executive_summary.md";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

let activeDomainFilter = 'ALL';
let activeStatusFilter = 'ALL';

function filterQueries() {
    const searchInput = document.getElementById('searchInput');
    const term = searchInput ? searchInput.value.toLowerCase().trim() : '';
    const rows = document.querySelectorAll('.task-row');
    let visibleCount = 0;

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
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });

    const countElem = document.getElementById('queryFilterCount');
    if (countElem) {
        countElem.innerHTML = `Showing <strong>${visibleCount}</strong> of ${rows.length} benchmark queries`;
    }
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

// Multi-Database Engine Switcher (DuckDB vs PostgreSQL vs Databricks vs Aurora Serverless)
const ENGINE_CONFIGS = {
    duckdb: {
        name: "DuckDB 2.0 In-Memory (Columnar OLAP)",
        navBadge: "⚡ DuckDB 2.0 In-Memory (1M+ Records/Table)",
        statusBanner: 'Active Engine: <strong>⚡ DuckDB 2.0 In-Memory Engine</strong> &mdash; 120 benchmark queries evaluated against 108M+ records. Showing columnar vectorized execution plans, SIMD AVX2 acceleration, and in-memory aggregation benchmarks.',
        domainBadge: "⚡ Evaluated on DuckDB 2.0 In-Memory Engine (1M+ Records/Table)",
        domainPillText: "⚡ DuckDB 2.0",
        tableBadgeText: "⚡ DuckDB 2.0",
        tableBadgeClass: "badge-duckdb",
        passRate: "95.8%",
        tasksPassed: "115 Passed • 5 Diverged",
        avgLatency: "232.2 ms",
        goldenLatency: "Golden Avg: 217.8 ms",
        dataVolume: "3.04 GiB",
        recordsVolume: "108,027,582 Records (148 Tables)",
        modelName: "agy/gemini-3.8-flash-low"
    },
    postgres: {
        name: "PostgreSQL 19.0 (Relational + pgvector + FTS)",
        navBadge: "🐘 PostgreSQL 19.0 + Extensions (Docker Compose)",
        statusBanner: 'Active Engine: <strong>🐘 PostgreSQL 19.0 + Extensions</strong> &mdash; 120 benchmark queries evaluated in Docker Compose. Showing relational row-store execution plans, pgvector distance indexing, GIN trigram matching, and ACID multi-session isolation.',
        domainBadge: "🐘 Evaluated on PostgreSQL 19.0 + Extensions (Docker Compose)",
        domainPillText: "🐘 PostgreSQL 19.0",
        tableBadgeText: "🐘 PostgreSQL 19.0",
        tableBadgeClass: "badge-postgres",
        passRate: "93.3%",
        tasksPassed: "112 Passed • 8 Diverged",
        avgLatency: "198.7 ms",
        goldenLatency: "Golden Avg: 178.6 ms",
        dataVolume: "3.48 GiB",
        recordsVolume: "108,027,582 Records (148 Tables)",
        modelName: "agy/gemini-3.8-flash-low"
    },
    databricks: {
        name: "Databricks SQL Warehouse (Serverless Cloud Analytics)",
        navBadge: "🧱 Databricks SQL Warehouse (Unity Catalog / Serverless)",
        statusBanner: 'Active Engine: <strong>🧱 Databricks Serverless SQL Warehouse</strong> &mdash; 120 benchmark queries audited against live cloud warehouse (<code>workspace.sql_frontier_eval_sandbox</code>). Showing serverless execution latency, higher-order array functions, and Spark SQL dialect analysis.',
        domainBadge: "🧱 Evaluated on Databricks Serverless Warehouse (Unity Catalog)",
        domainPillText: "🧱 Databricks SQL",
        tableBadgeText: "🧱 Databricks SQL",
        tableBadgeClass: "badge-databricks",
        passRate: "80.8%",
        tasksPassed: "97 Passed • 23 Diverged",
        avgLatency: "248.5 ms",
        goldenLatency: "Golden Avg: 386.4 ms",
        dataVolume: "Serverless Cloud",
        recordsVolume: "108M+ Records (Serverless Warehouse)",
        modelName: "agy/claude-opus-4-6-thinking"
    },
    aurora: {
        name: "Amazon Aurora Serverless v2 PostgreSQL (AWS IAM DB Auth)",
        navBadge: "☁️ Aurora Serverless v2 PostgreSQL (IAM DB Auth)",
        statusBanner: 'Active Engine: <strong>☁️ Amazon Aurora Serverless v2 PostgreSQL</strong> &mdash; 120 benchmark queries evaluated on AWS with IAM Database Authentication across 15 category-isolated IAM roles and scoped schemas. Showing auto-scaling Aurora compute, zero-credential token rotation, and distributed storage performance.',
        domainBadge: "☁️ Evaluated on Amazon Aurora Serverless v2 PostgreSQL (IAM DB Auth)",
        domainPillText: "☁️ Aurora PostgreSQL",
        tableBadgeText: "☁️ Aurora PostgreSQL",
        tableBadgeClass: "badge-aurora",
        passRate: "93.3%",
        tasksPassed: "112 Passed • 8 Diverged",
        avgLatency: "186.4 ms",
        goldenLatency: "Golden Avg: 172.5 ms",
        dataVolume: "AWS Cloud DB",
        recordsVolume: "108M+ Records (Aurora Serverless)",
        modelName: "agy/gemini-3.8-flash-low"
    }
};

function switchEngine(engine) {
    if (!ENGINE_CONFIGS[engine]) return;
    const cfg = ENGINE_CONFIGS[engine];
    try {
        localStorage.setItem('sql_frontier_active_engine', engine);
    } catch (e) {}

    // Update switcher pills (top nav)
    document.querySelectorAll('.engine-pill').forEach(btn => {
        if (btn.getAttribute('data-engine') === engine) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // Update prominent engine pivot bar buttons
    document.querySelectorAll('.engine-pivot-btn').forEach(btn => {
        if (btn.getAttribute('data-engine') === engine) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // Update engine status banner
    const statusBanner = document.getElementById('engine-status-banner');
    if (statusBanner) {
        statusBanner.innerHTML = cfg.statusBanner;
    }

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
    const dbxTbody = document.getElementById('tbody-databricks');
    const auroraTbody = document.getElementById('tbody-aurora');
    const badgeEngine = document.getElementById('leaderboard-engine-badge');

    if (duckdbTbody) duckdbTbody.style.display = 'none';
    if (pgTbody) pgTbody.style.display = 'none';
    if (dbxTbody) dbxTbody.style.display = 'none';
    if (auroraTbody) auroraTbody.style.display = 'none';

    if (engine === 'postgres') {
        if (pgTbody) pgTbody.style.display = '';
        if (badgeEngine) badgeEngine.textContent = 'PostgreSQL 19.0 Suite (120/120 Tasks)';
    } else if (engine === 'databricks') {
        if (dbxTbody) dbxTbody.style.display = '';
        if (badgeEngine) badgeEngine.textContent = 'Databricks SQL Suite (120/120 Tasks)';
    } else if (engine === 'aurora') {
        if (auroraTbody) auroraTbody.style.display = '';
        if (badgeEngine) badgeEngine.textContent = 'Amazon Aurora Serverless v2 Suite (120/120 Tasks)';
    } else {
        if (duckdbTbody) duckdbTbody.style.display = '';
        if (badgeEngine) badgeEngine.textContent = 'DuckDB 2.0 Suite (120/120 Tasks)';
    }

    // Update analytical domains badge & domain pills
    const domainBadge = document.getElementById('domain-engine-badge');
    if (domainBadge) {
        domainBadge.textContent = cfg.domainBadge;
    }

    document.querySelectorAll('.domain-engine-pill').forEach(pill => {
        pill.textContent = cfg.domainPillText;
        pill.classList.remove('postgres', 'aurora');
        if (engine === 'postgres') {
            pill.classList.add('postgres');
        } else if (engine === 'aurora') {
            pill.classList.add('aurora');
        }
    });

    // Update query explorer table engine badges
    document.querySelectorAll('.engine-table-badge').forEach(badge => {
        badge.textContent = cfg.tableBadgeText;
        badge.className = 'engine-table-badge ' + cfg.tableBadgeClass;
    });
}

// Restore saved engine preference on load
document.addEventListener('DOMContentLoaded', () => {
    let saved = 'duckdb';
    try {
        saved = localStorage.getItem('sql_frontier_active_engine') || 'duckdb';
    } catch (e) {}
    switchEngine(saved);
});
