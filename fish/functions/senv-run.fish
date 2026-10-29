function senv-run --description 'run a command and senv every exported var it changes, like loading env before starting a tmux server'
    if not set -q REX_SESSION
        echo 'senv-run: not in a rex terminal' >&2
        return 1
    end
    # per-shell or per-directory vars that would be wrong in any other window
    # (mise rebuilds PATH and its own state from the directory in each shell,
    # and macOS strips DYLD_* from the bash that replay starts, so replay blanks them)
    set -l skip PWD OLDPWD SHLVL _ PATH REX_SERVER REX_SESSION REX_BLOCK REX_BIN_DIR

    set -l names (set --export --names)
    set -l before
    for name in $names
        set -a before "$(string escape -- $$name | string join ' ')"
    end

    $argv
    set -l result $status

    set -l changed
    for name in (set --export --names)
        if contains -- $name $skip; or string match -qr -- '^(__MISE_|DYLD_)' $name
            continue
        end
        set -l i (contains -i -- $name $names)
        if test -z "$i"; or test "$before[$i]" != "$(string escape -- $$name | string join ' ')"
            set -a changed $name
        end
    end
    set -l removed
    for name in $names
        if not set -qx $name; and not contains -- $name $skip
            set -a removed $name
        end
    end

    test (count $changed) -gt 0; and senv $changed
    test (count $removed) -gt 0; and senv -e $removed
    return $result
end
