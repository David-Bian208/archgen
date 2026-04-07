"""
dev-context Skill 执行器

项目结构、模块依赖、API 查询
"""

import os
from pathlib import Path
from typing import Dict, List


def get_project_structure(root_path: Path = None, max_depth: int = 3) -> str:
    """获取项目结构"""
    if root_path is None:
        root_path = Path(__file__).parent.parent.parent.parent
    
    lines = ["📁 项目结构\n"]
    lines.append(f"**根目录：** {root_path}\n")
    lines.append("**目录结构：**\n```\n")
    
    def scan_dir(path: Path, prefix: str = "", depth: int = 0):
        if depth > max_depth:
            return
        
        try:
            items = sorted(path.iterdir())
        except PermissionError:
            return
        
        for i, item in enumerate(items):
            if item.name.startswith('.') or item.name.startswith('__'):
                continue
            
            is_last = (i == len(items) - 1)
            connector = "└── " if is_last else "├── "
            
            if item.is_dir():
                lines.append(f"{prefix}{connector}{item.name}/")
                scan_dir(item, prefix + ("    " if is_last else "│   "), depth + 1)
            else:
                lines.append(f"{prefix}{connector}{item.name}")
    
    scan_dir(root_path)
    lines.append("```")
    
    return "\n".join(lines)


def find_module(module_name: str, root_path: Path = None) -> str:
    """查找模块位置"""
    if root_path is None:
        root_path = Path(__file__).parent.parent.parent.parent
    
    results = []
    
    for py_file in root_path.rglob("*.py"):
        if module_name in py_file.name or module_name in str(py_file):
            results.append(str(py_file.relative_to(root_path)))
    
    if not results:
        return f"❌ 未找到模块：{module_name}"
    
    lines = [f"📦 模块查找：{module_name}\n"]
    lines.append("**找到以下文件：**\n")
    for result in results[:10]:
        lines.append(f"- {result}")
    
    return "\n".join(lines)


def analyze_imports(file_path: Path) -> str:
    """分析文件导入"""
    if not file_path.exists():
        return f"❌ 文件不存在：{file_path}"
    
    content = file_path.read_text(encoding='utf-8')
    imports = []
    
    for line in content.split('\n'):
        if line.strip().startswith('import ') or line.strip().startswith('from '):
            imports.append(line.strip())
    
    lines = [f"📦 模块依赖分析\n"]
    lines.append(f"**文件：** {file_path}\n")
    lines.append(f"**导入数量：** {len(imports)}\n\n")
    lines.append("**导入列表：**\n```\n")
    lines.extend(imports[:20])
    lines.append("```")
    
    return "\n".join(lines)


def execute(command: str) -> str:
    """执行命令"""
    cmd = command.lower()
    
    if "项目结构" in cmd or "目录结构" in cmd:
        return get_project_structure()
    
    if "查找" in cmd or "在哪里" in cmd:
        # 提取模块名
        parts = cmd.split("查找")
        if len(parts) > 1:
            module_name = parts[1].strip()
        else:
            module_name = "module"
        return find_module(module_name)
    
    if "依赖" in cmd:
        # 分析当前文件导入
        return analyze_imports(Path(__file__))
    
    return """
📦 dev-context Skill

**可用命令：**
- 查看项目结构
- 查找模块：[模块名]
- 分析这个文件的依赖

**示例：**
- 查看项目结构
- 查找 module：clinical_rules
- 分析这个文件的依赖
"""


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
    else:
        command = input("输入命令：")
    
    print(execute(command))
