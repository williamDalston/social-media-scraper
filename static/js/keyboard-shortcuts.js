/**
 * Keyboard Shortcuts System
 * Provides keyboard navigation and shortcuts for common actions
 */

class KeyboardShortcuts {
    constructor() {
        this.shortcuts = new Map();
        this.helpVisible = false;
        this.init();
    }

    init() {
        document.addEventListener('keydown', (e) => {
            this.handleKeyPress(e);
        });

        // Register default shortcuts
        this.registerDefaults();
    }

    registerDefaults() {
        // Refresh data
        this.register('r', () => {
            if (!this.isInputFocused()) {
                if (window.dashboard && window.dashboard.refreshData) {
                    window.dashboard.refreshData();
                }
            }
        }, 'Refresh data');

        // Search accounts
        this.register('/', (e) => {
            const searchInput = document.getElementById('accountSearch');
            if (searchInput && !this.isInputFocused()) {
                e.preventDefault();
                searchInput.focus();
            }
        }, 'Focus search');

        // Switch to charts tab
        this.register('1', () => {
            if (!this.isInputFocused()) {
                if (window.dashboard) {
                    window.dashboard.switchTab('charts');
                }
            }
        }, 'Switch to Charts');

        // Switch to grid tab
        this.register('2', () => {
            if (!this.isInputFocused()) {
                if (window.dashboard) {
                    window.dashboard.switchTab('grid');
                }
            }
        }, 'Switch to Grid');

        // Escape - clear search or close modals
        this.register('Escape', () => {
            const searchInput = document.getElementById('accountSearch');
            if (searchInput && document.activeElement === searchInput) {
                searchInput.value = '';
                if (window.dashboard && window.dashboard.filterAccounts) {
                    window.dashboard.filterAccounts('');
                }
                searchInput.blur();
            }
        }, 'Clear search / Close dialogs');

        // Help
        this.register('?', () => {
            if (!this.isInputFocused()) {
                this.toggleHelp();
            }
        }, 'Show keyboard shortcuts');
    }

    register(key, callback, description = '') {
        const normalizedKey = this.normalizeKey(key);
        this.shortcuts.set(normalizedKey, { callback, description, key });
    }

    normalizeKey(key) {
        return key.toLowerCase().replace(/\s+/g, '');
    }

    handleKeyPress(e) {
        const key = this.getKeyString(e);
        const normalizedKey = this.normalizeKey(key);
        
        const shortcut = this.shortcuts.get(normalizedKey);
        if (shortcut) {
            // Check if we should ignore (e.g., when typing in input)
            if (this.shouldIgnoreShortcut(e)) {
                return;
            }

            e.preventDefault();
            shortcut.callback(e);
        }
    }

    getKeyString(e) {
        if (e.key === 'Escape') return 'Escape';
        if (e.key === 'Enter') return 'Enter';
        if (e.key === 'Tab') return 'Tab';
        if (e.ctrlKey || e.metaKey) {
            const modifier = e.ctrlKey ? 'Ctrl' : 'Cmd';
            return `${modifier}+${e.key}`;
        }
        return e.key;
    }

    shouldIgnoreShortcut(e) {
        // Don't trigger shortcuts when typing in inputs, textareas, or contenteditable
        const target = e.target;
        const tagName = target.tagName.toLowerCase();
        
        if (tagName === 'input' && target.type !== 'checkbox' && target.type !== 'radio') {
            return true;
        }
        if (tagName === 'textarea') {
            return true;
        }
        if (target.isContentEditable) {
            return true;
        }
        
        return false;
    }

    isInputFocused() {
        const activeElement = document.activeElement;
        if (!activeElement) return false;
        
        const tagName = activeElement.tagName.toLowerCase();
        return (tagName === 'input' || tagName === 'textarea' || activeElement.isContentEditable);
    }

    toggleHelp() {
        if (this.helpVisible) {
            this.hideHelp();
        } else {
            this.showHelp();
        }
    }

    showHelp() {
        const shortcuts = Array.from(this.shortcuts.entries())
            .map(([key, data]) => ({ key: data.key, description: data.description }))
            .filter(s => s.description);

        const helpHtml = `
            <div class="keyboard-shortcuts-help">
                <div class="help-header">
                    <h3>Keyboard Shortcuts</h3>
                    <button class="help-close" onclick="keyboardShortcuts.hideHelp()">×</button>
                </div>
                <div class="help-content">
                    ${shortcuts.map(s => `
                        <div class="help-item">
                            <kbd>${this.formatKey(s.key)}</kbd>
                            <span>${s.description}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;

        const container = document.createElement('div');
        container.id = 'keyboard-shortcuts-overlay';
        container.className = 'keyboard-shortcuts-overlay';
        container.innerHTML = helpHtml;
        document.body.appendChild(container);

        // Close on escape
        const handleEscape = (e) => {
            if (e.key === 'Escape') {
                this.hideHelp();
                document.removeEventListener('keydown', handleEscape);
            }
        };
        document.addEventListener('keydown', handleEscape);

        // Close on overlay click
        container.addEventListener('click', (e) => {
            if (e.target === container) {
                this.hideHelp();
            }
        });

        this.helpVisible = true;
    }

    hideHelp() {
        const overlay = document.getElementById('keyboard-shortcuts-overlay');
        if (overlay) {
            overlay.remove();
        }
        this.helpVisible = false;
    }

    formatKey(key) {
        if (key.includes('+')) {
            const parts = key.split('+');
            return parts.map(p => `<kbd>${p}</kbd>`).join(' + ');
        }
        return `<kbd>${key}</kbd>`;
    }
}

// Initialize global keyboard shortcuts
const keyboardShortcuts = new KeyboardShortcuts();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = KeyboardShortcuts;
}

