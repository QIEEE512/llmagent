from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pathlib import Path

import app.db as db
from app.deps import get_current_user
from app.schemas import ApiResponse
from app.services.ai import simple_ai_reply, vision_answer
from app.services.documents import extract_text, resolve_local_path_from_files_url
from app.services.rag import chunk_text, retrieve_embeddings, retrieve_tfidf

router = APIRouter()


def _coll(database, name: str):
    """Get collection from either a pymongo Database (attribute access) or a dict-like fake db (item access)."""

    try:
        return getattr(database, name)
    except Exception:
        return database[name]


def _obj_id(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid id")


def _get_active_account_id(db, user_id: str) -> str:
    users = _coll(db, "users")
    accounts = _coll(db, "accounts")

    user = users.find_one({"_id": user_id})
    if not user:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")

    active = user.get("activeAccountId")
    if not active:
        # 兼容：如果没有切换过账户，则尝试找一个默认 account
        acc = accounts.find_one({"userId": user_id})
        if acc and acc.get("_id"):
            active = str(acc.get("_id"))
            # fake_db may not implement update_one; ignore in that case
            try:
                users.update_one({"_id": user_id}, {"$set": {"activeAccountId": active}})
            except Exception:
                pass

    # 如果仍没有 account（常见于最小联调/内存 fake db），则自动创建一个
    if not active:
        active = f"a_{ObjectId()}"
        try:
            accounts.insert_one({"_id": active, "userId": user_id, "name": "默认账户", "account": user.get("account"), "createdAt": 0})
        except Exception:
            pass
        try:
            users.update_one({"_id": user_id}, {"$set": {"activeAccountId": active}})
        except Exception:
            # fake db doesn't support update_one; ignore
            pass
    if not active:
        raise HTTPException(status_code=400, detail="no active account")

    return str(active)


def _load_history(db, conversation_id: str, limit: int = 20) -> List[dict]:
    messages = _coll(db, "messages")
    # fake_db in tests doesn't implement find/sort/limit; fall back to empty history
    if not hasattr(messages, "find"):
        return []
    cursor = messages.find({"conversationId": conversation_id}, {"role": 1, "content": 1})
    try:
        cursor = cursor.sort("createdAt", 1).limit(limit)
    except Exception:
        pass
    return [{"role": m.get("role"), "content": m.get("content")} for m in cursor]


def _validate_attachments(raw: Any) -> List[dict]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise HTTPException(status_code=400, detail="attachments must be an array")

    out: List[dict] = []
    for i, a in enumerate(raw):
        if not isinstance(a, dict):
            raise HTTPException(status_code=400, detail=f"attachments[{i}] must be an object")
        t = a.get("type")
        url = a.get("url")
        if t not in ("image", "file"):
            raise HTTPException(status_code=400, detail=f"attachments[{i}].type invalid")
        if not isinstance(url, str) or not url.strip():
            raise HTTPException(status_code=400, detail=f"attachments[{i}].url required")

        # 只保留允许字段，避免前端传过多数据污染 DB
        out.append(
            {
                "type": t,
                "url": url.strip(),
                "name": a.get("name"),
                "size": a.get("size"),
                "mime": a.get("mime"),
            }
        )
    return out


def _load_local_file_bytes_from_url(url: str) -> tuple[bytes, str]:
    """Only allow reading files served by this backend via /files/<name> to avoid SSRF."""
    parsed = urlparse(url)
    path = parsed.path or ""
    if not path.startswith("/files/"):
        raise HTTPException(status_code=400, detail="only /files/ URLs are allowed for vision")

    name = path[len("/files/") :]
    if not name or "/" in name or ".." in name:
        raise HTTPException(status_code=400, detail="invalid file url")

    # upload 保存目录与 upload router 保持一致
    base_dir = Path("/tmp/uploads")
    fp = base_dir / name
    if not fp.exists() or not fp.is_file():
        raise HTTPException(status_code=404, detail="file not found")

    data = fp.read_bytes()
    # 粗略 mime：优先根据后缀
    ext = fp.suffix.lower()
    mime = "image/png"
    if ext in (".jpg", ".jpeg"):
        mime = "image/jpeg"
    elif ext == ".webp":
        mime = "image/webp"

    return data, mime


@router.post("/chat", response_model=ApiResponse)
def chat(payload: Dict[str, Any], user=Depends(get_current_user)):
    database = db.get_db()

    # store: whether to persist conversation/messages in MongoDB.
    # Default true to keep backward-compatibility.
    # Frontend may set store=false when it already persists messages via Conversations API
    # (POST /conversations/{id}/messages) to avoid duplicated history.
    store = payload.get("store")
    if store is None:
        store = True
    store = bool(store)

    raw_attachments = payload.get("attachments")
    attachments = _validate_attachments(raw_attachments)

    text = (payload.get("text") or "").strip()
    if not text and not attachments:
        raise HTTPException(status_code=400, detail="text 不能为空")

    user_id = str(user.get("id") or user.get("userId") or user.get("_id"))
    account_id = _get_active_account_id(database, user_id)

    now = datetime.utcnow()

    conversation_id: Optional[str] = payload.get("conversationId")

    if store:
        if conversation_id:
            conversations = _coll(database, "conversations")
            conv = conversations.find_one({"_id": conversation_id, "userId": user_id, "accountId": account_id})
            if not conv:
                raise HTTPException(status_code=404, detail="conversation not found")
            try:
                conversations.update_one({"_id": conversation_id}, {"$set": {"updatedAt": now}})
            except Exception:
                pass
        else:
            conversation_id = f"c_{ObjectId()}"
            conversations = _coll(database, "conversations")
            conversations.insert_one(
                {
                    "_id": conversation_id,
                    "userId": user_id,
                    "accountId": account_id,
                    "createdAt": now,
                    "updatedAt": now,
                }
            )

        # 写入 user message
        user_mid = f"m_{ObjectId()}"
        messages = _coll(database, "messages")
        messages.insert_one(
            {
                "_id": user_mid,
                "conversationId": conversation_id,
                "userId": user_id,
                "accountId": account_id,
                "role": "user",
                "content": text,
                "attachments": attachments,
                "meta": payload.get("meta") or {},
                "createdAt": now,
            }
        )
    else:
        # When not storing, conversationId must be provided by the caller.
        if not conversation_id:
            raise HTTPException(status_code=400, detail="conversationId is required when store=false")

    # 视觉理解：如果存在图片附件，则调用 qwen3-vl-flash 获取理解结果
    vision_notes: List[str] = []
    for a in attachments:
        if a.get("type") != "image":
            continue
        try:
            img_bytes, mime = _load_local_file_bytes_from_url(a.get("url"))
            v = vision_answer(question=text, image_bytes=img_bytes, mime=mime)
            vision_notes.append(v)
        except HTTPException:
            raise
        except Exception:
            # 不影响主流程，忽略单张图片处理失败
            continue

    # 文档理解：如果存在 file 附件（/files/...），则抽取文本 + RAG 检索并注入到上下文
    doc_notes: List[str] = []
    doc_meta: List[dict] = []
    for a in attachments:
        if a.get("type") != "file":
            continue
        try:
            fp = resolve_local_path_from_files_url(a.get("url"))
            text_doc, meta = extract_text(fp, mime=a.get("mime"))
            if not text_doc.strip():
                continue

            q = text or "请总结这份文件的核心内容，并列出3-5条要点。"
            chunks = chunk_text(text_doc, chunk_chars=1200, overlap=150)
            try:
                retrieved = retrieve_embeddings(q, chunks, top_k=5, model="text-embedding-v4")
                rag_method = "text-embedding-v4"
            except Exception:
                retrieved = retrieve_tfidf(q, chunks, top_k=5)
                rag_method = "tfidf"

            ctx_lines = []
            for r in retrieved:
                ctx_lines.append(f"[chunk#{r.index} score={r.score:.3f}]\n{r.text}")
            ctx = "\n\n".join(ctx_lines)
            if ctx:
                doc_notes.append(
                    "你收到了⼀份用户上传的文件内容片段（已从文件中抽取并检索）：\n" + ctx
                )
                doc_meta.append({"url": a.get("url"), "name": a.get("name"), "rag": rag_method})
        except HTTPException:
            # file not found / invalid url / unsupported type: surface as user-level error
            raise
        except Exception:
            # don't block chat on a single file parsing failure
            continue

    history = _load_history(database, conversation_id, limit=20)

    # 注入附件信息与视觉理解到上下文
    injected_lines: List[str] = []
    if attachments:
        for a in attachments:
            name = a.get("name") or ""
            injected_lines.append(f"- {a.get('type')}: {name} {a.get('url')}")
        injected_lines.insert(0, "我这条消息带了附件：")

    if vision_notes:
        injected_lines.append("图片理解结果：")
        for i, note in enumerate(vision_notes, start=1):
            injected_lines.append(f"[{i}] {note}")

    if doc_notes:
        injected_lines.append("文件解析结果（RAG 片段）：")
        for i, note in enumerate(doc_notes, start=1):
            injected_lines.append(f"[doc{i}] {note}")

    if injected_lines:
        history = history + [{"role": "user", "content": "\n".join(injected_lines)}]

    # 如果用户只发图片没文字，也能回答
    prompt_text = text or "请根据我上传的图片进行说明。"
    answer = simple_ai_reply(prompt_text, history=history)

    assistant_mid: Optional[str] = None
    if store:
        # 写入 assistant message
        assistant_mid = f"m_{ObjectId()}"
        messages = _coll(database, "messages")
        messages.insert_one(
            {
                "_id": assistant_mid,
                "conversationId": conversation_id,
                "userId": user_id,
                "accountId": account_id,
                "role": "assistant",
                "content": answer,
                "createdAt": datetime.utcnow(),
            }
        )

        conversations = _coll(database, "conversations")
        try:
            conversations.update_one({"_id": conversation_id}, {"$set": {"updatedAt": datetime.utcnow()}})
        except Exception:
            pass

    return ApiResponse(
        data={
            "answer": answer,
            "conversationId": conversation_id,
            "messageId": assistant_mid,
        }
    )
