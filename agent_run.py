#!/usr/bin/env python3
"""Run the FrameProof agent loop on a video.

Usage: python3 agent_run.py <video> [--reference <face_still>] [--json]
"""

import json
import sys

from src.agent import run_agent


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    ref = None
    if "--reference" in argv:
        ref = argv[argv.index("--reference") + 1]
        args = [a for a in args if a != ref]
    if len(args) != 1:
        print(__doc__)
        return 3
    result = run_agent(args[0], reference=ref)
    if "--json" in argv:
        print(json.dumps(result, indent=2))
    else:
        print(f"{result['path']}: coarse={result['coarse_verdict']} agent={result['verdict']}")
        for d in result["dispositions"]:
            print(f"  [{d['severity']:4}] {d['check']:14} {d.get('disposition', ''):10} {d['detail']}")
        print(f"trace: {len(result['trace'])} steps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
