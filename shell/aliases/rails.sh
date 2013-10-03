alias rs="rails server"
alias rc="rails console"

createrailspgdb() {
  createuser -s $1
  createdb $1_development
  createdb $1_test
  createdb $1_production
}

newrails() {
  gem install rails
  rbenv rehash
  rails new $1 -T -d postgresql
  createrailspgdb $1
  cd $1
  git init
  git add .
  git commit -m "empty rails application"
  subl.
}