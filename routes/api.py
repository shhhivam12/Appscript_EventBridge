from flask import Blueprint, request, jsonify, current_app
from services.storage import APP_CREDENTIAL_SCHEMAS

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _storage():
    return current_app.config["STORAGE"]


# ── Workspaces ──

@api_bp.route("/workspaces", methods=["GET"])
def list_workspaces():
    return jsonify(_storage().get_workspaces())

@api_bp.route("/workspaces", methods=["POST"])
def create_workspace():
    data = request.json
    if not data or not data.get("name"):
        return jsonify({"error": "Name is required"}), 400
    return jsonify(_storage().create_workspace(data)), 201

@api_bp.route("/workspaces/<workspace_id>", methods=["GET"])
def get_workspace(workspace_id):
    ws = _storage().get_workspace(workspace_id)
    if not ws:
        return jsonify({"error": "Workspace not found"}), 404
    return jsonify(ws)

@api_bp.route("/workspaces/<workspace_id>", methods=["PUT"])
def update_workspace(workspace_id):
    ws = _storage().update_workspace(workspace_id, request.json)
    if not ws:
        return jsonify({"error": "Workspace not found"}), 404
    return jsonify(ws)

@api_bp.route("/workspaces/<workspace_id>", methods=["DELETE"])
def delete_workspace(workspace_id):
    _storage().delete_workspace(workspace_id)
    return jsonify({"success": True})


# ── Projects ──

@api_bp.route("/workspaces/<workspace_id>/projects", methods=["GET"])
def list_projects(workspace_id):
    return jsonify(_storage().get_projects(workspace_id))

@api_bp.route("/projects", methods=["POST"])
def create_project():
    data = request.json
    if not data or not data.get("name") or not data.get("workspace_id"):
        return jsonify({"error": "Name and workspace_id are required"}), 400
    return jsonify(_storage().create_project(data)), 201

@api_bp.route("/projects/<project_id>", methods=["GET"])
def get_project(project_id):
    proj = _storage().get_project(project_id)
    if not proj:
        return jsonify({"error": "Project not found"}), 404
    return jsonify(proj)

@api_bp.route("/projects/<project_id>", methods=["PUT"])
def update_project(project_id):
    proj = _storage().update_project(project_id, request.json)
    if not proj:
        return jsonify({"error": "Project not found"}), 404
    return jsonify(proj)

@api_bp.route("/projects/<project_id>", methods=["DELETE"])
def delete_project(project_id):
    _storage().delete_project(project_id)
    return jsonify({"success": True})


# ── Workflows ──

@api_bp.route("/projects/<project_id>/workflows", methods=["GET"])
def list_workflows(project_id):
    return jsonify(_storage().get_workflows(project_id=project_id))

@api_bp.route("/workspaces/<workspace_id>/workflows", methods=["GET"])
def list_workspace_workflows(workspace_id):
    return jsonify(_storage().get_workflows(workspace_id=workspace_id))

@api_bp.route("/workflows", methods=["POST"])
def create_workflow():
    data = request.json
    if not data or not data.get("name") or not data.get("project_id"):
        return jsonify({"error": "Name and project_id are required"}), 400
    return jsonify(_storage().create_workflow(data)), 201

@api_bp.route("/workflows/<workflow_id>", methods=["GET"])
def get_workflow(workflow_id):
    wf = _storage().get_workflow(workflow_id)
    if not wf:
        return jsonify({"error": "Workflow not found"}), 404
    return jsonify(wf)

@api_bp.route("/workflows/<workflow_id>", methods=["PUT"])
def update_workflow(workflow_id):
    wf = _storage().update_workflow(workflow_id, request.json)
    if not wf:
        return jsonify({"error": "Workflow not found"}), 404
    return jsonify(wf)

@api_bp.route("/workflows/<workflow_id>", methods=["DELETE"])
def delete_workflow(workflow_id):
    _storage().delete_workflow(workflow_id)
    return jsonify({"success": True})

@api_bp.route("/workflows/<workflow_id>/toggle", methods=["POST"])
def toggle_workflow(workflow_id):
    wf = _storage().get_workflow(workflow_id)
    if not wf:
        return jsonify({"error": "Workflow not found"}), 404
    new_status = "inactive" if wf["status"] == "active" else "active"
    wf = _storage().update_workflow(workflow_id, {"status": new_status})
    return jsonify(wf)


