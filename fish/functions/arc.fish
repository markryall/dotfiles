function arc --description "Open bookmarks or URLs in a specific Zen profile"
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
            echo "  arc spaces              list Zen profiles"
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
            __arc_spaces
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

    # One Zen call per profile, so a tag spanning profiles opens each one's tabs together.
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

function __arc_spaces --description "List Zen profile names"
    string replace -rf '^Name=' '' <"$HOME/Library/Application Support/zen/profiles.ini"
end

function __arc_open
    set -l q (string lower -- $argv[1])
    set -l names (__arc_spaces)
    set -l name
    for n in $names
        test (string lower -- $n) = $q; and set name $n; and break
    end
    if test -z "$name"
        for n in $names
            string match -q -- "*$q*" (string lower -- $n); and set name $n; and break
        end
    end
    if test -z "$name"
        echo "no profile matches: $argv[1]" >&2
        echo "profiles: "(string join ", " $names) >&2
        return 1
    end

    set -l args -P $name
    for u in $argv[2..]
        string match -qr '^[a-z]+://' -- $u; or set u https://$u
        set -a args --new-tab $u
    end
    # -n starts a fresh process each time; Zen hands the urls to the profile's
    # instance when it is already running, or becomes that instance when not.
    open -na /Applications/Zen.app --args $args
    echo "opened in $name: "(string join " " $argv[2..])
end
