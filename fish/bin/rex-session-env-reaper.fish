#!/opt/homebrew/bin/fish
# Drops senv files when their rex session is destroyed. Run it under launchd with
# KeepAlive (see fish/README.md), which restarts it when the server goes away.

set -l dir ~/.local/state/rex-session-env
# launchd's PATH won't have rex on it, so fall back to the copy inside the server app
set -l rex (command -s rex)
or set rex "$HOME/Library/Application Support/com.superlogical.rex/RexServer/Versions/Current/Rex Server.app/Contents/MacOS/rex"

# Catch sessions that ended while nothing was listening
set -l live ("$rex" ls --json | string match -rag '"session:([^"]+)"')
or exit 1
for file in $dir/*.fish
    contains -- (basename $file .fish) $live; or rm -f $file
end

"$rex" events --json | while read -l line
    set -l id (string match -rg '^\{"type":"session_destroyed","payload":\{"session_id":"session:([^"]+)"' -- $line)
    and rm -f $dir/$id.fish
end
