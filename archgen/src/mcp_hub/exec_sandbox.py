"""Exec Sandbox - 沙箱编排引擎（支持 parallel/settle）"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)


class ExecSandbox:
    """沙箱编排引擎 - 提供安全的工具编排执行环境"""
    
    def __init__(self, mcp_hub):
        self.mcp_hub = mcp_hub
        self.execution_count = 0
    
    async def execute(self, code: str, context: Dict) -> Any:
        """在沙箱中执行编排代码"""
        self.execution_count += 1
        execution_id = f"exec_{self.execution_count}"
        logger.info(f"开始执行沙箱代码: {execution_id}")
        
        sandbox_context = {
            "mcp": self._create_mcp_proxy(),
            "parallel": asyncio.gather,
            "settle": self._create_settle(),
            "logger": logger,
            **context
        }
        
        try:
            result = await self._run_in_sandbox(code, sandbox_context)
            logger.info(f"沙箱代码执行成功: {execution_id}")
            return result
        except Exception as e:
            logger.error(f"沙箱代码执行失败: {execution_id} - {e}")
            raise
    
    def _create_mcp_proxy(self):
        class MCPProxy:
            def __init__(self, hub):
                self._hub = hub
            
            async def callTool(self, tool_name: str, params: Dict) -> Any:
                return await self._hub.invoke_tool(tool_name, params)
            
            async def callToolSafe(self, tool_name: str, params: Dict) -> Dict:
                try:
                    result = await self.callTool(tool_name, params)
                    return {"success": True, "data": result}
                except Exception as e:
                    return {"success": False, "error": str(e)}
            
            async def listTools(self) -> list:
                return await self._hub.list_tools()
        
        return MCPProxy(self.mcp_hub)
    
    def _create_settle(self) -> Callable:
        """创建 settle（类似 Promise.settle，返回所有结果包括异常）"""
        async def settle(*coroutines):
            results = []
            for coro in coroutines:
                try:
                    result = await coro
                    results.append({"status": "fulfilled", "value": result})
                except Exception as e:
                    results.append({"status": "rejected", "reason": str(e)})
            return results
        return settle
    
    async def _run_in_sandbox(self, code: str, context: Dict) -> Any:
        try:
            has_main = "async def _main" in code or "def _main" in code
            
            if has_main:
                wrapped_code = f"""
import asyncio

{code}

async def _sandboxexec():
    if asyncio.iscoroutinefunction(_main):
        return await _main()
    else:
        return _main()
"""
            else:
                lines = code.strip().split("\n")
                indented = "\n".join("    " + line for line in lines)
                wrapped_code = f"""
async def _sandboxexec():
{indented}
"""
            
            exec_globals = {
                "mcp": context["mcp"],
                "parallel": context["parallel"],
                "settle": context["settle"],
                "logger": context["logger"],
                "__builtins__": {
                    "print": print,
                    "len": len,
                    "str": str,
                    "int": int,
                    "float": float,
                    "list": list,
                    "dict": dict,
                    "tuple": tuple,
                    "set": set,
                    "range": range,
                    "enumerate": enumerate,
                    "zip": zip,
                    "map": map,
                    "filter": filter,
                    "sorted": sorted,
                    "reversed": reversed,
                    "min": min,
                    "max": max,
                    "sum": sum,
                    "abs": abs,
                    "round": round,
                    "isinstance": isinstance,
                    "type": type,
                    "hasattr": hasattr,
                    "getattr": getattr,
                    "setattr": setattr,
                    "Exception": Exception,
                    "ValueError": ValueError,
                    "TypeError": TypeError,
                    "KeyError": KeyError,
                    "IndexError": IndexError,
                    "AttributeError": AttributeError,
                    "RuntimeError": RuntimeError,
                }
            }
            
            for key, value in context.items():
                if key not in ["mcp", "parallel", "settle", "logger", "__builtins__"]:
                    exec_globals[key] = value
            
            exec(compile(wrapped_code, "<sandbox>", "exec"), exec_globals)
            return await exec_globals["_sandboxexec"]()
            
        except Exception as e:
            logger.error(f"沙箱执行失败: {e}")
            raise RuntimeError(f"沙箱执行失败: {e}") from e
