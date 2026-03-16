import os
import yaml
from app.models import AppConfig


def load_config(path: str) -> AppConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    cfg = AppConfig.model_validate(raw)

    os.makedirs(cfg.global_config.output_dir, exist_ok=True)
    os.makedirs(cfg.global_config.state_dir, exist_ok=True)
    os.makedirs(cfg.global_config.snapshot_dir, exist_ok=True)
    return cfg