# ── Credentials ──

@api_bp.route("/credential-schemas", methods=["GET"])
def get_credential_schemas():
    return jsonify(APP_CREDENTIAL_SCHEMAS)

@api_bp.route("/workspaces/<workspace_id>/credentials", methods=["GET"])
def list_credentials(workspace_id):
    return jsonify(_storage().get_credentials(workspace_id))

@api_bp.route("/credentials", methods=["GET"])
def list_all_credentials():
    return jsonify(_storage().get_credentials())

@api_bp.route("/credentials", methods=["POST"])
def create_credential():
    data = request.json
    if not data or not data.get("name") or not data.get("workspace_id"):
        return jsonify({"error": "Name and workspace_id are required"}), 400
    return jsonify(_storage().create_credential(data)), 201

@api_bp.route("/credentials/<credential_id>", methods=["GET"])
def get_credential(credential_id):
    cred = _storage().get_credential(credential_id)
    if not cred:
        return jsonify({"error": "Credential not found"}), 404
    return jsonify(cred)

@api_bp.route("/credentials/<credential_id>", methods=["PUT"])
def update_credential(credential_id):
    cred = _storage().update_credential(credential_id, request.json)
    if not cred:
        return jsonify({"error": "Credential not found"}), 404
    return jsonify(cred)

@api_bp.route("/credentials/<credential_id>", methods=["DELETE"])
def delete_credential(credential_id):
    _storage().delete_credential(credential_id)
    return jsonify({"success": True})


# ── Apps Script: List scripts and functions ──

@api_bp.route("/scripts", methods=["GET"])
def list_scripts():
    script_svc = current_app.config["APPS_SCRIPT"]
    result = script_svc.list_scripts()
    if not result["success"]:
        return jsonify(result), 400
    return jsonify(result)

@api_bp.route("/scripts/<script_id>/functions", methods=["GET"])
def get_script_functions(script_id):
    script_svc = current_app.config["APPS_SCRIPT"]
    result = script_svc.get_script_functions(script_id)
    if not result["success"]:
        return jsonify(result), 400
    return jsonify(result)

@api_bp.route("/scripts/<script_id>/metadata", methods=["GET"])
def get_script_metadata(script_id):
    script_svc = current_app.config["APPS_SCRIPT"]
    result = script_svc.get_script_metadata(script_id)
    if not result["success"]:
        return jsonify(result), 400
    return jsonify(result)


# ── Event Logs ──

@api_bp.route("/events", methods=["GET"])
def list_events():
    workflow_id = request.args.get("workflow_id")
    limit       = int(request.args.get("limit", 50))
    events      = _storage().get_event_logs(workflow_id=workflow_id, limit=limit)

    # Enrich each event with the workflow name so the UI can show it directly.
    wf_cache = {}
    for evt in events:
        wid = evt.get("workflow_id")
        if wid and wid not in wf_cache:
            wf = _storage().get_workflow(wid)
            wf_cache[wid] = {"name": wf["name"], "id": wid, "nodes": wf.get("nodes", {})} if wf else None
        evt["workflow_info"] = wf_cache.get(wid) if wid else None

    return jsonify(events)


# ── Event Resumption ──

@api_bp.route("/events/<event_id>/resume", methods=["POST"])
def resume_event(event_id):
    data = request.json or {}
    approved = data.get("approved", True)
    comments = data.get("comments", "")
    
    storage = _storage()
    event_logs = storage._read_file("event_logs")
    log = next((l for l in event_logs if l["id"] == event_id), None)
    if not log:
        return jsonify({"error": "Event not found"}), 404
        
    if log.get("status") != "pending_human":
        return jsonify({"error": f"Event is not pending human approval. Status: {log.get('status')}"}), 400
        
    event_processor = current_app.config["EVENT_PROCESSOR"]
    result = event_processor.resume_workflow_execution(log, approved, comments)
    return jsonify(result)


# ── Workflow Testing Endpoints ──

@api_bp.route("/workflows/<workflow_id>/test-step", methods=["POST"])
def test_workflow_step(workflow_id):
    data = request.json or {}
    nodes = data.get("nodes")
    node_id = data.get("node_id")
    payload = data.get("payload", {})
    
    if not nodes or not node_id:
        return jsonify({"error": "nodes and node_id are required"}), 400
        
    temp_wf = {
        "id": workflow_id,
        "nodes": nodes
    }
    
    event_processor = current_app.config["EVENT_PROCESSOR"]
    # Run simulation
    run_result = event_processor.run_workflow_nodes(temp_wf, credential=None, event_type="test", payload=payload)
    
    node_result = run_result.get("step_results", {}).get(node_id, {})
    return jsonify(node_result)


