alias serve_this="open http://localhost:8000 && python -m SimpleHTTPServer"

alias rl="fresh && . ~/.zshrc"
alias ze="atom ~/.zshrc"

alias vim="mvim -v"
alias vi="mvim -v"
alias v="mvim -v"
alias vim.="mvim -v ."
alias vi.="mvim -v ."
alias v.="mvim -v ."
alias .v="mvim -v ."

alias subl.="subl ."
alias s.="subl ."
alias .s="subl ."

alias e="emacs"
alias e.="emacs ."
alias .e="emacs ."

alias vlc='/Applications/VLC.app/Contents/MacOS/VLC'
alias vlc-rc='vlc --intf rc'
alias vlc-nc='vlc --intf ncurses'

psg() {
  ps -ef | grep "$*"
}

gr() {
  grep -n -r $1 .
}
