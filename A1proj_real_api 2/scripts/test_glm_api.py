"""单独测试真实智谱 GLM API 是否可用。运行前请先在 .env 填写真实 ZHIPU_API_KEY。"""
from app.providers.glm import GLMProvider


def main() -> None:
    provider = GLMProvider()
    answer = provider.chat([
        {"role": "system", "content": "你是一个接口连通性测试助手。"},
        {"role": "user", "content": "请只回复：API_OK"},
    ], max_tokens=20, temperature=0)
    print("真实 GLM API 返回：", answer)


if __name__ == "__main__":
    main()
