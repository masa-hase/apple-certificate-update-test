#!/usr/bin/env python3
"""
Slackに通知を送信するスクリプト
"""
import os
import sys
import json
import argparse
import requests
from datetime import datetime


def send_slack_message(webhook_url, message, status='info'):
    """Slackにメッセージを送信"""
    
    # ステータスに応じた色とアイコンを設定
    color_map = {
        'success': '#36a64f',  # 緑
        'failure': '#ff0000',  # 赤
        'warning': '#ff9900',  # オレンジ
        'info': '#0099ff'      # 青
    }
    
    icon_map = {
        'success': ':white_check_mark:',
        'failure': ':x:',
        'warning': ':warning:',
        'info': ':information_source:'
    }
    
    color = color_map.get(status, '#808080')
    icon = icon_map.get(status, ':bell:')
    
    # 環境情報を取得
    environment = os.environ.get('ENVIRONMENT', 'main')
    env_name = 'Production' if environment == 'main' else environment.upper()
    
    # リポジトリ情報を取得
    repo_name = os.environ.get('GITHUB_REPOSITORY', 'Unknown Repository')
    workflow_name = os.environ.get('GITHUB_WORKFLOW', 'Certificate Update')
    run_id = os.environ.get('GITHUB_RUN_ID', '')
    run_number = os.environ.get('GITHUB_RUN_NUMBER', '')
    actor = os.environ.get('GITHUB_ACTOR', 'github-actions')
    
    # GitHub Actions の実行URLを生成
    workflow_url = f"https://github.com/{repo_name}/actions/runs/{run_id}" if run_id else None
    
    # Slackメッセージのペイロードを構築
    payload = {
        'attachments': [{
            'color': color,
            'fallback': f"{icon} {message}",
            'fields': [
                {
                    'title': 'Repository',
                    'value': f"<https://github.com/{repo_name}|{repo_name}>",
                    'short': True
                },
                {
                    'title': 'Workflow',
                    'value': workflow_name,
                    'short': True
                },
                {
                    'title': 'Environment',
                    'value': env_name,
                    'short': True
                },
                {
                    'title': 'Status',
                    'value': f"{icon} {status.upper()}",
                    'short': True
                },
                {
                    'title': 'Triggered by',
                    'value': actor,
                    'short': True
                }
            ],
            'text': message,
            'footer': 'Apple Certificate Updater',
            'footer_icon': 'https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png',
            'ts': int(datetime.now().timestamp())
        }]
    }
    
    # 実行番号とURLを追加
    if run_number:
        payload['attachments'][0]['fields'].append({
            'title': 'Run',
            'value': f"#{run_number}",
            'short': True
        })
    
    if workflow_url:
        payload['attachments'][0]['fields'].append({
            'title': 'Details',
            'value': f"<{workflow_url}|View Run>",
            'short': True
        })
    
    # 追加の詳細情報（証明書情報など）
    if status == 'success' and os.path.exists('/tmp/update_result.json'):
        try:
            with open('/tmp/update_result.json', 'r') as f:
                update_result = json.load(f)
                bundle_ids = update_result.get('bundle_ids', [])
                if bundle_ids:
                    payload['attachments'][0]['fields'].append({
                        'title': 'Updated Bundle IDs',
                        'value': ', '.join(bundle_ids),
                        'short': False
                    })
        except:
            pass
    
    # Slackに送信
    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        print(f"✅ Slack通知を送信しました: {status}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Slack通知の送信に失敗しました: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description='Send Slack notification')
    parser.add_argument('--status', choices=['success', 'failure', 'warning', 'info'], 
                       default='info', help='Notification status')
    parser.add_argument('--message', required=True, help='Notification message')
    
    args = parser.parse_args()
    
    # Webhook URLを環境変数から取得
    webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
    if not webhook_url:
        print("警告: SLACK_WEBHOOK_URL が設定されていません。通知をスキップします。")
        sys.exit(0)  # エラーではなく正常終了
    
    # メッセージを送信
    success = send_slack_message(webhook_url, args.message, args.status)
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()