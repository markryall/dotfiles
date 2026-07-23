function fish-usage-report --description "Generate an HTML report of fish function usage frequency and open it"
    set -l script ~/.config/fish/scripts/fish-usage-report.py
    if not test -f $script
        echo "missing $script" >&2
        return 1
    end
    set -l out (mktemp -d)/fish-usage-report.html
    python3 $script $out; or return 1
    open $out
end
