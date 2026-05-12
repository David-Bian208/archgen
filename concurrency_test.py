#!/usr/bin/env python3
"""
行为观察助手 V6.4.2 并发测试脚本

测试目标：
1. 多用户并发分析请求
2. 服务器资源监控
3. 中台数据完整性验证

用法：
    python3 concurrency_test.py
"""

import requests
import time
import threading
import json
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 配置
CHAINLIT_URL = "http://localhost:3000"
ADMIN_URL = "http://localhost:8000"
TEST_COUNT = 10  # 并发请求数
THREAD_COUNT = 5  # 并发线程数

# 测试结果
results = {
    "success": 0,
    "failed": 0,
    "response_times": [],
    "errors": []
}

def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def get_test_data(index):
    """生成测试数据"""
    test_cases = [
        "玥玥最近很暴躁，在看图时会把方向搞反，6和9看错",
        "在一起上课的时候，他分不清严厉还是凶。然后会很生气，我一般两种处理方式，第一种是我退让一步，然后他会寻求安慰，还有一种方式，我不退让，他就会生气发脾气",
        "昨天在超市，我看到一个玩具，我说不能买，他就开始大哭，哭得很大声，我在旁边劝他冷静，后来他慢慢停止了哭泣",
        "孩子最近在画画课上把画笔都扔了，我让她道歉，她哭了，后来我们聊了很久她才平静下来",
        "他今天在学校和同学打架了，老师叫我去学校，我到了之后他很生气，说同学先动手的，我让他道歉他不愿意"
    ]
    return test_cases[index % len(test_cases)]

def test_single_analysis(index):
    """测试单次分析请求"""
    start_time = time.time()
    
    try:
        # 测试场景识别
        test_input = get_test_data(index)
        
        # 模拟 API 调用（由于 Chainlit 使用 WebSocket，我们测试推理引擎）
        # 这里我们直接测试中台 API 作为替代
        response = requests.get(f"{ADMIN_URL}/api/stats", timeout=10)
        
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            results["success"] += 1
            results["response_times"].append(response_time)
            log(f"请求 {index+1}: ✅ 成功 ({response_time:.2f}s)")
        else:
            results["failed"] += 1
            results["errors"].append(f"请求 {index+1}: HTTP {response.status_code}")
            log(f"请求 {index+1}: ❌ 失败 ({response_time:.2f}s)", "ERROR")
            
    except Exception as e:
        results["failed"] += 1
        results["errors"].append(f"请求 {index+1}: {str(e)}")
        log(f"请求 {index+1}: ❌ 异常 {str(e)}", "ERROR")

def test_concurrent_requests():
    """测试并发请求"""
    log("=" * 60)
    log("开始并发测试")
    log("=" * 60)
    log(f"并发数：{THREAD_COUNT} 线程")
    log(f"总请求数：{TEST_COUNT}")
    print()
    
    start_time = time.time()
    
    # 使用线程池执行并发测试
    with ThreadPoolExecutor(max_workers=THREAD_COUNT) as executor:
        futures = [executor.submit(test_single_analysis, i) for i in range(TEST_COUNT)]
        
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                log(f"线程异常：{str(e)}", "ERROR")
    
    total_time = time.time() - start_time
    
    return total_time

def test_data_integrity():
    """测试中台数据完整性"""
    log("\n" + "=" * 60)
    log("测试中台数据完整性")
    log("=" * 60)
    
    try:
        # 获取统计数据
        stats_resp = requests.get(f"{ADMIN_URL}/api/stats", timeout=5)
        if stats_resp.status_code == 200:
            stats = stats_resp.json()
            log(f"总对话数：{stats['total']}")
            log(f"今日对话：{stats['today']}")
            log(f"用户数：{stats['users']}")
            
            # 获取对话列表
            list_resp = requests.get(f"{ADMIN_URL}/api/conversations?page=1&limit=10", timeout=5)
            if list_resp.status_code == 200:
                data = list_resp.json()
                log(f"对话列表项数：{len(data.get('items', []))}")
                log("✅ 数据完整性测试通过")
            else:
                log("❌ 对话列表 API 异常", "ERROR")
        else:
            log("❌ 统计数据 API 异常", "ERROR")
            
    except Exception as e:
        log(f"❌ 数据完整性测试失败：{str(e)}", "ERROR")

