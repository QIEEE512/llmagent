from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import PyMongoError

import app.db as db
from app import deps
from app.schemas import ApiResponse
from app.services.documents import extract_text, resolve_local_path_from_files_url
from app.services.ai import simple_ai_reply

import logging
import json
import re

logger = logging.getLogger(__name__)

router = APIRouter()


def _dt_to_iso(v: Any) -> Any:
    if isinstance(v, datetime):
        return v.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    return v


def _coll(database, name: str):
    try:
        return getattr(database, name)
    except Exception:
        return database[name]


def _now() -> datetime:
    return datetime.utcnow()


def _local_tz() -> timezone:
    """Local timezone for dateRange boundaries.

    Frontend selects date range by local calendar dates, so we interpret dateFrom/dateTo
    as local dates (default UTC+8). You can override via env:
    - APP_LOCAL_TIMEZONE_OFFSET_MINUTES, e.g. 480 for UTC+8, 0 for UTC.
    """

    import os

    raw = os.environ.get("APP_LOCAL_TIMEZONE_OFFSET_MINUTES")
    minutes = 480
    if raw:
        try:
            minutes = int(raw)
        except Exception:
            minutes = 480
    return timezone(timedelta(minutes=minutes))


def _get_active_account_id(database, user_id: str) -> str:
    # keep consistent with chat.py & conversations.py
    users = _coll(database, "users")
    accounts = _coll(database, "accounts")

    user = users.find_one({"_id": user_id})
    if not user:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")

    active = user.get("activeAccountId")
    if not active:
        acc = accounts.find_one({"userId": user_id})
        if acc and acc.get("_id"):
            active = str(acc.get("_id"))
            try:
                users.update_one({"_id": user_id}, {"$set": {"activeAccountId": active}})
            except Exception:
                pass

    if not active:
        active = f"a_{ObjectId()}"
        try:
            accounts.insert_one({"_id": active, "userId": user_id, "name": "默认账号", "account": user.get("account"), "createdAt": 0})
        except Exception:
            pass
        try:
            users.update_one({"_id": user_id}, {"$set": {"activeAccountId": active}})
        except Exception:
            pass

    if not active:
        raise HTTPException(status_code=400, detail="no active account")

    return str(active)


def _parse_date_yyyy_mm_dd(s: str, *, name: str) -> datetime:
    try:
        # date only; returned datetime is timezone-aware at local 00:00:00
        local = _local_tz()
        d = datetime.strptime(s, "%Y-%m-%d")
        return datetime(d.year, d.month, d.day, tzinfo=local)
    except Exception:
        raise HTTPException(status_code=400, detail=f"{name} must be YYYY-MM-DD")


def _materialize_messages(
    database,
    *,
    user_id: str,
    account_id: str,
    source_type: str,
    conversation_ids: Optional[list[str]],
    date_from: Optional[str],
    date_to: Optional[str],
    include_assistant: bool,
) -> list[dict]:
    messages = _coll(database, "messages")

    roles = ["user"]
    if include_assistant:
        roles.append("assistant")

    query: dict[str, Any] = {"userId": user_id, "accountId": account_id, "role": {"$in": roles}}

    if source_type == "conversations":
        ids = [str(x).strip() for x in (conversation_ids or []) if str(x).strip()]
        if not ids:
            raise HTTPException(status_code=400, detail="conversationIds is required")
        query["conversationId"] = {"$in": ids}

        # verify conversations exist and belong to user/account (avoid leaking)
        conversations = _coll(database, "conversations")
        for cid in ids:
            conv = conversations.find_one({"_id": cid, "userId": user_id, "accountId": account_id, "deletedAt": {"$exists": False}})
            if not conv:
                raise HTTPException(status_code=404, detail="conversation not found")

    elif source_type == "dateRange":
        if not date_from or not date_to:
            raise HTTPException(status_code=400, detail="dateFrom and dateTo are required")
        d_from = _parse_date_yyyy_mm_dd(str(date_from), name="dateFrom")
        d_to = _parse_date_yyyy_mm_dd(str(date_to), name="dateTo")
        if d_to < d_from:
            raise HTTPException(status_code=400, detail="dateTo must be >= dateFrom")

        # Inclusive local date range: [local_from_start, local_to_end)
        # Convert local boundaries to UTC naive datetime for Mongo (which stores naive UTC here).
        utc_from = d_from.astimezone(timezone.utc).replace(tzinfo=None)
        utc_to = (d_to + timedelta(days=1)).astimezone(timezone.utc).replace(tzinfo=None)
        query["createdAt"] = {"$gte": utc_from, "$lt": utc_to}

    else:
        raise HTTPException(status_code=400, detail="sourceType invalid")

    out: list[dict] = []
    try:
        if not hasattr(messages, "find"):
            return []
        cursor = messages.find(query)
        try:
            cursor = cursor.sort("createdAt", 1)
        except Exception:
            pass
        for m in cursor:
            out.append(
                {
                    "conversationId": m.get("conversationId"),
                    "role": m.get("role"),
                    "text": (m.get("content") or "").strip(),
                    "createdAt": m.get("createdAt"),
                }
            )
    except PyMongoError as e:
        raise HTTPException(status_code=503, detail=f"数据库不可用：{e}")

    # thin filtering
    out = [m for m in out if m.get("text")]
    if not out:
        raise HTTPException(status_code=404, detail="no material found")

    return out


