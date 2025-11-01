#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新 Gemini 渠道模型脚本
将所有 Gemini 渠道的模型替换为 Gemini 2.5 系列
"""

import os
import sys
import argparse
from typing import List, Dict, Optional

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import (
    log_info, log_success, log_warning, log_error,
    Colors
)

# 尝试导入MySQL连接库
try:
    import pymysql
    HAS_PYMYSQL = True
except ImportError:
    HAS_PYMYSQL = False
    log_error("pymysql not installed. Install with: pip install pymysql")
    sys.exit(1)

colors = Colors()

# Gemini 2.5 系列模型列表
GEMINI_25_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro-preview-03-25",
    "gemini-2.5-pro-preview-05-06",
    "gemini-2.5-pro-preview-06-05",
    "gemini-2.5-flash-preview-05-20",
    "gemini-2.5-flash-lite-preview-06-17",
]

# Gemini 渠道类型 ID (根据项目常量定义)
GEMINI_CHANNEL_TYPE = 14


class GeminiModelUpdater:
    """Gemini 模型更新器"""

    def __init__(self, host: str = "localhost", port: int = 3306,
                 user: str = "root", password: str = "123456",
                 database: str = "new-api"):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connection = None

    def connect(self) -> bool:
        """连接数据库"""
        try:
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            log_success(f"Connected to MySQL database: {self.database}")
            return True
        except Exception as e:
            log_error(f"Failed to connect to database: {e}")
            return False

    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            log_info("Database connection closed")

    def get_gemini_channels(self) -> List[Dict]:
        """获取所有 Gemini 渠道"""
        try:
            with self.connection.cursor() as cursor:
                sql = """
                    SELECT id, name, type, models, status
                    FROM channels
                    WHERE type = %s
                    ORDER BY id
                """
                cursor.execute(sql, (GEMINI_CHANNEL_TYPE,))
                channels = cursor.fetchall()
                return channels
        except Exception as e:
            log_error(f"Failed to fetch Gemini channels: {e}")
            return []

    def update_channel_models(self, channel_id: int, new_models: str, dry_run: bool = True) -> bool:
        """更新渠道模型"""
        try:
            if dry_run:
                log_info(f"[DRY RUN] Would update channel {channel_id} models to: {new_models}")
                return True

            with self.connection.cursor() as cursor:
                sql = "UPDATE channels SET models = %s WHERE id = %s"
                cursor.execute(sql, (new_models, channel_id))
                self.connection.commit()
                log_success(f"Updated channel {channel_id} models")
                return True
        except Exception as e:
            log_error(f"Failed to update channel {channel_id}: {e}")
            if not dry_run:
                self.connection.rollback()
            return False

    def run(self, dry_run: bool = True):
        """执行更新"""
        log_info("=" * 60)
        log_info("Gemini 渠道模型更新脚本")
        log_info("=" * 60)

        if dry_run:
            log_warning("DRY RUN MODE - No changes will be made")
        else:
            log_warning("LIVE MODE - Changes will be applied to database!")

        print()

        # 连接数据库
        if not self.connect():
            return

        try:
            # 获取所有 Gemini 渠道
            channels = self.get_gemini_channels()

            if not channels:
                log_warning("No Gemini channels found")
                return

            log_info(f"Found {len(channels)} Gemini channel(s)")
            print()

            # 新模型列表（逗号分隔）
            new_models_str = ",".join(GEMINI_25_MODELS)

            # 显示将要更新的渠道
            log_info("Channels to be updated:")
            log_info("-" * 60)

            for channel in channels:
                channel_id = channel['id']
                channel_name = channel['name']
                current_models = channel['models'] or ""
                status = "Enabled" if channel['status'] == 1 else "Disabled"

                print(f"\n{colors.BLUE}Channel ID:{colors.NC} {channel_id}")
                print(f"{colors.BLUE}Name:{colors.NC} {channel_name}")
                print(f"{colors.BLUE}Status:{colors.NC} {status}")
                print(f"{colors.YELLOW}Current models:{colors.NC}")
                if current_models:
                    for model in current_models.split(','):
                        print(f"  - {model.strip()}")
                else:
                    print(f"  (empty)")

                print(f"{colors.GREEN}New models:{colors.NC}")
                for model in GEMINI_25_MODELS:
                    print(f"  - {model}")

            print()
            log_info("-" * 60)

            # 确认更新
            if not dry_run:
                print()
                response = input(f"{colors.YELLOW}Proceed with update? (yes/no): {colors.NC}")
                if response.lower() not in ['yes', 'y']:
                    log_warning("Update cancelled by user")
                    return
                print()

            # 执行更新
            success_count = 0
            fail_count = 0

            for channel in channels:
                channel_id = channel['id']
                if self.update_channel_models(channel_id, new_models_str, dry_run):
                    success_count += 1
                else:
                    fail_count += 1

            # 显示结果
            print()
            log_info("=" * 60)
            if dry_run:
                log_info(f"DRY RUN completed: {success_count} channel(s) would be updated")
            else:
                log_success(f"Update completed: {success_count} channel(s) updated")
                if fail_count > 0:
                    log_error(f"Failed to update {fail_count} channel(s)")
            log_info("=" * 60)

        finally:
            self.close()


def main():
    parser = argparse.ArgumentParser(
        description='Update Gemini channels to use Gemini 2.5 series models',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (preview changes without applying)
  python update_gemini_models.py --dry-run

  # Apply changes
  python update_gemini_models.py

  # Custom database connection
  python update_gemini_models.py --host localhost --port 3306 --user root --password 123456
        """
    )

    parser.add_argument('--host', default='localhost',
                        help='MySQL host (default: localhost)')
    parser.add_argument('--port', type=int, default=3306,
                        help='MySQL port (default: 3306)')
    parser.add_argument('--user', default='root',
                        help='MySQL user (default: root)')
    parser.add_argument('--password', default='123456',
                        help='MySQL password (default: 123456)')
    parser.add_argument('--database', default='new-api',
                        help='Database name (default: new-api)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without applying them')

    args = parser.parse_args()

    updater = GeminiModelUpdater(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database
    )

    updater.run(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