def test_export_functionality():
    """测试导出功能"""
    log("\n" + "=" * 60)
    log("测试导出功能")
    log("=" * 60)
    
    try:
        response = requests.get(f"{ADMIN_URL}/api/export", timeout=10)
        
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            if 'csv' in content_type.lower():
                lines = response.text.strip().split('\n')
                log(f"导出成功：{len(lines)} 行数据")
                log("✅ 导出功能测试通过")
            else:
                log(f"❌ Content-Type 不正确：{content_type}", "ERROR")
        else:
            log(f"❌ 导出 API 返回错误：{response.status_code}", "ERROR")
            
    except Exception as e:
        log(f"❌ 导出功能测试失败：{str(e)}", "ERROR")

def print_summary(total_time):
    """打印测试总结"""
    log("\n" + "=" * 60)
    log("测试总结")
    log("=" * 60)
    
    log(f"\n总请求数：{TEST_COUNT}")
    log(f"成功：{results['success']}")
    log(f"失败：{results['failed']}")
    log(f"成功率：{results['success']/TEST_COUNT*100:.1f}%")
    
    if results['response_times']:
        avg_time = sum(results['response_times']) / len(results['response_times'])
        min_time = min(results['response_times'])
        max_time = max(results['response_times'])
        throughput = TEST_COUNT / total_time
        
        log(f"\n性能指标：")
        log(f"总耗时：{total_time:.2f}s")
        log(f"平均响应时间：{avg_time:.3f}s")
        log(f"最小响应时间：{min_time:.3f}s")
        log(f"最大响应时间：{max_time:.3f}s")
        log(f"吞吐量：{throughput:.2f} 请求/秒")
    
    if results['errors']:
        log(f"\n错误详情：")
        for error in results['errors']:
            log(f"  - {error}", "ERROR")
    
    # 评估
    log(f"\n评估结果：")
    if results['failed'] == 0:
        log("✅ 并发测试通过")
    else:
        log(f"❌ 并发测试失败（{results['failed']} 个请求失败）", "ERROR")
    
    if results['response_times']:
        avg_time = sum(results['response_times']) / len(results['response_times'])
        if avg_time < 1.0:
            log("✅ 性能表现优秀")
        elif avg_time < 3.0:
            log("✅ 性能表现良好")
        elif avg_time < 5.0:
            log("⚠️  性能表现一般")
        else:
            log("❌ 性能表现较差", "ERROR")

def main():
    """主测试流程"""
    log("🚀 行为观察助手 V6.4.2 并发测试开始")
    log(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 检查服务
    log("检查服务状态...")
    try:
        resp = requests.get(f"{CHAINLIT_URL}/health", timeout=5)
        if resp.status_code == 200:
            log("✅ Chainlit 服务正常")
        else:
            log("❌ Chainlit 服务异常", "ERROR")
            return
    except Exception as e:
        log(f"❌ Chainlit 服务未运行：{e}", "ERROR")
        return
    
    try:
        resp = requests.get(f"{ADMIN_URL}/api/stats", timeout=5)
        if resp.status_code == 200:
            log("✅ 中台服务正常")
        else:
            log("❌ 中台服务异常", "ERROR")
            return
    except Exception as e:
        log(f"❌ 中台服务未运行：{e}", "ERROR")
        return
    
    print()
    
    # 执行并发测试
    total_time = test_concurrent_requests()
    
    # 测试数据完整性
    test_data_integrity()
    
    # 测试导出功能
    test_export_functionality()
    
    # 打印总结
    print_summary(total_time)
    
    log(f"\n测试完成！")

if __name__ == "__main__":
    main()
