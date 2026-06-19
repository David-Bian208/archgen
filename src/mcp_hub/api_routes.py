"""ArchGen MCP Hub API 路由（增强版：流式/追踪/检查点/插件）"""

import logging
import asyncio
from typing import Dict, Optional, AsyncGenerator
from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import StreamingResponse
import json

from src.mcp_hub.hub_server import MCPHub
from src.mcp_hub.services.screenshot_service import ScreenshotMCPService
from src.mcp_hub.services.html_gen_service import HTMLGenMCPService
from src.mcp_hub.services.storage_service import StorageMCPService
from src.stream_utils import StreamProgress, StreamEvent, stream_workflow
from src.workflow_tracer import WorkflowTracer, get_tracer_manager
from src.checkpoint_manager import CheckpointManager, Checkpoint
from src.plugin_registry import get_plugin_registry

logger = logging.getLogger(__name__)

router = APIRouter()

_mcp_hub: Optional[MCPHub] = None
_checkpoint_manager = CheckpointManager()


async def get_mcp_hub() -> MCPHub:
    global _mcp_hub
    if _mcp_hub is None:
        _mcp_hub = MCPHub()
        
        screenshot_service = ScreenshotMCPService()
        _mcp_hub.register_server("screenshot", screenshot_service)
        
        html_gen_service = HTMLGenMCPService()
        _mcp_hub.register_server("html_gen", html_gen_service)
        
        storage_service = StorageMCPService()
        _mcp_hub.register_server("storage", storage_service)
        
        await _mcp_hub.initialize()
        logger.info("MCP Hub API 路由初始化完成（3个子服务）")
    return _mcp_hub


@router.get("/api/mcp/tools/list")
async def mcp_tools_list():
    """服务发现：获取所有可用工具列表"""
    try:
        hub = await get_mcp_hub()
        tools = await hub.list_tools()
        
        registry = get_plugin_registry()
        plugin_tools = registry.list_all_tools()
        
        return {"code": 0, "data": tools + plugin_tools}
    except Exception as e:
        logger.error(f"获取工具列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/mcp/tools/call")
async def mcp_tools_call(request: Dict = Body(...)):
    """单次调用：调用指定工具"""
    try:
        tool_name = request.get("name")
        if not tool_name:
            raise ValueError("缺少工具名称")
        
        params = request.get("params", {})
        
        hub = await get_mcp_hub()
        result = await hub.invoke_tool(tool_name, params)
        
        return {"code": 0, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"调用工具失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/mcp/exec")