def _normalize_profile(profile: Any) -> dict:
    if not isinstance(profile, dict):
        return {}

    out: dict[str, Any] = {}
    for key in ("name", "learningGoal", "preferences"):
        if key not in profile:
            continue
        value = profile.get(key)
        if value is None:
            continue
        if isinstance(value, str):
            out[key] = value.strip()
        else:
            out[key] = str(value)
    return out


def _merge_profile(base: Any, overrides: dict) -> dict:
    merged: dict[str, Any] = {}
    if isinstance(base, dict):
        merged.update(base)
    merged.update(overrides or {})
    return merged


def _normalize_story(story: Any) -> dict:
    if not isinstance(story, dict):
        return {}

    story.setdefault("storyVersion", 1)
    meta = story.get("meta")
    if not isinstance(meta, dict):
        story["meta"] = {}

    chapters = story.get("chapters")
    if not isinstance(chapters, list):
        story["chapters"] = []

    milestones = story.get("milestones")
    if not isinstance(milestones, list):
        story["milestones"] = []

    return story


def _truncate_material(material: list[dict], *, max_items: int = 200, max_chars: int = 20000) -> tuple[list[dict], dict]:
    """Truncate material to keep prompts bounded.

    Returns: (material, meta)
    """

    meta: dict[str, Any] = {"truncated": False, "maxItems": max_items, "maxChars": max_chars}
    if not material:
        return material, meta

    original_items = len(material)
    # keep latest max_items (material is already sorted asc)
    if original_items > max_items:
        material = material[-max_items:]
        meta["truncated"] = True
        meta["truncatedBy"] = "items"
        meta["originalItems"] = original_items

    out: list[dict] = []
    used = 0
    for m in material:
        t = str(m.get("text") or "")
        # approximate per-message cost
        cost = len(t) + 40
        if out and used + cost > max_chars:
            meta["truncated"] = True
            meta["truncatedBy"] = "chars"
            break
        out.append(m)
        used += cost
    meta["usedChars"] = used
    meta["usedItems"] = len(out)
    return out, meta


def _story_prompt(material: list[dict]) -> str:
    # Keep prompt compact: feed a timeline-like material.
    lines: list[str] = []
    for m in material:
        at = m.get("createdAt")
        # stringify datetime (fastapi/pydantic will serialize later; prompt needs text)
        at_s = at.isoformat() if hasattr(at, "isoformat") else str(at)
        role = m.get("role")
        text = m.get("text")
        lines.append(f"[{at_s}] {role}: {text}")

    joined = "\n".join(lines)

    return (
        "你是一个成长档案撰写助手。请根据下面的对话素材（按时间排序），生成一份温馨的成长日志 story JSON。\n"
        "要求：\n"
        "1) 严格输出 JSON，不要输出任何额外的文字。\n"
        "2) JSON 结构必须包含：storyVersion(number=1), title(string), chapters(array), milestones(array), meta(object)。\n"
        "3) chapters[*] 必须包含：chapterTitle(string), paragraphs(array of string), timeline(array of {at, summary})。\n"
        "4) milestones[*] 必须包含：title, at, summary, type。\n"
        "5) timeline.at 和 milestones.at 使用 ISO 8601 字符串。\n"
        "6) 章节 3-6 个，每章 2-4 段，每段 60-140 字左右。里程碑 3-8 条。\n"
        "7) 内容要适合儿童成长记录，积极、简要，不要编造不存在的事实。\n"
        "素材如下：\n"
        + joined
    )


