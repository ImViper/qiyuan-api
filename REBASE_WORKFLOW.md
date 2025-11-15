# Fork 仓库同步与 Rebase 操作流程

## 项目背景

- **上游仓库 (upstream)**: `https://github.com/QuantumNous/new-api.git`
- **Fork 仓库 (origin)**: `https://github.com/ImViper/qiyuan-api.git`
- **主分支 (main)**: 保持与上游完全一致
- **开发分支 (qiyuan-api)**: 基于 main，包含自定义改动

## 相关文档

- **REBASE_WORKFLOW.md**（本文档）: 同步和 rebase 的操作流程
- **UPSTREAM_CHANGELOG.md**: 记录每次从上游同步的更新内容

**推荐做法：** 每次同步后更新 UPSTREAM_CHANGELOG.md，记录新功能和重要修复，方便以后查阅。

## 定期同步流程

### 前置检查

```bash
# 1. 查看当前状态
git status

# 2. 查看远程仓库配置
git remote -v

# 3. 查看分支关系
git branch -vv
```

**预期输出：**
```
origin    https://github.com/ImViper/qiyuan-api.git (fetch)
origin    https://github.com/ImViper/qiyuan-api.git (push)
upstream  https://github.com/QuantumNous/new-api.git (fetch)
upstream  https://github.com/QuantumNous/new-api.git (push)
```

### Step 1: 获取最新代码

```bash
# 从所有远程仓库拉取最新代码
git fetch --all
```

**检查点：** 查看输出，确认上游是否有新的提交和标签。

### Step 2: 分析差异

```bash
# 检查本地 main 是否落后
git log main..upstream/main --oneline

# 检查本地 main 是否有额外提交（应该为空）
git log upstream/main..main --oneline

# 检查 qiyuan-api 领先 main 的提交
git log main..qiyuan-api --oneline
```

**预期结果：**
- main 应该落后或等于 upstream/main
- main 不应该有领先 upstream/main 的提交
- qiyuan-api 有你的自定义提交

### Step 3: 更新本地 main

```bash
# 切换到 main 分支
git checkout main

# 拉取最新代码（应该是 fast-forward）
git pull origin main

# 或者直接从上游拉取
# git pull upstream main
```

**检查点：** 确认是 fast-forward 合并，没有冲突。

```bash
# 验证 main 已同步
git log --oneline -5
git status
```

### Step 4: 记录更新内容（可选但推荐）

在 rebase 之前，记录本次从上游同步的更新内容，方便以后查阅。

```bash
# 记录本次更新的起止提交
OLD_COMMIT=$(git rev-parse main)  # rebase 前的 main
# 更新 main 后再执行
NEW_COMMIT=$(git rev-parse main)  # rebase 后的 main

# 查看更新概览
git log ${OLD_COMMIT}..${NEW_COMMIT} --oneline --reverse

# 查看详细信息（包括日期和作者）
git log ${OLD_COMMIT}..${NEW_COMMIT} --pretty=format:"%h|%s|%an|%ad" --date=short

# 查看版本标签
git log ${OLD_COMMIT}..${NEW_COMMIT} --decorate --oneline | grep "tag:"

# 查看文件变更统计
git diff ${OLD_COMMIT}..${NEW_COMMIT} --stat
```

**更新 UPSTREAM_CHANGELOG.md：**
- 在文件顶部添加新的同步记录
- 记录版本范围、主要功能、bug修复
- 标注对你项目的影响
- 参考现有格式进行补充

### Step 5: Rebase 开发分支

```bash
# 切换到开发分支
git checkout qiyuan-api

# 确认工作区干净
git status

# Rebase 到最新的 main
git rebase main
```

**可能的结果：**

#### ✅ 无冲突（最理想）
```
Successfully rebased and updated refs/heads/qiyuan-api.
```

#### ⚠️ 有冲突
```
CONFLICT (content): Merge conflict in xxx
error: could not apply xxx...
```

**解决冲突步骤：**
1. 查看冲突文件：`git status`
2. 手动编辑冲突文件，解决标记
3. 添加解决后的文件：`git add <file>`
4. 继续 rebase：`git rebase --continue`
5. 如果需要放弃：`git rebase --abort`

### Step 6: 验证 Rebase 结果

```bash
# 查看提交历史，确认你的提交在最上面
git log --oneline --graph -10

# 检查分支状态
git status
```

**预期输出：**
```
Your branch and 'origin/qiyuan-api' have diverged,
and have X and Y different commits each, respectively.
```

这是正常的！因为 rebase 改写了提交历史。

### Step 7: 提交更新日志（如果有修改）

如果你在 Step 4 更新了 `UPSTREAM_CHANGELOG.md`，现在提交它：

