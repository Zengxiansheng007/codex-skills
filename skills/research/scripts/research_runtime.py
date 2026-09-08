"""Deterministic research routing and durable failure boundaries (standard library)."""
from __future__ import annotations
import copy
import hashlib
import ipaddress
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

PROVIDERS = {"auto", "anysearch", "claude", "codex"}
PHASES = {"anysearch-ready", "guided-pending", "review", "paused", "complete"}
SECRET_FIELDS = {"api_key", "apikey", "password", "token", "authorization", "cookie", "secret", "auto_registered"}
SECRET_TEXT = re.compile(r"(?:as_sk_|sk-)[A-Za-z0-9_-]{16,}|Bearer\s+[^\s]+", re.I)
QUOTA_MESSAGES = {"quota_exhausted", "user_daily_quota_exhausted"}
LIMIT = 4 * 1024 * 1024

class GateError(ValueError):
    """A denied operation never changes the persisted task."""

def now():
    return datetime.now(timezone.utc).isoformat()

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

def clean(value, key=""):
    if key.casefold() in SECRET_FIELDS:
        return "[redacted]"  # Drop credential-bearing fields before persistence.
    if isinstance(value, dict):
        return {k: clean(v, k) for k, v in value.items() if k.casefold() not in SECRET_FIELDS}
    if isinstance(value, list):
        return [clean(v) for v in value]
    if isinstance(value, str):
        return SECRET_TEXT.sub("[redacted]", value)
    return value

def public_url(value):
    if not isinstance(value, str):
        return False
    try:
        url = urlsplit(value)
        host = url.hostname or ""
        if url.scheme not in {"http", "https"} or not host or url.username or url.password:
            return False
        if any(k.casefold() in SECRET_FIELDS for k, _ in parse_qsl(url.query)):
            return False
        if host.lower() in {"localhost", "localhost.localdomain"} or host.lower().endswith((".local", ".internal", ".localhost")):
            return False
        try:
            return ipaddress.ip_address(host.strip("[]")).is_global
        except ValueError:
            return "." in host and not host.endswith(".")
    except ValueError:
        return False

def require(condition, message):
    if not condition:
        raise GateError(message)

def event(state, action, **detail):
    state["events"].append({"at": now(), "action": action, **clean(detail)})

