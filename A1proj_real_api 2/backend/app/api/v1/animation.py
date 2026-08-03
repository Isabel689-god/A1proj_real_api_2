"""SOP 步骤动画演示 — 按需生成，不预加载。"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.config import get_settings
from langchain_openai import ChatOpenAI

router = APIRouter(prefix="/animation", tags=["动画演示"])

PROMPT = """你是一个工业设备维修动画师。根据下面的维修步骤，生成一个逼真的工厂设备操作演示HTML页面。

维修步骤：{step_desc}

严格要求：
1. 完整HTML文件（DOCTYPE、style、body）
2. 纯CSS动画（@keyframes），零JavaScript
3. 深色工业风背景#0a1020，主色#00e5b0，辅色#ff6b35
4. 模拟真实工厂设备外观——用CSS画出：数控面板/万用表/编码器/伺服电机/机械臂/传送带/报警灯/液压杆等
5. 必须有至少2个联动动画（如：探头下降+面板读数变化、报警灯闪烁+电机停转）
6. 使用box-shadow、gradient、border做出金属/塑料质感
7. 步骤文字以HUD风格叠加在动画上方
8. 循环3次后定格在完成状态
9. 适配手机竖屏（max-width:420px居中）
10. 控制在180行内，不要废话

直接输出HTML代码："""



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
            temperature=0.3,
            max_tokens=1500,
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
