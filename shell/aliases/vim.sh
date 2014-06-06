vimbundle() {
  if [[ -d ~/.vim/bundle/$2 ]]; then
  	echo $2 is already installed
  else	
    pushd ~/.vim/bundle
    git clone git://github.com/$1/$2
    popd
  fi
}