def _timeline_prompt(material: list[dict]) -> str:
    lines: list[str] = []
    for m in material:
        at = m.get("createdAt")
        at_s = at.isoformat() if hasattr(at, "isoformat") else str(at)
        role = m.get("role")
        text = m.get("text")
        lines.append(f"[{at_s}] {role}: {text}")

    joined = "\n".join(lines)

    return (
        "你是一个成长档案素材整理助手。请根据下面的对话素材（按时间排序），提炼一个简短的 timeline JSON，用于后续写成长日志。\n"
        "要求：\n"
        "1) 严格输出 JSON，不要输出任何额外文字。\n"
        "2) JSON 结构必须为：{\"timeline\": [ {\"at\": string, \"summary\": string, \"type\": string} ... ] }\n"
        "3) timeline 数量 10-30 条，按时间升序。at 用 ISO 8601 字符串。summary 20-60 字。type 可选 english/math/science/habit/emotion/reading/other。\n"
        "4) 不要编造不存在的事实；若素材不足可少于 10 条。\n"
        "素材如下：\n"
        + joined
    )


def _to_iso_str(v: Any) -> str:
    if isinstance(v, datetime):
        return v.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    s = str(v or "").strip()
    if not s:
        return _now().replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    return s


def _brief_text(s: str, *, max_len: int = 90) -> str:
    t = " ".join(str(s or "").strip().split())
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _fallback_timeline_from_material(material: list[dict], *, max_items: int = 20) -> list[dict]:
    if not material:
        return []
    picked = material[-max_items:]
    out: list[dict] = []
    for m in picked:
        text = str(m.get("text") or "").strip()
        if not text:
            continue
        out.append(
            {
                "at": _to_iso_str(m.get("createdAt")),
                "summary": _brief_text(text, max_len=60),
                "type": "other",
            }
        )
    return out


def _build_fallback_story(*, material: list[dict], timeline: list[dict], profile: dict, source_type: str, reason: str) -> dict:
    timeline = timeline or _fallback_timeline_from_material(material)
    if not timeline:
        timeline = [
            {
                "at": _to_iso_str(_now()),
                "summary": "近期有持续学习与交流记录。",
                "type": "other",
            }
        ]

    # Split timeline into up to 3 small chapters
    total = len(timeline)
    chunk = max(1, total // 3)
    chapters: list[dict] = []
    start = 0
    idx = 1
    while start < total and idx <= 3:
        seg = timeline[start : min(total, start + chunk)]
        if not seg:
            break
        paragraphs = [
            "本阶段保持了稳定的学习与表达节奏，能够持续完成对话与反馈。",
            "从记录中可见，孩子在沟通表达与学习参与度方面有连续性进展。",
        ]
        chapters.append(
            {
                "chapterTitle": f"成长片段 {idx}",
                "paragraphs": paragraphs,
                "timeline": [{"at": x.get("at"), "summary": x.get("summary")} for x in seg],
            }
        )
        start += chunk
        idx += 1

    milestones = []
    for x in timeline[: min(5, len(timeline))]:
        milestones.append(
            {
                "title": "学习记录",
                "at": x.get("at"),
                "summary": x.get("summary"),
                "type": x.get("type") or "other",
            }
        )

    title = "成长日志（简版）"
    if profile.get("name"):
        title = f"{profile.get('name')}的成长日志（简版）"

    return {
        "storyVersion": 1,
        "title": title,
        "chapters": chapters,
        "milestones": milestones,
        "meta": {
            "degraded": True,
            "degradedReason": reason,
            "sourceType": source_type,
            "fallback": "timeout_simple_story",
        },
        "profile": profile or {},
    }


def _log_model_non_json(*, stage: str, raw: str, extracted: str | None = None) -> None:
    """Log model raw output for debugging JSON issues.

    We log only a prefix to avoid leaking too much user material.
    """

    try:
        raw_s = str(raw or "")
        extracted_s = None if extracted is None else str(extracted or "")
        raw_preview = raw_s[:1200]
        info: dict[str, Any] = {
            "stage": stage,
            "rawLen": len(raw_s),
            "rawPreview": raw_preview,
        }
        if extracted_s is not None:
            info["extractedLen"] = len(extracted_s)
            info["extractedPreview"] = extracted_s[:1200]
        logger.warning("profile_story model returned non-JSON: %s", info)
    except Exception:
        # never fail the request because of logging
        pass


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)


