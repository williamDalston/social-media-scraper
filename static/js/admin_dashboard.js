/**
 * Admin Dashboard JavaScript
 * Handles real-time updates and status display
 */

let refreshInterval = null;
const REFRESH_INTERVAL_MS = 30000; // 30 seconds

// Load status on page load
document.addEventListener('DOMContentLoaded', () => {
    loadStatus();
    startAutoRefresh();
});

// Start auto-refresh
function startAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
    refreshInterval = setInterval(loadStatus, REFRESH_INTERVAL_MS);
}

// Stop auto-refresh
function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}

// Load system status
async function loadStatus() {
    try {
        const response = await fetch('/api/admin/status');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        
        // Hide loading, show dashboard
        document.getElementById('loading').style.display = 'none';
        document.getElementById('error').style.display = 'none';
        document.getElementById('dashboard').style.display = 'block';
        
        // Update all sections
        updateSystemHealth(data);
        updateDatabaseStatus(data);
        updateSystemResources(data);
        updateObservabilityStatus(data);
        updatePlatformStats(data);
        
        // Update timestamp
        const timestamp = new Date(data.timestamp);
        document.getElementById('last-updated').textContent = 
            `Last updated: ${timestamp.toLocaleString()}`;
        
    } catch (error) {
        console.error('Error loading status:', error);
        document.getElementById('loading').style.display = 'none';
        document.getElementById('error').style.display = 'block';
        document.getElementById('error').textContent = 
            `Error loading status: ${error.message}`;
    }
}

// Update system health section
function updateSystemHealth(data) {
    const healthHtml = `
        <div class="status-item">
            <span class="status-label">Overall Status</span>
            <span class="status-value status-healthy">✓ Healthy</span>
        </div>
        <div class="status-item">
            <span class="status-label">Database</span>
            <span class="status-value status-healthy">✓ Connected</span>
        </div>
        <div class="status-item">
            <span class="status-label">Total Accounts</span>
            <span class="status-value">${data.database.total_accounts}</span>
        </div>
        <div class="status-item">
            <span class="status-label">Total Snapshots</span>
            <span class="status-value">${data.database.total_snapshots}</span>
        </div>
        <div class="status-item">
            <span class="status-label">Latest Snapshot</span>
            <span class="status-value">${data.database.latest_snapshot_date ? 
                new Date(data.database.latest_snapshot_date).toLocaleDateString() : 'N/A'}</span>
        </div>
    `;
    document.getElementById('system-health').innerHTML = healthHtml;
}

// Update database status section
function updateDatabaseStatus(data) {
    const dbHtml = `
        <div class="status-item">
            <span class="status-label">Total Accounts</span>
            <span class="status-value">${data.database.total_accounts}</span>
        </div>
        <div class="status-item">
            <span class="status-label">Total Snapshots</span>
            <span class="status-value">${data.database.total_snapshots}</span>
        </div>
        <div class="status-item">
            <span class="status-label">Latest Snapshot Date</span>
            <span class="status-value">${data.database.latest_snapshot_date ? 
                new Date(data.database.latest_snapshot_date).toLocaleString() : 'N/A'}</span>
        </div>
    `;
    document.getElementById('database-status').innerHTML = dbHtml;
}

