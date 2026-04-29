#!/usr/bin/env python3
"""
知识库语义检索工具

功能：
1. 将知识库文档转换为向量
2. 支持语义检索（相似问题推荐）
3. 自动关联 Bug → 知识条目

使用示例：
```bash
# 索引所有文档
python3 scripts/knowledge_search.py --index

# 搜索相关问题
python3 scripts/knowledge_search.py --search "追问流程失效"

# 自动关联（分析 Git 提交）
python3 scripts/knowledge_search.py --auto-associate
```
"""

import os
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any

# 尝试导入 sentence-transformers（可选依赖）
try:
    from sentence_transformers import SentenceTransformer
    HAS_ENCODER = True
except ImportError:
    HAS_ENCODER = False
    print("⚠️ 未安装 sentence-transformers，使用关键词匹配模式")
    print("安装：pip install sentence-transformers")

class KnowledgeSearcher:
    def __init__(self, knowledge_base_path: str = "docs"):
        self.kb_path = Path(knowledge_base_path)
        self.index_path = Path(".knowledge_index.json")
        self.model = None
        
        if HAS_ENCODER:
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    
    def load_documents(self) -> List[Dict[str, Any]]:
        """加载所有知识库文档"""
        docs = []
        
        # 加载 docs/ 目录
        for md_file in self.kb_path.glob("*.md"):
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
                docs.append({
                    "path": str(md_file),
                    "title": md_file.stem,
                    "content": content,
                    "type": "best_practice"
                })
        
        # 加载 memory/lessons/ 目录
        lessons_path = Path("memory/lessons")
        if lessons_path.exists():
            for md_file in lessons_path.glob("*.md"):
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    docs.append({
                        "path": str(md_file),
                        "title": f"经验：{md_file.stem}",
                        "content": content,
                        "type": "lessons_learned"
                    })
        
        return docs
    
    def extract_chunks(self, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将文档分块（按章节）"""
        chunks = []
        
        for doc in docs:
            # 按标题分块
            sections = doc["content"].split("\n## ")
            
            for i, section in enumerate(sections):
                if len(section.strip()) > 50:  # 忽略太短的块
                    chunk_id = hashlib.md5(f"{doc['path']}:{i}".encode()).hexdigest()[:8]
                    chunks.append({
                        "chunk_id": chunk_id,
                        "doc_path": doc["path"],
                        "doc_title": doc["title"],
                        "content": section[:500],  # 限制长度
                        "type": doc["type"]
                    })
        
        return chunks
    
    def build_index(self):
        """构建检索索引"""
        print("📚 加载知识库文档...")
        docs = self.load_documents()
        print(f"   找到 {len(docs)} 个文档")
        
        print("📝 分块处理...")
        chunks = self.extract_chunks(docs)
        print(f"   生成 {len(chunks)} 个块")
        
        if self.model:
            print("🧠 生成向量...")
            texts = [c["content"] for c in chunks]
            embeddings = self.model.encode(texts, show_progress_bar=True)
            
            index = {
                "chunks": chunks,
                "embeddings": embeddings.tolist(),
                "model": "paraphrase-multilingual-MiniLM-L12-v2"
            }
        else:
            # 关键词匹配模式
            index = {
                "chunks": chunks,
                "keywords": self._extract_keywords(chunks),
                "mode": "keyword"
            }
        
        print("💾 保存索引...")
        with open(self.index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
        
        print("✅ 索引构建完成！")
    
    def _extract_keywords(self, chunks: List[Dict[str, Any]]) -> Dict[str, List[int]]:
        """提取关键词（用于无模型模式）"""
        keywords = {}
        
        for i, chunk in enumerate(chunks):
            # 简单分词（中文按字符）
            words = set(chunk["content"])
            for word in words:
                if word not in keywords:
                    keywords[word] = []
                keywords[word].append(i)
        
        return keywords
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索相关知识"""
        if not self.index_path.exists():
            print("❌ 索引不存在，请先运行 --index")
            return []
        
        with open(self.index_path, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        if index.get("model"):
            # 向量检索
            import numpy as np
            from sklearn.metrics.pairwise import cosine_similarity
            
            query_embedding = self.model.encode([query])
            similarities = cosine_similarity(query_embedding, index["embeddings"])[0]
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            results = []
            for idx in top_indices:
                results.append({
                    **index["chunks"][idx],
                    "score": float(similarities[idx])
                })
        else:
            # 关键词匹配
            scores = {}
            query_words = set(query)
            
            for i, chunk in enumerate(index["chunks"]):
                score = len(query_words & set(chunk["content"])) / len(query_words)
                if score > 0:
                    scores[i] = score
            
            top_indices = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
            
            results = []
            for idx, score in top_indices:
                results.append({
                    **index["chunks"][idx],
                    "score": score
                })
        
        return results
    
    def auto_associate(self, commit_message: str) -> List[Dict[str, Any]]:
        """自动关联 Git 提交与知识库"""
        print(f"🔍 分析提交信息：{commit_message[:50]}...")
        results = self.search(commit_message, top_k=3)
        
        if results:
            print("\n📚 关联的知识库条目：")
            for r in results:
                print(f"   - {r['doc_title']} (相关度：{r['score']:.2f})")
                print(f"     路径：{r['doc_path']}")
        else:
            print("\n⚠️ 未找到相关知识")
        
        return results


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="知识库语义检索工具")
    parser.add_argument("--index", action="store_true", help="构建索引")
    parser.add_argument("--search", type=str, help="搜索关键词")
    parser.add_argument("--auto-associate", type=str, help="自动关联 Git 提交")
    parser.add_argument("--top-k", type=int, default=5, help="返回结果数量")
    
    args = parser.parse_args()
    
    searcher = KnowledgeSearcher()
    
    if args.index:
        searcher.build_index()
    elif args.search:
        results = searcher.search(args.search, top_k=args.top_k)
        print(f"\n📚 找到 {len(results)} 个相关结果：\n")
        for r in results:
            print(f"【{r['doc_title']}】 (相关度：{r['score']:.2f})")
            print(f"路径：{r['doc_path']}")
            print(f"内容：{r['content'][:100]}...\n")
    elif args.auto_associate:
        searcher.auto_associate(args.auto_associate)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
