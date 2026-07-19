import sqlite3
import os
import platform

APP_NAME = "SynthbitAMS"

def get_db_path():
    if platform.system() == "Windows":
        app_data_dir = os.path.join(os.environ.get("APPDATA", ""), APP_NAME)
    elif platform.system() == "Darwin":
        app_data_dir = os.path.expanduser(f"~/Library/Application Support/{APP_NAME}")
    else:
        app_data_dir = os.path.expanduser(f"~/.local/share/{APP_NAME}")
    
    return os.path.join(app_data_dir, "ams.db")

def migrate():
    db_path = get_db_path()
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}. Skipping migration.")
        return
        
    print(f"Connecting to database at {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Add email to employees
    try:
        cursor.execute("ALTER TABLE employees ADD COLUMN email VARCHAR")
        print("Successfully added 'email' column to employees table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column 'email' already exists in employees table.")
        else:
            print(f"Error altering employees table: {e}")
            
    # 2. Add company_name and hr_email to device_config
    try:
        cursor.execute("ALTER TABLE device_config ADD COLUMN company_name VARCHAR DEFAULT 'Synthbit Technologies'")
        print("Successfully added 'company_name' column to device_config table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column 'company_name' already exists in device_config table.")
        else:
            print(f"Error altering device_config table: {e}")
            
    try:
        cursor.execute("ALTER TABLE device_config ADD COLUMN hr_email VARCHAR DEFAULT 'hr@synthbit.com'")
        print("Successfully added 'hr_email' column to device_config table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column 'hr_email' already exists in device_config table.")
        else:
            print(f"Error altering device_config table: {e}")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
