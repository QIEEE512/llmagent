from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from pymongo.errors import PyMongoError

import app.db as db
from app.services.oss import presign_get_url

router = APIRouter(tags=["PublicShare"])


def _coll(database, name: str):
    try:
        return getattr(database, name)
    except Exception:
        return database[name]


def _now() -> datetime:
    return datetime.utcnow()


def _is_expired(doc: dict[str, Any]) -> bool:
    exp = doc.get("expiresAt")
    if isinstance(exp, datetime):
        return exp <= _now()
    return False


def _escape_html(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )

def _render_story_html(*, story: dict[str, Any]) -> str:
    title = _escape_html(str(story.get("title") or "成长档案"))

    parts: list[str] = []
    parts.append(f"<h1 class='h1'>{title}</h1>")

    profile = story.get("profile") if isinstance(story, dict) else None
    if isinstance(profile, dict):
        name = _escape_html(str(profile.get("name") or "").strip())
        goal = _escape_html(str(profile.get("learningGoal") or "").strip())
        pref = _escape_html(str(profile.get("preferences") or "").strip())
        if name or goal or pref:
            parts.append("<h2 class='h2'>档案资料</h2>")
            parts.append("<ul class='ul'>")
            if name:
                parts.append(f"<li class='li'><span class='muted'>姓名</span> {name}</li>")
            if goal:
                parts.append(f"<li class='li'><span class='muted'>学习目标</span> {goal}</li>")
            if pref:
                parts.append(f"<li class='li'><span class='muted'>学习偏好</span> {pref}</li>")
            parts.append("</ul>")

    chapters = story.get("chapters") or []
    if isinstance(chapters, list) and chapters:
        for i, ch in enumerate(chapters, start=1):
            if not isinstance(ch, dict):
                continue
            ch_title = _escape_html(str(ch.get("chapterTitle") or f"章节 {i}"))
            parts.append(f"<h2 class='h2'>{ch_title}</h2>")
            paras = ch.get("paragraphs") or []
            if isinstance(paras, list) and paras:
                for p in paras:
                    parts.append(f"<p class='p'>{_escape_html(str(p))}</p>")

    milestones = story.get("milestones") or []
    if isinstance(milestones, list) and milestones:
        parts.append("<h2 class='h2'>里程碑</h2>")
        parts.append("<ul class='ul'>")
        for ms in milestones:
            if not isinstance(ms, dict):
                continue
            at = _escape_html(str(ms.get("at") or ""))
            m_title = _escape_html(str(ms.get("title") or ""))
            summary = _escape_html(str(ms.get("summary") or ""))
            parts.append(
                f"<li class='li'><span class='muted'>{at}</span> <b>{m_title}</b> {summary}</li>"
            )
        parts.append("</ul>")

    return "\n".join(parts)


@router.get("/s/{share_id}")
def public_share_download(share_id: str, format: str = Query("pdf", description="docx|pdf")):
    """Public download entry.

    Behavior:
    - not found -> 404
    - revoked/expired -> 410
    - active -> 302 redirect to a short-lived signed url
    """

    database = db.get_db()
    shares = _coll(database, "profile_story_shares")
    exports = _coll(database, "profile_story_exports")

    try:
        share = shares.find_one({"_id": share_id})
    except PyMongoError as e:
        raise HTTPException(status_code=503, detail=f"数据库不可用：{e}")

    if not share:
        raise HTTPException(status_code=404, detail="share not found")

    if (share.get("status") or "active") == "revoked":
        raise HTTPException(status_code=410, detail="share revoked")

    if _is_expired(share):
        raise HTTPException(status_code=410, detail="share expired")

    export_id = str(share.get("exportId") or "").strip()
    if not export_id:
        raise HTTPException(status_code=410, detail="share invalid")

    try:
        exp_doc = exports.find_one({"_id": export_id})
    except PyMongoError as e:
        raise HTTPException(status_code=503, detail=f"数据库不可用：{e}")

    if not exp_doc:
        raise HTTPException(status_code=410, detail="export not found")

    fmt = (format or "docx").strip().lower()
    if fmt not in ("docx", "pdf"):
        fmt = "docx"

    if fmt == "pdf":
        object_key = str(exp_doc.get("pdfObjectKey") or "").strip()
    else:
        object_key = str(exp_doc.get("objectKey") or "").strip()
    if not object_key:
        raise HTTPException(status_code=410, detail="export invalid")

    # optional auditing
    try:
        shares.update_one({"_id": share_id}, {"$set": {"lastAccessAt": _now()}, "$inc": {"accessCount": 1}})
    except Exception:
        pass

    try:
        if fmt == "pdf":
            signed = presign_get_url(
                object_key=object_key,
                response_content_disposition="inline",
            )
        else:
            # Force download for docx
            signed = presign_get_url(
                object_key=object_key,
                response_content_disposition="attachment",
            )
    except Exception:
        raise HTTPException(status_code=503, detail="oss presign failed")

    return RedirectResponse(url=signed, status_code=302)


