"""
Flask 主应用       
接口列表：
  POST   /api/auth/login              用户登录
  GET    /api/auth/me                 获取当前用户信息

  GET    /api/kb                      获取知识库列表
  POST   /api/kb/upload               上传 TXT 知识库
  DELETE /api/kb/<kb_id>              删除知识库

  POST   /api/chat                    AI 问答（阻塞式）
  POST   /api/chat/stream             AI 问答（SSE 流式）
  GET    /api/chat/history            获取问答历史
  DELETE /api/chat/history/<id>       删除单条历史
"""

import json
import os
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, request, jsonify, Response, stream_with_context
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
from ai_service import ask_question, ask_question_stream
from document_loader import is_supported_document, extract_document_text, SUPPORTED_EXTENSIONS
from rag_service import (
    index_knowledge_base,
    ensure_knowledge_base_index,
    retrieve_knowledge_context,
    delete_knowledge_base_index,
    get_kb_index_count,
)

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
def _friendly_error(error_msg: str) -> str:
    """将 AI 服务异常信息友好化。"""
    msg = str(error_msg)
    if "api_key" in msg.lower() or "authentication" in msg.lower() or "invalid" in msg.lower():
        return "API Key 无效或未配置，请检查 .env 文件中的 ZHIPUAI_API_KEY"
    if "connection" in msg.lower() or "timeout" in msg.lower():
        return "连接智谱 AI 超时，请检查网络连接"
    return msg


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
    """允许上传受支持的知识库文件。"""
    return is_supported_document(filename)


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
    """兼容旧版 SQLite：补齐会话表和问答扩展字段。"""
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

        history_columns = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(chat_histories)")).fetchall()
        }
        if "session_id" not in history_columns:
            conn.execute(text("ALTER TABLE chat_histories ADD COLUMN session_id INTEGER"))
        if "references_json" not in history_columns:
            conn.execute(text("ALTER TABLE chat_histories ADD COLUMN references_json TEXT"))

        kb_columns = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(knowledge_bases)")).fetchall()
        }
        if "original_filename" not in kb_columns:
            conn.execute(text("ALTER TABLE knowledge_bases ADD COLUMN original_filename VARCHAR(256)"))


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
    items = []
    for kb in kbs:
        item = kb.to_dict()
        try:
            item["chunk_count"] = get_kb_index_count(kb.id, user.id)
            item["indexed"] = item["chunk_count"] > 0
        except Exception:
            item["chunk_count"] = 0
            item["indexed"] = False
        items.append(item)
    return success(items)


@app.route("/api/kb/upload", methods=["POST"])
@jwt_required()
def upload_kb():
    """
    上传知识库文件
    Form-data: file=<txt/pdf/docx/md 文件>
    """
    user = get_current_user()

    if "file" not in request.files:
        return fail("未找到上传文件，字段名应为 file")

    file = request.files["file"]
    if file.filename == "":
        return fail("文件名不能为空")

    if not allowed_file(file.filename):
        supported = ", ".join(f".{ext}" for ext in sorted(SUPPORTED_EXTENSIONS))
        return fail(f"只支持上传以下格式文件：{supported}")

    # 生成唯一文件名，防止冲突
    original_name = file.filename
    safe_name = secure_filename(original_name)
    unique_filename = f"{uuid.uuid4().hex}_{safe_name}"
    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)

    file.save(file_path)

    # 统计文件信息
    file_size = os.path.getsize(file_path)
    try:
        parsed_text = extract_document_text(file_path, original_name)
        char_count = len(parsed_text)
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        return fail(f"文件解析失败：{str(e)}", 400)

    # 知识库名称：去掉扩展名
    kb_name = os.path.splitext(original_name)[0]

    kb = KnowledgeBase(
        user_id=user.id,
        name=kb_name,
        filename=unique_filename,
        original_filename=original_name,
        file_path=file_path,
        file_size=file_size,
        char_count=char_count,
    )
    db.session.add(kb)
    db.session.commit()

    # 建立向量索引
    try:
        rag_result = index_knowledge_base(kb.id, user.id, file_path, kb_name, original_name)
    except Exception as e:
        db.session.delete(kb)
        db.session.commit()
        if os.path.exists(file_path):
            os.remove(file_path)
        return fail(f"知识库向量化失败：{str(e)}", 500)

    return success({
        **kb.to_dict(),
        "chunk_count": rag_result["chunk_count"],
    }, "知识库上传成功", 201)


