"""
Continuous monitoring system for background health checks and error detection.
Runs periodic checks and sends alerts when issues are detected.
"""
import os
import time
import logging
import threading
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

from config.system_validation import SystemValidator
from config.pipeline_checks import PipelineValidator
from config.health_checks import run_health_checks, get_overall_health
from config.error_detection import get_error_summary, ErrorDetector
from config.alerting_rules import check_alerts, AlertRule

logger = logging.getLogger(__name__)


class MonitorStatus(Enum):
    """Monitor status."""
    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class MonitorCheck:
    """A monitoring check."""
    name: str
    check_function: Callable
    interval_seconds: int
    last_run: Optional[datetime] = None
    last_result: Optional[Dict[str, Any]] = None
    enabled: bool = True
    failure_count: int = 0
    consecutive_failures: int = 0


class ContinuousMonitor:
    """Continuous monitoring system."""
    
    def __init__(self, check_interval: int = 300):
        """
        Initialize continuous monitor.
        
        Args:
            check_interval: Interval between checks in seconds (default: 5 minutes)
        """
        self.check_interval = check_interval
        self.status = MonitorStatus.STOPPED
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.checks: List[MonitorCheck] = []
        self.alert_callbacks: List[Callable] = []
        
        # Register default checks
        self._register_default_checks()
    
    def _register_default_checks(self):
        """Register default monitoring checks."""
        # System validation check (every 30 minutes)
        self.add_check(
            name="system_validation",
            check_function=self._check_system_validation,
            interval_seconds=1800
        )
        
        # Pipeline validation check (every 30 minutes)
        self.add_check(
            name="pipeline_validation",
            check_function=self._check_pipeline_validation,
            interval_seconds=1800
        )
        
        # Health checks (every 5 minutes)
        self.add_check(
            name="health_checks",
            check_function=self._check_health,
            interval_seconds=300
        )
        
        # Error summary check (every 5 minutes)
        self.add_check(
            name="error_summary",
            check_function=self._check_errors,
            interval_seconds=300
        )
        
        # Alert rules check (every 5 minutes)
        self.add_check(
            name="alert_rules",
            check_function=self._check_alert_rules,
            interval_seconds=300
        )
    
    def add_check(self, name: str, check_function: Callable, 
                  interval_seconds: int, enabled: bool = True):
        """
        Add a monitoring check.
        
        Args:
            name: Check name
            check_function: Function to run for the check
            interval_seconds: Interval between checks
            enabled: Whether check is enabled
        """
        check = MonitorCheck(
            name=name,
            check_function=check_function,
            interval_seconds=interval_seconds,
            enabled=enabled
        )
        self.checks.append(check)
        logger.info(f"Added monitoring check: {name} (interval: {interval_seconds}s)")
    
    def add_alert_callback(self, callback: Callable):
        """
        Add alert callback function.
        
        Args:
            callback: Function to call when alerts are triggered
                      Should accept (alert_type, message, details) parameters
        """
        self.alert_callbacks.append(callback)
        logger.info("Added alert callback")
    
    def start(self):
        """Start continuous monitoring."""
        if self.status == MonitorStatus.RUNNING:
            logger.warning("Monitor is already running")
            return
        
        self.status = MonitorStatus.RUNNING
        self.stop_event.clear()
        
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="ContinuousMonitor"
        )
        self.monitor_thread.start()
        logger.info("Continuous monitoring started")
    
    def stop(self):
        """Stop continuous monitoring."""
        if self.status == MonitorStatus.STOPPED:
            return
        
        self.status = MonitorStatus.STOPPED
        self.stop_event.set()
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=10)
        
        logger.info("Continuous monitoring stopped")
    
    def pause(self):
        """Pause continuous monitoring."""
        self.status = MonitorStatus.PAUSED
        logger.info("Continuous monitoring paused")
    
    def resume(self):
        """Resume continuous monitoring."""
        if self.status == MonitorStatus.PAUSED:
            self.status = MonitorStatus.RUNNING
            logger.info("Continuous monitoring resumed")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        logger.info("Monitoring loop started")
        
        while not self.stop_event.is_set() and self.status == MonitorStatus.RUNNING:
            try:
                current_time = datetime.utcnow()
                
                # Run checks that are due
                for check in self.checks:
                    if not check.enabled:
                        continue
                    
                    if check.last_run is None or \
                       (current_time - check.last_run).total_seconds() >= check.interval_seconds:
                        try:
                            result = check.check_function()
                            check.last_result = result
                            check.last_run = current_time
                            
                            # Check if result indicates failure
                            if result and not result.get('success', True):
                                check.consecutive_failures += 1
                                check.failure_count += 1
                                
                                # Trigger alert if consecutive failures exceed threshold
                                if check.consecutive_failures >= 3:
                                    self._trigger_alert(
                                        alert_type=check.name,
                                        message=f"Check '{check.name}' has failed {check.consecutive_failures} times consecutively",
                                        details=result
                                    )
                            else:
                                check.consecutive_failures = 0
                                
                        except Exception as e:
                            logger.exception(f"Error running check {check.name}")
                            check.consecutive_failures += 1
                            check.failure_count += 1
                            
                            if check.consecutive_failures >= 3:
                                self._trigger_alert(
                                    alert_type=check.name,
                                    message=f"Check '{check.name}' error: {str(e)}",
                                    details={'error': str(e)}
                                )
                
                # Sleep until next check interval
                self.stop_event.wait(self.check_interval)
                
            except Exception as e:
                logger.exception("Error in monitoring loop")
                self.status = MonitorStatus.ERROR
                time.sleep(60)  # Wait before retrying
    
    def _check_system_validation(self) -> Dict[str, Any]:
        """Check system validation."""
        try:
            validator = SystemValidator()
            all_passed, results = validator.validate_all(skip_optional=False)
            summary = validator.get_summary()
            
            return {
                'success': all_passed,
                'summary': summary,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.exception("System validation check failed")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _check_pipeline_validation(self) -> Dict[str, Any]:
        """Check pipeline validation."""
        try:
            validator = PipelineValidator()
            all_passed, results = validator.validate_all()
            summary = validator.get_summary()
            
            return {
                'success': all_passed,
                'summary': summary,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.exception("Pipeline validation check failed")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _check_health(self) -> Dict[str, Any]:
        """Check system health."""
        try:
            db_path = os.getenv('DATABASE_PATH', 'social_media.db')
            results = run_health_checks(
                db_path=db_path,
                include_optional=True,
                use_cache=False
            )
            overall_health = get_overall_health(results)
            
            unhealthy_checks = [
                name for name, result in results.items()
                if result.status == 'unhealthy'
            ]
            
            return {
                'success': overall_health != 'unhealthy',
                'overall_health': overall_health,
                'unhealthy_checks': unhealthy_checks,
                'checks': {name: result.to_dict() for name, result in results.items()},
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.exception("Health check failed")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _check_errors(self) -> Dict[str, Any]:
        """Check error summary."""
        try:
            summary = get_error_summary(timedelta(hours=1))
            
            critical_errors = summary.get('by_severity', {}).get('critical', 0)
            high_errors = summary.get('by_severity', {}).get('high', 0)
            
            return {
                'success': critical_errors == 0 and high_errors < 10,
                'summary': summary,
                'critical_errors': critical_errors,
                'high_errors': high_errors,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.exception("Error summary check failed")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _check_alert_rules(self) -> Dict[str, Any]:
        """Check alert rules."""
        try:
            alerts = check_alerts()
            
            critical_alerts = [a for a in alerts if a.get('severity') == 'critical']
            high_alerts = [a for a in alerts if a.get('severity') == 'high']
            
            return {
                'success': len(critical_alerts) == 0 and len(high_alerts) < 5,
                'alerts': alerts,
                'critical_count': len(critical_alerts),
                'high_count': len(high_alerts),
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.exception("Alert rules check failed")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _trigger_alert(self, alert_type: str, message: str, details: Dict[str, Any]):
        """Trigger alert callbacks."""
        logger.warning(f"Alert triggered: {alert_type} - {message}")
        
        for callback in self.alert_callbacks:
            try:
                callback(alert_type, message, details)
            except Exception as e:
                logger.exception(f"Error in alert callback: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get monitor status."""
        return {
            'status': self.status.value,
            'check_interval': self.check_interval,
            'checks': [
                {
                    'name': check.name,
                    'enabled': check.enabled,
                    'interval_seconds': check.interval_seconds,
                    'last_run': check.last_run.isoformat() if check.last_run else None,
                    'failure_count': check.failure_count,
                    'consecutive_failures': check.consecutive_failures,
                    'last_result': check.last_result
                }
                for check in self.checks
            ],
            'timestamp': datetime.utcnow().isoformat()
        }


# Global monitor instance
_monitor: Optional[ContinuousMonitor] = None


def get_monitor() -> ContinuousMonitor:
    """Get or create global monitor instance."""
    global _monitor
    if _monitor is None:
        check_interval = int(os.getenv('MONITOR_CHECK_INTERVAL', 300))
        _monitor = ContinuousMonitor(check_interval=check_interval)
    return _monitor


def start_monitoring():
    """Start continuous monitoring."""
    monitor = get_monitor()
    monitor.start()


def stop_monitoring():
    """Stop continuous monitoring."""
    monitor = get_monitor()
    monitor.stop()