async def mcp_exec(request: Dict = Body(...)):
    """编排执行：在沙箱中执行编排代码"""
    try:
        code = request.get("code")
        if not code:
            raise ValueError("缺少代码")
        
        context = request.get("context", {})
        
        hub = await get_mcp_hub()
        result = await hub.exec_code(code, context)
        
        return {"code": 0, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"沙箱执行失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"沙箱执行失败: {str(e)}")


@router.post("/api/mcp/poster/generate")
async def mcp_poster_generate(request: Dict = Body(...)):
    """一键生成海报：使用 MCP 编排自动完成提取→渲染→截图流程"""
    try:
        html_content = request.get("html_content")
        if not html_content:
            raise ValueError("缺少 HTML 内容")
        
        output_path = request.get("output_path", "output/poster.png")
        size = request.get("size", "default")
        
        hub = await get_mcp_hub()
        
        result = await hub.exec_code(f"""
async def _main():
    result = await mcp.callTool("screenshot__capture", {{
        "html": html_content,
        "output_path": output_path,
        "size": size
    }})
    return {{
        "success": True,
        "output_path": result,
        "size": size
    }}
""", {
            "html_content": html_content,
            "output_path": output_path,
            "size": size
        })
        
        return {"code": 0, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"海报生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"海报生成失败: {str(e)}")


@router.post("/api/mcp/poster/generate-batch")
async def mcp_poster_generate_batch(request: Dict = Body(...)):
    """批量生成海报：并行生成多个尺寸"""
    try:
        html_content = request.get("html_content")
        if not html_content:
            raise ValueError("缺少 HTML 内容")
        
        output_dir = request.get("output_dir", "output")
        sizes = request.get("sizes", ["wechat", "xiaohongshu", "ppt"])
        
        hub = await get_mcp_hub()
        
        tasks_code = ", ".join([
            f'mcp.callTool("screenshot__capture", {{"html": html_content, "output_path": "{output_dir}/poster_{size}.png", "size": "{size}"}})'
            for size in sizes
        ])
        
        result = await hub.exec_code(f"""
async def _main():
    results = await parallel({tasks_code})
    return {{
        "success": True,
        "outputs": results,
        "count": len(results)
    }}
""", {
            "html_content": html_content,
            "output_dir": output_dir,
            "sizes": sizes
        })
        
        return {"code": 0, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"批量海报生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"批量海报生成失败: {str(e)}")


@router.post("/api/mcp/poster/full-pipeline")
async def mcp_poster_full_pipeline(request: Dict = Body(...)):
    """完整海报流水线：HTML生成→截图→存储→返回URL"""
    try:
        data = request.get("data")
        framework = request.get("framework", "claim")
        style = request.get("style", "minimal")
        sizes = request.get("sizes", ["default"])
        
        if not data:
            raise ValueError("缺少数据")
        
        hub = await get_mcp_hub()
        
        pipeline_code = """
async def _main():
    results = []
    
    for size in size_list:
        html = await mcp.callTool("html_gen__render", {
            "data": data,
            "framework": framework,
            "style": style,
            "size": size
        })
        
        output_path = f"output/poster_{framework}_{size}.png"
        
        png_path = await mcp.callTool("screenshot__capture", {
            "html": html,
            "output_path": output_path,
            "size": size
        })
        
        file_info = await mcp.callTool("storage__get_file_url", {
            "file_path": png_path
        })
        
        results.append({
            "size": size,
            "html_length": len(html),
            "png_path": png_path,
            "url": file_info.get("url", png_path),
            "file_size": file_info.get("size", 0)
        })
    
    return {
        "success": True,
        "framework": framework,
        "style": style,
        "outputs": results,
        "count": len(results)
    }
"""
        
        result = await hub.exec_code(pipeline_code, {
            "data": data,
            "framework": framework,
            "style": style,
            "size_list": sizes
        })
        
        return {"code": 0, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"完整流水线失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"完整流水线失败: {str(e)}")


# ========== 新增：流式输出端点 ==========

@router.post("/api/mcp/poster/full-pipeline/stream")
async def mcp_poster_full_pipeline_stream(request: Dict = Body(...)):
    """流式海报流水线：实时返回进度"""
    
    async def event_stream() -> AsyncGenerator[str, None]:
        progress = StreamProgress()
        
        async def run_pipeline():
            try:
                data = request.get("data")
                framework = request.get("framework", "claim")
                style = request.get("style", "minimal")
                sizes = request.get("sizes", ["default"])
                
                await progress.send_step("start", 0, "开始生成海报...")
                
                hub = await get_mcp_hub()
                results = []
                
                for i, size in enumerate(sizes):
                    step_progress = int((i + 1) / len(sizes) * 100)
                    
                    await progress.send_step(
                        "html_gen", 
                        int(step_progress * 0.3), 
                        f"正在生成HTML ({size})..."
                    )
                    
                    html = await hub.invoke_tool("html_gen__render", {
                        "data": data,
                        "framework": framework,
                        "style": style,
                        "size": size
                    })
                    
                    await progress.send_step(
                        "screenshot",
                        int(step_progress * 0.6),
                        f"正在截图 ({size})..."
                    )
                    
                    output_path = f"output/poster_{framework}_{size}.png"
                    
                    png_path = await hub.invoke_tool("screenshot__capture", {
                        "html": html,
                        "output_path": output_path,
                        "size": size
                    })
                    
                    await progress.send_step(
                        "storage",
                        int(step_progress * 0.9),
                        f"正在保存 ({size})..."
                    )
                    
                    file_info = await hub.invoke_tool("storage__get_file_url", {
                        "file_path": png_path
                    })
                    
                    results.append({
                        "size": size,
                        "html_length": len(html),
                        "png_path": png_path,
                        "url": file_info.get("url", png_path),
                        "file_size": file_info.get("size", 0)
                    })
                
                await progress.send_step("done", 100, "完成", {
                    "framework": framework,
                    "style": style,
                    "outputs": results,
                    "count": len(results)
                })
                
            except Exception as e:
                logger.error(f"流式流水线失败: {e}", exc_info=True)
                await progress.send_step("error", -1, f"执行失败: {str(e)}", error=str(e))
            finally:
                await progress.close()
        
        import asyncio
        asyncio.create_task(run_pipeline())
        
        async for chunk in progress.to_sse_stream():
            yield chunk
    
    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ========== 新增：可观测性端点 ==========

@router.get("/api/workflow/trace/{session_id}")
async def get_workflow_trace(session_id: str):
    """获取工作流追踪数据"""
    tracer_manager = get_tracer_manager()
    tracer = tracer_manager.get_tracer(session_id)
    
    if not tracer:
        return {"code": 404, "message": "未找到追踪数据"}
    
    return {"code": 0, "data": tracer.export()}


@router.get("/api/workflow/traces")
async def list_all_traces():
    """列出所有工作流追踪"""
    tracer_manager = get_tracer_manager()
    return {"code": 0, "data": tracer_manager.export_all()}


# ========== 新增：检查点端点 ==========

@router.post("/api/workflow/checkpoint")
async def create_checkpoint(request: Dict = Body(...)):
    """创建工作流检查点"""
    session_id = request.get("session_id")
    step = request.get("step")
    step_name = request.get("step_name")
    results = request.get("results", {})
    status = request.get("status", "running")
    
    if not session_id or step is None or not step_name:
        raise HTTPException(status_code=400, detail="缺少必填参数")
    
    checkpoint = _checkpoint_manager.create_checkpoint(
        session_id, step, step_name, results, status
    )
    
    return {"code": 0, "data": {"session_id": checkpoint.session_id, "step": checkpoint.step}}


@router.get("/api/workflow/checkpoint/{session_id}")
async def get_checkpoint(session_id: str):
    """获取工作流检查点"""
    checkpoint = _checkpoint_manager.load_checkpoint(session_id)
    
    if not checkpoint:
        return {"code": 404, "message": "未找到检查点"}
    
    from dataclasses import asdict
    return {"code": 0, "data": asdict(checkpoint)}


@router.post("/api/workflow/checkpoint/{session_id}/resume")
async def resume_checkpoint(session_id: str, request: Dict = Body(...)):
    """从检查点恢复工作流"""
    checkpoint = _checkpoint_manager.load_checkpoint(session_id)
    
    if not checkpoint:
        raise HTTPException(status_code=404, detail="未找到检查点")
    
    if checkpoint.status == "completed":
        return {"code": 0, "data": {"message": "工作流已完成", "results": checkpoint.results}}
    
    return {"code": 0, "data": {
        "message": "准备恢复",
        "from_step": checkpoint.step,
        "step_name": checkpoint.step_name,
        "saved_results": checkpoint.results
    }}


@router.delete("/api/workflow/checkpoint/{session_id}")
async def delete_checkpoint(session_id: str):
    """删除检查点"""
    success = _checkpoint_manager.delete_checkpoint(session_id)
    
    if success:
        return {"code": 0, "message": "检查点已删除"}
    else:
        return {"code": 404, "message": "检查点不存在"}


# ========== 新增：插件端点 ==========

@router.get("/api/plugins/list")
async def list_plugins():
    """列出所有插件和工具"""
    registry = get_plugin_registry()
    return {"code": 0, "data": registry.list_all_tools()}


@router.post("/api/plugins/call/{tool_id}")
async def call_plugin_tool(tool_id: str, request: Dict = Body(...)):
    """调用插件工具"""
    registry = get_plugin_registry()
    tool = registry.get_tool(tool_id)
    
    if not tool:
        raise HTTPException(status_code=404, detail=f"工具不存在: {tool_id}")
    
    try:
        params = request.get("params", {})
        result = await tool.handler(**params)
        return {"code": 0, "data": result}
    except Exception as e:
        logger.error(f"调用插件工具失败: {tool_id} - {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
