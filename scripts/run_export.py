#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
渠道导出快速运行脚本 - Python版本
"""

import os
import sys
import argparse
from pathlib import Path

# 添加当前目录到路径，以便导入utils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import (
    log_info, log_success, log_error,
    check_go_installed, run_command
)


def export_channels(format: str = 'json', output: str = None, verbose: bool = False) -> bool:
    """
    导出渠道数据
    
    Args:
        format: 导出格式 (json, csv, txt)
        output: 输出文件路径
        verbose: 是否显示详细信息
    
    Returns:
        是否成功
    """
    # 构建命令
    cmd = ['go', 'run', 'export_channels.go', '-format', format]
    
    if output:
        cmd.extend(['-output', output])
    
    if verbose:
        cmd.append('-verbose')
    
    log_info("正在导出渠道数据...")
    if verbose:
        print(f"执行命令: {' '.join(cmd)}")
    
    # 执行导出
    returncode, _, _ = run_command(cmd, verbose=verbose, check=False)
    
    if returncode == 0:
        log_success("✅ 导出完成！")
        return True
    else:
        log_error("❌ 导出失败！")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='渠道导出快速运行脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                          # 导出为JSON
  %(prog)s -f csv                   # 导出为CSV
  %(prog)s -f txt -o report.txt     # 导出为文本文件
  %(prog)s --format json -v         # 导出为JSON并显示详细信息
        """
    )
    
    parser.add_argument('-f', '--format', 
                       default='json',
                       choices=['json', 'csv', 'txt'],
                       help='输出格式 (默认: json)')
    
    parser.add_argument('-o', '--output',
                       help='输出文件路径')
    
    parser.add_argument('-v', '--verbose',
                       action='store_true',
                       help='显示详细信息')
    
    args = parser.parse_args()
    
    # 检查Go环境
    if not check_go_installed():
        log_error("Go 运行环境未找到")
        return 1
    
    # 执行导出
    success = export_channels(
        format=args.format,
        output=args.output,
        verbose=args.verbose
    )
    
    # Windows下pause效果
    if sys.platform == 'win32':
        input("\n按Enter键继续...")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())