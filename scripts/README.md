# 渠道管理脚本

这个目录包含用于导入、导出和管理渠道数据的完整工具集。

## 文件说明

### 核心脚本
- `channel_manager.go` - 完整的渠道管理脚本（导入/导出/备份/恢复）
- `export_channels.go` - 轻量级快速导出脚本（简化版本）
- `common/types.go` - 共享类型和工具函数

### 辅助脚本
- `docker_helper.sh` - Docker Compose 环境助手脚本（Linux/macOS）
- `docker_helper.bat` - Docker Compose 环境助手脚本（Windows）
- `reset_database.sh` - 安全数据库重置脚本（Linux/macOS）
- `reset_database.bat` - 安全数据库重置脚本（Windows）
- `run_export.sh` - 快速导出脚本（Linux/macOS）
- `run_export.bat` - 快速导出脚本（Windows）

## 使用方法

### 1. Docker Compose 环境（推荐）

如果您使用 Docker Compose 启动的 MySQL，推荐使用专门的助手脚本：

```bash
# 进入脚本目录
cd scripts

# 检查服务状态和连接
./docker_helper.sh check

# 导出渠道数据
./docker_helper.sh export json
./docker_helper.sh export csv channels.csv

# 备份所有渠道数据
./docker_helper.sh backup

# 导入渠道数据
./docker_helper.sh import channels.json

# 恢复渠道数据
./docker_helper.sh restore backup.json
```

### 2. 基本使用（通用方式）

```bash
# 进入脚本目录
cd scripts

# 导出所有渠道到JSON文件
go run channel_manager.go -action=export

# 导入渠道数据
go run channel_manager.go -action=import -input=channels.json

# 备份渠道数据
go run channel_manager.go -action=backup

# 恢复渠道数据
go run channel_manager.go -action=restore -input=backup.json
```

### 3. 快速导出（轻量级版本）

```bash
# 使用轻量级导出脚本（推荐用于快速导出）
go run export_channels.go

# 导出到指定文件
go run export_channels.go -output my_channels.json

# 不隐藏API密钥
go run export_channels.go -mask-keys=false

# 指定数据库连接
go run export_channels.go -dsn "root:123456@tcp(localhost:3306)/new-api"
```

**注意：** `export_channels.go` 仅支持JSON格式导出。如需CSV、TXT格式，请使用 `channel_manager.go`。

### 4. 高级用法

#### 导出相关

```bash
# 指定数据库连接
go run channel_manager.go -action=export -dsn "root:123456@tcp(localhost:3306)/new-api"

# 仅导出启用的渠道
go run channel_manager.go -action=export -status 1

# 仅导出OpenAI类型的渠道
go run channel_manager.go -action=export -type 1

# 导出为CSV格式
go run channel_manager.go -action=export -format csv

# 不隐藏API密钥（谨慎使用）
go run channel_manager.go -action=export -mask-keys=false

# 显示详细信息
go run channel_manager.go -action=export -verbose
```

#### 导入相关

```bash
# 导入时跳过已存在的渠道（默认）
go run channel_manager.go -action=import -input=channels.json -skip-existing

# 导入时更新已存在的渠道
go run channel_manager.go -action=import -input=channels.json -update-existing

# 模拟导入（不实际操作数据库）
go run channel_manager.go -action=import -input=channels.json -dry-run

# 详细导入过程
go run channel_manager.go -action=import -input=channels.json -verbose
```

#### 备份和恢复

```bash
# 完整备份（包含所有信息）
go run channel_manager.go -action=backup -output=full_backup.json

# 恢复前模拟（推荐）
go run channel_manager.go -action=restore -input=backup.json -dry-run

# 实际恢复（会删除现有数据）
go run channel_manager.go -action=restore -input=backup.json
```

### 5. 数据库连接配置

#### Docker Compose MySQL 配置

如果您使用 Docker Compose，脚本会自动使用以下默认连接：

```bash
# Docker Compose 默认配置
root:123456@tcp(localhost:3306)/new-api
```

**重要提示：**
1. 确保 Docker Compose 中的 MySQL 服务正在运行
2. 如果需要从主机连接，请在 `docker-compose.yml` 中启用端口映射：
   ```yaml
   mysql:
     ports:
       - "3306:3306"  # 取消注释这一行
   ```

#### 连接字符串优先级

脚本会按以下优先级查找数据库连接：

