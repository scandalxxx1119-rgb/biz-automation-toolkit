# 業務自動化ツール（ファイル整理 ＋ 画像一括加工）

ローカルで動く、**ファイル整理**と**画像一括加工**の自動化ツールです。
処理ルールはすべて `config.yaml` に集約しているため、**コードを書き換えずに**
設定だけで様々な業務に流用できます。受託案件の「自動化のベースがすでにあります」
というデモ・たたき台としてそのまま使えます。

---

## できること

### ① ファイル整理
- 指定フォルダ内のファイルを**一括処理**、または**監視して自動処理**
- ルールに基づく**リネーム**（プレフィックス／日付付与／連番付与／拡張子小文字化）
- **自動振り分け**（拡張子・ファイル名パターンで指定フォルダへ仕分け）

### ② 画像一括加工
- jpg / png / gif / webp / bmp を**一括加工**
- **リサイズ**（比率維持 / 指定サイズ固定 / 倍率指定）
- **透かしロゴの自動挿入**（位置・透明度・サイズ・余白を設定可能）
- **形式変換**（png → jpg など）と保存先指定

すべての処理は**個別に on/off** でき、案件ごとに必要な処理だけ組み合わせられます。
処理結果は**コンソールとログファイルの両方**に「何件・どこへ・エラーは何か」を記録します。

---

## セットアップ

必要なのは Python 3.9 以降です。

```bash
pip install -r requirements.txt
```

（依存は `Pillow`（画像処理）と `PyYAML`（設定読み込み）の2つだけです）

---

## クイックスタート（デモ）

```bash
# 1) デモ用のサンプルファイル・画像・ロゴを自動生成
python main.py gen-samples

# 2) ファイル整理＋画像加工をまとめて実行
python main.py all
```

実行後、`samples/output/` 配下に結果が出力されます。

```
samples/
├─ input/
│  ├─ files/     … 整理対象のサンプルファイル
│  └─ images/    … 加工対象のサンプル画像
└─ output/
   ├─ files/
   │  ├─ documents/   doc_20260602_report_A_005.txt   ← リネーム＋振り分け済み
   │  ├─ invoices/    doc_20260602_invoice_001_002.txt
   │  └─ others/
   └─ images/
      └─ photo_ocean_processed.jpg                    ← リサイズ＋透かし＋jpg変換済み
```

---

## コマンド一覧

| コマンド | 内容 |
|----------|------|
| `python main.py gen-samples` | デモ用サンプル一式を生成 |
| `python main.py organize`    | ファイル整理だけ実行 |
| `python main.py images`      | 画像加工だけ実行 |
| `python main.py all`         | 両方まとめて実行 |
| `python main.py watch`       | 入力フォルダを監視し、新規ファイルを自動処理（Ctrl+C で停止） |

### オプション

| オプション | 内容 |
|------------|------|
| `-c, --config <path>` | 使う設定ファイルを指定（既定: `config.yaml`）。案件ごとに設定を切り替えられる |
| `--interval <秒>`     | `watch` のポーリング間隔（既定: 3.0秒） |

```bash
# 案件Aの設定で実行
python main.py all -c configs/client_a.yaml

# まず動作確認だけしたい（後述の dry_run と併用）
python main.py organize -c configs/client_a.yaml
```

---

## 設定方法（`config.yaml`）

設定ファイルだけ編集すれば挙動が変わります。主要な項目を抜粋します。

### 共通

```yaml
general:
  dry_run: false    # true にすると「実際には変更せず、ログだけ出力」。本番前の確認に便利
  copy_mode: true   # true=元を残してコピー / false=移動（元ファイル削除）
  log_dir: logs
  log_level: INFO
```

### ファイル整理

```yaml
file_organizer:
  enabled: true
  input_dir: samples/input/files
  output_dir: samples/output/files

  rename:
    enabled: true
    prefix: "doc"          # 先頭に付ける文字
    add_date: true         # 日付を付与
    date_format: "%Y%m%d"
    add_sequence: true     # 連番を付与（001, 002, ...）
    sequence_digits: 3
    lowercase_ext: true    # 拡張子を小文字に統一

  sort:
    enabled: true
    # 上から順に評価し、最初にマッチした dest へ振り分ける。
    # ★ 名前ベースの特定ルールは、拡張子ベースの汎用ルールより前に置くこと。
    rules:
      - name: "画像"
        match_extensions: [jpg, png, gif, webp]
        dest: images
      - name: "請求書"
        match_name_contains: ["invoice", "請求"]
        dest: invoices
      - name: "ドキュメント"
        match_extensions: [pdf, docx, xlsx, txt, csv]
        dest: documents
    default_dest: others   # どのルールにもマッチしない場合
```

