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
  if [ -z $GH ]; then
    echo please set GH to specify where you want github repositories checked out
    return
  fi
  if [ -z $GH_USER ]; then
    echo please set GH_USER to specify your github username
    return
  fi
  _dvcscd git $GH $GH_USER $1 $2 $3
}

_glcd() {
  if [ -z $GL ]; then
    echo please set GL to specify where you want gitlab repositories checked out
    return
  fi
  if [ -z $GL_USER ]; then
    echo please set GL_USER to specify your gitlab username
    return
  fi
  _dvcscd git $GL $GL_USER $1 $2 $3
}

_bbcd() {
  if [ -z $BB ]; then
    echo please set BB to specify where you want bitbucket repositories checked out
    return
  fi
  if [ -z $BB_USER ]; then
    echo please set BB_USER to specify your bitbucket username
    return
  fi
  _dvcscd $1 $BB $BB_USER $2 $3 $4
}

gh() {
  _ghcd git@github.com: $1 $2
}

gl() {
  _glcd git@gitlab.com: $1 $2
}

bb() {
  _bbcd git git@bitbucket.org: $1 $2
}
