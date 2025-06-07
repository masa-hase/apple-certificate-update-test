#!/usr/bin/env python3
"""
証明書の有効期限をチェックして更新が必要か判定するスクリプト
"""
import os
import sys
import json
import requests
from datetime import datetime, timedelta
import jwt
import time


class AppStoreConnectAPI:
    def __init__(self, key_id, issuer_id, key_path):
        self.key_id = key_id
        self.issuer_id = issuer_id
        self.key_path = key_path
        self.base_url = "https://api.appstoreconnect.apple.com/v1"
        
    def _generate_token(self):
        """JWT トークンを生成"""
        with open(self.key_path, 'r') as f:
            private_key = f.read()
        
        # トークンの有効期限（最大20分）
        expiration_time = int(time.time()) + (20 * 60)
        
        # JWT ペイロード
        payload = {
            'iss': self.issuer_id,
            'exp': expiration_time,
            'aud': 'appstoreconnect-v1'
        }
        
        # JWT トークンを生成
        token = jwt.encode(
            payload,
            private_key,
            algorithm='ES256',
            headers={'kid': self.key_id}
        )
        
        return token
    
    def _make_request(self, endpoint, method='GET', params=None):
        """API リクエストを実行"""
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self._generate_token()}',
            'Content-Type': 'application/json'
        }
        
        response = requests.request(method, url, headers=headers, params=params)
        response.raise_for_status()
        
        return response.json()
    
    def get_certificates(self):
        """証明書一覧を取得"""
        return self._make_request('/certificates')
    
    def get_certificate_details(self, certificate_id):
        """証明書の詳細情報を取得"""
        return self._make_request(f'/certificates/{certificate_id}')
    
    def get_profiles(self, certificate_id=None):
        """プロビジョニングプロファイル一覧を取得"""
        params = {}
        if certificate_id:
            params['filter[certificates]'] = certificate_id
        return self._make_request('/profiles', params=params)


def get_bundle_ids_from_output():
    """GitHub Actions の前のステップから Bundle ID を取得"""
    # 環境変数から取得を試みる
    bundle_ids_json = os.environ.get('BUNDLE_IDS')
    if bundle_ids_json:
        return json.loads(bundle_ids_json)
    
    # ファイルから取得を試みる（ローカルテスト用）
    bundle_id = os.environ.get('BUNDLE_ID')
    if bundle_id:
        return [bundle_id]
    
    return None


