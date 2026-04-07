"""
dev-test Skill 执行器

测试生成、运行、分析
"""

import sys
import subprocess
from pathlib import Path
from typing import Dict, Any


def generate_test(func_name: str, func_code: str = "") -> str:
    """生成单元测试"""
    return f"""
🧪 生成单元测试

**函数：** {func_name}

**测试模板：**
```python
import pytest

def test_{func_name}_normal():
    '''测试正常情况'''
    # TODO: 实现测试
    pass

def test_{func_name}_edge_case():
    '''测试边界情况'''
    # TODO: 实现测试
    pass

def test_{func_name}_exception():
    '''测试异常情况'''
    # TODO: 实现测试
    with pytest.raises(Exception):
        pass
```

**下一步：**
1. 实现测试逻辑
2. 运行测试：pytest tests/test_{func_name}.py -v
"""


def run_tests(test_file: str = None) -> str:
    """运行测试"""
    if test_file is None:
        # 运行所有测试
        cmd = ["pytest", "-v", "--tb=short"]
    else:
        cmd = ["pytest", test_file, "-v", "--tb=short"]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        output = result.stdout + result.stderr
        
        # 解析结果
        if "passed" in output:
            return f"""
🧪 测试通过

**命令：** {' '.join(cmd)}

**输出：**
{output[:500]}

✅ 所有测试通过
"""
        else:
            return f"""
🧪 测试失败

**命令：** {' '.join(cmd)}

**输出：**
{output[:500]}

❌ 有测试失败，请查看错误信息
"""
    except subprocess.TimeoutExpired:
        return "❌ 测试超时（>60 秒）"
    except Exception as e:
        return f"❌ 运行失败：{str(e)}"


def analyze_failure(error_output: str) -> str:
    """分析测试失败原因"""
    return f"""
🧪 测试失败分析

**错误信息：**
{error_output[:300]}

**可能原因：**
1. 断言条件不满足
2. 返回值不符合预期
3. 异常未正确抛出

**修复建议：**
1. 检查输入数据
2. 检查函数逻辑
3. 检查断言条件
"""


def execute(command: str) -> str:
    """执行命令"""
    cmd = command.lower()
    
    if "生成" in cmd and "测试" in cmd:
        # 提取函数名
        func_name = "unknown"
        if "函数" in cmd:
            parts = cmd.split("函数")
            if len(parts) > 1:
                func_name = parts[1].strip()
        return generate_test(func_name)
    
    if "运行测试" in cmd:
        return run_tests()
    
    if "分析" in cmd and "失败" in cmd:
        return analyze_failure("")
    
    return """
🧪 dev-test Skill

**可用命令：**
- 为这个函数生成单元测试
- 运行测试
- 测试为什么失败

**示例：**
- 为这个函数生成单元测试：calculate_sum
- 运行测试
- 测试为什么失败
"""


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
    else:
        command = input("输入命令：")
    
    print(execute(command))
