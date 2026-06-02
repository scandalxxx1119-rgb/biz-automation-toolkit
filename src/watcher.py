"""フォルダ監視モジュール。

入力フォルダを一定間隔でポーリングし、新しいファイルが置かれたら
ファイル整理 / 画像加工を自動実行する。外部ライブラリ不要の簡易実装。
（受託案件では watchdog 等への差し替えも容易な構造にしている）
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Callable, Dict, Set

from . import file_organizer, image_processor


def _snapshot(path: str) -> Set[str]:
    """フォルダ内のファイル一覧（スナップショット）を取得する。"""
    if not os.path.isdir(path):
        return set()
    return {
        f for f in os.listdir(path)
        if os.path.isfile(os.path.join(path, f))
    }


def watch(
    config: Dict[str, Any],
    logger: logging.Logger,
    interval: float = 3.0,
) -> None:
    """入力フォルダを監視し、変化があれば処理を実行する。

    Ctrl+C で停止するまで動き続ける。

    Args:
        config: マージ済みの全体設定。
        logger: ログ出力用ロガー。
        interval: ポーリング間隔（秒）。
    """
    watch_targets: Dict[str, Callable[[], Any]] = {}

    if config["file_organizer"].get("enabled", False):
        d = config["file_organizer"]["input_dir"]
        watch_targets[d] = lambda: file_organizer.organize_files(config, logger)

    if config["image_processor"].get("enabled", False):
        d = config["image_processor"]["input_dir"]
        watch_targets[d] = lambda: image_processor.process_images(config, logger)

    if not watch_targets:
        logger.error("監視対象がありません（file_organizer / image_processor が無効）")
        return

    logger.info("=" * 60)
    logger.info("【監視モード】開始（%.1f秒間隔, Ctrl+C で停止）", interval)
    for d in watch_targets:
        logger.info("  監視対象: %s", d)

    snapshots = {d: _snapshot(d) for d in watch_targets}

    try:
        while True:
            time.sleep(interval)
            for d, handler in watch_targets.items():
                current = _snapshot(d)
                added = current - snapshots[d]
                if added:
                    logger.info("変化を検知（%d 件の新規）: %s", len(added), d)
                    handler()
                snapshots[d] = _snapshot(d)
    except KeyboardInterrupt:
        logger.info("【監視モード】停止しました。")
