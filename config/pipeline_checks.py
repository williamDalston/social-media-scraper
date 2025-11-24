"""
Pipeline validation system for checking all components of the data pipeline.
Validates scrapers, tasks, database operations, and data flow.
"""
import os
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """Pipeline stages."""

    INPUT = "input"
    SCRAPING = "scraping"
    PROCESSING = "processing"
    STORAGE = "storage"
    OUTPUT = "output"
    MONITORING = "monitoring"


class CheckSeverity(Enum):
    """Severity levels for pipeline checks."""

    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class PipelineCheckResult:
    """Result of a pipeline check."""

    stage: PipelineStage
    check_name: str
    severity: CheckSeverity
    status: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    fix_suggestion: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "stage": self.stage.value,
            "check_name": self.check_name,
            "severity": self.severity.value,
            "status": self.status,
            "message": self.message,
            "details": self.details,
            "fix_suggestion": self.fix_suggestion,
            "timestamp": self.timestamp.isoformat(),
        }


class PipelineValidator:
    """Validates the entire data pipeline."""

    def __init__(self):
        self.results: List[PipelineCheckResult] = []

    def validate_all(self) -> Tuple[bool, List[PipelineCheckResult]]:
        """Run all pipeline checks."""
        self.results = []

        logger.info("Starting pipeline validation...")

        self._validate_input_stage()
        self._validate_scraping_stage()
        self._validate_processing_stage()
        self._validate_storage_stage()
        self._validate_output_stage()
        self._validate_monitoring_stage()

        critical_failures = [
            r
            for r in self.results
            if r.severity == CheckSeverity.CRITICAL and not r.status
        ]
        errors = [
            r
            for r in self.results
            if r.severity == CheckSeverity.ERROR and not r.status
        ]

        all_passed = len(critical_failures) == 0 and len(errors) == 0

        logger.info(
            f"Pipeline validation complete: {len(self.results)} checks, "
            f"{len(critical_failures)} critical failures, {len(errors)} errors"
        )

        return all_passed, self.results

    def _validate_input_stage(self):
        """Validate input stage (account data, CSV uploads, etc.)."""
        logger.debug("Validating input stage...")

        # Check account data file
        accounts_file = os.getenv("ACCOUNTS_FILE", "hhs_accounts.json")
        if os.path.exists(accounts_file):
            try:
                import json

                with open(accounts_file, "r") as f:
                    accounts = json.load(f)

                if isinstance(accounts, list) and len(accounts) > 0:
                    self.results.append(
                        PipelineCheckResult(
                            stage=PipelineStage.INPUT,
                            check_name="accounts_file",
                            severity=CheckSeverity.INFO,
                            status=True,
                            message=f"Accounts file contains {len(accounts)} accounts",
                            details={"file": accounts_file, "count": len(accounts)},
                        )
                    )
                else:
                    self.results.append(
                        PipelineCheckResult(
                            stage=PipelineStage.INPUT,
                            check_name="accounts_file",
                            severity=CheckSeverity.WARNING,
                            status=False,
                            message="Accounts file is empty or invalid",
                            details={"file": accounts_file},
                            fix_suggestion="Ensure accounts file contains valid account data",
                        )
                    )
            except Exception as e:
                self.results.append(
                    PipelineCheckResult(
                        stage=PipelineStage.INPUT,
                        check_name="accounts_file",
                        severity=CheckSeverity.ERROR,
                        status=False,
                        message=f"Cannot read accounts file: {str(e)}",
                        details={"file": accounts_file, "error": str(e)},
                        fix_suggestion="Check file format and permissions",
                    )
                )
        else:
            self.results.append(
                PipelineCheckResult(
                    stage=PipelineStage.INPUT,
                    check_name="accounts_file",
                    severity=CheckSeverity.WARNING,
                    status=False,
                    message=f"Accounts file not found: {accounts_file}",
                    details={"file": accounts_file},
                    fix_suggestion="Create accounts file or set ACCOUNTS_FILE environment variable",
                )
            )

        # Check CSV upload directory
        upload_dir = os.getenv("UPLOAD_DIRECTORY", "uploads")
        if not os.path.exists(upload_dir):
            try:
                os.makedirs(upload_dir, exist_ok=True)
                self.results.append(
                    PipelineCheckResult(
                        stage=PipelineStage.INPUT,
                        check_name="upload_directory",
                        severity=CheckSeverity.INFO,
                        status=True,
                        message=f"Upload directory created: {upload_dir}",
                        details={"directory": upload_dir},
                    )
                )
            except Exception as e:
                self.results.append(
                    PipelineCheckResult(
                        stage=PipelineStage.INPUT,
                        check_name="upload_directory",
                        severity=CheckSeverity.ERROR,
                        status=False,
                        message=f"Cannot create upload directory: {str(e)}",
                        details={"directory": upload_dir, "error": str(e)},
                        fix_suggestion=f"Ensure directory {upload_dir} can be created or set UPLOAD_DIRECTORY",
                    )
                )
        else:
            if os.access(upload_dir, os.R_OK | os.W_OK):
                self.results.append(
                    PipelineCheckResult(
                        stage=PipelineStage.INPUT,
                        check_name="upload_directory",
                        severity=CheckSeverity.INFO,
                        status=True,
                        message=f"Upload directory is accessible: {upload_dir}",
                        details={"directory": upload_dir},
                    )
                )
            else:
                self.results.append(
                    PipelineCheckResult(
                        stage=PipelineStage.INPUT,
                        check_name="upload_directory",
                        severity=CheckSeverity.ERROR,
                        status=False,
                        message=f"Upload directory is not writable: {upload_dir}",
                        details={"directory": upload_dir},
                        fix_suggestion=f"Fix permissions for {upload_dir}",
                    )
                )

    def _validate_scraping_stage(self):
        """Validate scraping stage (scrapers, retry logic, etc.)."""
        logger.debug("Validating scraping stage...")

        # Check scraper modules
        try:
            from scraper.scrapers import get_scraper

            scraper = get_scraper(mode="simulated")
            if scraper:
                self.results.append(
                    PipelineCheckResult(
                        stage=PipelineStage.SCRAPING,
                        check_name="scraper_import",
                        severity=CheckSeverity.INFO,
                        status=True,
                        message="Scraper modules are importable",
                        details={},
                    )
                )
            else:
                self.results.append(
                    PipelineCheckResult(
                        stage=PipelineStage.SCRAPING,
                        check_name="scraper_import",
                        severity=CheckSeverity.ERROR,
                        status=False,
                        message="Cannot get scraper instance",
                        details={},
                        fix_suggestion="Check scraper configuration",
                    )
                )
        except Exception as e:
            self.results.append(
                PipelineCheckResult(
                    stage=PipelineStage.SCRAPING,
                    check_name="scraper_import",
                    severity=CheckSeverity.CRITICAL,
                    status=False,
                    message=f"Cannot import scrapers: {str(e)}",
                    details={"error": str(e)},
                    fix_suggestion="Ensure scraper modules are properly installed",
                )
            )

        # Check platform scrapers
        try:
            from scraper.platforms.base_platform import BasePlatformScraper

            # Check if platform scrapers exist
            platforms = ["x", "instagram", "facebook", "linkedin", "youtube", "truth"]
            available_platforms = []

            for platform in platforms:
                try:
                    module_name = f"scraper.platforms.{platform}_scraper"
                    __import__(module_name)
                    available_platforms.append(platform)
                except ImportError:
                    pass

            if available_platforms:
                self.results.append(
                    PipelineCheckResult(
                        stage=PipelineStage.SCRAPING,
                        check_name="platform_scrapers",
                        severity=CheckSeverity.INFO,
                        status=True,
                        message=f"Platform scrapers available: {', '.join(available_platforms)}",
                        details={"platforms": available_platforms},
                    )
                )
            else:
                self.results.append(
                    PipelineCheckResult(
                        stage=PipelineStage.SCRAPING,
                        check_name="platform_scrapers",
                        severity=CheckSeverity.WARNING,
                        status=False,
                        message="No platform scrapers found",
                        details={},
                        fix_suggestion="Implement platform-specific scrapers",
                    )
                )
        except Exception as e:
            self.results.append(
                PipelineCheckResult(
                    stage=PipelineStage.SCRAPING,
                    check_name="platform_scrapers",
                    severity=CheckSeverity.WARNING,
                    status=False,
                    message=f"Platform scraper check failed: {str(e)}",
                    details={"error": str(e)},
                )
            )

        # Check retry logic
        try:
            from scraper.utils.retry import retry_with_backoff
            from scraper.utils.intelligent_retry import intelligent_retry

            self.results.append(
                PipelineCheckResult(
                    stage=PipelineStage.SCRAPING,
                    check_name="retry_logic",
                    severity=CheckSeverity.INFO,
                    status=True,
                    message="Retry logic modules are available",
                    details={},
                )
            )
        except ImportError:
            self.results.append(
                PipelineCheckResult(
                    stage=PipelineStage.SCRAPING,
                    check_name="retry_logic",
                    severity=CheckSeverity.WARNING,
                    status=False,
                    message="Retry logic modules not found",
                    details={},
                    fix_suggestion="Implement retry logic for robust scraping",
                )
            )

    def _validate_processing_stage(self):
        """Validate processing stage (data transformation, validation, etc.)."""
        logger.debug("Validating processing stage...")

        # Check data processing modules
        try:
            from scraper.schema import DimAccount, FactFollowersSnapshot

            self.results.append(
                PipelineCheckResult(
                    stage=PipelineStage.PROCESSING,
                    check_name="data_models",
                    severity=CheckSeverity.INFO,
                    status=True,
                    message="Data models are importable",
                    details={},
                )
            )
        except Exception as e:
            self.results.append(
                PipelineCheckResult(
                    stage=PipelineStage.PROCESSING,
                    check_name="data_models",
                    severity=CheckSeverity.CRITICAL,
                    status=False,
                    message=f"Cannot import data models: {str(e)}",
                    details={"error": str(e)},
                    fix_suggestion="Ensure database schema is properly defined",
                )
            )

        # Check data validation
        try:
            from api.validators import validate_account_data

            self.results.append(
                PipelineCheckResult(
                    stage=PipelineStage.PROCESSING,
                    check_name="data_validation",
                    severity=CheckSeverity.INFO,
                    status=True,
                    message="Data validation modules are available",
                    details={},
                )
            )
        except ImportError:
            self.results.append(
                PipelineCheckResult(
                    stage=PipelineStage.PROCESSING,
                    check_name="data_validation",
                    severity=CheckSeverity.WARNING,
                    status=False,
                    message="Data validation modules not found",
                    details={},
                    fix_suggestion="Implement data validation for quality assurance",
                )
            )

    def _validate_storage_stage(self):
        """Validate storage stage (database, caching, etc.)."""
        logger.debug("Validating storage stage...")

        # Database check (already done in system validation, but verify here)
        try:
            from scraper.schema import init_db
            from sqlalchemy import text, inspect

            db_path = os.getenv("DATABASE_PATH", "social_media.db")
            engine = init_db(db_path)

            with engine.connect() as conn:
                # Check table structure
                inspector = inspect(engine)
                tables = inspector.get_table_names()

                required_tables = ["dim_account", "fact_followers_snapshot"]
                missing = [t for t in required_tables if t not in tables]

                if missing:
                    self.results.append(
                        PipelineCheckResult(
                            stage=PipelineStage.STORAGE,
                            check_name="database_tables",
                            severity=CheckSeverity.ERROR,
                            status=False,
                            message=f"Missing tables: {', '.join(missing)}",
                            details={"missing_tables": missing},
                            fix_suggestion="Run database migrations",
                        )
                    )
                else:
                    # Check for data
                    result = conn.execute(text("SELECT COUNT(*) FROM dim_account"))
                    account_count = result.scalar()

                    self.results.append(
                        PipelineCheckResult(
                            stage=PipelineStage.STORAGE,
                            check_name="database_storage",
                            severity=CheckSeverity.INFO,
                            status=True,
                            message=f"Database storage is working ({account_count} accounts)",
                            details={"account_count": account_count, "tables": tables},
                        )
                    )
        except Exception as e:
            self.results.append(
                PipelineCheckResult(
                    stage=PipelineStage.STORAGE,
                    check_name="database_storage",
                    severity=CheckSeverity.CRITICAL,
                    status=False,
                    message=f"Database storage check failed: {str(e)}",
                    details={"error": str(e)},
                    fix_suggestion="Fix database connection and schema",
                )
            )

        # Cache check
        try:
            from cache.redis_client import cache

            test_key = "pipeline_check"
            test_value = "test"
            cache.set(test_key, test_value, timeout=5)
            retrieved = cache.get(test_key)
            cache.delete(test_key)

            if retrieved == test_value:
                self.results.append(
                    PipelineCheckResult(
                        stage=PipelineStage.STORAGE,
                        check_name="cache_storage",
                        severity=CheckSeverity.INFO,
                        status=True,
                        message="Cache storage is working",
                        details={},
                    )
                )
            else:
                self.results.append(
                    PipelineCheckResult(
                        stage=PipelineStage.STORAGE,
                        check_name="cache_storage",
                        severity=CheckSeverity.WARNING,
                        status=False,
                        message="Cache read/write test failed",
                        details={},
                        fix_suggestion="Check Redis configuration",
                    )
                )
        except Exception as e:
            self.results.append(
                PipelineCheckResult(
                    stage=PipelineStage.STORAGE,
                    check_name="cache_storage",
                    severity=CheckSeverity.WARNING,
                    status=False,
                    message=f"Cache is not available: {str(e)}",
                    details={"error": str(e)},
                    fix_suggestion="Cache is optional but recommended for performance",
                )
            )

    def _validate_output_stage(self):
        """Validate output stage (API endpoints, exports, etc.)."""
        logger.debug("Validating output stage...")

        # Check API modules
        try:
            from api.schemas import AccountSchema
            from api.errors import APIError

            self.results.append(
                PipelineCheckResult(
                    stage=PipelineStage.OUTPUT,
                    check_name="api_modules",
                    severity=CheckSeverity.INFO,
                    status=True,
                    message="API modules are importable",
                    details={},
                )
            )
        except ImportError as e:
            self.results.append(
                PipelineCheckResult(
                    stage=PipelineStage.OUTPUT,
                    check_name="api_modules",
                    severity=CheckSeverity.ERROR,
                    status=False,
                    message=f"Cannot import API modules: {str(e)}",
                    details={"error": str(e)},
                    fix_suggestion="Ensure API modules are properly installed",
                )
            )

        # Check export functionality
        try:
            import pandas as pd
            import csv

            self.results.append(
                PipelineCheckResult(
                    stage=PipelineStage.OUTPUT,
                    check_name="export_libraries",
                    severity=CheckSeverity.INFO,
                    status=True,
                    message="Export libraries (pandas, csv) are available",
                    details={},
                )
            )
        except ImportError as e:
            self.results.append(
                PipelineCheckResult(
                    stage=PipelineStage.OUTPUT,
                    check_name="export_libraries",
                    severity=CheckSeverity.ERROR,
                    status=False,
                    message=f"Export libraries not available: {str(e)}",
                    details={"error": str(e)},
                    fix_suggestion="Install required export libraries: pip install pandas",
                )
            )

    def _validate_monitoring_stage(self):
        """Validate monitoring stage (logging, metrics, alerts, etc.)."""
        logger.debug("Validating monitoring stage...")

        # Check logging
        try:
            from config.logging_config import setup_logging

            self.results.append(
                PipelineCheckResult(
                    stage=PipelineStage.MONITORING,
                    check_name="logging",
                    severity=CheckSeverity.INFO,
                    status=True,
                    message="Logging configuration is available",
                    details={},
                )
            )
        except Exception as e:
            self.results.append(
                PipelineCheckResult(
                    stage=PipelineStage.MONITORING,
                    check_name="logging",
                    severity=CheckSeverity.WARNING,
                    status=False,
                    message=f"Logging configuration check failed: {str(e)}",
                    details={"error": str(e)},
                )
            )

        # Check metrics
        try:
            from config.metrics_config import setup_metrics

            self.results.append(
                PipelineCheckResult(
                    stage=PipelineStage.MONITORING,
                    check_name="metrics",
                    severity=CheckSeverity.INFO,
                    status=True,
                    message="Metrics configuration is available",
                    details={},
                )
            )
        except Exception as e:
            self.results.append(
                PipelineCheckResult(
                    stage=PipelineStage.MONITORING,
                    check_name="metrics",
                    severity=CheckSeverity.WARNING,
                    status=False,
                    message=f"Metrics configuration check failed: {str(e)}",
                    details={"error": str(e)},
                )
            )

        # Check health checks
        try:
            from config.health_checks import run_health_checks

            self.results.append(
                PipelineCheckResult(
                    stage=PipelineStage.MONITORING,
                    check_name="health_checks",
                    severity=CheckSeverity.INFO,
                    status=True,
                    message="Health check system is available",
                    details={},
                )
            )
        except Exception as e:
            self.results.append(
                PipelineCheckResult(
                    stage=PipelineStage.MONITORING,
                    check_name="health_checks",
                    severity=CheckSeverity.WARNING,
                    status=False,
                    message=f"Health check system check failed: {str(e)}",
                    details={"error": str(e)},
                )
            )

    def get_summary(self) -> Dict[str, Any]:
        """Get validation summary."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status)
        failed = total - passed

        by_stage = {}
        for stage in PipelineStage:
            stage_results = [r for r in self.results if r.stage == stage]
            by_stage[stage.value] = {
                "total": len(stage_results),
                "passed": sum(1 for r in stage_results if r.status),
                "failed": sum(1 for r in stage_results if not r.status),
            }

        critical_failures = [
            r
            for r in self.results
            if r.severity == CheckSeverity.CRITICAL and not r.status
        ]
        errors = [
            r
            for r in self.results
            if r.severity == CheckSeverity.ERROR and not r.status
        ]

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "critical_failures": len(critical_failures),
            "errors": len(errors),
            "all_passed": len(critical_failures) == 0 and len(errors) == 0,
            "by_stage": by_stage,
            "results": [r.to_dict() for r in self.results],
        }


def validate_pipeline() -> Tuple[bool, Dict[str, Any]]:
    """
    Validate the entire pipeline.

    Returns:
        Tuple of (all_passed, summary)
    """
    validator = PipelineValidator()
    all_passed, results = validator.validate_all()
    summary = validator.get_summary()
    return all_passed, summary
