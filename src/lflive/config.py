"""Configuration loader and schema for the lflive service.

This module provides data structures and file parsing routines to configure
network ports, preroll buffers, database paths, and external API endpoints
from YAML configuration files.

Usage example:
    from lflive.config import LFLiveConfig, load_config

    config = load_config('configs/lflive.yaml')
    print(config.tdf_port, config.consumer_port)
"""

import dataclasses
from pathlib import Path
import yaml


@dataclasses.dataclass
class LFLiveConfig:
    """Runtime configuration settings for lflive.

    Attributes:
        tdf_port: Port to listen on for incoming TDF data.
        consumer_port: Port to listen on for consumer connections.
        lfstats_url: Base endpoint URL for the lfstats REST API.
        database_path: Relative path to the SQLite persistence file.
        preroll_ms: Preroll delay in milliseconds.
        log_tdf: Flag to print all received TDF lines to standard output.
        log_output: Flag to print all generated broadcast lines to stdout.
    """

    tdf_port: int = 8000
    consumer_port: int = 8001
    lfstats_url: str = 'https://lfstats.com/api/'
    database_path: str = 'lflive.db'
    preroll_ms: int = 0
    log_tdf: bool = False
    log_output: bool = False


def load_config(path: str | Path | None = None) -> LFLiveConfig:
    """Loads lflive configuration from a YAML file if specified.

    If the path is None or the target file does not exist, a default
    configuration instance is returned.

    Args:
        path: Optional path to a YAML configuration file.

    Returns:
        LFLiveConfig: Initialized configuration instance.

    Raises:
        yaml.YAMLError: If the file exists but contains invalid YAML.

    Usage example:
        cfg = load_config('lflive_config.yaml')
        print(cfg.tdf_port)
    """
    if path is None:
        return LFLiveConfig()

    file_path = Path(path)
    if not file_path.is_file():
        return LFLiveConfig()

    with open(file_path, 'r', encoding='utf-8') as f:
        raw_data = yaml.safe_load(f)

    if not isinstance(raw_data, dict):
        return LFLiveConfig()

    return LFLiveConfig(
        tdf_port=int(raw_data.get('tdf_port', 8000)),
        consumer_port=int(raw_data.get('consumer_port', 8001)),
        lfstats_url=str(
            raw_data.get('lfstats_url', 'https://lfstats.com/api/')
        ),
        database_path=str(raw_data.get('database_path', 'lflive.db')),
        preroll_ms=int(raw_data.get('preroll_ms', 0)),
        log_tdf=bool(raw_data.get('log_tdf', False)),
        log_output=bool(raw_data.get('log_output', False)),
    )