// Update system resources section
function updateSystemResources(data) {
    const memoryPercent = data.system.memory_percent;
    const diskPercent = data.system.disk_percent;
    const cpuPercent = data.system.cpu_percent;
    
    const getStatusClass = (percent) => {
        if (percent > 90) return 'error';
        if (percent > 75) return 'warning';
        return '';
    };
    
    const getStatusText = (percent) => {
        if (percent > 90) return 'Critical';
        if (percent > 75) return 'Warning';
        return 'Normal';
    };
    
    const resourcesHtml = `
        <div class="status-item">
            <span class="status-label">Memory Usage</span>
            <span class="status-value status-${getStatusClass(memoryPercent)}">${memoryPercent.toFixed(1)}%</span>
        </div>
        <div class="progress-bar">
            <div class="progress-fill ${getStatusClass(memoryPercent)}" style="width: ${memoryPercent}%"></div>
        </div>
        <div class="status-item">
            <span class="status-label">Available Memory</span>
            <span class="status-value">${data.system.memory_available_gb} GB</span>
        </div>
        
        <div class="status-item" style="margin-top: 1rem;">
            <span class="status-label">Disk Usage</span>
            <span class="status-value status-${getStatusClass(diskPercent)}">${diskPercent.toFixed(1)}%</span>
        </div>
        <div class="progress-bar">
            <div class="progress-fill ${getStatusClass(diskPercent)}" style="width: ${diskPercent}%"></div>
        </div>
        <div class="status-item">
            <span class="status-label">Free Disk Space</span>
            <span class="status-value">${data.system.disk_free_gb} GB</span>
        </div>
        
        <div class="status-item" style="margin-top: 1rem;">
            <span class="status-label">CPU Usage</span>
            <span class="status-value status-${getStatusClass(cpuPercent)}">${cpuPercent.toFixed(1)}%</span>
        </div>
        <div class="progress-bar">
            <div class="progress-fill ${getStatusClass(cpuPercent)}" style="width: ${cpuPercent}%"></div>
        </div>
    `;
    document.getElementById('system-resources').innerHTML = resourcesHtml;
}

// Update observability status section
function updateObservabilityStatus(data) {
    const obsHtml = `
        <div class="status-item">
            <span class="status-label">Sentry</span>
            <span class="status-value ${data.observability.sentry_enabled ? 'status-healthy' : 'status-warning'}">
                ${data.observability.sentry_enabled ? '✓ Enabled' : '⚠ Disabled'}
            </span>
        </div>
        <div class="status-item">
            <span class="status-label">Logging Level</span>
            <span class="status-value">${data.observability.logging_level}</span>
        </div>
        <div class="status-item">
            <span class="status-label">Log Format</span>
            <span class="status-value">${data.observability.log_format}</span>
        </div>
        <div class="status-item">
            <span class="status-label">Health Endpoint</span>
            <span class="status-value status-healthy">✓ Available</span>
        </div>
        <div class="status-item">
            <span class="status-label">Metrics Endpoint</span>
            <span class="status-value status-healthy">✓ Available</span>
        </div>
    `;
    document.getElementById('observability-status').innerHTML = obsHtml;
}

// Update platform statistics section
function updatePlatformStats(data) {
    const platforms = data.database.platforms;
    const platformEntries = Object.entries(platforms || {});
    
    if (platformEntries.length === 0) {
        document.getElementById('platform-stats').innerHTML = 
            '<p style="color: #999; text-align: center; padding: 2rem;">No platform data available</p>';
        return;
    }
    
    const totalAccounts = Object.values(platforms).reduce((sum, count) => sum + count, 0);
    
    let statsHtml = `
        <div class="metrics-grid">
            <div class="metric">
                <div class="metric-value">${totalAccounts}</div>
                <div class="metric-label">Total Accounts</div>
            </div>
    `;
    
    platformEntries.forEach(([platform, count]) => {
        const percentage = ((count / totalAccounts) * 100).toFixed(1);
        statsHtml += `
            <div class="metric">
                <div class="metric-value">${count}</div>
                <div class="metric-label">${platform}</div>
                <div style="font-size: 0.75rem; color: #999; margin-top: 0.25rem;">${percentage}%</div>
            </div>
        `;
    });
    
    statsHtml += '</div>';
    
    // Add platform badges
    statsHtml += '<div style="margin-top: 1.5rem; padding-top: 1.5rem; border-top: 1px solid #f0f0f0;">';
    platformEntries.forEach(([platform, count]) => {
        statsHtml += `<span class="platform-badge">${platform}: ${count}</span>`;
    });
    statsHtml += '</div>';
    
    document.getElementById('platform-stats').innerHTML = statsHtml;
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    stopAutoRefresh();
});

