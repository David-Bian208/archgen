"""
dev-logs Skill 执行器

日志查看、搜索、分析
"""

import subprocess
from pathlib import Path
from typing import List, Dict
from datetime import datetime


def view_logs(log_file: str = None, lines: int = 100, level: str = None) -> str:
    """查看日志"""
    if log_file is None:
        # 查找日志文件
        workspace = Path(__file__).parent.parent.parent.parent
        log_files = list(workspace.rglob("*.log"))
        if log_files:
            log_file = str(log_files[0])
        else:
            return "ℹ️ 未找到日志文件"
    
    try:
        # 使用 tail 命令查看日志
        cmd = ["tail", "-n", str(lines), log_file]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        content = result.stdout
        
        # 按级别统计
        stats = {
            "INFO": content.count("INFO"),
            "WARNING": content.count("WARNING"),
            "ERROR": content.count("ERROR"),
        }
        
        # 按级别过滤
        if level:
            lines = [l for l in content.split('\n') if level in l]
            content = '\n'.join(lines)
        
        return f"""
📋 日志查看

**日志文件：** {log_file}
**行数：** {lines}

**日志内容：**
```
{content[:1000]}
```

**统计：**
- INFO: {stats['INFO']}
- WARNING: {stats['WARNING']}
- ERROR: {stats['ERROR']}
"""
    except Exception as e:
        return f"❌ 查看日志失败：{str(e)}"


def search_logs(keyword: str, log_file: str = None) -> str:
    """搜索日志"""
    if log_file is None:
        workspace = Path(__file__).parent.parent.parent.parent
        log_files = list(workspace.rglob("*.log"))
        if log_files:
            log_file = str(log_files[0])
        else:
            return "ℹ️ 未找到日志文件"
    
    try:
        cmd = ["grep", "-i", keyword, log_file]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        matches = result.stdout.strip().split('\n')
        matches = [m for m in matches if m]  # 移除空行
        
        if not matches:
            return f"🔍 未找到包含 '{keyword}' 的日志"
        
        return f"""
🔍 日志搜索

**关键词：** {keyword}
**日志文件：** {log_file}
**匹配结果：** {len(matches)} 条

**匹配内容：**
```
{chr(10).join(matches[:10])}
```
"""
    except Exception as e:
        return f"❌ 搜索失败：{str(e)}"


def analyze_error(error_log: str) -> str:
    """分析错误日志"""
    return f"""
🔍 错误分析

**错误日志：**
{error_log[:500]}

**可能原因：**
1. 代码逻辑错误
2. 依赖问题
3. 配置错误

**排查步骤：**
1. 查看完整错误堆栈
2. 检查相关代码
3. 检查配置文件

**建议：**
提供更多上下文以便精确分析
"""


def execute(command: str) -> str:
    """执行命令"""
    cmd = command.lower()
    
    if "查看" in cmd and "日志" in cmd:
        level = None
        if "错误" in cmd:
            level = "ERROR"
        return view_logs(level=level)
    
    if "搜索" in cmd and "日志" in cmd:
        # 提取关键词
        if '"' in command or "'" in command:
            quote = '"' if '"' in command else "'"
            parts = command.split(quote)
            if len(parts) > 1:
                keyword = parts[1]
            else:
                keyword = "error"
        else:
            keyword = "error"
        return search_logs(keyword)
    
    if "分析" in cmd and ("错误" in cmd or "异常" in cmd):
        return analyze_error("")
    
    return """
📋 dev-logs Skill

**可用命令：**
- 查看最近日志
- 查看错误日志
- 搜索包含"[关键词]"的日志
- 分析这个错误

**示例：**
- 查看最近日志
- 查看错误日志
- 搜索包含"timeout"的日志
- 分析这个错误
"""


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
    else:
        command = input("输入命令：")
    
    print(execute(command))
