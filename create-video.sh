TDF_REGEX="([0-9]-[0-9]{1,4}[-_ ][0-9]+)"

FPS=$1
FILE=$2
PLAYER=$3

if [[ ! $FILE =~ $TDF_REGEX ]]; then
	echo "$FILE is not a TDF file path."
	exit 1
fi

# Get the first match, replace space with underscore.
TDF="${BASH_REMATCH[1]// /_}"


echo "Creating HUD for TDF file $TDF for player $PLAYER, $FPS fps..."

venv-wsl/bin/python3 -m lfdata \
	--input_tdf "$FILE" \
	--video_player=$PLAYER \
	--fps=$FPS \
	--video_out=hud-$TDF-$PLAYER-full.mp4 \
	--alpha_video_out=hud-$TDF-$PLAYER-full-alpha.mp4 \
	--video_start_ms=0 \
	--config=LaserForcePro.yaml
