# Python脚本说明文档

本目录下的Python脚本是原有批处理(.bat)和Shell脚本(.sh)的跨平台替代版本，解决了原脚本的兼容性问题。

## 特性

- ✅ **跨平台兼容**：同一份代码可在Windows、Linux、macOS上运行
- ✅ **更好的错误处理**：详细的错误信息和异常处理
- ✅ **彩色输出**：在支持的终端中显示彩色日志
- ✅ **统一的参数解析**：使用标准的argparse库处理命令行参数
- ✅ **UTF-8编码支持**：正确处理中文和其他Unicode字符

## 脚本列表

### 1. utils.py - 通用工具库
提供所有脚本共享的工具函数：
- 彩色日志输出
- 命令执行封装
- 文件操作工具
- 渠道管理器封装

### 2. reset_database.py - 数据库重置工具
替代 `reset_database.bat` 和 `reset_database.sh`

**用法：**
```bash
# 完整的备份+重置流程
python reset_database.py

# 仅创建备份
python reset_database.py --backup-only

# 从备份恢复
python reset_database.py --restore backup.json

# 模拟运行
python reset_database.py --dry-run

# 显示帮助
python reset_database.py --help
```

### 3. docker_helper.py - Docker Compose渠道管理助手
替代 `docker_helper.bat` 和 `docker_helper.sh`

**用法：**
```bash
# 检查服务状态
python docker_helper.py check

# 导出渠道数据
python docker_helper.py export json
python docker_helper.py export csv channels.csv

# 备份渠道数据
python docker_helper.py backup
python docker_helper.py backup my_backup.json

# 导入渠道数据
python docker_helper.py import channels.json
python docker_helper.py import channels.json update

# 恢复备份
python docker_helper.py restore backup.json

# 显示帮助
python docker_helper.py --help
```

### 4. run_export.py - 渠道导出快速脚本
替代 `run_export.bat` 和 `run_export.sh`

**用法：**
```bash
# 导出为JSON（默认）
python run_export.py

# 导出为CSV
python run_export.py -f csv

# 导出为文本文件
python run_export.py -f txt -o report.txt

# 显示详细信息
python run_export.py -v

# 显示帮助
python run_export.py --help
```

### 5. test_python_scripts.py - 兼容性测试脚本
用于测试Python脚本的跨平台兼容性

**用法：**
```bash
python test_python_scripts.py
```

## 系统要求

- Python 3.6 或更高版本
- Go 运行环境（用于执行channel_manager.go等Go脚本）
- 数据库连接（MySQL/PostgreSQL/SQLite）

## 安装Python

### Windows
1. 从 [python.org](https://www.python.org/downloads/) 下载安装程序
2. 运行安装程序，勾选 "Add Python to PATH"
3. 验证安装：`python --version`

### Linux/macOS
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3 python3-pip

# CentOS/RHEL
sudo yum install python3 python3-pip

# macOS (使用Homebrew)
brew install python3

# 验证安装
python3 --version
```

## 从批处理/Shell脚本迁移

### Windows用户
原命令：
```batch
reset_database.bat --backup-only
docker_helper.bat export json
run_export.bat
```

新命令：
```batch
python reset_database.py --backup-only
python docker_helper.py export json
python run_export.py
```

### Linux/macOS用户
原命令：
```bash
./reset_database.sh --backup-only
./docker_helper.sh export json
./run_export.sh
```

新命令：
```bash
python3 reset_database.py --backup-only
python3 docker_helper.py export json
python3 run_export.py
```

## 可执行权限（Linux/macOS）

如果想直接执行脚本而不需要输入`python`：

```bash
# 添加执行权限
chmod +x reset_database.py docker_helper.py run_export.py

# 直接执行
./reset_database.py --help
./docker_helper.py check
./run_export.py
```

## 环境变量配置

可以通过环境变量配置数据库连接：

```bash
# Linux/macOS
export MYSQL_DSN="root:password@tcp(localhost:3306)/database"
python3 reset_database.py

# Windows
set MYSQL_DSN=root:password@tcp(localhost:3306)/database
python reset_database.py
```

## 故障排除

### 1. 中文显示乱码（Windows）
在Windows控制台中执行以下命令：
```batch
chcp 65001
```

或在Python脚本开始处添加：
```python
import sys
sys.stdout.reconfigure(encoding='utf-8')
```

### 2. 找不到Go命令
确保Go已安装并添加到PATH环境变量中：
```bash
go version
```

### 3. 权限问题（Linux/macOS）
如果遇到权限错误：
```bash
sudo python3 script_name.py
# 或
chmod +x script_name.py
```

### 4. 模块导入错误
确保在scripts目录下执行脚本，或将scripts目录添加到PYTHONPATH：
```bash
cd scripts
python3 reset_database.py
```

## 优势对比

| 特性 | 批处理/Shell脚本 | Python脚本 |
|------|-----------------|------------|
| 跨平台兼容 | ❌ 需要不同版本 | ✅ 一份代码 |
| 错误处理 | 基础 | 完善 |
| 代码可读性 | 一般 | 优秀 |
| 维护成本 | 高（多份代码） | 低（单份代码） |
| 调试难度 | 困难 | 简单 |
| 功能扩展 | 受限 | 灵活 |
| Unicode支持 | 有限 | 完整 |

## 贡献指南

如果需要添加新功能或修复bug：

1. 所有共享功能应添加到 `utils.py`
2. 保持代码风格一致（PEP 8）
3. 添加适当的错误处理
4. 更新本文档

## 许可证

与主项目保持一致。