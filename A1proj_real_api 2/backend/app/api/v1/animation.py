"""SOP 步骤动画演示 — 按需生成，不预加载。"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.config import get_settings
from langchain_openai import ChatOpenAI

router = APIRouter(prefix="/animation", tags=["动画演示"])

PROMPT = """生成一个简洁的HTML演示页面。展示这个维修步骤的操作动画。

步骤描述：{step_desc}

必须：
- 完整HTML（含<!DOCTYPE html>、<style>、<body>）
- 纯CSS动画（@keyframes），不用JS
- 深色背景#0a0f1d，青色主色#00c8b4
- 用div/圆形/线条表示设备，不用图片
- 一个主要动画元素（工具移动、信号波纹、状态灯闪烁等）
- 步骤文字在动画上方
- 循环3次后停在最终状态
- 手机竖屏适配，简洁明了
- 总共不超过150行HTML

直接输出HTML代码，不要解释。"""


class AnimationRequest(BaseModel):
    step_desc: str
    step_title: str = ""


@router.post("/generate")
async def generate_animation(req: AnimationRequest):
    settings = get_settings()
    if not settings.api_key:
        raise HTTPException(status_code=500, detail="API Key 未配置")

    try:
        model = ChatOpenAI(
            model=settings.LLM_MODEL,
            openai_api_key=settings.api_key,
            openai_api_base=settings.api_base,
            temperature=0.5,
            max_tokens=2048,
            timeout=60,
        )
        response = model.invoke(PROMPT.format(step_desc=req.step_desc or req.step_title))
        html = response.content.strip()
        for prefix in ["```html", "```"]:
            if html.startswith(prefix):
                html = html[len(prefix):]
        if html.endswith("```"):
            html = html[:-3]
        html = html.strip()
        return {"html": html, "title": req.step_title or req.step_desc[:20]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")