def validate(state):
    require(isinstance(state, dict), "state-object-required")
    require(state.get("schemaVersion") == "1.0", "state-version")
    require(isinstance(state.get("taskId"), str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", state["taskId"]), "task-id")
    require(state.get("phase") in PHASES, "state-phase")
    require(state.get("executor") in {"anysearch", "claude", "codex"}, "state-executor")
    require(state.get("requestedProvider") in PROVIDERS, "state-provider")
    require(state.get("branch") == ("anysearch" if state["executor"] == "anysearch" else "research-guided"), "state-branch")
    for field in ("objectives", "sources", "calls", "events", "pending", "completed", "capabilities"):
        require(isinstance(state.get(field), list), "state-field-" + field)
    require(state["objectives"] and all(isinstance(x, str) and x.strip() for x in state["objectives"]), "objectives-required")
    require(len(set(state["objectives"])) == len(state["objectives"]), "duplicate-objective")
    require(isinstance(state.get("fallbackAuthorized"), bool) and isinstance(state.get("noFallback"), bool), "state-authorization")
    require(isinstance(state.get("generation"), int) and state["generation"] >= 1, "state-generation")
    require(isinstance(state.get("requiredParams"), dict), "state-capability-params")
    require(isinstance(state.get("recoveryPending"), bool), "state-recovery")
    require(state.get("reinforcementRounds") in {0, 1}, "state-reinforcement")
    require(state["pending"] == [x for x in state["objectives"] if x not in state["completed"]], "state-progress")
    require(set(state["completed"]).issubset(state["objectives"]), "state-completed")
    require(state.get("pauseReason") if state["phase"] == "paused" else not state.get("pauseReason"), "state-pause-reason")
    require(state["phase"] != "anysearch-ready" or state["executor"] == "anysearch", "state-phase-executor")
    require(state["phase"] != "guided-pending" or state["executor"] != "anysearch", "state-phase-executor")
    require(state["phase"] != "complete" or state.get("qualityReceipt"), "completion-receipt-required")
    return state

def create(task_id, objectives, requested="auto", entry="research", user_choice="", no_fallback=False, codex_authorization=""):
    require(requested in PROVIDERS and entry in {"research", "research-guided"}, "invalid-route")
    require(requested == "auto" or bool(user_choice.strip()), "explicit-choice-evidence-required")
    executor = ("claude" if entry == "research-guided" else "anysearch") if requested == "auto" else requested
    require(entry != "research-guided" or executor != "anysearch", "guided-entry-provider-conflict")
    state = {
        "schemaVersion": "1.0", "taskId": task_id, "requestedProvider": requested,
        "executor": executor, "branch": "anysearch" if executor == "anysearch" else "research-guided",
        "phase": "anysearch-ready" if executor == "anysearch" else "guided-pending",
        "generation": 1, "objectives": objectives, "pending": list(objectives), "completed": [],
        "sources": [], "calls": [], "events": [], "capabilities": [], "requiredParams": {}, "pauseReason": None,
        "fallbackAuthorized": bool(codex_authorization.strip()), "noFallback": bool(no_fallback),
        "reinforcementRounds": 0, "qualityReceipt": None, "recoveryPending": False,
    }
    event(state, "created", explicitUserChoice=user_choice, codexFallbackAuthorization=codex_authorization)
    return validate(state)

def pause(state, reason):
    state["phase"] = "paused"; state["pauseReason"] = reason
    state["recoveryPending"] = True
    event(state, "paused", reason=reason)
    return state

def classify(status, body):
    if status == 402 and isinstance(body, dict) and body.get("code") == -1 and body.get("message") in QUOTA_MESSAGES:
        return "quota-exhausted"  # Unknown forms are deliberately not guessed.
    if status in {401, 403}:
        return "auth-failed"
    if status == 429:
        return "rate-limited"
    if 300 <= status < 400:
        return "redirect-denied"
    return "provider-error"

def switch_guided(state, reason):
    if state["noFallback"]:
        return pause(state, "fallback-forbidden")
    state.update(executor="claude", branch="research-guided", phase="guided-pending", pauseReason=None)
    state["generation"] += 1
    event(state, "routed-guided", reason=reason, executor="claude")
    return state

def resume(state, user_message, requested=None):
    validate(state)
    require(state["phase"] == "paused", "not-paused")
    require(isinstance(user_message, str) and user_message.strip(), "user-resume-evidence-required")
    if requested:
        require(requested in PROVIDERS - {"auto"}, "invalid-resume-provider")
        state["executor"] = requested
        state["requestedProvider"] = requested
    state["branch"] = "anysearch" if state["executor"] == "anysearch" else "research-guided"
    state["phase"] = "anysearch-ready" if state["executor"] == "anysearch" else "guided-pending"
    state["pauseReason"] = None; state["generation"] += 1
    state["recoveryPending"] = True
    event(state, "user-resume", userMessage=user_message, executor=state["executor"])
    return validate(state)  # The next actual call is the recovery probe; no hidden retry.

def guided_failure(state, reason):
    validate(state)
    require(state["phase"] == "guided-pending", "guided-not-pending")
    if state["executor"] == "claude" and state["fallbackAuthorized"] and not state["noFallback"]:
        state["executor"] = "codex"; state["generation"] += 1
        event(state, "authorized-codex-fallback", reason=reason)
        return state
    return pause(state, "guided-unavailable")

def safe_sources(state, raw, objective, method):
    require(isinstance(raw, list), "invalid-results")
    for item in raw:
        require(isinstance(item, dict), "invalid-source")
        url = item.get("url")
        require(public_url(url), "non-public-source-url")
        content = item.get("content") or item.get("snippet") or ""
        require(isinstance(content, str), "invalid-source-content")
        source = {"url": url, "title": str(item.get("title") or url), "content": content[:50000],
                  "readDepth": "body" if method == "extract" else "search-result",
                  "objective": objective, "retrievedAt": now(), "executor": state["executor"]}
        source = clean(source)
        source["sourceId"] = digest({"url": source["url"], "content": source["content"]})[:20]
        if not any(s["sourceId"] == source["sourceId"] and s["objective"] == objective for s in state["sources"]):
            state["sources"].append(source)

def execute_anysearch(state, items, key, transport, persist=lambda state: None):
    validate(state)
    require(state["executor"] == "anysearch" and state["phase"] == "anysearch-ready", "retrieval-not-permitted")
    require(isinstance(items, list) and 1 <= len(items) <= 5, "one-to-five-items")
    if not isinstance(key, str) or not key.strip():
        pause(state, "credential-missing"); persist(state); return state
    for item in items:
        require(isinstance(item, dict), "invalid-request-item")
        objective = item.get("objective")
        require(objective in state["objectives"], "unknown-objective")
        method = item.get("operation", "search")
        require(method in {"search", "extract", "get_sub_domains"}, "unsupported-operation")
        payload = {k: v for k, v in item.items() if k in {"query", "url", "tag", "params", "max_results", "domain", "zone", "language"}}
        if method == "search":
            require(isinstance(payload.get("query"), str) and payload["query"].strip(), "query-required")
            if payload.get("tag"):
                require(payload["tag"] in state["capabilities"], "discover-domain-before-search")
                params = payload.get("params", {})
                require(isinstance(params, dict), "invalid-domain-params")
                require(all(k in params for k in state["requiredParams"].get(payload["tag"], [])), "missing-domain-params")
            if "max_results" in payload:
                require(type(payload["max_results"]) is int and 1 <= payload["max_results"] <= 10, "max-results")
        if method == "extract":
            require(public_url(payload.get("url")), "extract-public-url-required")
        if method == "get_sub_domains":
            require(isinstance(payload.get("domain"), str) and re.fullmatch(r"[a-z_]+", payload["domain"]), "domain-required")
        call = {"operation": method, "objective": objective, "at": now(), "status": "started"}
        state["calls"].append(call); persist(state)  # Persist intent before an observable request.
        try:
            status, body = transport(method, payload, key)
            require(isinstance(status, int) and isinstance(body, dict), "invalid-response")
            # Remove even unlabelled occurrences of the actual key before processing.
            body = json.loads(canonical(clean(body)).replace(key, "[redacted]"))
            if not (200 <= status < 300 and type(body.get("code")) is int and body["code"] == 0):
                failure = classify(status, body)
                call.update(status="error", failure=failure, httpStatus=status)
                switch_guided(state, failure) if failure == "quota-exhausted" else pause(state, failure)
                persist(state); return state
            data = body.get("data")
            require(isinstance(data, dict), "invalid-response-data")
            if method == "get_sub_domains":
                domains = data.get("domains")
                require(isinstance(domains, list), "invalid-capabilities")
                for domain in domains:
                    for capability in domain.get("sub_domains", []):
                        tag = capability.get("sub_domain")
                        if isinstance(tag, str) and tag not in state["capabilities"]:
                            state["capabilities"].append(tag)
                        if isinstance(tag, str):
                            state["requiredParams"][tag] = [name for name, spec in capability.get("params", {}).items()
                                if isinstance(spec, dict) and spec.get("required") is True]
            elif method == "search":
                safe_sources(state, data.get("results"), objective, method)
            else:
                require(isinstance(data.get("content"), str), "invalid-extract-content")
                safe_sources(state, [data], objective, method)
            call["status"] = "ok"
            state["recoveryPending"] = False
            event(state, "request-recorded", objective=objective, operation=method)
        except Exception:
            call.update(status="error", failure="transport-or-response-error")
            pause(state, "transport-or-response-error")  # Never persist exception text or raw responses.
            persist(state); return state
        persist(state)
    return state

def guided_handoff(state):
    validate(state)
    require(state["phase"] == "guided-pending", "guided-not-pending")
    return {"kind": "research-guided-handoff", "taskId": state["taskId"], "generation": state["generation"],
            "executor": state["executor"], "objectives": state["pending"], "sources": state["sources"],
            "requiresActualExecution": True, "completionAuthority": "Codex"}

def accept_guided(state, receipt):
    validate(state)
    require(state["phase"] == "guided-pending", "guided-not-pending")
    require(isinstance(receipt, dict) and receipt.get("taskId") == state["taskId"]
            and receipt.get("generation") == state["generation"] and receipt.get("executor") == state["executor"], "guided-lineage")
    require(receipt.get("actualRetrieval") is True and isinstance(receipt.get("toolEvidence"), list)
            and receipt["toolEvidence"] and receipt.get("hostValidationPassed") is True, "actual-guided-evidence-required")
    raw = receipt.get("sources")
    require(isinstance(raw, list) and raw, "guided-sources-required")
    for item in raw:
        require(item.get("objective") in state["objectives"], "unknown-guided-objective")
        safe_sources(state, [item], item["objective"], "extract" if item.get("readDepth") == "body" else "search")
    event(state, "guided-evidence-accepted", executor=state["executor"], toolEvidence=clean(receipt["toolEvidence"]))
    state["phase"] = "review"
    state["recoveryPending"] = False
    return state

def complete(state, review):
    validate(state)
    require(state["phase"] in {"anysearch-ready", "review"}, "completion-not-permitted")
    require(not state["recoveryPending"], "recovery-probe-required")
    require(isinstance(review, dict) and review.get("taskId") == state["taskId"], "review-task")
    require(review.get("generation") == state["generation"], "review-generation")
    require(review.get("reviewedBy") == "Codex" and review.get("actualEvidenceReviewed") is True, "review-attestation")
    require(review.get("gaps") == [], "unresolved-gaps")
    claims = review.get("claims")
    require(isinstance(claims, list) and claims, "claims-required")
    sources = {s["sourceId"]: s for s in state["sources"]}
    covered = set()
    for claim in claims:
        require(isinstance(claim, dict) and isinstance(claim.get("text"), str) and claim["text"].strip(), "claim-text")
        objective = claim.get("objective")
        refs = claim.get("sourceIds")
        require(objective in state["objectives"] and isinstance(refs, list) and refs, "claim-coverage")
        require(all(ref in sources and sources[ref]["objective"] == objective and sources[ref]["content"].strip() for ref in refs), "claim-source-mapping")
        covered.add(objective)
    require(covered == set(state["objectives"]), "incomplete-coverage")
    state["qualityReceipt"] = clean(review)
    state["completed"] = list(state["objectives"]); state["pending"] = []
    state["phase"] = "complete"
    event(state, "quality-accepted", evidenceHash=digest(state["sources"]))
    return validate(state)

def reinforce(state, user_light_confirmation=None):
    validate(state)
    require(state["phase"] in {"anysearch-ready", "review"}, "reinforcement-not-permitted")
    require(not state["recoveryPending"], "recovery-probe-required")
    require(state["reinforcementRounds"] < 1, "reinforcement-limit")
    state["reinforcementRounds"] += 1
    state["phase"] = "anysearch-ready" if state["executor"] == "anysearch" else "guided-pending"
    state["generation"] += 1
    event(state, "content-reinforcement")
    return state

class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        skill_container = Path(__file__).resolve().parent.parent.parent
        require(not self.root.is_relative_to(skill_container), "state-dir-inside-skill-container")
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, task_id):
        require(isinstance(task_id, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", task_id), "task-id")
        path = self.root / (task_id + ".json")
        require(not path.is_symlink(), "state-symlink")
        return path

    def load(self, task_id):
        path = self.path(task_id)
        require(path.stat().st_size <= LIMIT, "state-too-large")
        document = json.loads(path.read_text(encoding="utf-8"))
        state = document.get("state")
        require(document.get("sha256") == digest(state), "state-integrity")
        validate(state)
        require(state["taskId"] == task_id, "state-task-mismatch")
        # An interrupted outbound request must never be retried implicitly.
        if any(c.get("status") == "started" for c in state["calls"]):
            pause(state, "interrupted-request")
            for call in state["calls"]:
                if call["status"] == "started":
                    call.update(status="error", failure="interrupted-request")
            self.save(state)
        return state

    def save(self, state, create_only=False):
        validate(state)
        state = clean(state)
        path = self.path(state["taskId"])
        if create_only:
            require(not path.exists(), "task-already-exists")
        payload = canonical({"state": state, "sha256": digest(state)}).encode("utf-8")
        require(len(payload) <= LIMIT, "state-too-large")
        descriptor, temp_name = tempfile.mkstemp(prefix=".research-", dir=self.root)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload); handle.flush(); os.fsync(handle.fileno())
            if create_only:
                os.link(temp_name, path)
                os.unlink(temp_name)
            else:
                os.replace(temp_name, path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
