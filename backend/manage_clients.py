import sys
import os
from app.database.database import MasterSessionLocal, app_data_dir, get_client_engine
from app.models.client import Client
from app.main import check_and_migrate_db

def add_client(client_id: str, name: str):
    db = MasterSessionLocal()
    try:
        existing = db.query(Client).filter(Client.id == client_id).first()
        if existing:
            print(f"Error: Client with ID '{client_id}' already exists.")
            return

        db_filename = f"{client_id}.db"
        new_client = Client(id=client_id, name=name, db_filename=db_filename)
        db.add(new_client)
        db.commit()
        print(f"Successfully added client '{name}' ({client_id}).")
        
        # Initialize the new database
        print(f"Initializing database for '{client_id}'...")
        db_path = os.path.join(app_data_dir, db_filename)
        engine = get_client_engine(db_filename)
        check_and_migrate_db(db_path, engine)
        print("Initialization complete.")
        
    finally:
        db.close()

def list_clients():
    db = MasterSessionLocal()
    try:
        clients = db.query(Client).all()
        if not clients:
            print("No clients found.")
            return
            
        print(f"{'ID':<15} | {'Name':<25} | {'Database File':<15} | {'Active'}")
        print("-" * 75)
        for c in clients:
            print(f"{c.id:<15} | {c.name:<25} | {c.db_filename:<15} | {c.is_active}")
    finally:
        db.close()

def deactivate_client(client_id: str):
    db = MasterSessionLocal()
    try:
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            print(f"Error: Client '{client_id}' not found.")
            return
            
        client.is_active = False
        db.commit()
        print(f"Client '{client_id}' has been deactivated.")
    finally:
        db.close()

def print_usage():
    print("Usage:")
    print("  python manage_clients.py list")
    print("  python manage_clients.py add <client_id> <name>")
    print("  python manage_clients.py deactivate <client_id>")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
        
    command = sys.argv[1].lower()
    
    if command == "list":
        list_clients()
    elif command == "add":
        if len(sys.argv) < 4:
            print("Error: Missing arguments for 'add'.")
            print("Usage: python manage_clients.py add <client_id> <name>")
            sys.exit(1)
        add_client(sys.argv[2], " ".join(sys.argv[3:]))
    elif command == "deactivate":
        if len(sys.argv) < 3:
            print("Error: Missing argument for 'deactivate'.")
            print("Usage: python manage_clients.py deactivate <client_id>")
            sys.exit(1)
        deactivate_client(sys.argv[2])
    else:
        print(f"Unknown command: {command}")
        print_usage()
