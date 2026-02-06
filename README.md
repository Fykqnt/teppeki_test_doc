# Japanese PII Redactor

日本語文書向けの個人情報（PII）秘匿化ツールです。Microsoft Presidioをベースに、日本語特有のパターン（氏名、住所、電話番号、マイナンバーなど）に対応しています。

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install presidio-analyzer presidio-anonymizer spacy
```

### 2. 日本語NLPモデルのダウンロード

```bash
python -m spacy download ja_core_news_lg
```

## 使い方

### 秘匿化の実行

```bash
# test_md/内のMarkdownファイルを秘匿化し、redacted/に出力
python -m redactor.redactor

# カスタムディレクトリを指定
python -m redactor.redactor --input <入力ディレクトリ> --output <出力ディレクトリ>

# 処理ファイル数を制限（動作確認用）
python -m redactor.redactor --limit 5
```

### 出力形式

秘匿化されたPIIは `<エンティティ名N>` 形式に置換されます。

```
# 入力例
氏名: 山田太郎
電話番号: 03-1234-5678

# 出力例
氏名: <PERSON1>
電話番号: <PHONE_NUMBER1>
```

## 精度検証

### 評価スクリプトの実行

秘匿化ロジックの精度（Precision, Recall, F1）と処理速度を測定できます。

```bash
# 全テストファイルで評価
python -m redactor.evaluate

# ファイル数を制限して評価
python -m redactor.evaluate --limit 10
```

### 評価指標

| 指標 | 説明 |
|------|------|
| Precision | 検出したPIIのうち、正しく検出できた割合 |
| Recall | 実際のPIIのうち、検出できた割合 |
| F1-Score | PrecisionとRecallの調和平均 |

評価結果は `evaluation_results.txt` に詳細が保存されます。

## 設定のカスタマイズ

精度向上のためのパラメータは `redactor/config.py` で調整できます。

| パラメータ | 説明 | デフォルト値 |
|-----------|------|-------------|
| `DEFAULT_SCORE_THRESHOLD` | 検出の閾値（高いほど厳密） | 0.85 |
| `TARGET_ENTITIES` | 検出対象のエンティティ一覧 | PERSON, ORG, PHONE_NUMBER など |
| `CONTEXT_WORDS` | コンテキスト単語（周辺にあるとスコア向上） | 各エンティティごとに定義 |
| `COMMON_JAPANESE_WORDS` | 除外する一般的な日本語単語 | 情報, 記録, 設定 など |

### 閾値の調整例

```python
# redactor/config.py

# 検出漏れを減らしたい場合（Recall向上）
DEFAULT_SCORE_THRESHOLD = 0.75

# 誤検出を減らしたい場合（Precision向上）
DEFAULT_SCORE_THRESHOLD = 0.90
```

## 対応エンティティ

- `PERSON` - 氏名（漢字・ローマ字）
- `ORG` / `ORGANIZATION` - 組織名
- `LOCATION` - 住所
- `PHONE_NUMBER` - 電話番号
- `EMAIL_ADDRESS` - メールアドレス
- `CREDIT_CARD` - クレジットカード番号
- `MY_NUMBER` - マイナンバー
- `DRIVERS_LICENSE` - 運転免許証番号
- `PASSPORT` - パスポート番号
- `BANK_ACCOUNT` - 口座番号
- `TAX_NUMBER` - 納税者番号（インボイス登録番号）
- `PASSWORD` - パスワード
- `SECRET_KEY` - APIキー・シークレットキー
- `CERTIFICATE` - 証明書・秘密鍵
- `SECURITY_CODE` - セキュリティコード
- `PIN` - 暗証番号

## ディレクトリ構成

```
.
├── redactor/
│   ├── redactor.py   # メインの秘匿化ロジック
│   ├── config.py     # 設定ファイル
│   └── evaluate.py   # 精度評価スクリプト
├── test_md/          # テスト用Markdownファイル
└── redacted/         # 秘匿化後の出力（自動生成）
```
