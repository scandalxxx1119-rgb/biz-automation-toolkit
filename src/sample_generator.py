"""デモ用のサンプルファイル・画像・透かしロゴを生成する。

`python main.py gen-samples` から呼ばれ、すぐにツールを試せる状態を作る。
"""

from __future__ import annotations

import logging
import os

from PIL import Image, ImageDraw, ImageFont


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """利用可能なフォントを返す（無ければデフォルト）。"""
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def generate_samples(base_dir: str, logger: logging.Logger) -> None:
    """サンプル一式を生成する。

    Args:
        base_dir: プロジェクトのルートディレクトリ。
        logger: ログ出力用ロガー。
    """
    files_dir = os.path.join(base_dir, "samples", "input", "files")
    images_dir = os.path.join(base_dir, "samples", "input", "images")
    assets_dir = os.path.join(base_dir, "assets")
    for d in (files_dir, images_dir, assets_dir):
        os.makedirs(d, exist_ok=True)

    # --- サンプルファイル（振り分け・リネーム用）---
    sample_files = {
        "report_A.txt": "サンプルテキスト：四半期レポート",
        "data_export.csv": "id,name,amount\n1,foo,1000\n2,bar,2000",
        "invoice_001.txt": "請求書サンプル：御請求金額 50,000円",
        "請求書_山田商事.txt": "請求書サンプル（日本語名）",
        "memo.md": "# メモ\n- やること1\n- やること2",
        "random_data.bin": "binary-ish placeholder",
    }
    for name, content in sample_files.items():
        path = os.path.join(files_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    logger.info("サンプルファイル %d 件を生成: %s", len(sample_files), files_dir)

    # --- サンプル画像（加工用）---
    swatches = [
        ("photo_sunset.jpg", (255, 140, 60), 1600, 1000),
        ("photo_ocean.jpg", (40, 120, 200), 2000, 1500),
        ("product_white.png", (235, 235, 235), 1200, 1200),
        ("banner_green.png", (70, 180, 110), 1800, 600),
    ]
    for name, color, w, h in swatches:
        img = Image.new("RGB", (w, h), color)
        draw = ImageDraw.Draw(img)
        font = _font(max(24, w // 20))
        label = f"SAMPLE {w}x{h}"
        draw.text((w // 20, h // 2), label, fill=(255, 255, 255), font=font)
        # 形式に合わせて保存
        img.save(os.path.join(images_dir, name))
    logger.info("サンプル画像 %d 枚を生成: %s", len(swatches), images_dir)

    # --- 透かしロゴ（透過PNG）---
    logo_path = os.path.join(assets_dir, "logo.png")
    logo = Image.new("RGBA", (400, 140), (0, 0, 0, 0))
    draw = ImageDraw.Draw(logo)
    draw.rounded_rectangle([0, 0, 399, 139], radius=20, fill=(20, 20, 20, 220))
    draw.text((28, 45), "YOUR LOGO", fill=(255, 255, 255, 255), font=_font(48))
    logo.save(logo_path)
    logger.info("透かしロゴを生成: %s", logo_path)

    logger.info("サンプル生成 完了。`python main.py all` で一括処理を試せます。")
