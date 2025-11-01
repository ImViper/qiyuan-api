#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库重置脚本 - Python版本
包含完整备份和安全恢复选项
"""

import os
import sys
import argparse
from pathlib import Path

# 添加当前目录到路径，以便导入utils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import (
    log_info, log_success, log_warning, log_error,
    get_timestamp, check_go_installed, ensure_directory,
    write_json_file, read_json_file, confirm_action,
    list_files_in_directory, get_file_info, ChannelManager
)


class DatabaseReset:
    """数据库重置管理类"""
    
    def __init__(self, dsn: str = "root:123456@tcp(localhost:3306)/new-api",
                 backup_dir: str = "./backups"):
        """
        初始化数据库重置管理器
        
        Args:
            dsn: 数据库连接字符串
            backup_dir: 备份目录路径
        """
        self.dsn = dsn
        self.backup_dir = backup_dir
        self.timestamp = get_timestamp()
        self.manager = ChannelManager(dsn)
        
    def create_backup(self, custom_name: str = None) -> str:
        """
        创建数据库备份
        
        Args:
            custom_name: 自定义备份文件名
        
        Returns:
            备份文件路径，失败返回None
        """
        ensure_directory(self.backup_dir)
        
        if custom_name:
            backup_file = os.path.join(self.backup_dir, custom_name)
        else:
            backup_file = os.path.join(self.backup_dir, f"reset_backup_{self.timestamp}.json")
        
        log_info("创建数据库备份...")
        
        if self.manager.backup(backup_file, verbose=True):
            log_success(f"备份已创建: {backup_file}")
            return backup_file
        else:
            log_error("备份创建失败")
            return None
    
    def count_current_data(self) -> int:
        """统计当前数据库内容"""
        log_info("统计当前数据库内容...")
        
        count = self.manager.count_channels()
        if count is not None:
            print(f"当前渠道数量: {count}")
            return count
        else:
            log_warning("无法统计当前数据")
            return 0
    
    def reset_database(self) -> bool:
        """重置数据库（清空所有渠道）"""
        log_warning("⚠️  即将清空所有渠道数据!")
        print("此操作不可逆转，请确保已创建备份")
        print()
        
        if not confirm_action("确认重置数据库?", "RESET"):
            log_info("取消重置操作")
            return False
        
        log_info("正在重置数据库...")
        
        # 创建空的备份文件用于重置
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            empty_data = {
                "export_time": get_timestamp("%Y-%m-%d %H:%M:%S"),
                "export_version": "1.0.0",
                "total_channels": 0,
                "database_info": "Reset Operation",
                "channels": []
            }
            write_json_file(tmp.name, empty_data)
            tmp_path = tmp.name
        
        try:
            if self.manager.restore(tmp_path):
                log_success("数据库已重置")
                return True
            else:
                log_error("数据库重置失败")
                return False
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def restore_database(self, restore_file: str) -> bool:
        """
        从备份文件恢复数据库
        
        Args:
            restore_file: 备份文件路径
        
        Returns:
            是否成功
        """
        if not os.path.exists(restore_file):
            log_error(f"备份文件不存在: {restore_file}")
            return False
        
        log_info(f"从备份文件恢复: {restore_file}")
        
        # 显示备份文件信息
        backup_data = read_json_file(restore_file)
        if backup_data:
            print("备份信息:")
            print(f"  导出时间: {backup_data.get('export_time', 'N/A')}")
            print(f"  渠道数量: {backup_data.get('total_channels', 0)}")
            print()
        
        if not confirm_action("确认从此备份恢复?"):
            log_info("取消恢复操作")
            return False
        
        if self.manager.restore(restore_file, verbose=True):
            log_success("数据库恢复完成")
            return True
        else:
            log_error("数据库恢复失败")
            return False
    
    def list_backups(self):
        """列出可用备份文件"""
        backup_files = list_files_in_directory(self.backup_dir, "*.json")
        
        if backup_files:
            print("可用备份文件:")
            for file_path in backup_files:
                info = get_file_info(file_path)
                if info:
                    print(f"  {info['name']} - {info['size']:,} bytes - {info['modified']}")
        else:
            print("无备份文件")
    
    def run_full_reset(self) -> bool:
        """执行完整的备份+重置流程"""
        log_info("开始完整的数据库重置流程")
        print("步骤 1: 创建备份")
        
        backup_file = self.create_backup()
        if not backup_file:
            log_error("备份失败，中止重置操作")
            return False
        
        print()
        print("步骤 2: 重置数据库")
        
        if self.reset_database():
            print()
            log_success("数据库重置完成")
            print()
            print(f"备份文件位置: {self.backup_dir}/")
            print(f"如需恢复，请使用: {sys.argv[0]} --restore <备份文件>")
            print()
            self.list_backups()
            return True
        else:
            log_error("重置失败，数据未被修改")
            return False
    
    def dry_run(self, backup_only: bool = False, reset_only: bool = False):
        """模拟运行，显示将要执行的操作"""
        print("=== 模拟运行 ===")
        print("将要执行的操作:")
        
        operations = []
        if not reset_only:
            operations.append(f"1. 创建备份到: {self.backup_dir}/reset_backup_{self.timestamp}.json")
        if not backup_only:
            operations.append("2. 重置数据库（清空所有渠道）")
        
        for op in operations:
            print(f"  {op}")
        
        print("=== 模拟结束 ===")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='数据库重置工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
安全重置流程:
  1. 自动创建完整备份
  2. 确认重置操作
  3. 清空渠道数据
  4. 提供恢复选项

示例:
  %(prog)s                           # 完整的备份+重置流程
  %(prog)s --backup-only             # 仅创建备份
  %(prog)s --restore backup.json     # 从备份恢复
  %(prog)s --dry-run                 # 模拟运行
        """
    )
    
    parser.add_argument('--backup-only', action='store_true',
                       help='仅创建备份，不重置数据库')
    parser.add_argument('--reset-only', action='store_true',
                       help='仅重置数据库，不创建备份（危险操作）')
    parser.add_argument('--restore', metavar='FILE',
                       help='从指定备份文件恢复数据库')
    parser.add_argument('--dry-run', action='store_true',
                       help='模拟运行，显示将要执行的操作')
    parser.add_argument('--backup-dir', default='./backups',
                       help='指定备份目录 (默认: ./backups)')
    parser.add_argument('--verbose', action='store_true',
                       help='显示详细信息')
    parser.add_argument('--dsn', default='root:123456@tcp(localhost:3306)/new-api',
                       help='数据库连接字符串')
    
    args = parser.parse_args()
    
    # 检查Go环境
    if not check_go_installed():
        log_error("Go 运行环境未找到")
        return 1
    
    # 创建数据库重置管理器
    reset_manager = DatabaseReset(dsn=args.dsn, backup_dir=args.backup_dir)
    
    # 如果指定了恢复文件
    if args.restore:
        return 0 if reset_manager.restore_database(args.restore) else 1
    
    # 显示当前状态
    reset_manager.count_current_data()
    print()
    
    # 模拟运行
    if args.dry_run:
        reset_manager.dry_run(args.backup_only, args.reset_only)
        return 0
    
    # 仅备份模式
    if args.backup_only:
        backup_file = reset_manager.create_backup()
        return 0 if backup_file else 1
    
    # 仅重置模式（危险）
    if args.reset_only:
        log_warning("⚠️  危险模式：仅重置，不创建备份")
        return 0 if reset_manager.reset_database() else 1
    
    # 完整流程：备份 + 重置
    return 0 if reset_manager.run_full_reset() else 1


if __name__ == "__main__":
    sys.exit(main())