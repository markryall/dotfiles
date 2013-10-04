timing() {
  direction=$1
  shift
  mkdir -p ~/.timing
  perl -e "my \$t=time(); print \"$direction\$t $*\\n\";" | tee -a ~/.timing/timings.txt
}

start() {
  timing + $*
}

stop() {
  timing - $*
}