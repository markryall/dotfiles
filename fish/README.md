# fish tools

Standalone fish functions/scripts that don't depend on the rest of this repo.
Each one is self-contained — copy or symlink the pieces you want into your
own fish config.

## fish-usage-report

Generates an HTML report comparing how often you actually type each of your
fish functions (from `fish_history`) against how long their names are, so you
can spot high-frequency functions worth giving a short alias. Opens the
report in your browser.

**Requires:** `python3` on `PATH`.

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
