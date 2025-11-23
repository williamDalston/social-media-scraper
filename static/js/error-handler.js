/**
 * Error Handler with Recovery Options
 * Provides user-friendly error messages and recovery actions
 */

class ErrorHandler {
    constructor() {
        this.errorTypes = {
            NETWORK: 'network',
            AUTH: 'authentication',
            PERMISSION: 'permission',
            VALIDATION: 'validation',
            SERVER: 'server',
            UNKNOWN: 'unknown'
        };
    }

    handleError(error, context = {}) {
        const errorInfo = this.parseError(error);
        const userMessage = this.getUserFriendlyMessage(errorInfo);
        const recoveryOptions = this.getRecoveryOptions(errorInfo, context);

        // Show error with recovery options
        if (window.toast) {
            const errorToast = toast.error(userMessage, 0); // Don't auto-dismiss
            
            // Add recovery button if options available
            if (recoveryOptions.length > 0) {
                const toastElement = errorToast;
                const actionsDiv = document.createElement('div');
                actionsDiv.className = 'error-recovery-actions';
                actionsDiv.style.marginTop = '8px';
                actionsDiv.style.display = 'flex';
                actionsDiv.style.gap = '8px';
                actionsDiv.style.flexWrap = 'wrap';

                recoveryOptions.forEach(option => {
                    const btn = document.createElement('button');
                    btn.className = 'btn';
                    btn.style.fontSize = '12px';
                    btn.style.padding = '6px 12px';
                    btn.textContent = option.label;
                    btn.onclick = () => {
                        option.action();
                        toast.remove(errorToast);
                    };
                    actionsDiv.appendChild(btn);
                });

                toastElement.querySelector('.toast-content').appendChild(actionsDiv);
            }
        }

        // Log error for debugging
        console.error('Error in context:', context, errorInfo);

        return { errorInfo, userMessage, recoveryOptions };
    }

    parseError(error) {
        if (typeof error === 'string') {
            return {
                type: this.errorTypes.UNKNOWN,
                message: error,
                originalError: error
            };
        }

        // Network errors
        if (error.message && (
            error.message.includes('Failed to fetch') ||
            error.message.includes('NetworkError') ||
            error.message.includes('network')
        )) {
            return {
                type: this.errorTypes.NETWORK,
                message: 'Network connection failed',
                originalError: error
            };
        }

        // HTTP status errors
        if (error.status || error.response) {
            const status = error.status || error.response?.status;
            const message = error.message || error.response?.data?.error || 'Request failed';

            if (status === 401) {
                return {
                    type: this.errorTypes.AUTH,
                    message: 'Authentication required',
                    status,
                    originalError: error
                };
            }

            if (status === 403) {
                return {
                    type: this.errorTypes.PERMISSION,
                    message: 'You don\'t have permission to perform this action',
                    status,
                    originalError: error
                };
            }

            if (status === 400) {
                return {
                    type: this.errorTypes.VALIDATION,
                    message: message,
                    status,
                    originalError: error
                };
            }

            if (status >= 500) {
                return {
                    type: this.errorTypes.SERVER,
                    message: 'Server error occurred',
                    status,
                    originalError: error
                };
            }

            return {
                type: this.errorTypes.UNKNOWN,
                message: message,
                status,
                originalError: error
            };
        }

        return {
            type: this.errorTypes.UNKNOWN,
            message: error.message || 'An unexpected error occurred',
            originalError: error
        };
    }

    getUserFriendlyMessage(errorInfo) {
        const messages = {
            [this.errorTypes.NETWORK]: 'Unable to connect to the server. Please check your internet connection.',
            [this.errorTypes.AUTH]: 'Your session has expired. Please log in again.',
            [this.errorTypes.PERMISSION]: 'You don\'t have permission to perform this action.',
            [this.errorTypes.VALIDATION]: errorInfo.message || 'Please check your input and try again.',
            [this.errorTypes.SERVER]: 'The server encountered an error. Please try again later.',
            [this.errorTypes.UNKNOWN]: errorInfo.message || 'An unexpected error occurred.'
        };

        return messages[errorInfo.type] || messages[this.errorTypes.UNKNOWN];
    }

    getRecoveryOptions(errorInfo, context) {
        const options = [];

        // Network errors - retry option
        if (errorInfo.type === this.errorTypes.NETWORK && context.retryAction) {
            options.push({
                label: 'Retry',
                action: context.retryAction
            });
        }

        // Auth errors - redirect to login
        if (errorInfo.type === this.errorTypes.AUTH) {
            options.push({
                label: 'Go to Login',
                action: () => {
                    window.location.href = '/api/auth/login';
                }
            });
        }

        // Permission errors - contact admin
        if (errorInfo.type === this.errorTypes.PERMISSION) {
            options.push({
                label: 'Contact Admin',
                action: () => {
                    // Could open a contact form or email
                    toast.info('Please contact your administrator for access.');
                }
            });
        }

        // Validation errors - show details
        if (errorInfo.type === this.errorTypes.VALIDATION && errorInfo.originalError?.response?.data?.details) {
            options.push({
                label: 'View Details',
                action: () => {
                    const details = errorInfo.originalError.response.data.details;
                    toast.info(JSON.stringify(details, null, 2), 10000);
                }
            });
        }

        // Server errors - retry
        if (errorInfo.type === this.errorTypes.SERVER && context.retryAction) {
            options.push({
                label: 'Retry',
                action: context.retryAction
            });
        }

        // Generic retry for any error if retry action provided
        if (context.retryAction && options.length === 0) {
            options.push({
                label: 'Retry',
                action: context.retryAction
            });
        }

        return options;
    }
}

// Initialize global error handler
const errorHandler = new ErrorHandler();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ErrorHandler;
}

