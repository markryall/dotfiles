pginit() {
  rm -rf /usr/local/var/postgres
  initdb /usr/local/var/postgres -E utf8
}

pgstart() { pg_ctl -D /usr/local/var/postgres -l /usr/local/var/postgres/server.log start }

pgstop() { pg_ctl -D /usr/local/var/postgres stop -s -m fast }