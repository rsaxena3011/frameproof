#!/usr/bin/env python3
"""FrameProof CLI: run the deterministic coarse pass on a video file.

Usage: python3 frameproof.py <video> [--json]
Exit code: 0 PASS, 1 WARN, 2 FAIL, 3 error.
"""

import json
import sys

from src.checks import analyse


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__)
        return 3
    try:
        report = analyse(args[0])
    except RuntimeError as e:
        print(f"error: {e}")
        return 3
    if "--json" in argv:
        print(json.dumps(report, indent=2))
    else:
        print(
            f"{report['path']}: {report['frames']} frames @ {report['fps']} fps, "
            f"{report['duration_s']}s, {report['shots']} shot(s), "
            f"jitter={report['luminance_jitter']}"
        )
        for f in report["findings"]:
            print(
                f"  [{f['severity']:4}] {f['check']:14} "
                f"{f['start_s']:>7.2f}s-{f['end_s']:>7.2f}s  {f['detail']}"
            )
        print(f"verdict: {report['verdict']}")
    return {"PASS": 0, "WARN": 1, "FAIL": 2}[report["verdict"]]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