def _extract_json_candidate(raw: str) -> str | None:
    """Extract a JSON candidate from model output.

    Supports:
    - ```json ... ``` fenced blocks
    - outermost {...} object
    - outermost [...] array
    """

    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None

    # 1) fenced blocks (prefer the first)
    m = _FENCE_RE.search(s)
    if m:
        inner = (m.group(1) or "").strip()
        if inner:
            return inner

    # 2) if it already starts with JSON markers, return as-is
    if s[0] in ("{", "["):
        return s

    # 3) try extract outermost object or array (best-effort)
    # object
    i = s.find("{")
    j = s.rfind("}")
    if i != -1 and j != -1 and j > i:
        return s[i : j + 1].strip()
    # array
    i = s.find("[")
    j = s.rfind("]")
    if i != -1 and j != -1 and j > i:
        return s[i : j + 1].strip()
    return None


def _safe_parse_json(raw: str, *, stage: str) -> Any:
    """Parse JSON with extraction + logging on failure."""

    extracted = _extract_json_candidate(raw)
    if extracted is None:
        _log_model_non_json(stage=stage, raw=raw, extracted=None)
        raise HTTPException(status_code=502, detail="model returned non-JSON")

    try:
        return json.loads(extracted)
    except Exception as e:
        try:
            logger.warning("profile_story json.loads failed stage=%s err=%s", stage, repr(e))
        except Exception:
            pass
        _log_model_non_json(stage=stage, raw=raw, extracted=extracted)
        raise HTTPException(status_code=502, detail="model returned non-JSON")


def _profile_story_timeout_seconds(default: float = 45.0) -> float:
    import os

    raw = os.environ.get("APP_PROFILE_STORY_MODEL_TIMEOUT_SECONDS")
    if not raw:
        return float(default)
    try:
        v = float(raw)
        return v if v > 0 else float(default)
    except Exception:
        return float(default)