```bash
# 查看修改
git diff UPSTREAM_CHANGELOG.md

# 添加文件
git add UPSTREAM_CHANGELOG.md

# 提交（使用合适的消息格式）
git commit -m "docs: 更新上游同步日志 (vX.X.X → vY.Y.Y)

记录 ${OLD_COMMIT:0:8}..${NEW_COMMIT:0:8} 的更新内容

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Step 8: 推送到远程

```bash
# 使用 force-with-lease 安全地强制推送
git push origin qiyuan-api --force-with-lease
```

**注意：**
- `--force-with-lease` 比 `--force` 更安全
- 如果远程有其他人的新提交，会拒绝推送
- 如果确定要覆盖，使用 `--force`

### Step 9: 最终验证

```bash
# 查看远程分支状态
git log origin/qiyuan-api --oneline -5

# 确认本地和远程一致
git status
```

**预期输出：**
```
On branch qiyuan-api
Your branch is up to date with 'origin/qiyuan-api'.
nothing to commit, working tree clean
```

## 完整脚本（无冲突情况）

```bash
#!/bin/bash

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Fork 仓库同步脚本 ===${NC}"

# 安全检查
if [ -n "$(git status --porcelain)" ]; then
  echo -e "${RED}错误：工作区有未提交的改动，请先处理${NC}"
  git status --short
  exit 1
fi

# 确认当前在 qiyuan-api 分支
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "qiyuan-api" ]; then
  echo -e "${YELLOW}当前分支: $CURRENT_BRANCH，切换到 qiyuan-api${NC}"
  git checkout qiyuan-api
fi

# 1. 拉取最新代码
echo -e "\n${GREEN}=== Step 1: 拉取所有远程更新 ===${NC}"
git fetch --all

# 2. 记录当前 main 的提交（用于后续生成更新日志）
OLD_MAIN=$(git rev-parse main)
echo -e "${YELLOW}当前 main: ${OLD_MAIN:0:8}${NC}"

# 3. 更新 main
echo -e "\n${GREEN}=== Step 2: 更新 main 分支 ===${NC}"
git checkout main
git pull origin main

# 4. 记录更新后的 main
NEW_MAIN=$(git rev-parse main)
echo -e "${YELLOW}更新后 main: ${NEW_MAIN:0:8}${NC}"

# 5. 显示更新概览
if [ "$OLD_MAIN" != "$NEW_MAIN" ]; then
  echo -e "\n${GREEN}=== 本次更新内容概览 ===${NC}"
  COMMIT_COUNT=$(git rev-list --count ${OLD_MAIN}..${NEW_MAIN})
  echo -e "${YELLOW}新增 $COMMIT_COUNT 个提交${NC}"

  # 显示版本标签
  echo -e "\n${GREEN}新增版本标签:${NC}"
  git log ${OLD_MAIN}..${NEW_MAIN} --decorate --oneline | grep "tag:" || echo "无新标签"

  # 显示最近 5 个提交
  echo -e "\n${GREEN}最近 5 个提交:${NC}"
  git log ${OLD_MAIN}..${NEW_MAIN} --oneline -5

  # 提示更新日志
  echo -e "\n${YELLOW}提示: 建议在 rebase 后更新 UPSTREAM_CHANGELOG.md${NC}"
  echo -e "${YELLOW}使用以下命令查看详细更新:${NC}"
  echo -e "  git log ${OLD_MAIN:0:8}..${NEW_MAIN:0:8} --oneline"
else
  echo -e "${YELLOW}main 分支无更新${NC}"
fi

# 6. Rebase qiyuan-api
echo -e "\n${GREEN}=== Step 3: Rebase qiyuan-api 分支 ===${NC}"
git checkout qiyuan-api
git rebase main

# 7. 检查是否有冲突
if [ $? -ne 0 ]; then
  echo -e "${RED}错误：Rebase 遇到冲突，请手动解决${NC}"
  echo -e "${YELLOW}解决冲突后:${NC}"
  echo -e "  git add <文件>"
  echo -e "  git rebase --continue"
  echo -e "${YELLOW}或放弃 rebase:${NC}"
  echo -e "  git rebase --abort"
  exit 1
fi

# 8. 显示 rebase 结果
echo -e "\n${GREEN}=== Rebase 成功！===${NC}"
git log --oneline --graph -10

# 9. 推送确认
echo -e "\n${YELLOW}准备推送到远程...${NC}"
read -p "确认推送? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo -e "${GREEN}=== 推送到远程 ===${NC}"
  git push origin qiyuan-api --force-with-lease

  if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✅ 同步完成！${NC}"
    git status
  else
    echo -e "\n${RED}推送失败，请检查错误信息${NC}"
    exit 1
  fi
else
  echo -e "${YELLOW}已取消推送${NC}"
  echo -e "稍后手动推送: git push origin qiyuan-api --force-with-lease"
fi

# 10. 提醒更新日志
if [ "$OLD_MAIN" != "$NEW_MAIN" ]; then
  echo -e "\n${YELLOW}📝 别忘了更新 UPSTREAM_CHANGELOG.md！${NC}"
  echo -e "记录范围: ${OLD_MAIN:0:8}..${NEW_MAIN:0:8}"
