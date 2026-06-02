"""ファイル整理モジュール（リネーム & 振り分け）。

config の file_organizer セクションに従って、入力フォルダ内のファイルを
リネームしつつ、ルールに基づいて出力フォルダ配下のサブフォルダへ振り分ける。
"""

from __future__ import annotations

import datetime
import logging
import os
import shutil
from typing import Any, Dict, List, Optional


def _build_new_name(
    original: str,
    index: int,
    rename_cfg: Dict[str, Any],
) -> str:
    """リネーム規則に従って新しいファイル名を組み立てる。

    Args:
        original: 元のファイル名（拡張子込み）。
        index: 0始まりの通し番号（連番付与に使う）。
        rename_cfg: config の rename セクション。

    Returns:
        新しいファイル名（拡張子込み）。
    """
    stem, ext = os.path.splitext(original)
    if rename_cfg.get("lowercase_ext", True):
        ext = ext.lower()

    sep = rename_cfg.get("separator", "_")
    parts: List[str] = []

    prefix = rename_cfg.get("prefix", "")
    if prefix:
        parts.append(str(prefix))

    date_str: Optional[str] = None
    if rename_cfg.get("add_date", False):
        date_str = datetime.datetime.now().strftime(
            rename_cfg.get("date_format", "%Y%m%d")
        )
    if date_str and rename_cfg.get("date_position", "prefix") == "prefix":
        parts.append(date_str)

    # 元のファイル名（stem）は常に残す
    parts.append(stem)

    if date_str and rename_cfg.get("date_position", "prefix") == "suffix":
        parts.append(date_str)

    suffix = rename_cfg.get("suffix", "")
    if suffix:
        parts.append(str(suffix))

    if rename_cfg.get("add_sequence", False):
        digits = int(rename_cfg.get("sequence_digits", 3))
        start = int(rename_cfg.get("sequence_start", 1))
        seq = str(start + index).zfill(digits)
        parts.append(seq)

    new_stem = sep.join(p for p in parts if p != "")
    return f"{new_stem}{ext}"


def _decide_dest(filename: str, sort_cfg: Dict[str, Any]) -> str:
    """振り分け規則に従って、振り分け先サブフォルダ名を決める。

    上から順にルールを評価し、最初にマッチしたものを採用する。
    どれにもマッチしなければ default_dest を返す。
    """
    name_lower = filename.lower()
    ext = os.path.splitext(filename)[1].lstrip(".").lower()

    for rule in sort_cfg.get("rules", []):
        exts = [e.lower().lstrip(".") for e in rule.get("match_extensions", [])]
        if exts and ext in exts:
            return rule.get("dest", "others")

        keywords = rule.get("match_name_contains", [])
        if keywords and any(kw.lower() in name_lower for kw in keywords):
            return rule.get("dest", "others")

    return sort_cfg.get("default_dest", "others")


def _unique_path(path: str) -> str:
    """同名ファイルが既に存在する場合、_2, _3 ... を付けて衝突を避ける。"""
    if not os.path.exists(path):
        return path
    stem, ext = os.path.splitext(path)
    counter = 2
    while True:
        candidate = f"{stem}_{counter}{ext}"
        if not os.path.exists(candidate):
            return candidate
        counter += 1


def organize_files(
    config: Dict[str, Any],
    logger: logging.Logger,
) -> Dict[str, int]:
    """ファイル整理（リネーム & 振り分け）を実行する。

    Args:
        config: マージ済みの全体設定。
        logger: ログ出力用ロガー。

    Returns:
        処理件数の集計 dict（processed / skipped / errors）。
    """
    cfg = config["file_organizer"]
    general = config["general"]
    dry_run = general.get("dry_run", False)
    copy_mode = general.get("copy_mode", True)

    input_dir = cfg["input_dir"]
    output_dir = cfg["output_dir"]
    rename_cfg = cfg["rename"]
    sort_cfg = cfg["sort"]

    stats = {"processed": 0, "skipped": 0, "errors": 0}

    logger.info("=" * 60)
    logger.info("【ファイル整理】開始  入力: %s", input_dir)
    if dry_run:
        logger.info("  ※ dry_run モード: 実際のファイル操作は行いません")

    if not os.path.isdir(input_dir):
        logger.error("  入力フォルダが存在しません: %s", input_dir)
        stats["errors"] += 1
        return stats

    files = sorted(
        f for f in os.listdir(input_dir)
        if os.path.isfile(os.path.join(input_dir, f))
    )
    if not files:
        logger.warning("  対象ファイルがありません。")
        return stats

    for index, filename in enumerate(files):
        src = os.path.join(input_dir, filename)
        try:
            # 1) リネーム
            if rename_cfg.get("enabled", False):
                new_name = _build_new_name(filename, index, rename_cfg)
            else:
                new_name = filename

            # 2) 振り分け先の決定
            if sort_cfg.get("enabled", False):
                dest_sub = _decide_dest(filename, sort_cfg)
                dest_dir = os.path.join(output_dir, dest_sub)
            else:
                dest_dir = output_dir

            dst = _unique_path(os.path.join(dest_dir, new_name))

            action = "コピー" if copy_mode else "移動"
            logger.info(
                "  [%s] %s -> %s",
                action,
                filename,
                os.path.relpath(dst, output_dir),
            )

            if not dry_run:
                os.makedirs(dest_dir, exist_ok=True)
                if copy_mode:
                    shutil.copy2(src, dst)
                else:
                    shutil.move(src, dst)

            stats["processed"] += 1

        except Exception as exc:  # 1ファイルの失敗で全体を止めない
            logger.error("  エラー: %s (%s)", filename, exc)
            stats["errors"] += 1

    logger.info(
        "【ファイル整理】完了  処理: %d / スキップ: %d / エラー: %d",
        stats["processed"],
        stats["skipped"],
        stats["errors"],
    )
    return stats
