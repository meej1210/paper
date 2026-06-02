param(
    [string]$BaseUrl = "http://127.0.0.1:5000/api",
    [string]$Username = $env:DEVSECOPS_USER,
    [string]$Password = $env:DEVSECOPS_PASSWORD,
    [ValidateSet("sast", "sca")][string]$Type = "sast",
    [Parameter(Mandatory=$true)][string]$TargetFile,
    [ValidateSet("high", "fixable", "any")][string]$FailOn = "high",
    [int]$Timeout = 180,
    [string]$OutDir = "tmp\ci-artifacts"
)

if (-not $Username -or -not $Password) {
    Write-Error "Set DEVSECOPS_USER/DEVSECOPS_PASSWORD or pass -Username/-Password."
    exit 1
}

$Python = "D:\anaconda\python.exe"
& $Python "$PSScriptRoot\ci_security_scan.py" --base-url $BaseUrl --username $Username --password $Password --type $Type --target-file $TargetFile --fail-on $FailOn --timeout $Timeout --out-dir $OutDir
exit $LASTEXITCODE
