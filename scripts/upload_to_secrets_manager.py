#!/usr/bin/env python3
"""
更新した証明書をAWS Secrets Managerにアップロードするスクリプト
"""
import os
import sys
import json
import base64
import boto3
from datetime import datetime
from botocore.exceptions import ClientError


def load_update_result():
    """証明書更新結果を読み込む"""
    result_path = '/tmp/update_result.json'
    if not os.path.exists(result_path):
        print("エラー: 更新結果ファイルが見つかりません", file=sys.stderr)
        return None
        
    with open(result_path, 'r') as f:
        return json.load(f)


def read_file_as_base64(file_path):
    """ファイルをBase64エンコードして読み込む"""
    with open(file_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def upload_to_secrets_manager(secret_data, secret_name, region_name):
    """AWS Secrets Managerにシークレットをアップロード"""
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    
    try:
        # 既存のシークレットを更新
        response = client.update_secret(
            SecretId=secret_name,
            SecretString=json.dumps(secret_data)
        )
        print(f"シークレット '{secret_name}' を更新しました")
        return True
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            # シークレットが存在しない場合は新規作成
            try:
                response = client.create_secret(
                    Name=secret_name,
                    SecretString=json.dumps(secret_data)
                )
                print(f"シークレット '{secret_name}' を作成しました")
                return True
            except ClientError as create_error:
                print(f"エラー: シークレットの作成に失敗しました: {create_error}", file=sys.stderr)
                return False
        else:
            print(f"エラー: シークレットの更新に失敗しました: {e}", file=sys.stderr)
            return False


def main():
    # 環境変数から設定を取得
    environment = os.environ.get('ENVIRONMENT', 'main')
    region_name = os.environ.get('AWS_REGION', 'ap-northeast-1')
    secret_base_name = os.environ.get('CERTIFICATE_SECRET_BASE_NAME', 'apple-certificate-update')
    
    # 環境に応じたサフィックス
    env_suffix = 'prd' if environment == 'main' else environment
    
    # 更新結果を読み込む
    update_result = load_update_result()
    if not update_result:
        sys.exit(1)
    
    # 証明書ファイルを読み込む
    cert_path = update_result.get('certificate_path')
    p12_path = update_result.get('p12_path')
    
    if not cert_path or not p12_path:
        print("エラー: 証明書ファイルパスが見つかりません", file=sys.stderr)
        sys.exit(1)
    
    if not os.path.exists(cert_path) or not os.path.exists(p12_path):
        print("エラー: 証明書ファイルが存在しません", file=sys.stderr)
        sys.exit(1)
    
    print("証明書ファイルを読み込んでいます...")
    
    # 証明書データを準備
    certificate_data = {
        'certificate': read_file_as_base64(cert_path),
        'p12': read_file_as_base64(p12_path),
        'p12_password': os.environ.get('P12_PASSWORD', ''),  # Fastlaneが生成したパスワード
        'bundle_ids': update_result.get('bundle_ids', []),
        'updated_at': datetime.utcnow().isoformat(),
        'updated_by': 'github-actions'
    }
    
    # プロビジョニングプロファイルも含める（存在する場合）
    profiles_dir = '/tmp/profiles'
    if os.path.exists(profiles_dir):
        profiles = {}
        for profile_file in os.listdir(profiles_dir):
            if profile_file.endswith('.mobileprovision'):
                profile_path = os.path.join(profiles_dir, profile_file)
                # Bundle IDをファイル名から推測（Fastlaneの命名規則に依存）
                bundle_id = profile_file.replace('.mobileprovision', '').replace('_', '.')
                profiles[bundle_id] = read_file_as_base64(profile_path)
        
        if profiles:
            certificate_data['provisioning_profiles'] = profiles
            print(f"プロビジョニングプロファイル {len(profiles)} 個を含めます")
    
    # シークレット名を決定（環境別）
    secret_name = f"{secret_base_name}/distribution-certificate-{env_suffix}"
    
    print(f"\nAWS Secrets Manager にアップロードしています...")
    print(f"リージョン: {region_name}")
    print(f"シークレット名: {secret_name}")
    
    # アップロード
    success = upload_to_secrets_manager(certificate_data, secret_name, region_name)
    
    if success:
        print("\n✅ 証明書のアップロードが完了しました")
        
        # メタデータも別途保存（オプション）
        metadata = {
            'last_update': datetime.utcnow().isoformat(),
            'bundle_ids': update_result.get('bundle_ids', []),
            'certificate_type': 'IOS_DISTRIBUTION',
            'update_source': 'github-actions'
        }
        
        metadata_secret_name = f"{secret_base_name}/certificate-metadata-{env_suffix}"
        upload_to_secrets_manager(metadata, metadata_secret_name, region_name)
        
    else:
        print("\n❌ 証明書のアップロードに失敗しました")
        sys.exit(1)


if __name__ == "__main__":
    main()