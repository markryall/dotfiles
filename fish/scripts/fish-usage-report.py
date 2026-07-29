#!/usr/bin/env python3
"""Generate an HTML usage report for fish functions vs. how often they're
actually typed, so high-frequency functions with long names surface as
candidates for a short alias. Prefers atuin's history.db (every invocation is
its own row) when present, falling back to fish's own fish_history (which
collapses exact repeats to one entry, undercounting no-arg commands). Reads
~/.config/fish/functions for the function list; writes the report to the path
given as argv[1].

Abbreviations are expanded on the command line before the command runs, so the
shorthand never reaches history — only the expansion does. Counting the first
word alone would therefore lose an abbreviated command entirely (`bundle exec
rspec` isn't a function) or dump unrelated ones into a shared bucket (every
`jj` subcommand). So commands are matched against the *longest* token prefix
of a known target, where a target is either a function name (one token) or an
abbreviation's expansion (several) — function counting is just the one-token
case of the same rule.

Since the trigger is unrecoverable from history, every occurrence of an
expansion is assumed to have been typed via its abbreviation, which is what
lets the report total up the keystrokes they've saved.

Optional settings live in ~/.config/fish/fish-usage-report.json (override with
FISH_USAGE_REPORT_CONFIG); every key is optional and the report runs fine
without the file at all:

    {
      "candidateMinLen": 3,       // a name this long...
      "candidateMinCount": 10,    // ...called this often is worth shortening
      "chartRows": 20,
      "assumedTriggerLen": 2,     // length to cost an unwritten abbreviation at
      "replaced": {               // abbreviations that replaced a function
        "d": ["desc"]             // whose name they don't share
      }
    }
"""
import json
import os
import re
import shlex
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone

HISTORY_FILE = os.path.expanduser("~/.local/share/fish/fish_history")
ATUIN_DB = os.path.expanduser("~/.local/share/atuin/history.db")
FUNCTIONS_DIR = os.path.expanduser("~/.config/fish/functions")
CONFIG_FILE = os.environ.get(
    "FISH_USAGE_REPORT_CONFIG",
    os.path.expanduser("~/.config/fish/fish-usage-report.json"),
)

DEFAULTS = {
    # A name this long, called this often, is worth shortening.
    "candidateMinLen": 3,
    "candidateMinCount": 10,
    "chartRows": 20,
    # What an as-yet-unwritten abbreviation would plausibly be, for costing out
    # the keystrokes a candidate is still leaving on the table.
    "assumedTriggerLen": 2,
    # trigger -> names it used to be called, for abbreviations that replaced a
    # function of a different name. Purely personal history, hence config.
    "replaced": {},
}


def load_commands_atuin():
    """Every command run, tokenised, from atuin's history.db, which (unlike
    fish's own history) logs every execution as its own row instead of
    collapsing exact repeats. Returns None if atuin has no usable data, so
    callers can fall back to fish_history.
    """
    if not os.path.isfile(ATUIN_DB):
        return None
    try:
        uri = f"file:{ATUIN_DB}?mode=ro"
        con = sqlite3.connect(uri, uri=True)
        try:
            cur = con.execute(
                "select command, timestamp from history where deleted_at is null"
            )
            rows = cur.fetchall()
        finally:
            con.close()
    except sqlite3.Error:
        return None

    if not rows:
        return None

    commands = []
    when_values = []
    for command, timestamp_ns in rows:
        tokens = (command or "").split()
        if tokens:
            commands.append(tokens)
        when_values.append(timestamp_ns / 1_000_000_000)
    return commands, when_values


