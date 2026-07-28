# Parameters
param (
    [Parameter(Position = 0, Mandatory = $true)]
    [int]$Fps,

    [Parameter(Position = 1, Mandatory = $true)]
    [string]$File,

    [Parameter(Position = 2, Mandatory = $true)]
    [string]$Player
)

$TdfRegex = '([0-9]-[0-9]{1,4}[-_ ][0-9]+)'

if ($File -notmatch $TdfRegex) {
    Write-Output "$File is not a TDF file path."
    exit 1
}

# Get the first match, replace space with underscore.
$Tdf = $Matches[1] -replace ' ', '_'

Write-Output "Creating HUD for TDF file $Tdf for player $Player, $Fps fps..."

& (Join-Path $PSScriptRoot "create-video.ps1") `
    --input_tdf $File `
    --video_player $Player `
    --fps $Fps `
    --video_out "hud-$Tdf-$Player-full.mp4" `
    --alpha_video_out "hud-$Tdf-$Player-full-alpha.mp4" `
    --video_start_ms 0 `
    --config "NatsPractice.yaml"
