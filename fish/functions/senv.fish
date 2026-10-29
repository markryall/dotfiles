function senv --description 'rex session env, like tmux set-environment: senv NAME=VALUE or NAME to keep, -e NAME to drop, none to list'
    if not set -q REX_SESSION
        echo 'senv: not in a rex terminal' >&2
        return 1
    end
    # conf.d/rex-session-env.fish sources this in every new shell of the session
    set -l file ~/.local/state/rex-session-env/(string replace session: '' $REX_SESSION).fish

    if test (count $argv) -eq 0
        test -f $file; and cat $file
        return
    end

    set -l erase false
    if test "$argv[1]" = -e
        set erase true
        set -e argv[1]
    end

    # values can be secrets (API tokens etc), so keep it private and drop files from ended sessions
    mkdir -p (dirname $file)
    chmod 700 (dirname $file)
    touch $file
    chmod 600 $file
    set -l live (rex ls --json 2>/dev/null | string match -rag '"session:([^"]+)"')
    if contains -- (basename $file .fish) $live
        for old in (dirname $file)/*.fish
            contains -- (basename $old .fish) $live; or rm -f $old
        end
    end
    for arg in $argv
        set -l name (string split -m1 = -- $arg)[1]
        if string match -q -- '*=*' $arg
            set -gx $name (string split -m1 = -- $arg)[2]
        end
        set -l kept (string match -v -- "set -gx $name *" <$file)
        string join \n -- $kept >$file
        if test $erase = true
            set -e $name
        else if set -q $name
            echo "set -gx $name "(string escape -- $$name) >>$file
        else
            echo "senv: $name isn't set" >&2
        end
    end
end
