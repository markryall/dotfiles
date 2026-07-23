#!/usr/bin/env python3
"""Generate an HTML usage report for fish functions vs. how often they're
actually typed, so high-frequency functions with long names surface as
candidates for a short alias. Reads ~/.local/share/fish/fish_history and
~/.config/fish/functions, writes the report to the path given as argv[1].
"""
import html
import json
import os
import re
import sys
from datetime import datetime, timezone

HISTORY_FILE = os.path.expanduser("~/.local/share/fish/fish_history")
FUNCTIONS_DIR = os.path.expanduser("~/.config/fish/functions")
CANDIDATE_MIN_LEN = 3
CANDIDATE_MIN_COUNT = 10
CHART_ROWS = 20


def load_counts():
    counts = {}
    when_values = []
    if not os.path.isfile(HISTORY_FILE):
        return counts, when_values
    cmd_re = re.compile(r"^- cmd:\s?(.*)$")
    when_re = re.compile(r"^\s+when:\s?(\d+)$")
    with open(HISTORY_FILE, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = cmd_re.match(line)
            if m:
                cmd = m.group(1).strip()
                if not cmd:
                    continue
                first = cmd.split()[0] if cmd.split() else ""
                if first:
                    counts[first] = counts.get(first, 0) + 1
                continue
            m = when_re.match(line)
            if m:
                when_values.append(int(m.group(1)))
    return counts, when_values


def load_function_names():
    names = []
    if not os.path.isdir(FUNCTIONS_DIR):
        return names
    for entry in os.listdir(FUNCTIONS_DIR):
        if entry.endswith(".fish"):
            names.append(entry[: -len(".fish")])
    return sorted(names)


def main():
    out_path = sys.argv[1]
    counts, when_values = load_counts()
    names = load_function_names()

    rows = []
    for name in names:
        c = counts.get(name, 0)
        candidate = len(name) >= CANDIDATE_MIN_LEN and c >= CANDIDATE_MIN_COUNT
        rows.append({"name": name, "count": c, "len": len(name), "candidate": candidate})

    rows.sort(key=lambda r: (-r["count"], r["name"]))

    chart_rows = [r for r in rows if r["count"] > 0][:CHART_ROWS]
    tail_rows = [r for r in rows if r not in chart_rows]

    if when_values:
        start = datetime.fromtimestamp(min(when_values), tz=timezone.utc).strftime("%Y-%m-%d")
        end = datetime.fromtimestamp(max(when_values), tz=timezone.utc).strftime("%Y-%m-%d")
        span = f"{start} → {end}"
    else:
        span = "no history found"

    total_invocations = sum(r["count"] for r in rows)
    candidates = [r for r in rows if r["candidate"]]

    data = {
        "chart": chart_rows,
        "tail": tail_rows,
        "span": span,
        "totalInvocations": total_invocations,
        "candidateMinLen": CANDIDATE_MIN_LEN,
        "candidateMinCount": CANDIDATE_MIN_COUNT,
    }

    html_out = TEMPLATE.replace("__DATA__", json.dumps(data))
    html_out = html_out.replace("__CANDIDATE_COUNT__", str(len(candidates)))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_out)


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fish function usage</title>
<style>
  :root {
    color-scheme: light;
    --surface-1:      #fcfcfb;
    --page-plane:     #f9f9f7;
    --text-primary:   #0b0b0b;
    --text-secondary: #52514e;
    --text-muted:      #898781;
    --gridline:       #e1e0d9;
    --baseline:       #c3c2b7;
    --series-1:       #2a78d6;
    --series-1-wash:  rgba(42, 120, 214, 0.12);
    --border:         rgba(11, 11, 11, 0.10);
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      color-scheme: dark;
      --surface-1:      #1a1a19;
      --page-plane:     #0d0d0d;
      --text-primary:   #ffffff;
      --text-secondary: #c3c2b7;
      --text-muted:      #898781;
      --gridline:       #2c2c2a;
      --baseline:       #383835;
      --series-1:       #3987e5;
      --series-1-wash:  rgba(57, 135, 229, 0.16);
      --border:         rgba(255, 255, 255, 0.10);
    }
  }
  :root[data-theme="dark"] {
    color-scheme: dark;
    --surface-1:      #1a1a19;
    --page-plane:     #0d0d0d;
    --text-primary:   #ffffff;
    --text-secondary: #c3c2b7;
    --text-muted:      #898781;
    --gridline:       #2c2c2a;
    --baseline:       #383835;
    --series-1:       #3987e5;
    --series-1-wash:  rgba(57, 135, 229, 0.16);
    --border:         rgba(255, 255, 255, 0.10);
  }

  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    background: var(--page-plane);
    color: var(--text-primary);
  }
  .viz-root {
    max-width: 880px;
    margin: 0 auto;
    padding: 40px 24px 64px;
  }
  header h1 {
    font-size: 22px;
    margin: 0 0 4px;
  }
  header p {
    margin: 0 0 28px;
    color: var(--text-secondary);
    font-size: 14px;
  }
  .stats {
    display: flex;
    gap: 12px;
    margin-bottom: 32px;
    flex-wrap: wrap;
  }
  .stat-tile {
    background: var(--surface-1);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px 18px;
    min-width: 140px;
  }
  .stat-tile .label {
    font-size: 12px;
    color: var(--text-secondary);
    margin-bottom: 4px;
  }
  .stat-tile .value {
    font-size: 24px;
    font-weight: 600;
  }
  .card {
    background: var(--surface-1);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px 24px 8px;
    margin-bottom: 24px;
    overflow-x: auto;
  }
  .card h2 {
    font-size: 15px;
    margin: 0 0 4px;
  }
  .card .sub {
    font-size: 12px;
    color: var(--text-secondary);
    margin: 0 0 20px;
  }
  .note {
    display: flex;
    gap: 10px;
    align-items: flex-start;
    background: var(--surface-1);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 24px;
    font-size: 12px;
    color: var(--text-secondary);
    line-height: 1.5;
  }
  .note .icon {
    color: var(--text-muted);
    flex-shrink: 0;
  }
  .note code {
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
    background: var(--series-1-wash);
    color: var(--text-primary);
    padding: 1px 4px;
    border-radius: 4px;
    font-size: 11px;
  }
  .chart {
    position: relative;
    min-width: 560px;
  }
  .gridlines {
    position: absolute;
    inset: 0;
    pointer-events: none;
  }
  .gridlines .line {
    position: absolute;
    top: 0;
    bottom: 22px;
    width: 1px;
    background: var(--gridline);
  }
  .gridlines .tick {
    position: absolute;
    bottom: 0;
    font-size: 11px;
    color: var(--text-muted);
    transform: translateX(-50%);
    font-variant-numeric: tabular-nums;
  }
  .row {
    display: grid;
    grid-template-columns: 140px 1fr;
    align-items: center;
    gap: 12px;
    padding: 5px 0;
    border-radius: 6px;
  }
  .row:hover {
    background: var(--series-1-wash);
  }
  .row .name {
    font-size: 13px;
    text-align: right;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: var(--text-primary);
  }
  .row .name .badge {
    display: inline-block;
    margin-left: 6px;
    padding: 1px 6px;
    border-radius: 999px;
    background: var(--series-1-wash);
    color: var(--series-1);
    font-size: 10px;
    font-weight: 600;
    vertical-align: middle;
  }
  .row .bar-wrap {
    position: relative;
    height: 24px;
  }
  .row .bar {
    position: absolute;
    left: 0;
    top: 0;
    height: 20px;
    background: var(--series-1);
    border-radius: 0 4px 4px 0;
    min-width: 2px;
  }
  .row .value {
    position: absolute;
    top: 0;
    height: 20px;
    display: flex;
    align-items: center;
    padding-left: 6px;
    font-size: 12px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    color: var(--text-primary);
    white-space: nowrap;
  }
  .baseline {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 22px;
    width: 1px;
    background: var(--baseline);
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }
  th {
    text-align: left;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--text-muted);
    font-weight: 600;
    padding: 8px 8px;
    border-bottom: 1px solid var(--gridline);
  }
  td {
    padding: 6px 8px;
    border-bottom: 1px solid var(--gridline);
    color: var(--text-secondary);
  }
  td.name-cell { color: var(--text-primary); }
  td.num {
    text-align: right;
    font-variant-numeric: tabular-nums;
    color: var(--text-primary);
  }
  .tooltip {
    position: fixed;
    pointer-events: none;
    background: var(--text-primary);
    color: var(--surface-1);
    font-size: 12px;
    padding: 6px 10px;
    border-radius: 6px;
    opacity: 0;
    transform: translate(-50%, -100%);
    transition: opacity 0.08s ease;
    z-index: 10;
    white-space: nowrap;
  }
  .tooltip strong { font-weight: 700; }
  footer {
    font-size: 12px;
    color: var(--text-muted);
  }
