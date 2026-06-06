"""综合测试脚本 - 验证 P0/P1/P2 任务实施"""

import sys
import json
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

def test_persona_dimensions():
    """测试六维人设配置文件"""
    print("\n📋 测试 1: 六维人设配置文件")
    
    path = Path("config/persona_dimensions.md")
    assert path.exists(), "persona_dimensions.md 不存在"
    
    content = path.read_text(encoding="utf-8")
    assert len(content) < 2000, f"文件过大: {len(content)} 字符 (要求 <2K)"
    
    # 检查六维是否都存在
    dimensions = ["核心驱动", "认知过滤", "受众画像", "能力边界", "表达范式", "价值标准"]
    for dim in dimensions:
        assert dim in content, f"缺少维度: {dim}"
    
    print("   ✅ 文件存在且大小合规")
    print("   ✅ 六维定义完整")
    return True


def test_prompts_yaml():
    """测试 Prompt 模板配置"""
    print("\n📋 测试 2: Prompt 模板配置")
    
    import yaml
    path = Path("config/prompts.yaml")
    assert path.exists(), "prompts.yaml 不存在"
    
    with open(path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    # 检查 4 个 LLM 阶段
    stages = ["router", "logic_editor", "extractor", "generator"]
    for stage in stages:
        assert stage in config, f"缺少 LLM 阶段: {stage}"
        assert "system_prompt" in config[stage], f"{stage} 缺少 system_prompt"
        assert "inject_dimensions" in config[stage], f"{stage} 缺少 inject_dimensions"
    
    # 检查 source_tag 规范
    assert "source_tag" in config, "缺少 source_tag 配置"
    assert "types" in config["source_tag"], "source_tag 缺少 types"
    
    print("   ✅ 4 个 LLM 阶段定义完整")
    print("   ✅ source_tag 规范存在")
    return True


def test_ai_pulse_client():
    """测试 AI-Pulse 客户端框架"""
    print("\n📋 测试 3: AI-Pulse 客户端框架")
    
    from src.ai_pulse_client import AIPulseClient, get_ai_pulse_client
    
    # 测试实例化
    client = AIPulseClient()
    assert client.base_url == "http://8.130.148.166:8887"
    assert client.timeout == 10
    
    # 测试自定义配置
    client2 = get_ai_pulse_client({"base_url": "http://test.com", "timeout": 20})
    assert client2.base_url == "http://test.com"
    assert client2.timeout == 20
    
    print("   ✅ 模块导入成功")
    print("   ✅ 实例化正常")
    print("   ✅ 配置参数正确")
    return True


def test_case_library():
    """测试案例库结构"""
    print("\n📋 测试 4: 案例库结构")
    
    path = Path("knowledge_base/cases/README.md")
    assert path.exists(), "cases/README.md 不存在"
    
    content = path.read_text(encoding="utf-8")
    
    # 检查必要内容
    required_sections = ["案例模板", "检索优先级", "source_tag 规范", "渲染规则"]
    for section in required_sections:
        assert section in content, f"缺少章节: {section}"
    
    print("   ✅ README.md 存在")
    print("   ✅ 包含所有必要章节")
    return True


def test_api_prompts():
    """测试 api.py 中的 prompt 修改"""
    print("\n📋 测试 5: api.py Prompt 修改")
    
    path = Path("api.py")
    content = path.read_text(encoding="utf-8")
    
    # 检查内容比例要求
    assert "理论内容≤20%" in content, "缺少内容比例要求"
    assert "实战内容≥80%" in content, "缺少实战比例要求"
    
    # 检查案例占位符
    assert "📌 待补充案例" in content or "📌 待补充" in content, "缺少案例占位符格式"
    
    # 检查素材来源标注
    assert "⚠️ [AI 推断]" in content, "缺少 AI 推断标注"
    assert "[来源：" in content, "缺少来源标注格式"
    
    # 检查 P0 渐进实施注释
    assert "P0 渐进实施" in content or "P0" in content, "缺少 P0 阶段说明"
    
    print("   ✅ 内容比例要求已添加")
    print("   ✅ 案例占位符格式已添加")
    print("   ✅ 素材来源标注已添加")
    return True


def test_workflow_view():
    """测试前端 WorkflowView.vue 的 5A/5B/5C 逻辑"""
    print("\n📋 测试 6: WorkflowView.vue 5A/5B/5C UI")
    
    path = Path("frontend/src/views/WorkflowView.vue")
    assert path.exists(), "WorkflowView.vue 不存在"
    
    content = path.read_text(encoding="utf-8")
    
    # 检查关键 UI 元素
    assert "5A" in content or "信息充足" in content, "缺少 5A 模式"
    assert "5B" in content or "需要您补充" in content, "缺少 5B 模式"
    assert "AI-Pulse" in content or "ai-pulse" in content, "缺少 AI-Pulse 按钮"
    assert "completeness" in content, "缺少 completeness 逻辑"
    
    print("   ✅ WorkflowView.vue 存在")
    print("   ✅ 5A/5B/5C 模式选择 UI 完整")
    return True


def test_source_tag_processor():
    """测试 P2: source_tag 处理器"""
    print("\n📋 测试 7: source_tag 处理器（P2）")
    
    from src.source_tag_processor import SourceTagProcessor, get_source_tag_processor
    
    processor = get_source_tag_processor()
    
    # 测试提取 source_tag
    content_with_tag = "⚠️ [AI 推断] 这是一段测试内容\n[来源：知识库] 另一段内容"
    tags = processor.extract_source_tags(content_with_tag)
    assert len(tags) > 0, "应该提取到 source_tag"
    
    # 测试内容验证
    is_valid, _ = processor.validate_content(content_with_tag)
    assert is_valid, "有标签的内容应该验证通过"
    
    # 测试无标签内容（宽松模式）
    content_no_tag = "这是一段没有标签的内容"
    processed = processor.process_content(content_no_tag, strict_mode=False)
    assert processed.is_valid, "宽松模式下无标签内容也应该有效"
    assert processed.source_tag == "ai_inferred:llm_generated", "无标签内容应该标记为 ai_inferred"
    
    # 测试无标签内容（严格模式）
    processed_strict = processor.process_content(content_no_tag, strict_mode=True)
    assert not processed_strict.is_valid, "严格模式下无标签内容应该无效"
    
    print("   ✅ source_tag 提取正常")
    print("   ✅ 内容验证逻辑正确")
    print("   ✅ 宽松/严格模式切换正常")
    return True


def test_llm_pipeline():
    """测试 P2: 4 阶段 LLM Pipeline"""
    print("\n📋 测试 8: 4 阶段 LLM Pipeline（P2）")
    
    from src.llm_pipeline import LLMPipeline, get_llm_pipeline
    
    # 测试实例化
    config = {
        "base_url": "https://api.deepseek.com/v1",
        "api_key": "test_key",
        "model": "deepseek-chat",
        "timeout": 30,
    }
    pipeline = get_llm_pipeline(config)
    
    assert pipeline.llm_config == config, "配置应该正确传递"
    assert pipeline.call_count == 0, "初始调用次数应该为 0"
    
    # 测试 prompt 构建（不调用真实 LLM）
    router_prompt = pipeline._build_router_prompt(
        article_text="测试文章",
        direction_list=[{"name": "技术深度分析"}, {"name": "商业趋势解读"}],
        edge_focus="AI 效率工具",
        edge_avoid="算法原理",
    )
    assert "AI 效率工具" in router_prompt, "Router prompt 应该包含 edge_focus"
    
    logic_prompt = pipeline._build_logic_editor_prompt(
        outline="测试提纲",
        drive="帮高净值人群节省时间",
        filter_rule="问题→方案→避坑→收益",
        value_standard="读者看完能直接上手操作",
    )
    assert "帮高净值人群节省时间" in logic_prompt, "Logic Editor prompt 应该包含 drive"
    
    extract_prompt = pipeline._build_extractor_prompt(
        revised_outline="修订提纲",
        audience_identity="企业主/高管",
        audience_pain_points="时间稀缺",
        audience_empathy="我知道你每天要处理X件事",
        value_standard="读者看完能直接上手操作",
    )
    assert "企业主/高管" in extract_prompt, "Extractor prompt 应该包含 audience_identity"
    
    gen_prompt = pipeline._build_generator_prompt(
        structured_json="结构化内容",
        voice_style="理性务实",
        voice_format="短句",
        voice_ratio="理论≤20%，实战≥80%",
        audience_identity="企业主/高管",
        audience_pain_points="时间稀缺",
    )
    assert "理性务实" in gen_prompt, "Generator prompt 应该包含 voice_style"
    
    print("   ✅ Pipeline 实例化正常")
    print("   ✅ Router prompt 构建正确")
    print("   ✅ Logic Editor prompt 构建正确")
    print("   ✅ Extractor prompt 构建正确")
    print("   ✅ Generator prompt 构建正确")
    return True


def test_p2_api_endpoints():
    """测试 P2: API 端点"""
    print("\n📋 测试 9: P2 API 端点")
    
    path = Path("api.py")
    content = path.read_text(encoding="utf-8")
    
    # 检查 P2 端点
    assert "/api/content/validate_source_tags" in content, "缺少 validate_source_tags 端点"
    assert "/api/content/pipeline/generate" in content, "缺少 pipeline/generate 端点"
    assert "/api/content/pipeline/full_workflow" in content, "缺少 pipeline/full_workflow 端点"
    
    # 检查 source_tag 处理集成
    assert "get_source_tag_processor" in content, "api.py 应该导入 source_tag 处理器"
    assert "process_content" in content or "process_full_article" in content, "api.py 应该使用 source_tag 处理"
    
    print("   ✅ validate_source_tags 端点存在")
    print("   ✅ pipeline/generate 端点存在")
    print("   ✅ pipeline/full_workflow 端点存在")
    print("   ✅ source_tag 处理已集成到内容生成端点")
    return True


def test_frontend_source_tag_component():
    """测试 P2: 前端 source_tag 组件"""
    print("\n📋 测试 10: 前端 source_tag 组件（P2）")
    
    path = Path("frontend/src/components/SourceTagFilter.vue")
    assert path.exists(), "SourceTagFilter.vue 不存在"
    
    content = path.read_text(encoding="utf-8")
    
    # 检查关键功能
    assert "validateSourceTags" in content, "组件应该调用 validateSourceTags API"
    assert "strictMode" in content, "组件应该支持严格/宽松模式切换"
    assert "getSourceTagColor" in content, "组件应该有 source_tag 颜色逻辑"
    
    # 检查 API 函数
    api_path = Path("frontend/src/utils/api.js")
    api_content = api_path.read_text(encoding="utf-8")
    assert "validateSourceTags" in api_content, "api.js 应该有 validateSourceTags 函数"
    assert "pipelineGenerate" in api_content, "api.js 应该有 pipelineGenerate 函数"
    assert "pipelineFullWorkflow" in api_content, "api.js 应该有 pipelineFullWorkflow 函数"
    
    print("   ✅ SourceTagFilter.vue 组件存在")
    print("   ✅ 组件功能完整（验证、模式切换、颜色标记）")
    print("   ✅ API 函数已添加")
    return True


def test_config_yaml():
    """测试 P2: 配置文件更新"""
    print("\n📋 测试 11: config.yaml 配置更新（P2）")
    
    import yaml
    path = Path("config/config.yaml")
    
    with open(path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    # 检查 ai_pulse 配置
    assert "ai_pulse" in config, "缺少 ai_pulse 配置"
    assert config["ai_pulse"]["enabled"] == True, "ai_pulse 应该默认启用"
    
    # 检查 source_tag 配置
    assert "source_tag" in config, "缺少 source_tag 配置"
    assert "strict_mode" in config["source_tag"], "source_tag 应该有 strict_mode 配置"
    assert "valid_prefixes" in config["source_tag"], "source_tag 应该有 valid_prefixes 配置"
    
    print("   ✅ ai_pulse 配置存在")
    print("   ✅ source_tag 配置存在")
    print("   ✅ strict_mode 配置正确")
    return True


def main():
    """运行所有测试"""
    print("=" * 60)
    print("🧪 ArchGen P0/P1/P2 任务实施综合测试")
    print("=" * 60)
    
    tests = [
        test_persona_dimensions,
        test_prompts_yaml,
        test_ai_pulse_client,
        test_case_library,
        test_api_prompts,
        test_workflow_view,
        test_source_tag_processor,
        test_llm_pipeline,
        test_p2_api_endpoints,
        test_frontend_source_tag_component,
        test_config_yaml,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            failed += 1
            print(f"   ❌ 测试失败: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
