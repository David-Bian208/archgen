#!/usr/bin/env python
"""ArchGen CLI 入口"""

import sys
import argparse
from pathlib import Path
from main import create_app

def main():
    parser = argparse.ArgumentParser(
        description="ArchGen - 将 Markdown 文章转换为架构图",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 启动 Web 服务
  archgen serve

  # 单次生成
  archgen generate article.md --type claim --style minimal --size default

  # 批量生成
  archgen batch ./articles/ --output ./output/
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # serve 命令
    serve_parser = subparsers.add_parser("serve", help="启动 Web 服务")
    serve_parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    serve_parser.add_argument("--port", type=int, default=8905, help="监听端口")
    serve_parser.add_argument("--reload", action="store_true", help="开启热重载")

    # generate 命令
    gen_parser = subparsers.add_parser("generate", help="生成架构图")
    gen_parser.add_argument("file", help="Markdown 文件路径")
    gen_parser.add_argument("--type", choices=["claim", "causal", "system", "comparison", "process"], help="文章类型")
    gen_parser.add_argument("--style", default="minimal", choices=["minimal", "business", "tech"], help="样式风格")
    gen_parser.add_argument("--size", default="default", choices=["default", "wechat", "xiaohongshu", "ppt"], help="输出尺寸")
    gen_parser.add_argument("--output", default="output", help="输出目录")

    # batch 命令
    batch_parser = subparsers.add_parser("batch", help="批量生成")
    batch_parser.add_argument("input_dir", help="输入目录")
    batch_parser.add_argument("--output", default="output", help="输出目录")

    args = parser.parse_args()

    if args.command == "serve":
        import uvicorn
        print(f"启动 ArchGen Web 服务: http://{args.host}:{args.port}")
        uvicorn.run("main:app", host=args.host, port=args.port, reload=args.reload)

    elif args.command == "generate":
        print(f"生成架构图: {args.file}")
        print(f"类型: {args.type or '自动识别'}, 样式: {args.style}, 尺寸: {args.size}")
        # TODO: 实现 CLI 生成逻辑
        print("CLI 生成功能待实现...")

    elif args.command == "batch":
        print(f"批量生成: {args.input_dir} -> {args.output}")
        # TODO: 实现批量生成逻辑
        print("批量生成功能待实现...")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
