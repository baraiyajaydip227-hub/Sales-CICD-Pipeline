
import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / ".github/config/pipeline_config.json"


def load_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Configuration not found: {CONFIG_PATH}"
        )

    with open(CONFIG_PATH, encoding="utf-8") as file:
        return json.load(file)


def get_qvf_file():
    qvf_path = os.environ.get("QVF_PATH")

    if qvf_path:
        path = Path(qvf_path)
        if not path.is_absolute():
            path = ROOT / path
    else:
        qvf_files = list((ROOT / "dist").glob("*.qvf"))

        if not qvf_files:
            raise FileNotFoundError(
                "No QVF artifact found in dist directory."
            )

        path = max(
            qvf_files,
            key=lambda item: item.stat().st_mtime
        )

    if not path.exists():
        raise FileNotFoundError(
            f"QVF file not found: {path}"
        )

    if path.suffix.lower() != ".qvf":
        raise ValueError("Invalid artifact. Expected .qvf file.")

    return path


def deploy_qvf():

    config = load_config()

    tenant = os.environ.get(
        "QLIK_TENANT_URL", ""
    ).rstrip("/")

    token = os.environ.get("QLIK_ACCESS_TOKEN")

    target_env = os.environ.get(
        "TARGET_ENV", "DEV"
    ).upper()

    if not tenant or not token:
        raise RuntimeError(
            "Qlik tenant URL or API Key is missing."
        )

    environments = config.get("environments", [])
    space_ids = config.get("space_ids", {})

    if target_env not in environments:
        raise ValueError(
            f"Invalid environment: {target_env}"
        )

    space_id = space_ids.get(target_env)

    if not space_id:
        raise ValueError(
            f"Space ID missing for {target_env}"
        )

    app_name = config["project"]["base_app"]

    qvf_file = get_qvf_file()

    print("Starting Qlik QVF Deployment...")
    print(f"Application: {app_name}")
    print(f"Target Environment: {target_env}")
    print(f"Target Space ID: {space_id}")
    print(f"QVF Artifact: {qvf_file.name}")
    print(f"Artifact Size: {qvf_file.stat().st_size} bytes")

    # Qlik Import API
    params = urllib.parse.urlencode({
        "spaceId": space_id,
        "name": app_name,
        "mode": "NEW"
    })

    import_url = (
        f"{tenant}/api/v1/apps/import?{params}"
    )

    with open(qvf_file, "rb") as file:
        qvf_data = file.read()

    request = urllib.request.Request(
        import_url,
        data=qvf_data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/octet-stream",
            "Accept": "application/json"
        },
        method="POST"
    )

    print("\nSending QVF to Qlik Cloud...")

    try:
        with urllib.request.urlopen(
            request, timeout=600
        ) as response:

            result = json.loads(
                response.read().decode("utf-8")
            )

        attributes = result.get("attributes", {})

        deployed_app_id = attributes.get("id")
        deployed_app_name = attributes.get(
            "name", app_name
        )

        if not deployed_app_id:
            raise RuntimeError(
                "Qlik did not return the deployed App ID."
            )

        print("\nDeployment Successful!")
        print(f"Environment: {target_env}")
        print(f"Application: {deployed_app_name}")
        print(f"Application ID: {deployed_app_id}")
        print(f"Space ID: {space_id}")

        # GitHub Actions output
        github_output = os.environ.get("GITHUB_OUTPUT")

        if github_output:
            with open(
                github_output,
                "a",
                encoding="utf-8"
            ) as file:
                file.write(
                    f"app_id={deployed_app_id}\n"
                )
                file.write(
                    f"environment={target_env}\n"
                )

        print("\nQVF Deployment Completed.")

    except urllib.error.HTTPError as error:

        error_body = error.read().decode(
            "utf-8", errors="replace"
        )

        print(f"HTTP Status: {error.code}")
        print(f"Qlik API Error: {error_body}")

        raise RuntimeError(
            f"QVF deployment failed in {target_env}."
        )

    except urllib.error.URLError as error:

        print(f"Connection Error: {error.reason}")

        raise RuntimeError(
            "Unable to connect to Qlik Cloud."
        )


if __name__ == "__main__":

    try:
        deploy_qvf()

    except Exception as error:
        print(f"\nERROR: {error}")
        sys.exit(1)
