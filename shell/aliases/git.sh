alias g="git status"
alias ga="git add -A ."
alias gl="git log"
alias gd="git diff"
alias gds="git diff --staged"
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

destroy_merged_branches() {
  git branch --merged | grep -v "\*" | xargs -n 1 git branch -d
}
