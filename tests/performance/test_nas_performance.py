"""
NAS performance tests.

Tests performance characteristics of NAS operations including
file I/O, directory operations, and concurrent access patterns.
"""

import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Generator, List

import pytest

from tests.fixtures.nas_fixtures import *


class TestNASPerformance:
    """Performance tests for NAS operations."""

    def test_nas_file_write_performance(
        self, nas_test_directory: Path, nas_file_scenarios: Dict, nas_available: bool
    ):
        """Test NAS file write performance."""
        if not nas_available:
            pytest.skip("NAS not available for testing")

        results = {}

        for scenario_name, scenario in nas_file_scenarios.items():
            test_file = nas_test_directory / f"perf_test_{scenario_name}.txt"

            start_time = time.time()
            test_file.write_text(scenario["content"])
            write_time = time.time() - start_time

            results[scenario_name] = {
                "write_time": write_time,
                "size": scenario["size"],
                "throughput_mbps": (scenario["size"] / (1024 * 1024)) / write_time
                if write_time > 0
                else 0,
            }

            # Verify file was written correctly
            assert test_file.exists()
            assert test_file.stat().st_size == scenario["size"]

            # Cleanup
            test_file.unlink()

        # Log performance results
        for scenario, metrics in results.items():
            print(
                f"{scenario}: {metrics['write_time']:.3f}s, {metrics['throughput_mbps']:.2f} MB/s"
            )

    def test_nas_file_read_performance(
        self, nas_test_directory: Path, nas_file_scenarios: Dict, nas_available: bool
    ):
        """Test NAS file read performance."""
        if not nas_available:
            pytest.skip("NAS not available for testing")

        results = {}

        for scenario_name, scenario in nas_file_scenarios.items():
            test_file = nas_test_directory / f"perf_test_{scenario_name}.txt"

            # Write file first
            test_file.write_text(scenario["content"])

            # Test read performance
            start_time = time.time()
            content = test_file.read_text()
            read_time = time.time() - start_time

            results[scenario_name] = {
                "read_time": read_time,
                "size": scenario["size"],
                "throughput_mbps": (scenario["size"] / (1024 * 1024)) / read_time
                if read_time > 0
                else 0,
            }

            # Verify content
            assert content == scenario["content"]

            # Cleanup
            test_file.unlink()

        # Log performance results
        for scenario, metrics in results.items():
            print(
                f"{scenario}: {metrics['read_time']:.3f}s, {metrics['throughput_mbps']:.2f} MB/s"
            )

    def test_nas_directory_operations_performance(
        self, nas_test_directory: Path, nas_available: bool
    ):
        """Test NAS directory operations performance."""
        if not nas_available:
            pytest.skip("NAS not available for testing")

        # Test directory creation performance
        start_time = time.time()
        test_dirs = []
        for i in range(100):
            test_dir = nas_test_directory / f"test_dir_{i}"
            test_dir.mkdir()
            test_dirs.append(test_dir)
        create_time = time.time() - start_time

        # Test directory listing performance
        start_time = time.time()
        dir_contents = list(nas_test_directory.iterdir())
        list_time = time.time() - start_time

        # Test directory deletion performance
        start_time = time.time()
        for test_dir in test_dirs:
            test_dir.rmdir()
        delete_time = time.time() - start_time

        print(f"Directory operations performance:")
        print(f"  Create 100 directories: {create_time:.3f}s")
        print(f"  List directory contents: {list_time:.3f}s")
        print(f"  Delete 100 directories: {delete_time:.3f}s")

        # Verify cleanup
        assert len(list(nas_test_directory.iterdir())) == 0

    def test_nas_concurrent_file_operations(
        self, nas_test_directory: Path, nas_available: bool
    ):
        """Test concurrent file operations on NAS."""
        if not nas_available:
            pytest.skip("NAS not available for testing")

        def worker(worker_id: int, num_files: int = 10) -> Dict[str, Any]:
            """Worker function for concurrent file operations."""
            results = {
                "worker_id": worker_id,
                "files_created": 0,
                "files_read": 0,
                "files_deleted": 0,
                "total_time": 0,
                "errors": [],
            }

            start_time = time.time()

            try:
                # Create files
                for i in range(num_files):
                    test_file = nas_test_directory / f"worker_{worker_id}_file_{i}.txt"
                    test_file.write_text(f"Worker {worker_id} file {i} content")
                    results["files_created"] += 1

                # Read files
                for i in range(num_files):
                    test_file = nas_test_directory / f"worker_{worker_id}_file_{i}.txt"
                    content = test_file.read_text()
                    assert f"Worker {worker_id} file {i} content" in content
                    results["files_read"] += 1

                # Delete files
                for i in range(num_files):
                    test_file = nas_test_directory / f"worker_{worker_id}_file_{i}.txt"
                    test_file.unlink()
                    results["files_deleted"] += 1

            except Exception as e:
                results["errors"].append(str(e))

            results["total_time"] = time.time() - start_time
            return results

        # Run concurrent workers
        num_workers = 10
        num_files_per_worker = 5

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(worker, i, num_files_per_worker)
                for i in range(num_workers)
            ]

            results = [future.result() for future in as_completed(futures)]

        # Analyze results
        total_files = sum(r["files_created"] for r in results)
        total_time = max(r["total_time"] for r in results)
        total_errors = sum(len(r["errors"]) for r in results)

        print(f"Concurrent operations results:")
        print(f"  Workers: {num_workers}")
        print(f"  Files per worker: {num_files_per_worker}")
        print(f"  Total files: {total_files}")
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Total errors: {total_errors}")
        print(f"  Throughput: {total_files / total_time:.2f} files/sec")

        # Verify no errors
        assert (
            total_errors == 0
        ), f"Errors occurred: {[r['errors'] for r in results if r['errors']]}"

    def test_nas_large_file_handling(
        self, nas_test_directory: Path, nas_available: bool
    ):
        """Test handling large files on NAS."""
        if not nas_available:
            pytest.skip("NAS not available for testing")

        # Test with progressively larger files
        file_sizes = [1, 5, 10, 25, 50]  # MB
        results = {}

        for size_mb in file_sizes:
            size_bytes = size_mb * 1024 * 1024
            test_file = nas_test_directory / f"large_file_{size_mb}mb.bin"

            # Test write performance
            start_time = time.time()
            with open(test_file, "wb") as f:
                f.write(b"\x00" * size_bytes)
            write_time = time.time() - start_time

            # Test read performance
            start_time = time.time()
            with open(test_file, "rb") as f:
                content = f.read()
            read_time = time.time() - start_time

            # Verify file
            assert len(content) == size_bytes

            results[size_mb] = {
                "write_time": write_time,
                "read_time": read_time,
                "write_throughput": size_mb / write_time if write_time > 0 else 0,
                "read_throughput": size_mb / read_time if read_time > 0 else 0,
            }

            # Cleanup
            test_file.unlink()

        # Log results
        print("Large file handling results:")
        for size_mb, metrics in results.items():
            print(
                f"  {size_mb}MB: write={metrics['write_time']:.3f}s ({metrics['write_throughput']:.2f} MB/s), "
                f"read={metrics['read_time']:.3f}s ({metrics['read_throughput']:.2f} MB/s)"
            )

    def test_nas_network_resilience(
        self, nas_test_directory: Path, nas_available: bool
    ):
        """Test NAS network resilience."""
        if not nas_available:
            pytest.skip("NAS not available for testing")

        # Test repeated operations to check for network issues
        num_operations = 100
        operation_times = []
        errors = []

        for i in range(num_operations):
            test_file = nas_test_directory / f"resilience_test_{i}.txt"

            try:
                start_time = time.time()

                # Write file
                test_file.write_text(f"Resilience test {i}")

                # Read file
                content = test_file.read_text()
                assert f"Resilience test {i}" in content

                # Delete file
                test_file.unlink()

                operation_time = time.time() - start_time
                operation_times.append(operation_time)

            except Exception as e:
                errors.append(str(e))

        # Analyze results
        if operation_times:
            avg_time = statistics.mean(operation_times)
            median_time = statistics.median(operation_times)
            max_time = max(operation_times)
            min_time = min(operation_times)

            print(f"Network resilience results:")
            print(f"  Operations: {num_operations}")
            print(f"  Errors: {len(errors)}")
            print(
                f"  Success rate: {(num_operations - len(errors)) / num_operations * 100:.1f}%"
            )
            print(f"  Average time: {avg_time:.3f}s")
            print(f"  Median time: {median_time:.3f}s")
            print(f"  Min time: {min_time:.3f}s")
            print(f"  Max time: {max_time:.3f}s")

            # Check for performance degradation
            first_half = operation_times[: len(operation_times) // 2]
            second_half = operation_times[len(operation_times) // 2 :]

            if first_half and second_half:
                first_avg = statistics.mean(first_half)
                second_avg = statistics.mean(second_half)
                degradation = (second_avg - first_avg) / first_avg * 100

                print(f"  Performance degradation: {degradation:.1f}%")

                # Fail if significant degradation
                assert (
                    degradation < 50
                ), f"Significant performance degradation: {degradation:.1f}%"

        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

    def test_nas_memory_usage(self, nas_test_directory: Path, nas_available: bool):
        """Test memory usage during NAS operations."""
        if not nas_available:
            pytest.skip("NAS not available for testing")

        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Perform various operations
        test_files = []
        for i in range(50):
            test_file = nas_test_directory / f"memory_test_{i}.txt"
            test_file.write_text("x" * 1024)  # 1KB per file
            test_files.append(test_file)

        peak_memory = process.memory_info().rss

        # Read all files
        for test_file in test_files:
            content = test_file.read_text()
            assert len(content) == 1024

        read_memory = process.memory_info().rss

        # Cleanup
        for test_file in test_files:
            test_file.unlink()

        final_memory = process.memory_info().rss

        memory_usage = {
            "initial": initial_memory,
            "peak": peak_memory,
            "read": read_memory,
            "final": final_memory,
            "peak_increase": peak_memory - initial_memory,
            "final_increase": final_memory - initial_memory,
        }

        print(f"Memory usage results:")
        print(f"  Initial: {memory_usage['initial'] / 1024 / 1024:.2f} MB")
        print(f"  Peak: {memory_usage['peak'] / 1024 / 1024:.2f} MB")
        print(f"  Final: {memory_usage['final'] / 1024 / 1024:.2f} MB")
        print(f"  Peak increase: {memory_usage['peak_increase'] / 1024 / 1024:.2f} MB")
        print(
            f"  Final increase: {memory_usage['final_increase'] / 1024 / 1024:.2f} MB"
        )

        # Check for memory leaks (final should be close to initial)
        memory_leak = memory_usage["final_increase"] / 1024 / 1024  # MB
        assert memory_leak < 10, f"Potential memory leak: {memory_leak:.2f} MB"

    def test_nas_throughput_benchmark(
        self, nas_test_directory: Path, nas_available: bool
    ):
        """Benchmark NAS throughput with different file sizes."""
        if not nas_available:
            pytest.skip("NAS not available for testing")

        file_sizes = [1024, 10240, 102400, 1024000]  # 1KB, 10KB, 100KB, 1MB
        results = {}

        for size in file_sizes:
            test_file = nas_test_directory / f"throughput_{size}.bin"

            # Write test
            start_time = time.time()
            test_file.write_bytes(b"\x00" * size)
            write_time = time.time() - start_time

            # Read test
            start_time = time.time()
            content = test_file.read_bytes()
            read_time = time.time() - start_time

            # Verify
            assert len(content) == size

            results[size] = {
                "write_time": write_time,
                "read_time": read_time,
                "write_throughput": size / write_time if write_time > 0 else 0,
                "read_throughput": size / read_time if read_time > 0 else 0,
            }

            # Cleanup
            test_file.unlink()

        # Log benchmark results
        print("NAS throughput benchmark:")
        for size, metrics in results.items():
            size_kb = size / 1024
            print(
                f"  {size_kb:.0f}KB: write={metrics['write_throughput']/1024:.2f} KB/s, "
                f"read={metrics['read_throughput']/1024:.2f} KB/s"
            )
