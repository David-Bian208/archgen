#!/usr/bin/env python
"""ArchGen CLI 入口"""

import sys
import argparse
from pathlib import Path


def _load_config():
    """加载配置并设置 API Key"""
    from main import load_config
    config = load_config()
    return config


def cmd_generate(args):
    """单次生成架构图"""
    config = _load_config()
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"错误: 文件不存在 - {args.file}", file=sys.stderr)
        sys.exit(1)

    text = file_path.read_text(encoding="utf-8")
    print(f"正在分析: {args.file} ({len(text)} 字符)")

    # 自动分类
    from src.classifier import ContentClassifier
    classifier = ContentClassifier(config.get("llm", {}))
    result = classifier.classify_by_intent(text)
    article_type = result.get("primary", args.type or "claim")
    print(f"识别类型: {article_type}")

    # 调用 API 生成图片
    import httpx
    import json
    llm_cfg = config.get("llm", {})
    payload = {
        "text": text,
        "article_type": article_type,
        "style": args.style or "minimal",
        "size": args.size or "default",
    }
    try:
        base_url = llm_cfg.get("base_url", "https://api.deepseek.com/v1")
        api_key = llm_cfg.get("api_key", "")
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        # 调用本地 API
        with httpx.Client(timeout=120) as client:
            resp = client.post(
                f"http://localhost:{config.get('app',{}).get('port',8927)}/api/generate",
                json=payload,
            )
            if resp.status_code == 200:
                output_dir = Path(args.output)
                output_dir.mkdir(parents=True, exist_ok=True)
                out_path = output_dir / f"{file_path.stem}_{article_type}.png"
                out_path.write_bytes(resp.content)
                print(f"已生成: {out_path}")
            else:
                print(f"生成失败: HTTP {resp.status_code}")
                print("提示: 请先启动后端服务 `python main.py`", file=sys.stderr)
                sys.exit(1)
    except httpx.ConnectError:
        print("错误: 无法连接后端服务，请先启动 `python main.py`", file=sys.stderr)
        sys.exit(1)


def cmd_batch(args):
    """批量生成架构图"""
    input_dir = Path(args.input_dir)
    if not input_dir.is_dir():
        print(f"错误: 目录不存在 - {args.input_dir}", file=sys.stderr)
        sys.exit(1)

    md_files = list(input_dir.glob("*.md"))
    if not md_files:
        print(f"目录中无 .md 文件: {args.input_dir}")
        return

    print(f"批量生成 {len(md_files)} 个文件...")
    for i, md_file in enumerate(md_files, 1):
        print(f"[{i}/{len(md_files)}] {md_file.name}")
        # 直接调用 cmd_generate 逻辑
        class Args: pass
        a = Args(); a.file = str(md_file); a.type = None; a.style = "minimal"; a.size = "default"; a.output = args.output
        try:
            cmd_generate(a)
        except SystemExit:
            print(f"  ⚠️ {md_file.name} 生成失败，继续下一个...")
    print("批量生成完成")


def main():
    parser = argparse.ArgumentParser(
        description="ArchGen - 将 Markdown 文章转换为架构图",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 启动 Web 服务
  archgen serve

  # 单次生成
  archgen generate article.md --style minimal --size default

  # 批量生成
  archgen batch ./articles/ --output ./output/
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # serve 命令
    serve_parser = subparsers.add_parser("serve", help="启动 Web 服务")
    serve_parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    serve_parser.add_argument("--port", type=int, default=8927, help="监听端口")
    serve_parser.add_argument("--reload", action="store_true", help="开启热重载")

    # generate 命令
    gen_parser = subparsers.add_parser("generate", help="生成架构图")
    gen_parser.add_argument("file", help="Markdown 文件路径")
    gen_parser.add_argument("--type", help="文章类型（自动识别，也可手动指定）")
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
        port = args.port or 8927
        print(f"启动 ArchGen Web 服务: http://{args.host}:{port}")
        uvicorn.run("main:app", host=args.host, port=port, reload=args.reload)

    elif args.command == "generate":
        cmd_generate(args)

    elif args.command == "batch":
        cmd_batch(args)

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
