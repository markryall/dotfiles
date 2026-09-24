function __b_complete_bookmarks
    $__fish_config_dir/bin/b.py list 2>/dev/null | awk -F'\t' '{printf "%s\t%s: %s\n", $1, $2, $3}'
end

function __b_complete_tags
    $__fish_config_dir/bin/b.py tags 2>/dev/null | awk -F'\t' -v p="$argv[1]" '{printf "%s%s\t%s bookmarks\n", p, $1, $2}'
end

function __b_complete_spaces
    $__fish_config_dir/bin/b.py spaces 2>/dev/null | cut -f1
end

complete -c b -f
complete -c b -n __fish_use_subcommand -a "(__b_complete_bookmarks)"
complete -c b -n __fish_use_subcommand -a "(__b_complete_tags @)"
complete -c b -n __fish_use_subcommand -a list -d 'List bookmarks'
complete -c b -n __fish_use_subcommand -a tags -d 'List tags, or the bookmarks carrying one'
complete -c b -n __fish_use_subcommand -a go -d 'Fuzzy-pick a bookmark (fzf)'
complete -c b -n __fish_use_subcommand -a in -d 'Open url(s) in a space'
complete -c b -n __fish_use_subcommand -a add -d 'Save a bookmark: b add <name> <space> <url>.. [+tag..]'
complete -c b -n __fish_use_subcommand -a edit -d 'Edit the bookmarks file'
complete -c b -n __fish_use_subcommand -a spaces -d 'List Crest spaces'
complete -c b -n __fish_use_subcommand -a help -d 'Show usage'
complete -c b -n '__fish_seen_subcommand_from tags; and test (count (commandline -opc)) -eq 2' -a "(__b_complete_tags)"
complete -c b -n '__fish_seen_subcommand_from in; and test (count (commandline -opc)) -eq 2' -a "(__b_complete_spaces)"
complete -c b -n '__fish_seen_subcommand_from add; and test (count (commandline -opc)) -eq 3' -a "(__b_complete_spaces)"
complete -c b -n '__fish_seen_subcommand_from add; and test (count (commandline -opc)) -ge 4' -a "(__b_complete_tags +)"
