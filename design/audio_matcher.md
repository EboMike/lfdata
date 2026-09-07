# Audio Matcher

The audio matcher module locates occurrences of a reference sound effect
(such as the game start buzzer, arena horns, chimes, or the countdown klaxon)
within video or audio recordings. Its primary purpose is to automatically
synchronize POV video footage (such as GoPro recordings) with LF game data
and replay timelines.

## Overview and How It Works

Synchronizing POV game footage with game replay data requires identifying the
exact moment the game begins. Because POV recordings typically contain loud
arena music, player shouting, running noise, and arena reverberation, simple
volume peak detection is insufficient.

The audio matcher uses 2D spectrogram template matching combined with
bandpass filtering and human voice rejection to robustly pinpoint reference
sound effects.

The matching pipeline follows these stages:

### 1. Audio Extraction and Normalization

When given a video or audio file, `AudioMatcher` invokes `ffmpeg` to extract
the audio stream and convert it to:
* Single channel (mono)
* Target sampling rate (default: 22,050 Hz)
* 32-bit floating point normalized audio samples

Optionally, search window boundaries (`start_ms` and `end_ms`) can be passed
to restrict decoding to a specific section of the recording. This avoids
extracting and processing large video files in their entirety.

### 2. Spectrogram Generation

The normalized audio signal is transformed into a power spectrogram using the
Short-Time Fourier Transform (STFT) via `scipy.signal.spectrogram`:
* `sample_rate`: 22,050 Hz
* `n_fft`: 1,024 samples (frequency window)
* `hop_length`: 256 samples (~11.61 ms per temporal frame)
* Overlap: 768 samples (`n_fft - hop_length`, 75% overlap)

This produces a 2D matrix representing frequency energy over time frames for
both the target recording and the reference sound template.

### 3. Frequency Bandpass Filtering

Audio effects typically concentrate energy within specific frequency bands.
For example, the SM5 General Quarters countdown alert operates predominantly
between 1,400 Hz and 2,400 Hz.

* If `freq_min_hz` and `freq_max_hz` are specified, the spectrograms are
  cropped to retain only frequencies within this active band.
* If omitted, the matcher analyzes the reference sound power spectrum and
  automatically determines frequency bounds (selecting bins containing at
  least 1% of peak power).

Restricting matching to the relevant frequency band filters out low-frequency
rumble, bass music, and high-frequency noise.

### 4. 2D Normalized Cross-Correlation

Once cropped to the target frequency band, magnitude spectrograms are
compared using OpenCV template matching:

```python
correlation_matrix = cv2.matchTemplate(
    mag_target, mag_ref, cv2.TM_CCOEFF_NORMED
)
```

This slides the 2D reference template across the target spectrogram over time,
generating a correlation series where scores range from -1.0 to 1.0.

### 5. Vocal and Speech Rejection (Vocal Penalty)

POV recordings frequently contain shouting, teammate call-outs, and heavy
breathing close to the microphone. Even within a filtered frequency band,
energetic shouts can produce correlation spikes.

To reject false positives caused by human speech, the matcher computes a
vocal penalty factor (0.0 to 1.0):
* Human vocal fundamentals and formant energy concentrate heavily between
  150 Hz and the lower bound of the target frequency band (`freq_min_hz`).
* The matcher computes the ratio of in-band energy to low-frequency energy
  for each temporal window in the target audio.
* If a window is dominated by low-frequency vocal energy relative to the
  reference sound, a penalty factor scales down the correlation score:

$$\text{final\_score} = \max(0, \text{correlation}) \times \text{penalty}$$

This suppresses false peaks caused by players shouting during the countdown.

### 6. Peak Detection via Non-Maximum Suppression (NMS)

To isolate distinct sound events and prevent duplicate triggers:
* Only peaks exceeding the detection `threshold` (default: 0.2) are evaluated.
* Non-Maximum Suppression (NMS) ensures detections are separated by at least
  `min_interval_ms` (defaults to the duration of the reference sound).
* Matches are returned sorted by confidence score descending.

---

## How to Run Audio Matching

The audio matcher can be invoked via platform launcher scripts, the installed
CLI entry point, or the Python API.

### Launcher Scripts

Convenience wrapper scripts are provided in the repository root:

* **PowerShell (Windows)**:
  ```powershell
  .\match-audio.ps1 <video_path> <reference_wav> [options]
  ```
* **Bash (Linux / macOS / WSL)**:
  ```bash
  ./match-audio.sh <video_path> <reference_wav> [options]
  ```
* **Command Prompt (Windows)**:
  ```cmd
  match-audio.bat <video_path> <reference_wav> [options]
  ```

### CLI Command (`match-audio`)

When installed in the virtual environment (`pip install -e .[video]`), the
command `match-audio` is available directly:

```bash
# Using a sound configuration YAML file (recommended)
match-audio <video_or_audio> --config <config_yaml> [options]

# Using a reference sound WAV directly
match-audio <video_or_audio> <reference_sound> [options]
```

Alternatively, run via the Python module:

```bash
python -m lfdata.video.audio_matcher <video_or_audio> \
  --config <config_yaml> [options]
```

### Command-Line Arguments

| Argument | Type | Default | Description |
|---|---|---|---|
| `video` | Path | (Required) | Target video or audio file to analyze. |
| `reference` | Path | `None` | Reference WAV (optional if `--config` used). |
| `--config` | Path | `None` | Path to YAML sound definition file. |
| `--threshold` | Float | Config/0.2 | Minimum confidence score (0.0 to 1.0). |
| `--min-interval-ms` | Int | Ref duration | Minimum ms between detections. |
| `--start-ms` | Int | `None` | Search start offset in milliseconds. |
| `--end-ms` | Int | `None` | Search end offset in milliseconds. |
| `--freq-min` | Float | Config/Auto | Lower frequency cutoff in Hz. |
| `--freq-max` | Float | Config/Auto | Upper frequency cutoff in Hz. |
| `--max-matches` | Int | `None` | Maximum number of matches to return. |
| `--json` | Flag | `False` | Output results as structured JSON. |

### Usage Examples

#### 1. Matching Using a Configuration File
Run matching using a tuned YAML definition (such as `sm5_game_start.yaml`):

```bash
./match-audio.sh gopro_game1.mp4 \
  --config configs/audio/sm5_game_start.yaml
```

Output:
```
Found 1 match(es):
  1. 20240 ms (00:20.240) - confidence: 0.5842
```

#### 2. Matching with Direct WAV File
Pass the reference sound WAV directly on the command line:

```bash
./match-audio.sh gopro_game1.mp4 "assets/sounds/countdown.wav"
```

#### 3. Restricting Search Window with Configuration
Search only the first 60 seconds with threshold override:

```bash
./match-audio.sh gopro_game1.mp4 \
  --config configs/audio/sm5_game_start.yaml \
  --start-ms 0 --end-ms 60000 --threshold 0.25
```

#### 4. Structured JSON Output
Generate JSON output suitable for automated processing pipelines:

```bash
./match-audio.sh gopro_game1.mp4 \
  --config configs/audio/sm5_game_start.yaml --json
```

Output:
```json
[
  {
    "timestamp_ms": 20240,
    "timestamp_sec": 20.24,
    "confidence": 0.5842
  }
]
```

### Python API Usage

The matcher can be imported and executed programmatically using either direct
parameters or a configuration file:

```python
from pathlib import Path
from lfdata.video.audio_matcher import AudioMatcher

matcher = AudioMatcher(sample_rate=22050, hop_length=256, n_fft=1024)

# Using a YAML configuration file:
results = matcher.match_with_config(
    video_or_audio_path='pov_video.mp4',
    config='configs/audio/sm5_game_start.yaml',
    start_ms=0,
    end_ms=60000,
)

# Or matching with explicit parameters:
results = matcher.match(
    video_or_audio_path='pov_video.mp4',
    reference_sound_path='countdown.wav',
    threshold=0.25,
    freq_min_hz=1400.0,
    freq_max_hz=2400.0,
    start_ms=0,
    end_ms=60000,
)

for match in results:
    print(
        f'Match at {match.timestamp_ms} ms '
        f'({match.timestamp_sec:.2f}s) '
        f'confidence: {match.confidence:.4f}'
    )
```

---

## How to Tune Audio Matching

Acoustic characteristics differ significantly across arenas due to speaker
placement, background music volume, and microphone enclosures. Tuning
determines optimal frequency cutoffs and detection thresholds across a set
of benchmark test cases to maximize accuracy and minimize false detections.

### The Audio Benchmark System

The benchmark system consists of three main components:
1. `SoundDefinition`: Defines a sound effect, its reference WAV file, frequency
   cutoffs, default threshold, and associated test cases.
2. `AudioTestCase`: An individual test video with a known ground-truth onset
   timestamp, acceptable error tolerance in milliseconds, and optional search
   window boundaries.
3. `AudioBenchmarkRunner`: Evaluates accuracy across test cases, computes
   timing discrepancies, and performs automated grid-search optimization.

### YAML Configuration Format

Sound definitions and test cases are stored in YAML files. See
`configs/audio/sm5_game_start.example.yaml` for a reference template:

```yaml
name: sm5_game_start
description: SM5 pre-game countdown klaxon / General Quarters alert
reference_sound_path: path/to/General Quarters.wav
freq_min_hz: 1400.0
freq_max_hz: 2400.0
threshold: 0.2
test_cases:
  - video_path: path/to/game_pov.mp4
    expected_timestamp_ms: 20200
    tolerance_ms: 500
    search_start_ms: 0
    search_end_ms: 60000
    description: Example POV video game 1 start
```

