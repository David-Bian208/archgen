"""
LLM 缓存机制
减少重复 API 调用，提升性能
"""

import hashlib
import json
import time
from typing import Optional, Dict, Any
from pathlib import Path


class LLMCache:
    """LLM 响应缓存"""
    
    def __init__(self, cache_dir: str = "/tmp/llm_cache", ttl_seconds: int = 300):
        """
        初始化缓存
        
        Args:
            cache_dir: 缓存目录
            ttl_seconds: 缓存过期时间（秒），默认 5 分钟
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds
        self.hits = 0
        self.misses = 0
    
    def _generate_cache_key(self, system_prompt: str, user_prompt: str) -> str:
        """生成缓存键（MD5 哈希）"""
        content = f"{system_prompt}|||{user_prompt}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """
        从缓存获取响应
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            
        Returns:
            缓存的响应文本，如果不存在或已过期则返回 None
        """
        cache_key = self._generate_cache_key(system_prompt, user_prompt)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if not cache_file.exists():
            self.misses += 1
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 检查是否过期
            if time.time() - data['timestamp'] > self.ttl_seconds:
                cache_file.unlink()  # 删除过期缓存
                self.misses += 1
                return None
            
            self.hits += 1
            return data['response']
        
        except (json.JSONDecodeError, KeyError, IOError):
            self.misses += 1
            return None
    
    def set(self, system_prompt: str, user_prompt: str, response: str) -> None:
        """
        设置缓存
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            response: LLM 响应文本
        """
        cache_key = self._generate_cache_key(system_prompt, user_prompt)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'response': response,
                    'timestamp': time.time(),
                }, f, ensure_ascii=False)
        except IOError as e:
            print(f"缓存写入失败：{e}")
    
    def clear(self) -> None:
        """清空缓存"""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.2f}%",
            "cache_dir": str(self.cache_dir),
            "ttl_seconds": self.ttl_seconds,
        }


# 全局缓存实例（单例模式）
_global_cache: Optional[LLMCache] = None


def get_llm_cache() -> LLMCache:
    """获取全局 LLM 缓存实例"""
    global _global_cache
    if _global_cache is None:
        _global_cache = LLMCache()
    return _global_cache


def clear_llm_cache() -> None:
    """清空全局 LLM 缓存"""
    cache = get_llm_cache()
    cache.clear()
