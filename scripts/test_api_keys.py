#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API密钥有效性测试脚本
支持测试数据库中存储的Gemini渠道API密钥
"""

import os
import sys
import json
import time
import argparse
import requests
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import (
    log_info, log_success, log_warning, log_error,
    get_timestamp, run_command, Colors
)

# Gemini API配置
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-pro", 
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash-8b"
]

# 渠道类型映射（来自系统常量）
CHANNEL_TYPE_GEMINI = 24
CHANNEL_TYPE_VERTEX = 36

colors = Colors()


class APIKeyTester:
    """API密钥测试器"""
    
    def __init__(self, dsn: str = "root:123456@tcp(localhost:3306)/new-api"):
        """
        初始化API密钥测试器
        
        Args:
            dsn: 数据库连接字符串
        """
        self.dsn = dsn
        self.test_results = []
        
    def test_gemini_key(self, api_key: str, model: str = "gemini-2.5-flash",
                       base_url: Optional[str] = None, timeout: int = 10) -> Tuple[bool, str, float]:
        """
        测试单个Gemini API密钥
        
        Args:
            api_key: API密钥
            model: 要测试的模型
            base_url: 自定义base URL（可选）
            timeout: 超时时间（秒）
        
        Returns:
            (是否成功, 消息, 响应时间)
        """
        if not base_url:
            base_url = GEMINI_BASE_URL
            
        # 构建请求URL
        url = f"{base_url}/models/{model}:generateContent?key={api_key}"
        
        # 构建测试请求
        payload = {
            "contents": [{
                "parts": [{
                    "text": "Say 'test successful' in 3 words only."
                }]
            }],
            "generationConfig": {
                "maxOutputTokens": 10,
                "temperature": 0.1
            }
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        start_time = time.time()
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=timeout
            )
            
            response_time = (time.time() - start_time) * 1000  # 转换为毫秒
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "candidates" in data and len(data["candidates"]) > 0:
                        return True, "API key is valid", response_time
                    else:
                        return False, f"Unexpected response format", response_time
                except json.JSONDecodeError:
                    return False, f"Invalid JSON response", response_time
                    
            elif response.status_code == 400:
                # API密钥格式错误或无效
                return False, f"Invalid API key (400 Bad Request)", response_time
                
            elif response.status_code == 403:
                # API密钥无权限或被禁用
                error_msg = "API key forbidden (403)"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg = f"Forbidden: {error_data['error'].get('message', 'Unknown error')}"
                except:
                    pass
                return False, error_msg, response_time
                
            elif response.status_code == 404:
                # 模型不存在
                return False, f"Model not found: {model}", response_time
                
            elif response.status_code == 429:
                # 速率限制
                return False, "Rate limit exceeded (429)", response_time
                
            else:
                return False, f"HTTP {response.status_code}: {response.text[:100]}", response_time
                
        except requests.exceptions.Timeout:
            response_time = timeout * 1000
            return False, f"Request timeout ({timeout}s)", response_time
            
        except requests.exceptions.ConnectionError as e:
            response_time = 0
            return False, f"Connection error: {str(e)[:100]}", response_time
            
        except Exception as e:
            response_time = 0
            return False, f"Unexpected error: {str(e)[:100]}", response_time
    
    def get_channels_from_db(self, channel_type: Optional[int] = None,
                            status: Optional[int] = None) -> List[Dict]:
        """
        从数据库获取渠道信息
        
        Args:
            channel_type: 渠道类型（可选，None表示所有Gemini相关类型）
            status: 渠道状态（可选，None表示所有状态）
        
        Returns:
            渠道列表
        """
        import tempfile
        
        # 使用channel_manager.go导出渠道数据
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # 构建导出命令
            cmd = ['go', 'run', 'channel_manager.go', 
                   '-action=export', 
                   f'-output={tmp_path}',
                   f'-dsn={self.dsn}']
            
            if channel_type is not None:
                cmd.append(f'-type={channel_type}')
            
            if status is not None:
                cmd.append(f'-status={status}')
            
            returncode, _, _ = run_command(cmd, capture_output=True, check=False)
            
            if returncode != 0:
                log_error("Failed to export channels from database")
                return []
            
            # 读取导出的数据
            with open(tmp_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                channels = data.get('channels', [])
                
                # 过滤Gemini和Vertex类型的渠道
                if channel_type is None:
                    gemini_channels = [
                        ch for ch in channels 
                        if ch.get('type') in [CHANNEL_TYPE_GEMINI, CHANNEL_TYPE_VERTEX]
                    ]
                    return gemini_channels
                
                return channels
                
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_channel(self, channel: Dict, model: Optional[str] = None) -> Dict:
        """
        测试单个渠道
        
        Args:
            channel: 渠道信息
            model: 测试模型（可选）
        
        Returns:
            测试结果
        """
        channel_id = channel.get('id', 0)
        channel_name = channel.get('name', 'Unknown')
        channel_type = channel.get('type', 0)
        api_key = channel.get('key', '')
        base_url = channel.get('base_url', '')
        test_model = channel.get('test_model', '')
        
        # 确定要测试的模型
        if not model:
            if test_model:
                model = test_model
            else:
                # 从渠道支持的模型中选择
                models = channel.get('models', '').split(',')
                models = [m.strip() for m in models if m.strip()]
                
                # 优先选择Gemini模型
                for m in models:
                    if 'gemini' in m.lower():
                        model = m
                        break
                
                if not model and models:
                    model = models[0]
                    
                if not model:
                    model = "gemini-2.5-flash"  # 默认模型
        
        # 处理多个API密钥的情况（用换行符分隔）
        api_keys = [k.strip() for k in api_key.split('\n') if k.strip()]
        
        if not api_keys:
            return {
                'channel_id': channel_id,
                'channel_name': channel_name,
                'success': False,
                'message': 'No API key found',
                'model': model,
                'response_time': 0
            }
        
        # 测试第一个有效的密钥
        for idx, key in enumerate(api_keys):
            # 如果是JSON格式的密钥（Vertex AI），跳过
            if key.startswith('[') or key.startswith('{'):
                continue
                
            success, message, response_time = self.test_gemini_key(
                key, model, base_url if base_url else None
            )
            
            result = {
                'channel_id': channel_id,
                'channel_name': channel_name,
                'channel_type': channel_type,
                'success': success,
                'message': message,
                'model': model,
                'response_time': response_time,
                'key_index': idx if len(api_keys) > 1 else -1,
                'total_keys': len(api_keys)
            }
            
            # 如果成功或者是最后一个密钥，返回结果
            if success or idx == len(api_keys) - 1:
                return result
        
        # 没有可测试的密钥
        return {
            'channel_id': channel_id,
            'channel_name': channel_name,
            'success': False,
            'message': 'No valid API key format found',
            'model': model,
            'response_time': 0
        }
    
    def test_channels_batch(self, channels: List[Dict], model: Optional[str] = None,
                           max_workers: int = 5) -> List[Dict]:
        """
        批量测试渠道
        
        Args:
            channels: 渠道列表
            model: 测试模型
            max_workers: 最大并发数
        
        Returns:
            测试结果列表
        """
        results = []
        total = len(channels)
        
        if total == 0:
            log_warning("No channels to test")
            return results
        
        log_info(f"Testing {total} channels with {max_workers} workers...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_channel = {
                executor.submit(self.test_channel, channel, model): channel
                for channel in channels
            }
            
            # 处理完成的任务
            completed = 0
            for future in as_completed(future_to_channel):
                channel = future_to_channel[future]
                try:
                    result = future.result()
                    results.append(result)
                    completed += 1
                    
                    # 打印进度
                    status_icon = "✅" if result['success'] else "❌"
                    print(f"[{completed}/{total}] {status_icon} {result['channel_name']}: "
                          f"{result['message']} ({result['response_time']:.0f}ms)")
                    
                except Exception as e:
                    completed += 1
                    log_error(f"Error testing channel {channel.get('name', 'Unknown')}: {e}")
                    results.append({
                        'channel_id': channel.get('id', 0),
                        'channel_name': channel.get('name', 'Unknown'),
                        'success': False,
                        'message': f"Test error: {str(e)}",
                        'response_time': 0
                    })
        
        return results
    
    def print_summary(self, results: List[Dict]):
        """打印测试摘要"""
        if not results:
            log_warning("No test results to display")
            return
        
        total = len(results)
        successful = sum(1 for r in results if r['success'])
        failed = total - successful
        
        print("\n" + "=" * 60)
        print("测试结果摘要")
        print("=" * 60)
        
        print(f"\n总计测试: {total} 个渠道")
        print(f"{colors.GREEN}成功: {successful}{colors.NC}")
        print(f"{colors.RED}失败: {failed}{colors.NC}")
        print(f"成功率: {successful/total*100:.1f}%")
        
        # 计算平均响应时间（仅成功的）
        success_times = [r['response_time'] for r in results if r['success']]
        if success_times:
            avg_time = sum(success_times) / len(success_times)
            print(f"平均响应时间: {avg_time:.0f}ms")
        
        # 显示失败的渠道
        if failed > 0:
            print(f"\n{colors.RED}失败的渠道:{colors.NC}")
            for r in results:
                if not r['success']:
                    print(f"  - [{r['channel_id']}] {r['channel_name']}: {r['message']}")
        
        # 显示最快和最慢的渠道
        if success_times:
            sorted_results = sorted(
                [r for r in results if r['success']], 
                key=lambda x: x['response_time']
            )
            
            print(f"\n{colors.GREEN}最快的渠道:{colors.NC}")
            for r in sorted_results[:3]:
                print(f"  - {r['channel_name']}: {r['response_time']:.0f}ms")
            
            if len(sorted_results) > 3:
                print(f"\n{colors.YELLOW}最慢的渠道:{colors.NC}")
                for r in sorted_results[-3:]:
                    print(f"  - {r['channel_name']}: {r['response_time']:.0f}ms")
    
    def export_results(self, results: List[Dict], output_file: str):
        """导出测试结果到文件"""
        timestamp = get_timestamp("%Y-%m-%d %H:%M:%S")
        
        export_data = {
            'test_time': timestamp,
            'total_channels': len(results),
            'successful': sum(1 for r in results if r['success']),
            'failed': sum(1 for r in results if not r['success']),
            'results': results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        log_success(f"Test results exported to: {output_file}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='API密钥有效性测试工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                              # 测试所有Gemini渠道
  %(prog)s --model gemini-2.5-flash    # 指定测试模型
  %(prog)s --status 1                   # 仅测试启用的渠道
  %(prog)s --channel-id 5              # 测试特定渠道
  %(prog)s --export results.json        # 导出结果到文件
  %(prog)s --workers 10                # 设置并发数
        """
    )
    
    parser.add_argument('--dsn', 
                       default='root:123456@tcp(localhost:3306)/new-api',
                       help='数据库连接字符串')
    
    parser.add_argument('--model',
                       help='指定测试模型 (默认: gemini-2.5-flash)')
    
    parser.add_argument('--status', type=int,
                       help='渠道状态筛选 (1=启用, 2=手动禁用, 3=自动禁用)')
    
    parser.add_argument('--channel-id', type=int,
                       help='测试特定渠道ID')
    
    parser.add_argument('--api-key',
                       help='直接测试指定的API密钥（不查询数据库）')
    
    parser.add_argument('--export',
                       help='导出测试结果到JSON文件')
    
    parser.add_argument('--workers', type=int, default=5,
                       help='最大并发测试数 (默认: 5)')
    
    parser.add_argument('--timeout', type=int, default=10,
                       help='请求超时时间（秒）(默认: 10)')
    
    parser.add_argument('--list-models', action='store_true',
                       help='列出支持的Gemini模型')
    
    args = parser.parse_args()
    
    # 列出支持的模型
    if args.list_models:
        print("支持的Gemini模型:")
        for model in GEMINI_MODELS:
            print(f"  - {model}")
        return 0
    
    # 创建测试器
    tester = APIKeyTester(dsn=args.dsn)
    
    # 直接测试API密钥
    if args.api_key:
        model = args.model or "gemini-2.5-flash"
        log_info(f"Testing API key directly with model: {model}")
        
        success, message, response_time = tester.test_gemini_key(
            args.api_key, model, timeout=args.timeout
        )
        
        if success:
            log_success(f"✅ API key is valid! Response time: {response_time:.0f}ms")
        else:
            log_error(f"❌ API key test failed: {message}")
        
        return 0 if success else 1
    
    # 从数据库获取渠道
    log_info("Fetching channels from database...")
    
    if args.channel_id:
        # 获取特定渠道
        channels = tester.get_channels_from_db()
        channels = [ch for ch in channels if ch.get('id') == args.channel_id]
        
        if not channels:
            log_error(f"Channel with ID {args.channel_id} not found")
            return 1
    else:
        # 获取所有Gemini渠道
        channels = tester.get_channels_from_db(status=args.status)
    
    if not channels:
        log_warning("No Gemini channels found in database")
        return 1
    
    log_info(f"Found {len(channels)} Gemini channel(s)")
    
    # 批量测试
    results = tester.test_channels_batch(
        channels, 
        model=args.model,
        max_workers=args.workers
    )
    
    # 打印摘要
    tester.print_summary(results)
    
    # 导出结果
    if args.export:
        tester.export_results(results, args.export)
    
    # 返回状态码
    failed_count = sum(1 for r in results if not r['success'])
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())