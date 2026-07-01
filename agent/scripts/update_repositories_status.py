#!/usr/bin/env python3
import subprocess
import os
from datetime import datetime

def run_git_cmd(args):
    try:
        res = subprocess.run(['git'] + args, capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def get_latest_commit_info(ref):
    # Get hash, author, relative date, and subject
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
    # Returns (ahead, behind)
    try:
        ahead = run_git_cmd(['rev-list', '--count', f'{remote_ref}..{local_ref}'])
        behind = run_git_cmd(['rev-list', '--count', f'{local_ref}..{remote_ref}'])
        return ahead, behind
    except Exception:
        return "N/A", "N/A"

def get_recent_commits(ref, count=5):
    commits_raw = run_git_cmd(['log', f'-{count}', '--format=- `%h` **%an** (%ar): %s', ref])
    if commits_raw.startswith("Error"):
        return "* (无法获取日志)"
    return commits_raw

def main():
    # Make sure we are in the project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    os.chdir(project_root)

    # 1. Fetch current status
    local_info = get_latest_commit_info('main')
    upstream_info = get_latest_commit_info('upstream/main')
    miro_info = get_latest_commit_info('ref-mirofish/main')
    agents_info = get_latest_commit_info('ref-tradingagents/main')

    ahead, behind = get_commit_gap('main', 'upstream/main')

    # 2. Build Markdown
    md = []
    md.append("# 🗺️ 参考项目与上游仓库追踪看板\n")
    md.append(f"> [!NOTE]\n> 本页面由系统自动维护生成。最近更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    md.append("## 📊 追踪仓库最新状态对比\n")
    md.append("| 仓库名称 | 追踪源地址 | 默认分支 | 最新 Commit | 提交作者 | 相对时间 |")
    md.append("|:---|:---|:---|:---|:---|:---|")
    
    # Local
    if local_info:
        md.append(f"| **Vibe-Trading-CNX (本地主分支)** | `skloxo/Vibe-Trading-CNX` | `main` | `{local_info['hash']}` | {local_info['author']} | {local_info['relative_date']} |")
    
    # Upstream
    if upstream_info:
        md.append(f"| **Vibe-Trading (原上游官方库)** | `HKUDS/Vibe-Trading` | `main` | `{upstream_info['hash']}` | {upstream_info['author']} | {upstream_info['relative_date']} |")
    
    # MiroFish
    if miro_info:
        md.append(f"| **MiroFish (参考项目一)** | `666ghj/MiroFish` | `main` | `{miro_info['hash']}` | {miro_info['author']} | {miro_info['relative_date']} |")
    
    # TradingAgents-CN
    if agents_info:
        md.append(f"| **TradingAgents-CN (参考项目二)** | `hsliuping/TradingAgents-CN` | `main` | `{agents_info['hash']}` | {agents_info['author']} | {agents_info['relative_date']} |")
    
    md.append("\n")

    md.append("## 📈 与上游官方版本差异\n")
    md.append(f"- 本地分支比上游官方分支：**领先 {ahead} 个提交**，**落后 {behind} 个提交**。")
    if int(behind) > 0 if behind.isdigit() else False:
        md.append(f"\n> [!TIP]\n> 发现上游官方分支有 {behind} 个新提交。如需查看最新改动，可使用 `git log main..upstream/main` 指令。")
    md.append("\n---\n")

    md.append("## 📜 追踪分支最近提交详情\n")

    # Upstream Commits
    md.append("### 🔗 Vibe-Trading (上游官方) 最近更新\n")
    md.append(get_recent_commits('upstream/main'))
    md.append("\n")

    # MiroFish Commits
    md.append("### 🐟 MiroFish (参考项目一) 最近更新\n")
    md.append(get_recent_commits('ref-mirofish/main'))
    md.append("\n")

    # TradingAgents-CN Commits
    md.append("### 🤖 TradingAgents-CN (参考项目二) 最近更新\n")
    md.append(get_recent_commits('ref-tradingagents/main'))
    md.append("\n")

    # Write output file
    output_path = os.path.join(project_root, 'REPOSITORIES_STATUS.md')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md))
    print(f"Successfully generated {output_path}")

if __name__ == '__main__':
    main()
