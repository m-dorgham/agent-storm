import yaml
from pathlib import Path

def load_config(config_path: str = "config.yaml") -> dict:
    """Load YAML config into a dictionary."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
