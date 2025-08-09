#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用工具库 - 提供跨平台的公共功能
"""

import os
import sys
import json
import platform
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple


class Colors:
    """终端颜色输出类（跨平台兼容）"""
    def __init__(self):
        self.use_colors = sys.stdout.isatty()
        
        if platform.system() == 'Windows':
            # Windows 10+ 支持 ANSI 颜色
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        
        self.RED = '\033[0;31m' if self.use_colors else ''
        self.GREEN = '\033[0;32m' if self.use_colors else ''
        self.YELLOW = '\033[1;33m' if self.use_colors else ''
        self.BLUE = '\033[0;34m' if self.use_colors else ''
        self.NC = '\033[0m' if self.use_colors else ''  # No Color


colors = Colors()


def log_info(message: str):
    """输出信息日志"""
    print(f"{colors.BLUE}[INFO]{colors.NC} {message}")


def log_success(message: str):
    """输出成功日志"""
    print(f"{colors.GREEN}[SUCCESS]{colors.NC} {message}")


def log_warning(message: str):
    """输出警告日志"""
    print(f"{colors.YELLOW}[WARNING]{colors.NC} {message}")


def log_error(message: str):
    """输出错误日志"""
    print(f"{colors.RED}[ERROR]{colors.NC} {message}")


def get_timestamp(format_str: str = "%Y%m%d_%H%M%S") -> str:
    """获取时间戳"""
    return datetime.now().strftime(format_str)


def check_go_installed() -> bool:
    """检查Go是否已安装"""
    return shutil.which('go') is not None


def run_command(cmd: List[str], capture_output: bool = False, 
                verbose: bool = False, check: bool = True) -> Tuple[int, str, str]:
    """
    执行命令并返回结果
    
    Args:
        cmd: 命令列表
        capture_output: 是否捕获输出
        verbose: 是否显示详细输出
        check: 是否检查返回码
    
    Returns:
        (return_code, stdout, stderr)
    """
    if verbose:
        log_info(f"执行命令: {' '.join(cmd)}")
    
    try:
        if capture_output:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            return result.returncode, result.stdout, result.stderr
        else:
            result = subprocess.run(cmd, check=check)
            return result.returncode, "", ""
    except subprocess.CalledProcessError as e:
        if check:
            raise
        return e.returncode, "", str(e)
    except Exception as e:
        log_error(f"命令执行失败: {e}")
        return -1, "", str(e)


def ensure_directory(path: str) -> Path:
    """确保目录存在"""
    dir_path = Path(path)
    if not dir_path.exists():
        dir_path.mkdir(parents=True, exist_ok=True)
        log_info(f"创建目录: {path}")
    return dir_path


def read_json_file(file_path: str) -> Optional[Dict[Any, Any]]:
    """读取JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log_error(f"读取JSON文件失败 {file_path}: {e}")
        return None


