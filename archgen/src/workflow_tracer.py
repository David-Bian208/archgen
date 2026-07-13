"""Workflow Tracer - 工作流可观测性系统"""

import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field

logger = logging.getLogger(__name__)


@dataclass
class Span:
    """追踪跨度"""
    name: str
    start_time: float
    end_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    @property
    def duration(self) -> float:
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "duration": self.duration
        }


class WorkflowTracer:
    """工作流追踪器"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.spans: List[Span] = []
        self.current_span: Optional[Span] = None
    
    def start_span(self, name: str, metadata: Optional[Dict] = None) -> Span:
        """开始一个追踪跨度"""
        if self.current_span:
            logger.warning(f"跨度 {self.current_span.name} 未结束就开始新的跨度")
        
        span = Span(
            name=name,
            start_time=time.time(),
            metadata=metadata or {}
        )
        self.current_span = span
        self.spans.append(span)
        logger.info(f"[{self.session_id}] 开始跨度: {name}")
        return span
    
    def end_span(self, result: Optional[Dict] = None, error: Optional[str] = None):
        """结束当前跨度"""
        if not self.current_span:
            logger.warning("没有活跃的跨度可以结束")
            return
        
        self.current_span.end_time = time.time()
        self.current_span.result = result
        self.current_span.error = error
        
        duration = self.current_span.duration
        status = "❌" if error else "✅"
        logger.info(f"[{self.session_id}] {status} 跨度: {self.current_span.name} ({duration:.2f}s)")
        
        self.current_span = None
    
    def export(self) -> Dict[str, Any]:
        """导出追踪数据"""
        total_duration = sum(s.duration for s in self.spans)
        return {
            "session_id": self.session_id,
            "total_duration": total_duration,
            "spans": [s.to_dict() for s in self.spans],
            "span_count": len(self.spans)
        }
    
    def get_slowest_spans(self, top_n: int = 3) -> List[Dict]:
        """获取最慢的 N 个跨度"""
        sorted_spans = sorted(self.spans, key=lambda s: s.duration, reverse=True)
        return [s.to_dict() for s in sorted_spans[:top_n]]


class TracerManager:
    """追踪管理器"""
    
    def __init__(self):
        self.tracers: Dict[str, WorkflowTracer] = {}
    
    def create_tracer(self, session_id: str) -> WorkflowTracer:
        """创建追踪器"""
        tracer = WorkflowTracer(session_id)
        self.tracers[session_id] = tracer
        return tracer
    
    def get_tracer(self, session_id: str) -> Optional[WorkflowTracer]:
        """获取追踪器"""
        return self.tracers.get(session_id)
    
    def export_all(self) -> Dict[str, Any]:
        """导出所有追踪数据"""
        return {
            session_id: tracer.export()
            for session_id, tracer in self.tracers.items()
        }


# 全局追踪管理器
_global_tracer_manager = TracerManager()


def get_tracer_manager() -> TracerManager:
    return _global_tracer_manager
