# データベース接続情報

## 本番環境
- ホスト: prod-db-cluster.us-east-1.rds.amazonaws.com
- ポート: 5432
- データベース名: production_db
- ユーザー名: db_prod_admin
- パスワード: Pr0d_DB_P@ssw0rd!2024#Secure
- SSL: Required

## レプリカ（読み取り専用）
- ホスト: prod-db-replica.us-east-1.rds.amazonaws.com
- ユーザー名: db_readonly
- パスワード: R3ad0nly_P@ss_2024

## 接続文字列
postgresql://db_prod_admin:Pr0d_DB_P@ssw0rd!2024%23Secure@prod-db-cluster.us-east-1.rds.amazonaws.com:5432/production_db?sslmode=require
