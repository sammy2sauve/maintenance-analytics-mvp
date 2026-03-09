import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / "data" / "db" / "truesignal.db"
conn = sqlite3.connect(db_path)

# Delete old duplicates
conn.execute("DELETE FROM maintenance_insights WHERE insight_type = 'day_of_week_pattern' AND id > 1")
conn.commit()

# Check what's left
cursor = conn.execute("SELECT insight_type, title FROM maintenance_insights")
for row in cursor.fetchall():
    print(row)

conn.close()