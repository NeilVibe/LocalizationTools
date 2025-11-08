#!/usr/bin/env python3
"""
Server Performance Benchmarking

Test server performance with realistic loads and measure response times.
"""

import sys
from pathlib import Path
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from loguru import logger
from server import config


class ServerBenchmark:
    """Benchmark server performance."""

    def __init__(self, base_url: str = None):
        """Initialize benchmark."""
        self.base_url = base_url or f"http://{config.SERVER_HOST}:{config.SERVER_PORT}"
        self.results = {}

    def test_endpoint(self, name: str, method: str, endpoint: str,
                     headers: dict = None, json_data: dict = None,
                     iterations: int = 100) -> dict:
        """
        Test endpoint performance.

        Args:
            name: Test name
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            headers: Optional headers
            json_data: Optional JSON data
            iterations: Number of requests to make

        Returns:
            Performance statistics dict
        """
        logger.info(f"Testing {name} ({iterations} iterations)...")

        response_times = []
        errors = 0

        for i in range(iterations):
            try:
                start = time.time()

                if method == "GET":
                    response = requests.get(
                        f"{self.base_url}{endpoint}",
                        headers=headers,
                        timeout=10
                    )
                elif method == "POST":
                    response = requests.post(
                        f"{self.base_url}{endpoint}",
                        headers=headers,
                        json=json_data,
                        timeout=10
                    )

                elapsed = time.time() - start

                if response.status_code in [200, 201]:
                    response_times.append(elapsed * 1000)  # Convert to ms
                else:
                    errors += 1

            except Exception as e:
                errors += 1
                logger.warning(f"Request {i+1} failed: {e}")

        if response_times:
            stats = {
                "test": name,
                "iterations": iterations,
                "successful": len(response_times),
                "errors": errors,
                "min_ms": round(min(response_times), 2),
                "max_ms": round(max(response_times), 2),
                "avg_ms": round(statistics.mean(response_times), 2),
                "median_ms": round(statistics.median(response_times), 2),
                "p95_ms": round(statistics.quantiles(response_times, n=20)[18], 2) if len(response_times) > 20 else None,
                "p99_ms": round(statistics.quantiles(response_times, n=100)[98], 2) if len(response_times) > 100 else None,
            }
        else:
            stats = {
                "test": name,
                "iterations": iterations,
                "successful": 0,
                "errors": errors,
                "status": "FAILED"
            }

        self.results[name] = stats
        return stats

    def test_concurrent_requests(self, name: str, method: str, endpoint: str,
                                headers: dict = None, json_data: dict = None,
                                workers: int = 10, requests_per_worker: int = 10) -> dict:
        """
        Test concurrent request performance.

        Args:
            name: Test name
            method: HTTP method
            endpoint: API endpoint
            headers: Optional headers
            json_data: Optional JSON data
            workers: Number of concurrent workers
            requests_per_worker: Requests per worker

        Returns:
            Performance statistics
        """
        logger.info(f"Testing {name} (concurrent: {workers} workers x {requests_per_worker} requests)...")

        response_times = []
        errors = 0

        def make_request():
            """Make a single request."""
            try:
                start = time.time()

                if method == "GET":
                    response = requests.get(
                        f"{self.base_url}{endpoint}",
                        headers=headers,
                        timeout=10
                    )
                elif method == "POST":
                    response = requests.post(
                        f"{self.base_url}{endpoint}",
                        headers=headers,
                        json=json_data,
                        timeout=10
                    )

                elapsed = time.time() - start

                if response.status_code in [200, 201]:
                    return elapsed * 1000
                else:
                    return None
            except Exception as e:
                return None

        # Execute concurrent requests
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = []
            for _ in range(workers * requests_per_worker):
                futures.append(executor.submit(make_request))

            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    response_times.append(result)
                else:
                    errors += 1

        total_time = time.time() - start_time

        if response_times:
            stats = {
                "test": name,
                "total_requests": workers * requests_per_worker,
                "successful": len(response_times),
                "errors": errors,
                "total_time_s": round(total_time, 2),
                "requests_per_second": round(len(response_times) / total_time, 2),
                "min_ms": round(min(response_times), 2),
                "max_ms": round(max(response_times), 2),
                "avg_ms": round(statistics.mean(response_times), 2),
                "median_ms": round(statistics.median(response_times), 2),
            }
        else:
            stats = {
                "test": name,
                "total_requests": workers * requests_per_worker,
                "successful": 0,
                "errors": errors,
                "status": "FAILED"
            }

        self.results[name] = stats
        return stats

    def print_results(self):
        """Print benchmark results in a nice format."""
        logger.info("\n" + "=" * 80)
        logger.info("BENCHMARK RESULTS")
        logger.info("=" * 80)

        for name, stats in self.results.items():
            logger.info(f"\n{name}:")
            for key, value in stats.items():
                if key != "test":
                    logger.info(f"  {key}: {value}")

        logger.info("\n" + "=" * 80)