@app.route("/api/kb/<int:kb_id>", methods=["DELETE"])
@jwt_required()
def delete_kb(kb_id):
    """删除知识库（同时删除文件、向量索引和相关历史）"""
    user = get_current_user()
    kb = KnowledgeBase.query.filter_by(id=kb_id, user_id=user.id).first()

    if not kb:
        return fail("知识库不存在或无权限", 404)

    # 删除向量索引
    try:
        delete_knowledge_base_index(kb_id, user.id)
    except Exception:
        pass

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


@app.route("/api/kb/<int:kb_id>/reindex", methods=["POST"])
@jwt_required()
def reindex_kb(kb_id):
    """重建指定知识库的向量索引。"""
    user = get_current_user()
    kb = KnowledgeBase.query.filter_by(id=kb_id, user_id=user.id).first()

    if not kb:
        return fail("知识库不存在或无权限", 404)

    if not os.path.exists(kb.file_path):
        return fail("知识库文件丢失，请重新上传", 500)

    try:
        result = index_knowledge_base(kb.id, user.id, kb.file_path, kb.name, kb.original_filename or kb.filename)
    except Exception as e:
        return fail(f"重建索引失败：{str(e)}", 500)

    return success({
        "kb_id": kb.id,
        "kb_name": kb.name,
        "chunk_count": result["chunk_count"],
    }, "知识库索引重建成功")


# ══════════════════════════════════════════════════════════════════════════════
# 问答公共前置逻辑（任务 2.2）
# ══════════════════════════════════════════════════════════════════════════════

