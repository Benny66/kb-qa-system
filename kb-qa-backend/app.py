"""
Flask 主应用   
接口列表：
  POST   /api/auth/login              用户登录
  GET    /api/auth/me                 获取当前用户信息

  GET    /api/kb                      获取知识库列表
  POST   /api/kb/upload               上传 TXT 知识库
  DELETE /api/kb/<kb_id>              删除知识库

  POST   /api/chat                    AI 问答
  GET    /api/chat/history            获取问答历史
  DELETE /api/chat/history/<id>       删除单条历史
"""

import os
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, request, jsonify
from sqlalchemy import text
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from models import db, User, KnowledgeBase, ChatSession, ChatHistory
from ai_service import ask_question

# ── 加载环境变量 ──────────────────────────────────────────────────────────────
load_dotenv()

# ── 应用初始化 ────────────────────────────────────────────────────────────────
app = Flask(__name__)

# 跨域配置（允许前端 localhost:5173 访问）
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

# 数据库配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(BASE_DIR, 'kb_qa.db')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# JWT 配置
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "fallback-secret-key")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False  # Token 不过期（简化版）

# 文件上传配置
UPLOAD_FOLDER = os.path.join(BASE_DIR, os.getenv("UPLOAD_FOLDER", "uploads"))
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 最大 10MB

# ── 插件初始化 ────────────────────────────────────────────────────────────────
db.init_app(app)
jwt = JWTManager(app)


# ── 工具函数 ──────────────────────────────────────────────────────────────────
def success(data=None, msg="success", code=200):
    """统一成功响应"""
    resp = {"code": code, "msg": msg}
    if data is not None:
        resp["data"] = data
    return jsonify(resp), code


def fail(msg="error", code=400):
    """统一失败响应"""
    return jsonify({"code": code, "msg": msg}), code


def allowed_file(filename: str) -> bool:
    """只允许上传 TXT 文件"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() == "txt"


def get_current_user() -> User | None:
    """根据 JWT 获取当前用户对象"""
    user_id = get_jwt_identity()
    return db.session.get(User, int(user_id))


def generate_session_title(question: str) -> str:
    """根据首轮问题生成会话标题。"""
    title = (question or "").strip().replace("\n", " ")
    if not title:
        return "新对话"
    return title[:30] + ("..." if len(title) > 30 else "")


def ensure_chat_schema():
    """兼容旧版 SQLite：补齐会话表和 session_id 字段。"""
    with db.engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                kb_id INTEGER NOT NULL,
                title VARCHAR(200) NOT NULL DEFAULT '新对话',
                created_at DATETIME,
                updated_at DATETIME,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(kb_id) REFERENCES knowledge_bases(id)
            )
        """))

        columns = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(chat_histories)")).fetchall()
        }
        if "session_id" not in columns:
            conn.execute(text("ALTER TABLE chat_histories ADD COLUMN session_id INTEGER"))


def build_session_history_messages(session_id: int, limit: int = 5) -> list[dict]:
    """从数据库中读取会话最近几轮历史，拼装为模型可用的 messages。"""
    records = (
        ChatHistory.query
        .filter_by(session_id=session_id)
        .order_by(ChatHistory.created_at.asc())
        .all()
    )[-limit:]

    messages = []
    for item in records:
        messages.append({"role": "user", "content": item.question})
        messages.append({"role": "assistant", "content": item.answer})
    return messages


# ── 数据库初始化 & 预置账号 ───────────────────────────────────────────────────
def init_db():
    """创建表并预置默认账号"""
    db.create_all()
    ensure_chat_schema()

    # 预置账号列表（用户名: 密码）
    preset_users = {
        "admin": "admin123",
        "demo": "demo123",
    }

    for username, password in preset_users.items():
        if not User.query.filter_by(username=username).first():
            user = User(
                username=username,
                password_hash=generate_password_hash(password),
            )
            db.session.add(user)

    db.session.commit()
    print("✅ 数据库初始化完成，预置账号：admin/admin123, demo/demo123")


# ══════════════════════════════════════════════════════════════════════════════
# 认证接口
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/auth/login", methods=["POST"])
def login():
    """
    用户登录
    Body: { "username": "admin", "password": "admin123" }
    """
    data = request.get_json()
    if not data:
        return fail("请求体不能为空")

    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return fail("用户名和密码不能为空")

    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return fail("用户名或密码错误", 401)

    token = create_access_token(identity=str(user.id))
    return success({
        "token": token,
        "user": user.to_dict(),
    }, "登录成功")


@app.route("/api/auth/me", methods=["GET"])
@jwt_required()
def get_me():
    """获取当前登录用户信息"""
    user = get_current_user()
    if not user:
        return fail("用户不存在", 404)
    return success(user.to_dict())


