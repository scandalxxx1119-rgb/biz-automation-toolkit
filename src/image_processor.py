"""画像一括加工モジュール（リサイズ / 透かし / 形式変換）。

config の image_processor セクションに従い、入力フォルダ内の画像を
順に加工して出力フォルダへ保存する。各処理は個別に on/off できる。
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Tuple

from PIL import Image

# 処理対象とする画像拡張子
SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}

# 透かしロゴの貼り付け位置 -> 計算用キー
_POSITIONS = {
    "top_left",
    "top_right",
    "bottom_left",
    "bottom_right",
    "center",
}


def _apply_resize(img: Image.Image, cfg: Dict[str, Any]) -> Image.Image:
    """リサイズを適用する。"""
    mode = cfg.get("mode", "keep_aspect")
    only_shrink = cfg.get("only_shrink", True)
    w, h = img.size

    if mode == "by_ratio":
        ratio = float(cfg.get("ratio", 1.0))
        new_size = (max(1, int(w * ratio)), max(1, int(h * ratio)))

    elif mode == "exact":
        new_size = (int(cfg.get("max_width", w)), int(cfg.get("max_height", h)))

    else:  # keep_aspect
        max_w = int(cfg.get("max_width", w))
        max_h = int(cfg.get("max_height", h))
        scale = min(max_w / w, max_h / h)
        if only_shrink:
            scale = min(scale, 1.0)
        new_size = (max(1, int(w * scale)), max(1, int(h * scale)))

    if only_shrink and mode != "by_ratio":
        if new_size[0] >= w and new_size[1] >= h:
            return img  # 拡大になる場合は何もしない

    return img.resize(new_size, Image.LANCZOS)


def _paste_position(
    base_size: Tuple[int, int],
    logo_size: Tuple[int, int],
    position: str,
    margin: int,
) -> Tuple[int, int]:
    """透かしの貼り付け座標(左上)を計算する。"""
    bw, bh = base_size
    lw, lh = logo_size
    if position == "top_left":
        return margin, margin
    if position == "top_right":
        return bw - lw - margin, margin
    if position == "bottom_left":
        return margin, bh - lh - margin
    if position == "center":
        return (bw - lw) // 2, (bh - lh) // 2
    # default: bottom_right
    return bw - lw - margin, bh - lh - margin


def _apply_watermark(
    img: Image.Image,
    cfg: Dict[str, Any],
    logger: logging.Logger,
) -> Image.Image:
    """透かしロゴを合成する。logo が無ければ元画像をそのまま返す。"""
    logo_path = cfg.get("logo_path", "")
    if not logo_path or not os.path.exists(logo_path):
        logger.warning("    透かしロゴが見つからないためスキップ: %s", logo_path)
        return img

    base = img.convert("RGBA")
    logo = Image.open(logo_path).convert("RGBA")

    # ロゴを元画像幅に対する scale 比率にリサイズ
    scale = float(cfg.get("scale", 0.2))
    target_w = max(1, int(base.width * scale))
    ratio = target_w / logo.width
    logo = logo.resize((target_w, max(1, int(logo.height * ratio))), Image.LANCZOS)

    # 透明度を適用（既存アルファに opacity を乗算）
    opacity = float(cfg.get("opacity", 0.5))
    if opacity < 1.0:
        alpha = logo.getchannel("A").point(lambda a: int(a * opacity))
        logo.putalpha(alpha)

    pos = _paste_position(
        base.size,
        logo.size,
        cfg.get("position", "bottom_right"),
        int(cfg.get("margin", 20)),
    )

    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    layer.paste(logo, pos, logo)
    return Image.alpha_composite(base, layer)


def _save_image(
    img: Image.Image,
    src_name: str,
    output_dir: str,
    cfg: Dict[str, Any],
) -> str:
    """形式変換しつつ保存し、保存先パスを返す。"""
    stem = os.path.splitext(src_name)[0]
    suffix = cfg.get("filename_suffix", "")
    to_format = cfg.get("to_format", "keep").lower()

    if to_format == "keep":
        out_ext = os.path.splitext(src_name)[1].lower()
    elif to_format in ("jpg", "jpeg"):
        out_ext = ".jpg"
    else:
        out_ext = f".{to_format}"

    out_name = f"{stem}{suffix}{out_ext}"
    out_path = os.path.join(output_dir, out_name)

    save_kwargs: Dict[str, Any] = {}
    if out_ext in (".jpg", ".jpeg"):
        # JPEG は透過を持てないので白背景に合成
        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            rgba = img.convert("RGBA")
            background.paste(rgba, mask=rgba.getchannel("A"))
            img = background
        else:
            img = img.convert("RGB")
        save_kwargs["quality"] = int(cfg.get("jpg_quality", 85))
        save_kwargs["optimize"] = True

    img.save(out_path, **save_kwargs)
    return out_path


def process_images(
    config: Dict[str, Any],
    logger: logging.Logger,
) -> Dict[str, int]:
    """画像一括加工を実行する。

    Args:
        config: マージ済みの全体設定。
        logger: ログ出力用ロガー。

    Returns:
        処理件数の集計 dict（processed / skipped / errors）。
    """
    cfg = config["image_processor"]
    general = config["general"]
    dry_run = general.get("dry_run", False)

    input_dir = cfg["input_dir"]
    output_dir = cfg["output_dir"]
    resize_cfg = cfg["resize"]
    wm_cfg = cfg["watermark"]
    convert_cfg = cfg["convert"]

    stats = {"processed": 0, "skipped": 0, "errors": 0}

    logger.info("=" * 60)
    logger.info("【画像加工】開始  入力: %s", input_dir)
    if dry_run:
        logger.info("  ※ dry_run モード: 実際の保存は行いません")

    if not os.path.isdir(input_dir):
        logger.error("  入力フォルダが存在しません: %s", input_dir)
        stats["errors"] += 1
        return stats

    files = sorted(
        f for f in os.listdir(input_dir)
        if os.path.splitext(f)[1].lower() in SUPPORTED_EXTS
    )
    if not files:
        logger.warning("  対象画像がありません。")
        return stats

    if not dry_run:
        os.makedirs(output_dir, exist_ok=True)

    for filename in files:
        src = os.path.join(input_dir, filename)
        try:
            applied = []
            with Image.open(src) as opened:
                img = opened.copy()

                if resize_cfg.get("enabled", False):
                    before = img.size
                    img = _apply_resize(img, resize_cfg)
                    applied.append(f"resize{before}->{img.size}")

                if wm_cfg.get("enabled", False):
                    img = _apply_watermark(img, wm_cfg, logger)
                    applied.append("watermark")

                if convert_cfg.get("enabled", False) or True:
                    # 保存は常に行う（convert.enabled=false でも keep 形式で保存）
                    save_cfg = dict(convert_cfg)
                    if not convert_cfg.get("enabled", False):
                        save_cfg["to_format"] = "keep"

                    if dry_run:
                        out_path = os.path.join(output_dir, filename)
                    else:
                        out_path = _save_image(img, filename, output_dir, save_cfg)
                    applied.append(f"save->{os.path.basename(out_path)}")

            logger.info("  [OK] %s  (%s)", filename, ", ".join(applied))
            stats["processed"] += 1

        except Exception as exc:  # 1枚の失敗で全体を止めない
            logger.error("  エラー: %s (%s)", filename, exc)
            stats["errors"] += 1

    logger.info(
        "【画像加工】完了  処理: %d / スキップ: %d / エラー: %d",
        stats["processed"],
        stats["skipped"],
        stats["errors"],
    )
    return stats
