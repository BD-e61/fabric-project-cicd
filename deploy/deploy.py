
import os
import time
from pathlib import Path

import requests
from azure.identity import ClientSecretCredential
from fabric_cicd import FabricWorkspace, publish_all_items


FABRIC_API = "https://api.fabric.microsoft.com/v1"


def run_notebook(workspace_id, notebook_name, access_token):
    """Run a notebook in the target Fabric workspace and wait for completion."""

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # Find the deployed notebook by name.
    items_url = f"{FABRIC_API}/workspaces/{workspace_id}/items"
    response = requests.get(items_url, headers=headers, timeout=30)
    response.raise_for_status()

    notebooks = [
        item for item in response.json().get("value", [])
        if item.get("type") == "Notebook"
        and item.get("displayName") == notebook_name
    ]

    if len(notebooks) != 1:
        raise RuntimeError(
            f"Expected exactly one notebook named '{notebook_name}', "
            f"but found {len(notebooks)} in workspace {workspace_id}."
        )

    notebook_id = notebooks[0]["id"]
    print(f"Found notebook: {notebook_name} ({notebook_id})")
    print(f"Starting notebook: {notebook_name}")

    # Start notebook execution.
    run_url = (
        f"{FABRIC_API}/workspaces/{workspace_id}"
        f"/notebooks/{notebook_id}/jobs/execute/instances?beta=false"
    )

    response = requests.post(
        run_url,
        headers=headers,
        timeout=30,
    )

    if response.status_code != 202:
        response.raise_for_status()
        raise RuntimeError(
            f"Unexpected response starting notebook: "
            f"{response.status_code} {response.text}"
        )

    # Fabric returns the job-instance URL in the Location header.
    status_url = response.headers.get("Location")
    if not status_url:
        raise RuntimeError(
            "Fabric accepted the notebook run but returned no Location header."
        )

    wait_seconds = int(response.headers.get("Retry-After", "10"))
    print(f"Notebook submitted. First status check in {wait_seconds}s.")

    # Poll until the notebook completes or fails.
    deadline = time.monotonic() + 3600  # 1-hour timeout

    while time.monotonic() < deadline:
        time.sleep(max(wait_seconds, 1))

        response = requests.get(
            status_url,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()

        result = response.json()
        status = result.get("status", "Unknown")
        print(f"Notebook status: {status}")

        if status == "Completed":
            print(f"Notebook '{notebook_name}' completed successfully.")
            return

        if status in ("Failed", "Cancelled"):
            raise RuntimeError(
                f"Notebook '{notebook_name}' ended with status '{status}'. "
                f"Failure details: {result.get('failureReason')}"
            )

        wait_seconds = int(response.headers.get("Retry-After", "10"))

    raise TimeoutError(
        f"Notebook '{notebook_name}' did not finish within one hour."
    )


def main():
    # Authentication
    tenant_id = os.environ["FABRIC_TENANT_ID"]
    client_id = os.environ["FABRIC_CLIENT_ID"]
    client_secret = os.environ["FABRIC_CLIENT_SECRET"]

    credential = ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
    )

    # Deployment configuration
    workspace_id = os.environ["FABRIC_WORKSPACE_ID"]
    environment = os.environ.get("FABRIC_ENVIRONMENT", "dev")

    repo_root = Path(__file__).resolve().parent.parent
    repository_directory = repo_root / "fabric"

    if not repository_directory.is_dir():
        raise FileNotFoundError(
            f"Fabric repository directory not found: "
            f"{repository_directory}"
        )

    item_types_in_scope = [
        "Notebook",
        "DataPipeline",
        "Environment",
        "Lakehouse",
    ]

    print(f"Target workspace ID: {workspace_id}")
    print(f"Environment: {environment}")
    print(f"Repository directory: {repository_directory}")
    print(f"Item types in scope: {item_types_in_scope}")

    workspace = FabricWorkspace(
        workspace_id=workspace_id,
        environment=environment,
        repository_directory=str(repository_directory),
        item_type_in_scope=item_types_in_scope,
        token_credential=credential,
    )

    # Step 1: Deploy Fabric artifacts.
    publish_all_items(workspace)
    print("Fabric deployment completed.")


    # Step 2: Run the notebook only in production.
    if environment.strip().lower() == "prod":
        print("Production deployment detected. Running NB_GET_WEATHER.")
    
        access_token = credential.get_token(
            "https://api.fabric.microsoft.com/.default"
        ).token
    
        run_notebook(
            workspace_id=workspace_id,
            notebook_name="NB_GET_WEATHER",
            access_token=access_token,
        )
    else:
        print(
            f"Skipping NB_GET_WEATHER: "
            f"environment '{environment}' is not production."
        )

    print("Deployment and notebook execution completed successfully.")


if __name__ == "__main__":
    main()
