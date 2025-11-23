/**
 * Progress Bar Component for Scraper Jobs
 * Provides real-time progress updates with speed metrics
 */

class ProgressBar {
    constructor(containerId = 'progressBarContainer') {
        this.container = document.getElementById(containerId);
        this.progressBarFill = document.getElementById('progressBarFill');
        this.progressText = document.getElementById('progressText');
        this.progressSpeed = document.getElementById('progressSpeed');
        this.progressTime = document.getElementById('progressTime');
        this.progressETA = document.getElementById('progressETA');
        this.progressMessage = document.getElementById('progressMessage');
        this.cancelBtn = document.getElementById('cancelScraperBtn');
        
        this.currentJobId = null;
        this.pollInterval = null;
        this.startTime = null;
        
        if (this.cancelBtn) {
            this.cancelBtn.addEventListener('click', () => this.cancel());
        }
    }
    
    show(jobId) {
        if (!this.container) return;
        
        this.currentJobId = jobId;
        this.startTime = Date.now();
        this.container.style.display = 'flex';
        this.update(0, 'Initializing...', 0, 0, 0);
        
        // Start polling for progress updates
        this.startPolling();
    }
    
    hide() {
        if (!this.container) return;
        
        this.stopPolling();
        this.container.style.display = 'none';
        this.currentJobId = null;
        this.startTime = null;
    }
    
    update(progress, message, speed, elapsed, eta) {
        if (!this.container || this.container.style.display === 'none') return;
        
        // Update progress bar
        if (this.progressBarFill) {
            this.progressBarFill.style.width = `${Math.min(100, Math.max(0, progress))}%`;
        }
        
        // Update text
        if (this.progressText) {
            this.progressText.textContent = `${Math.round(progress)}%`;
        }
        
        if (this.progressSpeed) {
            this.progressSpeed.textContent = `${speed.toFixed(2)} accounts/sec`;
        }
        
        if (this.progressTime) {
            const minutes = Math.floor(elapsed / 60);
            const seconds = Math.floor(elapsed % 60);
            this.progressTime.textContent = `Elapsed: ${minutes}m ${seconds}s`;
        }
        
        if (this.progressETA) {
            if (eta && eta > 0) {
                const minutes = Math.floor(eta / 60);
                const seconds = Math.floor(eta % 60);
                this.progressETA.textContent = `ETA: ${minutes}m ${seconds}s`;
            } else {
                this.progressETA.textContent = 'ETA: --';
            }
        }
        
        if (this.progressMessage) {
            this.progressMessage.textContent = message || 'Processing...';
        }
    }
    
