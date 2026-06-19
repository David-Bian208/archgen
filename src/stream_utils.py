"""SSE Stream Utilities - SSE 流式输出工具"""

import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class StreamEvent:
    """流式事件"""
    step: str
    progress: int
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_sse(self) -> str:
        """转换为 SSE 格式"""
        data = self.to_dict()
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


class StreamProgress:
    """流式进度管理器"""
    
    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()
        self._closed = False
    
    async def send(self, event: StreamEvent):
        """发送事件"""
        if self._closed:
            return
        await self.queue.put(event)
    
    async def send_step(self, step: str, progress: int, message: str, data: Optional[Dict] = None):
        """发送步骤事件"""
        event = StreamEvent(step=step, progress=progress, message=message, data=data)
        await self.send(event)
    
    async def close(self):
        """关闭流"""
        self._closed = True
        await self.queue.put(None)  # 结束标记
    
    async def to_sse_stream(self) -> AsyncGenerator[str, None]:
        """转换为 SSE 流"""
        while True:
            event = await self.queue.get()
            if event is None:
                break
            yield event.to_sse()


async def stream_workflow(
    workflow_func,
    *args,
    **kwargs
) -> AsyncGenerator[str, None]:
    """包装工作流函数，使其支持流式输出"""
    progress = StreamProgress()
    
    async def run_workflow():
        try:
            result = await workflow_func(progress, *args, **kwargs)
            await progress.send_step("done", 100, "完成", {"result": result})
        except Exception as e:
            logger.error(f"工作流执行失败: {e}", exc_info=True)
            await progress.send_step("error", -1, f"执行失败: {str(e)}", error=str(e))
        finally:
            await progress.close()
    
    # 启动工作流
    asyncio.create_task(run_workflow())
    
    # 返回 SSE 流
    async for chunk in progress.to_sse_stream():
        yield chunk