@api_bp.route("/workflows/<workflow_id>/test-trigger/start", methods=["POST"])
def test_trigger_start(workflow_id):
    storage = _storage()
    wf = storage.get_workflow(workflow_id)
    if not wf:
        return jsonify({"error": "Workflow not found"}), 404
        
    storage.update_workflow(workflow_id, {
        "testing_trigger": True,
        "captured_payload": None
    })
    return jsonify({"success": True})


@api_bp.route("/workflows/<workflow_id>/test-trigger/poll", methods=["GET"])
def test_trigger_poll(workflow_id):
    storage = _storage()
    wf = storage.get_workflow(workflow_id)
    if not wf:
        return jsonify({"error": "Workflow not found"}), 404
        
    if wf.get("captured_payload") is not None:
        payload = wf["captured_payload"]
        storage.update_workflow(workflow_id, {
            "testing_trigger": False,
            "captured_payload": None
        })
        return jsonify({"success": True, "payload": payload})
        
    return jsonify({"success": False})


@api_bp.route("/workflows/<workflow_id>/test-trigger/stop", methods=["POST"])
def test_trigger_stop(workflow_id):
    storage = _storage()
    wf = storage.get_workflow(workflow_id)
    if not wf:
        return jsonify({"error": "Workflow not found"}), 404
        
    storage.update_workflow(workflow_id, {
        "testing_trigger": False,
        "captured_payload": None
    })
    return jsonify({"success": True})


# ── Webhook connectivity test ──

@api_bp.route("/test-webhook", methods=["POST"])
def test_webhook_connectivity():
    """Quick echo endpoint used from the Help panel / settings to verify connectivity."""
    return jsonify({
        "success": True,
        "echo":    request.json,
        "message": "AppScript Bridge webhook endpoint is reachable",
    })


# ── Dashboard Stats ──

@api_bp.route("/stats", methods=["GET"])
def get_stats():
    storage = _storage()
    workspaces = storage.get_workspaces()
    projects = storage.get_projects()
    workflows = storage.get_workflows()
    events = storage.get_event_logs(limit=1000)

    active_wf = sum(1 for wf in workflows if wf["status"] == "active")
    success_events = sum(1 for e in events if e["status"] == "success")
    failed_events = sum(1 for e in events if e["status"] == "failed")

    return jsonify({
        "workspaces": len(workspaces),
        "projects": len(projects),
        "workflows": {"total": len(workflows), "active": active_wf, "inactive": len(workflows) - active_wf},
        "events": {"total": len(events), "success": success_events, "failed": failed_events},
    })


# ── Settings ──

@api_bp.route("/settings", methods=["GET"])
def get_settings():
    return jsonify(_storage().get_settings())


@api_bp.route("/settings", methods=["PUT"])
def update_settings():
    data = request.json or {}
    return jsonify(_storage().update_settings(data))


# ── AI Flow Generator ──

