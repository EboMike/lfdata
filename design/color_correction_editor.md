# Color Correction Editor

## Overview

The color correction editor is a separate tool with an UI that allows for editing settings that affect hoe
ffmpeg processes the GoPro footage.

There are two settings that can be adjusted:

* The LUT, which can be imported and exported as a .cube file.
* Noise reduction settings.

## The UI

The window has multiple tabs to indicate the stages of the process.

### First tab: Reference video

On the top, there is a button to load a reference video file. Pressing this button will allow the user
to pick a file. After selecting one, the tool will use this video as the new reference file. It will
load the file to check how long it is.

Once the file has been successfully checked, new elements appear underneath the button:

There is a horizontal bar that represents the timeline (the left end is the beginning of the video,
the right end is the end of the video). Underneath the bar is a still image showing the video at the
currently selected time of the video in the timeline.

Clicking on the timeline will change the still image to the video image at that point.

Clicking and dragging across the timeline will create a range, i.e. it highlights a part of the timeline.
A button next to the timeline allows the user to add the current range to the list of reference ranges.

There is a list of ranges that have been added, with a button to delete the currently selected range.

## Second tab: Color Correction

More information will be added here. This tab is empty for now.
This tab can only be selected if at least one range of the video has been added.