fi
```

**使用方法：**
```bash
# 保存为 sync-fork.sh
chmod +x sync-fork.sh
./sync-fork.sh
```

## 常见问题

### Q1: 为什么要用 rebase 而不是 merge？

**A:**
- **Rebase**: 保持线性历史，你的提交干净地叠在 main 上
- **Merge**: 会产生 merge commit，历史分叉

对于 fork 仓库的个人开发分支，rebase 更清晰。

### Q2: rebase 后分支显示 "diverged" 是正常的吗？

**A:** 完全正常！rebase 会改写提交的 hash，所以本地和远程历史不同了。这时必须用 force push。

### Q3: 什么时候用 --force-with-lease vs --force？

**A:**
- **--force-with-lease**: 如果远程有你不知道的新提交，会拒绝推送（更安全）
- **--force**: 无条件覆盖远程（危险，但有时必要）

个人分支一般用 `--force-with-lease` 即可。

### Q4: 如果 rebase 搞砸了怎么办？

**A:** 使用 reflog 回滚：

```bash
# 查看操作历史
git reflog

# 回到 rebase 之前的状态
git reset --hard HEAD@{n}  # n 是 reflog 里的序号
```

### Q5: scripts/ 目录切换分支时有残留文件正常吗？

**A:** 正常。Git 切换分支时：
- **删除 tracked 的文件**
- **保留 untracked 的文件**

如果看到 untracked 文件，可以：
```bash
# 清理所有 untracked 文件（谨慎使用！）
git clean -fd

# 或者切回原分支
git checkout qiyuan-api
```

### Q6: 如何快速生成更新日志？

**A:** 使用以下命令提取关键信息：

```bash
# 记录本次同步的范围
OLD_COMMIT="70f8a59a"  # 替换为实际的旧提交
NEW_COMMIT="e07347ac"  # 替换为实际的新提交

# 生成提交列表
git log ${OLD_COMMIT}..${NEW_COMMIT} --oneline --reverse > commits.txt

# 生成详细信息（带日期和作者）
git log ${OLD_COMMIT}..${NEW_COMMIT} --pretty=format:"%h|%s|%an|%ad" --date=short > commits_detail.txt

# 查看新增的版本标签
git log ${OLD_COMMIT}..${NEW_COMMIT} --decorate --oneline | grep "tag:"

# 查看文件变更统计
git diff ${OLD_COMMIT}..${NEW_COMMIT} --stat

# 查看某个具体功能的提交
git log ${OLD_COMMIT}..${NEW_COMMIT} --oneline --grep="keyword"
```

然后参考 `UPSTREAM_CHANGELOG.md` 的格式，整理成易读的更新日志。

### Q7: 多久需要同步一次上游？

**A:** 建议：
- **日常开发**: 每 1-2 周同步一次
- **有重要修复**: 立即同步
- **长期未开发**: 开始开发前先同步

定期同步的好处：
- 减少冲突的复杂度
- 及时获得 bug 修复
- 保持与上游功能一致

## 注意事项

1. **永远不要在 main 分支上开发**，main 只用于同步上游
2. **rebase 前确保工作区干净**，没有未提交的改动
3. **force push 前三思**，确认是你自己的分支
4. **定期同步**，避免落后太多导致冲突复杂化
5. **重要改动前先备份**，创建临时分支：`git branch backup-qiyuan-api`
6. **记录每次同步**，更新 UPSTREAM_CHANGELOG.md，方便以后查阅
7. **提交信息规范**，使用 conventional commits 格式（feat, fix, docs 等）

## 快速参考

### Git 命令

| 命令 | 说明 |
|------|------|
| `git fetch --all` | 拉取所有远程更新 |
| `git checkout main && git pull` | 更新 main |
| `git checkout qiyuan-api && git rebase main` | Rebase 开发分支 |
| `git push origin qiyuan-api --force-with-lease` | 强制推送 |
| `git rebase --abort` | 放弃 rebase |
| `git rebase --continue` | 解决冲突后继续 |
| `git reflog` | 查看操作历史（用于回滚） |

### 分析命令

| 命令 | 说明 |
|------|------|
| `git log A..B --oneline` | 查看 B 领先 A 的提交 |
| `git log A..B --stat` | 查看文件变更统计 |
| `git log --decorate --oneline \| grep "tag:"` | 查看版本标签 |
| `git diff A..B --stat` | 查看两个提交间的差异统计 |

### 快捷流程

```bash
# 完整同步流程（一行版）
git fetch --all && git checkout main && git pull && git checkout qiyuan-api && git rebase main && git push origin qiyuan-api --force-with-lease

# 检查上游是否有更新
git fetch --all && git log main..upstream/main --oneline

# 查看 qiyuan-api 的自定义提交
git log main..qiyuan-api --oneline

# 创建备份分支
git branch backup-$(date +%Y%m%d)
```

## 更新历史

- **2025-11-16**: 初始版本，记录完整 rebase 流程
- **2025-11-16**: 添加更新日志记录步骤、完善脚本、增加常见问题 Q6-Q7
