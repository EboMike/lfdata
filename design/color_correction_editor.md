# Color Correction Editor

## Overview

The color correction editor is a separate tool with an UI that allows for editing settings that affect hoe
ffmpeg processes the GoPro footage.

There are two settings that can be adjusted:

* The LUT, which can be imported and exported as a .cube file.
* Noise reduction settings.

## General rule

All expensive operations must run in worker threads. The UI must remain responsive.

## The UI

The window has multiple tabs to indicate the stages of the process.

### First tab: Reference video

#### Video picker

On the top, there is a button to load a reference video file. Pressing this button will allow the user
to pick a file. After selecting one, the tool will use this video as the new reference file. It will
load the file to check how long it is.

Once the file has been successfully checked, new elements appear underneath the button:

#### Timeline bar

There is a horizontal bar that represents the timeline (the left end is the beginning of the video,
the right end is the end of the video). Underneath the bar is a still image showing the video at the
currently selected time of the video in the timeline.

Clicking on the timeline will change the still image to the video image at that point.

Clicking and dragging across the timeline will create a range, i.e. it highlights a part of the timeline.
A button next to the timeline allows the user to add the current range to the list of reference ranges.

There is a list of ranges that have been added, with a button to delete the currently selected range.

#### Color averages bar

Underneath the timeline bar is another non-interactive bar of the same width and height. This bar shows
the average color for the video. Specifically:

For every X coordinate, the bar will show color information for the first frame in the video that matches
the timeline position at that X coordinate. Within this X coordinate, every pixel will show the average
color for all pixels along the Y axis relative to the bar's height. Meaning that the top pixel of the bar
corresponds to the top pixel of the video frame. The bottom pixel corresponds to a bottom pixel of the
video frame.

Because this is an expensive computation, it needs to be done in a separate thread. Every 5 seconds, the
UI should be updated with the data that has been computed so far.

### A node on the reference video

The list of ranges combined result in one reference video, meaning that whenever "reference video" is
mentioned here, it is a single video that comprises all the ranges from the list taken from the source
video strung together.

## Second tab: Color Correction

On the top, this tab has a visualization of the current LUT. The LUT is derived from the contents of a
`.cube` file. If none was loaded, it is a default LUT that does not modify the image in any way.

Below are controls to modify the LUT, together by clicking on the LUT panel
itself. A button ("Auto Detect") triggers the automatic color correction
detection from `ColorAnalyzer` in a background worker thread and applies the
suggested parameters directly to the active LUT and controls.

To address laser tag GoPro footage that is dark with bright lights, the controls
include:
* **Brightness & Contrast**: Global offset and mid-point contrast.
* **Black Level**: Lifts or cuts the black pedestal floor ($1 - x$), bringing
  hidden details out of pure pitch black without washing out highlights.
* **Deep Shadows**: Concentrated lift on near-black shadow tones (peaking in the
  ~17% luminance range) to boost arena walls, floor obstacles, and dark suits.
* **Shadows**: Lifts mid-shadow tones while tapering off towards highlights.
* **Highlights**: Adjusts bright highlights to recover detail or tone down
  intense reflections.
* **Gamma**: Midtone gamma power curve ($v^{1/\gamma}$) boosting dark and
  middle tones while pinning peak white at 1.0.
* **Dark Expansion**: Controls the curvature and intensity of the dark-region
  gamma boost to brighten dark areas more aggressively.
* **Light Rolloff**: Soft shoulder compression ($C^1$ continuous $\tanh$ knee)
  preventing bright vest LEDs, laser phasers, and base targets from harshly
  clipping.
* **Saturation, Temperature & Tint**: Color balance adjustments.

Underneath is a side-by-side comparison of the original video and the processed
video with the LUT applied. In both cases, the video is the reference video.
There is a play button that will make it play in a loop. The play button will
toggle with a pause button.

### Third tab: Noise reduction

On the top, there are settings that control noise reduction using options that are available in
ffmpeg.

Underneath is a side-by-side comparison of the video without (left) and with (right)
noise reduction applied. In both cases, the reference video with color correction applied
will be used as the base.

There is a play button that will make it play in a loop. The play button will
toggle with a pause button.

### Fourth tab: Export

The fourth tab has a button to save a test video. This will open a Save File dialog
to pick the destination file. After confirming, the tool will use ffmpeg to create
one video that combines all the selected ranges from the source video.

The fourth tab also contains a read-only text field with the noise reduction arguments
to plug into ffmpeg.
