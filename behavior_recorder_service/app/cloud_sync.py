"""
数据云同步模块

包含数据备份、恢复和同步功能
"""

import logging
import os
import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class CloudSync:
    """云同步管理类"""
    
    def __init__(self, bucket_name: str = "behavior-recorder-service"):
        """
        初始化云同步
        
        Args:
            bucket_name: S3 存储桶名称
        """
        self.bucket_name = bucket_name
        self.s3 = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION", "us-east-1")
        )
        logger.info("云同步服务初始化完成")
    
    def backup_user_data(self, user_id: int, data: Dict[str, Any]) -> str:
        """
        备份用户数据到云端
        
        Args:
            user_id: 用户 ID
            data: 要备份的数据
            
        Returns:
            备份文件路径
        """
        try:
            # 创建备份文件
            backup_data = {
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "data": data
            }
            
            # 生成备份文件名
            backup_filename = f"backups/user_{user_id}/{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # 上传到 S3
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=backup_filename,
                Body=json.dumps(backup_data, ensure_ascii=False),
                ContentType="application/json"
            )
            
            logger.info(f"用户数据备份成功：user_id={user_id}, file={backup_filename}")
            return backup_filename
        except Exception as e:
            logger.error(f"备份用户数据失败：{e}")
            raise
    
    def restore_user_data(self, user_id: int, backup_filename: str) -> Dict[str, Any]:
        """
        从云端恢复用户数据
        
        Args:
            user_id: 用户 ID
            backup_filename: 备份文件路径
            
        Returns:
            恢复的数据
        """
        try:
            # 从 S3 下载备份文件
            response = self.s3.get_object(
                Bucket=self.bucket_name,
                Key=backup_filename
            )
            
            # 读取并解析数据
            backup_data = json.loads(response["Body"].read())
            
            # 验证用户 ID
            if backup_data["user_id"] != user_id:
                raise ValueError("备份文件与用户不匹配")
            
            logger.info(f"用户数据恢复成功：user_id={user_id}, file={backup_filename}")
            return backup_data["data"]
        except Exception as e:
            logger.error(f"恢复用户数据失败：{e}")
            raise
    
    def list_user_backups(self, user_id: int) -> List[str]:
        """
        列出用户的所有备份
        
        Args:
            user_id: 用户 ID
            
        Returns:
            备份文件路径列表
        """
        try:
            prefix = f"backups/user_{user_id}/"
            response = self.s3.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            backups = []
            if "Contents" in response:
                for obj in response["Contents"]:
                    backups.append(obj["Key"])
            
            # 按时间倒序排序
            backups.sort(reverse=True)
            
            logger.info(f"列出用户备份成功：user_id={user_id}, count={len(backups)}")
            return backups
        except Exception as e:
            logger.error(f"列出用户备份失败：{e}")
            raise
    
    def delete_backup(self, backup_filename: str) -> bool:
        """
        删除备份文件
        
        Args:
            backup_filename: 备份文件路径
            
        Returns:
            是否删除成功
        """
        try:
            self.s3.delete_object(
                Bucket=self.bucket_name,
                Key=backup_filename
            )
            
            logger.info(f"备份文件删除成功：{backup_filename}")
            return True
        except Exception as e:
            logger.error(f"删除备份文件失败：{e}")
            raise
