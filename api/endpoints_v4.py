"""
V4.8.0 结构化评估引导器 API 端点（统一入口版）

V4.8.0 核心新增：
- 支持儿童背景信息（出生日期、阶段）
- 发展期待对标（基于年龄和阶段的精准诊断）

V4.3 核心修复（保留）：
- /api/v4/chat 统一指向 StructuredAssessorV4（V4.3 引擎）
- /api/v4/v43/chat 保留但标记为弃用
- 系统版本统一标识为 V4.8.0（稳定版）
"""

import logging
import time
from typing import Any, Optional

from fastapi import APIRouter, HTTPException

from app.agents.structured_assessor_v4 import StructuredAssessorV4
# from app.cloud_sync import CloudSync
from app.config import get_config
from app.llm.openai_client import OpenAIClient
from app.utils.test_db import get_database
from app.utils.analytics import track_usage

logger = logging.getLogger(__name__)

router = APIRouter()

_agent_v43: Optional[StructuredAssessorV4] = None


def get_agent_v43() -> StructuredAssessorV4:
    """
    获取 V4.8.0 结构化评估引导器实例
    
    V4.8.0 统一引擎：StructuredAssessorV4
    - 框架驱动：基于 clinical_assessment_framework.json
    - 工作流推进：BACKGROUND → CORE_ABC → DIFFERENTIAL → REPORT
    - 智能推断：环境、假设自动推断
    - V4.8.0 新增：支持儿童背景信息（出生日期、阶段）
    """
    global _agent_v43

    if _agent_v43 is None:
        config = get_config()
        llm_client = OpenAIClient(
            api_key=config.llm_api_key,
            base_url=config.llm_base_url,
            model=config.llm_model,
        )
        framework_path = "app/knowledge/clinical_assessment_framework.json"
        _agent_v43 = StructuredAssessorV4(llm_client, framework_path)
        logger.info("V4.8.0 Agent 实例已创建 - 结构化临床评估引导器（带背景信息支持）")

    return _agent_v43


@router.post(
    "/chat",
    response_model=dict[str, Any],
    summary="V4.8.0 结构化临床评估对话（带背景信息）",
    description="V4.8.0 稳定版：基于评估框架表的结构化信息收集，支持儿童背景信息（年龄、阶段）",
)
async def chat_v4(request: dict[str, Any]):
    """
    V4.8.0 对话接口 - 统一官方入口
    
    V4.8.0 核心特性：
    1. 框架驱动：每个问题对应评估框架中的明确字段
    2. 工作流推进：BACKGROUND → CORE_ABC → DIFFERENTIAL → REPORT
    3. 智能推断：根据年龄和情境自动推断环境（幼儿园/家庭/学校）
    4. 高效收敛：必填字段完成后立即触发报告
    5. 无重复追问：已填充字段不再询问
    6. V4.8.0 新增：支持儿童背景信息（出生日期、阶段），用于发展期待对标

    Args:
        request: 包含 session_id（可选）、user_input、child_profile（可选）

    Returns:
        对话响应，包含进度信息、推断环境、假设置信度
    """
    session_id = request.get("session_id")
    user_input = request.get("user_input", "").strip()
    child_profile = request.get("child_profile")  # V4.8.0 新增

    if not user_input:
        raise HTTPException(status_code=400, detail="user_input 不能为空")

    # 记录使用统计
    track_usage("chat_requested", {
        "session_id": session_id,
        "input_length": len(user_input)
    })

    start_time = time.time()
    logger.info(f"V4.8.0 收到对话：session={session_id}, input={user_input[:50]}..., profile={child_profile}")

    try:
        agent = get_agent_v43()
        # V4.8.0 新增：传递 child_profile 参数
        response = agent.process(session_id, user_input, child_profile)
        
        # 计算响应时间
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # 记录测试日志（V4.10.4 新增）
        try:
            db = get_database()
            # 如果没有 session_id，使用当前时间戳生成
            if not session_id:
                import uuid
                session_id = str(uuid.uuid4())[:8]
                logger.info(f"自动生成 session_id: {session_id}")
            # 创建/更新会话
            db.create_or_update_session(session_id, child_profile)
            # 记录对话日志
            db.add_test_log(
                session_id=session_id,
                user_input=user_input,
                ai_response=response,
                turn_number=response.get("progress", {}).get("total_turns", 1),
                response_time_ms=response_time_ms,
                stage=response.get("progress", {}).get("current_stage", "")
            )
            # 如果完成，标记会话
            if response.get("status") == "completed":
                db.complete_session(session_id, response.get("data", {}))
            logger.info(f"测试日志已记录：session={session_id}")
        except Exception as db_error:
            logger.warning(f"测试日志记录失败（不影响主功能）: {db_error}")

        progress = response.get("progress", {})
        # 记录使用统计
        track_usage("chat_completed", {
            "session_id": session_id,
            "status": response['status'],
            "turns": progress.get('total_turns', 0),
            "response_time_ms": response_time_ms
        })

        logger.info(f"V4.8.0 响应：status={response['status']}, turns={progress.get('total_turns', 'N/A')}, env={progress.get('inferred_environment', 'N/A')}")
        return response

    except Exception as e:
        logger.error(f"V4.8.0 对话失败：{e}")
        raise HTTPException(status_code=500, detail=f"对话失败：{str(e)}")


