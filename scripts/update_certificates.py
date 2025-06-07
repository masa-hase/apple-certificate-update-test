#!/usr/bin/env python3
"""
Apple Distribution証明書を更新するスクリプト
"""
import os
import sys
import json
import subprocess
import tempfile
from pathlib import Path


def load_certificate_info():
    """前のステップで保存された証明書情報を読み込む"""
    cert_info_path = '/tmp/certificate_check_result.json'
    if os.path.exists(cert_info_path):
        with open(cert_info_path, 'r') as f:
            return json.load(f)
    return {}


def create_certificate_signing_request():
    """証明書署名要求（CSR）を作成"""
    print("証明書署名要求（CSR）を作成しています...")
    
    # 一時ディレクトリを作成
    temp_dir = tempfile.mkdtemp()
    private_key_path = os.path.join(temp_dir, 'private_key.p12')
    csr_path = os.path.join(temp_dir, 'CertificateSigningRequest.certSigningRequest')
    
    # CSRを作成するためのFastlaneコマンド
    # 注: 実際の実装ではApp Store Connect APIを直接使用することも可能
    cmd = [
        'fastlane', 'cert',
        '--username', os.environ.get('APPLE_ID', ''),
        '--team_id', os.environ.get('TEAM_ID', ''),
        '--output_path', temp_dir,
        '--keychain_path', 'login.keychain',
        '--skip_install',
        '--platform', 'ios'
    ]
    
    # API Key認証を使用
    env = os.environ.copy()
    env['APP_STORE_CONNECT_API_KEY_KEY_ID'] = os.environ.get('APP_STORE_CONNECT_KEY_ID', '')
    env['APP_STORE_CONNECT_API_KEY_ISSUER_ID'] = os.environ.get('APP_STORE_CONNECT_ISSUER_ID', '')
    env['APP_STORE_CONNECT_API_KEY_KEY_FILEPATH'] = os.environ.get('APP_STORE_CONNECT_KEY_PATH', '')
    
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"エラー: CSRの作成に失敗しました")
            print(f"標準出力: {result.stdout}")
            print(f"標準エラー: {result.stderr}")
            return None, None
            
        print("CSRの作成に成功しました")
        return csr_path, private_key_path
        
    except Exception as e:
        print(f"エラー: {e}")
        return None, None


def revoke_old_certificate(certificate_id):
    """古い証明書を無効化"""
    print(f"古い証明書を無効化しています: {certificate_id}")
    
    # Fastlaneを使用して証明書を無効化
    cmd = [
        'fastlane', 'run', 'revoke_certificate',
        f'certificate_id:{certificate_id}',
        '--verbose'
    ]
    
    env = os.environ.copy()
    env['APP_STORE_CONNECT_API_KEY_KEY_ID'] = os.environ.get('APP_STORE_CONNECT_KEY_ID', '')
    env['APP_STORE_CONNECT_API_KEY_ISSUER_ID'] = os.environ.get('APP_STORE_CONNECT_ISSUER_ID', '')
    env['APP_STORE_CONNECT_API_KEY_KEY_FILEPATH'] = os.environ.get('APP_STORE_CONNECT_KEY_PATH', '')
    
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode == 0:
            print("古い証明書の無効化に成功しました")
        else:
            print(f"警告: 古い証明書の無効化に失敗しました（処理は継続します）")
            print(f"エラー: {result.stderr}")
    except Exception as e:
        print(f"警告: 証明書の無効化中にエラーが発生しました: {e}")


def create_new_certificate():
    """新しい証明書を作成"""
    print("\n新しいDistribution証明書を作成しています...")
    
    # 出力ディレクトリ
    output_dir = '/tmp/certificates'
    os.makedirs(output_dir, exist_ok=True)
    
    # Fastlaneで新しい証明書を作成
    cmd = [
        'fastlane', 'cert',
        '--output_path', output_dir,
        '--skip_install',  # キーチェーンにインストールしない
        '--platform', 'ios',
        '--development', 'false',  # Distribution証明書
        '--force'  # 既存の証明書があっても新規作成
    ]
    
    env = os.environ.copy()
    env['APP_STORE_CONNECT_API_KEY_KEY_ID'] = os.environ.get('APP_STORE_CONNECT_KEY_ID', '')
    env['APP_STORE_CONNECT_API_KEY_ISSUER_ID'] = os.environ.get('APP_STORE_CONNECT_ISSUER_ID', '')
    env['APP_STORE_CONNECT_API_KEY_KEY_FILEPATH'] = os.environ.get('APP_STORE_CONNECT_KEY_PATH', '')
    env['FASTLANE_DISABLE_COLORS'] = '1'  # カラー出力を無効化
    
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"エラー: 証明書の作成に失敗しました")
            print(f"標準出力: {result.stdout}")
            print(f"標準エラー: {result.stderr}")
            return None
            
        # 作成された証明書ファイルを探す
        cert_files = list(Path(output_dir).glob('*.cer'))
        p12_files = list(Path(output_dir).glob('*.p12'))
        
        if cert_files and p12_files:
            print(f"証明書の作成に成功しました")
            print(f"  証明書: {cert_files[0]}")
            print(f"  P12ファイル: {p12_files[0]}")
            
            return {
                'certificate_path': str(cert_files[0]),
                'p12_path': str(p12_files[0]),
                'output_dir': output_dir
            }
        else:
            print("エラー: 証明書ファイルが見つかりません")
            return None
            
    except Exception as e:
        print(f"エラー: {e}")
        return None


