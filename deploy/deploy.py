
import os
from pathlib import Path

from azure.identity import ClientSecretCredential
from fabric_cicd import FabricWorkspace, publish_all_items


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
    environment = os.environ.get("FABRIC_ENVIRONMENT", "DEV")

    # deploy.py is in /deploy, so the repo root is its parent.
    repo_root = Path(__file__).resolve().parent.parent
    repository_directory = repo_root / "fabric"

    if not repository_directory.is_dir():
        raise FileNotFoundError(
            f"Fabric repository directory not found: "
            f"{repository_directory}"
        )

    # Limit the deployment to the artifact types you use.
    # Adjust this list to match your repository.
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

    publish_all_items(workspace)

    print("Fabric deployment completed.")


if __name__ == "__main__":
    main()