# ========== V4.3 会话管理端点 ==========

@router.get(
    "/session/{session_id}",
    response_model=dict[str, Any],
    summary="获取 V4.3 会话状态",
)
async def get_session_v43(session_id: str):
    """获取 V4.3 会话信息"""
    agent = get_agent_v43()
    session = agent.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    return {
        "session_id": session.session_id,
        "created_at": session.created_at.isoformat(),
        "current_stage": session.current_stage,
        "turn_count": session.turn_count,
        "is_complete": session.is_complete,
        "completion_rate": session.get_overall_completion_rate(agent.framework.data),
        "filled_fields": {k: v.value for k, v in session.filled_data.items() if v.value},
        "inferred_hypotheses": session.inferred_hypotheses,
    }


@router.delete(
    "/session/{session_id}",
    response_model=dict[str, Any],
    summary="清理 V4.3 会话",
)
async def delete_session_v43(session_id: str):
    """清理 V4.3 会话"""
    agent = get_agent_v43()
    success = agent.cleanup_session(session_id)

    return {
        "success": success,
        "message": "会话已清理" if success else "会话不存在",
    }


# ========== 弃用端点（保留向后兼容）==========

@router.post(
    "/v43/chat",
    response_model=dict[str, Any],
    summary="V4.3 对话（弃用，请使用 /chat）",
    description="⚠️ 此端点已弃用，请使用 /api/v4/chat",
    deprecated=True,
)
async def chat_v43_deprecated(request: dict[str, Any]):
    """V4.3 对话接口（弃用）"""
    # 重定向到主端点
    return await chat_v4(request)


# ========== V4.10.4 测试日志与反馈端点 ==========

@router.post(
    "/feedback",
    response_model=dict[str, Any],
    summary="提交用户反馈",
    description="用户对 AI 输出进行评分和反馈",
)
async def submit_feedback(request: dict[str, Any]):
    """
    提交用户反馈
    
    Args:
        request: 包含 session_id, rating(1-5), accuracy(accurate/partial/inaccurate),
                feedback_text, improvement_suggestion
    
    Returns:
        提交结果
    """
    session_id = request.get("session_id")
    rating = request.get("rating")
    accuracy = request.get("accuracy")
    feedback_text = request.get("feedback_text", "")
    improvement_suggestion = request.get("improvement_suggestion", "")
    
    if not session_id or not rating:
        raise HTTPException(status_code=400, detail="session_id 和 rating 是必填项")
    
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="rating 必须在 1-5 之间")
    
    if accuracy and accuracy not in ['accurate', 'partial', 'inaccurate']:
        raise HTTPException(status_code=400, detail="accuracy 必须是 accurate/partial/inaccurate")
    
    try:
        db = get_database()
        db.add_feedback(
            session_id=session_id,
            rating=rating,
            accuracy=accuracy or 'partial',
            feedback_text=feedback_text,
            improvement_suggestion=improvement_suggestion
        )
        logger.info(f"用户反馈已保存：session={session_id}, rating={rating}")
        return {"status": "success", "message": "感谢你的反馈！"}
    
    except Exception as e:
        logger.error(f"保存反馈失败：{e}")
        raise HTTPException(status_code=500, detail=f"保存失败：{str(e)}")


