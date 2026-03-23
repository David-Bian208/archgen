"""
行为观察伙伴 - 简单性能测试
不需要额外依赖，使用 requests + threading
"""

import requests
import time
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 配置
API_URL = "http://localhost:8000"
TEST_SCENARIOS = [
    "我儿子在课堂上总是突然发出奇怪的声音，老师看他时他就笑。",
    "我女儿每天写作业时总是要去喝水、上厕所，就是不想写作业。",
    "孩子经常一个人摇晃身体，盯着旋转的风扇看。",
    "孩子每天都要走同样的路线去幼儿园，换一条路就会大哭大闹。",
    "孩子在游乐场想和其他小朋友玩，但直接抢玩具。",
]

# 结果统计
results = []
lock = threading.Lock()


def single_request(scenario, user_id):
    """单次请求"""
    start_time = time.time()
    
    try:
        payload = {
            "session_id": None,
            "user_input": scenario
        }
        
        response = requests.post(f"{API_URL}/api/v4/chat", json=payload, timeout=30)
        
        elapsed = time.time() - start_time
        
        result = {
            "user_id": user_id,
            "scenario": scenario[:20] + "...",
            "status_code": response.status_code,
            "elapsed": elapsed,
            "success": response.status_code == 200,
            "timestamp": datetime.now().isoformat()
        }
        
        with lock:
            results.append(result)
        
        status = "✅" if result["success"] else "❌"
        print(f"{status} 用户{user_id}: {elapsed:.2f}s (状态码：{response.status_code})")
        
    except Exception as e:
        elapsed = time.time() - start_time
        
        result = {
            "user_id": user_id,
            "scenario": scenario[:20] + "...",
            "status_code": 0,
            "elapsed": elapsed,
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        
        with lock:
            results.append(result)
        
        print(f"❌ 用户{user_id}: {elapsed:.2f}s (错误：{e})")


def run_concurrent_test(num_users=10):
    """并发测试"""
    print("=" * 60)
    print(f"并发测试：{num_users} 个用户同时提交")
    print("=" * 60)
    
    results.clear()
    start_time = time.time()
    
    # 使用线程池模拟并发
    with ThreadPoolExecutor(max_workers=num_users) as executor:
        futures = []
        
        for i in range(num_users):
            scenario = TEST_SCENARIOS[i % len(TEST_SCENARIOS)]
            future = executor.submit(single_request, scenario, i + 1)
            futures.append(future)
        
        # 等待所有请求完成
        for future in as_completed(futures):
            pass
    
    total_time = time.time() - start_time
    
    # 统计结果
    print("\n" + "=" * 60)
    print("测试结果统计")
    print("=" * 60)
    
    total = len(results)
    success = sum(1 for r in results if r["success"])
    failed = total - success
    
    avg_time = sum(r["elapsed"] for r in results) / total if total > 0 else 0
    max_time = max((r["elapsed"] for r in results), default=0)
    min_time = min((r["elapsed"] for r in results), default=0)
    
    print(f"\n请求总数：{total}")
    print(f"✅ 成功：{success} ({success/total*100:.1f}%)")
    print(f"❌ 失败：{failed} ({failed/total*100:.1f}%)")
    print(f"\n响应时间:")
    print(f"  平均：{avg_time:.2f}s")
    print(f"  最快：{min_time:.2f}s")
    print(f"  最慢：{max_time:.2f}s")
    print(f"  总耗时：{total_time:.2f}s")
    
    # 性能评级
    print(f"\n性能评级:")
    if avg_time < 5:
        print(f"  ⭐⭐⭐⭐⭐ 优秀（平均 {avg_time:.2f}s < 5s）")
    elif avg_time < 10:
        print(f"  ⭐⭐⭐⭐ 良好（平均 {avg_time:.2f}s < 10s）")
    elif avg_time < 15:
        print(f"  ⭐⭐⭐ 一般（平均 {avg_time:.2f}s < 15s）")
    else:
        print(f"  ⭐⭐ 需优化（平均 {avg_time:.2f}s >= 15s）")
    
    # 保存结果
    report = {
        "test_type": "concurrent_users",
        "num_users": num_users,
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": total,
            "success": success,
            "failed": failed,
            "success_rate": f"{success/total*100:.1f}%",
            "avg_time": f"{avg_time:.2f}s",
            "max_time": f"{max_time:.2f}s",
            "min_time": f"{min_time:.2f}s",
            "total_time": f"{total_time:.2f}s"
        },
        "results": results
    }
    
    import json
    with open("performance_test_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n报告已保存到：performance_test_report.json")
    
    return avg_time < 15  # 平均响应时间<15s 为合格


def run_single_performance_test():
    """单次性能测试"""
    print("=" * 60)
    print("单次请求性能测试")
    print("=" * 60)
    
    scenario = TEST_SCENARIOS[0]
    
    # 测试 3 次取平均
    times = []
    for i in range(3):
        start = time.time()
        
        payload = {
            "session_id": None,
            "user_input": scenario
        }
        
        response = requests.post(f"{API_URL}/api/v4/chat", json=payload, timeout=30)
        
        elapsed = time.time() - start
        times.append(elapsed)
        
        print(f"第{i+1}次：{elapsed:.2f}s (状态码：{response.status_code})")
    
    avg = sum(times) / len(times)
    
    print(f"\n平均响应时间：{avg:.2f}s")
    
    if avg < 5:
        print("✅ 性能优秀 (<5s)")
    elif avg < 10:
        print("✅ 性能良好 (<10s)")
    elif avg < 15:
        print("⚠️  性能一般 (<15s)")
    else:
        print("❌ 性能需优化 (>=15s)")
    
    return avg


def run_lighthouse_test():
    """Lighthouse 性能测试（需要安装）"""
    print("\n" + "=" * 60)
    print("Lighthouse 性能测试")
    print("=" * 60)
    
    try:
        import subprocess
        
        # 检查 lighthouse 是否安装
        result = subprocess.run(
            ["which", "lighthouse"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("运行 Lighthouse CLI...")
            subprocess.run([
                "lighthouse",
                "http://localhost:3000",
                "--output", "html",
                "--output-path", "lighthouse_report.html",
                "--quiet"
            ])
            print("✅ Lighthouse 报告已生成：lighthouse_report.html")
        else:
            print("⚠️  Lighthouse CLI 未安装")
            print("安装命令：npm install -g lighthouse")
            print("或使用在线测试：https://pagespeed.web.dev/")
    except Exception as e:
        print(f"❌ Lighthouse 测试失败：{e}")


def main():
    """主函数"""
    print("=" * 60)
    print("行为观察伙伴 - 性能测试套件")
    print("=" * 60)
    print()
    
    # 1. 单次性能测试
    print("【1. 单次请求性能测试】")
    avg_time = run_single_performance_test()
    
    print("\n")
    
    # 2. 并发测试
    print("【2. 并发用户测试】")
    concurrent_pass = run_concurrent_test(num_users=10)
    
    print("\n")
    
    # 3. Lighthouse 测试
    print("【3. Lighthouse 前端性能测试】")
    run_lighthouse_test()
    
    print("\n" + "=" * 60)
    print("性能测试完成")
    print("=" * 60)
    
    # 总体评价
    print("\n总体评价:")
    if avg_time < 10 and concurrent_pass:
        print("✅ 性能达标，可以发布")
    elif avg_time < 15:
        print("⚠️  性能可接受，建议优化后发布")
    else:
        print("❌ 性能不达标，需要优化")


if __name__ == "__main__":
    main()
