alias g="git status"
alias ga="git add ."
alias gaa="git add -A ."
alias gl="git log"
alias gd="git diff"
alias gsl="git stash list"
alias gsl="git stash list"
alias gsc="git stash clear"

commit() {
  git commit -m "$*"
}

push() {
  git commit -m "$*"
  git push
}

pull() {
  git stash
  git pull
  git stash pop
}