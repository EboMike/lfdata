# Usage

## Prerequisites

* Grab a binary from the [releases page](https://github.com/EboMike/lfdata/releases).
  Extract the contents wherever you want. You'll be running the tool in a command line
  from within this directory.
* Be sure to install ffmpeg. If you don't already have it, check out
  the [ffmpeg website](https://ffmpeg.org/).
* Install any font you'd like to use. IMPORTANT: The default fonts are not included,
  so you'll need to download them from the web, or choose different ones with the
  configuration file.
* Have the TDF file somewhere on your file system.

## Customizing (optional)

If you want to change the layout of the display, you can create a
configuration file. Check out `video_configuration_example.yaml` for
inspiration. You can move it to move, resize, or disable various
elements, change fonts, and add a couple of custom text strings.

## Testing it out

Creating an entire video takes a while. Try a single image first.

Run the tool like this:

```shell
lfdata --input_tdf <tdf_file> --video_player=<name of player> --image_at=<time in milliseconds>
```

Example:

```shell
lfdata --input_tdf 4_43_12345678.tdf --video_player=CmdrTaco --image_at=50000
```

This will take the TDF file, render an image from the point of view of player `CmdrTaco`, 50
seconds into the game (50000ms).

If the player name contains spaces or special characters, leave them out.

## Generating a video

Looks good? Let's create a video.

The basic way is like this:

```shell
lfdata --input_tdf 4_43_12345678.tdf --video_player CmdrTaco --fps=60 --video_out=hud.mp4 --alpha_video_out=hud-alpha.mp4
```

This will render an entire video of the game. Actually, there will be two videos: `hud.mp4` will be the overlay itself
with black background, and `hud-alpha.mp4` will be the alpha channel. See below in "video formats" on what alternatives
there are, and how to actually use these videos.

## Some more options

* **--video_start_ms**: The game time in milliseconds where to start the video. Defaults to 0.
* **--video_end_ms**: The game time in milliseconds where to end the video. Defaults to 10 seconds after the end of the
  game.
* **--no_pipe**: Create separate images and then use `ffmpeg` later to turn those into a video. Choose this if the
  streaming video creating doesn't work, although this is a bit slower (and puts a bunch of temporary files on your
  drive).
* **--config**: Path of a config file, if you actually read the "customization"
  section above.

## Video formats

### MP4

This is the recommended way. Creates two separate videos, one for the overlay and one for the alpha channel.

#### Using in Premiere

Put your actual footage on V1. Put the overlay in V2. Put the alpha video in V3.
Add the `Track Matte Key` effect to V2. In its settings, set `Matte` to
`Video 3`, and set `Composite Using` to `Matte Luma`.

### WebM

This is a very space-efficient format, but has no native support in many applications, such as Premiere. (There is a
webm plug-in, but it doesn't support alpha).

Enable `webm` by choosing a `--video_out` file name ending with `.webm`.

### QuickTime

Generates a ProRes 4444 video, which has its alpha channel baked in. This is a very high-fidelity format. It's also
huge. You won't have fun working with it.

## Merging Videos with `hudmerge`

Once you have generated your `hud.mp4` and `hud-alpha.mp4` files, you can merge
them directly onto your GoPro base video using `hudmerge`:

```shell
hudmerge gopro.mp4 hud.mp4 hud-alpha.mp4 -o final.mp4
```

Features:
* Automatic resolution scaling if GoPro resolution differs from HUD resolution.
* Automatic length sync: truncates to the shorter of the two sources.
* Fades out video and audio over the last 5 seconds.

