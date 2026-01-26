"""
SQLite database generator for maintenance analytics MVP.

This script creates a test database with dummy work order data
for testing the KPI calculation pipeline.

Usage:
    python create_test_db.py
"""

import sqlite3
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple, Optional


def create_database_folder() -> Path:
    """
    Create the data/db folder structure if it doesn't exist.
    
    Returns:
        Path object pointing to the db folder
    """
    db_folder = Path("data") / "db"
    db_folder.mkdir(parents=True, exist_ok=True)
    print(f"✓ Created folder: {db_folder}")
    return db_folder


def create_work_orders_table(conn: sqlite3.Connection) -> None:
    """
    Create the work_orders table with required schema.
    
    Args:
        conn: SQLite connection object
    """
    cursor = conn.cursor()
    
    cursor.execute("""
        DROP TABLE IF EXISTS work_orders
    """)
    
    cursor.execute("""
        CREATE TABLE work_orders (
            work_order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id TEXT,
            site TEXT,
            type TEXT,
            status TEXT,
            technician TEXT,
            creation_date DATE,
            scheduled_start DATE,
            start_date DATE,
            completion_date DATE,
            labor_hours_scheduled REAL,
            labor_hours_actual REAL,
            downtime_hours REAL,
            reactive_followup INTEGER,
            priority TEXT,
            due_date DATE
        )
    """)
    
    conn.commit()
    print("✓ Created work_orders table")


def generate_random_date(start_days_ago: int, end_days_ago: int) -> datetime:
    """
    Generate a random date within a range.
    
    Args:
        start_days_ago: Start of range (days before today)
        end_days_ago: End of range (days before today)
        
    Returns:
        Random datetime object
    """
    days_ago = random.randint(end_days_ago, start_days_ago)
    return datetime.now() - timedelta(days=days_ago)


def generate_work_orders(count: int = 50) -> List[Tuple]:
    """
    Generate dummy work order data.
    
    Args:
        count: Number of work orders to generate
        
    Returns:
        List of tuples containing work order data
    """
    work_types = ['PM', 'Reactive', 'Emergency']
    statuses = ['Completed', 'Pending', 'In Progress', 'Cancelled']
    technicians = [
        'John Smith', 'Jane Doe', 'Bob Johnson', 'Alice Williams',
        'Charlie Brown', 'Diana Martinez', 'Frank Wilson', 'Grace Lee'
    ]
    sites = ['Site A', 'Site B', 'Site C', 'Site D']
    priorities = ['Normal', 'High', 'Emergency']
    
    work_orders = []
    
    for i in range(1, count + 1):
        work_type = random.choice(work_types)
        status = random.choice(statuses)
        technician = random.choice(technicians)
        site = random.choice(sites)
        
        # Generate asset_id
        asset_id = f"ASSET-{random.randint(100, 999)}"
        
        # Set priority based on work type
        if work_type == 'Emergency':
            priority = 'Emergency'
        elif work_type == 'PM':
            priority = 'Normal'
        else:
            priority = random.choice(['Normal', 'High'])
        
        # Generate dates
        creation_date = generate_random_date(60, 45)
        scheduled_start = creation_date + timedelta(days=random.randint(1, 7))
        due_date = scheduled_start + timedelta(days=random.randint(1, 14))
        
        # For completed work orders, generate actual dates
        if status == 'Completed':
            start_date = scheduled_start + timedelta(days=random.randint(-1, 2))
            completion_date = start_date + timedelta(hours=random.randint(2, 48))
            
            # Calculate labor hours
            labor_hours_scheduled = round(random.uniform(1, 8), 2)
            labor_hours_actual = round(labor_hours_scheduled * random.uniform(0.7, 1.3), 2)
            downtime_hours = round(random.uniform(0, 8), 2) if work_type == 'Reactive' else 0
            
        elif status == 'In Progress':
            start_date = scheduled_start + timedelta(days=random.randint(-1, 2))
            completion_date = None
            labor_hours_scheduled = round(random.uniform(1, 8), 2)
            labor_hours_actual = round(random.uniform(0, labor_hours_scheduled), 2)
            downtime_hours = round(random.uniform(0, 4), 2) if work_type == 'Reactive' else 0
            
        else:  # Pending or Cancelled
            start_date = None
            completion_date = None
            labor_hours_scheduled = round(random.uniform(1, 8), 2)
            labor_hours_actual = 0
            downtime_hours = 0
        
        # Reactive followup flag
        reactive_followup = 1 if (work_type == 'Reactive' and random.random() < 0.3) else 0
        
        work_order = (
            asset_id,
            site,
            work_type,
            status,
            technician,
            creation_date.strftime('%Y-%m-%d'),
            scheduled_start.strftime('%Y-%m-%d'),
            start_date.strftime('%Y-%m-%d') if start_date else None,
            completion_date.strftime('%Y-%m-%d') if completion_date else None,
            labor_hours_scheduled,
            labor_hours_actual,
            downtime_hours,
            reactive_followup,
            priority,
            due_date.strftime('%Y-%m-%d')
        )
        
        work_orders.append(work_order)
    
    return work_orders


