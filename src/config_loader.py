"""設定ファイル(config.yaml / config.json)の読み込みを担う。

YAML と JSON の両方に対応し、拡張子で自動判別する。
非エンジニアが編集する前提なので、欠けているキーはデフォルト値で補い、
極力エラーを出さずに動くようにしている。
"""

from __future__ import annotations

import copy
import json
import os
from typing import Any, Dict

import yaml


# 設定が一部欠けていても動くようにするためのデフォルト値。
# config.yaml に書かれた値で上書きされる。
DEFAULTS: Dict[str, Any] = {
    "general": {
        "dry_run": False,
        "copy_mode": True,
        "log_dir": "logs",
        "log_level": "INFO",
    },
    "file_organizer": {
        "enabled": False,
        "input_dir": "samples/input/files",
        "output_dir": "samples/output/files",
        "rename": {
            "enabled": False,
            "prefix": "",
            "suffix": "",
            "add_date": False,
            "date_format": "%Y%m%d",
            "date_position": "prefix",
            "add_sequence": False,
            "sequence_digits": 3,
            "sequence_start": 1,
            "lowercase_ext": True,
            "separator": "_",
        },
        "sort": {
            "enabled": False,
            "rules": [],
            "default_dest": "others",
        },
    },
    "image_processor": {
        "enabled": False,
        "input_dir": "samples/input/images",
        "output_dir": "samples/output/images",
        "resize": {
            "enabled": False,
            "mode": "keep_aspect",
            "max_width": 1200,
            "max_height": 1200,
            "ratio": 0.5,
            "only_shrink": True,
        },
        "watermark": {
            "enabled": False,
            "logo_path": "assets/logo.png",
            "position": "bottom_right",
            "opacity": 0.5,
            "scale": 0.2,
            "margin": 20,
        },
        "convert": {
            "enabled": False,
            "to_format": "keep",
            "jpg_quality": 85,
            "filename_suffix": "_processed",
        },
    },
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """base を override で再帰的に上書きしたコピーを返す。"""
    result = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_config(path: str) -> Dict[str, Any]:
    """設定ファイルを読み込み、デフォルト値とマージして返す。

    Args:
        path: config.yaml または config.json のパス。

    Returns:
        マージ済みの設定 dict。
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"設定ファイルが見つかりません: {path}")

    ext = os.path.splitext(path)[1].lower()
    with open(path, "r", encoding="utf-8") as f:
        if ext in (".yaml", ".yml"):
            user_config = yaml.safe_load(f) or {}
        elif ext == ".json":
            user_config = json.load(f)
        else:
            raise ValueError(
                f"対応していない設定ファイル形式です: {ext}（.yaml / .yml / .json のみ）"
            )

    return _deep_merge(DEFAULTS, user_config)
