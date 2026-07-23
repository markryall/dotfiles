# fish tools

Standalone fish functions/scripts that don't depend on the rest of this repo.
Each one is self-contained — copy or symlink the pieces you want into your
own fish config.

## fish-usage-report

Generates an HTML report comparing how often you actually type each of your
fish functions against how long their names are, so you can spot
high-frequency functions worth giving a short alias. Opens the report in
your browser.

**Requires:** `python3` on `PATH`.

**Data source:** prefers [atuin](https://atuin.sh)'s history database
(`~/.local/share/atuin/history.db`) when present, since it logs every
invocation as its own row. Falls back to fish's own `fish_history` otherwise
— which collapses an exact repeat down to one entry (it bumps the timestamp
instead of appending), so commands you always run identically, especially
no-argument aliases, come out undercounted there. Treat fish_history-sourced
numbers as a floor, not an exact tally; the report notes which source it
used and adjusts its wording accordingly.

**Install:**

```sh
cp fish/functions/fish-usage-report.fish ~/.config/fish/functions/
mkdir -p ~/.config/fish/scripts
cp fish/scripts/fish-usage-report.py ~/.config/fish/scripts/
```

(Symlink instead of `cp` if you want to track changes from this repo.)

**Use:**

```sh
fish-usage-report
```

## github

Clones a GitHub repo into `$CODE/github/<user>/<project>` (creating the
folders if needed) and `cd`s into it, or just `cd`s there if it's already
cloned. Takes `user/project`, `project` alone (falls back to `$GH_USER`), or
a full `.git` URL/path — trailing `.git` is stripped either way.

**Install:**

```sh
cp fish/functions/github.fish ~/.config/fish/functions/
```

**Use:**

```sh
github markryall/dotfiles
github dotfiles   # uses $GH_USER
```

## arc

Open bookmarked URLs in a specific [Arc](https://arc.net) browser space by
name, with tab completion and a fuzzy picker. Bookmarks are read from a
pipe-delimited file at `~/.arc-bookmarks` — `name | space | url`, one per
line — which is **not** part of this repo (it's personal data; create your
own). A bookmark's URL can use `{1}`, `{2}`, … or `{*}` as placeholders that
get filled from extra args at open time.

**Requires:** [Arc](https://arc.net) on macOS; `fzf` for `arc go`.

**Install:**

```sh
cp fish/functions/arc.fish ~/.config/fish/functions/
cp fish/completions/arc.fish ~/.config/fish/completions/
touch ~/.arc-bookmarks   # or symlink to wherever you keep your own bookmarks file
```

**Use:**

```sh
arc                              # list bookmarks
arc <name>                       # open a bookmark in its space
arc go                           # fuzzy-pick a bookmark (fzf) and open it
arc add <name> <space> <url>     # save a bookmark
arc add order Work https://shop.example.com/orders/{1}
arc order 42           # fills {1} -> 42
arc in <space> <url>...          # open url(s) in a space
arc edit                         # open the bookmarks file
arc spaces                       # list Arc spaces
```