def insert_work_orders(conn: sqlite3.Connection, work_orders: List[Tuple]) -> None:
    """
    Insert work orders into the database.
    
    Args:
        conn: SQLite connection object
        work_orders: List of work order tuples
    """
    cursor = conn.cursor()
    
    cursor.executemany("""
        INSERT INTO work_orders (
            asset_id, site, type, status, technician,
            creation_date, scheduled_start, start_date, completion_date,
            labor_hours_scheduled, labor_hours_actual, downtime_hours,
            reactive_followup, priority, due_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, work_orders)
    
    conn.commit()
    print(f"✓ Inserted {len(work_orders)} work orders")


def print_database_stats(conn: sqlite3.Connection) -> None:
    """
    Print statistics about the generated database.
    
    Args:
        conn: SQLite connection object
    """
    cursor = conn.cursor()
    
    # Total count
    cursor.execute("SELECT COUNT(*) FROM work_orders")
    total = cursor.fetchone()[0]
    
    # By work type
    cursor.execute("""
        SELECT type, COUNT(*) 
        FROM work_orders 
        GROUP BY type
    """)
    by_type = cursor.fetchall()
    
    # By status
    cursor.execute("""
        SELECT status, COUNT(*) 
        FROM work_orders 
        GROUP BY status
    """)
    by_status = cursor.fetchall()
    
    # Completed work orders
    cursor.execute("""
        SELECT COUNT(*) 
        FROM work_orders 
        WHERE status = 'Completed'
    """)
    completed = cursor.fetchone()[0]
    
    print("\n" + "=" * 60)
    print("DATABASE STATISTICS")
    print("=" * 60)
    print(f"Total work orders: {total}")
    print(f"\nBy work type:")
    for wtype, count in by_type:
        print(f"  {wtype}: {count}")
    print(f"\nBy status:")
    for status, count in by_status:
        print(f"  {status}: {count}")
    print(f"\nCompleted work orders: {completed}")
    print("=" * 60)


def main() -> None:
    """
    Main function to create and populate the database.
    """
    print("Creating TrueSignal maintenance analytics database...")
    print()
    
    # Create folder structure
    db_folder = create_database_folder()
    db_path = db_folder / "truesignal.db"
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    print(f"✓ Connected to database: {db_path}")
    
    try:
        # Create table
        create_work_orders_table(conn)
        
        # Generate and insert data
        print("Generating work order data...")
        work_orders = generate_work_orders(count=150)  # Generate 150 for better testing
        insert_work_orders(conn, work_orders)
        
        # Print statistics
        print_database_stats(conn)
        
        print(f"\n✅ Database created successfully at: {db_path.absolute()}")
        print("You can now run the KPI pipeline with: python backend/pipeline.py")
        
    finally:
        conn.close()


if __name__ == "__main__":
    main()