@router.get(
    "/test/logs",
    response_model=dict[str, Any],
    summary="获取测试日志（管理员用）",
    description="查询测试日志数据",
)
async def get_test_logs(session_id: str = None, limit: int = 100):
    """
    获取测试日志
    
    Args:
        session_id: 会话 ID（可选）
        limit: 返回数量限制
    
    Returns:
        测试日志列表
    """
    try:
        db = get_database()
        logs = db.get_test_report(session_id=session_id, limit=limit)
        return {
            "status": "success",
            "count": len(logs),
            "data": logs
        }
    except Exception as e:
        logger.error(f"获取测试日志失败：{e}")
        raise HTTPException(status_code=500, detail=f"查询失败：{str(e)}")


@router.get(
    "/test/feedback-summary",
    response_model=dict[str, Any],
    summary="获取反馈汇总（管理员用）",
    description="查看用户反馈统计信息",
)
async def get_feedback_summary():
    """
    获取反馈汇总统计
    
    Returns:
        反馈统计信息
    """
    try:
        db = get_database()
        summary = db.get_feedback_summary()
        return {
            "status": "success",
            "data": summary
        }
    except Exception as e:
        logger.error(f"获取反馈汇总失败：{e}")
        raise HTTPException(status_code=500, detail=f"查询失败：{str(e)}")


@router.get(
    "/admin/conversations",
    response_model=list[dict[str, Any]],
    summary="获取所有对话记录（后台管理用）",
    description="获取所有会话的完整对话记录，用于后台管理",
)
async def get_all_conversations(limit: int = 1000):
    """
    获取所有对话记录
    
    Args:
        limit: 返回数量限制
    
    Returns:
        对话记录列表
    """
    try:
        db = get_database()
        logs = db.get_test_report(limit=limit)
        return logs
    except Exception as e:
        logger.error(f"获取对话记录失败：{e}")
        raise HTTPException(status_code=500, detail=f"查询失败：{str(e)}")


@router.post(
    "/test/export",
    response_model=dict[str, Any],
    summary="导出测试数据为 CSV（管理员用）",
    description="导出所有测试日志到 CSV 文件",
)
async def export_test_data(output_path: str = "test_logs_export.csv"):
    """
    导出测试数据
    
    Args:
        output_path: 输出文件路径
    
    Returns:
        导出结果
    """
    try:
        db = get_database()
        db.export_to_csv(output_path)
        return {
            "status": "success",
            "message": f"数据已导出到：{output_path}",
            "file": output_path
        }
    except Exception as e:
        logger.error(f"导出数据失败：{e}")
        raise HTTPException(status_code=500, detail=f"导出失败：{str(e)}")


# ========== V4.11.0 用户认证端点 ==========

# @router.post(
#     "/auth/register",
#     response_model=dict[str, Any],
#     summary="用户注册",
#     description="注册新用户",
# )
# async def register(request: dict[str, Any]):
#     """
#     用户注册
#     
#     Args:
#         request: 包含 username, email, password, full_name
#     
#     Returns:
#         注册结果
#     """
#     username = request.get("username")
#     email = request.get("email")
#     password = request.get("password")
#     full_name = request.get("full_name", "")
#     
#     if not username or not email or not password:
#         raise HTTPException(status_code=400, detail="用户名、邮箱和密码是必填项")
#     
#     db = get_database()
#     
#     # 检查用户名是否已存在
#     if db.get_user_by_username(username):
#         raise HTTPException(status_code=400, detail="用户名已存在")
#     
#     # 检查邮箱是否已存在
#     if db.get_user_by_email(email):
#         raise HTTPException(status_code=400, detail="邮箱已被注册")
#     
#     # 密码哈希
#     password_hash = get_password_hash(password)
#     
#     # 创建用户
#     user_id = db.add_user(username, email, password_hash, full_name)
#     
#     logger.info(f"用户注册成功：id={user_id}, email={email}")
#     return {
#         "status": "success",
#         "message": "注册成功",
#         "user_id": user_id
#     }


