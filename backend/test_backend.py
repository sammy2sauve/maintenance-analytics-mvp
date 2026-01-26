"""
Backend API test script for maintenance analytics MVP.

This script tests all KPI endpoints, validates response structure,
and reports on data quality and API health.

Usage:
    python backend/test_backend.py
"""

import requests
from typing import Dict, List, Any, Optional, Tuple
import sys
from datetime import datetime


class APITestError(Exception):
    """Custom exception for API test failures."""
    pass


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.RESET}\n")


def print_success(text: str) -> None:
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_error(text: str) -> None:
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")


def print_warning(text: str) -> None:
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def print_info(text: str) -> None:
    """Print info message."""
    print(f"  {text}")


def check_api_health(base_url: str) -> bool:
    """
    Check if the API is running and healthy.
    
    Args:
        base_url: Base URL of the API
        
    Returns:
        True if API is healthy, False otherwise
    """
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                print_success(f"API is healthy at {base_url}")
                return True
            else:
                print_warning(f"API returned status: {data.get('status')}")
                return True  # API is responding, even if degraded
        else:
            print_error(f"Health check failed with status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error(f"Could not connect to API at {base_url}")
        print_info("Make sure the API is running with: uvicorn backend.api:app --reload")
        return False
    except requests.exceptions.Timeout:
        print_error("API health check timed out")
        return False
    except Exception as e:
        print_error(f"Unexpected error during health check: {str(e)}")
        return False


def validate_kpi_fields(kpi: Dict[str, Any], endpoint_name: str) -> Tuple[bool, List[str]]:
    """
    Validate that a KPI object has all required fields.
    
    Args:
        kpi: KPI object dictionary
        endpoint_name: Name of the endpoint being tested
        
    Returns:
        Tuple of (is_valid, list_of_missing_fields)
    """
    # Required fields based on endpoint type
    if endpoint_name == "daily":
        required_fields = {
            "kpi_name": str,
            "period_date": str,
            "raw_value": (int, float, type(None)),
            "truesignal_value": (int, float, type(None)),
            "distortion_flag": (bool, int),
            "explanation_text": (str, type(None))
        }
    elif endpoint_name == "weekly":
        required_fields = {
            "kpi_name": str,
            "period_week": str,
            "raw_value": (int, float, type(None)),
            "truesignal_value": (int, float, type(None)),
            "distortion_flag": (bool, int),
            "explanation_text": (str, type(None))
        }
    elif endpoint_name == "monthly":
        required_fields = {
            "kpi_name": str,
            "period_month": str,
            "raw_value": (int, float, type(None)),
            "truesignal_value": (int, float, type(None)),
            "distortion_flag": (bool, int),
            "explanation_text": (str, type(None))
        }
    else:
        required_fields = {}
    
    missing_fields = []
    type_errors = []
    
    for field, expected_type in required_fields.items():
        if field not in kpi:
            missing_fields.append(field)
        else:
            value = kpi[field]
            if not isinstance(value, expected_type):
                type_errors.append(f"{field} (expected {expected_type}, got {type(value)})")
    
    is_valid = len(missing_fields) == 0 and len(type_errors) == 0
    errors = missing_fields + type_errors
    
    return is_valid, errors


def test_endpoint(
    base_url: str,
    endpoint: str,
    endpoint_name: str,
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Test a single KPI endpoint.
    
    Args:
        base_url: Base URL of the API
        endpoint: Endpoint path (e.g., "/kpis/daily")
        endpoint_name: Human-readable name for reporting
        params: Optional query parameters
        
    Returns:
        Dictionary with test results
    """
    url = f"{base_url}{endpoint}"
    
    results = {
        "endpoint": endpoint_name,
        "url": url,
        "success": False,
        "status_code": None,
        "kpi_count": 0,
        "valid_kpis": 0,
        "invalid_kpis": 0,
        "errors": [],
        "warnings": [],
        "sample_kpi": None
    }
    
    try:
        # Make request
        response = requests.get(url, params=params, timeout=10)
        results["status_code"] = response.status_code
        
        # Check status code
        if response.status_code != 200:
            results["errors"].append(f"Expected status 200, got {response.status_code}")
            return results
        
        # Parse JSON
        try:
            data = response.json()
        except ValueError as e:
            results["errors"].append(f"Failed to parse JSON: {str(e)}")
            return results
        
        # Check if data is a list
        if not isinstance(data, list):
            results["errors"].append(f"Expected list, got {type(data)}")
            return results
        
        results["kpi_count"] = len(data)
        
        # If empty, that's a warning but not an error
        if len(data) == 0:
            results["warnings"].append("No KPIs returned (empty result set)")
            results["success"] = True
            return results
        
        # Validate each KPI
        field_errors = {}
        
        for i, kpi in enumerate(data):
            is_valid, errors = validate_kpi_fields(kpi, endpoint_name)
            
            if is_valid:
                results["valid_kpis"] += 1
            else:
                results["invalid_kpis"] += 1
                for error in errors:
                    if error not in field_errors:
                        field_errors[error] = []
                    field_errors[error].append(i)
        
        # Store sample KPI for inspection
        if data:
            results["sample_kpi"] = data[0]
        
        # Add field errors to results
        for field, indices in field_errors.items():
            count = len(indices)
            results["errors"].append(
                f"Missing/invalid field '{field}' in {count} KPI(s)"
            )
        
        # Mark as successful if we got valid data
        results["success"] = results["invalid_kpis"] == 0
        
    except requests.exceptions.ConnectionError:
        results["errors"].append("Connection error - is the API running?")
    except requests.exceptions.Timeout:
        results["errors"].append("Request timed out")
    except Exception as e:
        results["errors"].append(f"Unexpected error: {str(e)}")
    
    return results


def print_test_results(results: Dict[str, Any]) -> None:
    """
    Print formatted test results for an endpoint.
    
    Args:
        results: Test results dictionary
    """
    print(f"\n{Colors.BOLD}Endpoint: {results['endpoint'].upper()}{Colors.RESET}")
    print(f"URL: {results['url']}")
    print(f"Status Code: {results['status_code']}")
    
    if results["success"]:
        print_success(f"Test passed")
    else:
        print_error(f"Test failed")
    
    print(f"\nResults:")
    print_info(f"Total KPIs: {results['kpi_count']}")
    print_info(f"Valid KPIs: {results['valid_kpis']}")
    
    if results["invalid_kpis"] > 0:
        print_info(f"{Colors.RED}Invalid KPIs: {results['invalid_kpis']}{Colors.RESET}")
    
    # Print errors
    if results["errors"]:
        print(f"\n{Colors.RED}Errors:{Colors.RESET}")
        for error in results["errors"]:
            print_error(error)
    
    # Print warnings
    if results["warnings"]:
        print(f"\n{Colors.YELLOW}Warnings:{Colors.RESET}")
        for warning in results["warnings"]:
            print_warning(warning)
    
    # Print sample KPI
    if results["sample_kpi"]:
        print(f"\nSample KPI:")
        print_info(f"Name: {results['sample_kpi'].get('kpi_name', 'N/A')}")
        print_info(f"Raw Value: {results['sample_kpi'].get('raw_value', 'N/A')}")
        print_info(f"TrueSignal Value: {results['sample_kpi'].get('truesignal_value', 'N/A')}")
        print_info(f"Distortion: {results['sample_kpi'].get('distortion_flag', 'N/A')}")


def run_all_tests(base_url: str = "http://localhost:8000") -> bool:
    """
    Run all API tests.
    
    Args:
        base_url: Base URL of the API
        
    Returns:
        True if all tests passed, False otherwise
    """
    print_header("MAINTENANCE ANALYTICS BACKEND API TEST")
    print(f"Testing API at: {base_url}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check API health first
    print_header("HEALTH CHECK")
    if not check_api_health(base_url):
        print_error("\nAPI health check failed. Aborting tests.")
        return False
    
    # Define endpoints to test
    endpoints = [
        ("/kpis/daily", "daily"),
        ("/kpis/weekly", "weekly"),
        ("/kpis/monthly", "monthly")
    ]
    
    # Run tests
    print_header("ENDPOINT TESTS")
    
    all_results = []
    
    for endpoint, name in endpoints:
        results = test_endpoint(base_url, endpoint, name)
        all_results.append(results)
        print_test_results(results)
    
    # Print summary
    print_header("TEST SUMMARY")
    
    total_tests = len(all_results)
    passed_tests = sum(1 for r in all_results if r["success"])
    failed_tests = total_tests - passed_tests
    
    total_kpis = sum(r["kpi_count"] for r in all_results)
    total_valid = sum(r["valid_kpis"] for r in all_results)
    total_invalid = sum(r["invalid_kpis"] for r in all_results)
    
    print(f"Tests Run: {total_tests}")
    print(f"Tests Passed: {Colors.GREEN}{passed_tests}{Colors.RESET}")
    
    if failed_tests > 0:
        print(f"Tests Failed: {Colors.RED}{failed_tests}{Colors.RESET}")
    else:
        print(f"Tests Failed: {failed_tests}")
    
    print(f"\nTotal KPIs Retrieved: {total_kpis}")
    print(f"Valid KPIs: {Colors.GREEN}{total_valid}{Colors.RESET}")
    
    if total_invalid > 0:
        print(f"Invalid KPIs: {Colors.RED}{total_invalid}{Colors.RESET}")
    else:
        print(f"Invalid KPIs: {total_invalid}")
    
    # Final verdict
    print()
    if failed_tests == 0 and total_invalid == 0:
        print_success("ALL TESTS PASSED! ✨")
        return True
    else:
        print_error("SOME TESTS FAILED")
        return False


def main() -> int:
    """
    Main entry point for test script.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Allow custom base URL from command line
        if len(sys.argv) > 1:
            base_url = sys.argv[1]
        else:
            base_url = "http://localhost:8000"
        
        success = run_all_tests(base_url)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 1
    except Exception as e:
        print_error(f"\nUnexpected error: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)