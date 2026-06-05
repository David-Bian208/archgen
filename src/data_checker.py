"""Data Checker - 数据完整性检查模块"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class DataCompletenessChecker:
    """数据完整性检查器，基于规则检查框架数据是否完整"""

    # 每个框架的必填字段定义
    REQUIRED_FIELDS = {
        "swot": {
            "fields": ["title", "strengths", "weaknesses", "opportunities", "threats"],
            "field_names": {
                "title": "分析标题",
                "strengths": "优势列表",
                "weaknesses": "劣势列表",
                "opportunities": "机会列表",
                "threats": "威胁列表",
            },
            "follow_up_questions": {
                "strengths": "请补充你的核心优势有哪些？",
                "weaknesses": "你认为目前的主要劣势是什么？",
                "opportunities": "市场上有哪些可以把握的机会？",
                "threats": "面临的主要威胁或风险有哪些？",
            },
        },
        "business_canvas": {
            "fields": ["title", "customer_segments", "value_propositions", "revenue_streams"],
            "field_names": {
                "title": "分析标题",
                "customer_segments": "客户细分",
                "value_propositions": "价值主张",
                "channels": "渠道",
                "customer_relationships": "客户关系",
                "revenue_streams": "收入来源",
                "key_resources": "核心资源",
                "key_activities": "关键业务",
                "key_partnerships": "合作伙伴",
                "cost_structure": "成本结构",
            },
            "follow_up_questions": {
                "customer_segments": "你的目标客户群体是谁？",
                "value_propositions": "你为客户提供什么核心价值？",
                "revenue_streams": "你的主要收入来源是什么？",
            },
        },
        "pestel": {
            "fields": ["title", "political", "economic", "social", "technological", "environmental", "legal"],
            "field_names": {
                "title": "分析标题",
                "political": "政治因素",
                "economic": "经济因素",
                "social": "社会因素",
                "technological": "技术因素",
                "environmental": "环境因素",
                "legal": "法律因素",
            },
            "follow_up_questions": {
                "political": "有哪些政策或政治因素影响？",
                "economic": "经济环境如何？",
                "social": "社会文化趋势有哪些？",
            },
        },
        "user_journey": {
            "fields": ["title", "persona", "stages"],
            "field_names": {
                "title": "分析标题",
                "persona": "用户角色",
                "stages": "旅程阶段",
            },
            "follow_up_questions": {
                "persona": "你的目标用户是谁？",
                "stages": "用户的主要使用阶段有哪些？",
            },
        },
        "time_matrix": {
            "fields": ["title", "q1_important_urgent", "q2_important_not_urgent"],
            "field_names": {
                "title": "分析标题",
                "q1_important_urgent": "重要且紧急",
                "q2_important_not_urgent": "重要不紧急",
                "q3_not_important_urgent": "不重要但紧急",
                "q4_not_important_not_urgent": "不重要不紧急",
            },
            "follow_up_questions": {
                "q1_important_urgent": "有哪些重要且紧急的任务需要立即处理？",
                "q2_important_not_urgent": "有哪些重要但不紧急的任务可以规划？",
            },
        },
        "claim": {
            "fields": ["title", "central_claim", "supporting_points", "conclusion"],
            "field_names": {
                "title": "标题",
                "central_claim": "核心主张",
                "supporting_points": "分论点",
                "conclusion": "结论",
            },
            "follow_up_questions": {
                "central_claim": "你的核心观点是什么？",
                "supporting_points": "有哪些分论点支撑？",
            },
        },
        "causal": {
            "fields": ["title", "chain", "root_cause", "final_effect"],
            "field_names": {
                "title": "标题",
                "chain": "因果链条",
                "root_cause": "根本原因",
                "final_effect": "最终结果",
            },
            "follow_up_questions": {
                "root_cause": "根本原因是什么？",
                "chain": "因果链条是怎样的？",
            },
        },
        "system": {
            "fields": ["title", "overview", "modules"],
            "field_names": {
                "title": "标题",
                "overview": "系统概述",
                "modules": "模块列表",
            },
            "follow_up_questions": {
                "overview": "系统整体是怎样的？",
                "modules": "包含哪些核心模块？",
            },
        },
        "comparison": {
            "fields": ["title", "dimensions", "items"],
            "field_names": {
                "title": "标题",
                "dimensions": "对比维度",
                "items": "对比项",
            },
            "follow_up_questions": {
                "dimensions": "从哪些维度进行对比？",
                "items": "对比的对象有哪些？",
            },
        },
        "process": {
            "fields": ["title", "steps"],
            "field_names": {
                "title": "标题",
                "steps": "步骤列表",
            },
            "follow_up_questions": {
                "steps": "具体有哪些步骤？",
            },
        },
    }

    def check_completeness(self, data: Dict, framework_key: str) -> Dict:
        """
        检查数据完整性

        Args:
            data: 用户填写的数据
            framework_key: 框架 key

        Returns:
            {
                "complete": true/false,
                "completeness_score": 0.85,
                "missing_fields": ["字段1", "字段2"],
                "follow_up_questions": ["追问问题1", "追问问题2"],
                "field_status": {"字段": "complete/missing/partial"}
            }
        """
        logger.info(f"检查 {framework_key} 框架数据完整性...")

        schema = self.REQUIRED_FIELDS.get(framework_key)
        if not schema:
            logger.warning(f"未知框架: {framework_key}")
            return {"complete": True, "completeness_score": 1.0, "missing_fields": [], "follow_up_questions": []}

        required_fields = schema["fields"]
        field_names = schema["field_names"]
        follow_up = schema["follow_up_questions"]

        missing_fields = []
        field_status = {}
        follow_up_questions = []

        for field in required_fields:
            value = data.get(field)
            if value is None or value == "" or (isinstance(value, list) and len(value) == 0):
                missing_fields.append(field)
                field_status[field] = "missing"
                if field in follow_up:
                    follow_up_questions.append(follow_up[field])
            elif isinstance(value, list) and len(value) < 2:
                field_status[field] = "partial"
            else:
                field_status[field] = "complete"

        total_fields = len(required_fields)
        complete_fields = sum(1 for s in field_status.values() if s == "complete")
        partial_fields = sum(1 for s in field_status.values() if s == "partial")
        completeness_score = (complete_fields + partial_fields * 0.5) / max(total_fields, 1)

        result = {
            "complete": len(missing_fields) == 0,
            "completeness_score": round(completeness_score, 2),
            "missing_fields": missing_fields,
            "missing_field_names": [field_names.get(f, f) for f in missing_fields],
            "follow_up_questions": follow_up_questions,
            "field_status": field_status,
        }

        logger.info(
            f"数据完整性检查完成: 完整度 {result['completeness_score']}, "
            f"缺失 {len(missing_fields)} 个字段"
        )
        return result

    def get_field_names(self, framework_key: str) -> Dict[str, str]:
        """获取字段显示名称"""
        schema = self.REQUIRED_FIELDS.get(framework_key)
        if schema:
            return schema["field_names"]
        return {}

    def get_follow_up_questions(self, framework_key: str) -> Dict[str, str]:
        """获取追问问题"""
        schema = self.REQUIRED_FIELDS.get(framework_key)
        if schema:
            return schema["follow_up_questions"]
        return {}
