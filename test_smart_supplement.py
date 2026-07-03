"""测试 smart_supplement API"""
import asyncio
import httpx

async def test_smart_supplement():
    """测试智能补充 API"""
    url = "http://localhost:8972/api/workflow/supplement/smart"
    
    # 测试用例 1: 字符串类型的 missing_item
    payload1 = {
        "session_id": "test-session-1",
        "topic": "作者身份定位",
        "context": "测试上下文",
        "missing_items": ["作者身份定位", "具体案例或数据"],
        "missing_item": "作者身份定位",  # 字符串类型
        "force_level": None,
        "retrieval_results": []
    }
    
    print("=== 测试 1: 字符串类型的 missing_item ===")
    print(f"请求: {payload1}")
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(url, json=payload1)
            print(f"状态码: {response.status_code}")
            print(f"响应: {response.json()}")
        except Exception as e:
            print(f"错误: {e}")
    
    # 测试用例 2: 字典类型的 missing_item
    payload2 = {
        "session_id": "test-session-2",
        "topic": "具体案例或数据",
        "context": "测试上下文",
        "missing_items": ["作者身份定位", "具体案例或数据"],
        "missing_item": {
            "dimension": "数据支撑",
            "label": "具体案例或数据",
            "description": "需要具体的案例或数据支撑"
        },  # 字典类型
        "force_level": None,
        "retrieval_results": []
    }
    
    print("\n=== 测试 2: 字典类型的 missing_item ===")
    print(f"请求: {payload2}")
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(url, json=payload2)
            print(f"状态码: {response.status_code}")
            print(f"响应: {response.json()}")
        except Exception as e:
            print(f"错误: {e}")

if __name__ == "__main__":
    asyncio.run(test_smart_supplement())
