#!/usr/bin/env python3
"""
行为观察助手 V6.4.2 自动化测试脚本
测试：ABC 智能引导 + 中台数据记录

用法：python3 auto_test_v642.py
"""

import requests
import json
import time
import sys
from datetime import datetime

# 配置
CHAINLIT_URL = "http://localhost:3000"
ADMIN_URL = "http://localhost:8000"

# 测试结果统计
test_results = []

def log(message, level="INFO"):
    """打印日志"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def check_services():
    """检查服务是否运行"""
    log("检查服务状态...")
    
    try:
        # 检查 Chainlit
        resp = requests.get(f"{CHAINLIT_URL}/health", timeout=5)
        if resp.status_code == 200:
            log("✅ Chainlit 服务运行正常 (端口 3000)")
        else:
            log("❌ Chainlit 服务异常", "ERROR")
            return False
    except Exception as e:
        log(f" Chainlit 服务未运行：{e}", "ERROR")
        return False
    
    try:
        # 检查中台
        resp = requests.get(f"{ADMIN_URL}/api/stats", timeout=5)
        if resp.status_code == 200:
            log("✅ 中台服务运行正常 (端口 8000)")
        else:
            log("❌ 中台服务异常", "ERROR")
            return False
    except Exception as e:
        log(f"❌ 中台服务未运行：{e}", "ERROR")
        return False
    
    return True

def test_abc_smart_guidance():
    """测试 1：ABC 智能引导 - B 包含 C 信息"""
    log("=" * 60)
    log("测试 1：ABC 智能引导 - B 包含 C 信息")
    log("=" * 60)
    
    test_input = """在一起上课的时候，他分不清严厉还是凶。然后会很生气，我一般两种处理方式，第一种是我退让一步，然后他会寻求安慰，想希望我安慰她，还有一种方式，我不退让，他就会生气发脾气，但发脾气的过程当中会克制，说我不想当好孩子啦，我想发脾气啦"""
    
    log(f"输入内容（长度：{len(test_input)} 字符）")
    log("预期：系统识别到 B 中包含 C 信息，直接出报告，不再追问 C")
    
    # 这里需要模拟 Chainlit 的对话流程
    # 由于 Chainlit 是 WebSocket 协议，我们使用简化的 HTTP 测试
    # 实际测试需要查看日志或使用浏览器自动化
    
    log("⚠️  Chainlit 使用 WebSocket 协议，无法直接用 HTTP 测试")
    log(" 请使用浏览器手动测试以下场景：")
    log(f"   1. 访问 {CHAINLIT_URL}")
    log("   2. 输入以下内容并发送：")
    print()
    print("   " + test_input)
    print()
    log("   3. 观察系统响应：")
    log("      ✅ 应直接生成报告，不再追问 C")
    log("      ❌ 如果继续追问 '您当时是怎么处理的？' 则测试失败")
    print()
    
    test_results.append({
        "name": "测试 1：ABC 智能引导",
        "status": "需要手动验证",
        "note": "请按照上述步骤在浏览器中测试"
    })

def test_admin_data_recording():
    """测试 2：中台数据记录"""
    log("=" * 60)
    log("测试 2：中台数据记录功能")
    log("=" * 60)
    
    try:
        # 获取当前统计数据
        resp = requests.get(f"{ADMIN_URL}/api/stats", timeout=5)
        stats = resp.json()
        
        log(f"当前统计数据：")
        log(f"  总对话数：{stats['total']}")
        log(f"  今日对话：{stats['today']}")
        log(f"  平均响应：{stats['avg_time']:.1f} 秒" if stats['avg_time'] else "  平均响应：无数据")
        log(f"  用户数：{stats['users']}")
        
        # 测试对话列表 API
        resp = requests.get(f"{ADMIN_URL}/api/conversations?page=1&limit=5", timeout=5)
        data = resp.json()
        
        log(f"\n对话列表（最近 5 条）：")
        for i, item in enumerate(data.get('items', []), 1):
            log(f"  {i}. [{item.get('scene_type', '-')} 场景] {item['user_message'][:50]}...")
        
        log("\n✅ 中台 API 正常工作")
        log("💡 请在浏览器中访问 http://localhost:8000 查看完整界面")
        
        test_results.append({
            "name": "测试 2：中台数据记录",
            "status": "通过",
            "note": "API 测试通过，界面请手动验证"
        })
        
    except Exception as e:
        log(f" 中台 API 测试失败：{e}", "ERROR")
        test_results.append({
            "name": "测试 2：中台数据记录",
            "status": "失败",
            "note": str(e)
        })

def test_admin_search():
    """测试 3：中台搜索功能"""
    log("=" * 60)
    log("测试 3：中台搜索与筛选功能")
    log("=" * 60)
    
    try:
        # 测试搜索 API
        search_keyword = "暴躁"
        resp = requests.get(f"{ADMIN_URL}/api/conversations?search={search_keyword}&page=1&limit=5", timeout=5)
        data = resp.json()
        
        log(f"搜索关键词：'{search_keyword}'")
        log(f"找到 {data['total']} 条结果")
        
        # 测试场景筛选 API
        for scene in ["A", "B", "C", "D", "E"]:
            resp = requests.get(f"{ADMIN_URL}/api/conversations?scene={scene}&page=1&limit=1", timeout=5)
            data = resp.json()
            log(f"场景 {scene} 类：{data['total']} 条")
        
        log("\n✅ 搜索与筛选 API 正常工作")
        
        test_results.append({
            "name": "测试 3：中台搜索筛选",
            "status": "通过",
            "note": "API 测试通过"
        })
        
    except Exception as e:
        log(f"❌ 搜索 API 测试失败：{e}", "ERROR")
        test_results.append({
            "name": "测试 3：中台搜索筛选",
            "status": "失败",
            "note": str(e)
        })

def test_admin_export():
    """测试 4：中台导出功能"""
    log("=" * 60)
    log("测试 4：中台导出 CSV 功能")
    log("=" * 60)
    
    try:
        # 测试导出 API
        resp = requests.get(f"{ADMIN_URL}/api/export", timeout=5)
        
        if resp.status_code == 200:
            content_type = resp.headers.get('Content-Type', '')
            content_disposition = resp.headers.get('Content-Disposition', '')
            
            log(f"导出响应状态：{resp.status_code}")
            log(f"Content-Type：{content_type}")
            log(f"Content-Disposition：{content_disposition}")
            
            # 检查 CSV 内容
            csv_content = resp.text
            lines = csv_content.strip().split('\n')
            log(f"CSV 行数：{len(lines)}")
            log(f"CSV 表头：{lines[0] if lines else '无'}")
            
            log("\n✅ 导出 API 正常工作")
            log(" 请在浏览器中点击'导出 CSV'按钮测试完整功能")
            
            test_results.append({
                "name": "测试 4：中台导出 CSV",
                "status": "通过",
                "note": "API 测试通过，界面导出请手动验证"
            })
        else:
            log(f"❌ 导出 API 返回错误：{resp.status_code}", "ERROR")
            test_results.append({
                "name": "测试 4：中台导出 CSV",
                "status": "失败",
                "note": f"HTTP {resp.status_code}"
            })
        
    except Exception as e:
        log(f"❌ 导出 API 测试失败：{e}", "ERROR")
        test_results.append({
            "name": "测试 4：中台导出 CSV",
            "status": "失败",
            "note": str(e)
        })

def print_summary():
    """打印测试总结"""
    log("\n" + "=" * 60)
    log("测试总结")
    log("=" * 60)
    
    passed = sum(1 for r in test_results if r['status'] == '通过')
    failed = sum(1 for r in test_results if r['status'] == '失败')
    manual = sum(1 for r in test_results if r['status'] == '需要手动验证')
    
    log(f"\n总测试数：{len(test_results)}")
    log(f"✅ 通过：{passed}")
    log(f"❌ 失败：{failed}")
    log(f"⚠️  需要手动验证：{manual}")
    
    print("\n详细结果：")
    for i, result in enumerate(test_results, 1):
        status_icon = "✅" if result['status'] == '通过' else "❌" if result['status'] == '失败' else "⚠️"
        log(f"  {i}. {status_icon} {result['name']}")
        if result.get('note'):
            log(f"     备注：{result['note']}")
    
    print()
    if failed > 0:
        log("❌ 有测试失败，请修复后重新测试", "ERROR")
        return False
    elif manual > 0:
        log("⚠️  部分测试需要手动验证，请在浏览器中完成", "WARNING")
        log("💡 手动验证完成后，所有测试通过即可部署")
        return True
    else:
        log("✅ 所有测试通过！可以部署到阿里云", "SUCCESS")
        return True

def main():
    """主测试流程"""
    log("🚀 行为观察助手 V6.4.2 自动化测试开始")
    log(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 步骤 1：检查服务
    if not check_services():
        log("❌ 服务检查失败，请确保 3000 和 8000 端口服务正常运行", "ERROR")
        log("启动命令：")
        log("  python3 admin_dashboard.py")
        log("  cd chainlit_v62 && chainlit run app.py --port 3000")
        sys.exit(1)
    
    print()
    
    # 步骤 2：执行测试
    test_abc_smart_guidance()
    print()
    
    test_admin_data_recording()
    print()
    
    test_admin_search()
    print()
    
    test_admin_export()
    print()
    
    # 步骤 3：打印总结
    success = print_summary()
    
    # 返回退出码
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
