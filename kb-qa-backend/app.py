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
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from models import db, User, KnowledgeBase, ChatHistory
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


# ── 数据库初始化 & 预置账号 ───────────────────────────────────────────────────
def init_db():
    """创建表并预置默认账号"""
    db.create_all()

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

    # 删除关联历史
    ChatHistory.query.filter_by(kb_id=kb_id).delete()

    db.session.delete(kb)
    db.session.commit()

    return success(msg="知识库已删除")


# ══════════════════════════════════════════════════════════════════════════════
# 问答接口
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/chat", methods=["POST"])
@jwt_required()
def chat():
    """
    AI 问答
    Body: { "kb_id": 1, "question": "xxx" }
    """
    user = get_current_user()
    data = request.get_json()

    if not data:
        return fail("请求体不能为空")

    kb_id = data.get("kb_id")
    question = data.get("question", "").strip()

    if not kb_id:
        return fail("请指定知识库 kb_id")
    if not question:
        return fail("问题不能为空")
    if len(question) > 1000:
        return fail("问题长度不能超过 1000 字符")

    # 验证知识库归属
    kb = KnowledgeBase.query.filter_by(id=kb_id, user_id=user.id).first()
    if not kb:
        return fail("知识库不存在或无权限", 404)

    if not os.path.exists(kb.file_path):
        return fail("知识库文件丢失，请重新上传", 500)

    # 调用 AI 服务
    result = ask_question(kb.file_path, question)

    if not result["success"]:
        return fail(f"AI 服务异常：{result['error']}", 500)

    # 保存历史记录
    history = ChatHistory(
        user_id=user.id,
        kb_id=kb_id,
        question=question,
        answer=result["answer"],
        tokens_used=result["tokens_used"],
    )
    db.session.add(history)
    db.session.commit()

    return success({
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
    Query: ?kb_id=1&page=1&per_page=20
    """
    user = get_current_user()

    kb_id = request.args.get("kb_id", type=int)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    per_page = min(per_page, 100)  # 最多 100 条

    query = ChatHistory.query.filter_by(user_id=user.id)
    if kb_id:
        query = query.filter_by(kb_id=kb_id)

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

    db.session.delete(history)
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
