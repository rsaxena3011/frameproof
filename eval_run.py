#!/usr/bin/env python3
"""Run the FrameProof agent over the labeled evaluation set.

Usage: python3 eval_run.py [--json]
Writes tests/eval/results.json and prints a per-clip table plus
verdict-level accuracy (overall and per class).
"""

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

from src.agent import run_agent

EVAL_DIR = Path(__file__).parent / "tests" / "eval"


def main() -> int:
    manifest = json.loads((EVAL_DIR / "manifest.json").read_text())
    rows, correct = [], 0
    per_class = defaultdict(lambda: [0, 0])
    for item in manifest:
        t0 = time.time()
        result = run_agent(str(EVAL_DIR / item["file"]))
        dt = time.time() - t0
        ok = result["verdict"] == item["expected_verdict"]
        correct += ok
        cls = item["file"].split("_")[0]
        per_class[cls][0] += ok
        per_class[cls][1] += 1
        rows.append({
            "file": item["file"],
            "expected": item["expected_verdict"],
            "got": result["verdict"],
            "ok": ok,
            "seconds": round(dt, 2),
            "confirmed": [d["check"] for d in result["dispositions"]
                          if d.get("disposition") == "confirmed"],
        })
        print(f"{'OK ' if ok else 'MISS'} {item['file']:20} "
              f"expected={item['expected_verdict']:10} got={result['verdict']:10} ({dt:.1f}s)")
    total = len(manifest)
    print(f"\nverdict accuracy: {correct}/{total} = {correct / total:.1%}")
    for cls, (c, n) in sorted(per_class.items()):
        print(f"  {cls:10} {c}/{n}")
    (EVAL_DIR / "results.json").write_text(json.dumps(
        {"accuracy": correct / total, "rows": rows}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
