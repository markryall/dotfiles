_dvcscd() {
  local cmd=$1
  shift
  local basepath=$1
  shift
  local username=$1
  shift
  local protocol=$1
  shift
  repo=$1
  repoarray=("${(s:/:)repo}")
  if [[ ${#repoarray} == 1 ]]; then
    repo=$1
  else
    username=$repoarray[-2]
    repo=$repoarray[-1]
  fi
  mkdir -p $basepath/$username
  local fullpath=$basepath/$username/$repo
  if [[ -d $fullpath ]]; then
    cd $fullpath
  else
    cd $basepath/$username
    $cmd clone $protocol$username/$repo.git
    cd $repo
  fi
  if [[ -f .prep ]]; then
    . ./.prep
  fi
}

_ghcd() {
  if [ -z $GH_BASE ]; then
    echo please set GH_BASE to specify where you want github repositories checked out
    return
  fi
  if [ -z $GH_USER ]; then
    echo please set GH_USER to specify your github username
    return
  fi
  _dvcscd git $GH_BASE $GH_USER $1 $2 $3
}

_bbcd() {
  if [ -z $BB_BASE ]; then
    echo please set GH_BASE to specify where you want bitbucket repositories checked out
    return
  fi
  if [ -z $BB_USER ]; then
    echo please set BB_USER to specify your bitbucket username
    return
  fi
  _dvcscd $1 $BB_BASE $BB_USER $2 $3 $4
}

gh() {
  _ghcd git@github.com: $1 $2
}

bb() {
  _bbcd git git@bitbucket.org: $1 $2
}

bbhg() {
  _bbcd hg ssh://hg@bitbucket.org/ $1 $2
}