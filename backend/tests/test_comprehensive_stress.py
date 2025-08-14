"""
Comprehensive Stress Test Suite for Receipt Processing API
==========================================================

This test suite evaluates the API's performance under various load conditions:
- Connection handling and pooling
- Concurrent user simulation
- Sustained load testing
- Error recovery and resilience
- Performance metrics and reporting

Usage:
    python tests/test_comprehensive_stress.py [--quick] [--data-dir tests/data]
    
    --quick: Run a shorter version of the tests (5 minutes instead of full suite)
    --data-dir: Path to directory containing receipt images (default: tests/data)
"""
import os
import pytest

import asyncio
import time
import random
import json
import statistics
import argparse
import os
import sys
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import httpx
from httpx import AsyncClient, Limits


# Skip by default in CI to avoid long-running load tests; set RUN_STRESS_TESTS=1 to enable
pytestmark = pytest.mark.skipif(os.getenv("RUN_STRESS_TESTS") != "1", reason="Stress tests disabled by default")


class TestPhase(Enum):
    """Test phases for structured execution"""
    WARMUP = "warmup"
    RAMPUP = "rampup"
    SUSTAINED = "sustained"
    SPIKE = "spike"
    COOLDOWN = "cooldown"


@dataclass
class TestConfig:
    """Configuration for a test scenario"""
    name: str
    users: int
    duration: int  # seconds
    requests_per_user: Optional[int] = None  # None means continuous
    delay_between_requests: float = 0.5
    timeout: float = 30.0
    phase: TestPhase = TestPhase.SUSTAINED


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics collector"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    response_times: List[float] = field(default_factory=list)
    errors: Dict[str, int] = field(default_factory=dict)
    status_codes: Dict[int, int] = field(default_factory=dict)
    timestamps: List[float] = field(default_factory=list)
    file_sizes: List[int] = field(default_factory=list)
    file_names: Dict[str, int] = field(default_factory=dict)
    
    def record_request(self, success: bool, response_time: float, 
                      error: Optional[str] = None, status_code: Optional[int] = None,
                      file_size: Optional[int] = None, file_name: Optional[str] = None):
        """Record a single request's metrics"""
        self.total_requests += 1
        self.timestamps.append(time.time())
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            if error:
                self.errors[error] = self.errors.get(error, 0) + 1
        
        if response_time > 0:
            self.response_times.append(response_time)
        
        if status_code:
            self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
        
        if file_size:
            self.file_sizes.append(file_size)
        
        if file_name:
            self.file_names[file_name] = self.file_names.get(file_name, 0) + 1
    
    def get_statistics(self) -> Dict:
        """Calculate comprehensive statistics"""
        if not self.response_times:
            return {
                "total_requests": self.total_requests,
                "successful_requests": self.successful_requests,
                "failed_requests": self.failed_requests,
                "success_rate": self._calculate_success_rate(),
                "errors": self.errors,
                "status_codes": self.status_codes
            }
        
        sorted_times = sorted(self.response_times)
        duration = self._calculate_duration()
        
        stats = {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self._calculate_success_rate(),
            "duration_seconds": duration,
            "requests_per_second": self.total_requests / duration if duration > 0 else 0,
            "response_times": {
                "mean": statistics.mean(self.response_times),
                "median": statistics.median(self.response_times),
                "min": min(self.response_times),
                "max": max(self.response_times),
                "std_dev": statistics.stdev(self.response_times) if len(self.response_times) > 1 else 0,
                "percentiles": {
                    "p50": self._percentile(sorted_times, 50),
                    "p75": self._percentile(sorted_times, 75),
                    "p90": self._percentile(sorted_times, 90),
                    "p95": self._percentile(sorted_times, 95),
                    "p99": self._percentile(sorted_times, 99),
                }
            },
            "errors": dict(sorted(self.errors.items(), key=lambda x: x[1], reverse=True)),
            "status_codes": dict(sorted(self.status_codes.items()))
        }
        
        # Add file size statistics if available
        if self.file_sizes:
            stats["file_sizes"] = {
                "mean_kb": statistics.mean(self.file_sizes) / 1024,
                "min_kb": min(self.file_sizes) / 1024,
                "max_kb": max(self.file_sizes) / 1024,
                "total_mb": sum(self.file_sizes) / (1024 * 1024)
            }
        
        # Add most processed files
        if self.file_names:
            top_files = sorted(self.file_names.items(), key=lambda x: x[1], reverse=True)[:5]
            stats["top_processed_files"] = top_files
        
        return stats
    
    def _calculate_success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    def _calculate_duration(self) -> float:
        """Calculate test duration in seconds"""
        if len(self.timestamps) < 2:
            return 0.0
        return self.timestamps[-1] - self.timestamps[0]
    
    def _percentile(self, sorted_list: List[float], percentile: int) -> float:
        """Calculate percentile value"""
        if not sorted_list:
            return 0.0
        index = int(len(sorted_list) * percentile / 100)
        return sorted_list[min(index, len(sorted_list) - 1)]


