"""
数据库模型定义 
表结构：
  - User             用户表（预置账号，无注册）
  - KnowledgeBase    知识库表（TXT 文件元信息）
  - ChatSession      会话表
  - ChatHistory      问答历史表
"""

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    """用户表（预置账号，不支持注册）"""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    # 存储 werkzeug 生成的 hash 密码
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # 关联
    knowledge_bases = db.relationship("KnowledgeBase", backref="owner", lazy=True)
    chat_sessions = db.relationship("ChatSession", backref="user", lazy=True)
    chat_histories = db.relationship("ChatHistory", backref="user", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "created_at": self.created_at.isoformat(),
        }


class KnowledgeBase(db.Model):
    """知识库表（每条记录对应一个上传的 TXT 文件）"""
    __tablename__ = "knowledge_bases"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(128), nullable=False)          # 知识库名称（文件名）
    filename = db.Column(db.String(256), nullable=False)      # 服务器存储文件名
    file_path = db.Column(db.String(512), nullable=False)     # 文件完整路径
    file_size = db.Column(db.Integer, default=0)              # 文件大小（字节）
    char_count = db.Column(db.Integer, default=0)             # 字符数
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # 关联
    chat_sessions = db.relationship("ChatSession", backref="knowledge_base", lazy=True)
    chat_histories = db.relationship("ChatHistory", backref="knowledge_base", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "filename": self.filename,
            "file_size": self.file_size,
            "char_count": self.char_count,
            "created_at": self.created_at.isoformat(),
        }


class ChatSession(db.Model):
    """会话表"""
    __tablename__ = "chat_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    kb_id = db.Column(db.Integer, db.ForeignKey("knowledge_bases.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False, default="新对话")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    chat_histories = db.relationship(
        "ChatHistory",
        backref="session",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        last_history = max(self.chat_histories, key=lambda h: h.created_at, default=None)
        return {
            "id": self.id,
            "user_id": self.user_id,
            "kb_id": self.kb_id,
            "kb_name": self.knowledge_base.name if self.knowledge_base else "",
            "title": self.title,
            "message_count": len(self.chat_histories),
            "last_question": last_history.question if last_history else "",
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class ChatHistory(db.Model):
    """问答历史表"""
    __tablename__ = "chat_histories"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    kb_id = db.Column(db.Integer, db.ForeignKey("knowledge_bases.id"), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey("chat_sessions.id"), nullable=True)
    question = db.Column(db.Text, nullable=False)             # 用户提问
    answer = db.Column(db.Text, nullable=False)               # AI 回答
    tokens_used = db.Column(db.Integer, default=0)            # 消耗 token 数
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "kb_id": self.kb_id,
            "kb_name": self.knowledge_base.name if self.knowledge_base else "",
            "session_id": self.session_id,
            "session_title": self.session.title if self.session else "",
            "question": self.question,
            "answer": self.answer,
            "tokens_used": self.tokens_used,
            "created_at": self.created_at.isoformat(),
        }
