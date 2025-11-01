#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库清理脚本 - 清空数据保留结构
支持选择性清理，显示每个表的功能和清理影响
"""

import os
import sys
import argparse
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import (
    log_info, log_success, log_warning, log_error,
    get_timestamp, Colors
)

# 尝试导入MySQL连接库
try:
    import pymysql
    HAS_PYMYSQL = True
except ImportError:
    HAS_PYMYSQL = False
    log_warning("pymysql not installed. Install with: pip install pymysql")

colors = Colors()


# 表信息定义：表名 -> (功能描述, 清理影响, 重要性级别, 分类)
TABLE_INFO = {
    # ========== 核心业务表 ==========
    'channels': {
        'description': 'AI模型渠道配置表',
        'function': '存储各种AI模型（OpenAI、Claude、Gemini等）的API配置信息',
        'impact': '清空后将丢失所有AI模型接入配置，系统无法调用任何AI服务',
        'importance': 'CRITICAL',
        'category': 'core',
        'fields': ['API密钥', '模型配置', '负载均衡权重', '速率限制']
    },
    
    'users': {
        'description': '用户账户表',
        'function': '存储系统用户信息，包括管理员和普通用户',
        'impact': '清空后所有用户将被删除，需要重新创建root账户（默认密码123456）',
        'importance': 'CRITICAL',
        'category': 'core',
        'fields': ['用户名', '密码哈希', '角色权限', '配额余额']
    },
    
    'tokens': {
        'description': 'API令牌表',
        'function': '存储用户的API访问令牌，用于API认证',
        'impact': '清空后所有API令牌失效，用户需要重新生成令牌',
        'importance': 'HIGH',
        'category': 'core',
        'fields': ['令牌密钥', '所属用户', '权限范围', '使用限制']
    },
    
    # ========== 业务功能表 ==========
    'abilities': {
        'description': '模型能力映射表',
        'function': '定义渠道与模型的能力映射关系和优先级',
        'impact': '清空后需要重新配置模型路由规则和优先级',
        'importance': 'HIGH',
        'category': 'business',
        'fields': ['模型组', '渠道映射', '优先级', '启用状态']
    },
    
    'redemptions': {
        'description': '兑换码表',
        'function': '存储充值兑换码信息',
        'impact': '清空后所有未使用的兑换码将失效',
        'importance': 'MEDIUM',
        'category': 'business',
        'fields': ['兑换码', '金额', '使用状态', '有效期']
    },
    
    'topups': {
        'description': '充值记录表',
        'function': '记录用户充值历史',
        'impact': '清空后将丢失所有充值记录，但不影响用户当前余额',
        'importance': 'MEDIUM',
        'category': 'business',
        'fields': ['充值金额', '交易单号', '支付方式', '充值时间']
    },
    
    # ========== 数据记录表 ==========
    'logs': {
        'description': '系统日志表',
        'function': '记录API调用日志和系统操作日志',
        'impact': '清空后将丢失所有历史日志，不影响系统运行',
        'importance': 'LOW',
        'category': 'logs',
        'fields': ['请求内容', '响应结果', '消耗配额', '调用时间']
    },
    
    'quota_data': {
        'description': '配额使用数据表',
        'function': '记录用户的模型使用量统计',
        'impact': '清空后将丢失使用统计数据，不影响配额余额',
        'importance': 'LOW',
        'category': 'logs',
        'fields': ['使用量', '模型名称', '统计时间', '用户信息']
    },
    
    'midjourneys': {
        'description': 'Midjourney任务表',
        'function': '存储Midjourney绘图任务记录',
        'impact': '清空后将丢失所有MJ任务历史',
        'importance': 'LOW',
        'category': 'logs',
        'fields': ['任务ID', '任务状态', '图片URL', '提示词']
    },
    
    'tasks': {
        'description': '异步任务表',
        'function': '存储系统异步任务执行记录',
        'impact': '清空后将丢失任务执行历史，进行中的任务可能中断',
        'importance': 'MEDIUM',
        'category': 'logs',
        'fields': ['任务ID', '任务类型', '执行状态', '结果数据']
    },
    
    # ========== 系统配置表 ==========
    'options': {
        'description': '系统配置表',
        'function': '存储系统全局配置选项',
        'impact': '清空后系统将使用默认配置，需要重新设置',
        'importance': 'HIGH',
        'category': 'system',
        'fields': ['配置键', '配置值', '配置说明']
    },
    
    'setups': {
        'description': '系统初始化表',
        'function': '记录系统初始化状态和版本信息',
        'impact': '清空后系统将认为未初始化，可能触发重新初始化流程',
        'importance': 'CRITICAL',
        'category': 'system',
        'fields': ['版本号', '初始化时间', '系统状态']
    }
}

# 重要性级别颜色
IMPORTANCE_COLORS = {
    'CRITICAL': '\033[91m',  # 红色
    'HIGH': '\033[93m',      # 黄色
    'MEDIUM': '\033[94m',     # 蓝色
    'LOW': '\033[92m',        # 绿色
}

# 分类描述
CATEGORY_DESC = {
    'core': '核心业务表 - 系统运行必需',
    'business': '业务功能表 - 影响具体功能',
    'logs': '数据记录表 - 历史数据',
    'system': '系统配置表 - 系统设置'
}


class DatabaseCleaner:
    """数据库清理器"""
    
    def __init__(self, host: str = "localhost", port: int = 3306,
                 user: str = "root", password: str = "123456",
                 database: str = "new-api"):
        """
        初始化清理器
        
        Args:
            host: MySQL主机
            port: MySQL端口
            user: MySQL用户名
            password: MySQL密码
            database: 数据库名
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connection = None
        
    def connect_db(self) -> bool:
        """连接数据库"""
        if not HAS_PYMYSQL:
            log_error("pymysql is required. Install with: pip install pymysql")
            return False
            
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
    
    def get_tables(self) -> List[str]:
        """获取数据库中的所有表"""
        if not self.connection:
            if not self.connect_db():
                return []
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                return [list(table.values())[0] for table in tables]
        except Exception as e:
            log_error(f"Failed to get tables: {e}")
            return []
    
    def get_table_count(self, table: str) -> int:
        """获取表中的记录数"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) as count FROM `{table}`")
                result = cursor.fetchone()
                return result['count'] if result else 0
        except Exception as e:
            log_error(f"Failed to count {table}: {e}")
            return -1
    
    def backup_table_data(self, table: str, backup_dir: str = "backups") -> bool:
        """备份单个表的数据"""
        try:
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = get_timestamp()
            backup_file = os.path.join(backup_dir, f"{table}_{timestamp}.sql")
            
            with self.connection.cursor() as cursor:
                # 获取表结构
                cursor.execute(f"SHOW CREATE TABLE `{table}`")
                create_table = cursor.fetchone()
                
                # 获取表数据
                cursor.execute(f"SELECT * FROM `{table}`")
                rows = cursor.fetchall()
                
                with open(backup_file, 'w', encoding='utf-8') as f:
                    # 写入表结构
                    f.write(f"-- Backup of {table} at {timestamp}\n")
                    f.write(f"-- Records: {len(rows)}\n\n")
                    f.write(f"DROP TABLE IF EXISTS `{table}`;\n")
                    f.write(create_table['Create Table'] + ";\n\n")
                    
                    # 写入数据
                    if rows:
                        f.write(f"-- Data for {table}\n")
                        for row in rows:
                            values = []
                            for value in row.values():
                                if value is None:
                                    values.append('NULL')
                                elif isinstance(value, (int, float)):
                                    values.append(str(value))
                                else:
                                    # 转义单引号
                                    escaped_value = str(value).replace("'", "''")
                                    values.append(f"'{escaped_value}'")
                            
                            values_str = ', '.join(values)
                            f.write(f"INSERT INTO `{table}` VALUES ({values_str});\n")
                
                log_success(f"Backed up {table} to {backup_file}")
                return True
                
        except Exception as e:
            log_error(f"Failed to backup {table}: {e}")
            return False
    
    def truncate_table(self, table: str) -> bool:
        """清空表数据"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(f"TRUNCATE TABLE `{table}`")
                self.connection.commit()
                return True
        except Exception as e:
            log_error(f"Failed to truncate {table}: {e}")
            return False
    
    def show_table_info(self, tables: List[str]) -> Dict[str, Dict]:
        """显示表信息"""
        print("\n" + "=" * 80)
        print("DATABASE TABLES INFORMATION")
        print("=" * 80)
        
        table_stats = {}
        categories = {}
        
        # 按分类组织表
        for table in tables:
            info = TABLE_INFO.get(table, {
                'description': '未知表',
                'function': '功能未定义',
                'impact': '影响未知',
                'importance': 'UNKNOWN',
                'category': 'unknown'
            })
            
            category = info.get('category', 'unknown')
            if category not in categories:
                categories[category] = []
            
            count = self.get_table_count(table)
            categories[category].append({
                'name': table,
                'count': count,
                'info': info
            })
            
            table_stats[table] = {
                'count': count,
                'info': info
            }
        
        # 按分类显示
        category_order = ['core', 'business', 'system', 'logs', 'unknown']
        
        for category in category_order:
            if category not in categories:
                continue
                
            print(f"\n{colors.CYAN}▶ {CATEGORY_DESC.get(category, '其他表')}{colors.NC}")
            print("-" * 70)
            
            for table_data in categories[category]:
                table = table_data['name']
                count = table_data['count']
                info = table_data['info']
                
                importance = info.get('importance', 'UNKNOWN')
                color = IMPORTANCE_COLORS.get(importance, '')
                
                print(f"\n{colors.BOLD}{table}{colors.NC} ({count} records)")
                print(f"  {color}[{importance}]{colors.NC} {info.get('description', '')}")
                print(f"  功能: {info.get('function', '')}")
                
                if 'fields' in info:
                    fields_str = ', '.join(info['fields'])
                    print(f"  字段: {fields_str}")
                
                print(f"  {colors.YELLOW}清理影响: {info.get('impact', '')}{colors.NC}")
        
        return table_stats
    
    def select_tables_interactive(self, tables: List[str]) -> List[str]:
        """交互式选择要清理的表"""
        print("\n" + "=" * 80)
        print("SELECT TABLES TO CLEAN")
        print("=" * 80)
        
        print("\n选择要清理的表（多选，用逗号分隔）:")
        print("  1. 清理所有表（危险！）")
        print("  2. 清理日志类表（logs, quota_data, midjourneys）")
        print("  3. 清理业务数据（保留配置）")
        print("  4. 自定义选择")
        print("  0. 取消操作")
        
        choice = input("\n请选择 [0-4]: ").strip()
        
        if choice == '0':
            return []
        elif choice == '1':
            return tables
        elif choice == '2':
            # 日志类表
            log_tables = ['logs', 'quota_data', 'midjourneys', 'tasks']
            return [t for t in log_tables if t in tables]
        elif choice == '3':
            # 业务数据（不包括核心配置）
            business_tables = ['logs', 'quota_data', 'midjourneys', 'tasks', 
                             'redemptions', 'topups']
            return [t for t in business_tables if t in tables]
        elif choice == '4':
            print("\n可用的表:")
            for i, table in enumerate(tables, 1):
                info = TABLE_INFO.get(table, {})
                importance = info.get('importance', 'UNKNOWN')
                color = IMPORTANCE_COLORS.get(importance, '')
                print(f"  {i}. {table} {color}[{importance}]{colors.NC}")
            
            selection = input("\n输入表编号（逗号分隔）: ").strip()
            if not selection:
                return []
            
            selected = []
            for num in selection.split(','):
                try:
                    idx = int(num.strip()) - 1
                    if 0 <= idx < len(tables):
                        selected.append(tables[idx])
                except ValueError:
                    continue
            
            return selected
        else:
            print("无效选择")
            return []
    
    def clean_tables(self, tables_to_clean: List[str], backup: bool = True) -> bool:
        """清理指定的表"""
        if not tables_to_clean:
            log_warning("No tables selected for cleaning")
            return False
        
        print("\n" + "=" * 80)
        print("CLEANING PROCESS")
        print("=" * 80)
        
        # 显示将要清理的表
        print("\n将要清理以下表:")
        total_records = 0
        for table in tables_to_clean:
            count = self.get_table_count(table)
            total_records += count if count > 0 else 0
            info = TABLE_INFO.get(table, {})
            importance = info.get('importance', 'UNKNOWN')
            color = IMPORTANCE_COLORS.get(importance, '')
            print(f"  • {table} ({count} records) {color}[{importance}]{colors.NC}")
        
        print(f"\n总计将清理 {len(tables_to_clean)} 个表，{total_records} 条记录")
        
        # 危险操作确认
        critical_tables = [t for t in tables_to_clean 
                          if TABLE_INFO.get(t, {}).get('importance') == 'CRITICAL']
        
        if critical_tables:
            print(f"\n{colors.RED}⚠️  警告：您将要清理以下关键表:{colors.NC}")
            for table in critical_tables:
                print(f"  • {table}: {TABLE_INFO[table]['impact']}")
            
            confirm = input(f"\n{colors.RED}确定要继续吗？输入 'CLEAN' 确认: {colors.NC}")
            if confirm != 'CLEAN':
                log_warning("Operation cancelled")
                return False
        else:
            confirm = input("\n确定要清理这些表吗？(y/N): ")
            if confirm.lower() != 'y':
                log_warning("Operation cancelled")
                return False
        
        # 备份
        if backup:
            print("\n正在备份数据...")
            backup_dir = f"backups/clean_{get_timestamp()}"
            for table in tables_to_clean:
                count = self.get_table_count(table)
                if count > 0:
                    self.backup_table_data(table, backup_dir)
            print(f"备份完成，文件保存在: {backup_dir}")
        
        # 清理
        print("\n正在清理表...")
        success_count = 0
        failed_tables = []
        
        for table in tables_to_clean:
            print(f"  Cleaning {table}...", end=" ")
            if self.truncate_table(table):
                print(f"{colors.GREEN}✓{colors.NC}")
                success_count += 1
            else:
                print(f"{colors.RED}✗{colors.NC}")
                failed_tables.append(table)
        
        # 结果汇总
        print("\n" + "=" * 80)
        print("CLEANING SUMMARY")
        print("=" * 80)
        
        print(f"\n成功清理: {success_count}/{len(tables_to_clean)} 个表")
        
        if failed_tables:
            print(f"{colors.RED}清理失败的表:{colors.NC}")
            for table in failed_tables:
                print(f"  • {table}")
        
        # 清理后的影响提示
        if success_count > 0:
            print(f"\n{colors.YELLOW}清理完成后的注意事项:{colors.NC}")
            
            if 'users' in tables_to_clean:
                print("  • 用户表已清空，系统将自动创建默认root账户（密码: 123456）")
            
            if 'channels' in tables_to_clean:
                print("  • 渠道表已清空，需要重新配置AI模型接入")
            
            if 'tokens' in tables_to_clean:
                print("  • 令牌表已清空，所有API访问令牌已失效")
            
            if 'options' in tables_to_clean:
                print("  • 配置表已清空，系统将使用默认配置")
            
            if 'abilities' in tables_to_clean:
                print("  • 能力表已清空，需要重新配置模型路由")
        
        return success_count == len(tables_to_clean)
    
    def show_statistics(self, tables: List[str]):
        """显示数据库统计信息"""
        print("\n" + "=" * 80)
        print("DATABASE STATISTICS")
        print("=" * 80)
        
        total_tables = len(tables)
        total_records = 0
        empty_tables = []
        large_tables = []
        
        for table in tables:
            count = self.get_table_count(table)
            if count > 0:
                total_records += count
                if count > 10000:
                    large_tables.append((table, count))
            elif count == 0:
                empty_tables.append(table)
        
        print(f"\n数据库: {self.database}")
        print(f"总表数: {total_tables}")
        print(f"总记录数: {total_records:,}")
        
        if empty_tables:
            print(f"\n空表 ({len(empty_tables)}):")
            for table in empty_tables[:5]:
                print(f"  • {table}")
            if len(empty_tables) > 5:
                print(f"  ... 还有 {len(empty_tables) - 5} 个空表")
        
        if large_tables:
            print(f"\n大表 (>10000 records):")
            for table, count in sorted(large_tables, key=lambda x: x[1], reverse=True)[:5]:
                print(f"  • {table}: {count:,} records")
    
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            self.connection = None


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Database Cleaner - Clean data while preserving structure',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Interactive mode
  %(prog)s --list                    # List all tables with information
  %(prog)s --clean logs              # Clean specific table
  %(prog)s --clean-logs              # Clean all log tables
  %(prog)s --clean-all --confirm     # Clean all tables (dangerous!)
  %(prog)s --stats                   # Show database statistics
  
