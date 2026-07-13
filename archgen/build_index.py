"""
ArchGen 向量索引构建器

扫 MD 目录 → MiniLM embed → 出 vector_index/
用于选题阶段的"整篇召回"——只找"哪篇"，不做切块 RAG

用法: cd archgen && python build_index.py [--md-dir=~/kb]

输出:
  vector_index/
    vectors.npy    (N, 384) float32
    metadata.pkl   [{path, abs_path, chars}]
"""

import os
import glob
import argparse
import json
import numpy as np
import pickle
import sys
from pathlib import Path

# 默认知识库目录：用户可通过 --md-dir 参数覆盖
DEFAULT_MD_DIR = os.path.expanduser("~/kb")
OUTPUT_DIR_DEFAULT = os.path.join(os.path.dirname(__file__), "vector_index")
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
BATCH_SIZE = 32
MAX_CHARS = 2000  # 每篇取前2000字做 embed（足够代表语义，且 MiniLM 支持 256 token 上下文）


def read_md(path: str) -> str:
    """读取 MD 文件前 MAX_CHARS 字符"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()[:MAX_CHARS]
    except Exception as e:
        print(f"[Index] 警告: 读取失败 {path}: {e}")
        return ""


def main():
    parser = argparse.ArgumentParser(description="ArchGen 向量索引构建")
    parser.add_argument(
        "--md-dir",
        default=DEFAULT_MD_DIR,
        help=f"MD 文件根目录 (默认: {DEFAULT_MD_DIR})",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help=f"输出目录 (默认: {OUTPUT_DIR_DEFAULT})",
    )
    args = parser.parse_args()

    output_dir = args.output_dir if args.output_dir else OUTPUT_DIR_DEFAULT
    md_dir = os.path.abspath(os.path.expanduser(args.md_dir))
    if not os.path.isdir(md_dir):
        print(f"[Index] 错误: 目录不存在: {md_dir}")
        sys.exit(1)

    print(f"[Index] 扫描目录: {md_dir}")
    print(f"[Index] 加载模型: {MODEL_NAME}")

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL_NAME, local_files_only=True)

    md_files = sorted(glob.glob(os.path.join(md_dir, "**/*.md"), recursive=True))
    if not md_files:
        print(f"[Index] 错误: 未找到 .md 文件")
        sys.exit(1)

    print(f"[Index] 找到 {len(md_files)} 个 MD 文件")

    metadata = []
    texts = []

    for p in md_files:
        rel = os.path.relpath(p, md_dir)
        content = read_md(p)
        metadata.append({
            "path": rel,
            "abs_path": p,
            "chars": len(content),
        })
        texts.append(content)
        print(f"  {rel}: {len(content)} chars")

    print(f"[Index] 编码中 (batch_size={BATCH_SIZE})...")
    vectors = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
    )
    # vectors: (N, 384) float32

    os.makedirs(output_dir, exist_ok=True)

    np.save(os.path.join(output_dir, "vectors.npy"), vectors)
    # 主输出：JSON（安全，无反序列化风险）
    with open(os.path.join(output_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    # 向后兼容：同时输出 pkl（旧版读取）
    with open(os.path.join(output_dir, "metadata.pkl"), "wb") as f:
        pickle.dump(metadata, f)

    print(f"[Index] 完成!")
    print(f"  {len(md_files)} files → {output_dir}/")
    print(f"  vectors shape: {vectors.shape}")
    print(f"  metadata size: {len(metadata)} entries")
    print(f"\n[Index] 提示: 启动服务器时会自动加载索引")


if __name__ == "__main__":
    main()
