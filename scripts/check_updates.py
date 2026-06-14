#!/usr/bin/env python3
"""
自动检查 apps 文件夹下应用的版本更新
"""
import os
import re
import json
import yaml
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def load_yaml(file_path: str) -> dict:
    """加载 YAML 文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_yaml(file_path: str, data: dict):
    """保存 YAML 文件"""
    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def get_github_latest_release(repo_url: str) -> Optional[str]:
    """
    从 GitHub 仓库获取最新版本
    repo_url: https://github.com/owner/repo 格式
    """
    try:
        # 提取 owner/repo
        match = re.search(r'github\.com/([^/]+)/([^/]+?)(?:\.git)?$', repo_url)
        if not match:
            return None

        owner, repo = match.groups()

        # 使用 GitHub API 获取最新 release
        api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
        headers = {}

        # 如果有 GITHUB_TOKEN，使用它来避免 API 限制
        github_token = os.environ.get('GITHUB_TOKEN')
        if github_token:
            headers['Authorization'] = f'token {github_token}'

        response = requests.get(api_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            tag = data.get('tag_name', '')
            # 去除 v 前缀
            return tag.lstrip('v')

        # 如果没有 release，尝试获取最新 tag
        api_url = f"https://api.github.com/repos/{owner}/{repo}/tags"
        response = requests.get(api_url, headers=headers, timeout=10)

        if response.status_code == 200:
            tags = response.json()
            if tags:
                tag = tags[0].get('name', '')
                return tag.lstrip('v')

        return None

    except Exception as e:
        print(f"Error getting GitHub release for {repo_url}: {e}")
        return None


def get_docker_latest_tag(image_name: str) -> Optional[str]:
    """
    从 Docker Hub 获取最新标签
    """
    try:
        # 解析镜像名称
        parts = image_name.split('/')
        if len(parts) == 2:
            namespace, repo = parts
        else:
            namespace = 'library'
            repo = parts[0]

        # 使用 Docker Hub API
        api_url = f"https://hub.docker.com/v2/repositories/{namespace}/{repo}/tags?page_size=100"
        response = requests.get(api_url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])

            # 过滤掉 latest 和其他特殊标签，只保留版本号
            version_tags = []
            for tag in results:
                name = tag.get('name', '')
                # 匹配语义化版本号
                if re.match(r'^\d+\.\d+', name):
                    version_tags.append(name)

            if version_tags:
                # 简单排序，取第一个（实际可能需要更复杂的版本比较）
                return version_tags[0]

        return None

    except Exception as e:
        print(f"Error getting Docker tag for {image_name}: {e}")
        return None


def get_current_version(app_path: Path) -> Optional[str]:
    """获取应用当前版本"""
    versions = []
    for item in app_path.iterdir():
        if item.is_dir() and re.match(r'^\d+', item.name):
            versions.append(item.name)

    if not versions:
        return None

    # 简单排序获取最新版本
    versions.sort(key=lambda v: [int(x) for x in re.findall(r'\d+', v)], reverse=True)
    return versions[0]


def compare_versions(current: str, latest: str) -> bool:
    """
    比较版本号，判断是否需要更新
    返回 True 表示 latest > current
    """
    def version_tuple(v):
        return tuple(map(int, re.findall(r'\d+', v)))

    try:
        return version_tuple(latest) > version_tuple(current)
    except:
        return False


def create_new_version(app_path: Path, app_name: str, current_version: str, new_version: str) -> bool:
    """创建新版本文件夹"""
    try:
        current_dir = app_path / current_version
        new_dir = app_path / new_version

        if new_dir.exists():
            print(f"  Version {new_version} already exists")
            return False

        # 创建新版本目录
        new_dir.mkdir(parents=True, exist_ok=True)

        # 复制并更新 docker-compose.yml
        compose_file = current_dir / 'docker-compose.yml'
        if compose_file.exists():
            content = compose_file.read_text(encoding='utf-8')
            # 更新镜像版本
            content = re.sub(
                rf'(image:\s*[^:]+:){current_version}',
                rf'\g<1>{new_version}',
                content
            )
            (new_dir / 'docker-compose.yml').write_text(content, encoding='utf-8')

        # 复制 data.yml
        data_file = current_dir / 'data.yml'
        if data_file.exists():
            content = data_file.read_text(encoding='utf-8')
            (new_dir / 'data.yml').write_text(content, encoding='utf-8')

        print(f"  ✓ Created new version {new_version}")
        return True

    except Exception as e:
        print(f"  ✗ Error creating new version: {e}")
        return False


def check_app_updates(apps_dir: Path) -> List[Dict]:
    """检查所有应用的更新"""
    updates = []

    for app_path in sorted(apps_dir.iterdir()):
        if not app_path.is_dir():
            continue

        app_name = app_path.name
        data_yml = app_path / 'data.yml'

        if not data_yml.exists():
            continue

        print(f"\nChecking {app_name}...")

        try:
            # 读取应用元数据
            app_data = load_yaml(str(data_yml))
            github_url = app_data.get('additionalProperties', {}).get('github')

            if not github_url:
                print(f"  No GitHub URL found")
                continue

            # 获取当前版本
            current_version = get_current_version(app_path)
            if not current_version:
                print(f"  No version found")
                continue

            print(f"  Current version: {current_version}")

            # 获取最新版本
            latest_version = get_github_latest_release(github_url)

            if not latest_version:
                print(f"  Could not fetch latest version")
                continue

            print(f"  Latest version: {latest_version}")

            # 比较版本
            if compare_versions(current_version, latest_version):
                print(f"  📦 Update available: {current_version} -> {latest_version}")

                # 创建新版本
                if create_new_version(app_path, app_name, current_version, latest_version):
                    updates.append({
                        'app': app_name,
                        'old_version': current_version,
                        'new_version': latest_version,
                        'github': github_url
                    })
            else:
                print(f"  ✓ Up to date")

        except Exception as e:
            print(f"  ✗ Error: {e}")
            continue

    return updates


def main():
    """主函数"""
    # 获取项目根目录
    root_dir = Path(__file__).parent.parent
    apps_dir = root_dir / 'apps'

    if not apps_dir.exists():
        print("Error: apps directory not found")
        return

    print("=== Starting version check ===")
    print(f"Apps directory: {apps_dir}")

    # 检查更新
    updates = check_app_updates(apps_dir)

    # 输出结果
    print("\n=== Summary ===")
    if updates:
        print(f"Found {len(updates)} updates:")
        for update in updates:
            print(f"  • {update['app']}: {update['old_version']} -> {update['new_version']}")

        # 保存更新信息到 JSON 文件供后续使用
        output_file = root_dir / 'updates.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(updates, f, indent=2, ensure_ascii=False)
        print(f"\nUpdates saved to {output_file}")
    else:
        print("No updates found")


if __name__ == '__main__':
    main()
