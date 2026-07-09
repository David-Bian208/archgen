"""Framework Matcher - 框架匹配模块"""

import json
import logging
import re
import time
from typing import Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class FrameworkMatcher:
    """框架匹配器，基于关键词+语义+规则的三层匹配策略"""

    # 10 个框架定义
    FRAMEWORKS = {
        # v2.0 新增
        "swot": {
            "name": "SWOT 分析",
            "categories": ["business", "personal", "project"],
            "layout_style": "2x2_matrix",
            "description": "分析优势、劣势、机会、威胁",
            "full_description": "SWOT 是一种经典的战略分析工具，将分析对象分为四个象限：内部优势（Strengths）— 组织拥有的核心竞争力和有利条件；内部劣势（Weaknesses）— 组织的短板和不足；外部机会（Opportunities）— 环境中有利于发展的因素；外部威胁（Threats）— 环境中可能造成风险的因素。通过交叉分析（SO 战略利用优势抓住机会、WO 战略克服劣势利用机会、ST 战略利用优势规避威胁、WT 战略减少劣势避开威胁）找出最佳行动方案。",
            "usage_guide": "适用于分析企业/个人/项目的内部优势劣势和外部机会威胁，帮助制定战略决策。常用于商业计划书、竞品分析、个人发展规划等场景。",
            "logic_description": "将分析对象分为四个象限：内部优势（S）、内部劣势（W）、外部机会（O）、外部威胁（T）。通过交叉分析（SO 战略、WO 战略、ST 战略、WT 战略）找出最佳行动方案。",
            "keywords": ["swot", "优势", "劣势", "机会", "威胁", "strength", "weakness",
                        "opportunity", "threat", "内部因素", "外部因素"],
            "prompt_template": """请从以下文本中提取 SWOT 分析数据：
{{
    "title": "分析标题",
    "strengths": ["优势1", "优势2"],
    "weaknesses": ["劣势1", "劣势2"],
    "opportunities": ["机会1", "机会2"],
    "threats": ["威胁1", "威胁2"],
    "summary": "总结"
}}
文本：{text}""",
            "field_keywords": {
                "strengths": ["优势", "强项", "strength", "长处", "核心竞争力", "擅长"],
                "weaknesses": ["劣势", "弱项", "weakness", "短板", "不足", "缺点"],
                "opportunities": ["机会", "机遇", "opportunity", "风口", "红利", "利好"],
                "threats": ["威胁", "风险", "threat", "挑战", "竞争", "隐患"],
                "summary": ["总结", "结论", "overall"],
            },
        },
        "business_canvas": {
            "name": "商业模式画布",
            "categories": ["business"],
            "layout_style": "9_grid",
            "description": "九宫格商业模式分析",
            "full_description": "商业模式画布（Business Model Canvas）是一种可视化商业建模工具，用一张画布从 9 个维度全面描述企业的商业模式：客户细分（Target Customers）- 企业服务的目标人群；价值主张（Value Proposition）- 为客户创造的核心价值；渠道通路（Channels）- 触达客户的方式；客户关系（Customer Relationships）- 与客户建立的关系类型；收入来源（Revenue Streams）- 企业如何赚钱；核心资源（Key Resources）- 实现商业模式必需的资源；关键业务（Key Activities）- 企业必须做的最重要的事情；重要合作（Key Partnerships）- 外部供应商和合作伙伴网络；成本结构（Cost Structure）- 商业模式运营产生的所有成本。帮助理清'为谁创造价值、如何创造价值、如何获取价值'的商业逻辑。",
            "usage_guide": "适用于全面分析企业的商业模式，从客户、价值、渠道、收入、成本等 9 个维度拆解。常用于创业计划、商业模式创新、企业战略转型等场景。",
            "logic_description": "以价值主张为核心，向两侧延伸：右侧关注客户（客户细分、渠道、客户关系、收入来源），左侧关注基础设施（核心资源、关键业务、合作伙伴、成本结构）。帮助理清'为谁创造价值、如何创造价值、如何获取价值'的商业逻辑。",
            "keywords": ["商业模式", "画布", "business model canvas", "价值主张", "客户细分",
                        "渠道", "客户关系", "收入来源", "核心资源", "关键业务", "合作伙伴",
                        "成本结构"],
            "prompt_template": """请从以下文本中提取商业模式画布数据：
{{
    "title": "分析标题",
    "customer_segments": ["客户细分"],
    "value_propositions": ["价值主张"],
    "channels": ["渠道"],
    "customer_relationships": ["客户关系"],
    "revenue_streams": ["收入来源"],
    "key_resources": ["核心资源"],
    "key_activities": ["关键业务"],
    "key_partnerships": ["合作伙伴"],
    "cost_structure": ["成本结构"]
}}
文本：{text}""",
            "field_keywords": {
                "customer_segments": ["客户", "用户", "受众", "目标人群", "segment", "受众群体"],
                "value_propositions": ["价值", "解决", "痛点", "好处", "优势", "核心能力"],
                "channels": ["渠道", "分发", "触达", "传播", "channel", "平台"],
                "customer_relationships": ["关系", "互动", "服务", "留存", "relationship", "维系"],
                "revenue_streams": ["收入", "盈利", "收费", "定价", "变现", "revenue", "收益"],
                "key_resources": ["资源", "资产", "团队", "技术", "resource", "核心"],
                "key_activities": ["活动", "运营", "生产", "开发", "activity", "业务"],
                "key_partnerships": ["合作", "伙伴", "联盟", "供应商", "partnership", "生态"],
                "cost_structure": ["成本", "费用", "投入", "开支", "cost", "支出"],
            },
        },
        "pestel": {
            "name": "PESTEL 分析",
            "categories": ["business", "risk"],
            "layout_style": "6_columns",
            "description": "从政治、经济、社会、技术、环境、法律六个维度分析宏观环境",
            "full_description": "PESTEL 是一种宏观环境分析框架，从六个维度系统评估外部环境对组织的影响：政治因素（政府政策、政治稳定性、贸易政策、税收政策）、经济因素（GDP 增长率、通胀率、利率、汇率、失业率）、社会因素（人口结构、文化价值观、教育水平、消费习惯）、技术因素（技术创新、研发投入、自动化程度、数字化转型）、环境因素（气候变化、资源枯竭、环保意识、碳排放）、法律因素（劳动法、反垄断法、数据保护法、行业监管）。该框架帮助企业识别外部机会和威胁，制定适应性战略。",
            "usage_guide": "适用于宏观环境分析，帮助企业识别外部环境中影响战略的六大因素。常用于市场调研、投资决策、行业分析、风险评估等场景。",
            "logic_description": "从六个维度分析宏观环境：政治（政策法规）、经济（市场趋势）、社会（人口文化）、技术（创新变革）、环境（可持续发展）、法律（合规要求）。帮助企业识别外部机会和威胁。",
            "keywords": ["pestel", "pest", "政治", "经济", "社会", "技术", "环境", "法律",
                        "political", "economic", "social", "technological", "environmental", "legal"],
            "prompt_template": """请从以下文本中提取 PESTEL 分析数据：
{{
    "title": "分析标题",
    "political": ["政治因素"],
    "economic": ["经济因素"],
    "social": ["社会因素"],
    "technological": ["技术因素"],
    "environmental": ["环境因素"],
    "legal": ["法律因素"],
    "summary": "总结"
}}
文本：{text}""",
            "field_keywords": {
                "political": ["政治", "政策", "government", "regulation", "监管"],
                "economic": ["经济", "市场", "financial", "trade", "通胀", "利率"],
                "social": ["社会", "文化", "人口", "social", "demographic", "趋势"],
                "technological": ["技术", "科技", "innovation", "digital", "自动化"],
                "environmental": ["环境", "生态", "carbon", "sustainable", "气候", "绿色"],
                "legal": ["法律", "法规", "legal", "compliance", "合规", "立法"],
                "summary": ["总结", "结论", "overall"],
            },
        },
        "user_journey": {
            "name": "用户旅程地图",
            "categories": ["product", "operations"],
            "layout_style": "timeline",
            "description": "用户体验流程分析",
            "full_description": "用户旅程地图（User Journey Map）是一种可视化工具，按照时间顺序追踪用户与产品或服务互动的全过程。典型阶段包括：认知阶段（发现产品）→ 考虑阶段（评估选项）→ 购买阶段（决策购买）→ 使用阶段（实际体验）→ 留存阶段（持续使用）→ 推荐阶段（主动分享）。每个阶段记录用户的触点（接触点）、痛点（遇到的问题）和情绪变化（满意度曲线），帮助产品团队找到体验优化的关键节点，提升整体用户满意度。",
            "usage_guide": "适用于分析用户从接触到使用产品的全流程体验，识别痛点和机会。常用于产品设计、服务优化、客户体验管理等场景。",
            "logic_description": "按照时间顺序追踪用户行为：认知→考虑→购买→使用→留存→推荐。每个阶段记录用户的触点、痛点和情绪变化，帮助找到体验优化的关键节点。",
            "keywords": ["用户旅程", "user journey", "体验", "触点", "痛点", "情绪曲线",
                        "阶段", "awareness", "consideration", "purchase", "retention"],
            "prompt_template": """请从以下文本中提取用户旅程数据：
{{
    "title": "分析标题",
    "persona": "用户角色",
    "stages": [
        {{"order": 1, "name": "阶段名", "description": "描述", "touchpoints": ["触点"], "pain_points": ["痛点"], "emotion": 3}}
    ],
    "summary": "总结"
}}
文本：{text}""",
            "field_keywords": {
                "persona": ["用户", "角色", "persona", "画像", "受众"],
                "stages": ["阶段", "步骤", "流程", "旅程", "stage", "环节"],
                "summary": ["总结", "结论", "overall"],
            },
        },
        "time_matrix": {
            "name": "时间管理矩阵",
            "categories": ["personal", "project"],
            "layout_style": "2x2_matrix",
            "description": "重要紧急四象限",
            "full_description": "时间管理矩阵（艾森豪威尔矩阵）按照重要性和紧急性两个维度，将任务分为四个象限：第一象限— 重要且紧急（危机、紧迫问题，必须立即处理）；第二象限— 重要但不紧急（规划、预防、关系建立，应该投入最多时间）；第三象限— 不重要但紧急（干扰、琐事，应该尽量减少或委托他人）；第四象限— 不重要且不紧急（消遣、浪费时间的活动，应该避免）。核心原则是：减少第三、四象限的时间投入，增加第二象限的投入，通过提前规划来减少第一象限的危机。",
            "usage_guide": "适用于任务优先级管理，帮助区分重要/紧急程度，合理分配时间和精力。常用于个人效率提升、项目管理、团队任务分配等场景。",
            "logic_description": "按照重要性和紧急性两个维度，将任务分为四象限：Q1 重要紧急（立即做）、Q2 重要不紧急（计划做）、Q3 不重要紧急（委托做）、Q4 不重要不紧急（减少做）。核心原则是减少 Q3/Q4，增加 Q2 投入。",
            "keywords": ["时间管理", "重要", "紧急", "四象限", "time matrix", "eisenhower",
                        "优先级", "第一象限", "第二象限", "第三象限", "第四象限"],
            "prompt_template": """请从以下文本中提取时间管理矩阵数据：
{{
    "title": "分析标题",
    "q1_important_urgent": [{"name": "任务", "description": "描述"}],
    "q2_important_not_urgent": [{"name": "任务", "description": "description"}],
    "q3_not_important_urgent": [{"name": "任务", "description": "描述"}],
    "q4_not_important_not_urgent": [{"name": "任务", "description": "描述"}],
    "summary": "总结"
}}
文本：{text}""",
            "field_keywords": {
                "q1_important_urgent": ["重要", "紧急", "关键", "优先"],
                "q2_important_not_urgent": ["重要", "规划", "长期", "战略"],
                "q3_not_important_urgent": ["紧急", "干扰", "临时", "琐事"],
                "q4_not_important_not_urgent": ["浪费", "娱乐", "消遣", "无关"],
                "summary": ["总结", "结论", "overall"],
            },
        },
        # v1.0 复用
        "claim": {
            "name": "主张型分析",
            "categories": ["business", "personal"],
            "layout_style": "center_radial",
            "description": "核心观点 + 分论点支撑",
            "full_description": "主张型分析是一种论证结构框架，以核心主张（Thesis）为中心，向外辐射多个分论点（Supporting Points）。每个分论点提供具体的证据和论证来支撑核心主张，最终汇聚到结论。这种'总-分-总'的逻辑结构非常适合演讲、论文、观点文章的结构化呈现，帮助读者/听众清晰理解作者的立场和论证过程。",
            "usage_guide": "适用于表达核心观点并用多个分论点支撑，适合演讲、论文、观点文章的结构化呈现。常用于观点表达、学术论证、决策建议等场景。",
            "logic_description": "以核心主张为中心，向外辐射多个分论点。每个分论点提供具体证据和论证，最终汇聚到结论。适合'总-分-总'的逻辑结构。",
            "keywords": ["观点", "主张", "论点", "核心", "argue", "claim", "thesis"],
            "prompt_template": """请从以下文本中提取主张型结构数据：
{{
    "title": "标题",
    "central_claim": "核心主张",
    "supporting_points": [{{"label": "分论点", "text": "内容", "weight": 0.8}}],
    "evidence": ["证据"],
    "conclusion": "结论"
}}
文本：{text}""",
            "field_keywords": {
                "central_claim": ["核心", "主张", "观点", "thesis", "立场"],
                "supporting_points": ["论点", "理由", "依据", "支撑", "support", "分"],
                "evidence": ["证据", "数据", "事实", "案例", "evidence"],
                "conclusion": ["结论", "总结", "conclusion", "最终"],
            },
        },
        "causal": {
            "name": "因果分析",
            "categories": ["business", "risk", "project"],
            "layout_style": "flow_chart",
            "description": "A→B→C 因果链条",
            "full_description": "因果分析是一种追溯事件之间因果关系的分析框架。从观察到的现象出发，逐层向前追溯原因链条（因为 A 所以 B，因为 B 所以 C），直到找到根本原因（Root Cause）。同时分析每个原因导致的连锁效应和最终结果。这种分析帮助理解'为什么会发生'以及'会导致什么'，常用于问题诊断、风险评估、事故分析、策略推演等场景。",
            "usage_guide": "适用于分析事件之间的因果关系，追溯根本原因或预测连锁反应。常用于问题诊断、风险评估、事故分析、策略推演等场景。",
            "logic_description": "从现象出发，逐层追溯原因链条，直到找到根本原因（Root Cause）。同时分析每个原因导致的连锁效应，帮助理解'为什么会发生'以及'会导致什么'。",
            "keywords": ["因果", "因为", "所以", "导致", "原因", "结果", "cause", "effect"],
            "prompt_template": """请从以下文本中提取因果分析数据：
{{
    "title": "标题",
    "chain": [{{"step": 1, "cause": "原因", "effect": "结果"}}],
    "root_cause": "根本原因",
    "final_effect": "最终结果"
}}
文本：{text}""",
            "field_keywords": {
                "chain": ["导致", "引起", "因此", "从而", "导致", "cause", "effect"],
                "root_cause": ["根本", "根源", "起源", "root", "源头", "本质"],
                "final_effect": ["结果", "影响", "最终", "outcome", "后果"],
            },
        },
        "system": {
            "name": "系统架构分析",
            "categories": ["product", "project"],
            "layout_style": "layered_arch",
            "description": "多模块相互作用架构",
            "full_description": "系统架构分析是一种将复杂系统按层级分解的分析框架。从顶层概述（系统的整体目标和定位）开始，向下逐层分解为中层模块（系统的核心组成部分）和底层组件（模块的具体实现单元）。每个模块说明其职责和与其他模块的连接关系，帮助理解'系统如何工作'以及'各部分如何协作'。适合技术架构、产品架构、组织架构的可视化呈现。",
            "usage_guide": "适用于分析复杂系统的组成结构和模块间关系，适合技术架构、产品架构、组织架构的可视化呈现。常用于系统设计、技术评审、架构文档等场景。",
            "logic_description": "将系统按层级分解：顶层概述→中层模块→底层组件。每个模块说明其职责和与其他模块的连接关系，帮助理解'系统如何工作'以及'各部分如何协作'。",
            "keywords": ["架构", "系统", "模块", "组件", "交互", "architecture", "system", "module"],
            "prompt_template": """请从以下文本中提取系统架构数据：
{{
    "title": "标题",
    "overview": "系统概述",
    "modules": [{{"name": "模块名", "role": "职责", "connections": ["连接"]}}]
}}
文本：{text}""",
            "field_keywords": {
                "overview": ["概述", "介绍", "整体", "overview", "总览"],
                "modules": ["模块", "组件", "部分", "模块", "module", "component", "层"],
            },
        },
        "comparison": {
            "name": "对比分析",
            "categories": ["business", "product", "finance"],
            "layout_style": "comparison_table",
            "description": "多维度对比评估",
            "full_description": "对比分析是一种对多个对象进行多维度评估的分析框架。选取多个对比维度（如功能、性能、价格、用户体验、市场份额等），对各个对比对象在每个维度上进行评估打分。通过横向对比（同一维度下不同对象的差异）找出优劣势，通过纵向对比（同一对象在不同维度上的表现）评估整体水平。常用于竞品分析、方案选择、产品对比、技术选型等场景，帮助决策者全面了解各选项的优劣。",
            "usage_guide": "适用于对多个对象进行多维度对比，找出各自的优劣势和差异。常用于竞品分析、方案选择、产品对比、技术选型等场景。",
            "logic_description": "选取多个对比维度（如功能、性能、价格、用户体验等），对各个对比对象在每个维度上进行评估打分。通过横向对比找出差异，通过纵向对比评估优劣。",
            "keywords": ["对比", "比较", "差异", "vs", "优劣", "comparison", "versus"],
            "prompt_template": """请从以下文本中提取对比分析数据：
{{
    "title": "标题",
    "dimensions": ["维度"],
    "items": [{{"name": "对比项", "scores": ["各维度评价"]}}]
}}
文本：{text}""",
            "field_keywords": {
                "dimensions": ["维度", "指标", "方面", "维度", "dimension", "标准"],
                "items": ["对比", "比较", "vs", "优劣", "comparison", "差异"],
            },
        },
        "process": {
            "name": "流程分析",
            "categories": ["operations", "project"],
            "layout_style": "timeline",
            "description": "步骤 1→2→3→4 流程",
            "full_description": "流程分析是一种按照时间或逻辑顺序分解步骤的分析框架。将完整的业务流程或操作流程分解为若干有序步骤，每个步骤包含标题、描述和注意事项。帮助理解'先做什么、后做什么、每个步骤的要点是什么'，找出流程中的瓶颈、冗余环节和优化空间。常用于流程优化、SOP 制定、操作手册编写、项目管理等场景。",
            "usage_guide": "适用于分析业务或操作的步骤流程，帮助理清执行顺序和关键节点。常用于流程优化、SOP 制定、操作手册、项目管理等场景。",
            "logic_description": "按照时间或逻辑顺序，将流程分解为若干步骤。每个步骤包含标题、描述和注意事项，帮助理解'先做什么、后做什么、每个步骤的要点是什么'。",
            "keywords": ["流程", "步骤", "过程", "第一步", "第二步", "process", "step"],
            "prompt_template": """请从以下文本中提取流程分析数据：
{{
    "title": "标题",
    "steps": [{{"order": 1, "title": "步骤标题", "description": "描述", "tips": ["提示"]}}]
}}
文本：{text}""",
            "field_keywords": {
                "steps": ["步骤", "流程", "过程", "第一步", "step", "阶段", "环节"],
            },
        },
    }

    # 匹配权重
    KEYWORD_WEIGHT = 0.4
    SEMANTIC_WEIGHT = 0.5
    RULE_WEIGHT = 0.1

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.api_key = self.config.get("api_key", "")
        self.base_url = self.config.get("base_url", "https://api.deepseek.com/v1")
        self.model = self.config.get("model", "deepseek-v4-flash")
        self.max_tokens = self.config.get("max_tokens", 1024)
        self.temperature = self.config.get("temperature", 0.1)
        self.timeout = self.config.get("timeout", 30)
        self.retry_times = self.config.get("retry_times", 3)
        self.retry_delay = self.config.get("retry_delay", 2)

    def match_frameworks(
        self,
        text: str,
        category: Optional[str] = None,
        top_n: int = 5,
    ) -> List[Dict]:
        """
        匹配框架，返回 Top N

        Args:
            text: 输入文本
            category: 业务领域（可选，用于过滤）
            top_n: 返回数量

        Returns:
            [
                {"key": "swot", "name": "SWOT 分析", "score": 0.85, "reason": "..."},
                ...
            ]
        """
        logger.info(f"开始框架匹配，分类: {category}, Top: {top_n}")

        # 1. 关键词匹配 (40%)
        keyword_scores = self._keyword_match(text)

        # 2. 语义匹配 (50%)
        semantic_scores = self._semantic_match(text)

        # 3. 规则匹配 (10%)
        rule_scores = self._rule_match(text, category)

        # 4. 综合评分
        combined_scores = {}
        for key in self.FRAMEWORKS:
            k_score = keyword_scores.get(key, 0)
            s_score = semantic_scores.get(key, 0)
            r_score = rule_scores.get(key, 0)
            combined_scores[key] = (
                k_score * self.KEYWORD_WEIGHT
                + s_score * self.SEMANTIC_WEIGHT
                + r_score * self.RULE_WEIGHT
            )

        # 5. 按分类过滤
        if category:
            combined_scores = {
                k: v for k, v in combined_scores.items()
                if category in self.FRAMEWORKS[k]["categories"]
            }

        # 6. 排序并返回 Top N
        sorted_scores = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
        top_frameworks = []
        for key, score in sorted_scores[:top_n]:
            fw = self.FRAMEWORKS[key]
            top_frameworks.append({
                "key": key,
                "name": fw["name"],
                "layout_style": fw["layout_style"],
                "description": fw["description"],
                "categories": fw["categories"],
                "score": round(score, 3),
            })

        logger.info(f"框架匹配完成，返回 {len(top_frameworks)} 个结果")
        return top_frameworks

    def get_framework(self, key: str) -> Optional[Dict]:
        """获取单个框架详情"""
        fw = self.FRAMEWORKS.get(key)
        if fw:
            return {"key": key, **fw}
        return None

    def get_all_frameworks(self) -> Dict:
        """获取所有框架定义"""
        return self.FRAMEWORKS

    def _keyword_match(self, text: str) -> Dict[str, float]:
        """关键词匹配"""
        lower_text = text.lower()
        scores = {}

        for key, fw in self.FRAMEWORKS.items():
            matched = [kw for kw in fw["keywords"] if kw.lower() in lower_text]
            total_keywords = len(fw["keywords"])
            score = len(matched) / max(total_keywords, 1)
            scores[key] = min(score * 2, 1.0)  # 归一化到 0-1

        return scores

    def _semantic_match(self, text: str) -> Dict[str, float]:
        """语义匹配（使用 LLM）"""
        prompt = f"""请分析以下文本最适合使用哪些分析框架。

可用框架列表：
{self._get_frameworks_list()}

请输出 JSON 格式：
{{
    "frameworks": [
        {{"key": "框架 key", "score": 0.0-1.0, "reason": "匹配理由"}}
    ]
}}

只输出 JSON，不要输出其他内容。

文本：
{text[:2000]}
"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"].strip()

            result = json.loads(content)
            scores = {}
            for fw in result.get("frameworks", []):
                if fw["key"] in self.FRAMEWORKS:
                    scores[fw["key"]] = float(fw["score"])
            return scores

        except Exception as e:
            logger.warning(f"语义匹配失败: {e}")
            return {key: 0.5 for key in self.FRAMEWORKS}  # 默认中等分数

    def _rule_match(self, text: str, category: Optional[str] = None) -> Dict[str, float]:
        """规则匹配（基于业务领域）"""
        scores = {key: 0.5 for key in self.FRAMEWORKS}  # 默认基础分

        # 如果指定了分类，相关框架加分
        if category:
            for key, fw in self.FRAMEWORKS.items():
                if category in fw["categories"]:
                    scores[key] = 0.8
                else:
                    scores[key] = 0.3

        # 文本长度规则：长文本更适合复杂框架
        text_len = len(text)
        if text_len > 2000:
            scores["business_canvas"] = min(scores.get("business_canvas", 0.5) + 0.1, 1.0)
            scores["pestel"] = min(scores.get("pestel", 0.5) + 0.1, 1.0)
        elif text_len < 500:
            scores["time_matrix"] = min(scores.get("time_matrix", 0.5) + 0.1, 1.0)
            scores["swot"] = min(scores.get("swot", 0.5) + 0.1, 1.0)

        return scores

    def _get_frameworks_list(self) -> str:
        """获取框架列表文本"""
        lines = []
        for key, fw in self.FRAMEWORKS.items():
            lines.append(f"- {key}: {fw['name']} - {fw['description']}")
        return "\n".join(lines)

    def preflight_check(self, text: str, framework_key: str) -> Dict:
        """
        轻量预检：基于关键词匹配评估每个字段的数据可获取性

        Args:
            text: 原文内容（MCP 总结或用户输入）
            framework_key: 框架 key

        Returns:
            {
                "framework_key": "swot",
                "framework_name": "SWOT 分析",
                "total_fields": 5,
                "anchored_count": 3,
                "inferred_count": 1,
                "missing_count": 1,
                "fill_rate": 0.6,
                "fields": {
                    "strengths": {"status": "anchored", "hits": 5},
                    "weaknesses": {"status": "anchored", "hits": 3},
                    "opportunities": {"status": "inferred", "hits": 1},
                    "threats": {"status": "missing", "hits": 0},
                    "summary": {"status": "anchored", "hits": 2}
                }
            }
        """
        fw = self.FRAMEWORKS.get(framework_key)
        if not fw:
            return {"error": f"框架不存在: {framework_key}"}

        field_keywords = fw.get("field_keywords", {})
        if not field_keywords:
            return {
                "framework_key": framework_key,
                "framework_name": fw["name"],
                "total_fields": 0,
                "anchored_count": 0,
                "inferred_count": 0,
                "missing_count": 0,
                "fill_rate": 0,
                "fields": {},
            }

        lower_text = text.lower()
        fields_status = {}
        anchored_count = 0
        inferred_count = 0
        missing_count = 0

        for field_name, kws in field_keywords.items():
            hits = sum(1 for kw in kws if kw.lower() in lower_text)
            if hits >= 3:
                status = "anchored"
                anchored_count += 1
            elif hits >= 1:
                status = "inferred"
                inferred_count += 1
            else:
                status = "missing"
                missing_count += 1

            fields_status[field_name] = {
                "status": status,
                "hits": hits,
            }

        total = len(field_keywords)
        fill_rate = round((anchored_count + inferred_count * 0.5) / max(total, 1), 2)

        return {
            "framework_key": framework_key,
            "framework_name": fw["name"],
            "total_fields": total,
            "anchored_count": anchored_count,
            "inferred_count": inferred_count,
            "missing_count": missing_count,
            "fill_rate": fill_rate,
            "fields": fields_status,
        }

    def autopopulate(self, text: str, framework_key: str) -> Dict:
        """
        使用 LLM 从原文中自动萃取数据，填充框架字段

        Args:
            text: 原文内容（MCP 总结或用户输入）
            framework_key: 框架 key

        Returns:
            {
                "framework_key": "swot",
                "framework_name": "SWOT 分析",
                "fields": {
                    "strengths": {
                        "value": ["优势1", "优势2"],
                        "status": "anchored",
                        "source": "原文锚点"
                    },
                    "weaknesses": {
                        "value": ["推测为XX"],
                        "status": "inferred",
                        "suggestion": "建议参考同类竞品"
                    },
                    "threats": {
                        "value": [],
                        "status": "missing",
                        "suggestion": "建议填写：XXX"
                    }
                },
                "fill_rate": 0.6
            }
        """
        fw = self.FRAMEWORKS.get(framework_key)
        if not fw:
            return {"error": f"框架不存在: {framework_key}"}

        prompt = fw.get("prompt_template", "").replace("{text}", text[:5000])

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2048,
            "temperature": 0.2,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"].strip()

            extracted = self._parse_json_response(content)
            if not extracted:
                extracted = {}

            # 给每个字段加上 status 标签
            field_keywords = fw.get("field_keywords", {})
            lower_text = text.lower()
            fields_result = {}
            anchored_count = 0
            inferred_count = 0
            missing_count = 0

            for field_name, kws in field_keywords.items():
                value = extracted.get(field_name, [])
                hits = sum(1 for kw in kws if kw.lower() in lower_text)

                if hits >= 3:
                    status = "anchored"
                    anchored_count += 1
                elif hits >= 1:
                    status = "inferred"
                    inferred_count += 1
                else:
                    status = "missing"
                    missing_count += 1

                suggestion = ""
                if status == "missing":
                    suggestion = f"原文未提及{field_name}相关信息，建议补充"
                elif status == "inferred":
                    suggestion = "基于上下文推测，请确认"

                fields_result[field_name] = {
                    "value": value if isinstance(value, list) else [str(value)] if value else [],
                    "status": status,
                    "suggestion": suggestion,
                }

            total = len(field_keywords)
            fill_rate = round((anchored_count + inferred_count * 0.5) / max(total, 1), 2)

            return {
                "framework_key": framework_key,
                "framework_name": fw["name"],
                "fields": fields_result,
                "fill_rate": fill_rate,
                "anchored_count": anchored_count,
                "inferred_count": inferred_count,
                "missing_count": missing_count,
            }

        except Exception as e:
            logger.error(f"autopopulate 失败: {e}")
            return {
                "framework_key": framework_key,
                "framework_name": fw.get("name", framework_key),
                "error": str(e),
                "fields": {},
                "fill_rate": 0,
            }

    def _parse_json_response(self, content: str) -> Optional[Dict]:
        """解析 LLM 返回的 JSON（增强容错）"""
        content = content.replace("'", '"').replace('`', '')

        try:
            result = json.loads(content)
            return result
        except json.JSONDecodeError:
            pass

        json_match = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        brace_match = re.search(r"\{.*\}", content, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        return {}