def update_provisioning_profiles(bundle_id):
    """プロビジョニングプロファイルを更新"""
    print(f"\nBundle ID '{bundle_id}' のプロビジョニングプロファイルを更新しています...")
    
    output_dir = '/tmp/profiles'
    os.makedirs(output_dir, exist_ok=True)
    
    # Fastlaneでプロファイルを更新
    cmd = [
        'fastlane', 'sigh',
        '--app_identifier', bundle_id,
        '--output_path', output_dir,
        '--skip_install',
        '--platform', 'ios',
        '--force',  # 新しいプロファイルを強制作成
        '--adhoc', 'false',
        '--development', 'false'  # Distribution用
    ]
    
    env = os.environ.copy()
    env['APP_STORE_CONNECT_API_KEY_KEY_ID'] = os.environ.get('APP_STORE_CONNECT_KEY_ID', '')
    env['APP_STORE_CONNECT_API_KEY_ISSUER_ID'] = os.environ.get('APP_STORE_CONNECT_ISSUER_ID', '')
    env['APP_STORE_CONNECT_API_KEY_KEY_FILEPATH'] = os.environ.get('APP_STORE_CONNECT_KEY_PATH', '')
    env['FASTLANE_DISABLE_COLORS'] = '1'
    
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"警告: プロビジョニングプロファイルの更新に失敗しました")
            print(f"エラー: {result.stderr}")
            return None
            
        # 作成されたプロファイルを探す
        profile_files = list(Path(output_dir).glob('*.mobileprovision'))
        
        if profile_files:
            print(f"プロビジョニングプロファイルの更新に成功しました")
            print(f"  プロファイル: {profile_files[0]}")
            return str(profile_files[0])
        else:
            print("警告: プロビジョニングプロファイルファイルが見つかりません")
            return None
            
    except Exception as e:
        print(f"警告: プロビジョニングプロファイルの更新中にエラーが発生しました: {e}")
        return None


def main():
    # リトライ試行回数を取得
    retry_attempt = int(os.environ.get('RETRY_ATTEMPT', '0'))
    if retry_attempt > 0:
        print(f"リトライ試行 {retry_attempt} 回目")
    
    # 証明書情報を読み込む
    cert_info = load_certificate_info()
    
    # 古い証明書を無効化（オプション）
    if cert_info.get('certificate_id'):
        revoke_old_certificate(cert_info['certificate_id'])
    
    # 新しい証明書を作成
    new_cert_info = create_new_certificate()
    if not new_cert_info:
        print("エラー: 証明書の作成に失敗しました")
        sys.exit(1)
    
    # Bundle IDを取得
    bundle_ids = json.loads(os.environ.get('BUNDLE_IDS', '[]'))
    if not bundle_ids:
        bundle_id = os.environ.get('BUNDLE_ID')
        if bundle_id:
            bundle_ids = [bundle_id]
    
    # 各Bundle IDのプロビジョニングプロファイルを更新
    if bundle_ids:
        for bundle_id in bundle_ids:
            update_provisioning_profiles(bundle_id)
    
    # 結果を保存
    result = {
        'success': True,
        'certificate_path': new_cert_info['certificate_path'],
        'p12_path': new_cert_info['p12_path'],
        'bundle_ids': bundle_ids
    }
    
    with open('/tmp/update_result.json', 'w') as f:
        json.dump(result, f, indent=2)
    
    # GitHub Actions の出力として設定
    if 'GITHUB_OUTPUT' in os.environ:
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f"success=true\n")
            f.write(f"certificate_path={new_cert_info['certificate_path']}\n")
            f.write(f"p12_path={new_cert_info['p12_path']}\n")
    
    print("\n✅ 証明書の更新が完了しました")


if __name__ == "__main__":
    main()