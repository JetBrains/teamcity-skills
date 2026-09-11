#!/usr/bin/env python3
"""Render a TeamCity evaluation-run JSON report as a standalone HTML page.

    python3 evals/render_teamcity_eval_report.py \
      --input /tmp/teamcity-eval-runs.json --output /tmp/teamcity-eval-runs.html

The generated page contains no credentials, prompts, trajectories, or raw
build logs.  Re-run the collector followed by this renderer after new builds.
"""

import argparse
import html
import json
import pathlib


COLORS = {
    "passed": "#147d4b",
    "skill-output-failed": "#c8511b",
    "runner-runtime-failure": "#9b3a12",
    "agent-runtime-failure": "#9b3a12",
    "agent-permission-failure": "#9b3a12",
    "agent-timeout": "#9b3a12",
    "external-vcs-failure": "#9b3a12",
    "vcs-auth-failure": "#9b3a12",
    "teamcity-auth-failure": "#9b3a12",
    "false-green/no-result": "#a06b00",
    "failed-without-result": "#9b3a12",
    "running": "#2864b0",
    "queued": "#6e6e6e",
    "canceled": "#6e6e6e",
}


def esc(value):
    return html.escape(str(value or "-"))


def compact_duration(seconds):
    if seconds is None:
        return "-"
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes}m {seconds:02d}s" if minutes else f"{seconds}s"


def all_jobs(data):
    jobs = {}
    for pipeline in data.get("pipelines", []):
        for head in pipeline.get("runs", []):
            for job in head.get("jobs", []):
                jobs.setdefault(job["id"], (pipeline["id"], head, job))
    return sorted(jobs.values(), key=lambda item: item[2]["id"], reverse=True)


def link(url, label):
    return f'<a href="{esc(url)}" target="_blank" rel="noreferrer">{esc(label)}</a>' if url else esc(label)


def arm_cell(case, arm):
    if case.get("executionModel") != "paired-arms":
        return '<span class="muted">not arm-based</span>'
    observation = (case.get("arms") or {}).get(arm)
    if not observation:
        return '<span class="muted">not run</span>'
    category = observation.get("classification", "unknown")
    color = COLORS.get(category, "#6e6e6e")
    history = observation.get("history") or {}
    sample_size = history.get("sampleSize", 0)
    pass_count = history.get("passCount", 0)
    pass_rate = history.get("passRate")
    target = history.get("targetMinSamples", 3)
    history_html = ""
    if sample_size:
        rate = f"{pass_rate * 100:.0f}%" if pass_rate is not None else "-"
        readiness = "measured" if sample_size >= target else f"need {target - sample_size} more"
        history_html = (
            f'<div class="detail">same-revision pass rate: '
            f'{pass_count}/{sample_size} ({rate}); {readiness}</div>'
        )
    return (
        f'<span class="status" style="color:{color}">{esc(category)}</span><br>'
        f'{link(observation.get("url"), "run " + str(observation.get("runId")))}'
        f'<div class="detail">{esc(observation.get("detail"))}</div>'
        f'{history_html}'
    )


def usage_cell(run):
    usage = ((run.get("result") or {}).get("agentUsage") or {})
    if not usage:
        return '<span class="muted">not reported</span>'
    tokens = []
    if "inputTokens" in usage:
        tokens.append(f'{usage["inputTokens"]:,.0f} in')
    if "outputTokens" in usage:
        tokens.append(f'{usage["outputTokens"]:,.0f} out')
    if "cacheReadTokens" in usage:
        tokens.append(f'{usage["cacheReadTokens"]:,.0f} cache read')
    if "cacheWriteTokens" in usage:
        tokens.append(f'{usage["cacheWriteTokens"]:,.0f} cache write')
    cost = (
        f'<div class="detail">${usage["totalCostUsd"]:,.4f} provider-reported</div>'
        if "totalCostUsd" in usage else
        '<div class="detail">provider cost not reported</div>'
    )
    return esc(" / ".join(tokens) or "token counts not reported") + cost


