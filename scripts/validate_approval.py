#!/usr/bin/env python3
"""
承認IDを検証し、承認されたリクエストかどうかを確認するスクリプト
"""
import os
import sys
import json
from datetime import datetime, timedelta


def load_approval_request():
    """保存された承認リクエスト情報を読み込む"""
    approval_file = '/tmp/approval_request.json'
    if not os.path.exists(approval_file):
        return None
    
    try:
        with open(approval_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"承認リクエストファイルの読み込みに失敗: {e}", file=sys.stderr)
        return None


def validate_approval_id(provided_approval_id, environment):
    """承認IDを検証"""
    
    # 承認IDが提供されていない場合
    if not provided_approval_id:
        print("エラー: 承認IDが提供されていません", file=sys.stderr)
        return False
    
    # 保存された承認リクエストを読み込む
    approval_request = load_approval_request()
    if not approval_request:
        print("エラー: 承認リクエストが見つかりません", file=sys.stderr)
        print("先に証明書チェックを実行して承認リクエストを作成してください", file=sys.stderr)
        return False
    
    # 承認IDの一致確認
    if approval_request['approval_id'] != provided_approval_id:
        print(f"エラー: 承認IDが一致しません", file=sys.stderr)
        print(f"提供されたID: {provided_approval_id}", file=sys.stderr)
        print(f"期待されるID: {approval_request['approval_id']}", file=sys.stderr)
        return False
    
    # 環境の一致確認
    if approval_request['environment'] != environment:
        print(f"エラー: 環境が一致しません", file=sys.stderr)
        print(f"提供された環境: {environment}", file=sys.stderr)
        print(f"期待される環境: {approval_request['environment']}", file=sys.stderr)
        return False
    
    # 承認リクエストの有効期限確認（24時間）
    requested_at = datetime.fromisoformat(approval_request['requested_at'])
    expiry_time = requested_at + timedelta(hours=24)
    current_time = datetime.utcnow()
    
    if current_time > expiry_time:
        print(f"エラー: 承認リクエストの有効期限が切れています", file=sys.stderr)
        print(f"リクエスト時刻: {requested_at}", file=sys.stderr)
        print(f"有効期限: {expiry_time}", file=sys.stderr)
        print(f"現在時刻: {current_time}", file=sys.stderr)
        return False
    
    # 既に処理済みかどうか確認
    if approval_request.get('status') == 'processed':
        print(f"エラー: この承認IDは既に処理済みです", file=sys.stderr)
        return False
    
    print(f"✅ 承認ID検証成功")
    print(f"承認ID: {provided_approval_id}")
    print(f"環境: {environment}")
    print(f"Bundle ID: {approval_request['bundle_id']}")
    print(f"リクエスト時刻: {requested_at}")
    
    return True


def mark_approval_as_processed(approval_action, approved_by=None):
    """承認リクエストを処理済みとしてマーク"""
    approval_file = '/tmp/approval_request.json'
    
    try:
        approval_request = load_approval_request()
        if approval_request:
            approval_request['status'] = 'processed'
            approval_request['approval_action'] = approval_action
            approval_request['processed_at'] = datetime.utcnow().isoformat()
            approval_request['approved_by'] = approved_by or os.environ.get('GITHUB_ACTOR', 'unknown')
            
            with open(approval_file, 'w') as f:
                json.dump(approval_request, f, indent=2)
            
            print(f"承認リクエストを{approval_action}として処理済みにマークしました")
    except Exception as e:
        print(f"警告: 承認ステータスの更新に失敗: {e}", file=sys.stderr)


def main():
    # 環境変数から情報を取得
    approval_action = os.environ.get('APPROVAL_ACTION', '').lower()
    approval_id = os.environ.get('APPROVAL_ID', '')
    environment = os.environ.get('ENVIRONMENT', 'main')
    
    if not approval_action:
        print("エラー: APPROVAL_ACTION が設定されていません", file=sys.stderr)
        sys.exit(1)
    
    if approval_action not in ['approve', 'reject']:
        print(f"エラー: 無効なアクション '{approval_action}'. 'approve' または 'reject' を指定してください", file=sys.stderr)
        sys.exit(1)
    
    # 承認IDを検証
    if not validate_approval_id(approval_id, environment):
        sys.exit(1)
    
    # 拒否の場合はここで終了
    if approval_action == 'reject':
        mark_approval_as_processed('reject')
        print(f"\n❌ 証明書更新が拒否されました（承認ID: {approval_id}）")
        # GitHub Actions の出力として設定
        if 'GITHUB_OUTPUT' in os.environ:
            with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
                f.write(f"approved=false\n")
                f.write(f"action=reject\n")
        sys.exit(0)
    
    # 承認の場合
    if approval_action == 'approve':
        mark_approval_as_processed('approve')
        print(f"\n✅ 証明書更新が承認されました（承認ID: {approval_id}）")
        print(f"証明書の更新を開始します...")
        
        # GitHub Actions の出力として設定
        if 'GITHUB_OUTPUT' in os.environ:
            with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
                f.write(f"approved=true\n")
                f.write(f"action=approve\n")


if __name__ == "__main__":
    main()