from flask import Blueprint, render_template, current_app, session, redirect
from services.storage import APP_CREDENTIAL_SCHEMAS

dashboard_bp = Blueprint("dashboard", __name__)


def _ctx(**extra):
    storage = current_app.config["STORAGE"]
    tokens = storage.get_google_tokens()
    
    # Build workspaces hierarchy for sidebar navigation
    nav_workspaces = []
    try:
        workspaces_list = storage.get_workspaces()
        projects_list = storage.get_projects()
        workflows_list = storage.get_workflows()
        
        for ws in workspaces_list:
            ws_id = ws["id"]
            ws_projects = [p for p in projects_list if p.get("workspace_id") == ws_id]
            ws_proj_nodes = []
            for prj in ws_projects:
                prj_id = prj["id"]
                prj_workflows = [w for w in workflows_list if w.get("project_id") == prj_id]
                ws_proj_nodes.append({
                    "id": prj_id,
                    "name": prj["name"],
                    "workflows": [{"id": w["id"], "name": w["name"]} for w in prj_workflows]
                })
            nav_workspaces.append({
                "id": ws_id,
                "name": ws["name"],
                "projects": ws_proj_nodes
            })
    except Exception as e:
        current_app.logger.error(f"Error building sidebar navigation: {str(e)}")
        nav_workspaces = []

    base = {
        "google_connected": bool(tokens and tokens.get("access_token")),
        "user_email": session.get("user_email", ""),
        "user_name": session.get("user_name", ""),
        "user_picture": session.get("user_picture", ""),
        "base_url": current_app.config["BASE_URL"],
        "app_schemas": APP_CREDENTIAL_SCHEMAS,
        "gcp_project_name": current_app.config.get("GCP_PROJECT_NAME", ""),
        "gcp_project_number": current_app.config.get("GCP_PROJECT_NUMBER", ""),
        "nav_workspaces": nav_workspaces,
    }
    base.update(extra)
    return base


@dashboard_bp.route("/")
def index():
    return render_template("dashboard.html", **_ctx(page="dashboard"))


@dashboard_bp.route("/workspaces")
def workspaces():
    return render_template("workspaces.html", **_ctx(page="workspaces"))


@dashboard_bp.route("/workspaces/<workspace_id>")
def workspace_detail(workspace_id):
    storage = current_app.config["STORAGE"]
    ws = storage.get_workspace(workspace_id)
    return render_template("workspace_detail.html", **_ctx(page="workspaces", workspace=ws))


@dashboard_bp.route("/workspaces/<workspace_id>/projects/<project_id>")
def project_detail(workspace_id, project_id):
    storage = current_app.config["STORAGE"]
    ws = storage.get_workspace(workspace_id)
    proj = storage.get_project(project_id)
    return render_template("project_detail.html", **_ctx(page="workspaces", workspace=ws, project=proj))


@dashboard_bp.route("/workspaces/<workspace_id>/projects/<project_id>/workflows/new")
def workflow_create(workspace_id, project_id):
    storage = current_app.config["STORAGE"]
    wf_data = {
        "project_id": project_id,
        "workspace_id": workspace_id,
        "name": "Untitled Workflow",
        "description": "",
    }
    wf = storage.create_workflow(wf_data)
    return redirect(f"/workflows/{wf['id']}/edit")


@dashboard_bp.route("/workflows/<workflow_id>/edit")
def workflow_edit(workflow_id):
    storage = current_app.config["STORAGE"]
    wf = storage.get_workflow(workflow_id)
    if not wf:
        return render_template("dashboard.html", **_ctx(page="dashboard"))
    proj = storage.get_project(wf["project_id"])
    ws = storage.get_workspace(wf["workspace_id"])
    creds = storage.get_credentials(wf["workspace_id"])

    import json
    source = wf.get("trigger", {}).get("source_app", "custom")
    test_payloads = {
        "servicenow": json.dumps({
            "event_type": wf.get("trigger", {}).get("event_type", "incident.created"),
            "number": "INC0010001",
            "short_description": "Test incident from AppScript Bridge",
            "priority": "3",
            "state": "1",
            "sys_id": "abc123def456"
        }, indent=2),
        "telegram": json.dumps({
            "message": {
                "message_id": 1,
                "from": {"id": 123456, "first_name": "Test", "username": "testuser"},
                "chat": {"id": 123456, "type": "private"},
                "date": 1234567890,
                "text": "/start Hello from AppScript Bridge"
            }
        }, indent=2),
        "google_chat": json.dumps({
            "type": "MESSAGE",
            "message": {
                "text": "Hello bot from space",
                "sender": {"displayName": "User", "email": "user@example.com"}
            },
            "space": {"name": "spaces/AAAAbbbb", "type": "ROOM"}
        }, indent=2),
        "gmail": json.dumps({
            "message": {
                "data": "eyJlbWFpbEFkZHJlc3MiOiJ1c2VyQGV4YW1wbGUuY29tIiwiaGlzdG9yeUlkIjoiMTIzNDU2In0=",
                "messageId": "msg_12345"
            }
        }, indent=2),
        "google_drive": json.dumps({
            "resource_state": "update",
            "resource_id": "file_12345",
            "file_name": "Monthly Report.docx",
            "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "owner": "user@example.com"
        }, indent=2),
        "google_sheets": json.dumps({
            "event": "row.added",
            "spreadsheet_id": "sheet_123456",
            "range": "Sheet1!A5:E5",
            "values": ["2026-06-07", "Apples", "10", "Pending"]
        }, indent=2),
        "google_calendar": json.dumps({
            "resource_state": "exists",
            "event_id": "event_789abc",
            "summary": "Sync meeting",
            "start": "2026-06-07T17:00:00Z",
            "end": "2026-06-07T18:00:00Z"
        }, indent=2),
        "custom": json.dumps({"test": True, "message": "Hello from AppScript Bridge"}, indent=2),
    }
    test_payload = test_payloads.get(source, test_payloads["custom"])

    return render_template("workflow_edit.html", **_ctx(
        page="workspaces", workflow=wf, project=proj, workspace=ws,
        credentials=creds, test_payload=test_payload,
    ))


@dashboard_bp.route("/credentials")
def credentials():
    return render_template("credentials.html", **_ctx(page="credentials"))


@dashboard_bp.route("/credentials/new/<app_type>")
def credential_create(app_type):
    schema = APP_CREDENTIAL_SCHEMAS.get(app_type)
    if not schema:
        return render_template("credentials.html", **_ctx(page="credentials"))
    return render_template("credential_create.html", **_ctx(
        page="credentials", app_type=app_type, schema=schema,
    ))


@dashboard_bp.route("/credentials/<credential_id>/manage")
def credential_manage(credential_id):
    storage = current_app.config["STORAGE"]
    cred = storage.get_credential(credential_id)
    if not cred:
        return render_template("credentials.html", **_ctx(page="credentials"))
    schema = APP_CREDENTIAL_SCHEMAS.get(cred.get("app_type", "custom"), APP_CREDENTIAL_SCHEMAS["custom"])
    return render_template("credential_manage.html", **_ctx(
        page="credentials", credential=cred, schema=schema,
    ))


@dashboard_bp.route("/events")
def events():
    return render_template("events.html", **_ctx(page="events"))


@dashboard_bp.route("/settings")
def settings():
    return render_template("settings.html", **_ctx(page="settings"))


@dashboard_bp.route("/guide")
def guide():
    return render_template("guide.html", **_ctx(page="guide"))