def write_json_file(file_path: str, data: Dict[Any, Any], indent: int = 2) -> bool:
    """写入JSON文件"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        return True
    except Exception as e:
        log_error(f"写入JSON文件失败 {file_path}: {e}")
        return False


def confirm_action(prompt: str, confirm_text: Optional[str] = None) -> bool:
    """
    确认操作
    
    Args:
        prompt: 提示信息
        confirm_text: 需要输入的确认文本（如 'RESET'），None 则使用 y/n
    
    Returns:
        是否确认
    """
    if confirm_text:
        response = input(f"{prompt} 输入 '{confirm_text}' 确认: ")
        return response == confirm_text
    else:
        response = input(f"{prompt} (y/n): ").lower()
        return response in ['y', 'yes']


def list_files_in_directory(directory: str, pattern: str = "*.json") -> List[str]:
    """列出目录中的文件"""
    dir_path = Path(directory)
    if not dir_path.exists():
        return []
    
    files = list(dir_path.glob(pattern))
    return [str(f) for f in files]


def get_file_info(file_path: str) -> Optional[Dict[str, Any]]:
    """获取文件信息"""
    path = Path(file_path)
    if not path.exists():
        return None
    
    stat = path.stat()
    return {
        'name': path.name,
        'size': stat.st_size,
        'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
        'path': str(path.absolute())
    }


class ChannelManager:
    """渠道管理器封装类"""
    
    def __init__(self, dsn: str = "root:123456@tcp(localhost:3306)/new-api", 
                 script_dir: Optional[str] = None):
        """
        初始化渠道管理器
        
        Args:
            dsn: 数据库连接字符串
            script_dir: 脚本目录路径
        """
        self.dsn = dsn
        self.script_dir = script_dir or os.path.dirname(os.path.abspath(__file__))
        
    def _build_cmd(self, action: str, **kwargs) -> List[str]:
        """构建channel_manager.go命令"""
        cmd = ['go', 'run', os.path.join(self.script_dir, 'channel_manager.go')]
        cmd.extend([f'-action={action}', f'-dsn={self.dsn}'])
        
        for key, value in kwargs.items():
            if value is not None and value != '':
                if isinstance(value, bool):
                    if value:
                        cmd.append(f'-{key}')
                else:
                    cmd.append(f'-{key}={value}')
        
        return cmd
    
    def export(self, output: str, format: str = 'json', verbose: bool = False) -> bool:
        """导出渠道数据"""
        cmd = self._build_cmd('export', output=output, format=format, verbose=verbose)
        returncode, _, _ = run_command(cmd, verbose=verbose, check=False)
        return returncode == 0
    
    def backup(self, output: str, verbose: bool = False) -> bool:
        """备份渠道数据"""
        cmd = self._build_cmd('backup', output=output, verbose=verbose)
        returncode, _, _ = run_command(cmd, verbose=verbose, check=False)
        return returncode == 0
    
    def restore(self, input_file: str, verbose: bool = False) -> bool:
        """恢复渠道数据"""
        cmd = self._build_cmd('restore', input=input_file, verbose=verbose)
        returncode, _, _ = run_command(cmd, verbose=verbose, check=False)
        return returncode == 0
    
    def import_channels(self, input_file: str, skip_existing: bool = True, 
                       dry_run: bool = False, verbose: bool = False) -> bool:
        """导入渠道数据"""
        kwargs = {'input': input_file, 'verbose': verbose}
        if dry_run:
            kwargs['dry-run'] = True
        if skip_existing:
            kwargs['skip-existing'] = True
        else:
            kwargs['update-existing'] = True
            
        cmd = self._build_cmd('import', **kwargs)
        returncode, _, _ = run_command(cmd, verbose=verbose, check=False)
        return returncode == 0
    
    def count_channels(self) -> Optional[int]:
        """统计渠道数量"""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            if self.export(tmp_path, verbose=False):
                data = read_json_file(tmp_path)
                if data:
                    return data.get('total_channels', 0)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        
        return None


def check_docker_compose_running(service_name: str = 'mysql', 
                                compose_file: str = '../docker-compose.yml') -> bool:
    """检查Docker Compose服务是否运行"""
    cmd = ['docker-compose', '-f', compose_file, 'ps']
    returncode, stdout, _ = run_command(cmd, capture_output=True, check=False)
    
    if returncode != 0:
        return False
    
    # 检查服务是否在运行
    for line in stdout.split('\n'):
        if service_name in line and 'Up' in line:
            return True
    
    return False


def parse_args_with_defaults(args: List[str], defaults: Dict[str, Any]) -> Dict[str, Any]:
    """解析命令行参数并合并默认值"""
    result = defaults.copy()
    i = 0
    
    while i < len(args):
        arg = args[i]
        
        # 处理 --key=value 格式
        if '=' in arg and arg.startswith('--'):
            key, value = arg[2:].split('=', 1)
            result[key.replace('-', '_')] = value
            i += 1
        # 处理 --key value 格式
        elif arg.startswith('--'):
            key = arg[2:].replace('-', '_')
            if i + 1 < len(args) and not args[i + 1].startswith('-'):
                result[key] = args[i + 1]
                i += 2
            else:
                result[key] = True
                i += 1
        # 处理 -k value 格式
        elif arg.startswith('-') and len(arg) == 2:
            key = arg[1]
            if i + 1 < len(args) and not args[i + 1].startswith('-'):
                result[key] = args[i + 1]
                i += 2
            else:
                result[key] = True
                i += 1
        else:
            # 位置参数
            if 'positional' not in result:
                result['positional'] = []
            result['positional'].append(arg)
            i += 1
    
    return result