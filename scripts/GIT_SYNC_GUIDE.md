# Git 仓库同步指令指南

## 🎯 快速指令（告诉 Claude 任意一句即可）

### 最简版（推荐）
```
同步上游到 qiyuan-api
```

### 明确版
```
1. main 同步 upstream
2. qiyuan-api 合并最新改动
```

### 一句话版
```
更新仓库：main镜像upstream，qiyuan-api合并
```

### 技术版
```
git sync: upstream → main → qiyuan-api
```

---

## 📋 执行步骤（自动）

当收到上述任一指令时，Claude 会自动执行：

### 第一阶段：同步 main 分支到 upstream
```bash
git checkout main
git fetch upstream
git reset --hard upstream/main
git push origin main --force-with-lease
```

### 第二阶段：合并到 qiyuan-api
```bash
git checkout qiyuan-api
git merge upstream/main
# 如遇冲突，自动解决（保留本地 MySQL 配置）
git push origin qiyuan-api
```

---

## ⚙️ 冲突解决策略

### docker-compose.yml
- **保留**：MySQL 配置（非 PostgreSQL）
- **保留**：端口 51099（非默认 3000）
- **保留**：MySQL 外部访问端口 3306

### 其他文件
- **保留**：scripts/ 目录所有改动
- **保留**：CLAUDE.md 等文档
- **采纳上游**：代码文件的上游改动
- **特殊处理**：relay/channel/gemini/constant.go（保留 Gemini 2.5 模型）

---

## 📌 注意事项

1. **main 分支**：完全镜像 upstream，不应有本地提交
2. **qiyuan-api 分支**：合并上游同时保留本地改动
3. **数据库配置**：始终保持 MySQL 配置不变
4. **自动操作**：无需手动确认每一步

---

## 🔄 后续维护

下次只需告诉 Claude：
```
按照 GIT_SYNC_GUIDE.md 执行
```

或者直接说：
```
同步上游
```

即可自动完成全部操作！
