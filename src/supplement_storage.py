"""
知识库补充内容存储 - Session 级临时存储 + 领域库预留

功能：
- Session 级补充内容持久化（JSON 文件存储）
- 动态合并补充内容到 MCP 摘要（供 LLM 使用）
- 预留领域库导出接口（export_to_domain）
- 30 天自动清理机制

设计原则：
- 不污染原始 MCP 数据
- 按 Session 隔离
- 可追溯来源（ai-pulse/manual/file）
- 为未来领域库预留完整元数据字段
"""

import json
import logging
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# 存储路径配置
SUPPLEMENTS_DIR = Path(__file__).parent.parent / "data" / "supplements"
DOMAIN_KNOWLEDGE_DIR = Path(__file__).parent.parent / "data" / "domain_knowledge"
METADATA_DIR = Path(__file__).parent.parent / "data" / "session_metadata"

# 确保目录存在
SUPPLEMENTS_DIR.mkdir(parents=True, exist_ok=True)
DOMAIN_KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
METADATA_DIR.mkdir(parents=True, exist_ok=True)

# Session 数据保留天数
SESSION_RETENTION_DAYS = 30


class SupplementStorage:
    """补充内容存储（Session 级）"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.file_path = SUPPLEMENTS_DIR / f"{session_id}.json"
        self.data = self._load()

    def _load(self) -> Dict:
        """加载 Session 数据"""
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载 Session 补充数据失败: {e}")
                return self._new_data()
        return self._new_data()

    def _new_data(self) -> Dict:
        """创建新的 Session 数据结构"""
        return {
            "session_id": self.session_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "supplements": [],
        }

    def _save(self):
        """保存到文件"""
        self.data["updated_at"] = datetime.now().isoformat()
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def add_supplement(
        self,
        supplement_type: str,
        dimension: str,
        content: str,
        source: str,
        source_detail: Optional[Dict] = None,
        domain_tags: Optional[List[str]] = None,
    ) -> str:
        """
        添加补充内容

        Args:
            supplement_type: 补充类型（case/persona/data/framework）
            dimension: 缺失维度标签（对应 CompletenessChecker）
            content: 补充内容正文
            source: 来源（ai-pulse/manual/file）
            source_detail: 来源详情（如 AI-Pulse 返回的案例元数据）
            domain_tags: 领域标签（为未来领域库预留）

        Returns:
            supplement_id: 补充内容 ID
        """
        supplement_id = f"supp_{uuid.uuid4().hex[:8]}"

        supplement = {
            "id": supplement_id,
            "type": supplement_type,
            "dimension": dimension,
            "content": content,
            "source": source,
            "source_detail": source_detail or {},
            "confirmed": False,  # 用户是否确认
            "domain_tags": domain_tags or [],
            "usage_count": 0,
            "created_at": datetime.now().isoformat(),
        }

        self.data["supplements"].append(supplement)
        self._save()

        logger.info(
            f"添加补充内容: session={self.session_id}, id={supplement_id}, "
            f"type={supplement_type}, source={source}"
        )

        return supplement_id

    def confirm_supplement(self, supplement_id: str) -> bool:
        """确认补充内容（标记为 confirmed）"""
        for supp in self.data["supplements"]:
            if supp["id"] == supplement_id:
                supp["confirmed"] = True
                self._save()
                logger.info(f"确认补充内容: id={supplement_id}")
                return True
        logger.warning(f"补充内容不存在: id={supplement_id}")
        return False

    def get_all(self, confirmed_only: bool = False) -> List[Dict]:
        """获取当前 Session 所有补充内容"""
        if confirmed_only:
            return [s for s in self.data["supplements"] if s.get("confirmed", False)]
        return self.data["supplements"]

    def get_by_id(self, supplement_id: str) -> Optional[Dict]:
        """根据 ID 获取补充内容"""
        for supp in self.data["supplements"]:
            if supp["id"] == supplement_id:
                return supp
        return None

    def delete(self, supplement_id: str) -> bool:
        """删除补充内容"""
        original_count = len(self.data["supplements"])
        self.data["supplements"] = [
            s for s in self.data["supplements"] if s["id"] != supplement_id
        ]
        if len(self.data["supplements"]) < original_count:
            self._save()
            logger.info(f"删除补充内容: id={supplement_id}")
            return True
        return False

    def merge_to_mcp(self, mcp_summary: str) -> str:
        """
        将已确认的补充内容合并到 MCP 摘要（供 LLM 使用）

        动态合并：只合并 confirmed=True 的补充内容
        """
        confirmed = self.get_all(confirmed_only=True)

        if not confirmed:
            return mcp_summary

        supplement_text = "\n\n--- 【用户补充的知识库】---\n"
        for s in confirmed:
            source_label = {
                "ai-pulse": "AI-Pulse",
                "manual": "用户手动补充",
                "file": "从知识库文件提取",
            }.get(s["source"], s["source"])

            supplement_text += (
                f"[{source_label}] [{s['dimension']}] {s['type']}：\n{s['content']}\n\n"
            )

        return mcp_summary + supplement_text

    def export_to_domain(
        self,
        domain_tag: str,
        supplement_ids: Optional[List[str]] = None,
    ) -> Dict:
        """
        将 Session 补充内容导出到领域知识库

        Args:
            domain_tag: 领域标签（如 "ai-efficiency"）
            supplement_ids: 要导出的补充内容 ID 列表（None = 导出全部已确认的）

        Returns:
            {
                "exported_count": 3,
                "domain_path": "data/domain_knowledge/ai-efficiency.json",
                "exists_count": 0,  # 已存在不重复导出
                "message": "...",
            }
        """
        # P1 阶段：返回 mock 数据（接口签名已定死，后续 P2 实现完整逻辑）
        return {
            "exported_count": 0,
            "domain_path": None,
            "exists_count": 0,
            "message": "领域知识库功能开发中，预计后续版本上线",
        }

    def get_stats(self) -> Dict:
        """获取当前 Session 补充统计"""
        all_supps = self.data["supplements"]
        confirmed = [s for s in all_supps if s.get("confirmed", False)]

        return {
            "total_count": len(all_supps),
            "confirmed_count": len(confirmed),
            "by_source": {
                "ai-pulse": len([s for s in all_supps if s["source"] == "ai-pulse"]),
                "manual": len([s for s in all_supps if s["source"] == "manual"]),
                "file": len([s for s in all_supps if s["source"] == "file"]),
            },
            "by_type": {
                "case": len([s for s in all_supps if s["type"] == "case"]),
                "persona": len([s for s in all_supps if s["type"] == "persona"]),
                "data": len([s for s in all_supps if s["type"] == "data"]),
            },
        }


def record_session_metadata(
    session_id: str,
    domain_tag: str = "",
    generation_mode: str = "",
    user_satisfaction: Optional[int] = None,
    exported_to_domain: bool = False,
) -> Dict:
    """
    记录项目元数据（埋点）

    用于后续分析：
    - 哪个领域用户做得最多？
    - 用户补充意愿如何？
    - 收藏转化率如何？
    - 哪种生成模式最常见？

    Args:
        session_id: 会话 ID
        domain_tag: 用户选择的领域标签
        generation_mode: 生成模式（standard/degraded_logic 等）
        user_satisfaction: 用户评分（1-5 星）
        exported_to_domain: 是否导出到领域库

    Returns:
        元数据记录
    """
    supplement_storage = SupplementStorage(session_id)
    stats = supplement_storage.get_stats()

    metadata = {
        "session_id": session_id,
        "domain_tag": domain_tag,
        "supplement_count": stats["total_count"],
        "confirmed_count": stats["confirmed_count"],
        "exported_to_domain": exported_to_domain,
        "generation_mode": generation_mode,
        "user_satisfaction": user_satisfaction,
        "created_at": datetime.now().isoformat(),
    }

    # 保存到元数据文件
    metadata_path = METADATA_DIR / f"{session_id}.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    logger.info(f"记录项目元数据: session={session_id}, domain={domain_tag}")

    return metadata


def cleanup_expired_supplements(days: int = SESSION_RETENTION_DAYS):
    """
    清理过期的 Session 补充数据

    保留 30 天，避免用户回来修改时需要重新补充
    """
    cutoff = datetime.now() - timedelta(days=days)
    cleaned_count = 0

    for file_path in SUPPLEMENTS_DIR.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            created_at = datetime.fromisoformat(data.get("created_at", ""))
            if created_at < cutoff:
                file_path.unlink()
                cleaned_count += 1
                logger.info(f"清理过期 Session 数据: {file_path.name}")

        except Exception as e:
            logger.warning(f"清理 Session 数据失败: {file_path.name}, error={e}")

    # 同时清理过期的元数据
    for file_path in METADATA_DIR.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            created_at = datetime.fromisoformat(data.get("created_at", ""))
            if created_at < cutoff:
                file_path.unlink()
                logger.info(f"清理过期元数据: {file_path.name}")

        except Exception as e:
            logger.warning(f"清理元数据失败: {file_path.name}, error={e}")

    if cleaned_count > 0:
        logger.info(f"清理完成: 删除 {cleaned_count} 个过期 Session 数据")

    return {"cleaned_count": cleaned_count}


def get_supplement_storage(session_id: str) -> SupplementStorage:
    """获取补充内容存储实例（便捷函数）"""
    return SupplementStorage(session_id)
