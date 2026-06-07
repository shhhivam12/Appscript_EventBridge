import re

_EXPR = re.compile(r'\{\{([^}]+)\}\}')


def _get_nested(obj, path):
    """Resolve a dot-path like 'payload.incident.number' against obj.
    Leading 'payload.' prefix is stripped so users can write either form."""
    if path.startswith("payload."):
        path = path[8:]
    val = obj
    for part in path.split("."):
        if isinstance(val, dict):
            val = val.get(part)
        else:
            return None
    return val


class EventProcessor:
    def __init__(self, storage, apps_script_service):
        self.storage = storage
        self.script_service = apps_script_service

    # ── Credential validation ────────────────────────────────────────────────

    def validate_api_key(self, api_key):
        cred = self.storage.get_credential_by_api_key(api_key)
        if not cred:
            return None, "Invalid API key"
        if not cred["is_active"]:
            return None, "Credential is deactivated"
        return cred, None

    def validate_credential(self, credential_id):
        cred = self.storage.get_credential(credential_id)
        if not cred:
            return None, "Credential not found"
        if not cred["is_active"]:
            return None, "Credential is deactivated"
        return cred, None

    # ── Workflow matching ────────────────────────────────────────────────────

    def find_workflows(self, credential_id, event_type=None):
        """Return active workflows whose trigger matches credential + event_type.
        Matching is case-insensitive; 'custom' acts as a wildcard."""
        matching = []
        for wf in self.storage.get_workflows():
            if wf["status"] != "active":
                continue
            trigger = wf.get("trigger", {})
            if trigger.get("credential_id") != credential_id:
                continue
            wf_event = (trigger.get("event_type") or "").lower().strip()
            in_event  = (event_type or "").lower().strip()
            if wf_event and in_event and wf_event not in (in_event, "custom"):
                continue
            matching.append(wf)
        return matching

    # ── Filter evaluation ────────────────────────────────────────────────────

    def _passes_filter(self, filter_cfg, payload):
        """Return (passes: bool, reason: str).
        passes=True means the payload satisfies all filter conditions."""
        if not filter_cfg or not filter_cfg.get("enabled"):
            return True, ""

        conditions = filter_cfg.get("conditions") or []
        if not conditions:
            return True, ""

        logic   = (filter_cfg.get("logic") or "AND").upper()
        results = []

        for cond in conditions:
            field    = (cond.get("field") or "").strip()
            operator = (cond.get("operator") or "eq").strip()
            expected = str(cond.get("value") or "")
            actual   = _get_nested(payload, field) if field else None
            results.append(self._compare(actual, operator, expected))

        passed = any(results) if logic == "OR" else all(results)
        if not passed:
            reason = f"Filter ({logic}) blocked: " + "; ".join(
                f"{c.get('field')} {c.get('operator')} {c.get('value')}"
                for c in conditions
            )
            return False, reason
        return True, ""

    @staticmethod
    def _compare(actual, operator, expected):
        try:
            if operator in ("eq",  "=="):  return str(actual) == str(expected)
            if operator in ("ne",  "!="):  return str(actual) != str(expected)
            if operator in ("gt",  ">"):   return float(actual) > float(expected)
            if operator in ("lt",  "<"):   return float(actual) < float(expected)
            if operator in ("gte", ">="):  return float(actual) >= float(expected)
            if operator in ("lte", "<="):  return float(actual) <= float(expected)
            if operator == "contains":     return str(expected).lower() in str(actual or "").lower()
            if operator == "not_contains": return str(expected).lower() not in str(actual or "").lower()
            if operator == "exists":       return actual is not None
            if operator == "not_exists":   return actual is None
            if operator == "starts_with":  return str(actual or "").lower().startswith(str(expected).lower())
            if operator == "ends_with":    return str(actual or "").lower().endswith(str(expected).lower())
        except (TypeError, ValueError):
            return False
        return False

    # ── Parameter resolution ─────────────────────────────────────────────────

    @staticmethod
    def _resolve_params(mappings, payload):
        """Resolve a [{name, value}] mapping list against payload.
        Expressions like {{payload.field}} are substituted with live values.
        Returns a dict, or None if mappings is empty (→ pass full payload)."""
        if not mappings:
            return None

        def _sub(match):
            val = _get_nested(payload, match.group(1).strip())
            return str(val) if val is not None else ""

        result = {}
        for m in mappings:
            name = (m.get("name") or "").strip()
            if not name:
                continue
            raw_value = str(m.get("value") or "")
            result[name] = _EXPR.sub(_sub, raw_value)
        return result or None

    # ── Variable & Template Resolution ────────────────────────────────────────

    def resolve_value(self, path, step_results):
        """Resolves a path like 'steps.node_id.payload.field' or 'payload.field' against step_results."""
        path = path.strip()
        if path.startswith("steps."):
            parts = path.split(".")
            if len(parts) >= 2:
                node_id = parts[1]
                sub_path = ".".join(parts[2:])
                node_data = step_results.get(node_id, {})
                return self._get_nested_val(node_data, sub_path)
        
        # Fallback to trigger payload
        if path.startswith("payload."):
            path = path[8:]
        trigger_payload = step_results.get("trigger", {}).get("payload", {})
        return self._get_nested_val(trigger_payload, path)

    def _get_nested_val(self, obj, path):
        if not path:
            return obj
        val = obj
        for part in path.split("."):
            if isinstance(val, dict):
                val = val.get(part)
            else:
                return None
        return val

    def resolve_template(self, template_str, step_results):
        if not template_str:
            return ""
        def _sub(match):
            val = self.resolve_value(match.group(1).strip(), step_results)
            return str(val) if val is not None else ""
        return _EXPR.sub(_sub, str(template_str))

    # ── Graph Execution Engine ────────────────────────────────────────────────

    def run_workflow_nodes(self, wf, credential, event_type, payload, execution_state=None):
        """Runs a workflow node graph starting either from scratch or from a saved execution_state."""
        if execution_state:
            step_results = execution_state.get("step_results")
            queue = execution_state.get("queue")
            visited = set(execution_state.get("visited", []))
        else:
            step_results = {
                "trigger": {
                    "payload": payload,
                    "response": payload,
                    "status": "success"
                }
            }
            queue = list(wf["nodes"]["trigger"].get("next", []))
            visited = {"trigger"}
            
        nodes = wf["nodes"]
        paused = False
        paused_node_id = None
        paused_instruction = ""
        
        while queue:
            node_id = queue.pop(0)
            if node_id in visited:
                continue
            visited.add(node_id)
            
            node = nodes.get(node_id)
            if not node:
                continue
                
            node_type = node.get("type")
            config = node.get("config") or {}
            success = True
            
            if node_type == "filter":
                conditions = config.get("conditions") or []
                logic = config.get("logic") or "AND"
                results = []
                for cond in conditions:
                    field = cond.get("field") or ""
                    operator = cond.get("operator") or "eq"
                    expected = cond.get("value") or ""
                    actual = self.resolve_value(field, step_results)
                    results.append(self._compare(actual, operator, expected))
                
                passed = any(results) if logic == "OR" else all(results)
                step_results[node_id] = {"status": "success" if passed else "skipped", "response": {"passed": passed}}
                success = passed
                
            elif node_type == "apps_script_api":
                params = config.get("parameters") or []
                resolved_params = {}
                for p in params:
                    resolved_params[p["name"]] = self.resolve_template(p.get("value"), step_results)
                call_params = resolved_params if params else step_results["trigger"]["payload"]
                result = self.script_service.run_script(
                    config.get("script_id", ""),
                    config.get("function_name", ""),
                    parameters=call_params,
                )
                step_results[node_id] = {
                    "status": "success" if result.get("success") else "failed",
                    "response": result.get("response", {}),
                    "error": result.get("error", ""),
                    "processing_time_ms": result.get("processing_time_ms", 0)
                }
                success = result.get("success", False)
                
            elif node_type == "web_app":
                params = config.get("parameters") or []
                resolved_params = {}
                for p in params:
                    resolved_params[p["name"]] = self.resolve_template(p.get("value"), step_results)
                call_params = resolved_params if params else step_results["trigger"]["payload"]
                result = self.script_service.call_web_app(
                    config.get("web_app_url", ""),
                    payload=call_params,
                )
                step_results[node_id] = {
                    "status": "success" if result.get("success") else "failed",
                    "response": result.get("response", {}),
                    "error": result.get("error", ""),
                    "processing_time_ms": result.get("processing_time_ms", 0)
                }
                success = result.get("success", False)
                
            elif node_type == "ai_agent":
                prompt_tpl = config.get("prompt", "")
                prompt = self.resolve_template(prompt_tpl, step_results)
                cred_id = config.get("credential_id")
                cred = self.storage.get_credential(cred_id)
                if not cred:
                    step_results[node_id] = {"status": "failed", "error": "AI credential not found"}
                    success = False
                else:
                    api_key = cred.get("config", {}).get("api_key")
                    app_type = cred.get("app_type")
                    model = cred.get("config", {}).get("model")
                    
                    import requests
                    import json
                    
                    if app_type == "gemini":
                        actual_model = model or "gemini-2.5-flash"
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{actual_model}:generateContent?key={api_key}"
                        headers = {"Content-Type": "application/json"}
                        payload_data = {"contents": [{"parts": [{"text": prompt}]}]}
                        try:
                            res = requests.post(url, headers=headers, json=payload_data, timeout=30)
                            res.raise_for_status()
                            res_json = res.json()
                            response_text = res_json["candidates"][0]["content"]["parts"][0]["text"]
                            success = True
                            err = ""
                        except Exception as e:
                            response_text = ""
                            success = False
                            err = f"Gemini API Error: {str(e)}"
                    elif app_type == "openai":
                        actual_model = model or "gpt-4o-mini"
                        url = "https://api.openai.com/v1/chat/completions"
                        headers = {
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {api_key}"
                        }
                        payload_data = {
                            "model": actual_model,
                            "messages": [{"role": "user", "content": prompt}]
                        }
                        try:
                            res = requests.post(url, headers=headers, json=payload_data, timeout=30)
                            res.raise_for_status()
                            res_json = res.json()
                            response_text = res_json["choices"][0]["message"]["content"]
                            success = True
                            err = ""
                        except Exception as e:
                            response_text = ""
                            success = False
                            err = f"OpenAI API Error: {str(e)}"
                    else:
                        step_results[node_id] = {"status": "failed", "error": f"Unknown AI provider: {app_type}"}
                        success = False
                        
                    if success:
                        cleaned_text = response_text.strip()
                        if cleaned_text.startswith("```"):
                            lines = cleaned_text.splitlines()
                            if lines[0].startswith("```"):
                                lines = lines[1:]
                            if lines and lines[-1].startswith("```"):
                                lines = lines[:-1]
                            cleaned_text = "\n".join(lines).strip()
                        
                        try:
                            response_json = json.loads(cleaned_text)
                            step_results[node_id] = {
                                "status": "success",
                                "response": response_json,
                                "text": response_text
                            }
                        except Exception:
                            step_results[node_id] = {
                                "status": "success",
                                "response": {"text": response_text},
                                "text": response_text
                            }
                    else:
                        step_results[node_id] = {"status": "failed", "error": err}
                
            elif node_type == "http_request":
                method = config.get("method", "GET").upper()
                url = self.resolve_template(config.get("url", ""), step_results)
                headers_list = config.get("headers") or []
                headers = {}
                for h in headers_list:
                    h_name = h.get("name")
                    h_val = self.resolve_template(h.get("value", ""), step_results)
                    if h_name:
                        headers[h_name] = h_val
                body_tpl = config.get("body", "")
                resolved_body = self.resolve_template(body_tpl, step_results)
                
                import requests
                try:
                    if method == "GET":
                        res = requests.get(url, headers=headers, timeout=15)
                    elif method == "POST":
                        res = requests.post(url, headers=headers, data=resolved_body, timeout=15)
                    elif method == "PUT":
                        res = requests.put(url, headers=headers, data=resolved_body, timeout=15)
                    elif method == "DELETE":
                        res = requests.delete(url, headers=headers, data=resolved_body, timeout=15)
                    elif method == "PATCH":
                        res = requests.patch(url, headers=headers, data=resolved_body, timeout=15)
                    else:
                        raise ValueError(f"Unsupported HTTP method: {method}")
                        
                    success = (200 <= res.status_code < 300)
                    status_code = res.status_code
                    try:
                        res_data = res.json()
                    except Exception:
                        res_data = {"text": res.text}
                        
                    step_results[node_id] = {
                        "status": "success" if success else "failed",
                        "response": res_data,
                        "status_code": status_code,
                        "error": "" if success else f"HTTP error status code {status_code}"
                    }
                except Exception as e:
                    success = False
                    step_results[node_id] = {
                        "status": "failed",
                        "response": {},
                        "error": str(e)
                    }
                    
            elif node_type == "human_in_loop":
                inst_tpl = config.get("instruction", "")
                paused_instruction = self.resolve_template(inst_tpl, step_results)
                paused = True
                paused_node_id = node_id
                break

            if success:
                for next_id in node.get("next", []):
                    queue.append(next_id)
                    
        if paused:
            return {
                "status": "pending_human",
                "paused_node_id": paused_node_id,
                "paused_instruction": paused_instruction,
                "step_results": step_results,
                "queue": queue,
                "visited": list(visited)
            }
            
        all_success = True
        final_errors = []
        for nid, r in step_results.items():
            if r.get("status") == "failed":
                all_success = False
                final_errors.append(f"{nid}: {r.get('error')}")
                
        final_response = {}
        if "action_node" in step_results:
            final_response = step_results["action_node"].get("response", {})
        else:
            keys = list(step_results.keys())
            if len(keys) > 1:
                final_response = step_results[keys[-1]].get("response", {})
                
        return {
            "status": "success" if all_success else "failed",
            "error": "; ".join(final_errors),
            "step_results": step_results,
            "response": final_response
        }

    # ── Event processing ─────────────────────────────────────────────────────

    def process_event(self, credential, event_type, payload):
        # Intercept and capture payload if workflow trigger is in testing/listening mode
        for wf in self.storage.get_workflows():
            trig_config = wf.get("nodes", {}).get("trigger", {}).get("config", {})
            if wf.get("testing_trigger") and trig_config.get("credential_id") == credential["id"]:
                wf_event = (trig_config.get("event_type") or "").lower().strip()
                in_event = (event_type or "").lower().strip()
                if not wf_event or wf_event in (in_event, "custom"):
                    self.storage.update_workflow(wf["id"], {
                        "captured_payload": payload,
                        "testing_trigger": False
                    })

        workflows = self.find_workflows(credential["id"], event_type)

        if not workflows:
            log = self.storage.create_event_log({
                "credential_id": credential["id"],
                "source_app":    credential.get("app_type", "custom"),
                "event_type":    event_type or "unknown",
                "payload":       payload,
                "status":        "skipped",
                "error":         "No active workflows matched this credential + event type",
            })
            return {"processed": 0, "skipped": 1, "logs": [log]}

        results  = []
        skipped  = 0
        import time
        for wf in workflows:
            t0 = time.time()
            # Execute workflow node graph
            run_res = self.run_workflow_nodes(wf, credential, event_type, payload)
            processing_time_ms = int((time.time() - t0) * 1000)

            log_data = {
                "workflow_id":        wf["id"],
                "credential_id":      credential["id"],
                "source_app":         credential.get("app_type", "custom"),
                "event_type":         event_type or "unknown",
                "payload":            payload,
                "status":             run_res["status"],
                "response":           run_res.get("response", {}),
                "error":              run_res.get("error", ""),
                "processing_time_ms": processing_time_ms,
                "step_results":       run_res["step_results"]
            }

            if run_res["status"] == "pending_human":
                # Save execution state to let user resume later
                log_data["execution_state"] = {
                    "step_results": run_res["step_results"],
                    "queue":        run_res["queue"],
                    "visited":      run_res["visited"]
                }
                log_data["human_step_info"] = {
                    "node_id":     run_res["paused_node_id"],
                    "name":        wf["nodes"][run_res["paused_node_id"]].get("name", "Human Gate"),
                    "instruction": run_res["paused_instruction"]
                }

            log = self.storage.create_event_log(log_data)
            
            self.storage.update_workflow(wf["id"], {
                "last_triggered": self.storage._now(),
                "trigger_count":  wf.get("trigger_count", 0) + 1,
            })
            results.append(log)

        succeeded = sum(1 for r in results if r["status"] == "success")
        failed    = sum(1 for r in results if r["status"] == "failed")
        skipped   = sum(1 for r in results if r["status"] == "skipped")
        pending   = sum(1 for r in results if r["status"] == "pending_human")
        return {"processed": succeeded, "failed": failed, "skipped": skipped, "pending": pending, "logs": results}

    def resume_workflow_execution(self, log, approved, comments):
        """Resumes a paused workflow execution from a human-in-the-loop task."""
        execution_state = log.get("execution_state")
        if not execution_state:
            return {"success": False, "error": "No execution state found in log"}
            
        workflow_id = log.get("workflow_id")
        wf = self.storage.get_workflow(workflow_id)
        if not wf:
            return {"success": False, "error": "Workflow not found"}
            
        human_info = log.get("human_step_info")
        node_id = human_info["node_id"]
        
        # Update human node results
        step_results = execution_state["step_results"]
        step_results[node_id] = {
            "status": "success",
            "response": {"approved": approved, "comments": comments}
        }
        
        # Enqueue children of human gate
        queue = execution_state.get("queue", [])
        nodes = wf.get("nodes", {})
        human_node = nodes.get(node_id, {})
        for next_id in human_node.get("next", []):
            queue.append(next_id)
            
        execution_state["queue"] = queue
        execution_state["step_results"] = step_results
        
        import time
        t0 = time.time()
        
        run_res = self.run_workflow_nodes(wf, None, None, None, execution_state=execution_state)
        processing_time_ms = int((time.time() - t0) * 1000)
        
        log["status"] = run_res["status"]
        log["response"] = run_res.get("response", {})
        log["error"] = run_res.get("error", "")
        log["processing_time_ms"] = log.get("processing_time_ms", 0) + processing_time_ms
        log["step_results"] = run_res["step_results"]
        
        if run_res["status"] == "pending_human":
            # Re-save execution state for another human node if hit again
            log["execution_state"] = {
                "step_results": run_res["step_results"],
                "queue":        run_res["queue"],
                "visited":      run_res["visited"]
            }
            log["human_step_info"] = {
                "node_id":     run_res["paused_node_id"],
                "name":        wf["nodes"][run_res["paused_node_id"]].get("name", "Human Gate"),
                "instruction": run_res["paused_instruction"]
            }
        else:
            # Done, clean up
            log.pop("execution_state", None)
            log.pop("human_step_info", None)
        
        event_logs = self.storage._read_file("event_logs")
        for i, el in enumerate(event_logs):
            if el["id"] == log["id"]:
                event_logs[i] = log
                break
        self.storage._write_file("event_logs", event_logs)
        
        return {
            "success": run_res["status"] == "success",
            "status": run_res["status"],
            "log": log
        }

    # ── Telegram parser ──────────────────────────────────────────────────────

    @staticmethod
    def parse_telegram_event(update):
        """Map a Telegram Update object to (event_type, payload)."""
        if "message" in update:
            text = update["message"].get("text", "")
            return ("command" if text.startswith("/") else "message"), update
        if "edited_message" in update:
            return "edited_message", update
        if "callback_query" in update:
            return "callback_query", update
        if "inline_query" in update:
            return "inline_query", update
        return "message", update

    # ── ServiceNow parser ────────────────────────────────────────────────────

    @staticmethod
    def parse_servicenow_event(payload):
        """Extract a normalised event_type from a ServiceNow webhook payload."""
        raw = (
            payload.get("event_type")
            or payload.get("event")
            or payload.get("type")
        )
        if not raw:
            table  = (payload.get("table") or payload.get("tableName") or "").lower()
            action = (
                payload.get("sys_action")
                or payload.get("action")
                or payload.get("operation")
                or ""
            ).lower()
            action_map = {
                "insert": "created", "inserted": "created",
                "update": "updated", "updated":  "updated",
                "delete": "deleted", "deleted":  "deleted",
            }
            mapped = action_map.get(action, action)
            raw = f"{table}.{mapped}" if table and mapped else (f"{table}.changed" if table else None)

        return (raw or "custom").lower().strip(), payload

    # ── Google Workspace parser ──────────────────────────────────────────────

    @staticmethod
    def parse_google_event(app_type, payload):
        """Map a Google Workspace event payload to (event_type, payload)."""
        import base64
        import json

        if app_type == "google_chat":
            event_type = "message.received"
            raw_type = payload.get("type")
            if raw_type == "ADDED_TO_SPACE":
                event_type = "added_to_space"
            elif raw_type == "REMOVED_FROM_SPACE":
                event_type = "removed_from_space"
            elif raw_type == "MESSAGE":
                event_type = "message.received"
            return event_type, payload

        elif app_type == "gmail":
            # Gmail Push Notification format: {"message": {"data": "...", "messageId": "..."}}
            event_type = "message.received"
            msg_data = payload.get("message", {})
            raw_data = msg_data.get("data")
            if raw_data:
                try:
                    # Pad base64 data if needed
                    missing_padding = len(raw_data) % 4
                    if missing_padding:
                        raw_data += '=' * (4 - missing_padding)
                    decoded = base64.b64decode(raw_data).decode("utf-8")
                    decoded_json = json.loads(decoded)
                    payload["decoded_message"] = decoded_json
                    if "historyId" in decoded_json:
                        event_type = "message.received"
                except Exception:
                    pass
            return event_type, payload

        elif app_type == "google_drive":
            # Google watch resource state: X-Goog-Resource-State header (mapped in payload)
            state = payload.get("resource_state", "update").lower()
            event_type = "file.updated"
            if state == "add":
                event_type = "file.created"
            elif state == "trash" or state == "remove":
                event_type = "file.deleted"
            return event_type, payload

        elif app_type == "google_sheets":
            # Google Sheets Apps Script edit triggers or custom watch
            event_type = payload.get("event") or "spreadsheet.updated"
            return event_type, payload

        elif app_type == "google_calendar":
            # Google Watch Calendar events
            state = payload.get("resource_state", "exists").lower()
            event_type = "event.updated"
            if state == "exists":
                event_type = "event.updated"
            elif state == "not_exists":
                event_type = "event.deleted"
            return event_type, payload

        return "custom", payload
