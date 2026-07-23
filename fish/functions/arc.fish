function arc --description "Open bookmarks or URLs in a specific Arc space"
    set -l file ~/.arc-bookmarks

    switch "$argv[1]"
        case "" list
            __arc_bookmark_lines $file | sort | awk -F'\t' '{printf "%-18s %-16s %s\n", $1, $2, $3}'
        case help -h --help
            echo "usage:"
            echo "  arc                     list bookmarks"
            echo "  arc <name>              open bookmark in its space"
            echo "  arc <name> <arg>..      fill a templated bookmark's {1} {2}.. or {*} placeholders"
            echo "  arc go                  fuzzy-pick a bookmark (fzf) and open it"
            echo "  arc in <space> <url>..  open url(s) in a space (name matched loosely)"
            echo "  arc add <name> <space> <url>..  save a bookmark"
            echo "  arc edit                open the bookmarks file"
            echo "  arc spaces              list Arc spaces"
            echo ""
            echo "templated bookmarks: use {1} {2} .. for positional args, {*} for all remaining args joined"
            echo "  arc add order Work https://shop.example.com/orders/{1}"
            echo "  arc add search Personal https://www.google.com/search?q={*}"
        case go
            if not type -q fzf
                echo "arc go needs fzf (brew install fzf)" >&2
                return 1
            end
            set -l sel (__arc_bookmark_lines $file | sort | awk -F'\t' '{printf "%-18s %-16s %s\n", $1, $2, $3}' | fzf --prompt="arc> " --height=~40% --reverse)
            test -n "$sel"; or return 1
            arc (string match -r '^\S+' -- $sel)
        case spaces
            osascript -l JavaScript -e 'const w = Application("Arc").windows; w.length ? w[0].spaces.title().join("\n") : "no Arc windows open"'
        case edit
            emacsclient -n $file
        case add
            if test (count $argv) -lt 4
                echo "usage: arc add <name> <space> <url>..." >&2
                return 1
            end
            echo "$argv[2] | $argv[3] | $argv[4..]" >>$file
            echo "added: $argv[2] -> $argv[3]"
        case in
            if test (count $argv) -lt 3
                echo "usage: arc in <space> <url>..." >&2
                return 1
            end
            __arc_open $argv[2..]
        case "*"
            for line in (__arc_bookmark_lines $file)
                set -l parts (string split \t $line)
                if test "$parts[1]" = "$argv[1]"
                    if string match -qr '\{[0-9]+\}|\{\*\}' -- $parts[3]
                        __arc_open_template $parts[2] $parts[3] $argv[2..]
                    else
                        __arc_open $parts[2] (string split " " $parts[3])
                    end
                    return
                end
            end
            echo "no bookmark: $argv[1] (arc list to see, arc add to create)" >&2
            return 1
    end
end

function __arc_bookmark_lines
    test -f $argv[1]; or return
    string match -rv '^\s*(#|$)' <$argv[1] | while read -l line
        set -l parts (string split -m 2 "|" $line)
        test (count $parts) -eq 3; or continue
        printf "%s\t%s\t%s\n" (string trim $parts[1]) (string trim $parts[2]) (string trim $parts[3])
    end
end

function __arc_open_template
    set -l space $argv[1]
    set -l template $argv[2]
    set -l rest $argv[3..]

    set -l n 1
    while string match -q "*{$n}*" -- $template
        if test (count $rest) -lt 1
            echo "usage: arc <name> ..." >&2
            echo "template: $template" >&2
            return 1
        end
        set -l val (string escape --style=url -- $rest[1])
        set template (string replace "{$n}" $val -- $template)
        set rest $rest[2..]
        set n (math $n + 1)
    end

    if string match -q '*{\*}*' -- $template
        if test (count $rest) -lt 1
            echo "usage: arc <name> ..." >&2
            echo "template: $template" >&2
            return 1
        end
        set -l val (string escape --style=url -- (string join " " $rest))
        set template (string replace '{*}' $val -- $template)
    end

    __arc_open $space $template
end

function __arc_open
    osascript -l JavaScript -e '
function run(argv) {
  const arc = Application("Arc");
  const q = argv[0].toLowerCase();
  if (!arc.windows.length) {
    arc.activate();
    for (let n = 0; n < 20 && !arc.windows.length; n++) delay(0.25);
    if (!arc.windows.length) throw "Arc has no windows";
  }
  const win = arc.windows[0];
  const titles = win.spaces.title();
  let i = titles.findIndex((t) => t.toLowerCase() === q);
  if (i < 0) i = titles.findIndex((t) => t.toLowerCase().includes(q));
  if (i < 0) throw "no space matches: " + argv[0] + "\nspaces: " + titles.join(", ");
  const space = win.spaces[i];
  space.focus();
  const urls = argv.slice(1).map((u) => (u.match(/^[a-z]+:\/\//) ? u : "https://" + u));
  for (const u of urls) space.tabs.push(arc.Tab({ url: u }));
  arc.activate();
  return "opened in " + titles[i] + ": " + urls.join(" ");
}
' -- $argv
end
