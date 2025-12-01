#!/usr/bin/env python3
"""
QuickSearch Phase 4 Testing Script
Tests all QuickSearch functionality with proper authentication
"""

import requests
import json
import time
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8888"
TEST_FILE = "/home/neil1988/LocalizationTools/RessourcesForCodingTheProject/datausedfortesting/test123.txt"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_test(msg):
    print(f"\n{Colors.BLUE}→ {msg}{Colors.END}")

def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")

def print_info(msg):
    print(f"{Colors.YELLOW}ℹ {msg}{Colors.END}")

class QuickSearchTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.token = None
        self.headers = {}

    def register_user(self):
        """Register a test user"""
        print_test("Registering test user...")

        url = f"{self.base_url}/api/v2/auth/register"
        data = {
            "username": f"testuser_{int(time.time())}",
            "password": "testpass123",
            "email": f"test{int(time.time())}@test.com"
        }

        try:
            response = requests.post(url, json=data)
            if response.status_code == 200:
                result = response.json()
                self.token = result.get('access_token')
                self.headers = {'Authorization': f'Bearer {self.token}'}
                print_success(f"User registered: {data['username']}")
                return True
            else:
                print_error(f"Registration failed: {response.text}")
                return False
        except Exception as e:
            print_error(f"Registration error: {e}")
            return False

    def test_health(self):
        """Test QuickSearch health endpoint"""
        print_test("Testing QuickSearch health endpoint...")

        url = f"{self.base_url}/api/v2/quicksearch/health"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                print_success(f"Health check passed: {json.dumps(data, indent=2)}")
                return True
            else:
                print_error(f"Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Health check error: {e}")
            return False

    def create_dictionary(self):
        """Test dictionary creation from test file"""
        print_test(f"Creating dictionary from {TEST_FILE}...")

        url = f"{self.base_url}/api/v2/quicksearch/create-dictionary"

        # Check if file exists
        if not Path(TEST_FILE).exists():
            print_error(f"Test file not found: {TEST_FILE}")
            return False

        try:
            with open(TEST_FILE, 'rb') as f:
                files = {'files': ('test123.txt', f, 'text/plain')}
                data = {
                    'game': 'BDO',
                    'language': 'FR'
                }

                response = requests.post(url, files=files, data=data, headers=self.headers)

                if response.status_code == 200:
                    result = response.json()
                    print_success(f"Dictionary created successfully!")
                    print_info(f"  Pairs count: {result.get('pairs_count', 'N/A')}")
                    print_info(f"  Dictionary: {result.get('game', 'N/A')}-{result.get('language', 'N/A')}")
                    return True
                else:
                    print_error(f"Dictionary creation failed: {response.status_code}")
                    print_error(f"Response: {response.text}")
                    return False
        except Exception as e:
            print_error(f"Dictionary creation error: {e}")
            return False

    def load_dictionary(self):
        """Test loading a dictionary"""
        print_test("Loading dictionary...")

        url = f"{self.base_url}/api/v2/quicksearch/load-dictionary"
        data = {
            'game': 'BDO',
            'language': 'FR'
        }

        try:
            response = requests.post(url, json=data, headers=self.headers)

            if response.status_code == 200:
                result = response.json()
                print_success(f"Dictionary loaded successfully!")
                print_info(f"  Pairs count: {result.get('pairs_count', 'N/A')}")
                return True
            else:
                print_error(f"Dictionary loading failed: {response.status_code}")
                print_error(f"Response: {response.text}")
                return False
        except Exception as e:
            print_error(f"Dictionary loading error: {e}")
            return False

    def test_search(self, query="검은별"):
        """Test one-line search"""
        print_test(f"Testing search with query: '{query}'...")

        url = f"{self.base_url}/api/v2/quicksearch/search"
        data = {
            'query': query,
            'match_type': 'contains'
        }

        try:
            response = requests.post(url, json=data, headers=self.headers)

            if response.status_code == 200:
                result = response.json()
                results = result.get('results', [])
                print_success(f"Search successful! Found {len(results)} results")

                if results:
                    print_info("Sample results:")
                    for i, r in enumerate(results[:3]):
                        print(f"    {i+1}. KR: {r.get('korean', '')[:30]}...")
                        print(f"       FR: {r.get('translation', '')[:30]}...")
                        print(f"       ID: {r.get('string_id', 'N/A')}")
                return True
            else:
                print_error(f"Search failed: {response.status_code}")
                print_error(f"Response: {response.text}")
                return False
        except Exception as e:
            print_error(f"Search error: {e}")
            return False

    def test_multiline_search(self):
        """Test multi-line search"""
        print_test("Testing multi-line search...")

        url = f"{self.base_url}/api/v2/quicksearch/search-multiline"
        data = {
            'queries': ['검은별', '무기', '방어구'],
            'match_type': 'contains'
        }

        try:
            response = requests.post(url, json=data, headers=self.headers)

            if response.status_code == 200:
                result = response.json()
                print_success(f"Multi-line search successful!")

                for query, matches in result.get('results', {}).items():
                    print_info(f"  '{query}': {len(matches)} results")
                return True
            else:
                print_error(f"Multi-line search failed: {response.status_code}")
                print_error(f"Response: {response.text}")
                return False
        except Exception as e:
            print_error(f"Multi-line search error: {e}")
            return False

    def list_dictionaries(self):
        """Test listing dictionaries"""
        print_test("Listing available dictionaries...")

        url = f"{self.base_url}/api/v2/quicksearch/list-dictionaries"

        try:
            response = requests.get(url, headers=self.headers)

            if response.status_code == 200:
                result = response.json()
                dictionaries = result.get('dictionaries', [])
                print_success(f"Found {len(dictionaries)} dictionaries:")
                for d in dictionaries:
                    print_info(f"  {d.get('game', 'N/A')}-{d.get('language', 'N/A')} ({d.get('pairs_count', 0)} pairs)")
                return True
            else:
                print_error(f"List dictionaries failed: {response.status_code}")
                print_error(f"Response: {response.text}")
                return False
        except Exception as e:
            print_error(f"List dictionaries error: {e}")
            return False

    def run_all_tests(self):
        """Run complete test suite"""
        print(f"\n{'='*70}")
        print(f"{Colors.BLUE}QUICKSEARCH PHASE 4 TESTING{Colors.END}")
        print(f"{'='*70}\n")

        tests = [
            ("Health Check", self.test_health),
            ("User Registration", self.register_user),
            ("Dictionary Creation", self.create_dictionary),
            ("Dictionary Loading", self.load_dictionary),
            ("List Dictionaries", self.list_dictionaries),
            ("One-Line Search", self.test_search),
            ("Multi-Line Search", self.test_multiline_search),
        ]

        results = []
        for name, test_func in tests:
            try:
                success = test_func()
                results.append((name, success))
                time.sleep(0.5)  # Brief pause between tests
            except Exception as e:
                print_error(f"{name} crashed: {e}")
                results.append((name, False))

        # Summary
        print(f"\n{'='*70}")
        print(f"{Colors.BLUE}TEST SUMMARY{Colors.END}")
        print(f"{'='*70}\n")

        passed = sum(1 for _, success in results if success)
        total = len(results)

        for name, success in results:
            status = f"{Colors.GREEN}✓ PASSED{Colors.END}" if success else f"{Colors.RED}✗ FAILED{Colors.END}"
            print(f"  {name:30} {status}")

        print(f"\n{'='*70}")
        print(f"Results: {passed}/{total} tests passed ({passed*100//total}%)")
        print(f"{'='*70}\n")

        return passed == total

if __name__ == "__main__":
    tester = QuickSearchTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)
