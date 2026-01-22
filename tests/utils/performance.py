"""
Performance testing utilities.

Provides utilities for performance testing including
benchmarks, profiling, and performance monitoring.
"""

import os
import statistics
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class PerformanceMonitor:
    """Monitor performance metrics during testing."""

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.operations = []
        self.memory_usage = []
        self.cpu_usage = []

    def start(self):
        """Start performance monitoring."""
        self.start_time = time.time()
        self._record_system_metrics()

    def stop(self):
        """Stop performance monitoring."""
        self.end_time = time.time()
        self._record_system_metrics()

    def record_operation(self, name: str, duration: float, **metadata):
        """Record a performance operation."""
        self.operations.append(
            {"name": name, "duration": duration, "timestamp": time.time(), **metadata}
        )

    def _record_system_metrics(self):
        """Record current system metrics."""
        if not PSUTIL_AVAILABLE:
            return
        process = psutil.Process(os.getpid())
        self.memory_usage.append(process.memory_info().rss)
        self.cpu_usage.append(process.cpu_percent())

    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        total_duration = (
            self.end_time - self.start_time if self.end_time and self.start_time else 0
        )

        return {
            "total_duration": total_duration,
            "operation_count": len(self.operations),
            "average_operation_time": (
                statistics.mean([op["duration"] for op in self.operations])
                if self.operations
                else 0
            ),
            "max_operation_time": (
                max([op["duration"] for op in self.operations])
                if self.operations
                else 0
            ),
            "min_operation_time": (
                min([op["duration"] for op in self.operations])
                if self.operations
                else 0
            ),
            "peak_memory_usage": max(self.memory_usage) if self.memory_usage else 0,
            "average_memory_usage": (
                statistics.mean(self.memory_usage) if self.memory_usage else 0
            ),
            "peak_cpu_usage": max(self.cpu_usage) if self.cpu_usage else 0,
            "average_cpu_usage": (
                statistics.mean(self.cpu_usage) if self.cpu_usage else 0
            ),
        }


@contextmanager
def performance_monitor():
    """Context manager for performance monitoring."""
    monitor = PerformanceMonitor()
    monitor.start()
    try:
        yield monitor
    finally:
        monitor.stop()


def benchmark_function(func: Callable, *args, **kwargs) -> Dict[str, Any]:
    """Benchmark a function's performance."""
    start_time = time.time()
    start_memory = (
        psutil.Process(os.getpid()).memory_info().rss if PSUTIL_AVAILABLE else 0
    )

    result = func(*args, **kwargs)

    end_time = time.time()
    end_memory = (
        psutil.Process(os.getpid()).memory_info().rss if PSUTIL_AVAILABLE else 0
    )

    return {
        "result": result,
        "duration": end_time - start_time,
        "memory_used": end_memory - start_memory,
        "start_time": start_time,
        "end_time": end_time,
    }


def benchmark_file_operation(
    operation: Callable, file_path: Path, *args, **kwargs
) -> Dict[str, Any]:
    """Benchmark a file operation."""
    file_size = file_path.stat().st_size if file_path.exists() else 0

    start_time = time.time()
    result = operation(file_path, *args, **kwargs)
    end_time = time.time()

    duration = end_time - start_time
    throughput = file_size / duration if duration > 0 else 0

    return {
        "result": result,
        "duration": duration,
        "file_size": file_size,
        "throughput_bytes_per_second": throughput,
        "throughput_mbps": (throughput / (1024 * 1024)) if throughput > 0 else 0,
    }


def benchmark_network_operation(operation: Callable, *args, **kwargs) -> Dict[str, Any]:
    """Benchmark a network operation."""
    start_time = time.time()
    result = operation(*args, **kwargs)
    end_time = time.time()

    return {
        "result": result,
        "duration": end_time - start_time,
        "start_time": start_time,
        "end_time": end_time,
    }


