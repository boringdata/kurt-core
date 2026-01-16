"""
GitHub App webhook handlers.

Handles events from GitHub when users install/uninstall the app,
or when repository events occur.
"""

from fastapi import APIRouter, Header, HTTPException, Request

from kurt.db import managed_session
from kurt.db.workspace_models import Workspace

router = APIRouter(prefix="/api/webhooks/github", tags=["webhooks"])


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify GitHub webhook signature.

    Args:
        payload: Raw request body
        signature: X-Hub-Signature-256 header value
        secret: Webhook secret from GitHub App settings

    Returns:
        True if signature is valid

    GitHub docs:
        https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries
    """
    import hashlib
    import hmac

    if not signature or not signature.startswith("sha256="):
        return False

    expected_signature = (
        "sha256="
        + hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
    )

    return hmac.compare_digest(expected_signature, signature)


@router.post("")
async def handle_github_webhook(
    request: Request,
    x_github_event: str = Header(None),
    x_hub_signature_256: str = Header(None),
):
    """
    Handle GitHub App webhook events.

    Events handled:
    - installation.created: User installed app on their repo
    - installation.deleted: User uninstalled app
    - installation_repositories: User granted/revoked repo access
    """
    import os

    # Verify webhook signature (in production)
    webhook_secret = os.environ.get("GITHUB_WEBHOOK_SECRET")
    if webhook_secret:
        body = await request.body()
        if not verify_webhook_signature(body, x_hub_signature_256, webhook_secret):
            raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()

    if x_github_event == "installation":
        return await handle_installation_event(payload)
    elif x_github_event == "installation_repositories":
        return await handle_installation_repositories_event(payload)
    elif x_github_event == "ping":
        return {"status": "pong"}
    else:
        return {"status": "ignored", "event": x_github_event}


async def handle_installation_event(payload: dict):
    """
    Handle GitHub App installation created/deleted events.

    When a user installs the app, we link the installation to the workspace
    that was passed in the 'state' parameter during the installation flow.
    """
    action = payload["action"]
    installation = payload["installation"]
    installation_id = installation["id"]
    account = installation["account"]["login"]

    if action == "created":
        # User just installed the app
        # Link installation to workspace(s) that match the repos
        repositories = payload.get("repositories", [])

        with managed_session() as session:
            from sqlmodel import select

            for repo_data in repositories:
                repo_name = repo_data["name"]

                # Find workspace(s) matching this owner/repo
                workspace = session.exec(
                    select(Workspace)
                    .where(Workspace.github_owner == account)
                    .where(Workspace.github_repo == repo_name)
                ).first()

                if workspace:
                    # Link installation to workspace
                    workspace.github_installation_id = installation_id
                    session.add(workspace)
                    session.commit()

        return {"status": "installation_linked", "installation_id": installation_id}

    elif action == "deleted":
        # User uninstalled the app
        with managed_session() as session:
            from sqlmodel import select

            # Clear installation ID from all workspaces using this installation
            workspaces = session.exec(
                select(Workspace).where(Workspace.github_installation_id == installation_id)
            ).all()

            for workspace in workspaces:
                workspace.github_installation_id = None
                workspace.github_installation_token = None
                workspace.github_installation_token_expires_at = None
                session.add(workspace)

            session.commit()

        return {"status": "installation_unlinked", "installation_id": installation_id}

    return {"status": "ignored", "action": action}


async def handle_installation_repositories_event(payload: dict):
    """
    Handle installation_repositories events.

    Triggered when user grants/revokes repo access after initial installation.
    """
    action = payload["action"]
    installation = payload["installation"]
    installation_id = installation["id"]
    repositories_added = payload.get("repositories_added", [])
    repositories_removed = payload.get("repositories_removed", [])

    if action == "added":
        # User granted access to more repos
        with managed_session() as session:
            from sqlmodel import select

            for repo_data in repositories_added:
                owner = installation["account"]["login"]
                repo_name = repo_data["name"]

                # Find workspace matching this repo
                workspace = session.exec(
                    select(Workspace)
                    .where(Workspace.github_owner == owner)
                    .where(Workspace.github_repo == repo_name)
                ).first()

                if workspace and not workspace.github_installation_id:
                    workspace.github_installation_id = installation_id
                    session.add(workspace)

            session.commit()

        return {
            "status": "repositories_added",
            "count": len(repositories_added),
        }

    elif action == "removed":
        # User revoked access to some repos
        with managed_session() as session:
            from sqlmodel import select

            for repo_data in repositories_removed:
                owner = installation["account"]["login"]
                repo_name = repo_data["name"]

                # Find workspace and unlink installation
                workspace = session.exec(
                    select(Workspace)
                    .where(Workspace.github_owner == owner)
                    .where(Workspace.github_repo == repo_name)
                    .where(Workspace.github_installation_id == installation_id)
                ).first()

                if workspace:
                    workspace.github_installation_id = None
                    workspace.github_installation_token = None
                    workspace.github_installation_token_expires_at = None
                    session.add(workspace)

            session.commit()

        return {
            "status": "repositories_removed",
            "count": len(repositories_removed),
        }

    return {"status": "ignored", "action": action}
