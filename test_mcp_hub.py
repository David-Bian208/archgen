"""测试 MCP Hub 功能"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.mcp_hub.hub_server import MCPHub
from src.mcp_hub.services.screenshot_service import ScreenshotMCPService


async def test_mcp_hub():
    print("=" * 60)
    print("测试 MCP Hub 功能")
    print("=" * 60)
    
    hub = MCPHub()
    screenshot_service = ScreenshotMCPService()
    hub.register_server("screenshot", screenshot_service)
    await hub.initialize()
    
    print("\n1. 测试服务发现（list_tools）")
    tools = await hub.list_tools()
    print(f"✅ 发现 {len(tools)} 个工具:")
    for tool in tools:
        print(f"   - {tool['jsName']}: {tool['description']}")
    
    print("\n2. 测试单次调用（capture）")
    html_content = """
    <html>
    <head><style>body{font-family:Arial;padding:40px;text-align:center;}</style></head>
    <body>
        <h1>MCP Hub 测试截图</h1>
        <p>如果能看到这段文字，说明 MCP Hub 工作正常</p>
    </body>
    </html>
    """
    output_path = "output/test_mcp_screenshot.png"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    start = time.time()
    result = await hub.invoke_tool("screenshot__capture", {
        "html": html_content,
        "output_path": output_path,
        "size": "default"
    })
    elapsed = time.time() - start
    
    if Path(result).exists():
        file_size = Path(result).stat().st_size
        print(f"✅ 截图成功! 耗时: {elapsed:.2f}s, 输出: {result} ({file_size} bytes)")
    else:
        print(f"❌ 截图失败")
    
    print("\n3. 测试沙箱编排（exec_code）")
    start = time.time()
    result = await hub.exec_code("""
async def _main():
    result = await mcp.callTool("screenshot__capture", {
        "html": html_content,
        "output_path": "output/test_mcp_exec.png",
        "size": "default"
    })
    return {
        "success": True,
        "output": result
    }
""", {
        "html_content": html_content
    })
    elapsed = time.time() - start
    
    print(f"✅ 沙箱执行成功! 耗时: {elapsed:.2f}s")
    print(f"   结果: {result}")
    
    print("\n4. 测试并行编排（parallel）")
    start = time.time()
    result = await hub.exec_code("""
async def _main():
    results = await parallel(
        mcp.callTool("screenshot__capture", {"html": html, "output_path": "output/test_parallel_1.png", "size": "default"}),
        mcp.callTool("screenshot__capture", {"html": html, "output_path": "output/test_parallel_2.png", "size": "default"})
    )
    return {
        "success": True,
        "outputs": results,
        "count": len(results)
    }
""", {
        "html": html_content
    })
    elapsed = time.time() - start
    
    print(f"✅ 并行执行成功! 耗时: {elapsed:.2f}s")
    print(f"   结果数量: {result.get('count', 0)}")
    
    await hub.shutdown()
    print("\n✅ 所有测试完成!")


if __name__ == "__main__":
    asyncio.run(test_mcp_hub())