def benchmark_concurrent_operations(
    operation: Callable, num_operations: int, max_workers: int = 10, *args, **kwargs
) -> Dict[str, Any]:
    """Benchmark concurrent operations."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(operation, *args, **kwargs) for _ in range(num_operations)
        ]

        results = [future.result() for future in as_completed(futures)]

    end_time = time.time()

    total_duration = end_time - start_time
    operations_per_second = num_operations / total_duration if total_duration > 0 else 0

    return {
        "results": results,
        "total_duration": total_duration,
        "num_operations": num_operations,
        "operations_per_second": operations_per_second,
        "max_workers": max_workers,
    }


def benchmark_memory_usage(operation: Callable, *args, **kwargs) -> Dict[str, Any]:
    """Benchmark memory usage of an operation."""
    if not PSUTIL_AVAILABLE:
        # Fallback to timing only if psutil not available
        start_time = time.time()
        result = operation(*args, **kwargs)
        end_time = time.time()
        return {
            "result": result,
            "duration": end_time - start_time,
            "start_memory": 0,
            "end_memory": 0,
            "final_memory": 0,
            "peak_memory_used": 0,
            "memory_leak": 0,
        }

    process = psutil.Process(os.getpid())

    # Force garbage collection
    import gc

    gc.collect()

    start_memory = process.memory_info().rss
    start_time = time.time()

    result = operation(*args, **kwargs)

    end_time = time.time()
    end_memory = process.memory_info().rss

    # Force garbage collection again
    gc.collect()
    final_memory = process.memory_info().rss

    return {
        "result": result,
        "duration": end_time - start_time,
        "start_memory": start_memory,
        "end_memory": end_memory,
        "final_memory": final_memory,
        "peak_memory_used": end_memory - start_memory,
        "memory_leak": final_memory - start_memory,
    }


def benchmark_database_operation(
    operation: Callable, *args, **kwargs
) -> Dict[str, Any]:
    """Benchmark a database operation."""
    start_time = time.time()
    result = operation(*args, **kwargs)
    end_time = time.time()

    return {
        "result": result,
        "duration": end_time - start_time,
        "start_time": start_time,
        "end_time": end_time,
    }


def benchmark_file_system_operation(
    operation: Callable, *args, **kwargs
) -> Dict[str, Any]:
    """Benchmark a file system operation."""
    start_time = time.time()
    result = operation(*args, **kwargs)
    end_time = time.time()

    return {
        "result": result,
        "duration": end_time - start_time,
        "start_time": start_time,
        "end_time": end_time,
    }


def benchmark_throughput(
    operation: Callable, data_sizes: List[int], *args, **kwargs
) -> Dict[str, Any]:
    """Benchmark throughput with different data sizes."""
    results = {}

    for size in data_sizes:
        # Create test data of specified size
        test_data = b"\x00" * size

        start_time = time.time()
        result = operation(test_data, *args, **kwargs)
        end_time = time.time()

        duration = end_time - start_time
        throughput = size / duration if duration > 0 else 0

        results[size] = {
            "result": result,
            "duration": duration,
            "size": size,
            "throughput_bytes_per_second": throughput,
            "throughput_mbps": (throughput / (1024 * 1024)) if throughput > 0 else 0,
        }

    return results


def benchmark_latency(
    operation: Callable, num_iterations: int = 100, *args, **kwargs
) -> Dict[str, Any]:
    """Benchmark operation latency."""
    durations = []

    for _ in range(num_iterations):
        start_time = time.time()
        result = operation(*args, **kwargs)
        end_time = time.time()

        durations.append(end_time - start_time)

    return {
        "result": result,
        "num_iterations": num_iterations,
        "durations": durations,
        "average_duration": statistics.mean(durations),
        "median_duration": statistics.median(durations),
        "min_duration": min(durations),
        "max_duration": max(durations),
        "std_duration": statistics.stdev(durations) if len(durations) > 1 else 0,
        "p95_duration": (
            sorted(durations)[int(0.95 * len(durations))] if durations else 0
        ),
        "p99_duration": (
            sorted(durations)[int(0.99 * len(durations))] if durations else 0
        ),
    }


def benchmark_scalability(
    operation: Callable, scale_factors: List[int], *args, **kwargs
) -> Dict[str, Any]:
    """Benchmark operation scalability."""
    results = {}

    for scale in scale_factors:
        start_time = time.time()
        result = operation(scale, *args, **kwargs)
        end_time = time.time()

        duration = end_time - start_time

        results[scale] = {
            "result": result,
            "duration": duration,
            "scale": scale,
            "throughput": scale / duration if duration > 0 else 0,
        }

    return results


def benchmark_resource_usage(operation: Callable, *args, **kwargs) -> Dict[str, Any]:
    """Benchmark resource usage of an operation."""
    if not PSUTIL_AVAILABLE:
        # Fallback to timing only if psutil not available
        start_time = time.time()
        result = operation(*args, **kwargs)
        end_time = time.time()
        return {
            "result": result,
            "duration": end_time - start_time,
            "initial_memory": 0,
            "final_memory": 0,
            "memory_used": 0,
            "initial_cpu": 0,
            "final_cpu": 0,
            "cpu_usage": 0,
        }

    process = psutil.Process(os.getpid())

    # Record initial state
    initial_memory = process.memory_info().rss
    initial_cpu = process.cpu_percent()

    start_time = time.time()
    result = operation(*args, **kwargs)
    end_time = time.time()

    # Record final state
    final_memory = process.memory_info().rss
    final_cpu = process.cpu_percent()

    return {
        "result": result,
        "duration": end_time - start_time,
        "initial_memory": initial_memory,
        "final_memory": final_memory,
        "memory_used": final_memory - initial_memory,
        "initial_cpu": initial_cpu,
        "final_cpu": final_cpu,
        "cpu_usage": final_cpu - initial_cpu,
    }


def benchmark_error_handling(
    operation: Callable, error_scenarios: List[Any], *args, **kwargs
) -> Dict[str, Any]:
    """Benchmark error handling performance."""
    results = {}

    for i, error_scenario in enumerate(error_scenarios):
        start_time = time.time()
        try:
            result = operation(error_scenario, *args, **kwargs)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
        end_time = time.time()

        results[i] = {
            "scenario": error_scenario,
            "result": result,
            "success": success,
            "error": error,
            "duration": end_time - start_time,
        }

    return results


def benchmark_concurrent_load(
    operation: Callable, num_concurrent: int, *args, **kwargs
) -> Dict[str, Any]:
    """Benchmark concurrent load handling."""
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results = []
    errors = []

    def worker():
        try:
            start_time = time.time()
            result = operation(*args, **kwargs)
            end_time = time.time()
            results.append(
                {
                    "result": result,
                    "duration": end_time - start_time,
                    "thread_id": threading.get_ident(),
                }
            )
        except Exception as e:
            errors.append({"error": str(e), "thread_id": threading.get_ident()})

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        futures = [executor.submit(worker) for _ in range(num_concurrent)]
        [future.result() for future in as_completed(futures)]

    end_time = time.time()

    return {
        "total_duration": end_time - start_time,
        "num_concurrent": num_concurrent,
        "successful_operations": len(results),
        "failed_operations": len(errors),
        "success_rate": len(results) / num_concurrent,
        "results": results,
        "errors": errors,
    }
