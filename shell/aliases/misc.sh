alias serve_this="open http://localhost:8000 && python -m SimpleHTTPServer"

alias rl=". ~/.zshrc"

alias vim="mvim -v"
alias vi="mvim -v"
alias vim.="mvim -v ."
alias vi.="mvim -v."

alias mate.="mate ."

alias subl.="subl ."

alias vlc='/Applications/VLC.app/Contents/MacOS/VLC'
alias vlc-rc='vlc --intf rc'
alias vlc-nc='vlc --intf ncurses'

psg() {
  ps -ef | grep "$*"
}

gr() {
  grep -n -r $1 .
}