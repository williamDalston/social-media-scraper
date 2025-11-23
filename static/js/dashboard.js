/**
 * Dashboard JavaScript with code splitting and lazy loading
 */

// Lazy load Chart.js only when needed
let Chart = null;
const loadChart = () => {
    if (!Chart) {
        return new Promise((resolve, reject) => {
            // Load Chart.js
            const chartScript = document.createElement('script');
            chartScript.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
            chartScript.onload = () => {
                Chart = window.Chart;
                // Register zoom plugin if available
                if (window.ChartZoom) {
                    Chart.register(window.ChartZoom);
                }
                resolve(Chart);
            };
            chartScript.onerror = reject;
            document.head.appendChild(chartScript);
        });
    }
    return Promise.resolve(Chart);
};

// Lazy load Grid.js only when grid tab is opened
let GridJS = null;
const loadGridJS = () => {
    if (!GridJS) {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://unpkg.com/gridjs/dist/gridjs.umd.js';
            script.onload = () => {
                GridJS = window.gridjs;
                resolve(GridJS);
            };
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }
    return Promise.resolve(GridJS);
};

// Frontend cache with TTL
const apiCache = new Map();
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

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

// Cached fetch with TTL
async function cachedFetch(url, options = {}) {
    const cacheKey = `${url}_${JSON.stringify(options)}`;
    const cached = apiCache.get(cacheKey);
    
    if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
        return cached.data;
    }

    try {
        const response = await fetch(url, options);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        apiCache.set(cacheKey, { data, timestamp: Date.now() });
        return data;
    } catch (error) {
        if (cached) {
            return cached.data;
        }
        throw error;
    }
}

// Chart management
let followersChart = null;
let engagementChart = null;
let gridInstance = null;
let chartLoadTimeout = null;

// Make charts available globally for export
window.followersChart = followersChart;
window.engagementChart = engagementChart;

// Auto-refresh management
let autoRefreshInterval = null;
let lastRefreshTime = null;
const AUTO_REFRESH_INTERVAL = 5 * 60 * 1000; // 5 minutes

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    initializeDashboard();
});

function initializeDashboard() {
    setupTabs();
    setupAutoRefresh();
    loadAccounts();
    updateRefreshIndicator();
}

function setupAutoRefresh() {
    const toggle = document.getElementById('autoRefreshToggle');
    if (!toggle) return;

    // Start auto-refresh if enabled
    if (toggle.checked) {
        startAutoRefresh();
    }

    toggle.addEventListener('change', (e) => {
        if (e.target.checked) {
            startAutoRefresh();
        } else {
            stopAutoRefresh();
        }
    });
}

function startAutoRefresh() {
    stopAutoRefresh(); // Clear any existing interval
    autoRefreshInterval = setInterval(() => {
        refreshData(true); // Silent refresh
    }, AUTO_REFRESH_INTERVAL);
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

async function refreshData(silent = false) {
    const indicator = document.getElementById('lastRefresh');
    const refreshIcon = document.getElementById('refreshIcon');
    
    if (!silent) {
        indicator.classList.add('refreshing');
        refreshIcon.style.animation = 'spin 1s linear infinite';
    }

    try {
        // Clear cache and reload
        apiCache.clear();
        
        // Reload current view
        if (document.getElementById('charts-view').classList.contains('active')) {
            await loadAccounts();
            // Reload current account's history if one is selected
            const activeAccount = document.querySelector('.account-item.active');
            if (activeAccount) {
                const handle = activeAccount.querySelector('.account-handle').textContent;
                const meta = activeAccount.querySelector('.account-meta').textContent;
                const platform = meta.split(' • ')[0];
                await loadHistory(platform, handle);
            }
        } else if (document.getElementById('grid-view').classList.contains('active')) {
            if (gridInstance) {
                gridInstance.forceRender();
            } else {
                await loadGrid();
            }
        }

        lastRefreshTime = new Date();
        updateRefreshIndicator();

        if (!silent && window.toast) {
            toast.success('Data refreshed successfully');
        }
    } catch (error) {
        console.error('Refresh failed:', error);
        if (!silent && window.toast) {
            toast.error('Failed to refresh data');
        }
    } finally {
        if (!silent) {
            indicator.classList.remove('refreshing');
            refreshIcon.style.animation = '';
        }
    }
}

function updateRefreshIndicator() {
    const indicator = document.getElementById('lastRefresh');
    if (!indicator) return;

    if (lastRefreshTime) {
        const now = new Date();
        const diff = Math.floor((now - lastRefreshTime) / 1000);
        
        if (diff < 60) {
            indicator.textContent = `Refreshed ${diff}s ago`;
        } else if (diff < 3600) {
            const minutes = Math.floor(diff / 60);
            indicator.textContent = `Refreshed ${minutes}m ago`;
        } else {
            const hours = Math.floor(diff / 3600);
            indicator.textContent = `Refreshed ${hours}h ago`;
        }
    } else {
        indicator.textContent = 'Never refreshed';
    }
}

// Update refresh indicator every minute
setInterval(updateRefreshIndicator, 60000);

function setupTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const tab = e.target.getAttribute('data-tab');
            switchTab(tab);
        });
    });
}

function switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
        btn.setAttribute('aria-selected', 'false');
    });
    document.querySelectorAll('.view-section').forEach(view => view.classList.remove('active'));

    if (tab === 'charts') {
        const chartsTab = document.querySelector(`[data-tab="charts"]`);
        chartsTab.classList.add('active');
        chartsTab.setAttribute('aria-selected', 'true');
        document.getElementById('charts-view').classList.add('active');
        // Focus management
        chartsTab.focus();
    } else if (tab === 'grid') {
        const gridTab = document.querySelector(`[data-tab="grid"]`);
        gridTab.classList.add('active');
        gridTab.setAttribute('aria-selected', 'true');
        document.getElementById('grid-view').classList.add('active');
        if (!gridInstance) {
            loadGrid();
        }
        // Focus management
        gridTab.focus();
    }
}

async function loadGrid() {
    const wrapper = document.getElementById('table-wrapper');
    const loading = document.getElementById('gridLoading');
    
    // Show loading state
    wrapper.innerHTML = `
        <div style="text-align: center; padding: 40px;">
            <div class="loading-spinner"></div>
            <p style="margin-top: 12px; color: var(--text-secondary);">Loading data grid...</p>
        </div>
    `;
    
    try {
        // Lazy load Grid.js
        await loadGridJS();
        
        gridInstance = new GridJS.Grid({
            columns: ['Platform', 'Handle', 'Org', 'Date', 'Followers', 'Engagement', 'Posts', 'Likes', 'Comments', 'Shares'],
            server: {
                url: '/api/grid',
                then: (data) => {
                    if (data.pagination) {
                        return data.data.map(row => [
                            row[0], row[1], row[2], row[3],
                            (row[4] || 0).toLocaleString(), 
                            (row[5] || 0).toLocaleString(), 
                            row[6] || 0,
                            (row[7] || 0).toLocaleString(), 
                            (row[8] || 0).toLocaleString(), 
                            (row[9] || 0).toLocaleString()
                        ]);
                    }
                    return data.map(row => [
                        row[0], row[1], row[2], row[3],
                        (row[4] || 0).toLocaleString(), 
                        (row[5] || 0).toLocaleString(), 
                        row[6] || 0,
                        (row[7] || 0).toLocaleString(), 
                        (row[8] || 0).toLocaleString(), 
                        (row[9] || 0).toLocaleString()
                    ]);
                }
            },
            search: true,
            sort: true,
            pagination: { limit: 50 },
            style: { table: { 'white-space': 'nowrap' } },
            className: { table: 'table-auto' }
        }).render(wrapper);
    } catch (error) {
        wrapper.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <div class="empty-state-title">Failed to Load Data Grid</div>
                <div class="empty-state-message">${error.message || 'An error occurred while loading the data grid.'}</div>
                <div class="empty-state-actions">
                    <button class="btn" onclick="window.dashboard.loadGrid()">Retry</button>
                </div>
            </div>
        `;
        if (window.errorHandler) {
            errorHandler.handleError(error, {
                retryAction: () => window.dashboard.loadGrid()
            });
        } else if (window.toast) {
            toast.error('Failed to load grid data: ' + error.message);
        }
    }
}

// Store all accounts for filtering
let allAccounts = [];

async function loadAccounts() {
    const list = document.getElementById('accountListContent');
    const skeleton = document.getElementById('accountListSkeleton');
    
    try {
        skeleton.style.display = 'block';
        list.innerHTML = '';

        const data = await cachedFetch('/api/summary');
        
        skeleton.style.display = 'none';

        if (!data || data.length === 0) {
            list.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📊</div>
                    <div class="empty-state-title">No Accounts Found</div>
                    <div class="empty-state-message">
                        Get started by uploading a CSV file with social media accounts or running the scraper to collect data.
                    </div>
                    <div class="empty-state-actions">
                        <button class="btn" onclick="document.getElementById('fileInput').click()">
                            Upload CSV
                        </button>
                        <button class="btn" onclick="runScraper()" style="background-color: #475569;">
                            Run Scraper
                        </button>
                    </div>
                </div>
            `;
            allAccounts = [];
            return;
        }

        // Store all accounts for filtering
        allAccounts = data.sort((a, b) => (b.followers || 0) - (a.followers || 0));
        
        // Render accounts
        renderAccounts(allAccounts);

        // Setup search functionality
        setupAccountSearch();

        if (allAccounts.length > 0) {
            const first = document.getElementById('acc-0');
            if (first) first.classList.add('active');
            loadHistory(allAccounts[0].platform, allAccounts[0].handle);
        }
    } catch (error) {
        skeleton.style.display = 'none';
        list.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <div class="empty-state-title">Failed to Load Accounts</div>
                <div class="empty-state-message">${error.message || 'An error occurred while loading accounts.'}</div>
                <div class="empty-state-actions">
                    <button class="btn" onclick="window.dashboard.loadAccounts()">Retry</button>
                </div>
            </div>
        `;
        if (window.errorHandler) {
            errorHandler.handleError(error, {
                retryAction: () => window.dashboard.loadAccounts()
            });
        } else if (window.toast) {
            toast.error('Failed to load accounts: ' + error.message);
        }
    }
}

function renderAccounts(accounts) {
    const list = document.getElementById('accountListContent');
    list.innerHTML = '';

    accounts.forEach((acc, index) => {
        const div = document.createElement('div');
        div.className = 'account-item';
        div.id = `acc-${index}`;
        div.setAttribute('data-handle', (acc.handle || '').toLowerCase());
        div.setAttribute('data-platform', (acc.platform || '').toLowerCase());
        div.innerHTML = `
            <span class="account-handle">${acc.handle || 'N/A'}</span>
            <span class="account-meta">${acc.platform || 'N/A'} • ${(acc.followers || 0).toLocaleString()} followers</span>
        `;
        div.onclick = () => {
            document.querySelectorAll('.account-item').forEach(el => el.classList.remove('active'));
            div.classList.add('active');
            loadHistory(acc.platform, acc.handle);
        };
        list.appendChild(div);
    });

    // Show no results message if filtered
    if (accounts.length === 0 && allAccounts.length > 0) {
        list.innerHTML = `
            <div class="empty-state" style="padding: 20px;">
                <div class="empty-state-icon">🔍</div>
                <div class="empty-state-title">No Results</div>
                <div class="empty-state-message">No accounts match your search criteria.</div>
            </div>
        `;
    }
}

function setupAccountSearch() {
    const searchInput = document.getElementById('accountSearch');
    if (!searchInput) return;

    // Debounce search
    let searchTimeout;
    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            filterAccounts(e.target.value);
        }, 300);
    });

    // Clear search on escape
    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            searchInput.value = '';
            filterAccounts('');
        }
    });
}

function filterAccounts(query) {
    if (!query || query.trim() === '') {
        renderAccounts(allAccounts);
        return;
    }

    const searchTerm = query.toLowerCase().trim();
    const filtered = allAccounts.filter(acc => {
        const handle = (acc.handle || '').toLowerCase();
        const platform = (acc.platform || '').toLowerCase();
        return handle.includes(searchTerm) || platform.includes(searchTerm);
    });

    renderAccounts(filtered);
}

const debouncedLoadHistory = debounce(loadHistory, 300);

async function loadHistory(platform, handle) {
    if (chartLoadTimeout) {
        clearTimeout(chartLoadTimeout);
    }

    // Show skeleton loaders
    document.getElementById('followersChartSkeleton').style.display = 'block';
    document.getElementById('engagementChartSkeleton').style.display = 'block';
    document.getElementById('followersLoading').style.display = 'flex';
    document.getElementById('engagementLoading').style.display = 'flex';

    try {
        // Lazy load Chart.js
        await loadChart();
        
        const data = await cachedFetch(`/api/history/${platform}/${handle}`);
        
        chartLoadTimeout = setTimeout(() => {
            updateCharts(handle, data);
            document.getElementById('followersLoading').style.display = 'none';
            document.getElementById('engagementLoading').style.display = 'none';
            document.getElementById('followersChartSkeleton').style.display = 'none';
            document.getElementById('engagementChartSkeleton').style.display = 'none';
        }, 50);
    } catch (error) {
        document.getElementById('followersLoading').style.display = 'none';
        document.getElementById('engagementLoading').style.display = 'none';
        document.getElementById('followersChartSkeleton').style.display = 'none';
        document.getElementById('engagementChartSkeleton').style.display = 'none';
        console.error('Failed to load history:', error);
        
        // Show error state in charts
        document.getElementById('followersChartContainer').innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <div class="empty-state-title">Failed to Load Data</div>
                <div class="empty-state-message">${error.message || 'Unable to load chart data.'}</div>
                <div class="empty-state-actions">
                    <button class="btn" onclick="window.dashboard.loadHistory('${platform}', '${handle}')">Retry</button>
                </div>
            </div>
        `;
        document.getElementById('engagementChartContainer').innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <div class="empty-state-title">Failed to Load Data</div>
                <div class="empty-state-message">${error.message || 'Unable to load chart data.'}</div>
                <div class="empty-state-actions">
                    <button class="btn" onclick="window.dashboard.loadHistory('${platform}', '${handle}')">Retry</button>
                </div>
            </div>
        `;
        
        if (window.errorHandler) {
            errorHandler.handleError(error, {
                retryAction: () => window.dashboard.loadHistory(platform, handle)
            });
        } else if (window.toast) {
            toast.error('Failed to load account history: ' + error.message);
        }
    }
}

function updateCharts(handle, data) {
    const followersContainer = document.getElementById('followersChartContainer');
    const engagementContainer = document.getElementById('engagementChartContainer');
    const followersCanvas = document.getElementById('followersChart');
    const engagementCanvas = document.getElementById('engagementChart');
    
    // Check for empty data
    if (!data || !data.dates || data.dates.length === 0) {
        followersContainer.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📈</div>
                <div class="empty-state-title">No Data Available</div>
                <div class="empty-state-message">
                    No historical data found for this account. Run the scraper to collect metrics.
                </div>
            </div>
        `;
        engagementContainer.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">💬</div>
                <div class="empty-state-title">No Engagement Data</div>
                <div class="empty-state-message">
                    No engagement metrics available for this account yet.
                </div>
            </div>
        `;
        return;
    }
    
    // Restore canvas elements if they were replaced
    if (!followersCanvas || !engagementCanvas) {
        followersContainer.innerHTML = '<canvas id="followersChart"></canvas>';
        engagementContainer.innerHTML = '<canvas id="engagementChart"></canvas>';
    }
    
    const ctxFollowers = document.getElementById('followersChart').getContext('2d');
    const ctxEngagement = document.getElementById('engagementChart').getContext('2d');

    if (followersChart) followersChart.destroy();
    if (engagementChart) engagementChart.destroy();

    followersChart = new Chart(ctxFollowers, {
        type: 'line',
        data: {
            labels: data.dates || [],
            datasets: [{
                label: `Followers: ${handle}`,
                data: data.followers || [],
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                fill: true,
                tension: 0.4,
                pointRadius: 3,
                pointHoverRadius: 6,
                pointBackgroundColor: '#3b82f6',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 750 },
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                title: { 
                    display: true, 
                    text: 'Follower Growth', 
                    color: '#f8fafc',
                    font: { size: 16, weight: 'bold' }
                },
                legend: { 
                    labels: { color: '#94a3b8' },
                    display: true
                },
                tooltip: {
                    backgroundColor: 'rgba(30, 41, 59, 0.95)',
                    titleColor: '#f8fafc',
                    bodyColor: '#94a3b8',
                    borderColor: '#334155',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: true,
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${context.parsed.y.toLocaleString()}`;
                        }
                    }
                },
                zoom: {
                    zoom: {
                        wheel: { enabled: true },
                        pinch: { enabled: true },
                        mode: 'x'
                    },
                    pan: {
                        enabled: true,
                        mode: 'x'
                    }
                }
            },
            scales: {
                y: { 
                    grid: { color: '#334155' }, 
                    ticks: { 
                        color: '#94a3b8',
                        callback: function(value) {
                            return value.toLocaleString();
                        }
                    } 
                },
                x: { 
                    grid: { display: false }, 
                    ticks: { color: '#94a3b8' } 
                }
            }
        }
    });

    engagementChart = new Chart(ctxEngagement, {
        type: 'bar',
        data: {
            labels: data.dates || [],
            datasets: [{
                label: `Daily Engagement`,
                data: data.engagement || [],
                backgroundColor: '#10b981',
                borderRadius: 4,
                borderSkipped: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 750 },
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                title: { 
                    display: true, 
                    text: 'Daily Engagement Volume', 
                    color: '#f8fafc',
                    font: { size: 16, weight: 'bold' }
                },
                legend: { 
                    labels: { color: '#94a3b8' },
                    display: true
                },
                tooltip: {
                    backgroundColor: 'rgba(30, 41, 59, 0.95)',
                    titleColor: '#f8fafc',
                    bodyColor: '#94a3b8',
                    borderColor: '#334155',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: true,
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${context.parsed.y.toLocaleString()}`;
                        }
                    }
                },
                zoom: {
                    zoom: {
                        wheel: { enabled: true },
                        pinch: { enabled: true },
                        mode: 'x'
                    },
                    pan: {
                        enabled: true,
                        mode: 'x'
                    }
                }
            },
            scales: {
                y: { 
                    grid: { color: '#334155' }, 
                    ticks: { 
                        color: '#94a3b8',
                        callback: function(value) {
                            return value.toLocaleString();
                        }
                    } 
                },
                x: { 
                    grid: { display: false }, 
                    ticks: { color: '#94a3b8' } 
                }
            }
        }
    });

    // Add chart export buttons
    addChartExportButtons(handle);
    
    // Update global references
    window.followersChart = followersChart;
    window.engagementChart = engagementChart;
}

function addChartExportButtons(handle) {
    const followersActions = document.getElementById('followersChartActions');
    const engagementActions = document.getElementById('engagementChartActions');
    if (followersActions) followersActions.style.display = 'flex';
    if (engagementActions) engagementActions.style.display = 'flex';
}

function exportChart(chartId) {
    const canvas = document.getElementById(chartId);
    if (!canvas) return;

    const chart = chartId === 'followersChart' ? followersChart : engagementChart;
    if (!chart) return;

    const url = canvas.toDataURL('image/png');
    const link = document.createElement('a');
    link.download = `${chartId}_${new Date().toISOString().split('T')[0]}.png`;
    link.href = url;
    link.click();

    if (window.toast) {
        toast.success('Chart exported successfully');
    }
}

function resetChartZoom(chartId) {
    const chart = chartId === 'followersChart' ? followersChart : engagementChart;
    if (!chart) return;

    if (chart.resetZoom) {
        chart.resetZoom();
    } else {
        // Fallback: reload chart
        const activeAccount = document.querySelector('.account-item.active');
        if (activeAccount) {
            const handle = activeAccount.querySelector('.account-handle').textContent;
            const meta = activeAccount.querySelector('.account-meta').textContent;
            const platform = meta.split(' • ')[0];
            loadHistory(platform, handle);
        }
    }

    if (window.toast) {
        toast.info('Chart zoom reset');
    }
}

// Export for use in HTML
window.dashboard = {
    switchTab,
    loadAccounts,
    loadHistory,
    loadGrid,
    filterAccounts,
    refreshData
};

window.exportChart = exportChart;
window.resetChartZoom = resetChartZoom;

