# Fork 仓库同步与 Rebase 操作流程

## 项目背景

- **上游仓库 (upstream)**: `https://github.com/QuantumNous/new-api.git`
- **Fork 仓库 (origin)**: `https://github.com/ImViper/qiyuan-api.git`
- **主分支 (main)**: 保持与上游完全一致
- **开发分支 (qiyuan-api)**: 基于 main，包含自定义改动

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

### Step 4: Rebase 开发分支

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

### Step 5: 验证 Rebase 结果

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

### Step 6: 推送到远程

```bash
# 使用 force-with-lease 安全地强制推送
git push origin qiyuan-api --force-with-lease
```

**注意：**
- `--force-with-lease` 比 `--force` 更安全
- 如果远程有其他人的新提交，会拒绝推送
- 如果确定要覆盖，使用 `--force`

### Step 7: 最终验证

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

# 安全检查
if [ -n "$(git status --porcelain)" ]; then
  echo "错误：工作区有未提交的改动，请先处理"
  exit 1
fi

# 1. 拉取最新代码
echo "=== 拉取所有远程更新 ==="
git fetch --all

# 2. 更新 main
echo "=== 更新 main 分支 ==="
git checkout main
git pull origin main

# 3. Rebase qiyuan-api
echo "=== Rebase qiyuan-api 分支 ==="
git checkout qiyuan-api
git rebase main

# 4. 检查是否有冲突
if [ $? -ne 0 ]; then
  echo "错误：Rebase 遇到冲突，请手动解决"
  exit 1
fi

# 5. 推送到远程
echo "=== 推送到远程 ==="
git push origin qiyuan-api --force-with-lease

echo "=== 完成！==="
git status
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

## 注意事项

1. **永远不要在 main 分支上开发**，main 只用于同步上游
2. **rebase 前确保工作区干净**，没有未提交的改动
3. **force push 前三思**，确认是你自己的分支
4. **定期同步**，避免落后太多导致冲突复杂化
5. **重要改动前先备份**，创建临时分支：`git branch backup-qiyuan-api`

## 快速参考

| 命令 | 说明 |
|------|------|
| `git fetch --all` | 拉取所有远程更新 |
| `git checkout main && git pull` | 更新 main |
| `git checkout qiyuan-api && git rebase main` | Rebase 开发分支 |
| `git push origin qiyuan-api --force-with-lease` | 强制推送 |
| `git rebase --abort` | 放弃 rebase |
| `git rebase --continue` | 解决冲突后继续 |
| `git reflog` | 查看操作历史（用于回滚） |

## 最后更新

- 2025-11-16: 初始版本，记录完整 rebase 流程
