"""ログ出力の共通設定。

コンソールとファイルの両方へ出力する。ファイルは log_dir 配下に
実行日時付きで保存され、「いつ・何件・どこへ・どんなエラー」を後から追える。
"""

from __future__ import annotations

import datetime
import logging
import os


def setup_logger(log_dir: str = "logs", level: str = "INFO") -> logging.Logger:
    """ツール共通のロガーを構築して返す。

    Args:
        log_dir: ログファイルの保存先フォルダ。
        level: ログレベル文字列（DEBUG / INFO / WARNING / ERROR）。

    Returns:
        設定済みの Logger。
    """
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger("biz_automation")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()  # 二重登録を防ぐ

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # コンソール出力
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    # ファイル出力（実行ごとにファイルを分ける）
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(log_dir, f"run_{timestamp}.log")
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    logger.info("ログ開始: %s", log_path)
    return logger