@router.get("/s/{share_id}/view", response_class=HTMLResponse)
def public_share_page(share_id: str):

        """Public web page (default: HTML content).

        This endpoint is public (no auth). It renders the story content as HTML,
        and provides buttons to download Word/PDF.
        """

        database = db.get_db()
        shares = _coll(database, "profile_story_shares")
        exports = _coll(database, "profile_story_exports")
        stories = _coll(database, "profile_stories")

        try:
                share = shares.find_one({"_id": share_id})
        except PyMongoError as e:
                raise HTTPException(status_code=503, detail=f"数据库不可用：{e}")

        if not share:
                raise HTTPException(status_code=404, detail="share not found")
        if (share.get("status") or "active") == "revoked":
                raise HTTPException(status_code=410, detail="share revoked")
        if _is_expired(share):
                raise HTTPException(status_code=410, detail="share expired")

        export_id = str(share.get("exportId") or "").strip()
        if not export_id:
                raise HTTPException(status_code=410, detail="share invalid")

        try:
                exp_doc = exports.find_one({"_id": export_id})
        except PyMongoError as e:
                raise HTTPException(status_code=503, detail=f"数据库不可用：{e}")
        if not exp_doc:
                raise HTTPException(status_code=410, detail="export not found")

        story_id = str(exp_doc.get("storyId") or share.get("storyId") or "").strip()
        if not story_id:
                raise HTTPException(status_code=410, detail="story not found")

        try:
                story_doc = stories.find_one({"_id": story_id})
        except PyMongoError as e:
                raise HTTPException(status_code=503, detail=f"数据库不可用：{e}")
        if not story_doc:
                raise HTTPException(status_code=410, detail="story not found")

        story = story_doc.get("story") or {}
        if not isinstance(story, dict):
                story = {}

        title = _escape_html(str(story.get("title") or "成长档案"))
        pdf_url = f"/s/{share_id}?format=pdf"
        docx_url = f"/s/{share_id}?format=docx"
        story_html = _render_story_html(story=story)

        html = f"""<!doctype html>
<html lang=\"zh-CN\">
    <head>
        <meta charset=\"utf-8\" />
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
        <title>{title}</title>
        <style>
            :root {{ color-scheme: light; }}
            body {{ margin: 0; font-family: -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif; background: #f6f7fb; color: #111; }}
            .wrap {{ max-width: 960px; margin: 0 auto; padding: 16px; }}
            .card {{ background: #fff; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,.06); overflow: hidden; }}
            .bar {{ display:flex; gap: 12px; align-items:center; justify-content: space-between; padding: 12px 16px; border-bottom: 1px solid #eee; position: sticky; top: 0; background: #fff; z-index: 10; }}
            .title {{ font-size: 16px; font-weight: 700; color: #111; overflow:hidden; text-overflow: ellipsis; white-space: nowrap; }}
            .actions {{ display:flex; gap: 10px; flex-wrap: wrap; justify-content: flex-end; }}
            .actions a {{ display:inline-block; padding: 8px 12px; border-radius: 10px; text-decoration:none; font-size: 14px; }}
            .btn-primary {{ background: #1677ff; color: #fff; }}
            .btn-ghost {{ background: #f0f5ff; color: #1677ff; }}
            .content {{ padding: 16px; }}
            .h1 {{ font-size: 26px; margin: 4px 0 16px; }}
            .h2 {{ font-size: 18px; margin: 18px 0 10px; }}
            .p {{ font-size: 15px; line-height: 1.8; margin: 10px 0; }}
            .ul {{ margin: 8px 0 0 18px; padding: 0; }}
            .li {{ margin: 8px 0; line-height: 1.6; }}
            .muted {{ color: #666; font-size: 12px; margin-right: 6px; }}
            .hint {{ font-size: 12px; color:#666; padding: 10px 16px; border-top: 1px solid #eee; background: #fff; }}
        </style>
    </head>
    <body>
        <div class=\"wrap\">
            <div class=\"card\">
                <div class=\"bar\">
                    <div class=\"title\">成长档案预览</div>
                    <div class=\"actions\">
                        <a class=\"btn-ghost\" href=\"{pdf_url}\" target=\"_blank\" rel=\"noreferrer\">打开/下载 PDF</a>
                        <a class=\"btn-primary\" href=\"{docx_url}\" target=\"_blank\" rel=\"noreferrer\">下载 Word</a>
                    </div>
                </div>
                <div class=\"content\">{story_html}</div>
                <div class=\"hint\">提示：如浏览器不支持内嵌 PDF，可直接使用右上角按钮下载或新窗口打开。</div>
            </div>
        </div>
    </body>
</html>"""

        return HTMLResponse(content=html)
