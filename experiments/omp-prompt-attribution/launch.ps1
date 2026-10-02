# Launch a bench run detached (tool-managed jobs get killed by command caps).
param([string]$Config, [string]$Results, [string]$Jobs, [string]$Trials, [string]$Harness, [string]$Tasks)
$root = "C:/Users/Yusuf/Desktop/harness-bench"
$argList = "-m bench --config $Config --results $Results run --harness $Harness --trials $Trials --jobs $Jobs --task $Tasks"
Start-Process -FilePath python -ArgumentList $argList -WorkingDirectory $root -RedirectStandardOutput "$root/$Results.log" -RedirectStandardError "$root/$Results.err" -WindowStyle Hidden
