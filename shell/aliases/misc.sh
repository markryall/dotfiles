alias serve_this="open http://localhost:8000 && python -m SimpleHTTPServer"

alias rl="fresh && . ~/.zshrc"
alias ze="atom ~/.zshrc"

alias vim="nvim"
alias vi="nvim"
alias v="nvim"
alias vim.="nvim ."
alias vi.="nvim ."
alias v.="nvim ."
alias .v="nvim ."

alias subl.="subl ."
alias s.="subl ."
alias .s="subl ."

alias a="atom"
alias a.="atom ."
alias .a="atom ."

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
