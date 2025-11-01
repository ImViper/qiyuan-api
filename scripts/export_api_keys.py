#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导出数据库中所有渠道的API密钥
支持从数据库导出Gemini渠道的API密钥到文件
支持测试API密钥有效性并只导出有效的密钥
"""

import os
import sys
import argparse
import time
import requests
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import (
    log_info, log_success, log_warning, log_error,
    get_timestamp
)

# 尝试导入MySQL连接库
try:
    import pymysql
    HAS_PYMYSQL = True
except ImportError:
    HAS_PYMYSQL = False
    log_warning("pymysql not installed. Install with: pip install pymysql")

# 渠道类型映射
CHANNEL_TYPE_GEMINI = 24
CHANNEL_TYPE_VERTEX = 36


class APIKeyExporter:
    """API密钥导出器"""
    
    def __init__(self, host: str = "localhost", port: int = 3306,
                 user: str = "root", password: str = "123456",
                 database: str = "new-api"):
        """
        初始化导出器
        
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
    
    def get_channels(self, channel_type: Optional[int] = None,
                     status: Optional[int] = None,
                     include_disabled: bool = False) -> List[Dict]:
        """
        从数据库获取渠道
        
        Args:
            channel_type: 渠道类型
            status: 渠道状态
            include_disabled: 是否包含禁用的渠道
        
        Returns:
            渠道列表
        """
        if not self.connection:
            if not self.connect_db():
                return []
        
        try:
            with self.connection.cursor() as cursor:
                # 构建查询
                query = """
                    SELECT id, name, type, `key`, status, models
                    FROM channels
                    WHERE 1=1
                """
                params = []
                
                if channel_type is not None:
                    query += " AND type = %s"
                    params.append(channel_type)
                else:
                    # 默认查询Gemini和Vertex类型
                    query += " AND type IN (%s, %s)"
                    params.extend([CHANNEL_TYPE_GEMINI, CHANNEL_TYPE_VERTEX])
                
                if status is not None:
                    query += " AND status = %s"
                    params.append(status)
                elif not include_disabled:
                    # 默认只获取启用的渠道
                    query += " AND status = 1"
                
                query += " ORDER BY id"
                
                cursor.execute(query, params)
                channels = cursor.fetchall()
                
                log_info(f"Found {len(channels)} channel(s) in database")
                return channels
                
        except Exception as e:
            log_error(f"Database query failed: {e}")
            return []
    
    def test_gemini_key(self, api_key: str, model: str = "gemini-2.5-flash", timeout: int = 10) -> Tuple[bool, str]:
        """
        测试Gemini API密钥有效性
        
        Args:
            api_key: API密钥
            model: 测试模型
            timeout: 超时时间
        
        Returns:
            (是否有效, 消息)
        """
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": "Say 'OK' in one word."
                }]
            }],
            "generationConfig": {
                "maxOutputTokens": 5,
                "temperature": 0.1
            }
        }
        
        headers = {"Content-Type": "application/json"}
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            
            if response.status_code == 200:
                data = response.json()
                if "candidates" in data and len(data["candidates"]) > 0:
                    return True, "Valid"
                else:
                    return False, "Invalid response"
                    
            elif response.status_code == 403:
                return False, "Forbidden"
            elif response.status_code == 429:
                return False, "Rate limited"
            else:
                return False, f"HTTP {response.status_code}"
                
        except requests.exceptions.Timeout:
            return False, "Timeout"
        except requests.exceptions.ConnectionError:
            return False, "Connection error"
        except Exception as e:
            return False, f"Error: {str(e)[:30]}"
    
    def extract_api_keys(self, channels: List[Dict]) -> List[Dict]:
        """
        提取API密钥
        
        Args:
            channels: 渠道列表
        
        Returns:
            API密钥信息列表
        """
        api_keys_info = []
        
        for channel in channels:
            channel_id = channel.get('id', 0)
            channel_name = channel.get('name', 'Unknown')
            channel_type = channel.get('type', 0)
            channel_status = channel.get('status', 0)
            api_key_str = channel.get('key', '')
            models = channel.get('models', '')
            
            # 处理多个API密钥（用换行符分隔）
            api_keys = [k.strip() for k in api_key_str.split('\n') if k.strip()]
            
            for key in api_keys:
                # 跳过JSON格式的密钥（Vertex AI）
                if key.startswith('[') or key.startswith('{'):
                    continue
                
                api_keys_info.append({
                    'channel_id': channel_id,
                    'channel_name': channel_name,
                    'channel_type': channel_type,
                    'channel_status': channel_status,
                    'api_key': key,
                    'models': models
                })
        
        return api_keys_info
    
    def filter_valid_keys(self, api_keys_info: List[Dict], max_workers: int = 5, 
                         model: str = "gemini-2.5-flash") -> List[Dict]:
        """
        过滤有效的API密钥
        
        Args:
            api_keys_info: API密钥信息列表
            max_workers: 最大并发数
            model: 测试模型
        
        Returns:
            有效的API密钥信息列表
        """
        if not api_keys_info:
            return []
        
        log_info(f"Testing {len(api_keys_info)} API keys to filter valid ones...")
        valid_keys = []
        tested_keys = set()  # 避免重复测试相同的密钥
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交测试任务
            future_to_info = {}
            for info in api_keys_info:
                key = info['api_key']
                if key not in tested_keys:
                    tested_keys.add(key)
                    future = executor.submit(self.test_gemini_key, key, model)
                    future_to_info[future] = info
                else:
                    # 如果密钥已测试过，直接跳过
                    continue
            
            # 处理结果
            completed = 0
            valid_count = 0
            
            for future in as_completed(future_to_info):
                info = future_to_info[future]
                try:
                    is_valid, message = future.result()
                    completed += 1
                    
                    if is_valid:
                        valid_count += 1
                        valid_keys.append(info)
                        # 隐藏部分密钥
                        masked_key = info['api_key'][:10] + "..." + info['api_key'][-4:] if len(info['api_key']) > 14 else info['api_key']
                        print(f"[{completed}/{len(future_to_info)}] ✓ Valid key from {info['channel_name']} ({masked_key})")
                    else:
                        masked_key = info['api_key'][:10] + "..." if len(info['api_key']) > 10 else info['api_key']
                        print(f"[{completed}/{len(future_to_info)}] ✗ Invalid key from {info['channel_name']}: {message}")
                    
                except Exception as e:
                    completed += 1
                    log_error(f"Error testing key: {e}")
        
        log_info(f"Found {valid_count} valid keys out of {len(tested_keys)} tested")
        return valid_keys
    
    def export_to_file(self, api_keys_info: List[Dict], output_file: str,
                      format: str = 'simple') -> bool:
        """
        导出API密钥到文件
        
        Args:
            api_keys_info: API密钥信息列表
            output_file: 输出文件路径
            format: 导出格式 ('simple', 'detailed', 'csv')
        
        Returns:
            是否成功
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                if format == 'simple':
                    # 简单格式：一行一个密钥
                    for info in api_keys_info:
                        f.write(f"{info['api_key']}\n")
                
                elif format == 'detailed':
                    # 详细格式：包含渠道信息
                    for info in api_keys_info:
                        status_str = "enabled" if info['channel_status'] == 1 else "disabled"
                        f.write(f"# Channel: {info['channel_name']} (ID: {info['channel_id']}, Status: {status_str})\n")
                        f.write(f"{info['api_key']}\n")
                        f.write("\n")
                
                elif format == 'csv':
                    # CSV格式
                    f.write("channel_id,channel_name,status,api_key,models\n")
                    for info in api_keys_info:
                        status_str = "enabled" if info['channel_status'] == 1 else "disabled"
                        models_str = info['models'].replace(',', ';')  # 避免CSV分隔符冲突
                        f.write(f"{info['channel_id']},{info['channel_name']},{status_str},{info['api_key']},{models_str}\n")
                
                else:
                    log_error(f"Unknown format: {format}")
                    return False
            
            log_success(f"Exported {len(api_keys_info)} API key(s) to: {output_file}")
            return True
            
        except Exception as e:
            log_error(f"Failed to export to file: {e}")
            return False
    
    def print_summary(self, api_keys_info: List[Dict]):
        """打印摘要信息"""
        if not api_keys_info:
            log_warning("No API keys found")
            return
        
        print("\n" + "=" * 60)
        print("API Keys Summary")
        print("=" * 60)
        
        total = len(api_keys_info)
        unique_channels = len(set(info['channel_id'] for info in api_keys_info))
        enabled_count = sum(1 for info in api_keys_info if info['channel_status'] == 1)
        disabled_count = total - enabled_count
        
        print(f"Total API keys: {total}")
        print(f"Unique channels: {unique_channels}")
        print(f"Enabled channels: {enabled_count}")
        print(f"Disabled channels: {disabled_count}")
        
        # 显示前5个密钥（部分隐藏）
        print("\nSample API keys (first 5):")
        for i, info in enumerate(api_keys_info[:5]):
            key = info['api_key']
            masked_key = key[:10] + "..." + key[-4:] if len(key) > 14 else key
            status = "enabled" if info['channel_status'] == 1 else "disabled"
            print(f"  {i+1}. {info['channel_name']} ({status}): {masked_key}")
    
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            self.connection = None


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Export API Keys from Database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Export formats:
  simple    - One API key per line (default)
  detailed  - Include channel information as comments
  csv       - CSV format with full details

Examples:
  %(prog)s                                    # Export all enabled Gemini API keys
  %(prog)s -o api_keys.txt                   # Export to specific file
  %(prog)s --format detailed                 # Export with channel info
  %(prog)s --format csv -o keys.csv          # Export as CSV
  %(prog)s --include-disabled                # Include disabled channels
  %(prog)s --status 1                        # Only enabled channels
  %(prog)s --type 24                         # Only Gemini channels (type 24)
  
  # Export only valid keys (test before export)
  %(prog)s --valid-only                      # Export only valid API keys
  %(prog)s --valid-only -o valid_keys.txt    # Export valid keys to specific file
  %(prog)s --valid-only --workers 10         # Test with 10 concurrent workers
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
    
    # 导出参数
    parser.add_argument('-o', '--output',
                       help='Output file (default: api_keys_TIMESTAMP.txt or valid_keys_TIMESTAMP.txt)')
    parser.add_argument('--format', choices=['simple', 'detailed', 'csv'],
                       default='simple',
                       help='Export format (default: simple)')
    parser.add_argument('--type', type=int,
                       help='Channel type (24=Gemini, 36=Vertex)')
    parser.add_argument('--status', type=int,
                       help='Channel status (1=enabled, 2=disabled)')
    parser.add_argument('--include-disabled', action='store_true',
                       help='Include disabled channels')
    parser.add_argument('--no-summary', action='store_true',
                       help='Skip printing summary')
    
    # 有效性测试参数
    parser.add_argument('--valid-only', action='store_true',
                       help='Export only valid API keys (will test each key)')
    parser.add_argument('--workers', type=int, default=5,
                       help='Number of concurrent workers for testing (default: 5)')
    parser.add_argument('--test-model', default='gemini-2.5-flash',
                       help='Model to use for testing (default: gemini-2.5-flash)')
    
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
    
    # 创建导出器
    exporter = APIKeyExporter(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database
    )
    
    # 获取渠道
    channels = exporter.get_channels(
        channel_type=args.type,
        status=args.status,
        include_disabled=args.include_disabled
    )
    
    if not channels:
        log_warning("No channels found")
        exporter.close()
        return 1
    
    # 提取API密钥
    api_keys_info = exporter.extract_api_keys(channels)
    
    if not api_keys_info:
        log_warning("No valid API keys found")
        exporter.close()
        return 1
    
    # 如果需要只导出有效的密钥，先进行测试
    if args.valid_only:
        api_keys_info = exporter.filter_valid_keys(
            api_keys_info, 
            max_workers=args.workers,
            model=args.test_model
        )
        
        if not api_keys_info:
            log_warning("No valid API keys found after testing")
            exporter.close()
            return 1
    
    # 确定输出文件名
    if args.output:
        output_file = args.output
    else:
        timestamp = get_timestamp()
        ext = 'csv' if args.format == 'csv' else 'txt'
        prefix = 'valid_keys' if args.valid_only else 'api_keys'
        output_file = f"{prefix}_{timestamp}.{ext}"
    
    # 导出到文件
    success = exporter.export_to_file(api_keys_info, output_file, args.format)
    
    # 打印摘要
    if not args.no_summary:
        exporter.print_summary(api_keys_info)
    
    # 关闭连接
    exporter.close()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())