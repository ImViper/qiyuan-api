# Scripts 目录

本目录包含用于管理渠道数据的Python脚本和Go工具。

## 🐍 Python脚本（跨平台）

所有Python脚本都支持Windows、Linux和macOS，解决了之前批处理和Shell脚本的兼容性问题。

### 核心脚本

| 脚本名称 | 功能描述 | 使用示例 |
|---------|---------|---------|
| `reset_database.py` | 数据库重置工具，支持备份和恢复 | `python reset_database.py --help` |
| `docker_helper.py` | Docker Compose渠道管理助手 | `python docker_helper.py check` |
| `run_export.py` | 快速导出渠道数据 | `python run_export.py -f json` |
| `test_api_keys.py` | API密钥有效性测试工具（支持Gemini） | `python test_api_keys.py --model gemini-2.5-flash` |
| `export_api_keys.py` | 导出数据库中的API密钥到文件 | `python export_api_keys.py -o keys.txt` |
| `batch_test_keys.py` | 批量测试API密钥（默认gemini-2.5-flash） | `python batch_test_keys.py --workers 10` |
| `utils.py` | 通用工具库（被其他脚本引用） | - |
| `test_python_scripts.py` | 测试脚本兼容性 | `python test_python_scripts.py` |

### 快速开始

```bash
# 检查环境
python test_python_scripts.py

# 备份数据库
python reset_database.py --backup-only

# 导出渠道数据
python run_export.py -f json -o channels.json

# Docker环境管理
python docker_helper.py check
python docker_helper.py export csv
```

详细使用说明请查看 [PYTHON_SCRIPTS_README.md](PYTHON_SCRIPTS_README.md)

## 🔧 Go工具

| 文件名称 | 功能描述 |
|---------|---------|
| `channel_manager.go` | 核心渠道管理器，提供导入/导出/备份/恢复功能 |
| `export_channels.go` | 渠道导出工具，支持多种格式 |
| `test_gemini_keys.go` | Gemini API密钥批量测试工具 |
| `common/types.go` | 共享的类型定义 |
| `go.mod` / `go.sum` | Go模块依赖管理 |

### Go工具使用

```bash
# 导出渠道
go run export_channels.go -format json -output channels.json

# 使用channel_manager
go run channel_manager.go -action=export -format=json -output=channels.json
go run channel_manager.go -action=backup -output=backup.json
go run channel_manager.go -action=restore -input=backup.json
```

## 📁 测试数据

- `test_channels.json` - 测试用的渠道数据样本

## 系统要求

- **Python**: 3.6 或更高版本
- **Go**: 1.16 或更高版本
- **数据库**: MySQL 5.7+ / PostgreSQL 9.6+ / SQLite

## 安装依赖

### Python
Python脚本使用标准库，无需额外安装依赖。

### Go
```bash
cd scripts
go mod tidy
```

## 环境变量

可以通过环境变量配置数据库连接：

```bash
# Linux/macOS
export MYSQL_DSN="root:password@tcp(localhost:3306)/database"

# Windows
set MYSQL_DSN=root:password@tcp(localhost:3306)/database
```

## 🔄 数据库重置

### 安全重置流程

```bash
# 完整的备份+重置流程
python reset_database.py

# 仅创建备份
python reset_database.py --backup-only

# 从备份恢复
python reset_database.py --restore backup.json

# 模拟运行
python reset_database.py --dry-run
```

**重置流程包括：**
1. 🛡️ 自动创建完整备份
2. ⚠️ 确认重置操作（需要输入 'RESET'）
3. 🗑️ 清空所有渠道数据
4. 📋 显示可用备份文件

## Docker Compose 支持

### 使用Docker助手

```bash
# 检查服务状态
python docker_helper.py check

# 导出渠道数据
python docker_helper.py export json
python docker_helper.py export csv channels.csv

# 备份所有渠道
python docker_helper.py backup

# 导入渠道数据
python docker_helper.py import channels.json

# 恢复渠道数据
python docker_helper.py restore backup.json
```

