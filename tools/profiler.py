"""
Performance profiling tools.
"""
import cProfile
import pstats
import io
import time
from functools import wraps
from typing import Callable, Optional
import memory_profiler
import line_profiler


def profile_function(func: Callable, output_file: Optional[str] = None):
    """
    Profile a function's performance.

    Args:
        func: Function to profile
        output_file: Optional file to save profile results
    """
    profiler = cProfile.Profile()
    profiler.enable()

    result = func()

    profiler.disable()

    # Generate stats
    stats = pstats.Stats(profiler)
    stats.sort_stats("cumulative")

    if output_file:
        stats.dump_stats(output_file)
        print(f"Profile saved to {output_file}")
    else:
        # Print to console
        stats.print_stats(20)  # Top 20 functions

    return result


def profile_memory(func: Callable):
    """
    Profile memory usage of a function.

    Args:
        func: Function to profile
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        profiler = memory_profiler.LineProfiler()
        profiler.add_function(func)
        profiler.enable()

        result = func(*args, **kwargs)

        profiler.disable()

        # Print memory profile
        stream = io.StringIO()
        memory_profiler.show_results(profiler, stream=stream)
        print(stream.getvalue())

        return result

    return wrapper


def time_function(func: Callable):
    """Decorator to time function execution."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"{func.__name__} took {elapsed*1000:.2f}ms")
        return result

    return wrapper


class PerformanceProfiler:
    """Performance profiler for application components."""

    def __init__(self):
        self.profiles = {}

    def profile_endpoint(self, endpoint_func: Callable, iterations: int = 10):
        """Profile an API endpoint."""
        profiler = cProfile.Profile()
        profiler.enable()

        for _ in range(iterations):
            endpoint_func()

        profiler.disable()

        stats = pstats.Stats(profiler)
        stats.sort_stats("cumulative")

        return stats

    def profile_query(self, query_func: Callable, iterations: int = 10):
        """Profile a database query."""
        return self.profile_endpoint(query_func, iterations)

    def generate_report(self, stats: pstats.Stats, output_file: str):
        """Generate profiling report."""
        with open(output_file, "w") as f:
            stats.print_stats(file=f)
        print(f"Profile report saved to {output_file}")


if __name__ == "__main__":
    # Example usage
    profiler = PerformanceProfiler()

    # Profile a function
    def example_function():
        time.sleep(0.1)
        return sum(range(1000))

    stats = profiler.profile_endpoint(example_function, iterations=10)
    stats.print_stats(10)
