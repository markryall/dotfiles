function b --description "Open bookmarks or URLs in a specific Crest space"
    switch "$argv[1]"
        case list
            __b_bookmarks list | sort | __b_table
        case "" help -h --help
            echo "b: open bookmarks and urls in Crest spaces"
            echo ""
            echo "  b mail-work                      open a bookmark in its space"
            echo "  b search fish shell abbr         fill a templated bookmark's {1} {2}.. or {*}"
            echo "  b @dev                           open every bookmark tagged dev"
            echo "  b go                             fuzzy-pick a bookmark (fzf) and open it"
            echo "  b in work example.com            open url(s) in a space (name matched loosely)"
            echo ""
            echo "  b list                           list bookmarks"
            echo "  b tags                           list tags and how many bookmarks carry each"
            echo "  b tags dev                       list the bookmarks tagged dev"
            echo "  b spaces                         list Crest spaces"
            echo ""
            echo "  b add <name> <space> <url>.. [+tag..]   save a bookmark"
            echo "  b add standup Work https://meet.google.com/abc-defg-hij +workday"
            echo "  b add order Work 'https://shop.example.com/orders/{1}'"
            echo "  b add search Personal 'https://www.google.com/search?q={*}'"
            echo "  b edit                           open the bookmarks file"
        case tags
            if test (count $argv) -ge 2
                set -l hits (__b_bookmarks tagged $argv[2])
                if test (count $hits) -eq 0
                    echo "no bookmarks tagged: $argv[2] (b tags to see)" >&2
                    return 1
                end
                printf '%s\n' $hits | sort | __b_table
            else
                __b_bookmarks tags | awk -F'\t' '{printf "%-18s %s\n", $1, $2}'
            end
        case go
            if not type -q fzf
                echo "b go needs fzf (brew install fzf)" >&2
                return 1
            end
            set -l sel (__b_bookmarks list | sort | __b_table | fzf --prompt="b> " --height=~40% --reverse)
            test -n "$sel"; or return 1
            b (string match -r '^\S+' -- $sel)
        case spaces
            __b_spaces
        case edit
            # $EDITOR may carry its own flags, like "emacsclient -n" or "code --wait"
            set -l editor vim
            set -q EDITOR; and test -n "$EDITOR"; and set editor (string split -n ' ' -- $EDITOR)
            $editor (__b_bookmarks file)
        case add
            __b_bookmarks add $argv[2..]
        case in
            if test (count $argv) -lt 3
                echo "usage: b in <space> <url>..." >&2
                return 1
            end
            __b_open $argv[2..]
        case '@*'
            __b_open_tag (string sub -s 2 -- $argv[1])
        case "*"
            set -l hit (__b_bookmarks get $argv[1])
            if test -z "$hit"
                echo "no bookmark: $argv[1] (b list to see, b add to create)" >&2
                return 1
            end
            set -l parts (string split \t $hit)
            if string match -qr '\{[0-9]+\}|\{\*\}' -- $parts[3]
                __b_open_template $parts[2] $parts[3] $argv[2..]
            else
                __b_open $parts[2] (string split " " $parts[3])
            end
    end
end

function __b_bookmarks --description "Query the TOML bookmarks file: name, space, urls, tags as TSV"
    $__fish_config_dir/bin/b.py $argv
end

function __b_table
    awk -F'\t' '{printf "%-22s %-16s %-18s %s\n", $1, $2, $4, $3}'
end

function __b_open_tag
    set -l lines (__b_bookmarks tagged $argv[1])
    if test (count $lines) -eq 0
        echo "no bookmarks tagged: $argv[1] (b tags to see)" >&2
        return 1
    end

    # One Crest call per space, so a tag spanning spaces opens each one's tabs together.
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
        __b_open $space $urls
    end
end

function __b_open_template
    set -l space $argv[1]
    set -l template $argv[2]
    set -l rest $argv[3..]

    set -l n 1
    while string match -q "*{$n}*" -- $template
        if test (count $rest) -lt 1
            echo "usage: b <name> ..." >&2
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
            echo "usage: b <name> ..." >&2
            echo "template: $template" >&2
            return 1
        end
        set -l val (string escape --style=url -- (string join " " $rest))
        set template (string replace '{*}' $val -- $template)
    end

    __b_open $space $template
end

function __b_spaces --description "List Crest spaces"
    __b_bookmarks spaces
end

function __b_open
    __b_bookmarks open $argv
end
