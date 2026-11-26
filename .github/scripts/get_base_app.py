
import json
import os
import sys
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / ".github/config/pipeline_config.json"


def main():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Config not found: {CONFIG_PATH}"
        )

    with open(CONFIG_PATH, encoding="utf-8") as file:
        config = json.load(file)

    app_name = config["project"]["base_app"]
    tenant = os.environ["QLIK_TENANT_URL"].rstrip("/")
    token = os.environ["QLIK_ACCESS_TOKEN"]

    params = urllib.parse.urlencode({
        "resourceType": "app",
        "name": app_name,
        "limit": 100,
        "noActions": "true"
    })

    url = f"{tenant}/api/v1/items?{params}"

    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        },
        method="GET"
    )

    print("Checking Qlik Base Application...")
    print(f"Expected App Name: {app_name}")

    try:
        with urllib.request.urlopen(
            request, timeout=30
        ) as response:
            result = json.loads(response.read())

        items = result.get("data", [])

        print(f"API Returned Items: {len(items)}")

        # Diagnostic information only; no secrets are printed.
        for item in items:
            print(
                "Found Item:",
                "Name =", item.get("name"),
                "| Resource Type =", item.get("resourceType"),
                "| Resource ID Available =",
                bool(item.get("resourceId"))
            )

        matches = [
            item for item in items
            if item.get("name") == app_name
            and item.get("resourceType") == "app"
        ]

        if len(matches) == 0:
            print("\nBase application was not found.")
            print(
                "Check the OAuth read scope and app visibility."
            )
            raise RuntimeError(
                f"Base app not found: {app_name}"
            )

        if len(matches) > 1:
            raise RuntimeError(
                f"Multiple apps found with name: {app_name}"
            )

        app_id = matches[0].get("resourceId")

        if not app_id:
            raise RuntimeError(
                "App ID not returned by Qlik API."
            )

        print(f"\nBase Application found: {app_name}")
        print("App ID retrieved successfully.")

        github_output = os.environ.get("GITHUB_OUTPUT")

        if github_output:
            with open(
                github_output, "a", encoding="utf-8"
            ) as file:
                file.write(f"app_id={app_id}\n")

    except urllib.error.HTTPError as error:
        error_body = error.read().decode(
            "utf-8", errors="replace"
        )

        print(f"Qlik API HTTP Error: {error.code}")
        print(f"Qlik API Response: {error_body}")

        raise RuntimeError(
            "Unable to discover Qlik base application."
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}")
        sys.exit(1)
