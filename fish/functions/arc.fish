function arc --description "Open bookmarks or URLs in a specific Arc space"
    switch "$argv[1]"
        case "" list
            __arc_bookmarks list | sort | __arc_table
        case help -h --help
            echo "usage:"
            echo "  arc                     list bookmarks"
            echo "  arc <name>              open bookmark in its space"
            echo "  arc <name> <arg>..      fill a templated bookmark's {1} {2}.. or {*} placeholders"
            echo "  arc @<tag>              open every bookmark carrying that tag"
            echo "  arc tags                list tags and how many bookmarks carry each"
            echo "  arc tags <tag>          list the bookmarks carrying a tag"
            echo "  arc go                  fuzzy-pick a bookmark (fzf) and open it"
            echo "  arc in <space> <url>..  open url(s) in a space (name matched loosely)"
            echo "  arc add <name> <space> <url>.. [+tag..]  save a bookmark"
            echo "  arc edit                open the bookmarks file"
            echo "  arc spaces              list Arc spaces"
            echo ""
            echo "templated bookmarks: use {1} {2} .. for positional args, {*} for all remaining args joined"
            echo "  arc add order Work https://shop.example.com/orders/{1}"
            echo "  arc add search Personal https://www.google.com/search?q={*}"
            echo ""
            echo "tags: a bookmark can carry any number, and a tag can span spaces"
            echo "  arc add standup-ops Work https://meet.google.com/abc-defg-hij +workday +ops"
            echo "  arc @workday"
        case tags
            if test (count $argv) -ge 2
                set -l hits (__arc_bookmarks tagged $argv[2])
                if test (count $hits) -eq 0
                    echo "no bookmarks tagged: $argv[2] (arc tags to see)" >&2
                    return 1
                end
                printf '%s\n' $hits | sort | __arc_table
            else
                __arc_bookmarks tags | awk -F'\t' '{printf "%-18s %s\n", $1, $2}'
            end
        case go
            if not type -q fzf
                echo "arc go needs fzf (brew install fzf)" >&2
                return 1
            end
            set -l sel (__arc_bookmarks list | sort | __arc_table | fzf --prompt="arc> " --height=~40% --reverse)
            test -n "$sel"; or return 1
            arc (string match -r '^\S+' -- $sel)
        case spaces
            osascript -l JavaScript -e 'const w = Application("Arc").windows; w.length ? w[0].spaces.title().join("\n") : "no Arc windows open"'
        case edit
            emacsclient -n (__arc_bookmarks file)
        case add
            __arc_bookmarks add $argv[2..]
        case in
            if test (count $argv) -lt 3
                echo "usage: arc in <space> <url>..." >&2
                return 1
            end
            __arc_open $argv[2..]
        case '@*'
            __arc_open_tag (string sub -s 2 -- $argv[1])
        case "*"
            set -l hit (__arc_bookmarks get $argv[1])
            if test -z "$hit"
                echo "no bookmark: $argv[1] (arc list to see, arc add to create)" >&2
                return 1
            end
            set -l parts (string split \t $hit)
            if string match -qr '\{[0-9]+\}|\{\*\}' -- $parts[3]
                __arc_open_template $parts[2] $parts[3] $argv[2..]
            else
                __arc_open $parts[2] (string split " " $parts[3])
            end
    end
end

function __arc_bookmarks --description "Query the TOML bookmarks file: name, space, urls, tags as TSV"
    $__fish_config_dir/bin/arc-bookmarks.py $argv
end

function __arc_table
    awk -F'\t' '{printf "%-22s %-16s %-18s %s\n", $1, $2, $4, $3}'
end

function __arc_open_tag
    set -l lines (__arc_bookmarks tagged $argv[1])
    if test (count $lines) -eq 0
        echo "no bookmarks tagged: $argv[1] (arc tags to see)" >&2
        return 1
    end

    # One Arc call per space, so a tag spanning spaces opens each space's tabs together.
    set -l spaces
    for line in $lines
        set -l parts (string split \t $line)
        if string match -qr '\{[0-9]+\}|\{\*\}' -- $parts[3]
            echo "skipping templated bookmark: $parts[1]" >&2
            continue
        end
        contains -- $parts[2] $spaces; or set -a spaces $parts[2]
    end

    for space in $spaces
        set -l urls
        for line in $lines
            set -l parts (string split \t $line)
            test "$parts[2]" = "$space"; or continue
            string match -qr '\{[0-9]+\}|\{\*\}' -- $parts[3]; and continue
            set -a urls (string split " " $parts[3])
        end
        __arc_open $space $urls
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
