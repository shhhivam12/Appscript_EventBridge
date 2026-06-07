import json
import os
import threading
from datetime import datetime, timezone

APP_CREDENTIAL_SCHEMAS = {
    "servicenow": {
        "label": "ServiceNow",
        "icon": "bi-gear-wide-connected",
        "color": "#81b5a1",
        "fields": [
            {"key": "instance_url", "label": "Instance URL", "type": "text", "placeholder": "https://dev12345.service-now.com", "required": True},
            {"key": "client_id", "label": "Client ID", "type": "text", "placeholder": "OAuth Client ID", "required": True},
            {"key": "client_secret", "label": "Client Secret", "type": "password", "placeholder": "OAuth Client Secret", "required": True},
            {"key": "username", "label": "Username", "type": "text", "placeholder": "admin", "required": False},
            {"key": "password", "label": "Password", "type": "password", "placeholder": "Password", "required": False},
        ],
        "webhook_events": [
            "incident.created", "incident.updated", "incident.resolved",
            "change_request.created", "change_request.approved",
            "problem.created", "custom",
        ],
    },
    "telegram": {
        "label": "Telegram",
        "icon": "bi-telegram",
        "color": "#0088cc",
        "fields": [
            {"key": "bot_token", "label": "Bot Token", "type": "password", "placeholder": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", "required": True},
        ],
        "webhook_events": [
            "message", "edited_message", "callback_query",
            "inline_query", "command", "custom",
        ],
    },
    "gemini": {
        "label": "Google Gemini",
        "icon": "bi-magic",
        "color": "#6C58AF",
        "fields": [
            {"key": "api_key", "label": "API Key", "type": "password", "placeholder": "AIzaSy...", "required": True},
            {"key": "model", "label": "Model Name", "type": "text", "placeholder": "gemini-2.5-flash", "required": False},
        ],
        "webhook_events": [],
    },
    "openai": {
        "label": "OpenAI",
        "icon": "bi-cpu",
        "color": "#FD5A44",
        "fields": [
            {"key": "api_key", "label": "API Key", "type": "password", "placeholder": "sk-proj-...", "required": True},
            {"key": "model", "label": "Model Name", "type": "text", "placeholder": "gpt-4o-mini", "required": False},
        ],
        "webhook_events": [],
    },
    "custom": {
        "label": "Custom / Generic",
        "icon": "bi-plug",
        "color": "#6366f1",
        "fields": [
            {"key": "base_url", "label": "Base URL", "type": "text", "placeholder": "https://api.example.com", "required": False},
            {"key": "auth_header", "label": "Auth Header Name", "type": "text", "placeholder": "Authorization", "required": False},
            {"key": "auth_value", "label": "Auth Header Value", "type": "password", "placeholder": "Bearer xxx", "required": False},
        ],
        "webhook_events": ["custom"],
    },
    "google_chat": {
        "label": "Google Chat",
        "icon": "bi-chat-left-text-fill",
        "color": "#0f9d58",
        "fields": [
            {"key": "webhook_url", "label": "Webhook URL", "type": "text", "placeholder": "https://chat.googleapis.com/v1/spaces/.../webhooks/...", "required": False},
            {"key": "bot_token", "label": "Bot Token", "type": "password", "placeholder": "Optional Bot token / authentication key", "required": False},
        ],
        "webhook_events": ["message.received", "added_to_space", "removed_from_space", "custom"],
    },
    "gmail": {
        "label": "Gmail",
        "icon": "bi-envelope-fill",
        "color": "#ea4335",
        "fields": [
            {"key": "client_id", "label": "OAuth Client ID", "type": "text", "placeholder": "OAuth Client ID (optional if using global account)", "required": False},
            {"key": "client_secret", "label": "OAuth Client Secret", "type": "password", "placeholder": "OAuth Client Secret (optional if using global account)", "required": False},
            {"key": "refresh_token", "label": "Refresh Token", "type": "password", "placeholder": "OAuth Refresh Token (optional)", "required": False},
            {"key": "service_account", "label": "Service Account JSON", "type": "text", "placeholder": "Paste Service Account JSON content here (for background delegation)", "required": False},
        ],
        "webhook_events": ["message.received", "draft.created", "label.added", "custom"],
    },
    "google_drive": {
        "label": "Google Drive",
        "icon": "bi-hdd-network-fill",
        "color": "#4285f4",
        "fields": [
            {"key": "client_id", "label": "OAuth Client ID", "type": "text", "placeholder": "OAuth Client ID (optional)", "required": False},
            {"key": "client_secret", "label": "OAuth Client Secret", "type": "password", "placeholder": "OAuth Client Secret (optional)", "required": False},
            {"key": "refresh_token", "label": "Refresh Token", "type": "password", "placeholder": "OAuth Refresh Token (optional)", "required": False},
            {"key": "service_account", "label": "Service Account JSON", "type": "text", "placeholder": "Paste Service Account JSON content here", "required": False},
        ],
        "webhook_events": ["file.created", "file.updated", "file.deleted", "custom"],
    },
    "google_sheets": {
        "label": "Google Sheets",
        "icon": "bi-file-earmark-spreadsheet-fill",
        "color": "#0f9d58",
        "fields": [
            {"key": "client_id", "label": "OAuth Client ID", "type": "text", "placeholder": "OAuth Client ID (optional)", "required": False},
            {"key": "client_secret", "label": "OAuth Client Secret", "type": "password", "placeholder": "OAuth Client Secret (optional)", "required": False},
            {"key": "refresh_token", "label": "Refresh Token", "type": "password", "placeholder": "OAuth Refresh Token (optional)", "required": False},
            {"key": "service_account", "label": "Service Account JSON", "type": "text", "placeholder": "Paste Service Account JSON content here", "required": False},
        ],
        "webhook_events": ["row.added", "spreadsheet.updated", "custom"],
    },
    "google_calendar": {
        "label": "Google Calendar",
        "icon": "bi-calendar-event-fill",
        "color": "#f4b400",
        "fields": [
            {"key": "client_id", "label": "OAuth Client ID", "type": "text", "placeholder": "OAuth Client ID (optional)", "required": False},
            {"key": "client_secret", "label": "OAuth Client Secret", "type": "password", "placeholder": "OAuth Client Secret (optional)", "required": False},
            {"key": "refresh_token", "label": "Refresh Token", "type": "password", "placeholder": "OAuth Refresh Token (optional)", "required": False},
            {"key": "service_account", "label": "Service Account JSON", "type": "text", "placeholder": "Paste Service Account JSON content here", "required": False},
        ],
        "webhook_events": ["event.created", "event.updated", "event.deleted", "custom"],
    },
}


class JSONStorage:
    _lock = threading.Lock()

    def __init__(self, data_dir):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self._ensure_files()

    def _ensure_files(self):
        defaults = {
            "workspaces": [],
            "projects": [],
            "workflows": [],
            "credentials": [],
            "event_logs": [],
            "google_tokens": {},
            "settings": {"gemini_api_key": ""},
        }
        for name, default in defaults.items():
            path = os.path.join(self.data_dir, f"{name}.json")
            if not os.path.exists(path):
                self._write_file(path, default)

    def _read_file(self, filename):
        path = os.path.join(self.data_dir, f"{filename}.json")
        with self._lock:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

    def _write_file(self, path_or_name, data):
        if not path_or_name.endswith(".json"):
            path_or_name = os.path.join(self.data_dir, f"{path_or_name}.json")
        with self._lock:
            with open(path_or_name, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)

    def _now(self):
        return datetime.now(timezone.utc).isoformat()

    # --- Workspaces ---
    def get_workspaces(self):
        return self._read_file("workspaces")

    def get_workspace(self, workspace_id):
        return next((w for w in self.get_workspaces() if w["id"] == workspace_id), None)

    def create_workspace(self, data):
        workspaces = self.get_workspaces()
        workspace = {
            "id": f"ws_{os.urandom(8).hex()}",
            "name": data["name"],
            "description": data.get("description", ""),
            "created_at": self._now(),
            "updated_at": self._now(),
        }
        workspaces.append(workspace)
        self._write_file("workspaces", workspaces)
        return workspace

    def update_workspace(self, workspace_id, data):
        workspaces = self.get_workspaces()
        for w in workspaces:
            if w["id"] == workspace_id:
                w.update({k: v for k, v in data.items() if k not in ("id", "created_at")})
                w["updated_at"] = self._now()
                self._write_file("workspaces", workspaces)
                return w
        return None

    def delete_workspace(self, workspace_id):
        workspaces = [w for w in self.get_workspaces() if w["id"] != workspace_id]
        self._write_file("workspaces", workspaces)
        projects = [p for p in self.get_projects() if p["workspace_id"] != workspace_id]
        self._write_file("projects", projects)
        workflows = [wf for wf in self.get_workflows() if wf["workspace_id"] != workspace_id]
        self._write_file("workflows", workflows)
        creds = [c for c in self.get_credentials() if c["workspace_id"] != workspace_id]
        self._write_file("credentials", creds)

    # --- Projects ---
    def get_projects(self, workspace_id=None):
        projects = self._read_file("projects")
        if workspace_id:
            return [p for p in projects if p["workspace_id"] == workspace_id]
        return projects

    def get_project(self, project_id):
        return next((p for p in self.get_projects() if p["id"] == project_id), None)

    def create_project(self, data):
        projects = self.get_projects()
        project = {
            "id": f"proj_{os.urandom(8).hex()}",
            "workspace_id": data["workspace_id"],
            "name": data["name"],
            "description": data.get("description", ""),
            "created_at": self._now(),
            "updated_at": self._now(),
        }
        projects.append(project)
        self._write_file("projects", projects)
        return project

    def update_project(self, project_id, data):
        projects = self.get_projects()
        for p in projects:
            if p["id"] == project_id:
                p.update({k: v for k, v in data.items() if k not in ("id", "created_at", "workspace_id")})
                p["updated_at"] = self._now()
                self._write_file("projects", projects)
                return p
        return None

    def delete_project(self, project_id):
        projects = [p for p in self.get_projects() if p["id"] != project_id]
        self._write_file("projects", projects)
        workflows = [wf for wf in self.get_workflows() if wf["project_id"] != project_id]
        self._write_file("workflows", workflows)

    # --- Workflows ---
    def _upgrade_workflow(self, wf):
        if "nodes" in wf:
            return wf
        
        nodes = {}
        trigger_cfg = wf.get("trigger") or {}
        nodes["trigger"] = {
            "id": "trigger",
            "type": "trigger",
            "name": "Webhook Trigger",
            "config": {
                "source_app": trigger_cfg.get("source_app", ""),
                "credential_id": trigger_cfg.get("credential_id", ""),
                "event_type": trigger_cfg.get("event_type", "")
            },
            "next": []
        }
        
        filter_cfg = wf.get("filter") or {}
        has_filter = filter_cfg.get("enabled", False)
        
        action_cfg = wf.get("action") or {}
        has_action = bool(action_cfg.get("script_id") or action_cfg.get("web_app_url"))
        
        next_node = "action_node"
        if has_filter:
            next_node = "filter_node"
            nodes["filter_node"] = {
                "id": "filter_node",
                "type": "filter",
                "name": "Filter Conditions",
                "config": {
                    "logic": filter_cfg.get("logic", "AND"),
                    "conditions": filter_cfg.get("conditions", [])
                },
                "next": ["action_node"] if has_action else []
            }
            
        nodes["trigger"]["next"] = [next_node] if (has_filter or has_action) else []
        
        if has_action:
            nodes["action_node"] = {
                "id": "action_node",
                "type": action_cfg.get("type", "apps_script_api"),
                "name": "Apps Script Action" if action_cfg.get("type") == "apps_script_api" else "Web App Action",
                "config": {
                    "script_id": action_cfg.get("script_id", ""),
                    "script_name": action_cfg.get("script_name", ""),
                    "function_name": action_cfg.get("function_name", ""),
                    "web_app_url": action_cfg.get("web_app_url", ""),
                    "parameters": action_cfg.get("parameters", [])
                },
                "next": []
            }
            
        wf["nodes"] = nodes
        return wf

    def get_workflows(self, project_id=None, workspace_id=None):
        workflows = self._read_file("workflows")
        upgraded = []
        for wf in workflows:
            upgraded.append(self._upgrade_workflow(wf))
        if project_id:
            return [wf for wf in upgraded if wf["project_id"] == project_id]
        if workspace_id:
            return [wf for wf in upgraded if wf["workspace_id"] == workspace_id]
        return upgraded

    def get_workflow(self, workflow_id):
        return next((wf for wf in self.get_workflows() if wf["id"] == workflow_id), None)

    def create_workflow(self, data):
        workflows = self.get_workflows()
        source_app = data.get("source_app", "custom")
        credential_id = data.get("credential_id", "")
        event_type = data.get("event_type", "custom")
        action_type = data.get("action_type", "apps_script_api")
        script_id = data.get("script_id", "")
        script_name = data.get("script_name", "")
        function_name = data.get("function_name", "")
        web_app_url = data.get("web_app_url", "")

        nodes = {
            "trigger": {
                "id": "trigger",
                "type": "trigger",
                "name": "Webhook Trigger",
                "config": {
                    "source_app": source_app,
                    "credential_id": credential_id,
                    "event_type": event_type
                },
                "next": ["action_node"] if (script_id or web_app_url) else []
            }
        }
        if script_id or web_app_url:
            nodes["action_node"] = {
                "id": "action_node",
                "type": action_type,
                "name": "Apps Script Action" if action_type == "apps_script_api" else "Web App Action",
                "config": {
                    "script_id": script_id,
                    "script_name": script_name,
                    "function_name": function_name,
                    "web_app_url": web_app_url,
                    "parameters": []
                },
                "next": []
            }

        workflow = {
            "id": f"wf_{os.urandom(8).hex()}",
            "project_id": data["project_id"],
            "workspace_id": data["workspace_id"],
            "name": data["name"],
            "description": data.get("description", ""),
            "status": "inactive",
            "trigger": {
                "type": "webhook",
                "source_app": source_app,
                "credential_id": credential_id,
                "event_type": event_type,
            },
            "action": {
                "type": action_type,
                "script_id": script_id,
                "script_name": script_name,
                "function_name": function_name,
                "web_app_url": web_app_url,
                "parameters": []
            },
            "nodes": nodes,
            "created_at": self._now(),
            "updated_at": self._now(),
            "last_triggered": None,
            "trigger_count": 0,
        }
        workflows.append(workflow)
        self._write_file("workflows", workflows)
        return workflow

    def update_workflow(self, workflow_id, data):
        workflows = self.get_workflows()
        for wf in workflows:
            if wf["id"] == workflow_id:
                for key in ("name", "description", "status", "last_triggered", "trigger_count", "testing_trigger", "captured_payload"):
                    if key in data:
                        wf[key] = data[key]
                if "trigger" in data:
                    wf["trigger"].update(data["trigger"])
                if "action" in data:
                    wf["action"].update(data["action"])
                if "nodes" in data:
                    wf["nodes"] = data["nodes"]
                    # Sync nodes back to old trigger/action/filter structures for full backwards compatibility
                    trigger_node = data["nodes"].get("trigger", {})
                    if trigger_node:
                        t_cfg = trigger_node.get("config", {})
                        wf["trigger"] = {
                            "type": "webhook",
                            "source_app": t_cfg.get("source_app", ""),
                            "credential_id": t_cfg.get("credential_id", ""),
                            "event_type": t_cfg.get("event_type", ""),
                        }
                    action_node = data["nodes"].get("action_node") or next((n for n in data["nodes"].values() if n.get("type") in ("apps_script_api", "web_app")), None)
                    if action_node:
                        a_cfg = action_node.get("config", {})
                        wf["action"] = {
                            "type": action_node.get("type", "apps_script_api"),
                            "script_id": a_cfg.get("script_id", ""),
                            "script_name": a_cfg.get("script_name", ""),
                            "function_name": a_cfg.get("function_name", ""),
                            "web_app_url": a_cfg.get("web_app_url", ""),
                            "parameters": a_cfg.get("parameters", []),
                        }
                    filter_node = data["nodes"].get("filter_node") or next((n for n in data["nodes"].values() if n.get("type") == "filter"), None)
                    if filter_node:
                        f_cfg = filter_node.get("config", {})
                        wf["filter"] = {
                            "enabled": True,
                            "logic": f_cfg.get("logic", "AND"),
                            "conditions": f_cfg.get("conditions", []),
                        }
                wf["updated_at"] = self._now()
                self._write_file("workflows", workflows)
                return wf
        return None

    def delete_workflow(self, workflow_id):
        workflows = [wf for wf in self.get_workflows() if wf["id"] != workflow_id]
        self._write_file("workflows", workflows)

    # --- Credentials (app-specific) ---
    def get_credentials(self, workspace_id=None):
        creds = self._read_file("credentials")
        if workspace_id:
            return [c for c in creds if c["workspace_id"] == workspace_id]
        return creds

    def get_credential(self, credential_id):
        return next((c for c in self.get_credentials() if c["id"] == credential_id), None)

    def get_credential_by_api_key(self, api_key):
        return next((c for c in self.get_credentials() if c.get("api_key") == api_key), None)

    def create_credential(self, data):
        creds = self.get_credentials()
        credential = {
            "id": f"cred_{os.urandom(8).hex()}",
            "workspace_id": data["workspace_id"],
            "name": data["name"],
            "app_type": data.get("app_type", "custom"),
            "config": data.get("config", {}),
            "api_key": f"asb_{os.urandom(16).hex()}",
            "api_secret": os.urandom(24).hex(),
            "is_active": True,
            "webhook_registered": False,
            "created_at": self._now(),
            "updated_at": self._now(),
        }
        creds.append(credential)
        self._write_file("credentials", creds)
        return credential

    def update_credential(self, credential_id, data):
        creds = self.get_credentials()
        for c in creds:
            if c["id"] == credential_id:
                for key in ("name", "is_active", "config", "webhook_registered"):
                    if key in data:
                        c[key] = data[key]
                c["updated_at"] = self._now()
                self._write_file("credentials", creds)
                return c
        return None

    def delete_credential(self, credential_id):
        creds = [c for c in self.get_credentials() if c["id"] != credential_id]
        self._write_file("credentials", creds)

    # --- Event Logs ---
    def get_event_logs(self, workflow_id=None, limit=50):
        logs = self._read_file("event_logs")
        if workflow_id:
            logs = [l for l in logs if l["workflow_id"] == workflow_id]
        logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return logs[:limit]

    def create_event_log(self, data):
        logs = self._read_file("event_logs")
        log = {
            "id": f"evt_{os.urandom(8).hex()}",
            "workflow_id": data.get("workflow_id", ""),
            "credential_id": data.get("credential_id", ""),
            "source_app": data.get("source_app", ""),
            "event_type": data.get("event_type", ""),
            "payload": data.get("payload", {}),
            "status": data.get("status", "pending"),
            "response": data.get("response", {}),
            "error": data.get("error", ""),
            "timestamp": self._now(),
            "processing_time_ms": data.get("processing_time_ms", 0),
            "execution_state": data.get("execution_state"),
            "human_step_info": data.get("human_step_info"),
            "step_results": data.get("step_results")
        }
        logs.append(log)
        if len(logs) > 1000:
            logs = logs[-1000:]
        self._write_file("event_logs", logs)
        return log

    # --- Google Tokens ---
    def get_google_tokens(self):
        return self._read_file("google_tokens")

    def save_google_tokens(self, tokens):
        self._write_file("google_tokens", tokens)

    # --- Settings ---
    def get_settings(self):
        return self._read_file("settings")

    def update_settings(self, data):
        settings = self.get_settings()
        settings.update({k: v for k, v in data.items() if k in ("gemini_api_key",)})
        self._write_file("settings", settings)
        return settings