</style>
</head>
<body>
<div class="viz-root">
  <header>
    <h1>Fish function usage</h1>
    <p id="subtitle"></p>
  </header>

  <div class="note">
    <span class="icon">&#9432;</span>
    <span>fish's history file collapses an exact repeat down to one entry (it just
    bumps the timestamp), so anything you run identically every time — like
    <code>a</code> or <code>e</code> with no arguments — is undercounted here.
    Commands typically run with varying arguments (<code>s &lt;file&gt;</code>) come
    much closer to a true count. Treat these numbers as a floor, not an exact
    tally.</span>
  </div>

  <div class="stats" id="stats"></div>

  <div class="card">
    <h2>Most-used functions</h2>
    <p class="sub">Top 20 by invocation count, from fish_history. Blue badge = long name (≥ 3 chars) called ≥ 10 times — a shortening candidate.</p>
    <div class="chart" id="chart"></div>
  </div>

  <div class="card">
    <h2>Everything else</h2>
    <p class="sub">Remaining functions, including ones never invoked directly in history (subcommands, sourced-only, etc).</p>
    <table id="tail-table">
      <thead><tr><th>Name</th><th style="text-align:right">Uses</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>

  <footer>Generated from fish_history — counts reflect distinct command lines typed, not raw invocation count (see note above).</footer>
