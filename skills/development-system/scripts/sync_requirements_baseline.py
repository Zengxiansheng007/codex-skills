"""Create the portable Phase/Story trace fixture from the authority baseline."""

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    source = Path(args.source).resolve()
    out = Path(args.out).resolve()
    data = json.loads(source.read_text(encoding="utf-8"))
    compact = {
        "documentId": data.get("documentId"),
        "version": data.get("version"),
        "status": data.get("status"),
        "functionalRequirements": [item["id"] for item in data.get("functionalRequirements", [])],
        "nonFunctionalRequirements": [item["id"] for item in data.get("nonFunctionalRequirements", [])],
        "acceptanceCriteria": [item["id"] for item in data.get("acceptanceCriteria", [])],
        "phases": [],
    }
    for phase in data.get("phases", []):
        compact["phases"].append({
            "phaseId": phase.get("phaseId"),
            "entryCriteria": phase.get("entryCriteria", []),
            "exitCriteria": phase.get("exitCriteria", []),
            "stories": [
                {
                    "storyId": story.get("storyId"),
                    "mappedRequirements": story.get("mappedRequirements", []),
                    "acceptanceCriteria": story.get("acceptanceCriteria", []),
                    "dependsOn": story.get("dependsOn", []),
                }
                for story in phase.get("stories", [])
            ],
        })
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(compact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "synced", "source": str(source), "out": str(out), "version": compact["version"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
