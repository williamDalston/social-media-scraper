"""
Performance benchmarking system.
Tracks performance baselines and compares against benchmarks.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class Benchmark:
    """Performance benchmark definition."""

    name: str
    metric: str
    baseline_value: float
    target_value: float
    unit: str = "ms"  # milliseconds, seconds, percent, etc.
    description: str = ""


@dataclass
class BenchmarkResult:
    """Benchmark comparison result."""

    benchmark_name: str
    current_value: float
    baseline_value: float
    target_value: float
    performance_vs_baseline: float  # percentage
    performance_vs_target: float  # percentage
    status: str  # 'exceeds', 'meets', 'below'
    timestamp: datetime


class PerformanceBenchmarker:
    """Tracks and compares performance against benchmarks."""

    def __init__(self):
        self.benchmarks: Dict[str, Benchmark] = {}
        self.results: List[BenchmarkResult] = []
        self._setup_default_benchmarks()

    def _setup_default_benchmarks(self):
        """Set up default performance benchmarks."""
        # API Response Time Benchmarks
        self.add_benchmark(
            Benchmark(
                name="api_response_time_p95",
                metric="api_latency_p95",
                baseline_value=500.0,  # 500ms baseline
                target_value=2000.0,  # 2s target (SLO)
                unit="ms",
                description="P95 API response time",
            )
        )

        # Database Query Time Benchmarks
        self.add_benchmark(
            Benchmark(
                name="db_query_time_p95",
                metric="db_query_p95",
                baseline_value=100.0,  # 100ms baseline
                target_value=500.0,  # 500ms target
                unit="ms",
                description="P95 database query time",
            )
        )

        # Scraper Success Rate Benchmarks
        self.add_benchmark(
            Benchmark(
                name="scraper_success_rate",
                metric="scraper_success_rate",
                baseline_value=90.0,  # 90% baseline
                target_value=95.0,  # 95% target
                unit="percent",
                description="Scraper success rate",
            )
        )

        # Memory Usage Benchmarks
        self.add_benchmark(
            Benchmark(
                name="memory_usage",
                metric="memory_rss_mb",
                baseline_value=500.0,  # 500MB baseline
                target_value=1000.0,  # 1GB target
                unit="MB",
                description="Memory RSS usage",
            )
        )

    def add_benchmark(self, benchmark: Benchmark):
        """Add or update a benchmark."""
        self.benchmarks[benchmark.name] = benchmark
        logger.info(f"Added benchmark: {benchmark.name}")

    def compare_to_benchmark(
        self, benchmark_name: str, current_value: float
    ) -> Optional[BenchmarkResult]:
        """
        Compare current value to benchmark.

        Args:
            benchmark_name: Name of the benchmark
            current_value: Current metric value

        Returns:
            BenchmarkResult or None
        """
        if benchmark_name not in self.benchmarks:
            return None

        benchmark = self.benchmarks[benchmark_name]

        # Calculate performance vs baseline and target
        # For lower-is-better metrics (latency, memory)
        if benchmark.unit in ["ms", "s", "MB"]:
            baseline_diff = (
                (benchmark.baseline_value - current_value)
                / benchmark.baseline_value
                * 100
            )
            target_diff = (
                (benchmark.target_value - current_value) / benchmark.target_value * 100
            )

            if current_value <= benchmark.target_value:
                status = "exceeds"
            elif current_value <= benchmark.baseline_value:
                status = "meets"
            else:
                status = "below"
        else:
            # For higher-is-better metrics (success rate, etc.)
            baseline_diff = (
                (current_value - benchmark.baseline_value)
                / benchmark.baseline_value
                * 100
            )
            target_diff = (
                (current_value - benchmark.target_value) / benchmark.target_value * 100
            )

            if current_value >= benchmark.target_value:
                status = "exceeds"
            elif current_value >= benchmark.baseline_value:
                status = "meets"
            else:
                status = "below"

        result = BenchmarkResult(
            benchmark_name=benchmark_name,
            current_value=current_value,
            baseline_value=benchmark.baseline_value,
            target_value=benchmark.target_value,
            performance_vs_baseline=baseline_diff,
            performance_vs_target=target_diff,
            status=status,
            timestamp=datetime.utcnow(),
        )

        self.results.append(result)
        return result

    def get_benchmark_summary(self) -> Dict:
        """Get summary of all benchmarks."""
        recent_results = {}

        for benchmark_name in self.benchmarks:
            # Get most recent result for each benchmark
            recent = [r for r in self.results if r.benchmark_name == benchmark_name]
            if recent:
                recent_results[benchmark_name] = recent[-1]

        return {
            "benchmarks": {
                name: {
                    "current_value": result.current_value,
                    "baseline_value": result.baseline_value,
                    "target_value": result.target_value,
                    "status": result.status,
                    "performance_vs_baseline": result.performance_vs_baseline,
                    "performance_vs_target": result.performance_vs_target,
                }
                for name, result in recent_results.items()
            },
            "timestamp": datetime.utcnow().isoformat(),
        }


# Global benchmarker instance
performance_benchmarker = PerformanceBenchmarker()
