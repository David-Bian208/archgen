"""
A/B 测试模块 (A/B Testing)

功能：
- 管理 A/B 测试配置
- 用户分组（50/50 流量分配）
- 实验状态管理
- 统计显著性检验

实验设计：
- 第一期：测试降级提示 Alert（显示 vs 不显示）
- 对照组 A：显示降级提示
- 实验组 B：不显示降级提示
"""

import logging
import hashlib
import json
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# 配置文件路径
CONFIG_PATH = Path(__file__).parent.parent / "data" / "ab_test_config.json"
CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

# 默认配置
DEFAULT_CONFIG = {
    "experiments": {
        "degradation_alert": {
            "name": "降级提示 Alert 测试",
            "description": "测试降级提示对用户确认率的影响",
            "status": "running",  # draft, running, paused, completed
            "start_date": "2026-06-01",
            "end_date": "2026-07-05",
            "traffic_split": 50,  # 50/50
            "groups": {
                "A": {
                    "name": "对照组",
                    "description": "不显示降级提示",
                    "show_alert": False,
                },
                "B": {
                    "name": "实验组",
                    "description": "显示降级提示",
                    "show_alert": True,
                },
            },
        },
        "knowledge_label": {
            "name": "知识级别标签测试",
            "description": "测试知识级别标签对用户理解的影响",
            "status": "draft",  # 第二期
            "start_date": None,
            "end_date": None,
            "traffic_split": 50,
            "groups": {
                "A": {"name": "对照组", "show_label": True},
                "B": {"name": "实验组", "show_label": False},
            },
        },
        "conditional_reevaluate": {
            "name": "条件化重新评估测试",
            "description": "测试条件化重新评估对问题数量的影响",
            "status": "draft",  # 第三期
            "start_date": None,
            "end_date": None,
            "traffic_split": 50,
            "groups": {
                "A": {"name": "对照组", "enable_reevaluate": True},
                "B": {"name": "实验组", "enable_reevaluate": False},
            },
        },
    },
    "created_at": datetime.now().isoformat(),
    "updated_at": datetime.now().isoformat(),
}


