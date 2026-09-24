function __arc_complete_bookmarks
    $__fish_config_dir/bin/arc-bookmarks.py list 2>/dev/null | awk -F'\t' '{printf "%s\t%s: %s\n", $1, $2, $3}'
end

function __arc_complete_tags
    $__fish_config_dir/bin/arc-bookmarks.py tags 2>/dev/null | awk -F'\t' -v p="$argv[1]" '{printf "%s%s\t%s bookmarks\n", p, $1, $2}'
end

function __arc_complete_spaces
    string replace -rf '^Name=' '' <"$HOME/Library/Application Support/zen/profiles.ini" 2>/dev/null
end

complete -c arc -f
complete -c arc -n __fish_use_subcommand -a "(__arc_complete_bookmarks)"
complete -c arc -n __fish_use_subcommand -a "(__arc_complete_tags @)"
complete -c arc -n __fish_use_subcommand -a list -d 'List bookmarks'
complete -c arc -n __fish_use_subcommand -a tags -d 'List tags, or the bookmarks carrying one'
complete -c arc -n __fish_use_subcommand -a go -d 'Fuzzy-pick a bookmark (fzf)'
complete -c arc -n __fish_use_subcommand -a in -d 'Open url(s) in a space'
complete -c arc -n __fish_use_subcommand -a add -d 'Save a bookmark: arc add <name> <space> <url>.. [+tag..]'
complete -c arc -n __fish_use_subcommand -a edit -d 'Edit the bookmarks file'
complete -c arc -n __fish_use_subcommand -a spaces -d 'List Zen profiles'
complete -c arc -n __fish_use_subcommand -a help -d 'Show usage'
complete -c arc -n '__fish_seen_subcommand_from tags; and test (count (commandline -opc)) -eq 2' -a "(__arc_complete_tags)"
complete -c arc -n '__fish_seen_subcommand_from in; and test (count (commandline -opc)) -eq 2' -a "(__arc_complete_spaces)"
complete -c arc -n '__fish_seen_subcommand_from add; and test (count (commandline -opc)) -eq 3' -a "(__arc_complete_spaces)"
complete -c arc -n '__fish_seen_subcommand_from add; and test (count (commandline -opc)) -ge 4' -a "(__arc_complete_tags +)"