def load_commands_fish_history():
    commands = []
    when_values = []
    if not os.path.isfile(HISTORY_FILE):
        return commands, when_values
    cmd_re = re.compile(r"^- cmd:\s?(.*)$")
    when_re = re.compile(r"^\s+when:\s?(\d+)$")
    with open(HISTORY_FILE, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = cmd_re.match(line)
            if m:
                tokens = m.group(1).split()
                if tokens:
                    commands.append(tokens)
                continue
            m = when_re.match(line)
            if m:
                when_values.append(int(m.group(1)))
    return commands, when_values


def load_commands():
    atuin = load_commands_atuin()
    if atuin is not None:
        commands, when_values = atuin
        return commands, when_values, "atuin"
    commands, when_values = load_commands_fish_history()
    return commands, when_values, "fish_history"


def load_abbrs():
    """Map expansion -> {"triggers": [...], "prefix": (tokens,)}.

    `abbr --show` emits re-runnable fish, one definition per line, as
    `abbr -a [flags] -- NAME [EXPANSION]`. Keyed on the whole expansion, since
    that is what history records; callers that only care which function is
    fronted use abbrs_by_first_token below.

    `prefix` is the leading tokens that will actually appear in history. For a
    --set-cursor abbreviation these stop short of the placeholder, and drop the
    token containing it: `make pair names=%` can only be relied on to produce
    `make pair`, since `names=` is completed with text we never see.
    """
    try:
        proc = subprocess.run(
            ["fish", "-c", "abbr --show"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    if proc.returncode != 0:
        return {}

    abbrs = {}
    for line in proc.stdout.splitlines():
        try:
            tokens = shlex.split(line)
        except ValueError:
            continue
        if not tokens or tokens[0] != "abbr" or "--" not in tokens:
            continue
        sep = tokens.index("--")
        flags, rest = tokens[:sep], tokens[sep + 1:]
        # --command abbrs expand a subcommand (git ci), not a top-level
        # command, so they never shorten one of our functions.
        if "--command" in flags:
            continue
        # --function abbrs compute their expansion at runtime; nothing to key on.
        if len(rest) < 2:
            continue
        name, raw = rest[0], rest[1]
        marker = cursor_marker(flags)
        prefix = tuple(raw.split(marker)[0].split()) if marker else tuple(raw.split())
        if marker and not raw.split(marker)[0].endswith((" ", "\t")):
            prefix = prefix[:-1]
        expansion = " ".join(raw.replace(marker, "").split()) if marker else " ".join(raw.split())
        if not expansion or not prefix:
            continue
        # With --regex the trigger is the pattern, not the name, so show that.
        if "--regex" in flags and flags.index("--regex") + 1 < len(flags):
            name = flags[flags.index("--regex") + 1]
        entry = abbrs.setdefault(expansion, {"triggers": set(), "prefix": prefix})
        entry["triggers"].add(name)
    return {
        expansion: {"triggers": sorted(e["triggers"]), "prefix": e["prefix"]}
        for expansion, e in abbrs.items()
    }


def cursor_marker(flags):
    """The --set-cursor placeholder, which defaults to % when given bare.
    Empty when the abbreviation doesn't use one.
    """
    for flag in flags:
        if flag.startswith("--set-cursor="):
            return flag.split("=", 1)[1]
    return "%" if "--set-cursor" in flags else ""


def abbrs_by_first_token(abbrs):
    """Expansions regrouped by the command they start with, so a function row
    can show the abbreviations that front it.
    """
    by_token = {}
    for entry in abbrs.values():
        by_token.setdefault(entry["prefix"][0], set()).update(entry["triggers"])
    return {token: sorted(names) for token, names in by_token.items()}


def load_config():
    """Optional JSON settings, so the script itself stays free of any one
    person's shell history. Absent or unreadable config just means defaults.
    """
    config = dict(DEFAULTS)
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            config.update(json.load(f))
    except (OSError, ValueError):
        return config
    return config


def load_function_names():
    names = []
    if not os.path.isdir(FUNCTIONS_DIR):
        return names
    for entry in os.listdir(FUNCTIONS_DIR):
        if entry.endswith(".fish"):
            names.append(entry[: -len(".fish")])
    return sorted(names)


def build_rows(function_names, abbrs, expansions, replaced):
    """One row per thing worth counting, plus the token prefixes that credit it.

    A function is a one-token target. An abbreviation whose expansion doesn't
    start with a function name has no row to attach to, so it gets its own —
    otherwise `bundle exec rspec` would vanish and every `jj` subcommand would
    pile into one bucket. Such a row also claims its bare trigger, which only
    appears in history from the shorthand's previous life as a function, so the
    count survives the conversion instead of resetting to zero — along with any
    differently-named predecessors declared in the `replaced` config, which the
    history has no way of connecting on its own.
    """
    rows = []
    lookup = {}

    for name in function_names:
        row = {
            "name": name,
            "count": 0,
            "len": len(name),
            "abbrs": abbrs.get(name, []),
            "kind": "function",
        }
        rows.append(row)
        lookup[(name,)] = row

    for expansion, entry in sorted(expansions.items()):
        prefix = entry["prefix"]
        if prefix in lookup:
            continue
        row = {
            "name": expansion,
            "count": 0,
            "len": len(expansion),
            "abbrs": entry["triggers"],
            "kind": "abbr",
        }
        rows.append(row)
        lookup[prefix] = row
        for trigger in entry["triggers"]:
            lookup.setdefault((trigger,), row)
            for old in replaced.get(trigger, []):
                lookup.setdefault((old,), row)

    return rows, lookup


def tally(commands, lookup):
    """Credit each command to the longest target that prefixes it, so `jj log
    -r x` counts toward `jj log` rather than a bare `jj`, and every command
    lands on at most one row.
    """
    longest = max((len(k) for k in lookup), default=0)
    for tokens in commands:
        for size in range(min(longest, len(tokens)), 0, -1):
            row = lookup.get(tuple(tokens[:size]))
            if row is not None:
                row["count"] += 1
                break


def main():
    out_path = sys.argv[1]
    config = load_config()
    commands, when_values, source = load_commands()
    names = load_function_names()
    abbrs = load_abbrs()

    rows, lookup = build_rows(
        names,
        abbrs_by_first_token(abbrs),
        abbrs,
        config["replaced"],
    )
    tally(commands, lookup)

    for row in rows:
        row["candidate"] = (
            row["kind"] == "function"
            and row["len"] >= config["candidateMinLen"]
            and row["count"] >= config["candidateMinCount"]
            and not row["abbrs"]
        )
        # Every occurrence is assumed to have been typed via the shortest
        # trigger — the abbreviation is unrecoverable from history, and the
        # point is to celebrate the saving, not to audit it.
        trigger = min(row["abbrs"], key=len) if row["abbrs"] else None
        row["saved"] = row["count"] * max(0, row["len"] - len(trigger)) if trigger else 0
        row["potential"] = (
            row["count"] * max(0, row["len"] - config["assumedTriggerLen"])
            if row["candidate"]
            else 0
        )

    rows.sort(key=lambda r: (-r["count"], r["name"]))

    chart_rows = [r for r in rows if r["count"] > 0][:config["chartRows"]]
    tail_rows = [r for r in rows if r not in chart_rows]

    if when_values:
        start = datetime.fromtimestamp(min(when_values), tz=timezone.utc).strftime("%Y-%m-%d")
        end = datetime.fromtimestamp(max(when_values), tz=timezone.utc).strftime("%Y-%m-%d")
        span = f"{start} → {end}"
    else:
        span = "no history found"

    total_invocations = sum(r["count"] for r in rows)
    candidates = [r for r in rows if r["candidate"]]
    abbreviated = [r for r in rows if r["abbrs"]]

    data = {
        "chart": chart_rows,
        "tail": tail_rows,
        "span": span,
        "source": source,
        "totalInvocations": total_invocations,
        "candidateMinLen": config["candidateMinLen"],
        "candidateMinCount": config["candidateMinCount"],
        "candidateCount": len(candidates),
        "abbreviatedCount": len(abbreviated),
        "keystrokesSaved": sum(r["saved"] for r in rows),
        "keystrokesOnTable": sum(r["potential"] for r in rows),
        "assumedTriggerLen": config["assumedTriggerLen"],
    }

    html_out = TEMPLATE.replace("__DATA__", json.dumps(data))
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
  .stat-tile .sub-value {
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 4px;
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
    grid-template-columns: 190px 1fr;
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
  .chip {
    display: inline-block;
    margin-left: 6px;
    padding: 1px 6px;
    border-radius: 999px;
    border: 1px solid var(--gridline);
    color: var(--text-muted);
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
    font-size: 10px;
    vertical-align: middle;
    white-space: nowrap;
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
  /* A near-full bar leaves no room to the right, so the label sits inside it. */
  .row .value.inside {
    transform: translateX(-100%);
    padding-left: 0;
    padding-right: 8px;
    color: #fff;
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

  <div class="note" id="note">
    <span class="icon">&#9432;</span>
    <span id="note-text"></span>
  </div>

  <div class="stats" id="stats"></div>

  <div class="card">
    <h2>Most-used commands</h2>
    <p class="sub" id="chart-sub"></p>
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

  <footer id="footer"></footer>
</div>

<div class="tooltip" id="tooltip" role="tooltip"></div>

<script>
const data = __DATA__;
const usingAtuin = data.source === "atuin";

document.getElementById("subtitle").textContent =
  "History window " + data.span + " • " + data.totalInvocations.toLocaleString() +
  " tracked invocations (via " + (usingAtuin ? "atuin" : "fish_history") + ")";

const sourceNote = usingAtuin
  ? "Counts come from atuin's history database, which logs every invocation " +
    "as its own row — including exact repeats — so these are true call counts, " +
    "not just distinct command variants."
  : "fish's history file collapses an exact repeat down to one entry (it just " +
    "bumps the timestamp), so anything you run identically every time — like a " +
    "no-argument alias — is undercounted here. Commands typically run with " +
    "varying arguments come much closer to a true count. Treat these numbers " +
    "as a floor, not an exact tally. Install atuin for exact counts.";

const abbrNote =
  " Abbreviations expand before the command runs, so history records the full " +
  "name and these counts stay attributed to it either way — no split totals, " +
  "no one-letter entries in your history.";

document.getElementById("note-text").textContent =
  sourceNote + (data.abbreviatedCount ? abbrNote : "");

document.getElementById("chart-sub").textContent =
  "Top 20 by invocation count, from " + (usingAtuin ? "atuin" : "fish_history") +
  ". Blue badge = long name (≥ " + data.candidateMinLen + " chars) called ≥ " +
  data.candidateMinCount + " times — a shortening candidate, costed against a " +
  data.assumedTriggerLen + "-character trigger. A ↔ chip means an abbreviation " +
  "already expands to it, so it's excluded from the badge.";

document.getElementById("footer").textContent = usingAtuin
  ? "Generated from atuin's history database — counts reflect every invocation."
  : "Generated from fish_history — counts reflect distinct command lines typed, not raw invocation count (see note above).";

const stats = document.getElementById("stats");
function statTile(label, value, sub) {
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
  if (sub) {
    const s = document.createElement("div");
    s.className = "sub-value";
    s.textContent = sub;
    tile.appendChild(s);
  }
  return tile;
}
stats.appendChild(statTile("Commands tracked", data.chart.length + data.tail.length));
stats.appendChild(statTile("Total invocations", data.totalInvocations.toLocaleString()));
stats.appendChild(statTile(
  "Keystrokes saved",
  data.keystrokesSaved.toLocaleString(),
  "🦭 " + data.keystrokesSaved.toLocaleString() + " seals spared"
));
stats.appendChild(statTile(
  "Still on the table",
  data.keystrokesOnTable.toLocaleString(),
  data.candidateCount + " candidates unshortened"
));

function abbrChip(row) {
  if (!row.abbrs || !row.abbrs.length) return null;
  const chip = document.createElement("span");
  chip.className = "chip";
  chip.textContent = "↔ " + row.abbrs.join(", ");
  chip.title = "Abbreviation" + (row.abbrs.length > 1 ? "s" : "") +
    " expanding to " + row.name;
  return chip;
}

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
  const chip = abbrChip(r);
  if (chip) nameEl.appendChild(chip);

  const barWrap = document.createElement("div");
  barWrap.className = "bar-wrap";
  const pct = (r.count / niceMax) * 100;
  const bar = document.createElement("div");
  bar.className = "bar";
  bar.style.width = "max(2px, " + pct + "%)";
  const value = document.createElement("div");
  value.className = pct > 82 ? "value inside" : "value";
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
    let suffix = " uses — " + r.name;
    if (r.saved) suffix += " · saved " + r.saved.toLocaleString() + " keystrokes 🦭";
    else if (r.potential) suffix += " · " + r.potential.toLocaleString() + " keystrokes on the table";
    tooltip.appendChild(document.createTextNode(suffix));
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
  const tailChip = abbrChip(r);
  if (tailChip) nameTd.appendChild(tailChip);
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
