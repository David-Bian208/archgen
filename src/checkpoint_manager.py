"""Checkpoint Manager - 错误恢复检查点系统"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class Checkpoint:
    """检查点数据"""
    session_id: str
    step: int
    step_name: str
    status: str  # "running", "completed", "failed"
    results: Dict[str, Any]
    error: Optional[str] = None
    created_at: float = 0.0
    updated_at: float = 0.0
    
    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()
        if self.updated_at == 0.0:
            self.updated_at = time.time()


class CheckpointManager:
    """检查点管理器"""
    
    def __init__(self, checkpoint_dir: str = "output/checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Checkpoint] = {}
    
    def _get_checkpoint_path(self, session_id: str) -> Path:
        """获取检查点文件路径"""
        return self.checkpoint_dir / f"{session_id}.json"
    
    def save_checkpoint(self, checkpoint: Checkpoint):
        """保存检查点"""
        checkpoint.updated_at = time.time()
        self._cache[checkpoint.session_id] = checkpoint
        
        path = self._get_checkpoint_path(checkpoint.session_id)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(asdict(checkpoint), f, ensure_ascii=False, indent=2)
        
        logger.info(f"检查点已保存: {checkpoint.session_id} - {checkpoint.step_name}")
    
    def load_checkpoint(self, session_id: str) -> Optional[Checkpoint]:
        """加载检查点"""
        if session_id in self._cache:
            return self._cache[session_id]
        
        path = self._get_checkpoint_path(session_id)
        if not path.exists():
            return None
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        checkpoint = Checkpoint(**data)
        self._cache[session_id] = checkpoint
        return checkpoint
    
    def delete_checkpoint(self, session_id: str) -> bool:
        """删除检查点"""
        path = self._get_checkpoint_path(session_id)
        if path.exists():
            path.unlink()
            self._cache.pop(session_id, None)
            return True
        return False
    
    def list_checkpoints(self) -> list:
        """列出所有检查点"""
        checkpoints = []
        for path in self.checkpoint_dir.glob("*.json"):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                checkpoints.append(data)
        return sorted(checkpoints, key=lambda c: c["updated_at"], reverse=True)
    
    def create_checkpoint(self, session_id: str, step: int, step_name: str, 
                         results: Dict[str, Any], status: str = "running") -> Checkpoint:
        """创建新检查点"""
        checkpoint = Checkpoint(
            session_id=session_id,
            step=step,
            step_name=step_name,
            status=status,
            results=results
        )
        self.save_checkpoint(checkpoint)
        return checkpoint
    
    def update_checkpoint(self, session_id: str, status: str, 
                         results: Optional[Dict] = None, error: Optional[str] = None) -> Optional[Checkpoint]:
        """更新检查点状态"""
        checkpoint = self.load_checkpoint(session_id)
        if not checkpoint:
            return None
        
        checkpoint.status = status
        if results:
            checkpoint.results.update(results)
        if error:
            checkpoint.error = error
        
        self.save_checkpoint(checkpoint)
        return checkpoint
