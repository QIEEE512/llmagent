from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    ok: bool = True
    # 前端登录页对接约定：成功 code=0, message='ok'
    # 失败场景当前仍以 FastAPI 的 HTTPException.detail 为主（后续可统一包装 ok=false）。
    code: int = 0
    message: str = "ok"
    data: Any | None = None


class RegisterRequest(BaseModel):
    name: str
    account: str
    phone: str | None = None
    password: str


class RegisterResponseData(BaseModel):
    userId: str


class LoginRequest(BaseModel):
    account: str
    password: str


class MeResponseData(BaseModel):
    id: str
    name: str
    account: str


class AccountItem(BaseModel):
    id: str
    name: str
    account: str


class AccountsListResponseData(BaseModel):
    items: list[AccountItem]


class AccountsCreateRequest(BaseModel):
    name: str


class AccountsSwitchRequest(BaseModel):
    accountId: str


class AccountsSwitchResponseData(BaseModel):
    activeAccountId: str


class LoginUser(BaseModel):
    id: str
    name: str
    account: str


class LoginResponseData(BaseModel):
    accessToken: str
    expiresIn: int
    user: LoginUser


class RecommendationItem(BaseModel):
    id: str
    text: str


class RecommendationsResponseData(BaseModel):
    items: list[RecommendationItem]


class ChatAttachment(BaseModel):
    type: Literal["image", "file"]
    url: str


class ChatRequest(BaseModel):
    text: str
    attachments: list[ChatAttachment] | None = None
    meta: dict[str, Any] | None = None


class ChatResponseData(BaseModel):
    answer: str
    conversationId: str
    messageId: str


class UploadResponseData(BaseModel):
    url: str
    mime: str
    size: int


class AsrRequest(BaseModel):
    audioUrl: str | None = None
    format: str | None = None
    sampleRate: int | None = None


class AsrResponseData(BaseModel):
    text: str
    durationMs: int | None = None


class AvatarProfile(BaseModel):
    # FRONTEND_TODO.md 约定：3~12（前端限制）。
    age: int = Field(ge=3, le=12)
    interests: list[str] = []
    style: str | None = None
    freeText: str | None = None


class AvatarVoice(BaseModel):
    presetId: str
    note: str | None = None


class AvatarOutput(BaseModel):
    characterStyle: str | None = None


class AvatarGenerateRequest(BaseModel):
    portraitUrl: str
    profile: AvatarProfile
    voice: AvatarVoice
    output: AvatarOutput | None = None


class AvatarGenerateResponseData(BaseModel):
    avatarId: str
    imageUrl: str
    meta: dict[str, Any] | None = None


class AvatarActiveResponseData(BaseModel):
    avatarId: str
    imageUrl: str
    portraitUrl: str | None = None
    profile: AvatarProfile | None = None
    voice: AvatarVoice | None = None
    createdAt: int | None = None