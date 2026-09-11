"""Narrow project operations with acknowledgement separate from point-in-time reads.

Declared roles: orchestration, validator. No retries, batch transaction or rollback.
Callers retain creation UUIDs before dispatch and reconcile unknown outcomes by read.
"""
from typing import Any
from uuid import UUID

from .client import LinearClient, LinearClientError, ProjectCreationIdentityError, UUID_RE


def _uuid(value: str, label: str, *, v4: bool = False) -> None:
    if not UUID_RE.fullmatch(value) or (v4 and UUID(value).version != 4):
        raise LinearClientError("INVALID_INPUT", f"{label} requires an exact UUID" + (" v4" if v4 else ""))


def _project_scope(project: dict, team_id: str, name: str | None = None, description: str | None = None) -> None:
    if project["archivedAt"] is not None or team_id not in {t["id"] for t in project["teams"]}:
        raise LinearClientError("PROJECT_MISMATCH", "Project is archived or does not belong to requested team")
    if name is not None and project["name"] != name:
        raise LinearClientError("PROJECT_MISMATCH", "Project name readback mismatch")
    if description is not None and project["description"] != description:
        raise LinearClientError("PROJECT_MISMATCH", "Project description readback mismatch")


def _failure(error: LinearClientError, progress: dict) -> dict:
    return {"ok": False, "data": progress, "error": {"code": error.code, "message": error.message}}


def create_project(client: LinearClient, name: str, team_id: str, project_id: str, description: str | None = None) -> dict[str, Any]:
    """Create only after complete visible inventory has no exact-name candidate.

    A name match blocks for caller selection, even if archived or in another team.
    This does not provide uniqueness against concurrent creators or hidden projects.
    """
    progress: dict[str, Any] = {"projectId": project_id, "teamId": team_id, "name": name,
                "mutation": "not_attempted", "readback": "not_attempted"}
    try:
        _uuid(project_id, "Creation identity", v4=True)
        _uuid(team_id, "Team")
        if not name.strip():
            raise LinearClientError("INVALID_INPUT", "Project name must not be blank")
        inventory = client.list_projects(include_archived=True)
        candidates = [p for p in inventory if p["name"] == name or p["id"] == project_id]
        if candidates:
            progress["candidates"] = candidates
            raise LinearClientError("PROJECT_CANDIDATES", "Existing candidates require exact-ID readback and caller selection; no creation attempted")
        progress["mutation"] = "unknown"
        client.create_project(name, team_id, project_id, description)
        progress["mutation"] = "acknowledged"
        progress["readback"] = "unverified"
        project = client.get_project(project_id)
        progress["project"] = project
        _project_scope(project, team_id, name, description)
        progress["readback"] = "matched"
        return {"ok": True, "data": progress}
    except LinearClientError as error:
        if isinstance(error, ProjectCreationIdentityError):
            progress["mutation"] = "acknowledged"
            progress["returnedProjectId"] = error.returned_id
        return _failure(error, progress)


def assign_issue_project(client: LinearClient, issue_id: str, project_id: str) -> dict[str, Any]:
    """Patch projectId only; verify the same issue UUID via a separate remote read."""
    progress: dict[str, Any] = {"requestedIssue": issue_id, "projectId": project_id,
                "mutation": "not_attempted", "readback": "not_attempted"}
    try:
        _uuid(project_id, "Destination project")
        project = client.get_project(project_id)
        issue = client.get_issue(issue_id)
        exact_id = issue.get("id")
        if not isinstance(exact_id, str):
            raise LinearClientError("INVALID_RESPONSE", "Missing issue identity")
        _uuid(exact_id, "Resolved issue")
        if issue_id not in (exact_id, issue.get("identifier")):
            raise LinearClientError("INVALID_RESPONSE", "Initial issue identity mismatch")
        progress["issueId"] = exact_id
        team = issue.get("team")
        if not isinstance(team, dict) or not isinstance(team.get("id"), str):
            raise LinearClientError("INVALID_RESPONSE", "Missing owning issue team")
        _project_scope(project, team["id"])
        previous = issue.get("project")
        if "project" not in issue or (previous is not None and (
            not isinstance(previous, dict) or not isinstance(previous.get("id"), str)
            or not UUID_RE.fullmatch(previous["id"])
        )):
            raise LinearClientError("INVALID_RESPONSE", "Missing/malformed initial issue project")
        progress["initialProjectId"] = previous.get("id") if isinstance(previous, dict) else None
        if progress["initialProjectId"] == project_id:
            progress["mutation"] = "already_matching"
        else:
            progress["mutation"] = "unknown"
            client.update_issue(exact_id, project_id=project_id)
            progress["mutation"] = "acknowledged"
        progress["readback"] = "unverified"
        observed = client.get_issue(exact_id)
        progress["observedIssue"] = observed
        destination = observed.get("project")
        observed_team = observed.get("team")
        if not isinstance(observed_team, dict) or observed_team.get("id") != team["id"]:
            raise LinearClientError("PROJECT_MISMATCH", "Independent issue team readback mismatch")
        if observed.get("id") != exact_id or not isinstance(destination, dict) or destination.get("id") != project_id:
            raise LinearClientError("PROJECT_MISMATCH", "Independent issue project readback mismatch")
        progress["readback"] = "matched"
        return {"ok": True, "data": progress}
    except LinearClientError as error:
        return _failure(error, progress)
