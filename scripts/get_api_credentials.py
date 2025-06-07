#!/usr/bin/env python3
"""
AWS Secrets Manager から App Store Connect API の認証情報を取得するスクリプト
"""
import os
import sys
import json
import base64
import boto3
from botocore.exceptions import ClientError


def get_secret(secret_name, region_name):
    """AWS Secrets Manager からシークレットを取得"""
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        print(f"エラー: シークレット '{secret_name}' の取得に失敗しました", file=sys.stderr)
        print(f"詳細: {e}", file=sys.stderr)
        sys.exit(1)
    
    # シークレットの値を取得
    if 'SecretString' in get_secret_value_response:
        secret = get_secret_value_response['SecretString']
        return json.loads(secret)
    else:
        # バイナリシークレットの場合
        decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])
        return json.loads(decoded_binary_secret)


def save_p8_key(key_content, output_path):
    """P8形式の秘密鍵をファイルに保存"""
    with open(output_path, 'w') as f:
        f.write(key_content)
    
    # ファイルのパーミッションを設定（秘密鍵なので読み取り専用）
    os.chmod(output_path, 0o400)


def main():
    # 環境変数から設定を取得
    environment = os.environ.get('ENVIRONMENT', 'main')
    region_name = os.environ.get('AWS_REGION', 'ap-northeast-1')
    
    # 環境に応じたシークレット名を構築
    secret_base = os.environ.get('API_CREDENTIALS_SECRET_BASE', 'apple-certificate-update')
    env_suffix = 'prd' if environment == 'main' else environment
    secret_name = f"{secret_base}/api-credentials-{env_suffix}"
    
    print(f"AWS Secrets Manager からAPI認証情報を取得しています...")
    print(f"リージョン: {region_name}")
    print(f"シークレット名: {secret_name}")
    
    # シークレットを取得
    credentials = get_secret(secret_name, region_name)
    
    # 必要な認証情報が含まれているか確認
    required_keys = ['key_id', 'issuer_id', 'private_key']
    missing_keys = [key for key in required_keys if key not in credentials]
    
    if missing_keys:
        print(f"エラー: シークレットに必要なキーが含まれていません: {missing_keys}", file=sys.stderr)
        sys.exit(1)
    
    # 認証情報を表示（秘密鍵は除く）
    print(f"\n取得した認証情報:")
    print(f"  Key ID: {credentials['key_id']}")
    print(f"  Issuer ID: {credentials['issuer_id']}")
    print(f"  Private Key: ****** (取得済み)")
    
    # P8形式の秘密鍵をファイルに保存
    key_path = '/tmp/AuthKey.p8'
    save_p8_key(credentials['private_key'], key_path)
    print(f"\n秘密鍵を保存しました: {key_path}")
    
    # GitHub Actions の出力として設定
    if 'GITHUB_OUTPUT' in os.environ:
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f"key_id={credentials['key_id']}\n")
            f.write(f"issuer_id={credentials['issuer_id']}\n")
            f.write(f"key_path={key_path}\n")
    
    # 環境変数として設定（後続のスクリプトで使用）
    print(f"\n環境変数に設定:")
    print(f"APP_STORE_CONNECT_KEY_ID={credentials['key_id']}")
    print(f"APP_STORE_CONNECT_ISSUER_ID={credentials['issuer_id']}")
    print(f"APP_STORE_CONNECT_KEY_PATH={key_path}")


if __name__ == "__main__":
    main()