import json
import sys
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "pipeline_config.json"


def validate_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")

    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        config = json.load(file)

    required_sections = ["project", "source", "environments", "deployment"]

    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing configuration section: {section}")

    required_source_fields = ["qvd_name", "bi_view_path", "erd_file"]

    for field in required_source_fields:
        if not config["source"].get(field):
            raise ValueError(f"Missing source configuration: {field}")

    if not config["environments"]:
        raise ValueError("No deployment environments configured")

    print("Configuration validation successful!")
    print(f"Project: {config['project']['name']}")
    print(f"Base App: {config['project']['base_app']}")
    print(f"QVD: {config['source']['qvd_name']}")
    print(f"Environments: {' -> '.join(config['environments'])}")


if __name__ == "__main__":
    try:
        validate_config()
    except Exception as error:
        print(f"Validation failed: {error}")
        sys.exit(1)
