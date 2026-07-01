#!/usr/bin/env python3
import subprocess
import os
import json
from datetime import datetime

def run_git_cmd(args):
    try:
        res = subprocess.run(['git'] + args, capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def get_latest_commit_info(ref):
    info = run_git_cmd(['log', '-1', '--format=%h|%an|%ar|%ad|%s', ref])
    if info.startswith("Error"):
        return None
    parts = info.split('|', 4)
    if len(parts) < 5:
        return None
    return {
        "hash": parts[0],
        "author": parts[1],
        "relative_date": parts[2],
        "date": parts[3],
        "subject": parts[4]
    }

def get_commit_gap(local_ref, remote_ref):
    try:
        ahead = run_git_cmd(['rev-list', '--count', f'{remote_ref}..{local_ref}'])
        behind = run_git_cmd(['rev-list', '--count', f'{local_ref}..{remote_ref}'])
        return ahead, behind
    except Exception:
        return "N/A", "N/A"

def get_recent_commits(ref, count=5):
    commits_raw = run_git_cmd(['log', f'-{count}', '--format=- `%h` **%an** (%ar): %s', ref])
    if commits_raw.startswith("Error") or not commits_raw.strip():
        return "* (暂无提交日志)"
    return commits_raw

def get_commits_since_hashes(ref, seen_hashes, count=100):
    commits_raw = run_git_cmd(['log', f'-{count}', '--format=%h|%an|%ad|%s', ref])
    if commits_raw.startswith("Error") or not commits_raw:
        return []
    
    new_commits = []
    for line in commits_raw.split('\n'):
        parts = line.split('|', 3)
        if len(parts) < 4:
            continue
        h, author, date, subject = parts
        if h in seen_hashes:
            continue
        new_commits.append({
            "hash": h,
            "author": author,
            "date": date,
            "subject": subject
        })
    return new_commits

def get_remote_default_branch(remote_name):
    # Check if refs/remotes/<remote>/HEAD exists (e.g. symbolic link set up by clone)
    # Otherwise check verify refs for common branch names
    for br in ['main', 'master', 'develop']:
        ref_path = f"refs/remotes/{remote_name}/{br}"
        res = run_git_cmd(['show-ref', '--verify', ref_path])
        if not res.startswith("Error"):
            return br
    # Fallback: scan remote branches
    branches_raw = run_git_cmd(['branch', '-r'])
    for line in branches_raw.split('\n'):
        line = line.strip()
        if line.startswith(f"{remote_name}/") and "HEAD" not in line:
            return line.split('/', 1)[1]
    return 'main'

def main():
    # Make sure we are in the project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    os.chdir(project_root)

    # 1. Setup Directories
    logs_dir = os.path.join(project_root, '.agents', 'research_archive', 'repo_sync_logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    state_file = os.path.join(logs_dir, 'seen_commits.json')
    seen_commits = {}
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                seen_commits = json.load(f)
        except Exception:
            seen_commits = {}

    # 2. Dynamically discover tracking remotes
    remotes_raw = run_git_cmd(['remote'])
    if remotes_raw.startswith("Error"):
        print("❌ 获取 remote 列表失败")
        return

    # Upstream is always tracked
    repos = {
        "upstream": {
            "ref": "upstream/main", 
            "name": "Vibe-Trading (原上游官方库)",
            "url": run_git_cmd(['remote', 'get-url', 'upstream'])
        }
    }

    # Gather ref-* remotes
    for remote in remotes_raw.split('\n'):
        remote = remote.strip()
        if remote.startswith('ref-'):
            br = get_remote_default_branch(remote)
            url = run_git_cmd(['remote', 'get-url', remote])
            # Display name formatting
            display_name = remote[4:].replace('_', ' ').replace('-', ' ').title()
            repos[remote] = {
                "ref": f"{remote}/{br}",
                "name": f"{display_name} (参考项目)",
                "url": url
            }

    # 3. Extract New Commits (Deltas)
    today_str = datetime.now().strftime('%Y-%m-%d')
    daily_new_commits = {}

    for key, info in repos.items():
        ref = info["ref"]
        seen_repo_hashes = set(seen_commits.get(key, []))
        
        # Get up to 100 commits from this ref to find new ones
        recent_list = get_commits_since_hashes(ref, seen_repo_hashes, count=100)
        
        if recent_list:
            daily_new_commits[key] = recent_list
            # Update state
            if key not in seen_commits:
                seen_commits[key] = []
            for c in recent_list:
                seen_commits[key].append(c["hash"])

    # 4. If there are new commits, generate/append to Daily Log
    if daily_new_commits:
        daily_log_path = os.path.join(logs_dir, f"{today_str}.md")
        daily_md = []
        if os.path.exists(daily_log_path):
            with open(daily_log_path, 'r', encoding='utf-8') as f:
                daily_md.append(f.read().strip())
            daily_md.append("\n\n---\n")
            daily_md.append(f"### 🔄 追加更新：{datetime.now().strftime('%H:%M:%S')}\n")
        else:
            daily_md.append(f"# 📅 仓库更新增量日志 ({today_str})")
            daily_md.append(f"\n> 最近对账更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        for key, commits in daily_new_commits.items():
            repo_name = repos[key]["name"]
            daily_md.append(f"#### 🔗 {repo_name}")
            for c in commits:
                daily_md.append(f"- `{c['hash']}` **{c['author']}** ({c['date']}): {c['subject']}")
            daily_md.append("")

        with open(daily_log_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(daily_md) + '\n')
        
        # Save updated seen state
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(seen_commits, f, ensure_ascii=False, indent=2)

    # 5. Fetch current status metadata for main board
    local_info = get_latest_commit_info('main')
    ahead, behind = get_commit_gap('main', 'upstream/main')

    # 6. Build Main REPOSITORIES_STATUS.md
    md = []
    md.append("# 🗺️ 参考项目与上游仓库追踪看板\n")
    md.append(f"> [!NOTE]\n> 本页面由系统自动维护生成。最近更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    md.append("## 📊 追踪仓库最新状态对比\n")
    md.append("| 仓库名称 | 追踪源地址 | 默认分支 | 最新 Commit | 提交作者 | 相对时间 |")
    md.append("|:---|:---|:---|:---|:---|:---|")
    
    # Local
    if local_info:
        md.append(f"| **Vibe-Trading-CNX (本地主分支)** | `skloxo/Vibe-Trading-CNX` | `main` | `{local_info['hash']}` | {local_info['author']} | {local_info['relative_date']} |")
    
    # Add all repos sorted by key
    for key in sorted(repos.keys()):
        info = repos[key]
        ref_info = get_latest_commit_info(info["ref"])
        if ref_info:
            md.append(f"| **{info['name']}** | `{info['url'].replace('https://github.com/', '')}` | `{info['ref'].split('/', 1)[1]}` | `{ref_info['hash']}` | {ref_info['author']} | {ref_info['relative_date']} |")
    
    md.append("\n")

    md.append("## 📈 与上游官方版本差异\n")
    md.append(f"- 本地分支比上游官方分支：**领先 {ahead} 个提交**，**落后 {behind} 个提交**。")
    if int(behind) > 0 if behind.isdigit() else False:
        md.append(f"\n> [!TIP]\n> 发现上游官方分支有 {behind} 个新提交。如需查看最新改动，可使用 `git log main..upstream/main` 指令。")
    md.append("\n---\n")

    # Historical Daily Logs List
    md.append("## 📅 历史每日增量日志归档")
    log_files = sorted([f for f in os.listdir(logs_dir) if f.endswith('.md')], reverse=True)
    if log_files:
        for f_name in log_files:
            date_part = f_name.replace('.md', '')
            file_url = f"file://wsl.localhost/Ubuntu-24.04/home/skloxo/aho/openclaw/project/Vibe-Trading/.agents/research_archive/repo_sync_logs/{f_name}"
            md.append(f"- [{date_part} 增量日志]({file_url})")
    else:
        md.append("- 暂无历史增量日志。")
    md.append("\n---\n")

    md.append("## 📜 追踪分支最近提交详情 (Top 5)\n")

    # Add commit details for each remote
    for key in sorted(repos.keys()):
        info = repos[key]
        md.append(f"### 🔗 {info['name']} 最近更新\n")
        md.append(get_recent_commits(info["ref"]))
        md.append("\n")

    # Write output file
    output_path = os.path.join(project_root, 'REPOSITORIES_STATUS.md')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md))
    print(f"Successfully generated {output_path}")

if __name__ == '__main__':
    main()
