# Apple証明書自動更新プロジェクト仕様書

## 概要
Apple Distribution証明書の更新をGitHub Actionsで自動化するプロジェクト
ブランチごとに異なる環境（PRD/UAT）の証明書を管理可能

## 主要要件

### 1. 証明書管理
- **対象証明書**: Apple Distribution証明書
- **更新タイミング**: 有効期限の30日前から更新開始
- **リトライ機能**: 更新失敗時のリトライ機能を実装

### 2. ストレージ
- **証明書の保存先**: AWS Secrets Manager
- **API認証情報の保存先**: AWS Secrets Manager
  - App Store Connect API Key ID
  - Issuer ID
  - 秘密鍵（.p8ファイル）

### 3. Apple Developer Portal連携
- **認証方式**: App Store Connect API Key（後日作成予定）
- **対象アプリ**: リポジトリ内に存在するアプリのみ
- **Bundle ID取得**: プロジェクトファイル（.xcodeproj等）から自動取得
- **環境別Bundle ID**: 
  - mainブランチ: 本番用Bundle ID（例: com.example.app）
  - developブランチ: UAT用Bundle ID（例: com.example.app.uat）

### 4. 実行スケジュール
- **定期実行**: 月1回、証明書の有効期限をチェック
- **手動実行**: GitHub Actionsのworkflow_dispatchに対応

### 5. 通知
- **成功時**: Slack通知
- **失敗時**: Slack通知

## 技術スタック
- GitHub Actions
- AWS SDK（Secrets Manager連携）
- App Store Connect API
- Slack Webhook API

## 環境管理
- **ブランチと環境のマッピング**:
  - mainブランチ → Production環境
  - developブランチ → UAT環境
- **環境別のシークレット管理**:
  - API認証情報: `apple-certificate-update/api-credentials-{環境}`
  - 証明書: `apple-certificate-update/distribution-certificate-{環境}`
- **設定ファイル**: `config/environments.json`で環境設定を管理

## セキュリティ考慮事項
- すべての機密情報はAWS Secrets Managerで管理
- GitHub Actions実行環境からのみアクセス可能
- 最小権限の原則に基づいたIAMロール設定
- 環境ごとに独立したシークレットで分離

## 今後の実装タスク
1. App Store Connect API Keyの作成と設定
2. AWS Secrets Managerのセットアップ
3. Bundle ID自動取得機能の実装
4. 証明書更新ロジックの実装
5. Slack通知機能の実装
6. GitHub Actionsワークフローの作成
7. エラーハンドリングとリトライ機能の実装