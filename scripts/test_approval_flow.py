#!/usr/bin/env python3
"""
承認フローをテストするためのスクリプト（実際のAPI呼び出しなし）
"""
import os
import sys
import json
from datetime import datetime, timedelta


def simulate_certificate_check():
    """証明書チェックをシミュレート"""
    print("🔍 証明書チェックをシミュレーション中...")
    
    # テスト用のデータを生成
    environment = os.environ.get('ENVIRONMENT', 'main')
    bundle_id = f"com.example.testapp{'.uat' if environment == 'develop' else ''}"
    
    # 有効期限を25日後に設定（30日以内なので更新対象）
    expiry_date = datetime.now() + timedelta(days=25)
    days_remaining = 25
    
    print(f"✅ シミュレーション結果:")
    print(f"  環境: {environment}")
    print(f"  Bundle ID: {bundle_id}")
    print(f"  有効期限: {expiry_date.strftime('%Y-%m-%d')}")
    print(f"  残り日数: {days_remaining}日")
    print(f"  更新必要: はい（30日以内）")
    
    return {
        'needs_update': True,
        'environment': environment,
        'bundle_id': bundle_id,
        'expiry_date': expiry_date.strftime('%Y-%m-%d'),
        'days_remaining': days_remaining
    }


def test_approval_request_generation():
    """承認リクエスト生成をテスト"""
    print("\n📝 承認リクエスト生成をテスト中...")
    
    # 承認IDを生成
    approval_id = f"test-{int(datetime.now().timestamp())}"
    
    cert_data = simulate_certificate_check()
    cert_data['approval_id'] = approval_id
    
    print(f"✅ 承認リクエストデータ:")
    for key, value in cert_data.items():
        print(f"  {key}: {value}")
    
    return cert_data


def simulate_slack_notification(approval_data):
    """Slack通知をシミュレート（実際には送信しない）"""
    print("\n💬 Slack通知をシミュレーション中...")
    
    repo_name = os.environ.get('GITHUB_REPOSITORY', 'user/apple-certificate-update-test')
    workflow_url = f"https://github.com/{repo_name}/actions/workflows/approval-certificate-update.yml"
    
    print(f"📤 以下の内容でSlackに送信されます:")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"🔐 Apple証明書更新の承認リクエスト")
    print(f"")
    print(f"環境: {approval_data['environment'].upper()}")
    print(f"Bundle ID: {approval_data['bundle_id']}")
    print(f"有効期限: {approval_data['expiry_date']}")
    print(f"残り日数: {approval_data['days_remaining']}日")
    print(f"")
    print(f"承認ID: {approval_data['approval_id']}")
    print(f"")
    print(f"🔗 承認・実行手順:")
    print(f"1. GitHub Actionsワークフローを開く:")
    print(f"   {workflow_url}")
    print(f"2. 「Run workflow」ボタンをクリック")
    print(f"3. 以下の値を入力:")
    print(f"   • approval_action: approve")
    print(f"   • environment: {approval_data['environment']}")
    print(f"   • approval_id: {approval_data['approval_id']}")
    print(f"4. 「Run workflow」で実行")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    return True


def save_test_approval_data(approval_data):
    """テスト用の承認データを保存"""
    print("\n💾 承認データを保存中...")
    
    approval_info = {
        'approval_id': approval_data['approval_id'],
        'environment': approval_data['environment'],
        'bundle_id': approval_data['bundle_id'],
        'expiry_date': approval_data['expiry_date'],
        'days_remaining': approval_data['days_remaining'],
        'requested_at': datetime.utcnow().isoformat(),
        'status': 'pending',
        'test_mode': True
    }
    
    os.makedirs('/tmp', exist_ok=True)
    with open('/tmp/approval_request.json', 'w') as f:
        json.dump(approval_info, f, indent=2)
    
    print(f"✅ 承認データを /tmp/approval_request.json に保存しました")
    
    # GitHub Actions の出力として設定
    if 'GITHUB_OUTPUT' in os.environ:
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f"needs_update=true\n")
            f.write(f"approval_id={approval_data['approval_id']}\n")
            f.write(f"environment={approval_data['environment']}\n")
            f.write(f"bundle_id={approval_data['bundle_id']}\n")
            f.write(f"expiry_date={approval_data['expiry_date']}\n")
            f.write(f"days_remaining={approval_data['days_remaining']}\n")


def show_next_steps(approval_data):
    """次のテスト手順を表示"""
    print(f"\n🎯 次のテスト手順:")
    print(f"")
    print(f"1. 📋 承認フローをテスト:")
    print(f"   - GitHub Actions で「Certificate Update with Approval」を開く")
    print(f"   - 「Run workflow」をクリック")
    print(f"   - 以下を入力:")
    print(f"     approval_action: approve")
    print(f"     environment: {approval_data['environment']}")
    print(f"     approval_id: {approval_data['approval_id']}")
    print(f"")
    print(f"2. ❌ 拒否テスト:")
    print(f"   - 上記と同じ手順で approval_action に 'reject' を入力")
    print(f"")
    print(f"3. 🔍 検証テスト:")
    print(f"   - 間違った approval_id や environment でテスト")
    print(f"   - エラーハンドリングを確認")


def main():
    print("🧪 Apple証明書更新承認フローのテストを開始します")
    print("=" * 50)
    
    # 環境変数をチェック
    environment = os.environ.get('ENVIRONMENT', 'main')
    force_update = os.environ.get('FORCE_UPDATE', 'false').lower() == 'true'
    
    print(f"🌟 テスト設定:")
    print(f"  環境: {environment}")
    print(f"  強制更新: {force_update}")
    print(f"  テストモード: 有効（実際のAPI呼び出しなし）")
    
    # Step 1: 証明書チェックシミュレーション
    try:
        approval_data = test_approval_request_generation()
    except Exception as e:
        print(f"❌ 承認リクエスト生成エラー: {e}")
        sys.exit(1)
    
    # Step 2: Slack通知シミュレーション
    try:
        simulate_slack_notification(approval_data)
    except Exception as e:
        print(f"❌ Slack通知シミュレーションエラー: {e}")
        sys.exit(1)
    
    # Step 3: 承認データ保存
    try:
        save_test_approval_data(approval_data)
    except Exception as e:
        print(f"❌ 承認データ保存エラー: {e}")
        sys.exit(1)
    
    # Step 4: 次の手順案内
    show_next_steps(approval_data)
    
    print(f"\n✅ テスト準備完了！")
    print(f"承認ID: {approval_data['approval_id']}")


if __name__ == "__main__":
    main()