@api_bp.route("/workflows/generate", methods=["POST"])
def generate_workflow_ai():
    import requests
    import json
    
    storage = _storage()
    settings = storage.get_settings()
    gemini_key = settings.get("gemini_api_key")
    if not gemini_key:
        return jsonify({"error": "Gemini API Key is not set in Settings"}), 400
        
    data = request.json or {}
    user_prompt = data.get("prompt")
    project_id = data.get("project_id")
    workspace_id = data.get("workspace_id")
    selected_cred_ids = data.get("credentials", [])
    selected_script_ids = data.get("scripts", [])
    
    if not user_prompt or not project_id or not workspace_id:
        return jsonify({"error": "prompt, project_id, and workspace_id are required"}), 400
        
    # Gather Credentials Context
    all_creds = storage.get_credentials(workspace_id)
    creds_ctx = []
    for c in all_creds:
        if c["id"] in selected_cred_ids:
            creds_ctx.append({
                "id": c["id"],
                "name": c["name"],
                "app_type": c["app_type"]
            })
            
    # Gather Apps Script Context
    apps_script = current_app.config["APPS_SCRIPT"]
    scripts_ctx = []
    for sid in selected_script_ids:
        # Try to resolve name and functions
        funcs_res = apps_script.get_script_functions(sid)
        functions = []
        if funcs_res.get("success"):
            functions = [f["name"] for f in funcs_res.get("functions", [])]
        
        # Resolve script name
        meta_res = apps_script.get_script_metadata(sid)
        name = "Unknown Apps Script Project"
        if meta_res.get("success"):
            name = meta_res.get("metadata", {}).get("title", name)
            
        scripts_ctx.append({
            "script_id": sid,
            "name": name,
            "functions": functions
        })
        
    # Build System Instructions
    system_instruction = (
        "You are an expert backend integration architect and a visual workflow flow generator.\n"
        "Your task is to take a user prompt requesting an automated workflow flow, look at the available context tools (credentials and scripts), and return a single valid JSON object containing the nodes and parameters mapping configuration.\n"
        "Return RAW JSON only. Do not format your response in markdown blocks (e.g. do NOT include ```json or ```). Output must start with { and end with }.\n\n"
        "Workflow Node Rules:\n"
        "1. Every workflow must start with a node with id: 'trigger' and type: 'trigger'.\n"
        "2. Node definitions follow these schemas:\n"
        "   a. Trigger Node (type: 'trigger'):\n"
        "      config schema: {\n"
        "        \"source_app\": \"(e.g., servicenow, telegram, google_sheets, google_chat, gmail, custom)\",\n"
        "        \"credential_id\": \"(match matching credential ID from context or leave empty string if custom)\",\n"
        "        \"event_type\": \"(trigger event matching app type, e.g. incident.created, message, row.added, custom)\"\n"
        "      }\n"
        "   b. Filter Node (type: 'filter'):\n"
        "      config schema: {\n"
        "        \"logic\": \"AND\" or \"OR\",\n"
        "        \"conditions\": [\n"
        "          {\"field\": \"(e.g., payload.priority or payload.message.text)\", \"operator\": \"eq\"|\"ne\"|\"gt\"|\"lt\"|\"contains\"|\"exists\", \"value\": \"(string comparison value)\"}\n"
        "        ]\n"
        "      }\n"
        "   c. AI Agent Action (type: 'ai_agent'):\n"
        "      config schema: {\n"
        "        \"credential_id\": \"(match matching Gemini or OpenAI credential ID from context)\",\n"
        "        \"model\": \"gemini-2.5-flash\",\n"
        "        \"prompt\": \"(prompt text, you can reference previous payload variables using double curly brackets like {{payload.short_description}})\"\n"
        "      }\n"
        "   d. Apps Script Project Run (type: 'apps_script_api'):\n"
        "      config schema: {\n"
        "        \"script_id\": \"(match script_id from context)\",\n"
        "        \"script_name\": \"(name of script from context)\",\n"
        "        \"function_name\": \"(function name from functions array in context)\",\n"
        "        \"parameters\": [\n"
        "          {\"name\": \"(parameter label)\", \"value\": \"(parameter value, can use mapping like {{payload.some_key}} or LLM response like {{steps.node_xxxx.response.output}})\"}\n"
        "        ]\n"
        "      }\n"
        "   e. Human In The Loop Gate (type: 'human_in_loop'):\n"
        "      config schema: {\n"
        "        \"instruction\": \"(approval instructions display string)\"\n"
        "      }\n"
        "   f. HTTP API Request (type: 'http_request'):\n"
        "      config schema: {\n"
        "        \"method\": \"GET\"|\"POST\"|\"PUT\",\n"
        "        \"url\": \"(request URL)\",\n"
        "        \"headers\": [{\"name\": \"Header-Name\", \"value\": \"Header-Value\"}],\n"
        "        \"body\": \"(raw body string)\"\n"
        "      }\n\n"
        "Important Parameter Chaining Rules:\n"
        "- Trigger output payload is accessible using: {{payload.key_name}}\n"
        "- Previous node's output responses are accessible using: {{steps.node_id.response.key_name}} (e.g., for an AI Agent, its final response is stored in {{steps.node_id.response.output}})\n"
        "- Chain nodes together using the 'next' array containing child node IDs. Nodes must be linked logically.\n"
        "- Give each action node a unique ID starting with 'node_' (e.g. node_1, node_2).\n\n"
        "Target JSON Format:\n"
        "{\n"
        "  \"name\": \"(A user friendly descriptive workflow name)\",\n"
        "  \"description\": \"(Short explanation of workflow)\",\n"
        "  \"nodes\": {\n"
        "    \"trigger\": {\n"
        "      \"id\": \"trigger\",\n"
        "      \"type\": \"trigger\",\n"
        "      \"name\": \"Webhook Trigger\",\n"
        "      \"config\": { ... },\n"
        "      \"next\": [\"node_1\"]\n"
        "    },\n"
        "    \"node_1\": {\n"
        "      \"id\": \"node_1\",\n"
        "      \"type\": \"...\",\n"
        "      \"name\": \"...\",\n"
        "      \"config\": { ... },\n"
        "      \"next\": [ ... ]\n"
        "    }\n"
        "  }\n"
        "}"
    )
    
    prompt = (
        f"Available Credentials:\n{json.dumps(creds_ctx, indent=2)}\n\n"
        f"Available Apps Script Projects:\n{json.dumps(scripts_ctx, indent=2)}\n\n"
        f"User Workflow Request: {user_prompt}"
    )
    
    # Call Gemini API
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
    payload = {
        "contents": [{
            "parts": [{
                "text": f"{system_instruction}\n\n{prompt}"
            }]
        }],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=30)
        if resp.status_code != 200:
            return jsonify({"error": f"Gemini API returned error code {resp.status_code}: {resp.text}"}), 400
            
        res_data = resp.json()
        candidates = res_data.get("candidates", [])
        if not candidates:
            return jsonify({"error": "Gemini API returned no candidates output."}), 400
            
        output_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        if not output_text:
            return jsonify({"error": "Gemini output text empty."}), 400
            
        # Strip markdown syntax if it exists
        output_text = output_text.strip()
        if output_text.startswith("```"):
            lines = output_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            output_text = "\n".join(lines).strip()
            
        wf_generated = json.loads(output_text)
        generated_nodes = wf_generated.get("nodes", {})
        
        if "trigger" not in generated_nodes:
            return jsonify({"error": "AI failed to generate a trigger node in the workflow structure."}), 400
            
        # Auto-coordinate layout calculation
        visited = set()
        def visit(node_id, x, y):
            if node_id in visited or node_id not in generated_nodes:
                return
            visited.add(node_id)
            generated_nodes[node_id]["position"] = {"x": x, "y": y}
            children = generated_nodes[node_id].get("next", [])
            for idx, child_id in enumerate(children):
                y_offset = (idx - (len(children) - 1) / 2.0) * 200
                visit(child_id, x + 350, int(y + y_offset))
                
        visit("trigger", 100, 150)
        
        # Write remaining nodes coordinate safety defaults
        for nid, node in generated_nodes.items():
            if "position" not in node:
                node["position"] = {"x": 100, "y": 150}
                
        # Register and save generated workflow
        trigger_cfg = generated_nodes["trigger"].get("config", {})
        action_node = None
        next_nodes = generated_nodes["trigger"].get("next", [])
        if next_nodes:
            action_node = generated_nodes.get(next_nodes[0])
            
        action_cfg = action_node.get("config", {}) if action_node else {}
        
        wf_data = {
            "project_id": project_id,
            "workspace_id": workspace_id,
            "name": wf_generated.get("name", "AI Generated Flow"),
            "description": wf_generated.get("description", "Workflow generated with Gemini AI assistant"),
            "source_app": trigger_cfg.get("source_app", "custom"),
            "credential_id": trigger_cfg.get("credential_id", ""),
            "event_type": trigger_cfg.get("event_type", "custom"),
            "action_type": action_node.get("type", "apps_script_api") if action_node else "apps_script_api",
            "script_id": action_cfg.get("script_id", ""),
            "script_name": action_cfg.get("script_name", ""),
            "function_name": action_cfg.get("function_name", ""),
            "web_app_url": action_cfg.get("web_app_url", ""),
        }
        
        new_wf = storage.create_workflow(wf_data)
        
        # Override the defaults with complete generated nodes!
        new_wf["nodes"] = generated_nodes
        storage.update_workflow(new_wf["id"], {"nodes": generated_nodes})
        
        return jsonify({"success": True, "workflow_id": new_wf["id"]})
        
    except Exception as e:
        return jsonify({"error": f"Failed to generate workflow: {str(e)}"}), 500