def _profile_story_enable_degraded_fallback(default: bool = False) -> bool:
    import os

    raw = (os.environ.get("APP_PROFILE_STORY_ENABLE_DEGRADED_FALLBACK") or "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def _detect_model_soft_error_text(text: str) -> str | None:
    s = str(text or "").strip()
    if not s:
        return None
    if s.startswith("（模型超时）") or "请求处理时间过长" in s:
        return "timeout"
    if s.startswith("（模型调用失败）") or s.startswith("（模型未配置）"):
        return "failed"
    return None


def _ai_json_reply(prompt: str, *, stage: str) -> Any:
    """Call model and parse JSON with retry + timeout-aware error mapping."""

    timeout_s = _profile_story_timeout_seconds(45.0)
    last_non_json_exc: HTTPException | None = None
    saw_timeout = False
    saw_model_failed = False

    prompts = [
        (stage, prompt),
        (
            f"{stage}_retry",
            "上一次输出不是合法 JSON（或 JSON 不完整）。\n"
            "请【只】输出严格合法的 JSON，不要输出任何解释、标题、Markdown 代码块。\n"
            "确保括号和引号完整、可被 json.loads 解析。\n\n"
            "原任务提示如下：\n"
            + prompt,
        ),
    ]

    for stage_name, p in prompts:
        text = simple_ai_reply(p, history=None, timeout_s=timeout_s, max_tokens=2200)
        soft_err = _detect_model_soft_error_text(text)
        if soft_err == "timeout":
            saw_timeout = True
            continue
        if soft_err == "failed":
            saw_model_failed = True
            continue

        try:
            return _safe_parse_json(text, stage=stage_name)
        except HTTPException as e:
            if e.status_code != 502:
                raise
            last_non_json_exc = e

    if saw_timeout:
        raise HTTPException(status_code=504, detail="model timeout, please retry")
    if saw_model_failed:
        raise HTTPException(status_code=502, detail="model call failed")
    if last_non_json_exc is not None:
        raise last_non_json_exc
    raise HTTPException(status_code=502, detail="model returned non-JSON")


@router.post("/profile/story/generate", response_model=ApiResponse)
def profile_story_generate(payload: dict[str, Any], user_id: str = Depends(deps.get_current_user_id)):
    source_type = (payload.get("sourceType") or "").strip()
    include_assistant = payload.get("includeAssistant")
    if include_assistant is None:
        include_assistant = True
    include_assistant = bool(include_assistant)

    database = db.get_db()
    account_id = _get_active_account_id(database, user_id)

    material = _materialize_messages(
        database,
        user_id=user_id,
        account_id=account_id,
        source_type=source_type,
        conversation_ids=payload.get("conversationIds"),
        date_from=payload.get("dateFrom"),
        date_to=payload.get("dateTo"),
        include_assistant=include_assistant,
    )

    material, trunc_meta = _truncate_material(material)

    profile = _normalize_profile(payload.get("profile"))
    enable_degraded_fallback = _profile_story_enable_degraded_fallback(False)

    # Strategy 3: two-stage generation
    # 1) compress long materials into a short timeline
    timeline_prompt = _timeline_prompt(material)
    try:
        timeline_obj = _ai_json_reply(timeline_prompt, stage="timeline")
        if isinstance(timeline_obj, dict):
            timeline = timeline_obj.get("timeline")
        elif isinstance(timeline_obj, list):
            timeline = timeline_obj
        else:
            timeline = None
        if not isinstance(timeline, list) or not timeline:
            if enable_degraded_fallback:
                # model may return null / wrong JSON root; degrade instead of crashing.
                timeline = _fallback_timeline_from_material(material)
                if not timeline:
                    raise HTTPException(status_code=502, detail="model returned empty timeline")
            else:
                raise HTTPException(status_code=502, detail="model returned invalid timeline JSON")
    except HTTPException as e:
        # Timeout fallback: build concise timeline from raw material and continue (optional).
        if e.status_code == 504 and enable_degraded_fallback:
            timeline = _fallback_timeline_from_material(material)
            if not timeline:
                raise
        else:
            raise

    # 2) generate story from the compressed timeline
    story_prompt = (
        "你是一个成长档案撰写助手。请根据下面的 timeline 要点，生成一份温馨的成长日记 story JSON。\n"
        "要求：\n"
        "1) 严格输出 JSON，不要输出任何额外文字。\n"
        "2) JSON 结构必须包含：storyVersion(number=1), title(string), chapters(array), milestones(array), meta(object)。\n"
        "3) chapters[*] 必须包含：chapterTitle(string), paragraphs(array of string), timeline(array of {at, summary})。\n"
        "4) milestones[*] 必须包含：title, at, summary, type。\n"
        "5) timeline.at 和 milestones.at 使用 ISO 8601 字符串。\n"
        "6) 章节 3-6 个，每章 2-4 段，每段 60-140 字左右。里程碑 3-8 条。\n"
        "7) 不要编造不存在的事实。\n"
        "timeline JSON 如下：\n"
        + __import__("json").dumps({"timeline": timeline}, ensure_ascii=False)
    )

    try:
        story_obj = _ai_json_reply(story_prompt, stage="story")
        story = _normalize_story(story_obj)
        if not story:
            if enable_degraded_fallback:
                story = _build_fallback_story(
                    material=material,
                    timeline=timeline,
                    profile=profile,
                    source_type=source_type,
                    reason="model_invalid_story_json",
                )
            else:
                raise HTTPException(status_code=502, detail="model returned invalid story JSON")
    except HTTPException as e:
        # Timeout fallback: return a simplified story instead of hard failure (optional).
        if e.status_code == 504 and enable_degraded_fallback:
            story = _build_fallback_story(
                material=material,
                timeline=timeline,
                profile=profile,
                source_type=source_type,
                reason="model_timeout",
            )
        else:
            raise

    if profile:
        story_profile = _merge_profile(story.get("profile"), profile)
        story["profile"] = story_profile

    # attach meta for frontend
    story["meta"].update(
        {
            "sourceType": source_type,
            "conversationIds": payload.get("conversationIds"),
            "dateFrom": payload.get("dateFrom"),
            "dateTo": payload.get("dateTo"),
            "includeAssistant": include_assistant,
            "material": trunc_meta,
        }
    )

    return ApiResponse(ok=True, data=story)


@router.post("/profile/story/save", response_model=ApiResponse)
def profile_story_save(payload: dict[str, Any], user_id: str = Depends(deps.get_current_user_id)):
    story = payload.get("story")
    source = payload.get("source") or {}
    profile = _normalize_profile(payload.get("profile"))

    if not isinstance(story, dict):
        raise HTTPException(status_code=400, detail="story is required")

    story = _normalize_story(story)
    if profile:
        story_profile = _merge_profile(story.get("profile"), profile)
        story["profile"] = story_profile

    database = db.get_db()
    account_id = _get_active_account_id(database, user_id)

    stories = _coll(database, "profile_stories")

    now = _now()
    story_id = f"s_{ObjectId()}"

    doc = {
        "_id": story_id,
        "userId": user_id,
        "accountId": account_id,
        # User-scope sharing: history query no longer filters by accountId.
        "scope": "user",
        "story": story,
        "source": source,
        "createdAt": now,
        "savedAt": now,
        "updatedAt": now,
    }

    try:
        stories.insert_one(doc)
    except PyMongoError as e:
        raise HTTPException(status_code=503, detail=f"数据库不可用：{e}")

    return ApiResponse(ok=True, data={"storyId": story_id, "savedAt": now})


@router.post("/profile/story/extract", response_model=ApiResponse)
def profile_story_extract(payload: dict[str, Any], user_id: str = Depends(deps.get_current_user_id)):
    raw_text = payload.get("rawText")
    file_url = payload.get("fileUrl")
    file_mime = payload.get("fileMime")
    profile = _normalize_profile(payload.get("profile"))

    if not raw_text and not file_url:
        raise HTTPException(status_code=400, detail="rawText or fileUrl is required")

    text_parts: list[str] = []
    if isinstance(raw_text, str) and raw_text.strip():
        text_parts.append(raw_text.strip())

    if file_url:
        fp = resolve_local_path_from_files_url(file_url)
        extracted, _meta = extract_text(fp, mime=file_mime)
        if extracted.strip():
            text_parts.append(extracted.strip())

    text = "\n\n".join(text_parts).strip()
    if not text:
        raise HTTPException(status_code=422, detail="no extractable text")

    max_chars = 20000
    if len(text) > max_chars:
        text = text[:max_chars] + "\n(内容已截断)"

    profile_hint = ""
    if profile:
        profile_hint = "\n\n已有资料（用于补全或纠错）：\n" + __import__("json").dumps(profile, ensure_ascii=False)

    prompt = (
        "你是成长档案资料整理助手。请根据原始材料生成一份成长日记 story JSON。\n"
        "要求：\n"
        "1) 严格输出 JSON，不要输出任何额外文字。\n"
        "2) JSON 结构必须包含：storyVersion(number=1), title(string), chapters(array), milestones(array), meta(object)。\n"
        "3) chapters[*] 必须包含：chapterTitle(string), paragraphs(array of string), timeline(array of {at, summary})。\n"
        "4) milestones[*] 必须包含：title, at, summary, type。\n"
        "5) timeline.at 和 milestones.at 使用 ISO 8601 字符串。\n"
        "6) 需要抽取并填充 profile：{name, learningGoal, preferences}。\n"
        "7) 需要提供 sourceMaterialSummary（对原始材料的简短摘要，string）。\n"
        "8) 不要编造不存在的事实。\n"
        "原始材料如下：\n"
        + text
        + profile_hint
    )

    story = _ai_json_reply(prompt, stage="extract")
    story = _normalize_story(story)

    story.setdefault("sourceMaterialSummary", "")

    if profile:
        story_profile = _merge_profile(story.get("profile"), profile)
        story["profile"] = story_profile

    return ApiResponse(ok=True, data=story)


@router.get("/profile/stories", response_model=ApiResponse)
def profile_stories_list(
    page: int = 1,
    pageSize: int = 20,
    user_id: str = Depends(deps.get_current_user_id),
):
    if page < 1:
        page = 1
    if pageSize < 1:
        pageSize = 20
    if pageSize > 100:
        pageSize = 100

    database = db.get_db()
    _ = _get_active_account_id(database, user_id)
    stories = _coll(database, "profile_stories")

    query: dict[str, Any] = {
        "userId": user_id,
        "deletedAt": {"$exists": False},
    }

    try:
        cursor = stories.find(query)
        try:
            cursor = cursor.sort("updatedAt", -1)
        except Exception:
            pass

        # best-effort total for real pymongo; fake collections may not support count
        total = None
        try:
            total = stories.count_documents(query)  # type: ignore[attr-defined]
        except Exception:
            total = None

        skip = (page - 1) * pageSize
        items_raw = list(cursor)
        items_raw = items_raw[skip : skip + pageSize]

        items: list[dict[str, Any]] = []
        for d in items_raw:
            story = d.get("story") or {}
            title = d.get("title") or (story.get("title") if isinstance(story, dict) else None)
            items.append(
                {
                    "storyId": str(d.get("_id")),
                    "title": title or "",
                    "savedAt": _dt_to_iso(d.get("savedAt") or d.get("createdAt")),
                    "updatedAt": _dt_to_iso(d.get("updatedAt") or d.get("savedAt") or d.get("createdAt")),
                }
            )

        data = {"items": items, "page": page, "pageSize": pageSize}
        if isinstance(total, int):
            data["total"] = total
        else:
            data["total"] = len(items)

        return ApiResponse(ok=True, data=data)
    except PyMongoError as e:
        raise HTTPException(status_code=503, detail=f"数据库不可用：{e}")


@router.get("/profile/story/list", response_model=ApiResponse)
def profile_story_list_compat(
    page: int = 1,
    pageSize: int = 20,
    user_id: str = Depends(deps.get_current_user_id),
):
    """Compatibility alias for legacy frontend path."""
    return profile_stories_list(page=page, pageSize=pageSize, user_id=user_id)


@router.get("/profile/stories/{story_id}", response_model=ApiResponse)
def profile_stories_detail(story_id: str, user_id: str = Depends(deps.get_current_user_id)):
    database = db.get_db()
    _ = _get_active_account_id(database, user_id)
    stories = _coll(database, "profile_stories")

    doc = stories.find_one({"_id": story_id, "userId": user_id, "deletedAt": {"$exists": False}})
    if not doc:
        raise HTTPException(status_code=404, detail="story not found")

    data = {
        "storyId": str(doc.get("_id")),
        "savedAt": _dt_to_iso(doc.get("savedAt") or doc.get("createdAt")),
        "updatedAt": _dt_to_iso(doc.get("updatedAt") or doc.get("savedAt") or doc.get("createdAt")),
        "source": doc.get("source") or {},
        "story": doc.get("story") or {},
    }
    return ApiResponse(ok=True, data=data)


@router.get("/profile/story/detail/{story_id}", response_model=ApiResponse)
def profile_story_detail_compat(story_id: str, user_id: str = Depends(deps.get_current_user_id)):
    """Compatibility alias for legacy frontend path."""
    return profile_stories_detail(story_id=story_id, user_id=user_id)


@router.post("/profile/stories/{story_id}/update", response_model=ApiResponse)
def profile_stories_update(story_id: str, payload: dict[str, Any], user_id: str = Depends(deps.get_current_user_id)):
    payload = payload or {}
    profile = _normalize_profile(payload.get("profile"))
    story_payload = payload.get("story")

    if not profile and not isinstance(story_payload, dict):
        raise HTTPException(status_code=400, detail="profile or story is required")

    database = db.get_db()
    _ = _get_active_account_id(database, user_id)
    stories = _coll(database, "profile_stories")

    doc = stories.find_one({"_id": story_id, "userId": user_id, "deletedAt": {"$exists": False}})
    if not doc:
        raise HTTPException(status_code=404, detail="story not found")

    if isinstance(story_payload, dict):
        story = story_payload
    else:
        story = doc.get("story") if isinstance(doc, dict) else {}

    story = _normalize_story(story)
    if profile:
        story_profile = _merge_profile(story.get("profile"), profile)
        story["profile"] = story_profile

    now = _now()

    try:
        stories.update_one(
            {"_id": story_id, "userId": user_id, "deletedAt": {"$exists": False}},
            {"$set": {"story": story, "updatedAt": now}},
        )
    except PyMongoError as e:
        raise HTTPException(status_code=503, detail=f"数据库不可用：{e}")

    return ApiResponse(ok=True, data={"updatedAt": _dt_to_iso(now)})


@router.post("/profile/stories/{story_id}/delete", response_model=ApiResponse)
def profile_stories_delete(story_id: str, user_id: str = Depends(deps.get_current_user_id)):
    database = db.get_db()
    _ = _get_active_account_id(database, user_id)
    stories = _coll(database, "profile_stories")
    now = _now()

    try:
        r = stories.update_one(
            {"_id": story_id, "userId": user_id, "deletedAt": {"$exists": False}},
            {"$set": {"deletedAt": now, "updatedAt": now}},
        )
    except PyMongoError as e:
        raise HTTPException(status_code=503, detail=f"数据库不可用：{e}")

    matched = getattr(r, "matched_count", 1)
    if not matched:
        raise HTTPException(status_code=404, detail="story not found")
    return ApiResponse(ok=True, data={})
