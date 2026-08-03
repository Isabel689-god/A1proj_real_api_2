"""SOP 步骤动画演示生成 API — LLM 动态生成 HTML 页面。"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.config import get_settings
from langchain_openai import ChatOpenAI

router = APIRouter(prefix="/animation", tags=["动画演示"])

ANIMATION_PROMPT = """你是工业设备维修培训动画师。根据下面的维修步骤，生成一个独立的完整HTML页面，
用CSS动画和简单图形演示这个操作过程。工人看这个页面就能直观理解应该怎么操作。

要求：
1. 必须是完整的HTML文件（含<!DOCTYPE html>、<style>、<body>）
2. 用CSS动画（@keyframes）展示操作动作，不要用JavaScript
3. 用简单的div/圆形/线条表示设备和工具，不要用图片
4. 背景深色科技风（#0a0f1d），主色青绿（#00c8b4）
5. 步骤文字叠加在动画上方
6. 动画循环播放3次后停在最终状态
7. 整个页面简洁明了，适配手机竖屏

维修步骤：{step_desc}

直接输出HTML代码，不要解释。"""


class AnimationRequest(BaseModel):
    step_desc: str
    step_title: str = ""


@router.post("/generate")
async def generate_animation(req: AnimationRequest):
    """调用 LLM 生成步骤动画 HTML。"""
    settings = get_settings()
    if not settings.api_key:
        raise HTTPException(status_code=500, detail="LLM API Key 未配置")

    try:
        model = ChatOpenAI(
            model=settings.LLM_MODEL,
            openai_api_key=settings.api_key,
            openai_api_base=settings.api_base,
            temperature=0.7,
            max_tokens=4096,
            timeout=120,
        )
        prompt = ANIMATION_PROMPT.format(step_desc=req.step_desc)
        response = model.invoke(prompt)
        html = response.content.strip()
        # 清理markdown代码块包裹
        if html.startswith("```html"):
            html = html[7:]
        if html.startswith("```"):
            html = html[3:]
        if html.endswith("```"):
            html = html[:-3]
        html = html.strip()
        return {"html": html, "title": req.step_title}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")