def run_benchmarks():
    """Run comprehensive server benchmarks."""
    logger.info("=" * 80)
    logger.info("SERVER PERFORMANCE BENCHMARKING")
    logger.info("=" * 80)

    benchmark = ServerBenchmark()

    # Check if server is running
    try:
        response = requests.get(f"{benchmark.base_url}/health", timeout=5)
        if response.status_code != 200:
            logger.error("❌ Server not responding! Start server first:")
            logger.error("   python3 server/main.py")
            return False
    except Exception as e:
        logger.error(f"❌ Cannot connect to server: {e}")
        logger.error("Start server first: python3 server/main.py")
        return False

    logger.success("✓ Server is running")

    # Test 1: Health check endpoint
    benchmark.test_endpoint(
        name="Health Check (100 requests)",
        method="GET",
        endpoint="/health",
        iterations=100
    )

    # Test 2: Root endpoint
    benchmark.test_endpoint(
        name="Root Endpoint (100 requests)",
        method="GET",
        endpoint="/",
        iterations=100
    )

    # Test 3: Version endpoint
    benchmark.test_endpoint(
        name="Version Endpoint (100 requests)",
        method="GET",
        endpoint="/api/version/latest",
        iterations=100
    )

    # Test 4: Announcements endpoint
    benchmark.test_endpoint(
        name="Announcements (100 requests)",
        method="GET",
        endpoint="/api/announcements",
        iterations=100
    )

    # Test 5: Concurrent health checks
    benchmark.test_concurrent_requests(
        name="Concurrent Health Checks (10 workers x 20 requests)",
        method="GET",
        endpoint="/health",
        workers=10,
        requests_per_worker=20
    )

    # Test 6: Concurrent root endpoint
    benchmark.test_concurrent_requests(
        name="Concurrent Root Endpoint (20 workers x 10 requests)",
        method="GET",
        endpoint="/",
        workers=20,
        requests_per_worker=10
    )

    # Print results
    benchmark.print_results()

    # Performance assessment
    logger.info("\n" + "=" * 80)
    logger.info("PERFORMANCE ASSESSMENT")
    logger.info("=" * 80)

    health_check = benchmark.results.get("Health Check (100 requests)")
    if health_check and health_check.get("avg_ms"):
        avg_ms = health_check["avg_ms"]
        if avg_ms < 50:
            logger.success(f"✓ Excellent performance: {avg_ms}ms average response time")
        elif avg_ms < 100:
            logger.info(f"✓ Good performance: {avg_ms}ms average response time")
        elif avg_ms < 200:
            logger.warning(f"⚠ Acceptable performance: {avg_ms}ms average response time")
        else:
            logger.error(f"❌ Poor performance: {avg_ms}ms average response time")

    concurrent = benchmark.results.get("Concurrent Health Checks (10 workers x 20 requests)")
    if concurrent and concurrent.get("requests_per_second"):
        rps = concurrent["requests_per_second"]
        logger.info(f"Throughput: {rps} requests/second")

        if rps > 100:
            logger.success("✓ Excellent throughput")
        elif rps > 50:
            logger.info("✓ Good throughput")
        else:
            logger.warning("⚠ Consider performance optimization")

    return True


if __name__ == "__main__":
    success = run_benchmarks()
    sys.exit(0 if success else 1)