# ══════════════════════════════════════════════════════════════════════════════
# 知识库接口
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/kb", methods=["GET"])
@jwt_required()
def list_kb():
    """获取当前用户的知识库列表"""
    user = get_current_user()
    kbs = (
        KnowledgeBase.query
        .filter_by(user_id=user.id)
        .order_by(KnowledgeBase.created_at.desc())
        .all()
    )
    return success([kb.to_dict() for kb in kbs])


@app.route("/api/kb/upload", methods=["POST"])
@jwt_required()
def upload_kb():
    """
    上传 TXT 知识库文件
    Form-data: file=<TXT文件>
    """
    user = get_current_user()

    if "file" not in request.files:
        return fail("未找到上传文件，字段名应为 file")

    file = request.files["file"]
    if file.filename == "":
        return fail("文件名不能为空")

    if not allowed_file(file.filename):
        return fail("只支持上传 .txt 格式文件")

    # 生成唯一文件名，防止冲突
    original_name = file.filename
    safe_name = secure_filename(original_name)
    unique_filename = f"{uuid.uuid4().hex}_{safe_name}"
    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)

    file.save(file_path)

    # 统计文件信息
    file_size = os.path.getsize(file_path)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            char_count = len(f.read())
    except UnicodeDecodeError:
        with open(file_path, "r", encoding="gbk", errors="replace") as f:
            char_count = len(f.read())

    # 知识库名称：去掉扩展名
    kb_name = os.path.splitext(original_name)[0]

    kb = KnowledgeBase(
        user_id=user.id,
        name=kb_name,
        filename=unique_filename,
        file_path=file_path,
        file_size=file_size,
        char_count=char_count,
    )
    db.session.add(kb)
    db.session.commit()

    return success(kb.to_dict(), "知识库上传成功", 201)


@app.route("/api/kb/<int:kb_id>", methods=["DELETE"])
@jwt_required()
def delete_kb(kb_id):
    """删除知识库（同时删除文件和相关历史）"""
    user = get_current_user()
    kb = KnowledgeBase.query.filter_by(id=kb_id, user_id=user.id).first()

    if not kb:
        return fail("知识库不存在或无权限", 404)

    # 删除物理文件
    if os.path.exists(kb.file_path):
        os.remove(kb.file_path)

    # 删除关联会话和历史
    sessions = ChatSession.query.filter_by(kb_id=kb_id, user_id=user.id).all()
    for session in sessions:
        db.session.delete(session)

    ChatHistory.query.filter_by(kb_id=kb_id, user_id=user.id).delete()

    db.session.delete(kb)
    db.session.commit()

    return success(msg="知识库已删除")


