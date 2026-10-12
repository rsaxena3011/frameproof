#!/usr/bin/env python3
"""FrameProof web UI: upload a clip, run the agent loop, get a verdict
with evidence, and record a human approve/reject decision.

Run: python3 app.py  (serves on http://127.0.0.1:5050)
Jobs are stored under jobs/<job_id>/ with the agent report and the
human decision log (the audit trail the agent loop answers to).
"""

import json
import time
import uuid
from pathlib import Path

from flask import Flask, abort, redirect, render_template_string, request, url_for
from werkzeug.utils import secure_filename

from src.agent import run_agent
from src.identity import drift_scan
from src.props import persistence_scan

BASE = Path(__file__).resolve().parent
JOBS = BASE / "jobs"
JOBS.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 512 * 1024 * 1024

PAGE = """
<!doctype html>
<title>FrameProof</title>
<style>
 body{font-family:system-ui,sans-serif;max-width:860px;margin:2rem auto;padding:0 1rem}
 .verdict{font-size:1.6rem;font-weight:700}
 .PASS{color:#137333}.ESCALATE{color:#b3261e}.REGEN{color:#b06000}.AUTO{color:#0b57d0}
 table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:.35rem .5rem;text-align:left}
 pre{background:#f4f4f4;padding:.7rem;overflow:auto;max-height:300px}
 button{padding:.5rem 1.2rem;font-size:1rem;margin-right:.5rem}
</style>
<h1>FrameProof</h1>
<p>Agentic QC for AI-generated video. Upload a clip; the agent inspects it,
re-inspects every suspect span at full resolution, and shows its evidence.
A human always has the final word.</p>
<form method="post" action="/run" enctype="multipart/form-data">
 <p>Video (required): <input type="file" name="video" required></p>
 <p>Character reference still (optional, enables identity-drift):
    <input type="file" name="reference"></p>
 <p>Prop reference crop (optional, enables prop persistence):
    <input type="file" name="prop"></p>
 <p><button type="submit">Run inspection</button></p>
</form>
{% if jobs %}
<h2>Past inspections</h2>
<ul>{% for j in jobs %}<li><a href="/job/{{ j }}">{{ j }}</a></li>{% endfor %}</ul>
{% endif %}
"""

JOB_PAGE = """
<!doctype html>
<title>FrameProof job {{ job_id }}</title>
<style>
 body{font-family:system-ui,sans-serif;max-width:860px;margin:2rem auto;padding:0 1rem}
 .verdict{font-size:1.6rem;font-weight:700}
 .PASS{color:#137333}.ESCALATE{color:#b3261e}.REGEN{color:#b06000}.AUTO{color:#0b57d0}
 table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:.35rem .5rem;text-align:left}
 pre{background:#f4f4f4;padding:.7rem;overflow:auto;max-height:300px}
 button{padding:.5rem 1.2rem;font-size:1rem;margin-right:.5rem}
</style>
<p><a href="/">&larr; FrameProof</a></p>
<h1>Job {{ job_id }}</h1>
<p class="verdict {{ cls }}">Verdict: {{ report.verdict }}</p>
<p>Coarse pass said {{ report.coarse_verdict }}; the clip has {{ report.shots }} shot(s).</p>
{% if report.autofix %}
<p><strong>Auto-fix applied:</strong> {{ report.autofix.output }}
 (jitter {{ report.autofix.jitter_before }} &rarr; {{ report.autofix.jitter_after }})</p>
{% endif %}
{% if extras.identity %}
<p><strong>Identity drift:</strong> {{ extras.identity.verdict }}
 ({{ extras.identity.drift_samples|length }} drift samples)</p>
{% endif %}
{% if extras.prop %}
<p><strong>Prop persistence:</strong> {{ extras.prop.verdict }}
 (missing in {{ extras.prop.missing_samples|length }} samples)</p>
{% endif %}
<h2>Findings</h2>
<table><tr><th>Check</th><th>Severity</th><th>Span (s)</th><th>Disposition</th><th>Evidence</th></tr>
{% for d in report.dispositions %}
<tr><td>{{ d.check }}</td><td>{{ d.severity }}</td>
<td>{{ d.start_s }}-{{ d.end_s }}</td><td>{{ d.disposition or '' }}</td>
<td>{{ d.detail }}{% if d.dense_evidence %} | dense: {{ d.dense_evidence }}{% endif %}</td></tr>
{% endfor %}
</table>
<h2>Agent trace</h2>
<pre>{% for s in report.trace %}[{{ s.stage }}] {{ s.msg }}
{% endfor %}</pre>
<h2>Human decision</h2>
{% if decision %}
<p>Recorded: <strong>{{ decision.decision }}</strong> at {{ decision.at }}
{% if decision.note %} &mdash; {{ decision.note }}{% endif %}</p>
{% else %}
<form method="post" action="/job/{{ job_id }}/decide">
 <input type="text" name="note" placeholder="Optional note" size="40">
 <button type="submit" name="decision" value="APPROVED">Approve release</button>
 <button type="submit" name="decision" value="REJECTED">Reject</button>
</form>
{% endif %}
"""


def _save_upload(f, dest: Path) -> str | None:
    if f and f.filename:
        name = secure_filename(f.filename)
        f.save(dest / name)
        return name
    return None


@app.route("/")
def index():
    jobs = sorted(p.name for p in JOBS.iterdir() if p.is_dir())
    return render_template_string(PAGE, jobs=jobs)


@app.route("/run", methods=["POST"])
def run():
    job_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    job_dir = JOBS / job_id
    job_dir.mkdir(parents=True)
    video = _save_upload(request.files.get("video"), job_dir)
    if not video:
        abort(400, "video is required")
    ref = _save_upload(request.files.get("reference"), job_dir)
    prop = _save_upload(request.files.get("prop"), job_dir)
    video_path = str(job_dir / video)
    report = run_agent(video_path)
    extras = {}
    if ref:
        extras["identity"] = drift_scan(video_path, str(job_dir / ref))
    if prop:
        extras["prop"] = persistence_scan(video_path, str(job_dir / prop))
    (job_dir / "report.json").write_text(
        json.dumps({"report": report, "extras": extras}, indent=2)
    )
    return redirect(url_for("job", job_id=job_id), code=303)


@app.route("/job/<job_id>")
def job(job_id):
    job_dir = JOBS / secure_filename(job_id)
    data_file = job_dir / "report.json"
    if not data_file.exists():
        abort(404)
    data = json.loads(data_file.read_text())
    decision = None
    dec_file = job_dir / "decision.json"
    if dec_file.exists():
        decision = json.loads(dec_file.read_text())
    verdict = data["report"]["verdict"]
    cls = {"PASS": "PASS", "ESCALATE": "ESCALATE",
           "REGEN NOTE": "REGEN", "AUTO-FIX": "AUTO"}.get(verdict, "")
    return render_template_string(
        JOB_PAGE, job_id=job_id, report=data["report"],
        extras=data["extras"], decision=decision, cls=cls,
    )


@app.route("/job/<job_id>/decide", methods=["POST"])
def decide(job_id):
    job_dir = JOBS / secure_filename(job_id)
    if not (job_dir / "report.json").exists():
        abort(404)
    decision = {
        "decision": request.form.get("decision", ""),
        "note": request.form.get("note", ""),
        "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    (job_dir / "decision.json").write_text(json.dumps(decision, indent=2))
    return redirect(url_for("job", job_id=job_id), code=303)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050)