</div>

<div class="tooltip" id="tooltip" role="tooltip"></div>

<script>
const data = __DATA__;

document.getElementById("subtitle").textContent =
  "History window " + data.span + " • " + data.totalInvocations.toLocaleString() + " tracked invocations";

const stats = document.getElementById("stats");
function statTile(label, value) {
  const tile = document.createElement("div");
  tile.className = "stat-tile";
  const l = document.createElement("div");
  l.className = "label";
  l.textContent = label;
  const v = document.createElement("div");
  v.className = "value";
  v.textContent = value;
  tile.appendChild(l);
  tile.appendChild(v);
  return tile;
}
const candidateCount = __CANDIDATE_COUNT__;
stats.appendChild(statTile("Functions tracked", data.chart.length + data.tail.length));
stats.appendChild(statTile("Total invocations", data.totalInvocations.toLocaleString()));
stats.appendChild(statTile("Shortening candidates", candidateCount));

const chartEl = document.getElementById("chart");
const tooltip = document.getElementById("tooltip");

const max = data.chart.length ? Math.max(...data.chart.map(r => r.count)) : 1;
const niceMax = Math.ceil(max / 50) * 50 || 1;
const ticks = [0, 0.25, 0.5, 0.75, 1].map(f => Math.round(niceMax * f));

const gridlines = document.createElement("div");
gridlines.className = "gridlines";
ticks.forEach(t => {
  const pct = (t / niceMax) * 100;
  const line = document.createElement("div");
  line.className = "line";
  line.style.left = pct + "%";
  gridlines.appendChild(line);
  const tick = document.createElement("div");
  tick.className = "tick";
  tick.style.left = pct + "%";
  tick.textContent = t.toLocaleString();
  gridlines.appendChild(tick);
});
chartEl.appendChild(gridlines);

const rowsWrap = document.createElement("div");
rowsWrap.style.marginLeft = "0";
rowsWrap.style.paddingBottom = "22px";
data.chart.forEach(r => {
  const row = document.createElement("div");
  row.className = "row";

  const nameEl = document.createElement("div");
  nameEl.className = "name";
  nameEl.textContent = r.name;
  if (r.candidate) {
    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = "shorten?";
    nameEl.appendChild(badge);
  }

  const barWrap = document.createElement("div");
  barWrap.className = "bar-wrap";
  const pct = (r.count / niceMax) * 100;
  const bar = document.createElement("div");
  bar.className = "bar";
  bar.style.width = "max(2px, " + pct + "%)";
  const value = document.createElement("div");
  value.className = "value";
  value.style.left = "max(2px, " + pct + "%)";
  value.textContent = r.count.toLocaleString();
  barWrap.appendChild(bar);
  barWrap.appendChild(value);

  row.appendChild(nameEl);
  row.appendChild(barWrap);

  row.addEventListener("pointermove", (e) => {
    tooltip.style.left = e.clientX + "px";
    tooltip.style.top = (e.clientY - 12) + "px";
    tooltip.style.opacity = "1";
    tooltip.textContent = "";
    const strong = document.createElement("strong");
    strong.textContent = r.count.toLocaleString();
    tooltip.appendChild(strong);
    tooltip.appendChild(document.createTextNode(" uses — " + r.name));
  });
  row.addEventListener("pointerleave", () => {
    tooltip.style.opacity = "0";
  });

  rowsWrap.appendChild(row);
});
chartEl.appendChild(rowsWrap);

const baseline = document.createElement("div");
baseline.className = "baseline";
chartEl.appendChild(baseline);

const tbody = document.querySelector("#tail-table tbody");
data.tail.forEach(r => {
  const tr = document.createElement("tr");
  const nameTd = document.createElement("td");
  nameTd.className = "name-cell";
  nameTd.textContent = r.name;
  const countTd = document.createElement("td");
  countTd.className = "num";
  countTd.textContent = r.count.toLocaleString();
  tr.appendChild(nameTd);
  tr.appendChild(countTd);
  tbody.appendChild(tr);
});
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
