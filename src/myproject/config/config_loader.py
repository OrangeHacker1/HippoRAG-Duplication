from pathlib import Path
import yaml

_DEFAULT_CONFIG = Path(__file__).parent / "config.yaml"


def load_config(path=None):
    p = Path(path) if path else _DEFAULT_CONFIG
    with open(p, "r") as f:
        return yaml.safe_load(f)
