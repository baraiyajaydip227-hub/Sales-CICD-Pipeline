
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent

# Required QVF generation prerequisites
REQUIRED_FILES = [
    "Sales_ERD.md",
    "sql/bi_views/vw_sales.sql",
    "qvs/qvd/Generate_Sales.qvs"
]

def validate_prerequisites():
    print("Checking QVF generation prerequisites...")

    missing = []

    for file in REQUIRED_FILES:
        path = ROOT / file

        if path.exists():
            print(f"[OK] {file}")
        else:
            print(f"[MISSING] {file}")
            missing.append(file)

    if missing:
        print("\nPrerequisites validation failed.")
        sys.exit(1)

    print("\nAll prerequisites are available.")

if __name__ == "__main__":
    validate_prerequisites()
