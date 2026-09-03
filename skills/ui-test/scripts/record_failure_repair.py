#!/usr/bin/env python3
"""Fixed CLI for validating and recording one failure/repair event."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ui_test_core.failure_repair_store import FailureRepairEventStore
from ui_test_core.strict_json import load_strict_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("append", "rebuild"))
    parser.add_argument("--diagnostics-root", required=True)
    parser.add_argument("--product-id", required=True)
    parser.add_argument("--event")
    args = parser.parse_args()
    store = FailureRepairEventStore(Path(args.diagnostics_root), product_id=args.product_id)
    if args.operation == "rebuild":
        result = store.rebuild_projections()
    else:
        if not args.event:
            raise ValueError("E_HISTORY_EVENT_PATH_REQUIRED")
        # 先使用严格 JSON 解析和 Schema 校验，再进入锁定的统一追加接口。
        result = store.append(load_strict_json(args.event))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
