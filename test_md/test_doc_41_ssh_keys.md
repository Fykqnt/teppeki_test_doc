# SSH鍵管理情報

## サーバー接続情報
- ホスト名: prod-web-01.example.com
- IPアドレス: 192.168.1.100
- ポート: 22
- ユーザー名: deploy

## SSH公開鍵
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC8hkx... deploy@workstation

## SSH秘密鍵（パスフレーズ保護）
-----BEGIN RSA PRIVATE KEY-----
Proc-Type: 4,ENCRYPTED
DEK-Info: AES-128-CBC,1234567890ABCDEF
[暗号化された秘密鍵]
-----END RSA PRIVATE KEY-----

パスフレーズ: MyS3cur3P@ssphrase!2024
作成日: 2024年1月10日
有効期限: 2025年1月10日
