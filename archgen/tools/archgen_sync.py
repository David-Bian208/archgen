#!/usr/bin/env python3
"""
ArchGen Sync 工具 - 本地文件夹同步到云端
功能：
1. 扫描本地文件夹中的 Markdown 文件
2. 计算文件哈希值，识别新增/修改/删除
3. 上传文件到云端服务器
4. 支持增量同步和全量同步
"""

import os
import sys
import json
import hashlib
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional
import httpx

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ArchGenSync:
    """ArchGen 本地文件夹同步工具"""

    ALLOWED_EXTENSIONS = {".md", ".txt", ".markdown"}
    DEFAULT_LOCAL_FOLDER = str(Path.home() / "My_Knowledge_Base" / "Inbox")
    DEFAULT_SERVER_URL = "http://localhost:8905"
    SYNC_STATE_FILE = ".archgen_sync_state.json"

    def __init__(
        self,
        local_folder: str = None,
        server_url: str = None,
        api_key: str = None,
    ):
        self.local_folder = Path(local_folder or self.DEFAULT_LOCAL_FOLDER)
        self.server_url = (server_url or self.DEFAULT_SERVER_URL).rstrip("/")
        self.api_key = api_key or os.getenv("ARCHGEN_API_KEY", "")
        self.sync_state_path = self.local_folder / self.SYNC_STATE_FILE
        self.sync_state = self._load_sync_state()

    def _load_sync_state(self) -> Dict:
        """加载同步状态"""
        if self.sync_state_path.exists():
            try:
                with open(self.sync_state_path) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载同步状态失败: {e}")
        return {
            "last_sync_time": None,
            "synced_files": {},  # {file_path: {"hash": "...", "size": 123, "synced_at": "..."}}
            "total_synced": 0,
        }

    def _save_sync_state(self):
        """保存同步状态"""
        self.sync_state["last_sync_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(self.sync_state_path, "w") as f:
            json.dump(self.sync_state, f, indent=2, ensure_ascii=False)

    def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件 MD5 哈希值"""
        md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5.update(chunk)
        return md5.hexdigest()

    def scan_local_files(self) -> List[Dict]:
        """扫描本地文件夹中的所有支持的文件"""
        if not self.local_folder.exists():
            logger.error(f"本地文件夹不存在: {self.local_folder}")
            return []

        files = []
        for file_path in self.local_folder.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in self.ALLOWED_EXTENSIONS:
                # 跳过同步状态文件
                if file_path.name == self.SYNC_STATE_FILE:
                    continue

                file_hash = self._calculate_file_hash(file_path)
                files.append({
                    "name": file_path.name,
                    "path": str(file_path),
                    "relative_path": str(file_path.relative_to(self.local_folder)),
                    "size": file_path.stat().st_size,
                    "hash": file_hash,
                    "modified_at": time.strftime(
                        "%Y-%m-%d %H:%M:%S",
                        time.localtime(file_path.stat().st_mtime)
                    ),
                })

        logger.info(f"扫描到 {len(files)} 个文件在 {self.local_folder}")
        return files

    def detect_changes(self, local_files: List[Dict]) -> Dict:
        """检测文件变化（新增/修改/删除）"""
        synced = self.sync_state.get("synced_files", {})

        new_files = []
        modified_files = []
        unchanged_files = []

        for file_info in local_files:
            file_path = file_info["path"]
            file_hash = file_info["hash"]

            if file_path not in synced:
                new_files.append(file_info)
            elif synced[file_path]["hash"] != file_hash:
                modified_files.append(file_info)
            else:
                unchanged_files.append(file_info)

        # 检测已删除的文件
        deleted_files = []
        local_paths = {f["path"] for f in local_files}
        for synced_path in synced:
            if synced_path not in local_paths:
                deleted_files.append(synced_path)

        return {
            "new": new_files,
            "modified": modified_files,
            "unchanged": unchanged_files,
            "deleted": deleted_files,
        }

    async def upload_file(self, file_info: Dict) -> bool:
        """上传单个文件到云端"""
        file_path = Path(file_info["path"])
        if not file_path.exists():
            logger.error(f"文件不存在: {file_path}")
            return False

        try:
            url = f"{self.server_url}/api/v1/files/upload"
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            with open(file_path, "rb") as f:
                files = {
                    "file": (file_info["name"], f, "text/markdown"),
                }
                data = {
                    "relative_path": file_info["relative_path"],
                    "file_hash": file_info["hash"],
                    "file_size": file_info["size"],
                }

                async with httpx.AsyncClient(timeout=60) as client:
                    response = await client.post(
                        url,
                        headers=headers,
                        data=data,
                        files=files,
                    )
                    response.raise_for_status()
                    result = response.json()

            if result.get("code") == 0:
                logger.info(f"✅ 上传成功: {file_info['name']} ({file_info['size']} bytes)")
                return True
            else:
                logger.error(f"❌ 上传失败: {file_info['name']} - {result.get('msg', 'Unknown')}")
                return False

        except Exception as e:
            logger.error(f"❌ 上传异常: {file_info['name']} - {e}")
            return False

    async def sync_files(self, full_sync: bool = False) -> Dict:
        """
        同步文件到云端

        Args:
            full_sync: True=全量同步，False=增量同步

        Returns:
            同步结果统计
        """
        logger.info("=" * 60)
        logger.info("ArchGen Sync 开始")
        logger.info(f"本地文件夹: {self.local_folder}")
        logger.info(f"云端服务器: {self.server_url}")
        logger.info(f"同步模式: {'全量' if full_sync else '增量'}")
        logger.info("=" * 60)

        # 1. 扫描本地文件
        local_files = self.scan_local_files()
        if not local_files:
            logger.warning("没有找到需要同步的文件")
            return {"status": "no_files", "uploaded": 0, "failed": 0}

        # 2. 检测变化
        changes = self.detect_changes(local_files)
        logger.info(f"\n文件变化检测:")
        logger.info(f"  新增: {len(changes['new'])} 个")
        logger.info(f"  修改: {len(changes['modified'])} 个")
        logger.info(f"  未变化: {len(changes['unchanged'])} 个")
        logger.info(f"  删除: {len(changes['deleted'])} 个")

        # 3. 上传新增和修改的文件
        files_to_upload = changes["new"] + changes["modified"]
        if full_sync:
            files_to_upload = local_files

        uploaded = 0
        failed = 0

        for file_info in files_to_upload:
            success = await self.upload_file(file_info)
            if success:
                uploaded += 1
                # 更新同步状态
                self.sync_state["synced_files"][file_info["path"]] = {
                    "hash": file_info["hash"],
                    "size": file_info["size"],
                    "synced_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
            else:
                failed += 1

        # 4. 处理删除的文件
        for deleted_path in changes["deleted"]:
            if deleted_path in self.sync_state["synced_files"]:
                del self.sync_state["synced_files"][deleted_path]
                logger.info(f"🗑️  移除已删除文件: {deleted_path}")

        # 5. 更新统计
        self.sync_state["total_synced"] = len(self.sync_state["synced_files"])
        self._save_sync_state()

        # 6. 输出结果
        logger.info("\n" + "=" * 60)
        logger.info("同步完成")
        logger.info(f"  上传成功: {uploaded} 个")
        logger.info(f"  上传失败: {failed} 个")
        logger.info(f"  已同步总数: {self.sync_state['total_synced']} 个")
        logger.info("=" * 60)

        return {
            "status": "completed",
            "uploaded": uploaded,
            "failed": failed,
            "total_synced": self.sync_state["total_synced"],
        }

    def list_synced_files(self) -> List[Dict]:
        """列出已同步的文件"""
        synced = self.sync_state.get("synced_files", {})
        files = []
        for path, info in synced.items():
            files.append({
                "path": path,
                "name": Path(path).name,
                "size": info.get("size", 0),
                "hash": info.get("hash", ""),
                "synced_at": info.get("synced_at", ""),
            })
        return sorted(files, key=lambda x: x["name"])


async def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="ArchGen Sync - 本地文件夹同步工具")
    parser.add_argument(
        "--folder",
        type=str,
        default=ArchGenSync.DEFAULT_LOCAL_FOLDER,
        help=f"本地文件夹路径 (默认: {ArchGenSync.DEFAULT_LOCAL_FOLDER})",
    )
    parser.add_argument(
        "--server",
        type=str,
        default=ArchGenSync.DEFAULT_SERVER_URL,
        help=f"云端服务器 URL (默认: {ArchGenSync.DEFAULT_SERVER_URL})",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API Key (可选，或设置 ARCHGEN_API_KEY 环境变量)",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="全量同步（默认增量同步）",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出已同步的文件",
    )

    args = parser.parse_args()

    sync_tool = ArchGenSync(
        local_folder=args.folder,
        server_url=args.server,
        api_key=args.api_key,
    )

    if args.list:
        files = sync_tool.list_synced_files()
        if not files:
            logger.info("没有已同步的文件")
        else:
            logger.info(f"\n已同步文件 ({len(files)} 个):")
            for f in files:
                logger.info(f"  {f['name']} ({f['size']} bytes) - 同步于 {f['synced_at']}")
        return

    result = await sync_tool.sync_files(full_sync=args.full)
    logger.info(f"\n同步结果: {json.dumps(result, indent=2, ensure_ascii=False)}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