**リネーム結果の例**（`report_A.txt`、5番目のファイルの場合）:
`doc_20260602_report_A_005.txt`
（`prefix` + `日付` + `元名` + `連番` を `separator` でつないだもの）

### 画像一括加工

```yaml
image_processor:
  enabled: true
  input_dir: samples/input/images
  output_dir: samples/output/images

  resize:
    enabled: true
    mode: keep_aspect    # keep_aspect(比率維持) / exact(固定) / by_ratio(倍率)
    max_width: 1200
    max_height: 1200
    only_shrink: true    # 元より大きくしない

  watermark:
    enabled: true
    logo_path: assets/logo.png
    position: bottom_right   # top_left/top_right/bottom_left/bottom_right/center
    opacity: 0.5             # 0.0〜1.0
    scale: 0.2               # 元画像幅に対するロゴ幅の比率
    margin: 20               # 端からの余白(px)

  convert:
    enabled: true
    to_format: jpg       # jpg / png / webp / keep(元のまま)
    jpg_quality: 85
    filename_suffix: "_processed"
```

> JSON 派の方は `config.json` を作って `-c config.json` で渡すこともできます
> （拡張子で自動判別します）。

---

## 案件ごとのカスタマイズ手順

このツールを別業務に寄せる典型的な流れ:

1. **設定だけで足りる場合**（ほとんどのケース）
   `config.yaml` をコピーして `configs/client_x.yaml` を作り、
   入力／出力フォルダ・リネーム規則・振り分けルール・画像加工値を書き換える。
   実行時に `-c configs/client_x.yaml` を渡すだけ。

2. **新しい処理を足したい場合**
   各機能はモジュールに分かれています。

   | ファイル | 役割 |
   |----------|------|
   | `main.py`                  | コマンド受付（エントリーポイント） |
   | `src/config_loader.py`     | 設定の読み込み（YAML/JSON、デフォルト補完） |
   | `src/logger_setup.py`      | ログ出力（コンソール＋ファイル） |
   | `src/file_organizer.py`    | リネーム＋振り分け |
   | `src/image_processor.py`   | リサイズ／透かし／形式変換 |
   | `src/watcher.py`           | フォルダ監視 |
   | `src/sample_generator.py`  | デモ用サンプル生成 |

   例: 「画像にEXIF削除を追加したい」→ `image_processor.py` に関数を1つ足して
   `process_images()` の処理列に差し込み、`config.yaml` にスイッチを足すだけ。

3. **本番投入前の確認**
   `general.dry_run: true` にして実行すると、実ファイルを一切変更せず
   「何が・どこへ動くか」をログで確認できます。安全に動作検証してから本番へ。

---

## ログ

実行ごとに `logs/run_YYYYMMDD_HHMMSS.log` が作られ、処理内容・件数・エラーが
すべて残ります。コンソールにも同じ内容が表示されます。

```
2026-06-02 09:14:37 [INFO] 【ファイル整理】開始  入力: .../samples/input/files
2026-06-02 09:14:37 [INFO]   [コピー] invoice_001.txt -> invoices\doc_20260602_invoice_001_002.txt
2026-06-02 09:14:37 [INFO] 【ファイル整理】完了  処理: 6 / スキップ: 0 / エラー: 0
```

---

## 設計上のポイント（デモで説明できる強み）

- **設定とコードの分離**: 処理ルールは `config.yaml` に集約。非エンジニアでも編集可能。
- **モジュール分割**: 機能ごとに独立。案件に必要な処理だけ組み合わせられる。
- **安全機構**: `dry_run`（無変更確認）、`copy_mode`（移動 vs コピー）、
  出力先の同名ファイル自動リネーム（`_2`, `_3`…）で上書き事故を防止。
- **堅牢性**: 1ファイルの失敗で全体が止まらず、エラーはログに記録して処理を継続。
- **監視運用**: `watch` でフォルダ常駐の自動処理にも対応。
```
