# 数据库表结构说明

本文档详细说明 qiyuan-api 系统中所有数据库表的功能、结构和清理影响。

## 📊 表分类概览

系统共有 12 个主要数据表，按功能分为以下几类：

| 分类 | 表名 | 重要性 | 说明 |
|------|------|--------|------|
| **核心业务表** | channels, users, tokens | CRITICAL/HIGH | 系统运行必需 |
| **业务功能表** | abilities, redemptions, topups | MEDIUM/HIGH | 影响具体功能 |
| **数据记录表** | logs, quota_data, midjourneys, tasks | LOW/MEDIUM | 历史数据 |
| **系统配置表** | options, setups | HIGH/CRITICAL | 系统设置 |

## 🔴 核心业务表（CRITICAL）

### 1. channels - AI模型渠道配置表

**功能**: 存储各种AI模型（OpenAI、Claude、Gemini、通义千问等）的API配置信息

**重要字段**:
- `id`: 渠道ID
- `type`: 渠道类型（24=Gemini, 36=Vertex等）
- `key`: API密钥（支持多个，换行分隔）
- `name`: 渠道名称
- `base_url`: 自定义API地址
- `models`: 支持的模型列表
- `status`: 状态（1=启用, 2=禁用, 3=自动禁用）
- `priority`: 优先级
- `weight`: 负载均衡权重

**清理影响**: 
- ❌ 清空后将丢失所有AI模型接入配置
- ❌ 系统无法调用任何AI服务
- ❌ 需要重新配置所有渠道

---

### 2. users - 用户账户表

**功能**: 存储系统用户信息，包括管理员和普通用户

**重要字段**:
- `id`: 用户ID
- `username`: 用户名
- `password`: 密码哈希
- `role`: 角色（100=普通用户, 10=管理员, 1=超级管理员）
- `status`: 状态（1=正常, 2=禁用）
- `quota`: 配额余额
- `used_quota`: 已使用配额
- `request_count`: 请求次数

**清理影响**: 
- ❌ 清空后所有用户将被删除
- ⚠️ 系统会自动创建默认root账户（密码: 123456）
- ❌ 用户配额信息将丢失

---

### 3. tokens - API令牌表

**功能**: 存储用户的API访问令牌，用于API认证

**重要字段**:
- `id`: 令牌ID
- `user_id`: 所属用户ID
- `key`: 令牌密钥（sk-开头）
- `name`: 令牌名称
- `status`: 状态
- `expired_time`: 过期时间
- `remain_quota`: 剩余配额
- `unlimited_quota`: 是否无限配额

**清理影响**: 
- ❌ 清空后所有API令牌失效
- ❌ 外部应用无法继续使用API
- ⚠️ 用户需要重新生成令牌

## 🟡 业务功能表（HIGH/MEDIUM）

### 4. abilities - 模型能力映射表

**功能**: 定义渠道与模型的能力映射关系和优先级

**重要字段**:
- `group`: 模型组
- `model`: 模型名称
- `channel_id`: 渠道ID
- `enabled`: 是否启用
- `priority`: 优先级（越大越优先）
- `weight`: 权重

**清理影响**: 
- ⚠️ 清空后需要重新配置模型路由规则
- ⚠️ 影响模型选择和负载均衡
- ✅ 不影响基本功能，使用默认路由

---

### 5. redemptions - 兑换码表

**功能**: 存储充值兑换码信息

**重要字段**:
- `id`: 兑换码ID
- `user_id`: 创建用户ID
- `key`: 兑换码
- `status`: 状态（1=未使用, 2=已使用, 3=已禁用）
- `name`: 名称
- `quota`: 额度
- `used_user_id`: 使用者ID

**清理影响**: 
- ⚠️ 清空后所有未使用的兑换码将失效
- ✅ 不影响已充值的余额
- ✅ 可以重新生成兑换码

---

### 6. topups - 充值记录表

**功能**: 记录用户充值历史

**重要字段**:
- `id`: 记录ID
- `user_id`: 用户ID
- `amount`: 充值额度
- `money`: 充值金额
- `trade_no`: 交易单号
- `created_time`: 充值时间
- `status`: 状态

**清理影响**: 
- ✅ 清空后将丢失所有充值记录
- ✅ 不影响用户当前余额
- ⚠️ 无法查询历史充值信息

## 🟢 数据记录表（LOW）

### 7. logs - 系统日志表

**功能**: 记录API调用日志和系统操作日志

**重要字段**:
- `id`: 日志ID
- `user_id`: 用户ID
- `created_at`: 创建时间
- `type`: 日志类型（1=充值, 2=消费, 3=系统）
- `content`: 日志内容
- `model`: 使用的模型
- `token_name`: 使用的令牌
- `quota`: 消耗配额
- `prompt_tokens`: 提示词令牌数
- `completion_tokens`: 完成令牌数

**清理影响**: 
- ✅ 清空后将丢失所有历史日志
- ✅ 不影响系统运行
- ⚠️ 无法进行使用分析

---

### 8. quota_data - 配额使用数据表

**功能**: 记录用户的模型使用量统计

**重要字段**:
- `id`: 记录ID
- `user_id`: 用户ID
- `username`: 用户名
- `model_name`: 模型名称
- `created_at`: 统计时间
- `used_quota`: 使用配额
- `count`: 调用次数

**清理影响**: 
- ✅ 清空后将丢失使用统计数据
- ✅ 不影响配额余额
- ⚠️ 无法生成使用报告

---

### 9. midjourneys - Midjourney任务表

