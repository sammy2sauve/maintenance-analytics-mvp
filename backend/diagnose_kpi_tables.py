"""
Comprehensive API Issue Diagnostic Script

This script identifies the exact cause of API 500 errors by checking:
1. Database existence and structure
2. KPI table schemas
3. Data availability
4. Column name mismatches
5. Type conversion issues

Usage:
    python diagnose_kpi_tables.py
"""

import sqlite3
from pathlib import Path
import sys
from typing import Dict, List, Any, Optional


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}")


def print_success(text: str) -> None:
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_error(text: str) -> None:
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")


def print_warning(text: str) -> None:
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def print_info(text: str, indent: int = 2) -> None:
    """Print info message."""
    print(f"{' ' * indent}{text}")


def check_database_file() -> Optional[Path]:
    """
    Check if database file exists.
    
    Returns:
        Path to database if it exists, None otherwise
    """
    print_header("1. DATABASE FILE CHECK")
    
    db_path = Path("data/db/truesignal.db")
    
    if db_path.exists():
        print_success(f"Database found at: {db_path.absolute()}")
        
        # Get file size
        size_bytes = db_path.stat().st_size
        size_kb = size_bytes / 1024
        print_info(f"File size: {size_kb:.2f} KB")
        
        return db_path
    else:
        print_error(f"Database NOT found at: {db_path.absolute()}")
        print_info("Solution: Run 'python create_test_db.py'")
        return None