class ABTestManager:
    """A/B 测试管理器"""

    def __init__(self, config_path: str = str(CONFIG_PATH)):
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """加载配置"""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载 A/B 测试配置失败: {e}")
                return DEFAULT_CONFIG
        else:
            self._save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG

    def _save_config(self, config: Dict):
        """保存配置"""
        config["updated_at"] = datetime.now().isoformat()
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def assign_user(self, session_id: str, experiment_key: str = "degradation_alert") -> Dict:
        """
        为用户分配实验组
        
        Args:
            session_id: 会话 ID
            experiment_key: 实验 key
            
        Returns:
            {
                "experiment_key": "degradation_alert",
                "group": "A",
                "config": {"show_alert": true}
            }
        """
        experiment = self.config.get("experiments", {}).get(experiment_key)
        if not experiment:
            logger.warning(f"实验不存在: {experiment_key}")
            return {"experiment_key": experiment_key, "group": "A", "config": {}}
        
        # 检查实验状态
        if experiment.get("status") != "running":
            logger.info(f"实验未运行: {experiment_key} ({experiment.get('status')})")
            return {"experiment_key": experiment_key, "group": "A", "config": {}}
        
        # 检查时间范围
        start_date = experiment.get("start_date")
        end_date = experiment.get("end_date")
        now = datetime.now().date()
        
        if start_date and datetime.fromisoformat(start_date).date() > now:
            logger.info(f"实验未开始: {experiment_key}")
            return {"experiment_key": experiment_key, "group": "A", "config": {}}
        
        if end_date and datetime.fromisoformat(end_date).date() < now:
            logger.info(f"实验已结束: {experiment_key}")
            experiment["status"] = "completed"
            self._save_config(self.config)
            return {"experiment_key": experiment_key, "group": "A", "config": {}}
        
        # 使用 session_id hash 分配组
        hash_value = int(hashlib.md5(session_id.encode()).hexdigest(), 16)
        traffic_split = experiment.get("traffic_split", 50)
        
        # 50/50 分配
        group_key = "A" if hash_value % 100 < traffic_split else "B"
        group_config = experiment.get("groups", {}).get(group_key, {})
        
        return {
            "experiment_key": experiment_key,
            "group": group_key,
            "config": group_config,
            "experiment_name": experiment.get("name", ""),
        }

    def get_experiment_config(self, experiment_key: str) -> Optional[Dict]:
        """获取实验配置"""
        return self.config.get("experiments", {}).get(experiment_key)

    def start_experiment(self, experiment_key: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
        """启动实验"""
        experiment = self.config.get("experiments", {}).get(experiment_key)
        if not experiment:
            raise ValueError(f"实验不存在: {experiment_key}")
        
        experiment["status"] = "running"
        if start_date:
            experiment["start_date"] = start_date
        if end_date:
            experiment["end_date"] = end_date
        
        self._save_config(self.config)
        logger.info(f"实验已启动: {experiment_key}")

    def pause_experiment(self, experiment_key: str):
        """暂停实验"""
        experiment = self.config.get("experiments", {}).get(experiment_key)
        if not experiment:
            raise ValueError(f"实验不存在: {experiment_key}")
        
        experiment["status"] = "paused"
        self._save_config(self.config)
        logger.info(f"实验已暂停: {experiment_key}")

    def stop_experiment(self, experiment_key: str):
        """停止实验"""
        experiment = self.config.get("experiments", {}).get(experiment_key)
        if not experiment:
            raise ValueError(f"实验不存在: {experiment_key}")
        
        experiment["status"] = "completed"
        experiment["end_date"] = datetime.now().date().isoformat()
        self._save_config(self.config)
        logger.info(f"实验已停止: {experiment_key}")

    def get_all_experiments(self) -> Dict:
        """获取所有实验配置"""
        return self.config.get("experiments", {})

    def calculate_significance(self, group_a_data: Dict, group_b_data: Dict) -> Dict:
        """
        计算统计显著性（卡方检验简化版）
        
        Args:
            group_a_data: {"success": 100, "total": 120}
            group_b_data: {"success": 90, "total": 115}
            
        Returns:
            {
                "p_value": 0.05,
                "significant": true,
                "confidence_level": 0.95,
                "recommendation": "采用实验组"
            }
        """
        import math
        
        a_success = group_a_data.get("success", 0)
        a_total = group_a_data.get("total", 0)
        b_success = group_b_data.get("success", 0)
        b_total = group_b_data.get("total", 0)
        
        if a_total == 0 or b_total == 0:
            return {
                "p_value": 1.0,
                "significant": False,
                "confidence_level": 0.95,
                "recommendation": "数据不足",
            }
        
        # 计算比例
        p_a = a_success / a_total
        p_b = b_success / b_total
        
        # 合并比例
        p_pool = (a_success + b_success) / (a_total + b_total)
        
        # 标准误
        se = math.sqrt(p_pool * (1 - p_pool) * (1/a_total + 1/b_total))
        
        if se == 0:
            return {
                "p_value": 1.0,
                "significant": False,
                "confidence_level": 0.95,
                "recommendation": "数据不足",
            }
        
        # Z 统计量
        z = (p_b - p_a) / se
        
        # 近似 p 值（使用正态分布近似）
        p_value = 2 * (1 - _normal_cdf(abs(z)))
        
        # 判断显著性
        significant = p_value < 0.05
        
        # 推荐
        if significant:
            if p_b > p_a:
                recommendation = "采用实验组（B 组表现更好）"
            else:
                recommendation = "保持对照组（A 组表现更好）"
        else:
            recommendation = "无显著差异，建议继续测试或采用实验组（简化体验）"
        
        return {
            "p_value": round(p_value, 4),
            "significant": significant,
            "confidence_level": 0.95,
            "group_a_rate": round(p_a, 4),
            "group_b_rate": round(p_b, 4),
            "recommendation": recommendation,
        }


def _normal_cdf(x: float) -> float:
    """标准正态分布 CDF 近似"""
    import math
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def get_ab_test_manager() -> ABTestManager:
    """获取 A/B 测试管理器实例"""
    return ABTestManager()
