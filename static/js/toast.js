/**
 * Toast Notification System
 * Provides user-friendly feedback for actions
 */

class ToastManager {
    constructor() {
        this.container = null;
        this.init();
    }

    init() {
        // Create toast container if it doesn't exist
        if (!document.getElementById('toast-container')) {
            this.container = document.createElement('div');
            this.container.id = 'toast-container';
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        } else {
            this.container = document.getElementById('toast-container');
        }
    }

    show(message, type = 'info', duration = 5000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'polite');
        
        const icon = this.getIcon(type);
        toast.innerHTML = `
            <div class="toast-content">
                <span class="toast-icon">${icon}</span>
                <span class="toast-message">${this.escapeHtml(message)}</span>
            </div>
            <button class="toast-close" aria-label="Close notification" onclick="this.parentElement.remove()">
                <span aria-hidden="true">×</span>
            </button>
        `;

        this.container.appendChild(toast);

        // Trigger animation
        requestAnimationFrame(() => {
            toast.classList.add('toast-show');
        });

        // Auto-remove after duration
        if (duration > 0) {
            setTimeout(() => {
                this.remove(toast);
            }, duration);
        }

        return toast;
    }

    success(message, duration = 5000) {
        const toast = this.show(message, 'success', duration);
        // Add success animation
        if (toast) {
            toast.classList.add('success-animation');
        }
        return toast;
    }

    error(message, duration = 7000) {
        return this.show(message, 'error', duration);
    }

    warning(message, duration = 6000) {
        return this.show(message, 'warning', duration);
    }

    info(message, duration = 5000) {
        return this.show(message, 'info', duration);
    }

    remove(toast) {
        toast.classList.add('toast-hide');
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 300);
    }

    getIcon(type) {
        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ'
        };
        return icons[type] || icons.info;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize global toast manager
const toast = new ToastManager();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ToastManager;
}