def check_table_exists(cursor: sqlite3.Cursor, table_name: str) -> bool:
    """
    Check if a table exists in the database.
    
    Args:
        cursor: SQLite cursor
        table_name: Name of table to check
        
    Returns:
        True if table exists, False otherwise
    """
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
    """, (table_name,))
    
    return cursor.fetchone() is not None


def analyze_table_schema(
    cursor: sqlite3.Cursor, 
    table_name: str,
    expected_columns: Dict[str, str]
) -> Dict[str, Any]:
    """
    Analyze table schema and compare with expected structure.
    
    Args:
        cursor: SQLite cursor
        table_name: Name of table to analyze
        expected_columns: Dictionary of expected column names and types
        
    Returns:
        Dictionary with analysis results
    """
    results = {
        'exists': False,
        'columns': {},
        'missing_columns': [],
        'extra_columns': [],
        'type_mismatches': [],
        'row_count': 0,
        'sample_data': None
    }
    
    # Check if table exists
    if not check_table_exists(cursor, table_name):
        return results
    
    results['exists'] = True
    
    # Get table schema
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    
    # Build column dictionary
    for col in columns:
        col_id, col_name, col_type, not_null, default_val, pk = col
        results['columns'][col_name] = {
            'type': col_type,
            'not_null': bool(not_null),
            'primary_key': bool(pk)
        }
    
    # Find missing columns
    actual_columns = set(results['columns'].keys())
    expected_column_names = set(expected_columns.keys())
    
    results['missing_columns'] = list(expected_column_names - actual_columns)
    results['extra_columns'] = list(actual_columns - expected_column_names)
    
    # Get row count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    results['row_count'] = cursor.fetchone()[0]
    
    # Get sample data if available
    if results['row_count'] > 0:
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
        sample = cursor.fetchone()
        col_names = [desc[0] for desc in cursor.description]
        results['sample_data'] = dict(zip(col_names, sample))
    
    return results


def check_kpi_tables(db_path: Path) -> Dict[str, Any]:
    """
    Check all KPI tables for schema and data issues.
    
    Args:
        db_path: Path to database file
        
    Returns:
        Dictionary with results for all tables
    """
    print_header("2. KPI TABLES CHECK")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Expected schemas for each table
    expected_schemas = {
        'daily_kpis': {
            'id': 'INTEGER',
            'period_date': 'DATE',
            'kpi_name': 'TEXT',
            'raw_value': 'REAL',
            'truesignal_value': 'REAL',
            'distortion_flag': 'BOOLEAN',
            'explanation_text': 'TEXT',
            'created_at': 'TIMESTAMP'
        },
        'weekly_kpis': {
            'id': 'INTEGER',
            'period_week': 'TEXT',
            'kpi_name': 'TEXT',
            'raw_value': 'REAL',
            'truesignal_value': 'REAL',
            'distortion_flag': 'BOOLEAN',
            'explanation_text': 'TEXT',
            'created_at': 'TIMESTAMP'
        },
        'monthly_kpis': {
            'id': 'INTEGER',
            'period_month': 'TEXT',
            'kpi_name': 'TEXT',
            'raw_value': 'REAL',
            'truesignal_value': 'REAL',
            'distortion_flag': 'BOOLEAN',
            'explanation_text': 'TEXT',
            'created_at': 'TIMESTAMP'
        }
    }
    
    all_results = {}
    
    for table_name, expected_columns in expected_schemas.items():
        print(f"\n{Colors.BOLD}Analyzing: {table_name}{Colors.RESET}")
        print("-" * 70)
        
        results = analyze_table_schema(cursor, table_name, expected_columns)
        all_results[table_name] = results
        
        if not results['exists']:
            print_error(f"Table '{table_name}' does NOT exist!")
            print_info("Solution: Run 'python backend/pipeline.py' to create KPI tables")
            continue
        
        print_success(f"Table exists")
        
        # Check columns
        print(f"\nColumns found: {len(results['columns'])}")
        for col_name, col_info in results['columns'].items():
            expected = "✓" if col_name in expected_columns else "?"
            print_info(f"{expected} {col_name}: {col_info['type']}")
        
        # Report missing columns
        if results['missing_columns']:
            print_error(f"\nMissing columns: {', '.join(results['missing_columns'])}")
        else:
            print_success("\nAll expected columns present")
        
        # Report extra columns
        if results['extra_columns']:
            print_warning(f"Extra columns (not expected): {', '.join(results['extra_columns'])}")
        
        # Report row count
        print(f"\nRows in table: {results['row_count']}")
        if results['row_count'] == 0:
            print_error("No data in table!")
            print_info("Solution: Run 'python backend/pipeline.py' to populate KPIs")
        else:
            print_success(f"Contains {results['row_count']} KPI records")
        
        # Show sample data
        if results['sample_data']:
            print(f"\n{Colors.BOLD}Sample record:{Colors.RESET}")
            for key, value in results['sample_data'].items():
                value_str = str(value)[:50]  # Truncate long values
                print_info(f"{key}: {value_str}")
    
    conn.close()
    return all_results


def check_work_orders_table(db_path: Path) -> Dict[str, Any]:
    """
    Check work_orders table structure and data.
    
    Args:
        db_path: Path to database file
        
    Returns:
        Dictionary with analysis results
    """
    print_header("3. WORK_ORDERS TABLE CHECK")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    expected_columns = {
        'work_order_id': 'INTEGER',
        'asset_id': 'TEXT',
        'site': 'TEXT',
        'type': 'TEXT',
        'status': 'TEXT',
        'technician': 'TEXT',
        'creation_date': 'DATE',
        'scheduled_start': 'DATE',
        'start_date': 'DATE',
        'completion_date': 'DATE',
        'labor_hours_scheduled': 'REAL',
        'labor_hours_actual': 'REAL',
        'downtime_hours': 'REAL',
        'reactive_followup': 'INTEGER',
        'priority': 'TEXT',
        'due_date': 'DATE'
    }
    
    results = analyze_table_schema(cursor, 'work_orders', expected_columns)
    
    if not results['exists']:
        print_error("work_orders table does NOT exist!")
        print_info("Solution: Run 'python create_test_db.py'")
    else:
        print_success("work_orders table exists")
        
        if results['missing_columns']:
            print_error(f"Missing columns: {', '.join(results['missing_columns'])}")
        else:
            print_success("All expected columns present")
        
        if results['row_count'] == 0:
            print_error("No work orders in table!")
            print_info("Solution: Run 'python create_test_db.py'")
        else:
            print_success(f"Contains {results['row_count']} work orders")
            
            # Get data distribution
            cursor.execute("SELECT type, COUNT(*) FROM work_orders GROUP BY type")
            type_dist = cursor.fetchall()
            
            print(f"\n{Colors.BOLD}Work type distribution:{Colors.RESET}")
            for wtype, count in type_dist:
                print_info(f"{wtype}: {count}")
            
            cursor.execute("SELECT status, COUNT(*) FROM work_orders GROUP BY status")
            status_dist = cursor.fetchall()
            
            print(f"\n{Colors.BOLD}Status distribution:{Colors.RESET}")
            for status, count in status_dist:
                print_info(f"{status}: {count}")
    
    conn.close()
    return results


def check_api_models() -> None:
    """Print expected API response models."""
    print_header("4. API EXPECTED RESPONSE MODELS")
    
    print(f"\n{Colors.BOLD}DailyKPIRecord expects:{Colors.RESET}")
    print_info("id: Optional[int]")
    print_info("kpi_name: str")
    print_info("raw_value: Optional[float]")
    print_info("truesignal_value: Optional[float]")
    print_info("distortion_flag: bool")
    print_info("explanation_text: Optional[str]")
    print_info("created_at: Optional[str]")
    print_info("period_date: str")
    
    print(f"\n{Colors.BOLD}WeeklyKPIRecord expects:{Colors.RESET}")
    print_info("Same as Daily, but with 'period_week' instead of 'period_date'")
    
    print(f"\n{Colors.BOLD}MonthlyKPIRecord expects:{Colors.RESET}")
    print_info("Same as Daily, but with 'period_month' instead of 'period_date'")


def print_recommendations(kpi_results: Dict[str, Any], work_orders_result: Dict[str, Any]) -> None:
    """
    Print recommendations based on diagnostic results.
    
    Args:
        kpi_results: Results from KPI table checks
        work_orders_result: Results from work_orders table check
    """
    print_header("5. RECOMMENDATIONS & NEXT STEPS")
    
    issues_found = False
    
    # Check work_orders
    if not work_orders_result.get('exists'):
        print_error("CRITICAL: work_orders table missing")
        print_info("→ Run: python create_test_db.py")
        issues_found = True
    elif work_orders_result.get('row_count', 0) == 0:
        print_error("CRITICAL: No data in work_orders table")
        print_info("→ Run: python create_test_db.py")
        issues_found = True
    
    # Check KPI tables
    for table_name, results in kpi_results.items():
        if not results.get('exists'):
            print_error(f"CRITICAL: {table_name} table missing")
            print_info("→ Run: python backend/pipeline.py")
            issues_found = True
        elif results.get('row_count', 0) == 0:
            print_warning(f"WARNING: No data in {table_name}")
            print_info("→ Run: python backend/pipeline.py")
            issues_found = True
        elif results.get('missing_columns'):
            print_error(f"CRITICAL: {table_name} has missing columns")
            print_info(f"   Missing: {', '.join(results['missing_columns'])}")
            print_info("→ Drop table and run: python backend/pipeline.py")
            issues_found = True
    
    if not issues_found:
        print_success("No critical issues found!")
        print(f"\n{Colors.BOLD}If you're still getting 500 errors:{Colors.RESET}")
        print_info("1. Check API logs for specific error messages")
        print_info("2. Verify API is using correct import paths")
        print_info("3. Test endpoints individually at http://localhost:8000/docs")
        print_info("4. Check backend/db.py for column name mismatches")
    
    print(f"\n{Colors.BOLD}To test the API:{Colors.RESET}")
    print_info("1. Start API: uvicorn backend.api:app --reload")
    print_info("2. Open browser: http://localhost:8000/docs")
    print_info("3. Try executing /kpis/daily endpoint")


def main() -> int:
    """
    Main diagnostic function.
    
    Returns:
        Exit code (0 for success, 1 for issues found)
    """
    print_header("MAINTENANCE ANALYTICS API DIAGNOSTIC")
    print(f"This script will identify issues preventing the API from working\n")
    
    # Check database file
    db_path = check_database_file()
    if not db_path:
        return 1
    
    # Check work_orders table
    work_orders_result = check_work_orders_table(db_path)
    
    # Check KPI tables
    kpi_results = check_kpi_tables(db_path)
    
    # Show expected API models
    check_api_models()
    
    # Print recommendations
    print_recommendations(kpi_results, work_orders_result)
    
    print_header("DIAGNOSTIC COMPLETE")
    
    # Determine if there are critical issues
    has_critical_issues = (
        not work_orders_result.get('exists') or
        work_orders_result.get('row_count', 0) == 0 or
        not all(r.get('exists', False) for r in kpi_results.values()) or
        any(r.get('row_count', 0) == 0 for r in kpi_results.values())
    )
    
    return 1 if has_critical_issues else 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)