# @router.post(
#     "/auth/login",
#     response_model=dict[str, Any],
#     summary="用户登录",
#     description="用户登录获取访问令牌",
# )
# async def login(request: dict[str, Any]):
#     """
#     用户登录
#     
#     Args:
#         request: 包含 email, password
#     
#     Returns:
#         登录结果和访问令牌
#     """
#     email = request.get("email")
#     password = request.get("password")
#     
#     if not email or not password:
#         raise HTTPException(status_code=400, detail="邮箱和密码是必填项")
#     
#     db = get_database()
#     
#     # 查找用户
#     user = db.get_user_by_email(email)
#     if not user:
#         raise HTTPException(status_code=401, detail="邮箱或密码错误")
#     
#     # 验证密码
#     if not verify_password(password, user["password_hash"]):
#         raise HTTPException(status_code=401, detail="邮箱或密码错误")
#     
#     # 创建访问令牌
#     access_token = create_access_token(data={"sub": str(user["id"]), "email": user["email"]})
#     
#     logger.info(f"用户登录成功：id={user['id']}, email={email}")
#     return {
#         "status": "success",
#         "message": "登录成功",
#         "access_token": access_token,
#         "user": {
#             "id": user["id"],
#             "username": user["username"],
#             "email": user["email"],
#             "full_name": user["full_name"]
#         }
#     }


# @router.post(
#     "/children",
#     response_model=dict[str, Any],
#     summary="添加儿童",
#     description="为用户添加儿童信息",
# )
# async def add_child(request: dict[str, Any]):
#     """
#     添加儿童
#     
#     Args:
#         request: 包含 user_id, name, gender, birth_date, age, notes
#     
#     Returns:
#         添加结果
#     """
#     user_id = request.get("user_id")
#     name = request.get("name")
#     gender = request.get("gender", "")
#     birth_date = request.get("birth_date", "")
#     age = request.get("age", 0)
#     notes = request.get("notes", "")
#     
#     if not user_id or not name:
#         raise HTTPException(status_code=400, detail="用户 ID 和儿童姓名是必填项")
#     
#     db = get_database()
#     
#     # 添加儿童
#     child_id = db.add_child(user_id, name, gender, birth_date, age, notes)
#     
#     logger.info(f"儿童添加成功：id={child_id}, name={name}")
#     return {
#         "status": "success",
#         "message": "儿童添加成功",
#         "child_id": child_id
#     }


# @router.get(
#     "/children/{user_id}",
#     response_model=dict[str, Any],
#     summary="获取用户的儿童列表",
#     description="获取指定用户的所有儿童信息",
# )
# async def get_children(user_id: int):
#     """
#     获取用户的儿童列表
#     
#     Args:
#         user_id: 用户 ID
#     
#     Returns:
#         儿童列表
#     """
#     db = get_database()
#     children = db.get_children_by_user_id(user_id)
#     
#     return {
#         "status": "success",
#         "children": children
#     }


# @router.get(
#     "/sessions/{user_id}",
#     response_model=dict[str, Any],
#     summary="获取用户的会话列表",
#     description="获取指定用户的所有会话记录",
# )
# async def get_user_sessions(user_id: int, limit: int = 100):
#     """
#     获取用户的会话列表
#     
#     Args:
#         user_id: 用户 ID
#         limit: 返回数量限制
#     
#     Returns:
#         会话列表
#     """
#     db = get_database()
#     sessions = db.get_sessions_by_user_id(user_id, limit)
#     
#     return {
#         "status": "success",
#         "sessions": sessions
#     }


# ========== V4.11.0 云同步端点 ==========

# @router.post(
#     "/cloud/backup",
#     response_model=dict[str, Any],
#     summary="备份用户数据",
#     description="将用户数据备份到云端",
# )
# async def backup_user_data(request: dict[str, Any]):
#     """
#     备份用户数据
#     
#     Args:
#         request: 包含 user_id
#     
#     Returns:
#         备份结果
#     """
#     user_id = request.get("user_id")
#     
#     if not user_id:
#         raise HTTPException(status_code=400, detail="用户 ID 是必填项")
#     
#     try:
#         # 获取用户数据
#         db = get_database()
#         children = db.get_children_by_user_id(user_id)
#         sessions = db.get_sessions_by_user_id(user_id)
#         
#         # 准备备份数据
#         backup_data = {
#             "children": children,
#             "sessions": sessions
#         }
#         
#         # 备份到云端
#         cloud_sync = CloudSync()
#         backup_file = cloud_sync.backup_user_data(user_id, backup_data)
#         
#         logger.info(f"用户数据备份成功：user_id={user_id}")
#         return {
#             "status": "success",
#             "message": "数据备份成功",
#             "backup_file": backup_file
#         }
#     except Exception as e:
#         logger.error(f"备份用户数据失败：{e}")
#         raise HTTPException(status_code=500, detail=f"备份失败：{str(e)}")


