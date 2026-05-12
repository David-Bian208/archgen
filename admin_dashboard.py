"""
行为观察助手 - 中台管理服务 V6.4.2 (端口 8000)
界面：紫色顶栏 + 统计卡片 + 表格列表 + 分页
功能：显示所有对话，包括未生成回答的
"""

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
import sqlite3
import os
import csv
import io
from datetime import datetime

app = FastAPI(title="行为观察助手 - 中台管理")

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'conversations.db')

def get_db():
    """获取数据库连接"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            response_time_seconds REAL,
            scene_type TEXT,
            hypothesis TEXT
        )
    """)
    conn.commit()
    return conn

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """中台首页 - 紫色顶栏 + 统计卡片 + 表格列表 + 分页"""
    return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>行为观察助手 - 中台管理</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f5f7fa; color: #333; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px 30px; }
        .header h1 { font-size: 20px; }
        .header p { opacity: 0.8; margin-top: 5px; font-size: 14px; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px; }
        .stat-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
        .stat-card h3 { font-size: 32px; color: #667eea; }
        .stat-card p { color: #666; margin-top: 5px; font-size: 14px; }
        .controls { background: white; padding: 15px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); display: flex; gap: 10px; align-items: center; }
        .controls input { flex: 1; padding: 10px 15px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; }
        .controls select { padding: 10px 15px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; }
        .controls button { padding: 10px 20px; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; color: white; }
        .controls .search-btn { background: #667eea; }
        .controls .search-btn:hover { background: #5a6fd6; }
        .controls .export-btn { background: #4caf50; }
        .controls .export-btn:hover { background: #43a047; }
        table { width: 100%; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
        th { background: #f8f9fa; padding: 15px; text-align: left; font-weight: 600; font-size: 14px; color: #555; }
        td { padding: 12px 15px; border-top: 1px solid #eee; vertical-align: top; font-size: 14px; }
        tr:hover { background: #f8f9fa; }
        .time-cell { color: #888; font-size: 12px; white-space: nowrap; }
        .message-cell { max-width: 350px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; cursor: pointer; }
        .message-cell:hover { white-space: normal; overflow: visible; }
        .badge { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 500; }
        .badge-A { background: #e3f2fd; color: #1976d2; }
        .badge-B { background: #fff3e0; color: #f57c00; }
        .badge-C { background: #e8f5e9; color: #388e3c; }
        .badge-D { background: #fce4ec; color: #c2185b; }
        .badge-E { background: #f3e5f5; color: #7b1fa2; }
        .no-answer { color: #ff6b6b; font-size: 12px; }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; }
        .modal.show { display: flex; align-items: center; justify-content: center; }
        .modal-content { background: white; border-radius: 12px; padding: 25px; max-width: 600px; width: 90%; max-height: 80vh; overflow-y: auto; }
        .modal-content h3 { margin-bottom: 15px; color: #667eea; }
        .modal-content pre { white-space: pre-wrap; line-height: 1.6; }
        .close-btn { float: right; background: none; border: none; font-size: 24px; cursor: pointer; color: #999; }
        .pagination { display: flex; justify-content: center; align-items: center; gap: 15px; padding: 20px; }
        .pagination button { padding: 8px 16px; border: 1px solid #ddd; background: white; border-radius: 6px; cursor: pointer; font-size: 14px; }
        .pagination button:hover { background: #f0f0f0; }
        .pagination button:disabled { opacity: 0.5; cursor: not-allowed; }
    </style>
</head>
<body>
    <div class="header">
        <h1>中台管理</h1>
        <p>查看所有问答数据，支持搜索、筛选和导出</p>
    </div>
    
    <div class="container">
        <div class="stats" id="stats">
            <div class="stat-card"><h3 id="total">-</h3><p>总对话数</p></div>
            <div class="stat-card"><h3 id="today">-</h3><p>今日对话</p></div>
            <div class="stat-card"><h3 id="avgTime">-</h3><p>平均响应(秒)</p></div>
            <div class="stat-card"><h3 id="users">-</h3><p>用户数</p></div>
        </div>
        
        <div class="controls">
            <input type="text" id="searchInput" placeholder="搜索问题或回答内容...">
            <select id="sceneFilter">
                <option value="">全部场景</option>
                <option value="A">A类</option>
                <option value="B">B类</option>
                <option value="C">C类</option>
                <option value="D">D类</option>
                <option value="E">E类</option>
            </select>
            <button class="search-btn" onclick="loadData(1)">搜索</button>
            <button class="export-btn" onclick="exportCSV()">导出CSV</button>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>时间</th>
                    <th>场景</th>
                    <th>用户问题</th>
                    <th>助手回答</th>
                    <th>耗时(秒)</th>
                </tr>
            </thead>
            <tbody id="tableBody">
                <tr><td colspan="5" style="text-align:center;padding:40px;">加载中...</td></tr>
            </tbody>
        </table>
        
        <div class="pagination">
            <button id="prevBtn" onclick="changePage(-1)">上一页</button>
            <span id="pageInfo">1 / 1</span>
            <button id="nextBtn" onclick="changePage(1)">下一页</button>
        </div>
    </div>
    
    <div class="modal" id="modal">
        <div class="modal-content">
            <button class="close-btn" onclick="closeModal()">&times;</button>
            <h3 id="modalTitle">详细内容</h3>
            <pre id="modalBody"></pre>
        </div>
    </div>

    <script>
        let currentPage = 1;
        let totalPages = 1;
        const pageSize = 20;
        
        async function loadStats() {
            const res = await fetch('/api/stats');
            const data = await res.json();
            document.getElementById('total').textContent = data.total;
            document.getElementById('today').textContent = data.today;
            document.getElementById('avgTime').textContent = data.avg_time ? data.avg_time.toFixed(1) : '-';
            document.getElementById('users').textContent = data.users;
        }
        
        async function loadData(page) {
            currentPage = page;
            const search = document.getElementById('searchInput').value;
            const scene = document.getElementById('sceneFilter').value;
            
            const params = new URLSearchParams({ page, limit: pageSize, search, scene });
            const res = await fetch(`/api/conversations?${params}`);
            const data = await res.json();
            
            totalPages = Math.ceil(data.total / pageSize) || 1;
            document.getElementById('pageInfo').textContent = `${currentPage} / ${totalPages}`;
            document.getElementById('prevBtn').disabled = currentPage <= 1;
            document.getElementById('nextBtn').disabled = currentPage >= totalPages;
            
            const tbody = document.getElementById('tableBody');
            if (!data.items.length) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:40px;">暂无数据</td></tr>';
                return;
            }
            
            tbody.innerHTML = data.items.map(item => `
                <tr>
                    <td class="time-cell">${item.timestamp}</td>
                    <td>${item.scene_type ? '<span class="badge badge-' + item.scene_type + '">' + item.scene_type + '</span>' : '-'}</td>
                    <td class="message-cell" onclick="showDetail(${item.id}, 'user')">${escapeHtml((item.user_message || '').substring(0, 50))}${(item.user_message || '').length > 50 ? '...' : ''}</td>
                    <td class="message-cell" onclick="showDetail(${item.id}, 'assistant')">
                        ${item.assistant_response ? escapeHtml(item.assistant_response.substring(0, 50)) + (item.assistant_response.length > 50 ? '...' : '') : '<span class="no-answer">未生成回答</span>'}
                    </td>
                    <td>${item.response_time ? item.response_time.toFixed(1) : '-'}</td>
                </tr>
            `).join('');
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        function changePage(delta) {
            const newPage = currentPage + delta;
            if (newPage >= 1 && newPage <= totalPages) {
                loadData(newPage);
            }
        }
        
        async function showDetail(id, type) {
            const res = await fetch(`/api/conversations/${id}`);
            const data = await res.json();
            document.getElementById('modalTitle').textContent = type === 'user' ? '用户问题' : '助手回答';
            const content = type === 'user' ? data.user_message : data.assistant_response;
            document.getElementById('modalBody').textContent = content || '(无内容)';
            document.getElementById('modal').classList.add('show');
        }
        
        function closeModal() {
            document.getElementById('modal').classList.remove('show');
        }
        
        async function exportCSV() {
            const search = document.getElementById('searchInput').value;
            const scene = document.getElementById('sceneFilter').value;
            const params = new URLSearchParams({ export: 'true', search, scene });
            window.location.href = `/api/export?${params}`;
        }
        
        // 初始化
        loadStats();
        loadData(1);
        
        // 回车搜索
        document.getElementById('searchInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') loadData(1);
        });
        
        // 点击模态框外部关闭
        document.getElementById('modal').addEventListener('click', (e) => {
            if (e.target.id === 'modal') closeModal();
        });
    </script>
</body>
</html>
"""

@app.get("/api/stats")
async def get_stats():
    """获取统计数据 - 以用户提问为准"""
    conn = get_db()
    
    # 总对话数（以用户提问为准，包括未生成回答的）
    total = conn.execute("SELECT COUNT(*) FROM conversations WHERE role='user'").fetchone()[0]
    
    # 今日对话数
    today = datetime.now().strftime("%Y-%m-%d")
    today_count = conn.execute("SELECT COUNT(*) FROM conversations WHERE role='user' AND date(timestamp) = ?", (today,)).fetchone()[0]
    
    # 平均响应时间（只计算有回答的）
    avg_time_result = conn.execute("SELECT AVG(response_time_seconds) FROM conversations WHERE role='assistant' AND response_time_seconds IS NOT NULL").fetchone()[0]
    avg_time = avg_time_result if avg_time_result else 0
    
    # 用户数（不同的 session_id）
    users = conn.execute("SELECT COUNT(DISTINCT session_id) FROM conversations").fetchone()[0]
    
    conn.close()
    
    return {
        "total": total,
        "today": today_count,
        "avg_time": avg_time,
        "users": users
    }

@app.get("/api/conversations")
async def get_conversations(page: int = 1, limit: int = 20, search: str = "", scene: str = "", export: str = ""):
    """获取对话列表 - 显示所有用户输入，包括未生成回答的"""
    conn = get_db()
    
    # 获取所有用户消息
    user_msgs = conn.execute("""
        SELECT id, session_id, content as user_message, timestamp 
        FROM conversations 
        WHERE role = 'user'
        ORDER BY id DESC
    """).fetchall()
    
    items = []
    for um in user_msgs:
        # 搜索过滤
        if search:
            match_user = search.lower() in um["user_message"].lower()
            # 也检查是否有匹配的助手回答
            assistant_check = conn.execute(
                "SELECT content FROM conversations WHERE session_id = ? AND role = 'assistant' AND id > ? ORDER BY id ASC LIMIT 1",
                (um["session_id"], um["id"])
            ).fetchone()
            match_assistant = assistant_check and search.lower() in assistant_check["content"].lower()
            if not match_user and not match_assistant:
                continue
        
        # 获取对应的助手回答（同一 session 中 ID 较大的 assistant 记录）
        assistant = conn.execute(
            "SELECT content, timestamp, response_time_seconds, scene_type, hypothesis FROM conversations WHERE session_id = ? AND role = 'assistant' AND id > ? ORDER BY id ASC LIMIT 1",
            (um["session_id"], um["id"])
        ).fetchone()
        
        # 场景筛选 - 未生成回答的对话也能显示
        if scene:
            if assistant and assistant["scene_type"] and assistant["scene_type"].startswith(scene):
                pass  # 匹配场景，保留
            elif not assistant or not assistant["scene_type"]:
                # 未生成回答的对话，用户选择特定场景时不显示
                continue
            else:
                continue
        
        items.append({
            "id": um["id"],
            "session_id": um["session_id"],
            "user_message": um["user_message"],
            "assistant_response": assistant["content"] if assistant else None,
            "timestamp": um["timestamp"],
            "response_time": assistant["response_time_seconds"] if assistant else None,
            "scene_type": assistant["scene_type"] if assistant else None,
            "hypothesis": assistant["hypothesis"] if assistant else None
        })
    
    total = len(items)
    offset = (page - 1) * limit
    items = items[offset:offset + limit]
    
    conn.close()
    
    return {
        "total": total,
        "items": items
    }

@app.get("/api/conversations/{conversation_id}")
async def get_conversation_detail(conversation_id: int):
    """获取单条对话详情"""
    conn = get_db()
    
    # 获取用户问题
    user = conn.execute("SELECT * FROM conversations WHERE id = ? AND role = 'user'", (conversation_id,)).fetchone()
    
    if not user:
        return {"error": "未找到"}
    
    # 获取对应的助手回答
    assistant = conn.execute(
        "SELECT * FROM conversations WHERE session_id = ? AND role = 'assistant' AND id > ? ORDER BY id ASC LIMIT 1",
        (user["session_id"], conversation_id)
    ).fetchone()
    
    conn.close()
    
    return {
        "user_message": user["content"],
        "assistant_response": assistant["content"] if assistant else None,
        "timestamp": user["timestamp"],
        "response_time": assistant["response_time_seconds"] if assistant else None,
        "scene_type": assistant["scene_type"] if assistant else None,
        "hypothesis": assistant["hypothesis"] if assistant else None
    }

@app.get("/api/export")
async def export_csv(search: str = "", scene: str = ""):
    """导出 CSV"""
    conn = get_db()
    
    # 获取所有用户消息
    user_msgs = conn.execute("""
        SELECT id, session_id, content as user_message, timestamp 
        FROM conversations 
        WHERE role = 'user'
        ORDER BY id DESC
    """).fetchall()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["时间", "场景类型", "假设", "用户问题", "助手回答", "响应时间(秒)"])
    
    for um in user_msgs:
        assistant = conn.execute(
            "SELECT content, response_time_seconds, scene_type, hypothesis FROM conversations WHERE session_id = ? AND role = 'assistant' AND id > ? ORDER BY id ASC LIMIT 1",
            (um["session_id"], um["id"])
        ).fetchone()
        
        # 搜索过滤
        if search:
            user_match = search.lower() in um["user_message"].lower()
            assistant_match = assistant and search.lower() in assistant["content"].lower()
            if not user_match and not assistant_match:
                continue
        
        # 场景筛选
        if scene:
            if not assistant or not assistant["scene_type"] or not assistant["scene_type"].startswith(scene):
                continue
        
        writer.writerow([
            um["timestamp"],
            assistant["scene_type"] if assistant else "",
            assistant["hypothesis"] if assistant else "",
            um["user_message"],
            assistant["content"] if assistant else "(未生成回答)",
            assistant["response_time_seconds"] if assistant else ""
        ])
    
    conn.close()
    
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=conversations.csv"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
