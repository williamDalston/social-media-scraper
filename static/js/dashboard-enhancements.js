/**
 * Dashboard UI enhancements - filtering, search, advanced visualizations
 */

// Advanced filtering
class DashboardFilter {
    constructor() {
        this.filters = {
            platform: null,
            organization: null,
            minFollowers: null,
            dateRange: null
        };
    }

    applyFilters(accounts) {
        return accounts.filter(account => {
            if (this.filters.platform && account.platform !== this.filters.platform) {
                return false;
            }
            if (this.filters.organization && account.org_name !== this.filters.organization) {
                return false;
            }
            if (this.filters.minFollowers && account.followers < this.filters.minFollowers) {
                return false;
            }
            return true;
        });
    }

    renderFilterUI() {
        const filterHTML = `
            <div class="filter-panel">
                <h3>Filters</h3>
                <div class="filter-group">
                    <label>Platform:</label>
                    <select id="platformFilter">
                        <option value="">All Platforms</option>
                        <option value="X">X</option>
                        <option value="Instagram">Instagram</option>
                        <option value="Facebook">Facebook</option>
                        <option value="LinkedIn">LinkedIn</option>
                        <option value="YouTube">YouTube</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label>Min Followers:</label>
                    <input type="number" id="minFollowersFilter" placeholder="0">
                </div>
                <div class="filter-group">
                    <label>Date Range:</label>
                    <input type="date" id="dateFrom">
                    <input type="date" id="dateTo">
                </div>
                <button onclick="applyFilters()">Apply Filters</button>
                <button onclick="clearFilters()">Clear</button>
            </div>
        `;
        document.querySelector('.sidebar').insertAdjacentHTML('afterbegin', filterHTML);
    }
}

// Search functionality
function setupSearch() {
    const searchInput = document.createElement('input');
    searchInput.type = 'text';
    searchInput.placeholder = 'Search accounts...';
    searchInput.id = 'accountSearch';
    searchInput.className = 'search-input';
    
    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        const accounts = document.querySelectorAll('.account-item');
        
        accounts.forEach(account => {
            const text = account.textContent.toLowerCase();
            account.style.display = text.includes(query) ? 'block' : 'none';
        });
    });
    
    document.querySelector('.sidebar').insertBefore(
        searchInput,
        document.querySelector('.sidebar').firstChild
    );
}

// Advanced visualizations
function createComparisonChart(accounts) {
    // Compare multiple accounts side by side
    const ctx = document.createElement('canvas');
    ctx.id = 'comparisonChart';
    
    // Implementation would use Chart.js to show multiple accounts
    // This is a placeholder for the structure
}

// Export functionality
function exportData(format = 'csv') {
    const url = format === 'csv' ? '/api/download' : `/api/export?format=${format}`;
    window.location.href = url;
}

// Real-time updates
function setupRealTimeUpdates() {
    // Poll for updates every 30 seconds
    setInterval(async () => {
        try {
            const response = await fetch('/api/summary');
            const data = await response.json();
            updateDashboard(data);
        } catch (error) {
            console.error('Failed to update dashboard:', error);
        }
    }, 30000);
}

// Initialize enhancements
document.addEventListener('DOMContentLoaded', () => {
    setupSearch();
    const filter = new DashboardFilter();
    filter.renderFilterUI();
    setupRealTimeUpdates();
});

