TDF_REGEX="([0-9]-[0-9]{1,4}[-_ ][0-9]+)"

FILE=$1
PLAYER=$2

if [[ ! $FILE =~ $TDF_REGEX ]]; then
	echo "$FILE is not a TDF file path."
	exit 1
fi

# Get the first match, replace space with underscore.
TDF="${BASH_REMATCH[1]// /_}"


echo "Creating HUD for TDF file $TDF for player $PLAYER"

VIDEO_OUT=hud-$TDF-$PLAYER-full.mp4
ALPHA_OUT=hud-$TDF-$PLAYER-full-alpha.mp4

# venv-wsl/bin/python3 -m lfdata --input_tdf "$FILE" --video_player=$PLAYER --config=LaserForcePro.yaml --image-at=105000
venv-wsl/bin/python3 -m lfdata --input_tdf "$FILE" --video_player=$PLAYER --video_out=$VIDEO_OUT --alpha_video_out=$ALPHA_OUT --config=LaserForcePro.yaml

cp $VIDEO_OUT /mnt/e/Videos/Editing/MiniProjects/Laserforce/LaserForcePro
cp $ALPHA_OUT /mnt/e/Videos/Editing/MiniProjects/Laserforce/LaserForcePro
rm -f $VIDEO_OUT
rm -f $ALPHA_OUT


