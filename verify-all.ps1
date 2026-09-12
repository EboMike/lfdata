# Parameters
param (
    [Parameter(Position = 0, Mandatory = $false)]
    [string]$Path = ".",
    [Parameter(Mandatory = $false)]
    [Alias("boost_grace_period", "BoostGracePeriod", "BoostGracePeriodMs")]
    [Nullable[int]]$boost_grace_period_ms = $null,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArgs
)

# Parse any grace period flags or values from remaining arguments
if ($RemainingArgs) {
    for ($i = 0; $i -lt $RemainingArgs.Count; $i++) {
        $arg = $RemainingArgs[$i]
        if ($arg -match '^--?bo+st_grace_period(_ms)?=(?<val>\d+)$') {
            $boost_grace_period_ms = [int]$Matches['val']
        } elseif ($arg -match '^--?bo+st_grace_period(_ms)?$') {
            if ($i + 1 -lt $RemainingArgs.Count -and $RemainingArgs[$i + 1] -match '^\d+$') {
                $boost_grace_period_ms = [int]$RemainingArgs[++$i]
            }
        } elseif ($arg -match '^\d+$' -and $null -eq $boost_grace_period_ms) {
            $boost_grace_period_ms = [int]$arg
        }
    }
}

# Resolve full path to target directory or file
$TargetPath = Resolve-Path $Path -ErrorAction SilentlyContinue
if (-not $TargetPath -or -not (Test-Path $TargetPath)) {
    Write-Output "Path does not exist: $Path"
    exit 1
}

# Locate Python executable
$PythonPaths = @(
    (Join-Path $PSScriptRoot "venv\Scripts\python.exe"),
    (Join-Path $PSScriptRoot ".venv\Scripts\python.exe")
)

$PythonCmd = "python"
foreach ($Path in $PythonPaths) {
    if (Test-Path $Path) {
        $PythonCmd = $Path
        break
    }
}

# Set PYTHONPATH to src folder to ensure local imports work
$env:PYTHONPATH = Join-Path $PSScriptRoot "src"

$ExtraArgs = @()
if ($null -ne $boost_grace_period_ms) {
    $ExtraArgs += @("--boost_grace_period_ms", "$boost_grace_period_ms")
}

& $PythonCmd -m lfdata.verify_all $TargetPath @ExtraArgs


