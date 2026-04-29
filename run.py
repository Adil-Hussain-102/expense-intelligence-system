# run.py


import sys
from app.database.db import test_connection, create_all_tables
# run_dashboard.py
# Place this file in your project ROOT (same level as app/ and dashboard/)
# Run with: python run_dashboard.py

import sys
import os

# Add project root to Python path so all imports work correctly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now launch streamlit
import subprocess
subprocess.run([
    sys.executable, "-m", "streamlit", "run",
    os.path.join(os.path.dirname(__file__), "dashboard", "main.py")
])

def main():
    if len(sys.argv) < 2:
        print("""
Expense Intelligence System — CLI

Commands:
  python run.py test-db     Test database connection
  python run.py setup-db    Create all tables
  python run.py seed        Seed sample data
  python run.py dashboard   Launch Streamlit dashboard
        """)
        return

    command = sys.argv[1]

    if command == "test-db":
        test_connection()

    elif command == "setup-db":
        create_all_tables()

    elif command == "seed":
        from app.database.seed import run_seed
        run_seed()

    elif command == "dashboard":
        import subprocess
        subprocess.run(["streamlit", "run", "dashboard/main.py"])

    else:
        print(f"Unknown command: {command}")
        print("Run 'python run.py' to see available commands.")


if __name__ == "__main__":
    main()