def check_certificate_expiry_for_bundle_ids(api, bundle_ids, days_threshold=30):
    """特定のBundle IDに関連する証明書の有効期限をチェック"""
    print("証明書一覧を取得しています...")
    print(f"対象Bundle ID: {', '.join(bundle_ids)}")
    
    try:
        # すべての証明書を取得
        response = api.get_certificates()
        certificates = response.get('data', [])
        
        if not certificates:
            print("警告: 証明書が見つかりません")
            return None, True
        
        # Distribution証明書をフィルタリング
        distribution_certs = [
            cert for cert in certificates 
            if cert['attributes']['certificateType'] == 'IOS_DISTRIBUTION'
        ]
        
        if not distribution_certs:
            print("警告: Distribution証明書が見つかりません")
            return None, True
        
        # 各証明書に関連するプロファイルを確認してBundle IDと照合
        matching_certs = []
        
        for cert in distribution_certs:
            cert_id = cert['id']
            print(f"\n証明書 {cert_id} のプロファイルを確認中...")
            
            # この証明書に関連するプロファイルを取得
            profiles_response = api.get_profiles(certificate_id=cert_id)
            profiles = profiles_response.get('data', [])
            
            # プロファイルのBundle IDを確認
            for profile in profiles:
                profile_bundle_id = profile['attributes'].get('bundleId', {}).get('identifier')
                if profile_bundle_id in bundle_ids:
                    print(f"  ✓ マッチ: {profile_bundle_id}")
                    matching_certs.append({
                        'cert': cert,
                        'bundle_id': profile_bundle_id
                    })
                    break
        
        if not matching_certs:
            print(f"\n警告: Bundle ID {bundle_ids} に関連するDistribution証明書が見つかりません")
            return None, True
        
        # 最新の証明書を取得（有効期限でソート）
        latest_match = max(
            matching_certs,
            key=lambda x: x['cert']['attributes']['expirationDate']
        )
        
        latest_cert = latest_match['cert']
        matched_bundle_id = latest_match['bundle_id']
        
        # 有効期限を確認
        expiry_date_str = latest_cert['attributes']['expirationDate']
        expiry_date = datetime.fromisoformat(expiry_date_str.replace('Z', '+00:00'))
        current_date = datetime.now(expiry_date.tzinfo)
        days_remaining = (expiry_date - current_date).days
        
        print(f"\n現在の証明書情報:")
        print(f"  証明書ID: {latest_cert['id']}")
        print(f"  証明書名: {latest_cert['attributes']['name']}")
        print(f"  Bundle ID: {matched_bundle_id}")
        print(f"  有効期限: {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  残り日数: {days_remaining}日")
        
        # 更新が必要か判定
        needs_update = days_remaining <= days_threshold
        
        return {
            'certificate_id': latest_cert['id'],
            'bundle_id': matched_bundle_id,
            'expiry_date': expiry_date.strftime('%Y-%m-%d'),
            'days_remaining': days_remaining,
            'needs_update': needs_update
        }, needs_update
        
    except Exception as e:
        print(f"エラー: 証明書の確認中にエラーが発生しました: {e}", file=sys.stderr)
        return None, True


def main():
    # 環境変数から設定を取得
    key_id = os.environ.get('APP_STORE_CONNECT_KEY_ID')
    issuer_id = os.environ.get('APP_STORE_CONNECT_ISSUER_ID')
    key_path = os.environ.get('APP_STORE_CONNECT_KEY_PATH', '/tmp/AuthKey.p8')
    force_update = os.environ.get('FORCE_UPDATE', 'false').lower() == 'true'
    
    if not all([key_id, issuer_id, key_path]):
        print("エラー: API認証情報が設定されていません", file=sys.stderr)
        sys.exit(1)
    
    # Bundle IDを取得
    bundle_ids = get_bundle_ids_from_output()
    if not bundle_ids:
        print("エラー: Bundle IDが取得できません", file=sys.stderr)
        print("extract_bundle_id.py を先に実行してください", file=sys.stderr)
        sys.exit(1)
    
    # APIクライアントを初期化
    api = AppStoreConnectAPI(key_id, issuer_id, key_path)
    
    # 強制更新が指定されている場合
    if force_update:
        print("強制更新モードが有効です")
        result = {
            'needs_update': True,
            'force_update': True,
            'bundle_ids': bundle_ids
        }
        needs_update = True
    else:
        # 証明書の有効期限をチェック
        result, needs_update = check_certificate_expiry_for_bundle_ids(api, bundle_ids)
    
    # 結果を出力
    if needs_update:
        print(f"\n✅ 証明書の更新が必要です")
    else:
        print(f"\n⏸️  証明書の更新は不要です（有効期限に余裕があります）")
    
    # GitHub Actions の出力として設定
    if 'GITHUB_OUTPUT' in os.environ:
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f"needs_update={'true' if needs_update else 'false'}\n")
            if result and not force_update:
                f.write(f"expiry_date={result.get('expiry_date', 'unknown')}\n")
                f.write(f"days_remaining={result.get('days_remaining', 'unknown')}\n")
                f.write(f"certificate_id={result.get('certificate_id', 'unknown')}\n")
                f.write(f"bundle_id={result.get('bundle_id', 'unknown')}\n")
    
    # 結果をファイルに保存（後続のスクリプトで使用）
    if result:
        with open('/tmp/certificate_check_result.json', 'w') as f:
            json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()