def render(data):
    summary = data.get("summary", {})
    counts = summary.get("classifications", {})
    jobs = all_jobs(data)
    denominator = max(1, summary.get("jobRunsObserved", 0))
    bars = "".join(
        f'<div class="bar" style="width:{count / denominator * 100:.1f}%;background:{COLORS.get(category, "#6e6e6e")}" '
        f'title="{esc(category)}: {count}"></div>'
        for category, count in sorted(counts.items())
    ) or '<div class="bar" style="width:100%;background:#d6d6d6"></div>'

    matrix_rows = []
    for case in data.get("cases", []):
        coverage = " / ".join(case.get("assertions") or [])
        if case.get("targets"):
            coverage += (" / " if coverage else "") + "targets: " + " / ".join(case["targets"])
        matrix_rows.append(
            '<tr>'
            f'<td><code>{esc(case["id"])}</code><div class="detail">{esc(case["scope"])}</div></td>'
            f'<td>{esc(case["kind"])}<br><span class="gate">{esc(case["gate"])}</span></td>'
            f'<td>{esc(coverage)}</td>'
            f'<td>{arm_cell(case, "skill")}</td>'
            f'<td>{arm_cell(case, "baseline")}</td>'
            '</tr>'
        )

    rows = []
    for pipeline, head, job in jobs[:12]:
        category = job["classification"]
        result = job.get("result") or {}
        case = result.get("caseId") or "-"
        rows.append(
            '<tr>'
            f'<td>{link(job.get("url"), str(job["id"]))}</td>'
            f'<td><code>{esc(case)}</code></td>'
            f'<td>{esc(result.get("arm"))}</td>'
            f'<td><span class="status" style="color:{COLORS.get(category, "#6e6e6e")}">{esc(category)}</span></td>'
            f'<td>{esc(job.get("classificationDetail"))}</td>'
            f'<td>{esc(job.get("agent"))}</td>'
            f'<td>{compact_duration(job.get("durationSeconds"))}</td>'
            f'<td>{usage_cell(job)}</td>'
            '</tr>'
        )

    legend = "".join(
        f'<span><i style="background:{COLORS.get(category, "#6e6e6e")}"></i>{esc(category)} {count}</span>'
        for category, count in sorted(counts.items())
    ) or "<span>No job runs collected</span>"
    recommendations = "".join(f"<li>{esc(item)}</li>" for item in data.get("recommendations", []))
    usage = summary.get("agentUsage") or {}
    if usage.get("runsMeasured"):
        measured = usage.get("fieldsMeasured") or {}
        cost = (
            f' / ${usage["totalCostUsd"]:,.4f} provider-reported cost'
            if measured.get("totalCostUsd") else
            ' / provider cost unavailable'
        )
        usage_line = (
            f'Measured agent usage across {usage["runsMeasured"]} run(s): '
            f'{usage.get("inputTokens", 0):,.0f} input / '
            f'{usage.get("outputTokens", 0):,.0f} output / '
            f'{usage.get("cacheReadTokens", 0):,.0f} cache read / '
            f'{usage.get("cacheWriteTokens", 0):,.0f} cache write'
            f'{cost}'
        )
    else:
        usage_line = "Agent token/cost telemetry has not been reported by collected runs yet."
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>TeamCity evaluation runs</title><style>
body{{margin:0;background:#f6f7f8;color:#1d252c;font:14px/1.45 Inter,system-ui,sans-serif}}main{{max-width:1200px;margin:auto;padding:32px 24px 60px}}h1{{font-size:28px;margin:0}}h2{{font-size:16px;margin:30px 0 12px}}.meta{{color:#64717c;margin:4px 0 22px}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}.section{{background:#fff;border:1px solid #dce1e5;border-radius:10px;padding:16px}}.value{{font-size:26px;font-weight:700}}.label,.muted,.detail,.gate{{color:#64717c}}.detail{{font-size:11px;margin-top:4px}}.barline{{display:flex;overflow:hidden;height:12px;border-radius:8px;background:#e9ecef;margin-top:16px}}.bar{{min-width:4px}}.legend{{display:flex;gap:14px;flex-wrap:wrap;margin:9px 0;color:#52606c;font-size:12px}}.legend i{{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px}}.visually-hidden{{position:absolute;clip-path:inset(50%);overflow:hidden;width:1px;height:1px;white-space:nowrap}}code{{font-size:12px;overflow-wrap:anywhere}}table{{border-collapse:collapse;width:100%;min-width:900px;font-size:12px}}th{{text-align:left;color:#64717c;font-weight:600}}td,th{{padding:9px 8px;border-bottom:1px solid #e5e8eb;vertical-align:top}}a{{color:#2864b0;text-decoration:none}}.status{{font-weight:650}}ol{{margin:0;padding-left:22px}}li+li{{margin-top:8px}}@media(max-width:700px){{main{{padding:20px 14px}}.metrics{{grid-template-columns:1fr 1fr}}.table-wrap{{overflow:auto}}}}@media(max-width:420px){{.metrics{{grid-template-columns:1fr 1fr}}}}
</style></head><body><main>
<h1>TeamCity evaluation runs</h1><div class="meta">{esc(data.get("server"))} / collected {esc(data.get("generatedAt"))}</div>
<section class="section"><div class="metrics"><div><div class="value">{summary.get("caseContracts", 0)}</div><div class="label">case contracts</div></div><div><div class="value">{summary.get("pairedCaseContracts", 0)}</div><div class="label">paired agent cases</div></div><div><div class="value">{summary.get("distinctArmsObserved", 0)}/{summary.get("expectedArmSlots", 0)}</div><div class="label">case arms observed</div></div><div><div class="value">{counts.get("running", 0) + counts.get("queued", 0)}</div><div class="label">active eval jobs</div></div></div><div class="barline">{bars}</div><div class="legend">{legend}</div><div class="detail">{esc(usage_line)}</div></section>
<h2>Case x arm matrix</h2><section class="section table-wrap"><table><caption class="visually-hidden">Latest skill and baseline result for every evaluation contract</caption><thead><tr><th scope="col">Case</th><th scope="col">Contract</th><th scope="col">What is tested</th><th scope="col">Skill</th><th scope="col">Baseline</th></tr></thead><tbody>{"".join(matrix_rows)}</tbody></table></section>
<h2>Recent execution ledger</h2><section class="section table-wrap"><table><caption class="visually-hidden">Recent unique evaluator jobs</caption><thead><tr><th scope="col">Job</th><th scope="col">Case</th><th scope="col">Arm</th><th scope="col">Verdict</th><th scope="col">Reason</th><th scope="col">Agent</th><th scope="col">Duration</th><th scope="col">Agent usage</th></tr></thead><tbody>{"".join(rows)}</tbody></table></section>
<h2>Next useful evaluations</h2><section class="section"><ol>{recommendations}</ol></section>
</main></body></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    data = json.loads(args.input.read_text())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(data))
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
