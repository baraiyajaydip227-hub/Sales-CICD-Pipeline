
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / ".github/config/pipeline_config.json"


def load_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Config file not found: {CONFIG_PATH}"
        )

    with open(CONFIG_PATH, encoding="utf-8") as file:
        return json.load(file)


def check_app_privileges(tenant, token, app_id):
    print("\nChecking Qlik Application Permissions...")

    check_url = f"{tenant}/api/v1/apps/{app_id}"

    check_request = urllib.request.Request(
        check_url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        },
        method="GET"
    )

    try:
        with urllib.request.urlopen(
            check_request, timeout=30
        ) as response:
            app_info = json.loads(response.read())

        privileges = app_info.get("privileges", [])

        print("App Permission Check:")
        print(f"Available Privileges: {privileges}")
        print(
            f"Export Permission: {'export' in privileges}"
        )

        return privileges

    except urllib.error.HTTPError as error:
        error_body = error.read().decode(
            "utf-8", errors="replace"
        )

        print(
            f"App Permission Check Failed: HTTP {error.code}"
        )
        print(f"Qlik API Error: {error_body}")

        raise RuntimeError(
            "Unable to verify Qlik application permissions."
        )


def export_qvf():
    config = load_config()

    tenant = os.environ["QLIK_TENANT_URL"].rstrip("/")
    token = os.environ["QLIK_ACCESS_TOKEN"]
    app_id = os.environ["QLIK_APP_ID"]

    if not app_id:
        raise RuntimeError(
            "Dynamic Base App ID is missing."
        )

    app_name = config["project"]["base_app"]

    if config["deployment"]["no_data"] is not True:
        raise RuntimeError(
            "No-data export must be enabled."
        )

    print("Starting Qlik Cloud QVF export...")
    print(f"Base Application: {app_name}")
    print("No-Data Export: Enabled")

    # Step 1: Check actual app privileges
    privileges = check_app_privileges(
        tenant,
        token,
        app_id
    )

    # Step 2: Start QVF export
    export_url = (
        f"{tenant}/api/v1/apps/{app_id}/export?NoData=true"
    )

    request = urllib.request.Request(
        export_url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/octet-stream"
        },
        method="POST"
    )

    print("\nStarting export request...")

    try:
        with urllib.request.urlopen(
            request, timeout=120
        ) as response:
            download_url = response.headers.get("Location")

        if not download_url:
            raise RuntimeError(
                "Qlik export Location header is missing."
            )

        if download_url.startswith("/"):
            download_url = tenant + download_url

        parsed_url = urlparse(download_url)

        if parsed_url.scheme != "https":
            raise RuntimeError(
                "Unexpected QVF download URL scheme."
            )

        tenant_host = urlparse(tenant).netloc

        download_headers = {}

        if parsed_url.netloc == tenant_host:
            download_headers["Authorization"] = (
                f"Bearer {token}"
            )

        download_request = urllib.request.Request(
            download_url,
            headers=download_headers
        )

        with urllib.request.urlopen(
            download_request, timeout=300
        ) as response:
            qvf_data = response.read()

        if not qvf_data:
            raise RuntimeError(
                "Exported QVF file is empty."
            )

        # Step 3: Save versioned QVF artifact
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
            parents=True,
            exist_ok=True
        )

        filename = (
            f"{app_name}-v{version}-{commit}-{timestamp}.qvf"
        )

        output_path = output_dir / filename
        output_path.write_bytes(qvf_data)

        print("\nQVF export successful.")
        print(f"Artifact: {filename}")
        print(f"Size: {len(qvf_data)} bytes")

        github_output = os.environ.get("GITHUB_OUTPUT")

        if github_output:
            with open(
                github_output,
                "a",
                encoding="utf-8"
            ) as file:
                file.write(
                    f"qvf_path=dist/{filename}\n"
                )

    except urllib.error.HTTPError as error:
        error_body = error.read().decode(
            "utf-8",
            errors="replace"
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
