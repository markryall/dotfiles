tfpull() {
  git stash
  git tf pull
  git stash pop
}

tfpush() {
  git commit -m "$*"
  git tf checkin
}