Safety:
  - Always backs up data before cleaning
  - Requires confirmation for critical tables
  - Shows impact analysis before cleaning
        """
    )
    
    # 数据库连接参数
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
    
    # 操作参数
    parser.add_argument('--list', action='store_true',
                       help='List all tables with details')
    parser.add_argument('--stats', action='store_true',
                       help='Show database statistics')
    parser.add_argument('--clean', nargs='+',
                       help='Clean specific tables')
    parser.add_argument('--clean-logs', action='store_true',
                       help='Clean all log tables')
    parser.add_argument('--clean-all', action='store_true',
                       help='Clean all tables (requires --confirm)')
    parser.add_argument('--confirm', action='store_true',
                       help='Skip confirmation prompts')
    parser.add_argument('--no-backup', action='store_true',
                       help='Skip backup before cleaning')
    
    args = parser.parse_args()
    
    # 检查pymysql
    if not HAS_PYMYSQL:
        print("\n" + "=" * 60)
        print("pymysql library required")
        print("=" * 60)
        print("\nInstall with:")
        print("  pip install pymysql")
        print("\nOr with conda:")
        print("  conda install pymysql")
        return 1
    
    # 创建清理器
    cleaner = DatabaseCleaner(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database
    )
    
    # 连接数据库
    if not cleaner.connect_db():
        return 1
    
    # 获取所有表
    tables = cleaner.get_tables()
    if not tables:
        log_error("No tables found in database")
        cleaner.close()
        return 1
    
    # 执行操作
    try:
        if args.list:
            # 列出所有表
            cleaner.show_table_info(tables)
            cleaner.show_statistics(tables)
            
        elif args.stats:
            # 显示统计
            cleaner.show_statistics(tables)
            
        elif args.clean:
            # 清理指定表
            tables_to_clean = [t for t in args.clean if t in tables]
            if not tables_to_clean:
                log_error(f"Tables not found: {args.clean}")
                return 1
            
            cleaner.show_table_info(tables_to_clean)
            
            if args.confirm or cleaner.clean_tables(tables_to_clean, not args.no_backup):
                log_success("Cleaning completed")
            
        elif args.clean_logs:
            # 清理日志表
            log_tables = ['logs', 'quota_data', 'midjourneys', 'tasks']
            tables_to_clean = [t for t in log_tables if t in tables]
            
            if tables_to_clean:
                cleaner.show_table_info(tables_to_clean)
                cleaner.clean_tables(tables_to_clean, not args.no_backup)
            else:
                log_warning("No log tables found")
            
        elif args.clean_all:
            # 清理所有表
            if not args.confirm:
                print(f"\n{colors.RED}⚠️  This will clean ALL tables!{colors.NC}")
                print("Add --confirm flag to proceed")
                return 1
            
            cleaner.show_table_info(tables)
            cleaner.clean_tables(tables, not args.no_backup)
            
        else:
            # 交互模式
            cleaner.show_table_info(tables)
            cleaner.show_statistics(tables)
            
            tables_to_clean = cleaner.select_tables_interactive(tables)
            if tables_to_clean:
                cleaner.clean_tables(tables_to_clean, not args.no_backup)
            else:
                log_info("No operation performed")
    
    finally:
        # 关闭连接
        cleaner.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())