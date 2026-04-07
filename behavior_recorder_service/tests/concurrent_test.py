#!/usr/bin/env python3
"""
并发性能测试脚本（V4.11.1）

测试优化后的服务性能：
- 10 并发请求
- 目标：成功率>90%，平均响应时间<10s
"""

import json
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests


def make_request(session_id: str) -> dict:
    """发送单个请求
    
    Args:
        session_id: 会话 ID
        
    Returns:
        请求结果字典
    """
    payload = {
        "session_id": session_id,
        "user_input": "在幼儿园做操时，小明一直盯着旁边的小朋友看，不跟着做动作",
        "child_profile": {
            "name": "小明",
            "age": 5,
            "stage": "kindergarten_middle"
        }
    }
    
    start_time = time.time()
    try:
        response = requests.post(
            "http://localhost:8001/api/v4/analyze",
            json=payload,
            timeout=90  # 90 秒超时（API 超时 60 秒 + 缓冲）
        )
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            return {
                "success": True,
                "elapsed": elapsed,
                "status_code": response.status_code,
                "error": None
            }
        else:
            return {
                "success": False,
                "elapsed": elapsed,
                "status_code": response.status_code,
                "error": f"HTTP {response.status_code}"
            }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "success": False,
            "elapsed": elapsed,
            "status_code": None,
            "error": str(e)
        }


def run_concurrent_test(num_requests: int = 10, max_workers: int = 10):
    """运行并发测试
    
    Args:
        num_requests: 总请求数（默认 10）
        max_workers: 最大并发数（默认 10）
        
    Returns:
        测试结果字典
    """
    print(f"🚀 开始并发测试：{num_requests} 个请求，{max_workers} 并发")
    print("=" * 60)
    
    start_time = time.time()
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有请求
        futures = {
            executor.submit(make_request, f"perf_test_{i}"): i
            for i in range(num_requests)
        }
        
        # 收集结果
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            
            # 实时显示进度
            idx = futures[future]
            status = "✅" if result["success"] else "❌"
            print(f"{status} 请求 {idx}: {result['elapsed']:.2f}s " + 
                  (f"- {result['error']}" if result['error'] else ""))
    
    total_time = time.time() - start_time
    
    # 统计分析
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    success_rate = len(successful) / len(results) * 100 if results else 0
    
    elapsed_times = [r["elapsed"] for r in successful]
    if elapsed_times:
        avg_time = statistics.mean(elapsed_times)
        min_time = min(elapsed_times)
        max_time = max(elapsed_times)
        median_time = statistics.median(elapsed_times)
    else:
        avg_time = min_time = max_time = median_time = 0
    
    # 输出报告
    print("\n" + "=" * 60)
    print("📊 性能测试报告")
    print("=" * 60)
    print(f"总请求数：{num_requests}")
    print(f"成功请求：{len(successful)}/{num_requests}")
    print(f"失败请求：{len(failed)}/{num_requests}")
    print(f"成功率：{success_rate:.1f}%")
    print(f"总耗时：{total_time:.2f}s")
    print(f"吞吐量：{num_requests/total_time:.2f} requests/s")
    print()
    print("响应时间统计:")
    print(f"  平均：{avg_time:.2f}s")
    print(f"  中位数：{median_time:.2f}s")
    print(f"  最小：{min_time:.2f}s")
    print(f"  最大：{max_time:.2f}s")
    print()
    
    # 验收标准
    print("📋 验收标准:")
    if success_rate >= 90:
        print(f"  ✅ 10 并发成功率：{success_rate:.1f}% >= 90%")
    else:
        print(f"  ❌ 10 并发成功率：{success_rate:.1f}% < 90%")
    
    if avg_time < 10:
        print(f"  ✅ 平均响应时间：{avg_time:.2f}s < 10s")
    else:
        print(f"  ❌ 平均响应时间：{avg_time:.2f}s >= 10s")
    
    print("=" * 60)
    
    # 返回测试结果
    return {
        "success_rate": success_rate,
        "avg_time": avg_time,
        "total_time": total_time,
        "passed": success_rate >= 90 and avg_time < 10
    }


if __name__ == "__main__":
    result = run_concurrent_test()
    exit(0 if result["passed"] else 1)
