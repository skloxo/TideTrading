#!/usr/bin/env bash
# =============================================================================
# sync-upstream.sh — Vibe-Trading-CNX 上游追踪脚本
# =============================================================================
# 背景：
#   Vibe-Trading-CNX 已宣布独立，不再作为 HKUDS/Vibe-Trading 的 fork 维护。
#   上游 remote 已从 "upstream" 改名为 "ref-upstream"（只读参考）。
#   本脚本用于周期性拉取上游代码变更，生成 diff 报告供人工审阅，
#   再由开发者决定是否 cherry-pick 有价值的改动到 CNX 主线。
#
# 使用方式：
#   bash scripts/sync-upstream.sh           # 拉取上游并生成 diff 报告
#   bash scripts/sync-upstream.sh --check   # 仅查看上游新 commits，不生成报告
#   bash scripts/sync-upstream.sh --apply   # 交互式 cherry-pick 模式
#
# 重要：本脚本不会自动 push 或 merge 任何内容。所有合并需人工审阅后执行。
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE="ref-upstream"
UPSTREAM_BRANCH="main"
LOCAL_BRANCH="main"
REPORT_DIR="${REPO_ROOT}/.agents/upstream-sync-reports"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
REPORT_FILE="${REPORT_DIR}/diff_${TIMESTAMP}.md"

cd "$REPO_ROOT"

echo "========================================================"
echo "  Vibe-Trading-CNX 上游追踪脚本 (sync-upstream)"
echo "========================================================"
echo ""
echo "Remote  : ${REMOTE} -> https://github.com/HKUDS/Vibe-Trading.git"
echo "本地分支: ${LOCAL_BRANCH}"
echo ""

# 参数解析
MODE="report"
if [[ "${1:-}" == "--check" ]]; then
    MODE="check"
elif [[ "${1:-}" == "--apply" ]]; then
    MODE="apply"
fi

# Step 1: 拉取上游最新代码（只到本地 ref，不 merge）
echo "[1/3] 拉取上游最新代码到 ${REMOTE} ..."
git fetch "${REMOTE}" "${UPSTREAM_BRANCH}"
echo "      完成。"
echo ""

UPSTREAM_REF="${REMOTE}/${UPSTREAM_BRANCH}"
UPSTREAM_HEAD="$(git rev-parse ${UPSTREAM_REF})"
LOCAL_HEAD="$(git rev-parse ${LOCAL_BRANCH})"
MERGE_BASE="$(git merge-base "${LOCAL_BRANCH}" "${UPSTREAM_REF}" 2>/dev/null || echo '')"

echo "比较信息："
echo "  本地  HEAD : ${LOCAL_HEAD:0:10}..."
echo "  上游  HEAD : ${UPSTREAM_HEAD:0:10}..."
if [[ -n "$MERGE_BASE" ]]; then
    echo "  共同祖先  : ${MERGE_BASE:0:10}..."
fi
echo ""

# Step 2: 列出上游新增 commits
echo "[2/3] 上游新增 commits："
if [[ -n "$MERGE_BASE" ]]; then
    NEW_COMMITS="$(git log --oneline "${MERGE_BASE}..${UPSTREAM_REF}" 2>/dev/null || true)"
else
    NEW_COMMITS="$(git log --oneline "${UPSTREAM_REF}" -20 2>/dev/null || true)"
fi

if [[ -z "$NEW_COMMITS" ]]; then
    echo "  已是最新，上游无新 commits。"
    exit 0
fi

echo "$NEW_COMMITS" | head -30 | sed 's/^/  /'
echo ""

# --check 模式：仅查看，不生成报告
if [[ "$MODE" == "check" ]]; then
    echo "[--check 模式] 仅查看，退出。"
    exit 0
fi

# Step 3: 生成 diff 报告
echo "[3/3] 生成差异报告 ..."
mkdir -p "${REPORT_DIR}"

DIFF_STAT="$(git diff --stat "${LOCAL_BRANCH}...${UPSTREAM_REF}" 2>/dev/null | head -60 || echo '(无法生成 stat)')"

cat > "${REPORT_FILE}" << REPORT
# 上游 Diff 追踪报告

生成时间  : $(date '+%Y-%m-%d %H:%M:%S')
上游 Remote: ${REMOTE} -> https://github.com/HKUDS/Vibe-Trading.git
上游 HEAD  : ${UPSTREAM_HEAD}
本地  HEAD : ${LOCAL_HEAD}
共同祖先   : ${MERGE_BASE:-未知}

---

## 上游新增 Commits

\`\`\`
${NEW_COMMITS}
\`\`\`

---

## 文件级 Diff 摘要（stat）

\`\`\`
${DIFF_STAT}
\`\`\`

---

## 操作建议

- 查看具体文件 diff: git diff ${LOCAL_BRANCH}...${UPSTREAM_REF} -- <file>
- Cherry-pick 单个 commit: git cherry-pick <hash>
- 批量合并: 先 git checkout -b upstream-merge，测试后再合入 main

REPORT

echo "      报告已保存: ${REPORT_FILE}"
echo ""

# --apply 交互式 cherry-pick 模式
if [[ "$MODE" == "apply" ]]; then
    echo "[--apply 模式] 输入要 cherry-pick 的 commit hash（输入 q 退出）："
    echo ""
    git log --oneline "${MERGE_BASE:-}..${UPSTREAM_REF}" | head -30 | sed 's/^/  /'
    echo ""
    while true; do
        read -rp "hash> " hash
        if [[ "$hash" == "q" || -z "$hash" ]]; then
            break
        fi
        echo "  cherry-pick: $hash"
        git cherry-pick "$hash" || echo "  !! 失败，请手动解决冲突后 git cherry-pick --continue"
    done
fi

echo "========================================================"
echo "  完成！报告路径: ${REPORT_FILE}"
echo "========================================================"
