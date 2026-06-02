#!/usr/bin/env python
"""業務自動化ツール エントリーポイント（CLI）。

使い方:
    python main.py gen-samples          # デモ用サンプルを生成
    python main.py organize             # ファイル整理だけ実行
    python main.py images               # 画像加工だけ実行
    python main.py all                  # 両方まとめて実行
    python main.py watch                # 入力フォルダを監視して自動処理
    python main.py all -c other.yaml    # 別の設定ファイルで実行（案件切替）

設定はすべて config.yaml 側に寄せているため、通常はコードを編集せず
このコマンドと設定ファイルだけで運用できる。
"""

from __future__ import annotations

import argparse
import os
import sys

# Windows コンソールで日本語ログが文字化けしないよう UTF-8 に統一する
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

# src パッケージを import できるようにする
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from src import (  # noqa: E402
    config_loader,
    file_organizer,
    image_processor,
    logger_setup,
    sample_generator,
    watcher,
)


def _resolve_paths(config: dict) -> None:
    """設定内の相対パスをプロジェクトルート基準の絶対パスに変換する。

    どのフォルダから実行しても同じ場所を指すようにするため。
    """
    def to_abs(p: str) -> str:
        return p if os.path.isabs(p) else os.path.join(BASE_DIR, p)

    g = config["general"]
    g["log_dir"] = to_abs(g["log_dir"])

    fo = config["file_organizer"]
    fo["input_dir"] = to_abs(fo["input_dir"])
    fo["output_dir"] = to_abs(fo["output_dir"])

    ip = config["image_processor"]
    ip["input_dir"] = to_abs(ip["input_dir"])
    ip["output_dir"] = to_abs(ip["output_dir"])
    ip["watermark"]["logo_path"] = to_abs(ip["watermark"]["logo_path"])


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ファイル整理＋画像一括加工の業務自動化ツール",
    )
    parser.add_argument(
        "command",
        choices=["gen-samples", "organize", "images", "all", "watch"],
        help="実行するコマンド",
    )
    parser.add_argument(
        "-c", "--config",
        default=os.path.join(BASE_DIR, "config.yaml"),
        help="設定ファイルのパス（既定: config.yaml）",
    )
    parser.add_argument(
        "--interval", type=float, default=3.0,
        help="watch コマンドのポーリング間隔（秒, 既定: 3.0）",
    )
    args = parser.parse_args()

    config = config_loader.load_config(args.config)
    _resolve_paths(config)

    logger = logger_setup.setup_logger(
        log_dir=config["general"]["log_dir"],
        level=config["general"]["log_level"],
    )
    logger.info("設定ファイル: %s", args.config)

    if args.command == "gen-samples":
        sample_generator.generate_samples(BASE_DIR, logger)
        return 0

    summary = {}
    if args.command in ("organize", "all"):
        if config["file_organizer"].get("enabled", False):
            summary["file_organizer"] = file_organizer.organize_files(config, logger)
        else:
            logger.info("file_organizer は無効化されています（config）")

    if args.command in ("images", "all"):
        if config["image_processor"].get("enabled", False):
            summary["image_processor"] = image_processor.process_images(config, logger)
        else:
            logger.info("image_processor は無効化されています（config）")

    if args.command == "watch":
        watcher.watch(config, logger, interval=args.interval)
        return 0

    # 最終サマリ
    logger.info("=" * 60)
    logger.info("■ 実行サマリ")
    total_err = 0
    for name, stats in summary.items():
        logger.info(
            "  %s: 処理 %d / スキップ %d / エラー %d",
            name, stats["processed"], stats["skipped"], stats["errors"],
        )
        total_err += stats["errors"]
    logger.info("完了しました。")
    return 1 if total_err else 0


if __name__ == "__main__":
    sys.exit(main())