### Docker Compose配置

确保在 `docker-compose.yml` 中启用MySQL端口映射：
```yaml
mysql:
  ports:
    - "3306:3306"  # 启用端口映射以支持脚本连接
```

## 🔑 API密钥测试

### 测试Gemini API密钥有效性

支持多种方式测试和管理Gemini API密钥：

#### 1. 导出API密钥到文件
```bash
# 导出所有启用的Gemini渠道密钥
python export_api_keys.py

# 导出到指定文件
python export_api_keys.py -o api_keys.txt

# 导出为CSV格式（包含渠道信息）
python export_api_keys.py --format csv -o keys.csv

# 导出详细格式（包含注释）
python export_api_keys.py --format detailed

# 包含禁用的渠道
python export_api_keys.py --include-disabled
```

#### 2. 批量测试API密钥（推荐）
```bash
# 从数据库批量测试所有密钥（默认使用gemini-2.5-flash）
python batch_test_keys.py

# 设置并发数
python batch_test_keys.py --workers 10

# 保存测试结果
python batch_test_keys.py --save-results results.txt

# 先导出再测试
python batch_test_keys.py --export-first

# 从文件读取密钥测试
python batch_test_keys.py --from-file api_keys.txt

# 指定其他模型
python batch_test_keys.py --model gemini-2.5-pro
```

#### 3. 单独测试功能
```bash
# 测试所有Gemini渠道
python test_api_keys.py

# 指定测试模型（默认gemini-2.5-flash）
python test_api_keys.py --model gemini-2.5-flash

# 仅测试启用的渠道
python test_api_keys.py --status 1

# 测试特定渠道
python test_api_keys.py --channel-id 5

# 直接测试API密钥（不查询数据库）
python test_api_keys.py --api-key "YOUR_API_KEY"

# 导出测试结果
python test_api_keys.py --export results.json

# 设置并发数
python test_api_keys.py --workers 10

# 列出支持的模型
python test_api_keys.py --list-models
```

#### Go版本
```bash
# 测试所有Gemini渠道
go run test_gemini_keys.go

# 指定测试模型
go run test_gemini_keys.go -model gemini-2.5-flash

# 测试特定渠道
go run test_gemini_keys.go -channel-id 5

# 直接测试API密钥
go run test_gemini_keys.go -api-key "YOUR_API_KEY"

# 导出结果
go run test_gemini_keys.go -export results.json
```

### 支持的Gemini模型

- gemini-2.5-flash （默认，推荐）
- gemini-2.5-pro
- gemini-1.5-pro
- gemini-1.5-flash
- gemini-2.0-flash
- gemini-1.5-flash-8b

### 测试结果说明

测试脚本会：
1. 从数据库查询所有Gemini类型的渠道
2. 并发测试每个渠道的API密钥
3. 显示每个渠道的测试结果和响应时间
4. 生成测试摘要报告
5. 可选导出详细结果到JSON文件

成功标志：
- ✅ API密钥有效
- ❌ API密钥无效或错误

## 故障排除

### Windows中文乱码
```batch
chcp 65001
```

### 权限问题（Linux/macOS）
```bash
chmod +x *.py
```

### Go模块问题
```bash
go mod download
go mod tidy
```

### API测试失败常见原因

1. **403 Forbidden**: API密钥无效或被禁用
2. **429 Too Many Requests**: 达到速率限制
3. **404 Not Found**: 指定的模型不存在
4. **Timeout**: 网络连接问题或API响应慢
5. **Connection Error**: 无法连接到Gemini API服务器

## 为什么使用Python？

- ✅ **跨平台兼容**：一份代码，多平台运行
- ✅ **更好的错误处理**：详细的错误信息和异常处理
- ✅ **易于维护**：代码更清晰，调试更方便
- ✅ **丰富的标准库**：无需额外依赖即可实现复杂功能
- ✅ **Unicode支持**：完美处理中文和其他语言