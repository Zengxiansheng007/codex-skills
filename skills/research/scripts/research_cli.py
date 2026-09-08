"""CLI for host-orchestrated research. The host supplies actual user directives."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
from research_runtime import (GateError, Store, accept_guided, clean, complete, create,
                              execute_anysearch, guided_failure, guided_handoff, pause,
                              reinforce, resume)
from anysearch_boundary import perform

@contextmanager
def lock(store, task_id):
    path = store.path(task_id).with_suffix(".lock")
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.close(descriptor)
        yield
    finally:
        path.unlink(missing_ok=True)  # Only this invocation's exclusive task lock.

def read_json(path):
    item = Path(path)
    if item.stat().st_size > 2 * 1024 * 1024:
        raise GateError("input-too-large")
    return json.loads(item.read_text(encoding="utf-8"))

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--task", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    start = sub.add_parser("create")
    start.add_argument("--objectives", required=True, help="JSON file containing a list")
    start.add_argument("--provider", choices=["auto","anysearch","claude","codex"], default="auto")
    start.add_argument("--entry", choices=["research","research-guided"], default="research")
    start.add_argument("--user-choice", default="")
    start.add_argument("--no-fallback", action="store_true")
    start.add_argument("--codex-authorization", default="")
    sub.add_parser("status"); sub.add_parser("handoff")
    execute = sub.add_parser("execute-anysearch")
    execute.add_argument("--items", required=True)
    execute.add_argument("--public-retrieval-authorized", action="store_true")
    recover = sub.add_parser("resume")
    recover.add_argument("--user-message", required=True)
    recover.add_argument("--provider", choices=["anysearch","claude","codex"])
    feedback = sub.add_parser("accept-guided"); feedback.add_argument("--receipt", required=True)
    failure = sub.add_parser("guided-failure"); failure.add_argument("--reason", default="unavailable")
    review = sub.add_parser("complete"); review.add_argument("--review", required=True)
    sub.add_parser("reinforce")
    args = parser.parse_args(argv)
    state = None; store = None
    try:
        store = Store(args.state_dir)
        with lock(store, args.task):
            if args.command == "create":
                state = create(args.task, read_json(args.objectives), args.provider, args.entry,
                               args.user_choice, args.no_fallback, args.codex_authorization)
                store.save(state, create_only=True)
            else:
                state = store.load(args.task)
                if args.command == "execute-anysearch":
                    if not args.public_retrieval_authorized:
                        raise GateError("public-retrieval-authorization-required")
                    try:
                        execute_anysearch(state, read_json(args.items), os.environ.get("ANYSEARCH_API_KEY",""),
                                          perform, persist=store.save)
                    except Exception:
                        if state.get("phase") == "anysearch-ready":
                            pause(state, "invalid-request")
                            store.save(state)  # Persist failure before releasing the task lock.
                        raise
                elif args.command == "resume":
                    resume(state, args.user_message, args.provider)
                elif args.command == "accept-guided":
                    accept_guided(state, read_json(args.receipt))
                elif args.command == "guided-failure":
                    guided_failure(state, args.reason)
                elif args.command == "complete":
                    complete(state, read_json(args.review))
                elif args.command == "reinforce":
                    reinforce(state)
                elif args.command == "handoff":
                    print(json.dumps(clean(guided_handoff(state)), ensure_ascii=False))
                    return 0
                store.save(state)
            print(json.dumps(clean(state), ensure_ascii=False))
            return 2 if state["phase"] == "paused" else 0
    except FileExistsError:
        print(json.dumps({"status":"denied","reason":"task-exists-or-locked"}))
        return 3
    except Exception as exc:
        # Validation detail is safe; transport exceptions never escape the runtime.
        reason = str(exc) if isinstance(exc, GateError) else "invalid-input-or-state"
        print(json.dumps({"status":"denied","reason":clean(reason)}, ensure_ascii=False))
        return 3

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # JSON output stays UTF-8 on Windows.
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
