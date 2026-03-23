import sqlite3

# Connect to database (creates file if not exists)
conn = sqlite3.connect("complaints.db")

# Create cursor
cursor = conn.cursor()

# Create table
cursor.execute("""
CREATE TABLE IF NOT EXISTS complaints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    description TEXT,
    flat_no TEXT,
    block TEXT,
    image_path TEXT,
    status TEXT,
    priority TEXT,
    created_at TEXT,
    deadline_at TEXT
)
""")

# Save changes
conn.commit()

# Close connection
conn.close()

print("Database & Table Created Successfully ✅")