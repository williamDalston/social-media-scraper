/**
 * Modal Dialog System
 * Provides confirmation dialogs and modal windows
 */

class ModalManager {
    constructor() {
        this.container = null;
        this.init();
    }

    init() {
        // Create modal container if it doesn't exist
        if (!document.getElementById('modal-container')) {
            this.container = document.createElement('div');
            this.container.id = 'modal-container';
            this.container.className = 'modal-container';
            document.body.appendChild(this.container);
        } else {
            this.container = document.getElementById('modal-container');
        }
    }

    confirm(options) {
        return new Promise((resolve) => {
            const {
                title = 'Confirm Action',
                message = 'Are you sure you want to proceed?',
                confirmText = 'Confirm',
                cancelText = 'Cancel',
                confirmClass = 'btn-danger',
                onConfirm,
                onCancel
            } = options;

            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.setAttribute('role', 'dialog');
            modal.setAttribute('aria-modal', 'true');
            modal.setAttribute('aria-labelledby', 'modal-title');
            
            modal.innerHTML = `
                <div class="modal-dialog">
                    <div class="modal-header">
                        <h2 id="modal-title" class="modal-title">${this.escapeHtml(title)}</h2>
                        <button class="modal-close" aria-label="Close dialog" onclick="this.closest('.modal-overlay').remove()">
                            <span aria-hidden="true">×</span>
                        </button>
                    </div>
                    <div class="modal-body">
                        <p>${this.escapeHtml(message)}</p>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary modal-cancel">${this.escapeHtml(cancelText)}</button>
                        <button class="btn ${confirmClass} modal-confirm">${this.escapeHtml(confirmText)}</button>
                    </div>
                </div>
            `;

            this.container.appendChild(modal);

            // Focus management
            const firstButton = modal.querySelector('.modal-cancel');
            const confirmButton = modal.querySelector('.modal-confirm');
            firstButton.focus();

            // Close on overlay click
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.close(modal);
                    resolve(false);
                    if (onCancel) onCancel();
                }
            });

            // Close on escape key
            const handleEscape = (e) => {
                if (e.key === 'Escape') {
                    this.close(modal);
                    resolve(false);
                    if (onCancel) onCancel();
                    document.removeEventListener('keydown', handleEscape);
                }
            };
            document.addEventListener('keydown', handleEscape);

            // Cancel button
            modal.querySelector('.modal-cancel').addEventListener('click', () => {
                this.close(modal);
                resolve(false);
                if (onCancel) onCancel();
                document.removeEventListener('keydown', handleEscape);
            });

            // Confirm button
            modal.querySelector('.modal-confirm').addEventListener('click', () => {
                this.close(modal);
                resolve(true);
                if (onConfirm) onConfirm();
                document.removeEventListener('keydown', handleEscape);
            });

            // Animate in
            requestAnimationFrame(() => {
                modal.classList.add('modal-show');
            });
        });
    }

    alert(options) {
        return new Promise((resolve) => {
            const {
                title = 'Alert',
                message = '',
                buttonText = 'OK',
                onClose
            } = options;

            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.setAttribute('role', 'alertdialog');
            modal.setAttribute('aria-modal', 'true');
            modal.setAttribute('aria-labelledby', 'modal-title');
            
            modal.innerHTML = `
                <div class="modal-dialog">
                    <div class="modal-header">
                        <h2 id="modal-title" class="modal-title">${this.escapeHtml(title)}</h2>
                        <button class="modal-close" aria-label="Close dialog" onclick="this.closest('.modal-overlay').remove()">
                            <span aria-hidden="true">×</span>
                        </button>
                    </div>
                    <div class="modal-body">
                        <p>${this.escapeHtml(message)}</p>
                    </div>
                    <div class="modal-footer">
                        <button class="btn modal-ok">${this.escapeHtml(buttonText)}</button>
                    </div>
                </div>
            `;

            this.container.appendChild(modal);

            const okButton = modal.querySelector('.modal-ok');
            okButton.focus();

            const close = () => {
                this.close(modal);
                resolve();
                if (onClose) onClose();
            };

            okButton.addEventListener('click', close);
            modal.querySelector('.modal-close').addEventListener('click', close);

            // Close on escape
            const handleEscape = (e) => {
                if (e.key === 'Escape') {
                    close();
                    document.removeEventListener('keydown', handleEscape);
                }
            };
            document.addEventListener('keydown', handleEscape);

            requestAnimationFrame(() => {
                modal.classList.add('modal-show');
            });
        });
    }

    close(modal) {
        modal.classList.remove('modal-show');
        setTimeout(() => {
            if (modal.parentElement) {
                modal.remove();
            }
        }, 300);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize global modal manager
const modal = new ModalManager();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ModalManager;
}