class ReceiptImageProvider:
    """Provides receipt images from a data directory"""
    
    def __init__(self, data_dir: str, cost_control: bool = False):
        self.data_dir = Path(data_dir)
        self.image_paths = []
        self.image_categories = {}
        self.cost_control = cost_control
        self._load_images()
    
    def _load_images(self):
        """Load all image paths from the data directory, optionally limit to 50 for cost control"""
        if not self.data_dir.exists():
            raise ValueError(f"Data directory does not exist: {self.data_dir}")

        # Common image extensions
        extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.webp', '*.JPG', '*.JPEG', '*.PNG']

        all_images = []
        for ext in extensions:
            all_images.extend(self.data_dir.glob(ext))
            all_images.extend(self.data_dir.rglob(ext))

        if not all_images:
            raise ValueError(f"No images found in {self.data_dir}")

        if self.cost_control and len(all_images) > 50:
            self.image_paths = random.sample(all_images, 50)
        else:
            self.image_paths = all_images

        # Categorize images by subdirectory (only for the selected images)
        for path in self.image_paths:
            relative_path = path.relative_to(self.data_dir)
            category = relative_path.parts[0] if len(relative_path.parts) > 1 else "root"
            if category not in self.image_categories:
                self.image_categories[category] = []
            self.image_categories[category].append(path)

        print(f"\n📁 Receipt Image Analysis:")
        if self.cost_control:
            print(f"   Total images used for test: {len(self.image_paths)} (cost control: max 50)")
        else:
            print(f"   Total images used for test: {len(self.image_paths)}")

        # Show category breakdown
        if len(self.image_categories) > 1:
            print(f"   Categories:")
            for category, paths in self.image_categories.items():
                print(f"     - {category}: {len(paths)} images")

        # Show file size distribution
        sizes = []
        for p in self.image_paths:
            try:
                sizes.append(p.stat().st_size)
            except:
                pass

        if sizes:
            print(f"   Size distribution:")
            print(f"     - Min: {min(sizes)/1024:.1f}KB")
            print(f"     - Max: {max(sizes)/1024:.1f}KB")
            print(f"     - Average: {statistics.mean(sizes)/1024:.1f}KB")
            print(f"     - Total: {sum(sizes)/(1024*1024):.1f}MB")

        # Sample some filenames
        sample_files = random.sample(self.image_paths, min(3, len(self.image_paths)))
        print(f"   Sample files:")
        for f in sample_files:
            print(f"     - {f.name}")
    
    def get_random_image(self) -> Tuple[str, bytes, int]:
        """Get a random image from the collection"""
        image_path = random.choice(self.image_paths)
        
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
            return (image_path.name, image_data, len(image_data))
        except Exception as e:
            print(f"Error reading {image_path}: {e}")
            # Try another image
            return self.get_random_image()
    
    def get_image_by_index(self, index: int) -> Tuple[str, bytes, int]:
        """Get a specific image by index (for reproducible tests)"""
        image_path = self.image_paths[index % len(self.image_paths)]
        
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
            return (image_path.name, image_data, len(image_data))
        except Exception as e:
            print(f"Error reading {image_path}: {e}")
            # Return next image
            return self.get_image_by_index(index + 1)
    
    def get_image_from_category(self, category: str) -> Tuple[str, bytes, int]:
        """Get a random image from a specific category"""
        if category in self.image_categories:
            image_path = random.choice(self.image_categories[category])
        else:
            image_path = random.choice(self.image_paths)
        
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
            return (image_path.name, image_data, len(image_data))
        except Exception as e:
            print(f"Error reading {image_path}: {e}")
            return self.get_random_image()


