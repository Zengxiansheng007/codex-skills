"""Checkpoint health and savings metrics."""

from __future__ import annotations

from typing import Any


SENSITIVE_LABELS = {"url", "raw_url", "prompt", "request", "response", "authorization", "cookie", "token", "password"}


def checkpoint_metrics(attempts: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [item for item in attempts if item.get("eligible_sample")]
    passed = [item for item in eligible if item.get("status") == "passed"]
    sample = len(eligible)
    rate = len(passed) / sample if sample else None
    if sample < 10:
        health = "insufficient"
    elif sample < 20:
        health = "provisional"
    else:
        health = "healthy" if (rate or 0) >= 0.95 else "degraded"
    return {
        "schema_version": "ui-test.metric-summary.v1",
        "sample_count": sample,
        "reuse_success_rate": rate,
        "health": health,
        "module_ready_success_count": sum(item.get("module_ready", False) for item in attempts),
        "entry_midscene_calls": sum(item.get("entry_midscene_calls", 0) for item in attempts),
        "saved_duration_ms": sum(item.get("saved_duration_ms", 0) for item in attempts),
        "stale_count": sum(item.get("status") == "stale" for item in attempts),
        "fallback_count": sum(bool(item.get("fallback_used")) for item in attempts),
        "flaky_count": sum(item.get("status") == "flaky" for item in attempts),
    }


def project_run_metrics(run_result: dict[str, Any], *, labels: dict[str, str] | None = None) -> list[dict[str, Any]]:
    labels = labels or {}
    sensitive = sorted(key for key in labels if key.lower() in SENSITIVE_LABELS)
    if sensitive:
        raise ValueError("E_METRIC_SENSITIVE_LABEL")
    steps = run_result.get("step_results", [])
    attempts = [attempt for step in steps for attempt in step.get("attempts", [])]
    checkpoint = run_result.get("checkpoint_metrics", {})
    metrics = [
        _metric("midscene.calls", sum(1 for step in steps if step.get("tool") == "midscene"), "count", labels, len(steps)),
        _metric("midscene.entry_calls", sum(step.get("entry_midscene_calls", 0) for step in steps), "count", labels, len(steps)),
        _metric("run.retry_count", sum(max(len(step.get("attempts", [])) - 1, 0) for step in steps), "count", labels, len(steps)),
        _metric("run.fallback_count", sum(bool(step.get("fallback_used")) for step in steps), "count", labels, len(steps)),
        _metric("run.deterministic_conflicts", len(run_result.get("conflicts", [])), "count", labels, len(steps)),
        _metric("checkpoint.hit_count", checkpoint.get("hit_count", 0), "count", labels, checkpoint.get("sample_count", 0)),
        _metric("budget.warning_count", len(run_result.get("budget_warnings", [])), "count", labels, len(steps)),
    ]
    if attempts:
        metrics.append(_metric("run.attempt_duration_ms", sum(item.get("duration_ms", 0) for item in attempts), "ms", labels, len(attempts)))
    return metrics


def _metric(name: str, value: int | float, unit: str, labels: dict[str, str], sample_count: int) -> dict[str, Any]:
    return {
        "schema_version": "ui-test.metric-record.v1",
        "metric_name": name,
        "value": value,
        "unit": unit,
        "labels": dict(sorted(labels.items())),
        "sample_count": sample_count,
        "stability": "insufficient-sample" if sample_count < 10 else "sampled",
    }
