/**
 * Theme Toggle System
 * Provides dark/light mode switching
 */

class ThemeManager {
    constructor() {
        this.currentTheme = 'dark';
        this.init();
    }

    init() {
        // Load saved theme preference
        const savedTheme = localStorage.getItem('theme') || 'dark';
        this.setTheme(savedTheme);

        // Watch for system preference changes
        if (window.matchMedia) {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: light)');
            mediaQuery.addEventListener('change', (e) => {
                if (!localStorage.getItem('theme')) {
                    this.setTheme(e.matches ? 'light' : 'dark');
                }
            });
        }
    }

    setTheme(theme) {
        this.currentTheme = theme;
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);

        // Update toggle button if it exists
        const toggle = document.getElementById('themeToggle');
        if (toggle) {
            toggle.setAttribute('aria-label', `Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`);
            toggle.textContent = theme === 'dark' ? '☀️' : '🌙';
        }

        // Dispatch event for other components
        window.dispatchEvent(new CustomEvent('themechange', { detail: { theme } }));
    }

    toggle() {
        const newTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
        this.setTheme(newTheme);
    }

    getTheme() {
        return this.currentTheme;
    }
}

// Initialize global theme manager
const themeManager = new ThemeManager();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ThemeManager;
}

