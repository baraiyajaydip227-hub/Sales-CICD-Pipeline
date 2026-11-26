
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / ".github/config/pipeline_config.json"


def load_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Config file not found: {CONFIG_PATH}"
        )

    with open(CONFIG_PATH, encoding="utf-8") as file:
        return json.load(file)


def export_qvf():
    config = load_config()

    tenant = os.environ["QLIK_TENANT_URL"].rstrip("/")
    token = os.environ["QLIK_ACCESS_TOKEN"]
    app_id = os.environ["QLIK_APP_ID"]

    if not app_id:
        raise RuntimeError("Dynamic Base App ID is missing.")

    app_name = config["project"]["base_app"]
    no_data = config["deployment"]["no_data"]

    if no_data is not True:
        raise RuntimeError(
            "No-data export must be enabled in pipeline_config.json."
        )

    export_url = (
        f"{tenant}/api/v1/apps/{app_id}/export?NoData=true"
    )

    request = urllib.request.Request(
        export_url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        },
        method="POST"
    )

    print("Starting Qlik Cloud QVF export...")
    print(f"Base Application: {app_name}")
    print("No-Data Export: Enabled")

    try:
        with urllib.request.urlopen(
            request, timeout=120
        ) as response:
            download_url = response.headers.get("Location")

        if not download_url:
            raise RuntimeError(
                "Qlik export URL was not returned."
            )

        if download_url.startswith("/"):
            download_url = tenant + download_url

        download_request = urllib.request.Request(
            download_url,
            headers={
                "Authorization": f"Bearer {token}"
            }
        )

        with urllib.request.urlopen(
            download_request, timeout=300
        ) as response:
            qvf_data = response.read()

        if not qvf_data:
            raise RuntimeError(
                "Exported QVF file is empty."
            )

        version = os.environ.get(
            "GITHUB_RUN_NUMBER", "local"
        )

        commit = os.environ.get(
            "GITHUB_SHA", "local"
        )[:7]

        timestamp = datetime.now(
            timezone.utc
        ).strftime("%Y%m%dT%H%M%SZ")

        output_dir = ROOT / "dist"
        output_dir.mkdir(
            parents=True, exist_ok=True
        )

        filename = (
            f"{app_name}-v{version}-{commit}-{timestamp}.qvf"
        )

        output_path = output_dir / filename
        output_path.write_bytes(qvf_data)

        print("QVF export successful.")
        print(f"Artifact: {filename}")
        print(f"Size: {len(qvf_data)} bytes")

        github_output = os.environ.get("GITHUB_OUTPUT")

        if github_output:
            with open(
                github_output, "a", encoding="utf-8"
            ) as file:
                file.write(
                    f"qvf_path=dist/{filename}\n"
                )

    except urllib.error.HTTPError as error:
        error_body = error.read().decode(
            "utf-8", errors="replace"
        )

        print(f"HTTP Status: {error.code}")
        print(f"Qlik API Error: {error_body}")

        raise RuntimeError(
            f"Qlik export failed. HTTP {error.code}"
        )

    except urllib.error.URLError as error:
        print(f"Connection Error: {error.reason}")

        raise RuntimeError(
            "Unable to connect to Qlik Cloud."
        )


if __name__ == "__main__":
    try:
        export_qvf()

    except Exception as error:
        print(f"ERROR: {error}")
        sys.exit(1)
