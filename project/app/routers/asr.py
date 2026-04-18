from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps import get_current_user_id
from app.schemas import ApiResponse, AsrRequest, AsrResponseData

router = APIRouter(tags=["ASR"])


@router.post("/asr", response_model=ApiResponse)
def asr(payload: AsrRequest, user_id: str = Depends(get_current_user_id)):
    # 第一阶段：占位实现（返回空文本）。
    # 后续：接入通义千问语音/多模态模型，读取 audioUrl 并产出转写。
    data = AsrResponseData(text="", durationMs=None)
    return ApiResponse(ok=True, data=data)
