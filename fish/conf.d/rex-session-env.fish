# Env saved with senv for this rex session, so new windows and splits pick it up.
if set -q REX_SESSION
    set -l file ~/.local/state/rex-session-env/(string replace session: '' $REX_SESSION).fish
    test -f $file; and source $file
end