# ══════════════════════════════════════════════════════════════════════════════
# 问答接口
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/chat/sessions", methods=["GET"])
@jwt_required()
def list_chat_sessions():
    """获取会话列表。Query: ?kb_id=1&page=1&per_page=20"""
    user = get_current_user()

    kb_id = request.args.get("kb_id", type=int)
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    query = ChatSession.query.filter_by(user_id=user.id)
    if kb_id:
        query = query.filter_by(kb_id=kb_id)

    pagination = (
        query
        .order_by(ChatSession.updated_at.desc(), ChatSession.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return success({
        "items": [item.to_dict() for item in pagination.items],
        "total": pagination.total,
        "page": page,
        "per_page": per_page,
        "pages": pagination.pages,
    })


@app.route("/api/chat/sessions", methods=["POST"])
@jwt_required()
def create_chat_session():
    """新建会话。Body: { "kb_id": 1, "title": "可选标题" }"""
    user = get_current_user()
    data = request.get_json() or {}

    kb_id = data.get("kb_id")
    title = (data.get("title") or "").strip()

    if not kb_id:
        return fail("请指定知识库 kb_id")

    kb = KnowledgeBase.query.filter_by(id=kb_id, user_id=user.id).first()
    if not kb:
        return fail("知识库不存在或无权限", 404)

    session = ChatSession(
        user_id=user.id,
        kb_id=kb_id,
        title=title or "新对话",
    )
    db.session.add(session)
    db.session.commit()

    return success(session.to_dict(), "会话创建成功", 201)


@app.route("/api/chat/sessions/<int:session_id>", methods=["GET"])
@jwt_required()
def get_chat_session_detail(session_id):
    """获取单个会话详情及消息列表。"""
    user = get_current_user()
    session = ChatSession.query.filter_by(id=session_id, user_id=user.id).first()

    if not session:
        return fail("会话不存在或无权限", 404)

    messages = (
        ChatHistory.query
        .filter_by(session_id=session_id, user_id=user.id)
        .order_by(ChatHistory.created_at.asc())
        .all()
    )

    return success({
        **session.to_dict(),
        "messages": [item.to_dict() for item in messages],
    })


@app.route("/api/chat/sessions/<int:session_id>", methods=["DELETE"])
@jwt_required()
def delete_chat_session(session_id):
    """删除会话及其全部消息。"""
    user = get_current_user()
    session = ChatSession.query.filter_by(id=session_id, user_id=user.id).first()

    if not session:
        return fail("会话不存在或无权限", 404)

    db.session.delete(session)
    db.session.commit()
    return success(msg="会话已删除")


@app.route("/api/chat", methods=["POST"])
@jwt_required()
def chat():
    """
    AI 问答
    Body: {
      "kb_id": 1,
      "session_id": 1,
      "question": "xxx",
      "history": []
    }
    """
    user = get_current_user()
    data = request.get_json()

    if not data:
        return fail("请求体不能为空")

    kb_id = data.get("kb_id")
    session_id = data.get("session_id")
    question = data.get("question", "").strip()
    chat_history = data.get("history", [])

    if not kb_id:
        return fail("请指定知识库 kb_id")
    if not question:
        return fail("问题不能为空")
    if len(question) > 1000:
        return fail("问题长度不能超过 1000 字符")
    if chat_history is not None and not isinstance(chat_history, list):
        return fail("history 必须是数组")

    kb = KnowledgeBase.query.filter_by(id=kb_id, user_id=user.id).first()
    if not kb:
        return fail("知识库不存在或无权限", 404)

    if not os.path.exists(kb.file_path):
        return fail("知识库文件丢失，请重新上传", 500)

    session = None
    if session_id:
        session = ChatSession.query.filter_by(id=session_id, user_id=user.id).first()
        if not session:
            return fail("会话不存在或无权限", 404)
        if session.kb_id != kb.id:
            return fail("会话与知识库不匹配")
    else:
        session = ChatSession(
            user_id=user.id,
            kb_id=kb.id,
            title=generate_session_title(question),
        )
        db.session.add(session)
        db.session.flush()

    # 优先使用服务端已保存的会话历史，支持刷新后继续聊天
    history_messages = build_session_history_messages(session.id)
    if not history_messages:
        history_messages = chat_history or []

    result = ask_question(kb.file_path, question, history_messages)

    if not result["success"]:
        db.session.rollback()
        return fail(f"AI 服务异常：{result['error']}", 500)

    history = ChatHistory(
        user_id=user.id,
        kb_id=kb_id,
        session_id=session.id,
        question=question,
        answer=result["answer"],
        tokens_used=result["tokens_used"],
    )
    db.session.add(history)

    if history.question and session.title == "新对话":
        session.title = generate_session_title(history.question)
    session.updated_at = datetime.now(timezone.utc)

    db.session.commit()

    return success({
        "session_id": session.id,
        "session_title": session.title,
        "history_id": history.id,
        "question": question,
        "answer": result["answer"],
        "tokens_used": result["tokens_used"],
        "kb_name": kb.name,
        "created_at": history.created_at.isoformat(),
    })


@app.route("/api/chat/history", methods=["GET"])
@jwt_required()
def get_history():
    """
    获取问答历史
    Query: ?kb_id=1&session_id=1&page=1&per_page=20
    """
    user = get_current_user()

    kb_id = request.args.get("kb_id", type=int)
    session_id = request.args.get("session_id", type=int)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    per_page = min(per_page, 100)

    query = ChatHistory.query.filter_by(user_id=user.id)
    if kb_id:
        query = query.filter_by(kb_id=kb_id)
    if session_id:
        query = query.filter_by(session_id=session_id)

    pagination = (
        query
        .order_by(ChatHistory.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return success({
        "items": [h.to_dict() for h in pagination.items],
        "total": pagination.total,
        "page": page,
        "per_page": per_page,
        "pages": pagination.pages,
    })


@app.route("/api/chat/history/<int:history_id>", methods=["DELETE"])
@jwt_required()
def delete_history(history_id):
    """删除单条问答历史"""
    user = get_current_user()
    history = ChatHistory.query.filter_by(id=history_id, user_id=user.id).first()

    if not history:
        return fail("记录不存在或无权限", 404)

    session = history.session
    db.session.delete(history)
    if session and not ChatHistory.query.filter(
        ChatHistory.session_id == session.id,
        ChatHistory.id != history.id,
    ).first():
        db.session.delete(session)

    db.session.commit()

    return success(msg="历史记录已删除")


# ── 健康检查 ──────────────────────────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    return success({"status": "ok", "time": datetime.now(timezone.utc).isoformat()})


# ── 启动 ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(host="0.0.0.0", port=5001, debug=True)
