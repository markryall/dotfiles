#!/usr/bin/env python3
"""Read and write the b bookmarks file, emitting TSV for the fish `b` function,
and open urls in Crest spaces through Crest's own MCP server (`crest-browser mcp`).

The bookmarks file is TOML: one table per bookmark, keyed by its name.

    [chat-work]
    space = "Work"
    url = "https://chat.example.com"
    tags = ["workday"]

`url` may be a string or a list of strings (they open together). `tags` is
optional, and a tag may be carried by any number of bookmarks across spaces.

Every read subcommand prints TSV: name, space, space-joined urls, space-joined tags.

`spaces` lists the Crest spaces allowed in Settings > Agents, and `open <space>
<url>..` opens urls as tabs of the space whose name matches loosely (ignoring
case and punctuation, exact before substring), bringing the last one forward.
"""

import json
import os
import re
import subprocess
import sys
import tomllib

BARE_KEY = re.compile(r"^[A-Za-z0-9_-]+$")

FILE = os.environ.get("B_BOOKMARKS", os.path.expanduser("~/.browser-bookmarks.toml"))
CREST = "/Applications/Crest.app/Contents/Helpers/crest-browser"


def load():
    try:
        with open(FILE, "rb") as f:
            raw = tomllib.load(f)
    except FileNotFoundError:
        return []
    except tomllib.TOMLDecodeError as e:
        sys.exit(f"b: {FILE} is not valid TOML: {e}")

    bookmarks = []
    for name, entry in raw.items():
        if not isinstance(entry, dict):
            print(f"b: skipping {name}: not a table", file=sys.stderr)
            continue
        space = entry.get("space")
        url = entry.get("url")
        if not space or not url:
            print(f"b: skipping {name}: needs both space and url", file=sys.stderr)
            continue
        urls = [url] if isinstance(url, str) else list(url)
        tags = entry.get("tags", [])
        if isinstance(tags, str):
            tags = tags.split()
        bookmarks.append((name, space, urls, list(tags)))
    return bookmarks


def emit(bookmarks):
    for name, space, urls, tags in bookmarks:
        print("\t".join([name, space, " ".join(urls), " ".join(tags)]))


def add(argv):
    if len(argv) < 3:
        sys.exit("usage: b.py add <name> <space> <url>.. [+tag..]")
    name, space = argv[0], argv[1]
    urls = [a for a in argv[2:] if not a.startswith("+")]
    tags = [a[1:] for a in argv[2:] if a.startswith("+")]
    if not urls:
        sys.exit("usage: b.py add <name> <space> <url>.. [+tag..]")
    if any(b[0] == name for b in load()):
        sys.exit(f"b: {name} already exists (b edit to change it)")

    q = json.dumps
    key = name if BARE_KEY.match(name) else q(name)
    lines = [f"\n[{key}]"]
    lines.append(f"space = {q(space)}")
    lines.append(f"url = {q(urls[0])}" if len(urls) == 1
                 else "url = [" + ", ".join(q(u) for u in urls) + "]")
    if tags:
        lines.append("tags = [" + ", ".join(q(t) for t in tags) + "]")

    with open(FILE, "a") as f:
        f.write("\n".join(lines) + "\n")
    print(f"added: {name} -> {space}" + (f" [{' '.join(tags)}]" if tags else ""))


class Crest:
    """A minimal MCP client over stdio to Crest's agent server."""

    def __init__(self):
        if not os.access(CREST, os.X_OK):
            sys.exit(f"b: {CREST} not found (is Crest installed?)")
        self.proc = subprocess.Popen([CREST, "mcp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        self.next_id = 0
        self.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                    "clientInfo": {"name": "b", "version": "1"}})
        self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.call("identify", name="b", color="#FF69B4")

    def send(self, message):
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()

    def request(self, method, params):
        self.next_id += 1
        self.send({"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params})
        for line in self.proc.stdout:
            message = json.loads(line)
            if message.get("id") != self.next_id:
                continue
            if "error" in message:
                sys.exit(f"b: crest {method}: {message['error'].get('message')}")
            return message["result"]
        sys.exit(f"b: crest exited during {method}")

    def call(self, tool, **arguments):
        result = self.request("tools/call", {"name": tool, "arguments": arguments})
        text = "".join(c.get("text", "") for c in result.get("content", []))
        if result.get("isError"):
            sys.exit(f"b: crest {tool}: {text}")
        try:
            return json.loads(text)
        except ValueError:
            return text

    def close(self):
        self.proc.stdin.close()
        self.proc.wait(timeout=5)


def loose(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())


def spaces(crest):
    return [s for s in crest.call("list_spaces")["spaces"]]


def find_space(crest, query):
    known = spaces(crest)
    q = loose(query)
    hit = next((s for s in known if loose(s["name"]) == q), None) \
        or next((s for s in known if q in loose(s["name"])), None)
    if hit is None:
        sys.exit(f"b: no space matches: {query}\nspaces: " + ", ".join(s["name"] for s in known))
    if hit.get("locked"):
        sys.exit(f"b: {hit['name']} is locked (unlock it in Crest first)")
    return hit


def open_urls(argv):
    if len(argv) < 2:
        sys.exit("usage: b.py open <space> <url>..")
    crest = Crest()
    space = find_space(crest, argv[0])
    urls = [u if re.match(r"^[a-z]+://", u) else f"https://{u}" for u in argv[1:]]
    for i, url in enumerate(urls):
        crest.call("open_tab", space=space["id"], url=url, show=i == len(urls) - 1)
    crest.close()
    print(f"opened in {space['name']}: " + " ".join(urls))


def main():
    argv = sys.argv[1:]
    cmd = argv[0] if argv else "list"

    if cmd == "list":
        emit(load())
    elif cmd == "get":
        hits = [b for b in load() if b[0] == argv[1]]
        if not hits:
            return 1
        emit(hits)
    elif cmd == "tagged":
        emit([b for b in load() if argv[1] in b[3]])
    elif cmd == "tags":
        counts = {}
        for _, _, _, tags in load():
            for tag in tags:
                counts[tag] = counts.get(tag, 0) + 1
        for tag in sorted(counts):
            print(f"{tag}\t{counts[tag]}")
    elif cmd == "file":
        print(FILE)
    elif cmd == "add":
        add(argv[1:])
    elif cmd == "spaces":
        crest = Crest()
        for space in spaces(crest):
            print(space["name"] + ("\tlocked" if space.get("locked") else ""))
        crest.close()
    elif cmd == "open":
        open_urls(argv[1:])
    else:
        sys.exit(f"b.py: unknown command: {cmd}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
