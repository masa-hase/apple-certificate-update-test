#!/usr/bin/env python3
"""
Xcodeプロジェクトファイルから Bundle ID を抽出するスクリプト
"""
import os
import re
import json
import sys
from pathlib import Path


def find_xcodeproj():
    """リポジトリ内の .xcodeproj ファイルを検索"""
    current_dir = Path.cwd()
    xcodeproj_files = list(current_dir.glob("**/*.xcodeproj"))
    
    if not xcodeproj_files:
        print("エラー: .xcodeproj ファイルが見つかりません", file=sys.stderr)
        sys.exit(1)
    
    if len(xcodeproj_files) > 1:
        print(f"警告: 複数の .xcodeproj ファイルが見つかりました。最初のファイルを使用します: {xcodeproj_files[0]}")
    
    return xcodeproj_files[0]


def extract_bundle_id_from_pbxproj(pbxproj_path):
    """project.pbxproj ファイルから Bundle ID を抽出"""
    bundle_ids = set()
    
    with open(pbxproj_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # PRODUCT_BUNDLE_IDENTIFIER のパターンを検索
    pattern = r'PRODUCT_BUNDLE_IDENTIFIER\s*=\s*"?([^";]+)"?;'
    matches = re.findall(pattern, content)
    
    for match in matches:
        # 変数参照を除外（$(...)を含むもの）
        if not '$(' in match:
            bundle_ids.add(match.strip())
    
    return list(bundle_ids)


def extract_bundle_id_from_plist(xcodeproj_path):
    """Info.plist から Bundle ID を抽出（フォールバック）"""
    project_dir = xcodeproj_path.parent
    info_plists = list(project_dir.glob("**/Info.plist"))
    
    bundle_ids = []
    
    for plist_path in info_plists:
        try:
            # plistbuddy を使用してBundle IDを読み取る
            import subprocess
            result = subprocess.run(
                ['/usr/libexec/PlistBuddy', '-c', 'Print :CFBundleIdentifier', str(plist_path)],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                bundle_id = result.stdout.strip()
                if not '$(' in bundle_id:  # 変数参照を除外
                    bundle_ids.append(bundle_id)
        except Exception as e:
            print(f"警告: {plist_path} の読み取りに失敗しました: {e}", file=sys.stderr)
    
    return bundle_ids


def load_environment_config():
    """環境設定をロード"""
    config_path = Path.cwd() / 'config' / 'environments.json'
    if config_path.exists():
        with open(config_path, 'r') as f:
            return json.load(f)
    return None


def apply_environment_suffix(bundle_ids, environment):
    """環境に応じたBundle IDのサフィックスを適用"""
    config = load_environment_config()
    if not config:
        return bundle_ids
    
    env_config = config.get('environments', {}).get(environment)
    if not env_config:
        return bundle_ids
    
    suffix = env_config.get('bundle_id_suffix', '')
    if not suffix:
        return bundle_ids
    
    # サフィックスを適用
    modified_bundle_ids = []
    for bundle_id in bundle_ids:
        # すでにサフィックスがついている場合は追加しない
        if not bundle_id.endswith(suffix):
            modified_bundle_ids.append(bundle_id + suffix)
        else:
            modified_bundle_ids.append(bundle_id)
    
    return modified_bundle_ids


def main():
    # 環境を取得
    environment = os.environ.get('ENVIRONMENT', 'main')
    print(f"環境: {environment}")
    
    # Xcodeプロジェクトを検索
    xcodeproj_path = find_xcodeproj()
    print(f"Xcodeプロジェクトを検出: {xcodeproj_path}")
    
    # project.pbxproj ファイルのパス
    pbxproj_path = xcodeproj_path / "project.pbxproj"
    
    if not pbxproj_path.exists():
        print(f"エラー: {pbxproj_path} が見つかりません", file=sys.stderr)
        sys.exit(1)
    
    # Bundle ID を抽出
    bundle_ids = extract_bundle_id_from_pbxproj(pbxproj_path)
    
    # Bundle ID が見つからない場合は Info.plist から取得を試みる
    if not bundle_ids:
        print("project.pbxproj から Bundle ID が見つかりません。Info.plist を確認しています...")
        bundle_ids = extract_bundle_id_from_plist(xcodeproj_path)
    
    if not bundle_ids:
        print("エラー: Bundle ID が見つかりません", file=sys.stderr)
        sys.exit(1)
    
    # 環境に応じたサフィックスを適用
    bundle_ids = apply_environment_suffix(bundle_ids, environment)
    
    # 結果を出力
    print(f"\n検出された Bundle ID ({environment}環境):")
    for bundle_id in bundle_ids:
        print(f"  - {bundle_id}")
    
    # GitHub Actions の出力として設定
    if 'GITHUB_OUTPUT' in os.environ:
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            # 最初のBundle IDをメインとして設定
            f.write(f"bundle_id={bundle_ids[0]}\n")
            # すべてのBundle IDをJSON形式で出力
            f.write(f"bundle_ids={json.dumps(bundle_ids)}\n")
    
    # 環境変数として設定（ローカルテスト用）
    print(f"\n環境変数に設定:")
    print(f"BUNDLE_ID={bundle_ids[0]}")
    print(f"BUNDLE_IDS={json.dumps(bundle_ids)}")


if __name__ == "__main__":
    main()