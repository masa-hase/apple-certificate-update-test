#!/usr/bin/env python3
"""
Slackに証明書更新の承認リクエストを送信するスクリプト
"""
import os
import sys
import json
import requests
from datetime import datetime


def send_approval_request(webhook_url, approval_data):
    """Slackに承認リクエストを送信"""
    
    # 環境情報
    environment = approval_data['environment']
    env_name = 'Production' if environment == 'main' else environment.upper()
    
    # リポジトリ情報
    repo_name = os.environ.get('GITHUB_REPOSITORY', 'Unknown Repository')
    run_id = os.environ.get('GITHUB_RUN_ID', '')
    
    # GitHub ActionsのURLを生成
    workflow_url = f"https://github.com/{repo_name}/actions/runs/{run_id}" if run_id else None
    
    # 承認/拒否用のGitHub Actions手動実行URL
    workflow_file = "approval-certificate-update.yml"
    approve_url = f"https://github.com/{repo_name}/actions/workflows/{workflow_file}"
    
    # Slack Blockを構築
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🔐 Apple証明書更新の承認リクエスト",
                "emoji": True
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*環境:* {env_name}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Bundle ID:* {approval_data['bundle_id']}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*有効期限:* {approval_data['expiry_date']}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*残り日数:* {approval_data['days_remaining']}日"
                }
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"証明書の有効期限が近づいています。更新を実行しますか？\n\n承認ID: `{approval_data['approval_id']}`\n\n⚠️ 下記のリンクをクリックして、GitHub Actionsで手動実行してください。"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"🔗 *承認・実行手順:*\n1. <{approve_url}|GitHub Actionsワークフローを開く>\n2. 「Run workflow」ボタンをクリック\n3. 以下の値を入力:\n   • `approval_action`: `approve`\n   • `environment`: `{environment}`\n   • `approval_id`: `{approval_data['approval_id']}`\n4. 「Run workflow」で実行"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"❌ *拒否する場合:*\n上記リンクで `approval_action` に `reject` を入力してください。"
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"リポジトリ: <https://github.com/{repo_name}|{repo_name}>"
                }
            ]
        }
    ]
    
    if workflow_url:
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"<{workflow_url}|ワークフローの詳細を見る>"
                }
            ]
        })
    
    # Slackメッセージのペイロード
    payload = {
        "text": f"🔐 Apple証明書更新の承認リクエスト ({env_name})",
        "blocks": blocks
    }
    
    # Slackに送信
    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        print(f"✅ Slack承認リクエストを送信しました")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Slack承認リクエストの送信に失敗しました: {e}", file=sys.stderr)
        return False


def get_approval_instructions(approval_data):
    """承認手順の詳細を取得"""
    repo_name = os.environ.get('GITHUB_REPOSITORY', '')
    workflow_url = f"https://github.com/{repo_name}/actions/workflows/approval-certificate-update.yml"
    
    instructions = f"""
📋 **承認手順**:

1. GitHub Actionsワークフローを開く:
   {workflow_url}

2. 「Run workflow」ボタンをクリック

3. 以下のパラメータを入力:
   • approval_action: approve (承認) または reject (拒否)
   • environment: {approval_data['environment']}
   • approval_id: {approval_data['approval_id']}

4. 「Run workflow」ボタンで実行

⚠️ 承認IDは必ず正確に入力してください。
"""
    return instructions


def main():
    # 環境変数から情報を取得
    webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
    if not webhook_url:
        print("エラー: SLACK_WEBHOOK_URL が設定されていません", file=sys.stderr)
        sys.exit(1)
    
    # 承認データを構築
    approval_data = {
        'environment': os.environ.get('ENVIRONMENT', 'main'),
        'bundle_id': os.environ.get('BUNDLE_ID', 'Unknown'),
        'expiry_date': os.environ.get('EXPIRY_DATE', 'Unknown'),
        'days_remaining': os.environ.get('DAYS_REMAINING', 'Unknown'),
        'approval_id': os.environ.get('APPROVAL_ID', 'Unknown')
    }
    
    # 承認リクエストを送信
    success = send_approval_request(webhook_url, approval_data)
    
    if success:
        print(f"\n✅ 承認リクエストをSlackに送信しました。")
        print(f"承認ID: {approval_data['approval_id']}")
        print(f"\n{get_approval_instructions(approval_data)}")
        
        # 承認情報をファイルに保存（承認処理で使用）
        approval_info = {
            'approval_id': approval_data['approval_id'],
            'environment': approval_data['environment'],
            'bundle_id': approval_data['bundle_id'],
            'requested_at': datetime.utcnow().isoformat(),
            'status': 'pending'
        }
        
        with open('/tmp/approval_request.json', 'w') as f:
            json.dump(approval_info, f, indent=2)
            
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()