# @router.post(
#     "/cloud/restore",
#     response_model=dict[str, Any],
#     summary="恢复用户数据",
#     description="从云端恢复用户数据",
# )
# async def restore_user_data(request: dict[str, Any]):
#     """
#     恢复用户数据
#     
#     Args:
#         request: 包含 user_id, backup_file
#     
#     Returns:
#         恢复结果
#     """
#     user_id = request.get("user_id")
#     backup_file = request.get("backup_file")
#     
#     if not user_id or not backup_file:
#         raise HTTPException(status_code=400, detail="用户 ID 和备份文件路径是必填项")
#     
#     try:
#         # 从云端恢复数据
#         cloud_sync = CloudSync()
#         restored_data = cloud_sync.restore_user_data(user_id, backup_file)
#         
#         logger.info(f"用户数据恢复成功：user_id={user_id}")
#         return {
#             "status": "success",
#             "message": "数据恢复成功",
#             "data": restored_data
#         }
#     except Exception as e:
#         logger.error(f"恢复用户数据失败：{e}")
#         raise HTTPException(status_code=500, detail=f"恢复失败：{str(e)}")


# @router.get(
#     "/cloud/backups/{user_id}",
#     response_model=dict[str, Any],
#     summary="列出用户备份",
#     description="列出用户的所有云端备份",
# )
# async def list_user_backups(user_id: int):
#     """
#     列出用户备份
#     
#     Args:
#         user_id: 用户 ID
#     
#     Returns:
#         备份列表
#     """
#     try:
#         cloud_sync = CloudSync()
#         backups = cloud_sync.list_user_backups(user_id)
#         
#         return {
#             "status": "success",
#             "backups": backups
#         }
#     except Exception as e:
#         logger.error(f"列出用户备份失败：{e}")
#         raise HTTPException(status_code=500, detail=f"列出备份失败：{str(e)}")


# @router.delete(
#     "/cloud/backup",
#     response_model=dict[str, Any],
#     summary="删除备份",
#     description="删除指定的云端备份",
# )
# async def delete_backup(request: dict[str, Any]):
#     """
#     删除备份
#     
#     Args:
#         request: 包含 backup_file
#     
#     Returns:
#         删除结果
#     """
#     backup_file = request.get("backup_file")
#     
#     if not backup_file:
#         raise HTTPException(status_code=400, detail="备份文件路径是必填项")
#     
#     try:
#         cloud_sync = CloudSync()
#         success = cloud_sync.delete_backup(backup_file)
#         
#         logger.info(f"备份文件删除成功：{backup_file}")
#         return {
#             "status": "success",
#             "message": "备份删除成功"
#         }
#     except Exception as e:
#         logger.error(f"删除备份文件失败：{e}")
#         raise HTTPException(status_code=500, detail=f"删除失败：{str(e)}")


# ========== 健康检查端点 ==========

@router.get(
    "/health",
    response_model=dict[str, Any],
    summary="健康检查",
    description="检查服务健康状态",
)
async def health_check():
    """
    健康检查
    
    Returns:
        健康状态
    """
    return {
        "status": "ok",
        "version": "V6.1.0"
    }

# ========== 核心分析端点 ==========