def _prepare_chat_context(user, data: dict):
    """
    问答接口公共前置逻辑：参数校验、kb 权限校验、session 处理、RAG 检索。
    供流式和非流式接口共用。

    Returns:
        (ctx_tuple, None)  成功
        (None, error_response)  校验失败
    """
    kb_id = data.get("kb_id")
    session_id = data.get("session_id")
    question = data.get("question", "").strip()
    chat_history = data.get("history", [])

    if not kb_id:
        return None, fail("请指定知识库 kb_id")
    if not question:
        return None, fail("问题不能为空")
    if len(question) > 1000:
        return None, fail("问题长度不能超过 1000 字符")
    if chat_history is not None and not isinstance(chat_history, list):
        return None, fail("history 必须是数组")

    kb = KnowledgeBase.query.filter_by(id=kb_id, user_id=user.id).first()
    if not kb:
        return None, fail("知识库不存在或无权限", 404)

    if not os.path.exists(kb.file_path):
        return None, fail("知识库文件丢失，请重新上传", 500)

    try:
        ensure_knowledge_base_index(kb.id, user.id, kb.file_path, kb.name, kb.original_filename or kb.filename)
    except Exception as e:
        return None, fail(f"知识库索引不可用：{str(e)}", 500)

    session = None
    if session_id:
        session = ChatSession.query.filter_by(id=session_id, user_id=user.id).first()
        if not session:
            return None, fail("会话不存在或无权限", 404)
        if session.kb_id != kb.id:
            return None, fail("会话与知识库不匹配")
    else:
        session = ChatSession(
            user_id=user.id,
            kb_id=kb.id,
            title=generate_session_title(question),
        )
        db.session.add(session)
        db.session.flush()

    history_messages = build_session_history_messages(session.id)
    if not history_messages:
        history_messages = chat_history or []

    try:
        retrieval_result = retrieve_knowledge_context(kb.id, user.id, question)
    except Exception as e:
        db.session.rollback()
        return None, fail(f"知识检索失败：{str(e)}", 500)

    references = [
        {
            "content": item["content"],
            "metadata": item.get("metadata", {}),
            "distance": item.get("distance"),
        }
        for item in retrieval_result["chunks"]
    ]

    return (kb, session, question, retrieval_result, references, history_messages), None


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
    AI 问答（阻塞式）
    Body: { "kb_id": 1, "session_id": 1, "question": "xxx", "history": [] }
    """
    user = get_current_user()
    data = request.get_json()
    if not data:
        return fail("请求体不能为空")

    ctx, err = _prepare_chat_context(user, data)
    if err is not None:
        return err

    kb, session, question, retrieval_result, references, history_messages = ctx

    result = ask_question(retrieval_result["context"], question, history_messages)
    if not result["success"]:
        db.session.rollback()
        return fail(f"AI 服务异常：{result['error']}", 500)

    history = ChatHistory(
        user_id=user.id,
        kb_id=kb.id,
        session_id=session.id,
        question=question,
        answer=result["answer"],
        references_json=json.dumps(references, ensure_ascii=False),
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
        "references": references,
        "tokens_used": result["tokens_used"],
        "kb_name": kb.name,
        "retrieved_chunks": len(retrieval_result["chunks"]),
        "created_at": history.created_at.isoformat(),
    })


@app.route("/api/chat/stream", methods=["POST"])
@jwt_required()
def chat_stream():
    """
    AI 问答（SSE 流式，任务 2.1）
    Body: { "kb_id": 1, "session_id": 1, "question": "xxx", "history": [] }
    Response: text/event-stream
      data: {"type": "delta", "content": "..."}
      data: {"type": "done",  "session_id": 1, "history_id": 1, "tokens_used": 256, "references": [...]}
      data: {"type": "error", "error": "..."}
    """
    user = get_current_user()
    data = request.get_json()
    if not data:
        return fail("请求体不能为空")

    ctx, err = _prepare_chat_context(user, data)
    if err is not None:
        return err

    kb, session, question, retrieval_result, references, history_messages = ctx

    # 提前将需要在闭包中使用的标量取出，避免生成器内 SQLAlchemy session 状态问题
    session_id_val = session.id
    kb_id_val = kb.id
    user_id_val = user.id
    references_json_str = json.dumps(references, ensure_ascii=False)
    context_text = retrieval_result["context"]

    # 提前 commit，确保 session 已持久化
    db.session.commit()

    def sse_generator():
        """SSE 生成器：逐块推送 token，流结束后写入历史（任务 2.3 / 2.4）"""
        full_answer = []
        tokens_used = 0
        history_id = None
        final_title = generate_session_title(question)

        try:
            for frame in ask_question_stream(context_text, question, history_messages):
                frame_type = frame.get("type")

                if frame_type == "delta":
                    full_answer.append(frame["content"])
                    yield f"data: {json.dumps(frame, ensure_ascii=False)}\n\n"

                elif frame_type == "done":
                    tokens_used = frame.get("tokens_used", 0)

                    # 流结束后写入历史（任务 2.4）
                    with app.app_context():
                        answer_text = "".join(full_answer)
                        history_record = ChatHistory(
                            user_id=user_id_val,
                            kb_id=kb_id_val,
                            session_id=session_id_val,
                            question=question,
                            answer=answer_text,
                            references_json=references_json_str,
                            tokens_used=tokens_used,
                        )
                        db.session.add(history_record)

                        sess = db.session.get(ChatSession, session_id_val)
                        if sess:
                            if sess.title == "新对话" and question:
                                sess.title = generate_session_title(question)
                                final_title = sess.title
                            sess.updated_at = datetime.now(timezone.utc)

                        db.session.commit()
                        history_id = history_record.id

                    # 推送结束帧（任务 2.5）
                    done_frame = {
                        "type": "done",
                        "session_id": session_id_val,
                        "session_title": final_title,
                        "history_id": history_id,
                        "tokens_used": tokens_used,
                        "references": references,
                        "retrieved_chunks": len(references),
                    }
                    yield f"data: {json.dumps(done_frame, ensure_ascii=False)}\n\n"

                elif frame_type == "error":
                    yield f"data: {json.dumps(frame, ensure_ascii=False)}\n\n"

        except GeneratorExit:
            # 客户端中止（AbortController），不写入历史
            pass
        except Exception as e:
            err_frame = {"type": "error", "error": _friendly_error(str(e))}
            yield f"data: {json.dumps(err_frame, ensure_ascii=False)}\n\n"

    # 构造 SSE 响应（任务 2.6 / 2.7）
    resp = Response(
        stream_with_context(sse_generator()),
        mimetype="text/event-stream",
    )
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["X-Accel-Buffering"] = "no"
    resp.headers["Connection"] = "keep-alive"
    return resp


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