#### Configuration Field Reference

* `name`: Unique identifier for the sound effect.
* `description`: Explanatory notes about the sound.
* `reference_sound_path`: Path to reference audio WAV file (relative paths are
  resolved relative to the directory containing the YAML file).
* `freq_min_hz`: Lower frequency cutoff in Hz (e.g. `1400.0`).
* `freq_max_hz`: Upper frequency cutoff in Hz (e.g. `2400.0`).
* `threshold`: Detection confidence threshold (0.0 to 1.0, e.g. `0.2`).
* `test_cases`: List of test recordings:
  * `video_path`: Path to example video or audio file.
  * `expected_timestamp_ms`: Ground-truth sound onset time in milliseconds.
  * `tolerance_ms`: Acceptable error window around expected time (default: 500).
  * `search_start_ms`: Optional search window start offset in ms.
  * `search_end_ms`: Optional search window end offset in ms.
  * `description`: Optional notes regarding camera angle, arena, or noise level.

### Running Benchmark Evaluations

To evaluate existing parameters against configured test cases, run the
`evaluate` command:

* **PowerShell (Windows)**:
  ```powershell
  .\tune-audio.ps1 evaluate configs/audio/my_sound.yaml
  ```
* **Bash (Linux / macOS / WSL)**:
  ```bash
  ./tune-audio.sh evaluate configs/audio/my_sound.yaml
  ```
* **CLI Command**:
  ```bash
  python -m lfdata.video.audio_benchmark evaluate configs/audio/my_sound.yaml
  ```

#### Evaluation Overrides
You can test parameter adjustments without modifying the YAML file:

```bash
./tune-audio.sh evaluate configs/audio/my_sound.yaml \
  --freq-min 1200 --freq-max 2200 --threshold 0.25
```

#### Evaluation Output
The runner displays pass/fail status, timing error, and false positive metrics:

```
Sound: sm5_game_start
Passed: 3/3 (100.0%)
Mean Error: 42.3 ms

Case Details:
  1. [PASS] expected: 20200ms, detected: 20240ms
     (err: +40ms, conf: 0.5842) - Match detected within tolerance.
  2. [PASS] expected: 15450ms, detected: 15495ms
     (err: +45ms, conf: 0.4910) - Match detected within tolerance.
  3. [PASS] expected: 31100ms, detected: 31142ms
     (err: +42ms, conf: 0.6120) - Match detected within tolerance.
```

### Automated Parameter Tuning (`tune`)

The `tune` command executes an automated grid search across candidate
frequency bounds and thresholds:

* **PowerShell (Windows)**:
  ```powershell
  .\tune-audio.ps1 tune configs/audio/my_sound.yaml --save
  ```
* **Bash (Linux / macOS / WSL)**:
  ```bash
  ./tune-audio.sh tune configs/audio/my_sound.yaml --save
  ```

Passing `--save` updates the YAML configuration file directly with the best
discovered parameters.

#### Optimization Scoring Function
The tuning algorithm evaluates candidate combinations and ranks them using a
composite scoring formula:

1. **Accuracy**: Strongly prioritizes maximizing test cases passing within
   `tolerance_ms` (+1,000 points per 1.0 accuracy).
2. **Mean Timing Error**: Penalizes timing jitter and error (-0.1 points per
   millisecond of absolute error).
3. **True Match Confidence**: Rewards high confidence on verified detections
   (+10 points per confidence score).
4. **False Positive Margin**: Rewards configurations with a wide safety margin
   between true detections and out-of-tolerance noise (+20 points per margin).

---

## Step-by-Step Workflow for a New Sound Effect

To create and tune a detector for a new sound effect:

1. **Extract Reference Audio**:
   Extract a clean 1–3 second audio snippet of the sound effect from arena
   footage or audio files. Save it as an uncompressed 16-bit PCM WAV file.

2. **Collect Benchmark Videos**:
   Assemble 3–5 representative POV recordings recorded under varying arena
   conditions (different background music, shouting, volume levels).

3. **Identify Ground Truth**:
   Open each video in a video editor or audio tool (such as Audacity) and note
   the exact millisecond timestamp where the sound begins.

4. **Create Configuration File**:
   Create `configs/audio/<sound_name>.yaml` by copying the example template
   from `configs/audio/sm5_game_start.example.yaml` and adding your test cases.

5. **Run Auto-Tuning**:
   Execute the tuning script to discover optimal cutoffs and threshold:
   ```bash
   ./tune-audio.sh tune configs/audio/<sound_name>.yaml --save
   ```

6. **Verify and Deploy**:
   Review the resulting configuration and run `evaluate` to verify high
   confidence margins:
   ```bash
   ./tune-audio.sh evaluate configs/audio/<sound_name>.yaml
   ```