@router.post(
    "/analyze",
    response_model=dict[str, Any],
    summary="行为分析",
    description="分析行为并生成报告",
)
async def analyze(request: dict[str, Any]):
    """
    行为分析
    
    Args:
        request: 包含 session_id, user_input, child_profile, records, context
    
    Returns:
        分析结果
    """
    session_id = request.get("session_id")
    user_input = request.get("user_input", "").strip()
    child_profile = request.get("child_profile")
    records = request.get("records")
    context = request.get("context", "")

    # 直接处理 records 格式的请求
    if records or context:
        # 构建描述
        descriptions = []
        
        # 处理 records
        if records and isinstance(records, list):
            for record in records:
                if isinstance(record, dict):
                    ant = record.get("antecedent", "")
                    beh = record.get("behavior", "")
                    cons = record.get("consequence", "")
                    if ant or beh or cons:
                        descriptions.append(f"情境：{ant}，行为：{beh}，结果：{cons}")
        
        # 添加 context
        if context:
            descriptions.append(f"背景：{context}")
        
        # 构建 user_input
        if descriptions:
            user_input = "\n".join(descriptions)

    # 确保有输入
    if not user_input:
        raise HTTPException(status_code=400, detail="请提供 user_input 或 records 和 context")

    # 记录使用统计
    track_usage("analyze_requested", {
        "session_id": session_id,
        "has_records": bool(records),
        "has_context": bool(context)
    })

    try:
        agent = get_agent_v43()
        response = agent.process(session_id, user_input, child_profile)
        
        # 记录使用统计
        track_usage("analyze_completed", {
            "session_id": session_id,
            "status": response.get('status')
        })
        
        # 检查是否完成
        if response.get("status") == "completed" and response.get("data"):
            # 提取报告和干预计划
            data = response.get("data")
            report = data.get("report", {})
            intervention_plan = data.get("intervention_plan", {})
            
            # 确保返回正确的格式，包含完整的上下文数据
            return {
                "context": data.get("context", ""),
                "child_behavior": data.get("child_behavior", ""),
                "others_response": data.get("others_response", ""),
                "report": report,
                "intervention_plan": intervention_plan
            }
        
        return response
    except Exception as e:
        logger.error(f"分析失败：{e}")
        raise HTTPException(status_code=500, detail=f"分析失败：{str(e)}")

# ========== V4.11.0 数据管理端点 ==========

@router.get(
    "/data/search/{user_id}",
    response_model=dict[str, Any],
    summary="搜索会话",
    description="根据关键词搜索用户的会话",
)
async def search_sessions(user_id: int, keyword: str, limit: int = 100):
    """
    搜索会话
    
    Args:
        user_id: 用户 ID
        keyword: 搜索关键词
        limit: 返回数量限制
    
    Returns:
        匹配的会话列表
    """
    db = get_database()
    sessions = db.search_sessions(user_id, keyword, limit)
    
    return {
        "status": "success",
        "sessions": sessions
    }


@router.get(
    "/data/filter/{user_id}",
    response_model=dict[str, Any],
    summary="筛选会话",
    description="根据条件筛选用户的会话",
)
async def filter_sessions(user_id: int, child_id: int = None, status: str = None, limit: int = 100):
    """
    筛选会话
    
    Args:
        user_id: 用户 ID
        child_id: 儿童 ID（可选）
        status: 会话状态（可选）
        limit: 返回数量限制
    
    Returns:
        筛选后的会话列表
    """
    db = get_database()
    sessions = db.filter_sessions(user_id, child_id, status, limit)
    
    return {
        "status": "success",
        "sessions": sessions
    }


@router.post(
    "/data/export",
    response_model=dict[str, Any],
    summary="导出用户数据",
    description="导出用户的所有数据",
)
async def export_user_data(request: dict[str, Any]):
    """
    导出用户数据
    
    Args:
        request: 包含 user_id, format
    
    Returns:
        导出结果
    """
    user_id = request.get("user_id")
    output_format = request.get("format", "csv")
    
    if not user_id:
        raise HTTPException(status_code=400, detail="用户 ID 是必填项")
    
    if output_format not in ["csv", "json"]:
        raise HTTPException(status_code=400, detail="格式必须是 csv 或 json")
    
    try:
        db = get_database()
        output_path = db.export_user_data(user_id, output_format)
        
        logger.info(f"用户数据导出成功：user_id={user_id}, format={output_format}")
        return {
            "status": "success",
            "message": "数据导出成功",
            "file": output_path
        }
    except Exception as e:
        logger.error(f"导出用户数据失败：{e}")
        raise HTTPException(status_code=500, detail=f"导出失败：{str(e)}")
