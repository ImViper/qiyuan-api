#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Docker Compose 渠道管理助手脚本 - Python版本
"""

import os
import sys
import argparse
from pathlib import Path

# 添加当前目录到路径，以便导入utils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import (
    log_info, log_success, log_warning, log_error,
    get_timestamp, check_go_installed, run_command,
    confirm_action, check_docker_compose_running, ChannelManager
)


class DockerHelper:
    """Docker Compose渠道管理助手"""
    
    def __init__(self, dsn: str = "root:123456@tcp(localhost:3306)/new-api",
                 compose_file: str = "../docker-compose.yml"):
        """
        初始化Docker助手
        
        Args:
            dsn: 数据库连接字符串
            compose_file: Docker Compose文件路径
        """
        self.dsn = dsn
        self.compose_file = compose_file
        self.manager = ChannelManager(dsn)
        
    def check_services(self) -> bool:
        """检查Docker服务状态"""
        log_info("Checking Docker Compose service status...")
        
        # 检查MySQL服务是否运行
        if not check_docker_compose_running('mysql', self.compose_file):
            log_error("MySQL service is not running")
            print("Please start Docker Compose service first:")
            print(f"  cd .. && docker-compose up -d")
            return False
        
        log_success("MySQL service is running")
        
        # 测试数据库连接
        log_info("Testing database connection...")
        count = self.manager.count_channels()
        
        if count is not None:
            log_success("Database connection successful")
            print(f"Found {count} channels")
            return True
        else:
            log_error("Database connection failed")
            print("Please check:")
            print("  1. MySQL service is running")
            print("  2. Port mapping is correct")
            print("  3. Database connection string is correct")
            return False
    
    def export_channels(self, format: str = 'json', output: str = None) -> bool:
        """
        导出渠道数据
        
        Args:
            format: 导出格式 (json, csv, txt)
            output: 输出文件路径
        
        Returns:
            是否成功
        """
        if not output:
            timestamp = get_timestamp()
            output = f"channels_export_{timestamp}.{format}"
        
        log_info(f"Exporting channel data in {format} format...")
        
        if self.manager.export(output, format=format, verbose=True):
            log_success(f"Channel data exported to: {output}")
            return True
        else:
            log_error("Export failed")
            return False
    
    def backup_channels(self, output: str = None) -> bool:
        """
        备份渠道数据
        
        Args:
            output: 输出文件路径
        
        Returns:
            是否成功
        """
        if not output:
            timestamp = get_timestamp()
            output = f"channels_backup_{timestamp}.json"
        
        log_info("Backing up channel data...")
        
        if self.manager.backup(output, verbose=True):
            log_success(f"Channel data backed up to: {output}")
            return True
        else:
            log_error("Backup failed")
            return False
    
    def import_channels(self, input_file: str, mode: str = 'skip') -> bool:
        """
        导入渠道数据
        
        Args:
            input_file: 输入文件路径
            mode: 导入模式 (skip: 跳过重复, update: 更新重复)
        
        Returns:
            是否成功
        """
        if not os.path.exists(input_file):
            log_error(f"File not found: {input_file}")
            return False
        
        log_info(f"Importing channel data from: {input_file}")
        
        skip_existing = (mode == 'skip')
        
        if mode == 'update':
            log_warning("Will update existing channels")
        else:
            log_info("Will skip existing channels")
        
        # 先进行模拟导入
        log_info("Running simulation import...")
        if self.manager.import_channels(input_file, skip_existing=skip_existing, 
                                       dry_run=True, verbose=False):
            print()
            if confirm_action("Confirm actual import?"):
                log_info("Running actual import...")
                if self.manager.import_channels(input_file, skip_existing=skip_existing,
                                               dry_run=False, verbose=True):
                    log_success("Import completed")
                    return True
                else:
                    log_error("Import failed")
                    return False
            else:
                log_info("Import cancelled")
                return False
        else:
            log_error("Simulation import failed")
            return False
    
    def restore_channels(self, input_file: str) -> bool:
        """
        恢复渠道数据（会删除现有数据）
        
        Args:
            input_file: 备份文件路径
        
        Returns:
            是否成功
        """
        if not os.path.exists(input_file):
            log_error(f"Backup file not found: {input_file}")
            return False
        
        log_warning("Restore operation will delete all existing channel data!")
        print(f"Backup file: {input_file}")
        print()
        
        if confirm_action("Confirm restore operation?"):
            log_info("Running restore operation...")
            if self.manager.restore(input_file, verbose=True):
                log_success("Restore completed")
                return True
            else:
                log_error("Restore failed")
                return False
        else:
            log_info("Restore cancelled")
            return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Docker Compose 渠道管理助手',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # check命令
    check_parser = subparsers.add_parser('check', 
                                         help='检查 Docker 服务状态和连接')
    
    # export命令
    export_parser = subparsers.add_parser('export', 
                                          help='导出渠道数据')
    export_parser.add_argument('format', nargs='?', default='json',
                              choices=['json', 'csv', 'txt'],
                              help='导出格式 (默认: json)')
    export_parser.add_argument('output', nargs='?',
                              help='输出文件路径')
    
    # backup命令
    backup_parser = subparsers.add_parser('backup', 
                                          help='备份渠道数据（完整备份）')
    backup_parser.add_argument('output', nargs='?',
                              help='输出文件路径')
    
    # import命令
    import_parser = subparsers.add_parser('import', 
                                          help='导入渠道数据')
    import_parser.add_argument('input', help='输入文件路径')
    import_parser.add_argument('mode', nargs='?', default='skip',
                              choices=['skip', 'update'],
                              help='导入模式 (默认: skip)')
    
    # restore命令
    restore_parser = subparsers.add_parser('restore', 
                                           help='恢复渠道数据（删除现有数据）')
    restore_parser.add_argument('input', help='备份文件路径')
    
    # 通用参数
    parser.add_argument('--dsn', default='root:123456@tcp(localhost:3306)/new-api',
                       help='数据库连接字符串')
    parser.add_argument('--compose-file', default='../docker-compose.yml',
                       help='Docker Compose文件路径')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        print("\n示例:")
        print(f"  {sys.argv[0]} check                      # 检查服务状态")
        print(f"  {sys.argv[0]} export json                # 导出为JSON")
        print(f"  {sys.argv[0]} export csv channels.csv    # 导出为CSV")
        print(f"  {sys.argv[0]} backup                     # 创建备份")
        print(f"  {sys.argv[0]} import channels.json       # 导入数据")
        print(f"  {sys.argv[0]} restore backup.json        # 恢复备份")
        return 1
    
    # 检查Go环境
    if not check_go_installed():
        log_error("Go 运行环境未找到")
        return 1
    
    # 创建Docker助手
    helper = DockerHelper(dsn=args.dsn, compose_file=args.compose_file)
    
    # 执行命令
    if args.command == 'check':
        return 0 if helper.check_services() else 1
    
    elif args.command == 'export':
        return 0 if helper.export_channels(args.format, args.output) else 1
    
    elif args.command == 'backup':
        return 0 if helper.backup_channels(args.output) else 1
    
    elif args.command == 'import':
        return 0 if helper.import_channels(args.input, args.mode) else 1
    
    elif args.command == 'restore':
        return 0 if helper.restore_channels(args.input) else 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())