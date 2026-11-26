
import json
import sys
from pathlib import Path

# Repository root
ROOT = Path(__file__).resolve().parents[2]

CONFIG_FILE = ROOT / ".github" / "config" / "pipeline_config.json"


def load_config():
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Config not found: {CONFIG_FILE}")

    with open(CONFIG_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def validate_prerequisites(config):
    print("Checking QVF generation prerequisites...")

    source = config["source"]

    required_files = [
        source["erd_file"],
        str(Path(source["bi_view_path"]) / "vw_sales.sql"),
        "qvs/qvd/Generate_Sales.qvs"
    ]

    missing = []

    for file in required_files:
        path = ROOT / file

        if path.is_file():
            print(f"[OK] {file}")
        else:
            print(f"[MISSING] {file}")
            missing.append(file)

    if missing:
        print("\nPrerequisites validation failed.")
        sys.exit(1)

    print("\nAll prerequisites are available.")
    print(f"Base Application: {config['project']['base_app']}")
    print(f"QVD Name: {source['qvd_name']}")
    print(f"BI Connection: {config['connections']['bi_connection']}")
    print(f"QVD Connection: {config['connections']['qvd_connection']}")

    return True


if __name__ == "__main__":
    try:
        config = load_config()
        validate_prerequisites(config)
    except Exception as error:
        print(f"\nERROR: {error}")
        sys.exit(1)