**功能**: 存储Midjourney绘图任务记录

**重要字段**:
- `id`: 记录ID
- `user_id`: 用户ID
- `mj_id`: Midjourney任务ID
- `action`: 操作类型
- `prompt`: 提示词
- `status`: 任务状态
- `image_url`: 生成的图片URL
- `progress`: 进度

**清理影响**: 
- ✅ 清空后将丢失所有MJ任务历史
- ✅ 不影响新任务执行
- ⚠️ 无法查询历史生成的图片

---

### 10. tasks - 异步任务表

**功能**: 存储系统异步任务执行记录

**重要字段**:
- `id`: 任务ID
- `task_id`: 第三方任务ID
- `platform`: 平台（suno, udio等）
- `user_id`: 用户ID
- `action`: 操作类型
- `status`: 任务状态
- `submit_time`: 提交时间
- `start_time`: 开始时间
- `finish_time`: 完成时间
- `result_data`: 结果数据

**清理影响**: 
- ⚠️ 清空后将丢失任务执行历史
- ⚠️ 进行中的任务可能中断
- ✅ 不影响新任务提交

## 🔵 系统配置表（HIGH/CRITICAL）

### 11. options - 系统配置表

**功能**: 存储系统全局配置选项

**重要字段**:
- `key`: 配置键
- `value`: 配置值

**常见配置项**:
- `Notice`: 系统公告
- `SystemName`: 系统名称
- `Theme`: 主题设置
- `RegisterEnabled`: 是否开放注册
- `EmailVerificationEnabled`: 邮箱验证
- `GitHubOAuthEnabled`: GitHub登录
- `WeChatAuthEnabled`: 微信登录

**清理影响**: 
- ⚠️ 清空后系统将使用默认配置
- ⚠️ 需要重新设置所有自定义配置
- ✅ 系统仍可正常运行

---

### 12. setups - 系统初始化表

**功能**: 记录系统初始化状态和版本信息

**重要字段**:
- `id`: 记录ID
- `version`: 系统版本
- `initialized_at`: 初始化时间

**清理影响**: 
- ❌ 清空后系统将认为未初始化
- ⚠️ 可能触发重新初始化流程
- ⚠️ 建议不要清理此表

## 🛠️ 数据库清理工具使用

### 安装依赖

```bash
pip install pymysql
```

### 使用方法

```bash
# 查看所有表信息
python clean_database.py --list

# 显示数据库统计
python clean_database.py --stats

# 交互式清理（推荐）
python clean_database.py

# 清理日志类表
python clean_database.py --clean-logs

# 清理指定表
python clean_database.py --clean logs quota_data

# 清理所有表（危险！）
python clean_database.py --clean-all --confirm

# 不备份直接清理（不推荐）
python clean_database.py --clean logs --no-backup
```

### 安全特性

1. **自动备份**: 清理前自动备份数据到 `backups/` 目录
2. **确认机制**: 清理关键表需要输入 'CLEAN' 确认
3. **影响分析**: 清理前显示详细的影响说明
4. **颜色标识**: 
   - 🔴 CRITICAL - 关键表（红色）
   - 🟡 HIGH - 重要表（黄色）
   - 🔵 MEDIUM - 中等重要（蓝色）
   - 🟢 LOW - 低重要性（绿色）

### 推荐清理策略

#### 1. 日常维护（每周）
```bash
python clean_database.py --clean-logs
```
清理日志类表，释放空间

#### 2. 月度清理
```bash
python clean_database.py --clean logs quota_data midjourneys tasks
```
清理所有历史记录

#### 3. 系统重置
```bash
python clean_database.py --clean-all --confirm
```
完全重置系统（需要重新配置）

#### 4. 保留配置重置
```bash
python clean_database.py --clean logs quota_data midjourneys tasks redemptions topups
```
保留用户、渠道和配置，只清理业务数据

## 🔄 系统自动初始化机制

### 清空所有数据后的自动恢复

当清空所有表数据后，系统重启时会：

1. **自动创建默认账户**
   - 检测到 `users` 表为空时，自动创建root账户
   - 默认用户名：`root`
   - 默认密码：`123456`
   - 默认配额：100,000,000

2. **自动初始化系统**
   - 创建 `setups` 表记录，标记系统已初始化
   - 加载默认系统配置
   - 启用基本功能

3. **需要手动恢复的内容**
   - AI渠道配置（channels表）
   - API访问令牌（tokens表）
   - 模型路由规则（abilities表）
   - 自定义系统设置（options表）

### 快速重置系统

```bash
# 完全重置（清空所有数据）
python clean_database.py --clean-all --confirm

# 重启服务让系统自动初始化
docker-compose restart new-api

# 使用默认账户登录
# 用户名: root
# 密码: 123456
```

## ⚠️ 注意事项

1. **备份优先**: 任何清理操作前都应该备份
2. **影响评估**: 仔细阅读每个表的清理影响
3. **关键表谨慎**: channels、users、setups 表清理需特别谨慎
4. **测试环境**: 建议先在测试环境验证
5. **定期维护**: 定期清理日志表可以提高性能
6. **自动初始化**: 清空users表后系统会自动创建root账户（密码123456）

## 🔄 恢复方法

如果误清理了重要数据，可以从备份恢复：

```bash
# 查看备份文件
ls backups/

# 使用MySQL命令恢复
mysql -u root -p123456 new-api < backups/clean_20240101_120000/channels_20240101_120000.sql
```

或使用恢复脚本：
```bash
python reset_database.py --restore backups/backup.json
```