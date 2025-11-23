/**
 * Tooltip System
 * Provides contextual help and tooltips for complex features
 */

class TooltipManager {
    constructor() {
        this.tooltips = new Map();
        this.init();
    }

    init() {
        // Auto-initialize tooltips with data-tooltip attribute
        document.addEventListener('DOMContentLoaded', () => {
            this.initializeTooltips();
        });
    }

    initializeTooltips() {
        document.querySelectorAll('[data-tooltip]').forEach(element => {
            this.addTooltip(element, element.getAttribute('data-tooltip'));
        });
    }

    addTooltip(element, text, position = 'top') {
        if (!element || !text) return;

        const tooltipId = `tooltip-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        this.tooltips.set(element, { text, position, id: tooltipId });

        element.addEventListener('mouseenter', (e) => this.showTooltip(e, element));
        element.addEventListener('mouseleave', () => this.hideTooltip(element));
        element.addEventListener('focus', (e) => this.showTooltip(e, element));
        element.addEventListener('blur', () => this.hideTooltip(element));
    }

    showTooltip(e, element) {
        const tooltipData = this.tooltips.get(element);
        if (!tooltipData) return;

        // Remove existing tooltip if any
        this.hideTooltip(element);

        const tooltip = document.createElement('div');
        tooltip.id = tooltipData.id;
        tooltip.className = `tooltip tooltip-${tooltipData.position}`;
        tooltip.setAttribute('role', 'tooltip');
        tooltip.textContent = tooltipData.text;
        document.body.appendChild(tooltip);

        // Position tooltip
        this.positionTooltip(tooltip, element, tooltipData.position);

        // Show with animation
        requestAnimationFrame(() => {
            tooltip.classList.add('tooltip-show');
        });
    }

    hideTooltip(element) {
        const tooltipData = this.tooltips.get(element);
        if (!tooltipData) return;

        const tooltip = document.getElementById(tooltipData.id);
        if (tooltip) {
            tooltip.classList.remove('tooltip-show');
            setTimeout(() => {
                if (tooltip.parentElement) {
                    tooltip.remove();
                }
            }, 200);
        }
    }

    positionTooltip(tooltip, element, position) {
        const rect = element.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();
        const scrollX = window.scrollX || window.pageXOffset;
        const scrollY = window.scrollY || window.pageYOffset;

        let top, left;

        switch (position) {
            case 'top':
                top = rect.top + scrollY - tooltipRect.height - 8;
                left = rect.left + scrollX + (rect.width / 2) - (tooltipRect.width / 2);
                break;
            case 'bottom':
                top = rect.bottom + scrollY + 8;
                left = rect.left + scrollX + (rect.width / 2) - (tooltipRect.width / 2);
                break;
            case 'left':
                top = rect.top + scrollY + (rect.height / 2) - (tooltipRect.height / 2);
                left = rect.left + scrollX - tooltipRect.width - 8;
                break;
            case 'right':
                top = rect.top + scrollY + (rect.height / 2) - (tooltipRect.height / 2);
                left = rect.right + scrollX + 8;
                break;
            default:
                top = rect.top + scrollY - tooltipRect.height - 8;
                left = rect.left + scrollX + (rect.width / 2) - (tooltipRect.width / 2);
        }

        // Keep tooltip within viewport
        const padding = 10;
        if (left < padding) left = padding;
        if (left + tooltipRect.width > window.innerWidth - padding) {
            left = window.innerWidth - tooltipRect.width - padding;
        }
        if (top < scrollY + padding) {
            top = scrollY + padding;
        }

        tooltip.style.top = `${top}px`;
        tooltip.style.left = `${left}px`;
    }
}

// Initialize global tooltip manager
const tooltipManager = new TooltipManager();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TooltipManager;
}

