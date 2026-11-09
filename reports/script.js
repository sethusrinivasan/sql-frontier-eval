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
