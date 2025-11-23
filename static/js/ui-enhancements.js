/**
 * UI Enhancement Utilities
 * Adds interactive features and visual improvements
 */

// Add platform badges to account items
function addPlatformBadges() {
    const accountItems = document.querySelectorAll('.account-item');
    accountItems.forEach(item => {
        const platform = item.dataset.platform || item.querySelector('.account-meta')?.textContent?.split('•')[0]?.trim().toLowerCase();
        if (platform && !item.querySelector('.platform-badge')) {
            const badge = document.createElement('span');
            badge.className = `platform-badge ${platform}`;
            badge.textContent = platform.charAt(0).toUpperCase() + platform.slice(1);
            const handle = item.querySelector('.account-handle');
            if (handle) {
                handle.insertBefore(badge, handle.firstChild);
            }
        }
    });
}

// Add ripple effect to buttons
function addRippleEffect() {
    const buttons = document.querySelectorAll('.btn, .btn-icon, .tab-btn');
    buttons.forEach(button => {
        if (!button.classList.contains('ripple')) {
            button.classList.add('ripple');
        }
    });
}

// Add smooth scroll to account items
function enhanceAccountList() {
    const accountList = document.getElementById('accountListContent');
    if (!accountList) return;
    
    accountList.addEventListener('click', (e) => {
        const accountItem = e.target.closest('.account-item');
        if (accountItem) {
            // Add click animation
            accountItem.style.transform = 'scale(0.98)';
            setTimeout(() => {
                accountItem.style.transform = '';
            }, 150);
        }
    });
}

// Add loading states with animations
function showLoadingState(element, message = 'Loading...') {
    if (!element) return;
    
    const loadingHTML = `
        <div class="loading-overlay" style="display: flex; align-items: center; justify-content: center;">
            <div style="text-align: center;">
                <div class="loading-spinner"></div>
                <p style="margin-top: 16px; color: var(--text-secondary);">${message}</p>
            </div>
        </div>
    `;
    
    element.style.position = 'relative';
    element.insertAdjacentHTML('beforeend', loadingHTML);
}

function hideLoadingState(element) {
    if (!element) return;
    const overlay = element.querySelector('.loading-overlay');
    if (overlay) {
        overlay.style.opacity = '0';
        setTimeout(() => overlay.remove(), 300);
    }
}

// Add success animation
function showSuccessAnimation(element, message) {
    if (!element) return;
    
    const successHTML = `
        <div class="success-animation" style="
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--gradient-success);
            color: white;
            padding: 16px 24px;
            border-radius: 12px;
            box-shadow: var(--shadow-xl);
            z-index: 10000;
            animation: slideInRight 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        ">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 20px;">✓</span>
                <span>${message}</span>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', successHTML);
    
    setTimeout(() => {
        const notification = document.querySelector('.success-animation');
        if (notification) {
            notification.style.animation = 'slideOutRight 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
            setTimeout(() => notification.remove(), 300);
        }
    }, 3000);
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Enhance chart tooltips
function enhanceChartTooltips() {
    // This will be called when charts are created
    // Chart.js tooltips are already styled in dashboard.js
}

// Add keyboard navigation enhancements
function addKeyboardNavigation() {
    document.addEventListener('keydown', (e) => {
        // Escape key to close modals/dropdowns
        if (e.key === 'Escape') {
            const menus = document.querySelectorAll('.export-dropdown, .user-dropdown');
            menus.forEach(menu => {
                if (menu.style.display !== 'none') {
                    menu.style.display = 'none';
                }
            });
        }
        
        // Arrow keys for account navigation
        if (e.target.classList.contains('account-item') || e.target.closest('.account-item')) {
            const items = Array.from(document.querySelectorAll('.account-item'));
            const currentIndex = items.indexOf(e.target.closest('.account-item'));
            
            if (e.key === 'ArrowDown' && currentIndex < items.length - 1) {
                e.preventDefault();
                items[currentIndex + 1].focus();
                items[currentIndex + 1].click();
            } else if (e.key === 'ArrowUp' && currentIndex > 0) {
                e.preventDefault();
                items[currentIndex - 1].focus();
                items[currentIndex - 1].click();
            }
        }
    });
}

// Add intersection observer for fade-in animations
function addScrollAnimations() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1
    });
    
    document.querySelectorAll('.chart-container, .metric-card, .stat-item').forEach(el => {
        observer.observe(el);
    });
}

// Initialize all enhancements
function initUIEnhancements() {
    addPlatformBadges();
    addRippleEffect();
    enhanceAccountList();
    addKeyboardNavigation();
    addScrollAnimations();
    
    // Re-run when account list updates
    const accountListObserver = new MutationObserver(() => {
        addPlatformBadges();
        enhanceAccountList();
    });
    
    const accountList = document.getElementById('accountListContent');
    if (accountList) {
        accountListObserver.observe(accountList, { childList: true, subtree: true });
    }
}

// Export functions for global use
window.UIEnhancements = {
    init: initUIEnhancements,
    showLoading: showLoadingState,
    hideLoading: hideLoadingState,
    showSuccess: showSuccessAnimation,
    addPlatformBadges,
    addRippleEffect
};

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initUIEnhancements);
} else {
    initUIEnhancements();
}

