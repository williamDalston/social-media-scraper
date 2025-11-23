/**
 * Frontend performance monitoring for production.
 */
class FrontendPerformanceMonitor {
    constructor() {
        this.metrics = {
            pageLoad: null,
            apiCalls: [],
            renderTimes: [],
            errors: []
        };
        this.init();
    }

    init() {
        // Monitor page load
        if (document.readyState === 'complete') {
            this.recordPageLoad();
        } else {
            window.addEventListener('load', () => this.recordPageLoad());
        }

        // Monitor API calls
        this.monitorAPICalls();

        // Monitor errors
        this.monitorErrors();

        // Monitor render performance
        this.monitorRenderPerformance();
    }

    recordPageLoad() {
        const perfData = window.performance.timing;
        const loadTime = perfData.loadEventEnd - perfData.navigationStart;
        const domContentLoaded = perfData.domContentLoadedEventEnd - perfData.navigationStart;
        const firstPaint = perfData.responseEnd - perfData.navigationStart;

        this.metrics.pageLoad = {
            loadTime,
            domContentLoaded,
            firstPaint,
            timestamp: new Date().toISOString()
        };

        // Send to backend if available
        this.sendMetrics();
    }

    monitorAPICalls() {
        const originalFetch = window.fetch;
        const self = this;

        window.fetch = function(...args) {
            const startTime = performance.now();
            const url = args[0];

            return originalFetch.apply(this, args)
                .then(response => {
                    const duration = performance.now() - startTime;
                    self.metrics.apiCalls.push({
                        url,
                        duration,
                        status: response.status,
                        timestamp: new Date().toISOString()
                    });
                    return response;
                })
                .catch(error => {
                    const duration = performance.now() - startTime;
                    self.metrics.apiCalls.push({
                        url,
                        duration,
                        error: error.message,
                        timestamp: new Date().toISOString()
                    });
                    throw error;
                });
        };
    }

    monitorErrors() {
        window.addEventListener('error', (event) => {
            this.metrics.errors.push({
                message: event.message,
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno,
                timestamp: new Date().toISOString()
            });
        });

        window.addEventListener('unhandledrejection', (event) => {
            this.metrics.errors.push({
                message: 'Unhandled Promise Rejection',
                reason: event.reason,
                timestamp: new Date().toISOString()
            });
        });
    }

    monitorRenderPerformance() {
        if ('PerformanceObserver' in window) {
            try {
                const observer = new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        if (entry.entryType === 'measure') {
                            this.metrics.renderTimes.push({
                                name: entry.name,
                                duration: entry.duration,
                                timestamp: new Date().toISOString()
                            });
                        }
                    }
                });
                observer.observe({ entryTypes: ['measure'] });
            } catch (e) {
                console.debug('PerformanceObserver not supported');
            }
        }
    }

    sendMetrics() {
        // Send metrics to backend periodically
        if (this.metrics.pageLoad) {
            fetch('/api/performance/frontend', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    pageLoad: this.metrics.pageLoad,
                    apiCalls: this.metrics.apiCalls.slice(-10), // Last 10
                    errors: this.metrics.errors.slice(-5) // Last 5
                })
            }).catch(() => {
                // Silently fail - metrics are optional
            });
        }
    }

    getStats() {
        const apiCalls = this.metrics.apiCalls;
        const avgApiTime = apiCalls.length > 0
            ? apiCalls.reduce((sum, call) => sum + call.duration, 0) / apiCalls.length
            : 0;

        return {
            pageLoad: this.metrics.pageLoad,
            apiCalls: {
                total: apiCalls.length,
                avgDuration: avgApiTime,
                errors: apiCalls.filter(c => c.error).length
            },
            errors: this.metrics.errors.length,
            timestamp: new Date().toISOString()
        };
    }
}

// Initialize global monitor
window.frontendPerformanceMonitor = new FrontendPerformanceMonitor();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FrontendPerformanceMonitor;
}

