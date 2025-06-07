# GitHub Actions ワークフロー説明

## update-certificates.yml

Apple Distribution証明書を自動更新するためのGitHub Actionsワークフローです。

### 実行タイミング
- **定期実行**: 毎月1日の午前9時（JST）
- **手動実行**: workflow_dispatchで任意のタイミングで実行可能
  - `force_update`オプション: 有効期限に関わらず強制的に証明書を更新

### ジョブ構成

#### 1. check-and-update-certificates
メインの証明書チェック・更新ジョブ
- Bundle IDをXcodeプロジェクトから自動取得
- AWS Secrets ManagerからAPI認証情報を取得
- 証明書の有効期限をチェック（30日前から更新）
- 必要に応じて証明書を更新
- 更新した証明書をAWS Secrets Managerにアップロード
- Slackに成功/失敗を通知

#### 2. retry-update
メインジョブが失敗した場合のリトライジョブ
- 最大3回まで自動リトライ
- リトライ間隔は5分、10分、15分と段階的に増加
- 3回失敗した場合は手動介入が必要な旨をSlackに通知

### 必要なSecrets
- `AWS_ACCESS_KEY_ID`: AWS アクセスキー
- `AWS_SECRET_ACCESS_KEY`: AWS シークレットキー
- `SLACK_WEBHOOK_URL`: Slack通知用のWebhook URL

### 依存ツール
- Python 3.11
- boto3 (AWS SDK)
- Fastlane (証明書管理用)
- requests, pyyaml