    startPolling() {
        if (!this.currentJobId) return;
        
        // Poll every 500ms for real-time updates
        this.pollInterval = setInterval(async () => {
            try {
                await this.fetchProgress();
            } catch (error) {
                console.error('Error fetching progress:', error);
            }
        }, 500);
        
        // Initial fetch
        this.fetchProgress();
    }
    
    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }
    
    async fetchProgress() {
        if (!this.currentJobId) return;
        
        try {
            // Try to use the v1 API endpoint first
            let response;
            try {
                response = await fetch(`/api/v1/jobs/${this.currentJobId}`, {
                    headers: {
                        'Authorization': `Bearer ${this.getAuthToken()}`
                    }
                });
            } catch (e) {
                // If v1 endpoint fails, try fallback
                response = null;
            }
            
            if (response && response.ok) {
                const data = await response.json();
                this.updateFromJobData(data);
                return;
            }
            
            // Fallback: Try to check Celery task status directly
            try {
                const taskResponse = await fetch(`/api/jobs/${this.currentJobId}/status`);
                if (taskResponse.ok) {
                    const taskData = await taskResponse.json();
                    this.updateFromTaskData(taskData);
                    return;
                }
            } catch (e) {
                // Ignore fallback errors
            }
            
            // If all else fails, estimate progress from elapsed time
            if (this.startTime) {
                const elapsed = (Date.now() - this.startTime) / 1000;
                // Estimate: assume 2-5 seconds per account on average
                const estimatedProgress = Math.min(95, (elapsed / 5) * 10); // Rough estimate
                this.update(estimatedProgress, 'Processing...', 0, elapsed, 0);
            }
            
        } catch (error) {
            console.error('Error fetching progress:', error);
            // On error, hide progress bar after a delay
            if (this.startTime && (Date.now() - this.startTime) > 300000) { // 5 minutes
                this.hide();
            }
        }
    }
    
    updateFromJobData(jobData) {
        const progress = jobData.progress || 0;
        let message = 'Processing...';
        let speed = 0;
        let elapsed = 0;
        let eta = 0;
        
        // Parse result if it contains progress info
        let result = null;
        if (jobData.result) {
            try {
                result = typeof jobData.result === 'string' 
                    ? JSON.parse(jobData.result) 
                    : jobData.result;
                
                if (result.message) {
                    message = result.message;
                }
                
                if (result.speed !== undefined) {
                    speed = result.speed;
                }
                
                if (result.elapsed !== undefined) {
                    elapsed = result.elapsed;
                }
                
                if (result.eta !== undefined) {
                    eta = result.eta;
                }
            } catch (e) {
                // Ignore parse errors
            }
        }
        
        // Calculate elapsed time from job timestamps
        if (jobData.started_at && !elapsed) {
            const started = new Date(jobData.started_at);
            elapsed = (Date.now() - started.getTime()) / 1000;
        }
        
        // Calculate speed if we have processed/total
        if (result && result.processed && result.total && elapsed > 0) {
            speed = result.processed / elapsed;
            if (speed > 0 && result.total > result.processed) {
                eta = (result.total - result.processed) / speed;
            }
        }
        
        this.update(progress, message, speed, elapsed, eta);
        
        // Hide if completed or failed
        if (jobData.status === 'completed' || jobData.status === 'failed') {
            setTimeout(() => {
                this.hide();
                if (jobData.status === 'completed' && window.toast) {
                    toast.success('Scraper completed successfully!');
                } else if (jobData.status === 'failed' && window.toast) {
                    toast.error(`Scraper failed: ${jobData.error_message || 'Unknown error'}`);
                }
            }, 2000);
        }
    }
    
    updateFromTaskData(taskData) {
        // Handle Celery task state format
        if (taskData.state === 'PROGRESS' && taskData.info) {
            const info = taskData.info;
            const progress = info.progress || 0;
            const message = info.message || 'Processing...';
            const speed = info.speed || 0;
            const elapsed = info.elapsed || 0;
            const eta = info.eta || 0;
            
            this.update(progress, message, speed, elapsed, eta);
        } else if (taskData.state === 'SUCCESS') {
            this.update(100, 'Completed!', 0, 0, 0);
            setTimeout(() => this.hide(), 2000);
        } else if (taskData.state === 'FAILURE') {
            this.update(0, 'Failed', 0, 0, 0);
            setTimeout(() => this.hide(), 2000);
        }
    }
    
    async cancel() {
        if (!this.currentJobId) return;
        
        if (window.modal) {
            const confirmed = await modal.confirm({
                title: 'Cancel Scraper',
                message: 'Are you sure you want to cancel the scraper?',
                confirmText: 'Cancel',
                cancelText: 'Keep Running'
            });
            
            if (!confirmed) return;
        }
        
        try {
            // Try to cancel the job via API
            const response = await fetch(`/api/v1/jobs/${this.currentJobId}/cancel`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`,
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                if (window.toast) {
                    toast.info('Scraper cancellation requested...');
                }
                this.hide();
            } else {
                if (window.toast) {
                    toast.error('Failed to cancel scraper');
                }
            }
        } catch (error) {
            console.error('Error canceling scraper:', error);
            if (window.toast) {
                toast.error('Error canceling scraper');
            }
        }
    }
    
    getAuthToken() {
        // Try to get auth token from localStorage or cookie
        try {
            return localStorage.getItem('auth_token') || '';
        } catch (e) {
            return '';
        }
    }
}

// Create global instance
window.progressBar = new ProgressBar();

