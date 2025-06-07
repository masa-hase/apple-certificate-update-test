# Apple Certificate Auto-Update

Apple Distribution証明書を自動更新するGitHub Actionsワークフローです。証明書の有効期限を定期的にチェックし、期限が近づいたら自動的に更新します。

## 機能

- 📅 月次での証明書有効期限チェック（毎月1日）
- 🔄 有効期限30日前から自動更新
- 🌳 ブランチごとの環境分離（main: Production, develop: UAT）
- 🔐 AWS Secrets Managerでの安全な証明書管理
- 📱 Bundle IDの自動取得（Xcodeプロジェクトから）
- 💬 Slack通知（成功・失敗時）
- 🔁 失敗時の自動リトライ（最大3回）

## セットアップ手順

### 1. App Store Connect API Keyの作成

1. [App Store Connect](https://appstoreconnect.apple.com/)にログイン
2. 「ユーザーとアクセス」→「キー」→「App Store Connect API」へ移動
3. 「+」ボタンをクリックして新しいキーを作成
   - 名前: `GitHub Actions Certificate Update`
   - アクセス: `Admin`（証明書の作成・削除権限が必要）
4. 以下の情報を保存：
   - **Issuer ID**: ページ上部に表示
   - **Key ID**: 作成したキーのID
   - **秘密鍵（.p8ファイル）**: ダウンロード（再ダウンロード不可）

### 2. AWS Secrets Managerの設定

環境ごとに以下のシークレットを作成：

#### Production環境（mainブランチ用）
```bash
# API認証情報
aws secretsmanager create-secret \
  --name "apple-certificate-update/api-credentials-prd" \
  --secret-string '{
    "key_id": "YOUR_KEY_ID",
    "issuer_id": "YOUR_ISSUER_ID",
    "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
  }'
```

#### UAT環境（developブランチ用）
```bash
# API認証情報
aws secretsmanager create-secret \
  --name "apple-certificate-update/api-credentials-uat" \
  --secret-string '{
    "key_id": "YOUR_KEY_ID",
    "issuer_id": "YOUR_ISSUER_ID",
    "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
  }'
```

### 3. GitHub Secretsの設定

リポジトリの「Settings」→「Secrets and variables」→「Actions」で以下を設定：

| Secret名 | 説明 |
|---------|------|
| `AWS_ACCESS_KEY_ID` | AWS IAMユーザーのアクセスキー |
| `AWS_SECRET_ACCESS_KEY` | AWS IAMユーザーのシークレットキー |
| `SLACK_WEBHOOK_URL` | Slack通知用のWebhook URL |

### 4. AWS IAMポリシーの設定

GitHub ActionsがAWS Secrets Managerにアクセスするための最小権限ポリシー：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:CreateSecret",
        "secretsmanager:UpdateSecret"
      ],
      "Resource": [
        "arn:aws:secretsmanager:ap-northeast-1:*:secret:apple-certificate-update/*"
      ]
    }
  ]
}
```

### 5. 環境設定のカスタマイズ

`config/environments.json`を編集して環境設定をカスタマイズ：

```json
{
  "environments": {
    "main": {
      "name": "Production",
      "bundle_id_suffix": "",
      "secret_name_suffix": "prd",
      "certificate_name": "Distribution - Production"
    },
    "develop": {
      "name": "UAT",
      "bundle_id_suffix": ".uat",
      "secret_name_suffix": "uat",
      "certificate_name": "Distribution - UAT"
    }
  }
}
```

## 使用方法

### 自動実行（承認フロー付き）
1. 毎月1日の午前9時（JST）に自動実行
2. 証明書の有効期限が30日以内の場合、Slackに承認リクエストを送信
3. Slackで承認手順を確認してGitHub Actionsで手動承認
4. 承認後に証明書更新を実行

### 手動実行
1. GitHubリポジトリの「Actions」タブを開く
2. 「Certificate Update with Approval」ワークフローを選択
3. 「Run workflow」をクリック
4. オプション：
   - `force_update`: チェックすると有効期限に関わらず強制更新
   - `environment`: 特定の環境を指定（main/develop）
   - `approval_action`: 承認操作（approve/reject）※承認時のみ使用
   - `approval_id`: 承認ID※承認時のみ使用

### 承認フロー
1. **証明書チェック**: ワークフローが証明書の有効期限をチェック
2. **Slack通知**: 更新が必要な場合、Slackに承認リクエストを送信
3. **手動承認**: Slackのリンクから GitHub Actions で手動承認
   - `approval_action`: `approve` (承認) または `reject` (拒否)
   - `environment`: 対象環境
   - `approval_id`: Slackで提供された承認ID
4. **証明書更新**: 承認された場合のみ証明書更新を実行

## ワークフローの動作

1. **環境判定**: 実行ブランチまたは手動指定から環境を決定
2. **Bundle ID取得**: Xcodeプロジェクトから自動取得し、環境に応じたサフィックスを付与
3. **API認証情報取得**: AWS Secrets Managerから環境別の認証情報を取得
4. **証明書チェック**: 現在の証明書の有効期限を確認
5. **証明書更新**: 必要に応じて新しい証明書を作成
6. **保存**: 新しい証明書をAWS Secrets Managerに保存
7. **通知**: Slackに結果を通知

## トラブルシューティング

### 証明書が見つからない
- Bundle IDが正しいか確認
- App Store ConnectでアプリのBundle IDが登録されているか確認

### API認証エラー
- API Keyの権限が`Admin`になっているか確認
- Secrets Managerの認証情報が正しくJSON形式で保存されているか確認

### AWS権限エラー
- IAMユーザーに必要な権限が付与されているか確認
- リージョン設定（デフォルト: ap-northeast-1）が正しいか確認

## ライセンス

MIT License