# Defined interactively
function github
    set arg_parts (string split "/" $argv[1])
    set repo_user $arg_parts[-2]
    # assign to default github user if just one part (project)
    if test "$repo_user" = ""
        set repo_user $GH_USER
    end
    # strip .git from the end if present
    set repo_project_parts (string split "." $arg_parts[-1])
    set repo_project $repo_project_parts[1]
    set repo_url git@github.com:$repo_user/$repo_project.git
    set local_parent_path $CODE/github/$repo_user
    set local_path $local_parent_path/$repo_project
    mkdir -p $local_parent_path
    if test -d $local_path
        echo "$local_path already exists"
    else
        echo "cloning $repo_url to $local_path"
        git clone $repo_url $local_path
    end
    cd $local_path
end