class StressTestRunner:
    """Main stress test runner"""
    
    def __init__(self, base_url: str = "http://localhost:8001", data_dir: str = "tests/data", cost_control: bool = False):
        self.base_url = base_url
        self.metrics = PerformanceMetrics()

        # Try to find the data directory
        if not Path(data_dir).exists():
            # Try relative to script location
            script_dir = Path(__file__).parent
            data_dir = script_dir / "data"

        self.image_provider = ReceiptImageProvider(data_dir, cost_control=cost_control)
    
    async def health_check(self) -> bool:
        """Perform a health check on the API"""
        try:
            async with AsyncClient(base_url=self.base_url) as client:
                response = await client.get("/health", timeout=5.0)
                return response.status_code == 200
        except:
            return False
    
    async def run_test_suite(self, quick_mode: bool = False):
        """Run the complete test suite"""
        print("\n🚀 Starting Comprehensive Stress Test Suite")
        print("=" * 70)
        print(f"Target API: {self.base_url}")
        print(f"Mode: {'Quick (5 min)' if quick_mode else 'Full Suite'}")
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        # Health check
        print("\n🏥 Performing health check...")
        if await self.health_check():
            print("✅ API is healthy")
        else:
            print("❌ API health check failed! Please ensure the API is running.")
            return
        
        # Test configurations
        if quick_mode:
            test_configs = self._get_quick_test_configs()
        else:
            test_configs = self._get_full_test_configs()
        
        results = {}
        
        for config in test_configs:
            print(f"\n📊 Running: {config.name}")
            print("-" * 50)
            
            result = await self._run_single_test(config)
            results[config.name] = result
            
            # Brief pause between tests
            if config != test_configs[-1]:
                print("\n⏸️  Pausing 10 seconds before next test...")
                await asyncio.sleep(10)
        
        # Generate final report
        self._generate_final_report(results)
    
    def _get_quick_test_configs(self) -> List[TestConfig]:
        """Quick test configurations (5 minutes total)"""
        return [
            TestConfig("Warmup", users=5, duration=30, delay_between_requests=1.0, phase=TestPhase.WARMUP),
            TestConfig("Moderate Load", users=15, duration=120, delay_between_requests=0.5, phase=TestPhase.SUSTAINED),
            TestConfig("Peak Load", users=25, duration=90, delay_between_requests=0.2, phase=TestPhase.SPIKE),
            TestConfig("Cooldown", users=5, duration=60, delay_between_requests=2.0, phase=TestPhase.COOLDOWN),
        ]
    
    def _get_full_test_configs(self) -> List[TestConfig]:
        """Full test configurations"""
        return [
            TestConfig("Warmup", users=5, duration=60, delay_between_requests=2.0, phase=TestPhase.WARMUP),
            TestConfig("Ramp Up", users=10, duration=120, delay_between_requests=1.0, phase=TestPhase.RAMPUP),
            TestConfig("Sustained Load", users=20, duration=300, delay_between_requests=0.5, phase=TestPhase.SUSTAINED),
            TestConfig("Spike Test", users=40, duration=120, delay_between_requests=0.1, phase=TestPhase.SPIKE),
            TestConfig("Recovery Test", users=10, duration=120, delay_between_requests=1.0, phase=TestPhase.SUSTAINED),
            TestConfig("Endurance Test", users=15, duration=600, delay_between_requests=0.3, phase=TestPhase.SUSTAINED),
            TestConfig("Cooldown", users=5, duration=60, delay_between_requests=2.0, phase=TestPhase.COOLDOWN),
        ]
    
    async def _run_single_test(self, config: TestConfig) -> Dict:
        """Run a single test configuration"""
        test_metrics = PerformanceMetrics()
        
        # Configure connection limits based on user count
        limits = Limits(
            max_keepalive_connections=min(config.users * 2, 100),
            max_connections=min(config.users * 3, 150),
            keepalive_expiry=30.0
        )
        
        # Create progress tracker
        progress_tracker = self._create_progress_tracker(config)
        
        async with AsyncClient(base_url=self.base_url, limits=limits, timeout=60.0) as client:
            # Start progress monitoring
            monitor_task = asyncio.create_task(progress_tracker(test_metrics))
            
            # Create user tasks
            user_tasks = []
            for user_id in range(config.users):
                task = self._simulate_user(client, user_id, config, test_metrics)
                user_tasks.append(task)
            
            # Run all user simulations
            await asyncio.gather(*user_tasks, return_exceptions=True)
            
            # Stop monitoring
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
        
        # Return metrics
        stats = test_metrics.get_statistics()
        self._print_test_summary(config, stats)
        return stats
    
    async def _simulate_user(self, client: AsyncClient, user_id: int, 
                           config: TestConfig, metrics: PerformanceMetrics):
        """Simulate a single user's behavior"""
        start_time = time.time()
        request_count = 0
        consecutive_errors = 0
        
        while time.time() - start_time < config.duration:
            try:
                # Get a real receipt image
                if config.phase == TestPhase.SPIKE:
                    # During spike, use random images for variety
                    filename, image_data, file_size = self.image_provider.get_random_image()
                else:
                    # For other phases, use consistent images per user for reproducibility
                    filename, image_data, file_size = self.image_provider.get_image_by_index(
                        user_id * 100 + request_count
                    )
                
                # Determine content type based on file extension
                ext = filename.lower().split('.')[-1]
                content_type = {
                    'jpg': 'image/jpeg',
                    'jpeg': 'image/jpeg',
                    'png': 'image/png',
                    'gif': 'image/gif',
                    'webp': 'image/webp'
                }.get(ext, 'image/jpeg')
                
                files = {
                    'file': (f'{config.phase.value}_{user_id}_{filename}', 
                            image_data, content_type)
                }
                
                # Make request
                request_start = time.time()
                response = await client.post(
                    "/receipts",
                    files=files,
                    timeout=config.timeout
                )
                request_duration = time.time() - request_start
                
                # Record metrics
                success = response.status_code in [200, 201]
                metrics.record_request(
                    success, 
                    request_duration, 
                    status_code=response.status_code,
                    file_size=file_size,
                    file_name=filename
                )
                
                if success:
                    consecutive_errors = 0
                else:
                    consecutive_errors += 1
                    # Log non-success responses
                    if response.status_code not in [200, 201]:
                        print(f"\n❌ User {user_id}: Status {response.status_code} for {filename}")
                
                request_count += 1
                
                # Adaptive delay based on phase and errors
                delay = self._calculate_delay(config, success, consecutive_errors)
                await asyncio.sleep(delay)
                
            except httpx.TimeoutException:
                consecutive_errors += 1
                metrics.record_request(False, config.timeout, error="Timeout")
                await asyncio.sleep(config.delay_between_requests * (1 + consecutive_errors))
            except httpx.ConnectError:
                consecutive_errors += 1
                metrics.record_request(False, 0, error="ConnectionError")
                await asyncio.sleep(config.delay_between_requests * (2 + consecutive_errors))
            except Exception as e:
                consecutive_errors += 1
                error_type = type(e).__name__
                metrics.record_request(False, 0, error=error_type)
                print(f"\n❌ User {user_id}: {error_type} - {str(e)}")
                await asyncio.sleep(config.delay_between_requests * 2)
    
    def _calculate_delay(self, config: TestConfig, success: bool, consecutive_errors: int) -> float:
        """Calculate adaptive delay based on phase, success, and error count"""
        base_delay = config.delay_between_requests
        
        # Exponential backoff for consecutive errors
        if consecutive_errors > 0:
            return min(base_delay * (2 ** consecutive_errors), 30.0)
        
        if not success:
            # Back off on failures
            return base_delay * random.uniform(2, 4)
        
        if config.phase == TestPhase.SPIKE:
            # More aggressive during spike
            return base_delay * random.uniform(0.5, 1.0)
        elif config.phase == TestPhase.WARMUP:
            # Gentle during warmup
            return base_delay * random.uniform(1.0, 2.0)
        else:
            # Normal variation
            return base_delay * random.uniform(0.8, 1.2)
    
    def _create_progress_tracker(self, config: TestConfig):
        """Create a progress tracking coroutine"""
        async def track_progress(metrics: PerformanceMetrics):
            start_time = time.time()
            
            while True:
                elapsed = time.time() - start_time
                progress = (elapsed / config.duration) * 100
                
                rate = metrics.successful_requests / elapsed if elapsed > 0 else 0
                success_rate = metrics._calculate_success_rate()
                
                # Calculate average file size processed
                avg_size_kb = (statistics.mean(metrics.file_sizes) / 1024) if metrics.file_sizes else 0
                
                print(f"\r⏱️  Progress: {progress:5.1f}% | "
                      f"✅ Success: {success_rate:5.1f}% | "
                      f"📈 Rate: {rate:6.2f} req/s | "
                      f"📊 Total: {metrics.total_requests:4d} | "
                      f"📁 Avg: {avg_size_kb:6.1f}KB", end="", flush=True)
                
                await asyncio.sleep(2)
        
        return track_progress
    
    def _print_test_summary(self, config: TestConfig, stats: Dict):
        """Print summary for a single test"""
        print()  # New line after progress
        print(f"\n📋 {config.name} Results:")
        print(f"   Duration: {stats.get('duration_seconds', 0):.1f}s")
        print(f"   Total Requests: {stats['total_requests']}")
        print(f"   Success Rate: {stats['success_rate']:.1f}%")
        print(f"   Avg Rate: {stats.get('requests_per_second', 0):.2f} req/s")
        
        if 'response_times' in stats:
            rt = stats['response_times']
            print(f"   Response Times:")
            print(f"     Mean: {rt['mean']:.2f}s")
            print(f"     P95: {rt['percentiles']['p95']:.2f}s")
            print(f"     P99: {rt['percentiles']['p99']:.2f}s")
        
        if 'file_sizes' in stats:
            fs = stats['file_sizes']
            print(f"   File Sizes:")
            print(f"     Average: {fs['mean_kb']:.1f}KB")
            print(f"     Total processed: {fs['total_mb']:.1f}MB")
        
        if 'top_processed_files' in stats and stats['top_processed_files']:
            print(f"   Most processed files:")
            for filename, count in stats['top_processed_files'][:3]:
                print(f"     - {filename}: {count} times")
    
    def _generate_final_report(self, results: Dict[str, Dict]):
        """Generate comprehensive final report"""
        print("\n" + "=" * 70)
        print("📊 FINAL STRESS TEST REPORT")
        print("=" * 70)
        
        # Overall statistics
        total_requests = sum(r['total_requests'] for r in results.values())
        total_success = sum(r['successful_requests'] for r in results.values())
        overall_success_rate = (total_success / total_requests * 100) if total_requests > 0 else 0
        
        # Calculate total data processed
        total_mb = sum(r.get('file_sizes', {}).get('total_mb', 0) for r in results.values())
        
        print(f"\n🎯 Overall Performance:")
        print(f"   Total Requests: {total_requests:,}")
        print(f"   Total Successful: {total_success:,}")
        print(f"   Overall Success Rate: {overall_success_rate:.1f}%")
        print(f"   Total Data Processed: {total_mb:.1f}MB")
        
        # Best and worst performing phases
        best_phase = max(results.items(), key=lambda x: x[1]['success_rate'])
        worst_phase = min(results.items(), key=lambda x: x[1]['success_rate'])
        
        print(f"\n🏆 Best Performance: {best_phase[0]} ({best_phase[1]['success_rate']:.1f}% success)")
        print(f"⚠️  Worst Performance: {worst_phase[0]} ({worst_phase[1]['success_rate']:.1f}% success)")
        
        # Performance characteristics
        sustained_result = results.get("Sustained Load", {})
        spike_result = results.get("Spike Test", {})
        
        if sustained_result:
            print(f"\n📈 Sustained Load Capacity:")
            print(f"   Rate: {sustained_result.get('requests_per_second', 0):.2f} req/s")
            print(f"   Success Rate: {sustained_result.get('success_rate', 0):.1f}%")
            print(f"   P95 Response: {sustained_result.get('response_times', {}).get('percentiles', {}).get('p95', 0):.2f}s")
        
        if spike_result:
            print(f"\n⚡ Peak Load Handling:")
            print(f"   Rate: {spike_result.get('requests_per_second', 0):.2f} req/s")
            print(f"   Success Rate: {spike_result.get('success_rate', 0):.1f}%")
            print(f"   P95 Response: {spike_result.get('response_times', {}).get('percentiles', {}).get('p95', 0):.2f}s")
        
        # Error analysis
        all_errors = {}
        for result in results.values():
            for error, count in result.get('errors', {}).items():
                all_errors[error] = all_errors.get(error, 0) + count
        
        if all_errors:
            print(f"\n❌ Error Summary:")
            for error, count in sorted(all_errors.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"   {error}: {count}")
        
        # Response time analysis across all tests
        all_response_times = []
        for result in results.values():
            if 'response_times' in result:
                all_response_times.extend([result['response_times']['mean'], 
                                         result['response_times']['percentiles']['p95']])
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        
        if overall_success_rate < 95:
            print("   ⚠️  Success rate below 95% - investigate error causes")
        
        if sustained_result and sustained_result.get('response_times', {}).get('percentiles', {}).get('p95', 0) > 3:
            print("   ⚠️  P95 response time exceeds 3 seconds - consider optimization")
        
        if 'Timeout' in all_errors:
            print("   ⚠️  Timeout errors detected - review timeout settings or optimize slow operations")
        
        if 'ConnectionError' in all_errors:
            print("   ⚠️  Connection errors detected - check server capacity and connection limits")
        
        # Performance grade
        grade = self._calculate_performance_grade(overall_success_rate, sustained_result, all_errors)
        print(f"\n🏅 Performance Grade: {grade}")
        
        print(f"\n✅ Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    def _calculate_performance_grade(self, success_rate: float, sustained_result: Dict, errors: Dict) -> str:
        """Calculate an overall performance grade"""
        score = 100
        
        # Success rate impact
        if success_rate < 99:
            score -= (99 - success_rate) * 2
        
        # Response time impact
        if sustained_result:
            p95 = sustained_result.get('response_times', {}).get('percentiles', {}).get('p95', 0)
            if p95 > 3:
                score -= 10
            elif p95 > 2:
                score -= 5
        
        # Error impact
        if errors:
            score -= min(len(errors) * 5, 20)
        
        # Grade assignment
        if score >= 95:
            return "A+ (Excellent)"
        elif score >= 90:
            return "A (Very Good)"
        elif score >= 85:
            return "B+ (Good)"
        elif score >= 80:
            return "B (Satisfactory)"
        elif score >= 75:
            return "C (Needs Improvement)"
        else:
            return "D (Poor)"


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Comprehensive API Stress Test")
    parser.add_argument("--quick", action="store_true", help="Run quick 5-minute test suite")
    parser.add_argument("--url", default="http://localhost:8001", help="API base URL")
    parser.add_argument("--data-dir", default="tests/data", help="Directory containing receipt images")
    parser.add_argument("--cost-control", action="store_true", help="Limit to 50 images for cost control")

    args = parser.parse_args()

    # Check if running from project root or tests directory
    data_path = Path(args.data_dir)
    if not data_path.exists():
        # Try relative to current directory
        if Path("data").exists():
            data_path = Path("data")
        elif Path("tests/data").exists():
            data_path = Path("tests/data")
        else:
            print(f"❌ Error: Data directory '{args.data_dir}' not found!")
            print("Please ensure you have a 'data' folder with receipt images in the tests directory.")
            sys.exit(1)

    # Run stress test
    try:
        runner = StressTestRunner(base_url=args.url, data_dir=str(data_path), cost_control=args.cost_control)
        await runner.run_test_suite(quick_mode=args.quick)
    except ValueError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())