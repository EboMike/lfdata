# lfdata

A Python project for managing LF data, sourced from TDF files.

## How to use it

If you're using a prebuild executable, go to the
[usage instructions](docs/usage.md) to find out how to create a video.

## Setup

Before running the tool, you should set up a Python virtual environment and install the required dependencies. 

> [!IMPORTANT]
> Python virtual environments are **not** cross-platform. A virtual environment created under Windows contains Windows binaries and will not run under WSL or Linux. If you use both Windows and WSL, create separate environments (e.g., `venv` for Windows, and `venv-wsl` for WSL/Linux).

### Automated Setup (Recommended)

You can automatically set up the virtual environment and install the package with dev dependencies in editable mode using the provided setup scripts:

* **On Windows (CMD / PowerShell)**:
  ```cmd
  setup.bat
  ```
* **On WSL / Linux / macOS**:
  ```bash
  chmod +x setup.sh
  ./setup.sh
  ```

### Manual Setup

If you prefer to set up the environment manually:

#### 1. Create a Virtual Environment

* **On Windows**:
  ```powershell
  python -m venv venv
  ```
* **On WSL / Linux**:
  ```bash
  python3 -m venv venv-wsl
  ```

#### 2. Activate the Virtual Environment

* **On Windows (CMD/PowerShell)**:
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
* **On WSL / Linux**:
  ```bash
  source venv-wsl/bin/activate
  ```
* **On Git Bash / macOS**:
  ```bash
  source venv/bin/activate
  ```

#### 3. Install Dependencies

Once activated, install the required dependencies:
```bash
pip install -r requirements.txt
```
Or by installing the package in editable mode with development dependencies:
```bash
pip install -e .[dev]
```


## Running the Tool

You can run the tool using the provided launcher scripts, which automatically configure the Python environment and run within the virtual environment:

### On Windows (CMD / PowerShell)
```cmd
run.bat --input_tdf assets/sm5_sanitized.tdf --print_replay
```

### On Bash (Git Bash / Linux / macOS)
```bash
./run.sh --input_tdf assets/sm5_sanitized.tdf --print_replay
```

## Options
* `--input_tdf <path>`: (Required) Path to the TDF file.
* `--print_replay`: (Optional) Prints all parsed game replay events to stdout.

## Nicer projects
If you want to see actual artisanal organic lf-based code instead of this
slop, check out:
- https://github.com/spookybear0/laserforce_ranking
- https://github.com/zmaniacz/lfstats-next
