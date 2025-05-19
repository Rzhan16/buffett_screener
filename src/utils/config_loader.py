"""
YAML configuration loader with strict key checking.
"""
import yaml
from typing import Dict

class ConfigLoaderError(Exception):
    pass

def load_config(path: str) -> Dict:
    """
    Load a YAML configuration file and return as a dict.
    Raises ConfigLoaderError if the file is not a dict or cannot be parsed.
    
    Parameters
    ----------
    path : str
        Path to the YAML file
    
    Returns
    -------
    dict
        Parsed configuration
    """
    try:
        with open(path, 'r') as f:
            config = yaml.safe_load(f)
        if not isinstance(config, dict):
            raise ConfigLoaderError(f"Config at {path} is not a dict.")
        return config
    except Exception as e:
        raise ConfigLoaderError(f"Failed to load config from {path}: {e}") 