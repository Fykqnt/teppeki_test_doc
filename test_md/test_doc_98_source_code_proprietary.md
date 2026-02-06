# ソースコード管理台帳（極秘）

## プロジェクト情報
- プロジェクト名: SecurePayment System
- リポジトリ: https://git.company.com/secure-payment
- 管理者: 開発部長 高橋誠
- 機密レベル: レベル5（最高機密）

## アクセス権限者
### フルアクセス（読み取り・書き込み）
- 社員番号: E-2020-0123, 氏名: 山田太郎, 役職: リードエンジニア
- 社員番号: E-2021-0234, 氏名: 鈴木花子, 役職: シニアエンジニア
- 社員番号: E-2022-0345, 氏名: 田中一郎, 役職: エンジニア

### 読み取り専用
- 社員番号: E-2023-0456, 氏名: 佐藤次郎, 役職: QAエンジニア

## 重要ファイル
- /src/payment/crypto.py: 暗号化処理実装
- /src/payment/api_client.py: 決済API連携
- /config/production.env: 本番環境設定
  - API_KEY=pk_live_abc123def456
  - SECRET_KEY=sk_live_xyz789uvw012
  - DB_PASSWORD=Pr0d_DB_P@ss!2024

## コミット履歴
2024-01-24 山田太郎: セキュリティパッチ適用 (commit: a1b2c3d4)
2024-01-23 鈴木花子: 決済API v2.0対応 (commit: e5f6g7h8)

## セキュリティ設定
- 2要素認証: 必須
- SSH鍵認証: 必須
- IP制限: 社内ネットワークのみ
- ブランチ保護: main/productionブランチは承認必須

最終更新: 2024年1月25日
