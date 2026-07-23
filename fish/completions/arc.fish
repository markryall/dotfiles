function __arc_complete_bookmarks
    set -l file ~/.arc-bookmarks
    test -f $file; or return
    string match -rv '^\s*(#|$)' <$file | while read -l line
        set -l parts (string split -m 2 "|" $line)
        test (count $parts) -eq 3; or continue
        printf "%s\t%s: %s\n" (string trim $parts[1]) (string trim $parts[2]) (string trim $parts[3])
    end
end

function __arc_complete_spaces
    osascript -l JavaScript -e 'const w = Application("Arc").windows; w.length ? w[0].spaces.title().join("\n") : ""' 2>/dev/null
end

complete -c arc -f
complete -c arc -n __fish_use_subcommand -a "(__arc_complete_bookmarks)"
complete -c arc -n __fish_use_subcommand -a list -d 'List bookmarks'
complete -c arc -n __fish_use_subcommand -a in -d 'Open url(s) in a space'
complete -c arc -n __fish_use_subcommand -a add -d 'Save a bookmark: arc add <name> <space> <url>'
complete -c arc -n __fish_use_subcommand -a edit -d 'Edit the bookmarks file'
complete -c arc -n __fish_use_subcommand -a spaces -d 'List Arc spaces'
complete -c arc -n __fish_use_subcommand -a help -d 'Show usage'
complete -c arc -n '__fish_seen_subcommand_from in; and test (count (commandline -opc)) -eq 2' -a "(__arc_complete_spaces)"
complete -c arc -n '__fish_seen_subcommand_from add; and test (count (commandline -opc)) -eq 3' -a "(__arc_complete_spaces)"