1. 命令行参数 `-dsn`
2. 环境变量 `SQL_DSN`
3. Docker Compose 默认值 `root:123456@tcp(localhost:3306)/new-api`

#### 连接字符串示例

```bash
# Docker Compose MySQL（推荐）
export SQL_DSN="root:123456@tcp(localhost:3306)/new-api"

# 自定义 MySQL
export SQL_DSN="user:password@tcp(localhost:3306)/database"

# PostgreSQL
export SQL_DSN="host=localhost user=username password=password dbname=database sslmode=disable"

# SQLite
export SQL_DSN="sqlite:data/new-api.db"
```

#### Docker 环境检查

使用 Docker 助手脚本可以自动检查环境：

```bash
# 检查 Docker 服务和数据库连接
./docker_helper.sh check

# Windows
docker_helper.bat check
```

### 4. 输出格式

#### JSON格式（默认）
```json
{
  "export_time": "2024-01-01 12:00:00",
  "export_version": "1.0.0", 
  "total_channels": 5,
  "channels": [
    {
      "id": 1,
      "name": "OpenAI官方",
      "type": 1,
      "status": 1,
      "group": "default",
      ...
    }
  ]
}
```

#### CSV格式
包含所有渠道字段的CSV文件，可用Excel打开。

#### TXT格式
人类可读的文本报告格式。

### 5. 渠道类型和状态

**渠道类型：**
- 1: OpenAI
- 3: Azure  
- 21: Anthropic
- 25: Gemini
- 更多类型见脚本中的映射表

**渠道状态：**
- 1: 启用
- 2: 手动禁用
- 3: 自动禁用

### 6. 安全注意事项

- 默认情况下，脚本会隐藏API密钥的敏感部分
- 使用 `-mask-keys=false` 可以导出完整密钥，但请谨慎处理
- 导出的文件可能包含敏感信息，请妥善保管

## 示例用法

```bash
# 快速导出所有渠道（轻量级）
go run export_channels.go

# 导出启用的OpenAI渠道到CSV（完整功能）
go run channel_manager.go -action=export -type 1 -status 1 -format csv -output openai_channels.csv

# 完整导出（包含API密钥）
go run export_channels.go -mask-keys=false -output full_export.json

# 连接远程MySQL数据库
go run channel_manager.go -action=export -dsn "user:pass@tcp(remote-host:3306)/newapi" -verbose
```

## 故障排除

1. **连接数据库失败**
   - 检查数据库连接字符串是否正确
   - 确保数据库服务正在运行
   - 检查网络连接（远程数据库）

2. **权限错误**
   - 确保有数据库读取权限
   - 检查输出目录的写入权限

3. **依赖问题**
   - 运行 `go mod tidy` 安装依赖
   - 确保Go版本兼容

## 🔄 数据库重置

如果您想重置数据库内容并确保数据安全，推荐使用专门的重置脚本：

### 安全重置流程

```bash
# Linux/macOS
./reset_database.sh

# Windows
reset_database.bat
```

**重置流程包括：**
1. 🛡️ 自动创建完整备份
2. ⚠️ 确认重置操作（需要输入 'RESET'）
3. 🗑️ 清空所有渠道数据
4. 📋 显示可用备份文件

### 重置选项

```bash
# 仅创建备份（不重置）
./reset_database.sh --backup-only

# 从备份恢复数据
./reset_database.sh --restore backup.json

# 模拟运行（查看将要执行的操作）
./reset_database.sh --dry-run

# 指定备份目录
./reset_database.sh --backup-dir ./my_backups
```

### ⚠️ 安全提示

1. **自动备份**: 重置前会自动创建带时间戳的备份文件
2. **确认机制**: 必须输入 'RESET' 才能执行重置操作  
3. **恢复支持**: 可以随时从备份文件恢复数据
4. **备份位置**: 默认保存在 `./backups/` 目录

### 常见场景

```bash
# 完整的安全重置（推荐）
./reset_database.sh

# 清理测试数据前先备份
./reset_database.sh --backup-only
# 手动清理后如需恢复
./reset_database.sh --restore backups/reset_backup_20240102_143000.json

# 定期备份
./reset_database.sh --backup-only --backup-dir ./daily_backups
```

## 扩展

可以基于此脚本扩展更多功能：
- 渠道数据备份和恢复
- 渠道配置迁移  
- 渠道状态监控
- 批量渠道管理
- 定时备份任务
- 数据库健康检查