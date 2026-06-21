import logging
import requests
from config import settings

logger = logging.getLogger(__name__)

def call_qwen_api(query: str, context: str) -> str:
    logger.info("调用 qwen-max API")
    url = f"{settings.qwen_api_base}/chat/completions"
    headers = {"Authorization": f"Bearer {settings.qwen_api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "qwen-max",
        "messages": [
            {"role": "system", "content": f"你是知识库助手，只根据以下知识回答，不要编造。\n知识：{context}"},
            {"role": "user", "content": query}
        ],
        "temperature": 0.3
    }
    logger.info(f"[qwen-api] system prompt: 你是知识库助手，只根据以下知识回答，不要编造。\n知识：{context[:500]}{'...(截断)' if len(context) > 500 else ''}")
    logger.info(f"[qwen-api] user query: {query}")
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    logger.info("qwen-max API 调用成功")
    return resp.json()["choices"][0]["message"]["content"]

def call_ollama(query: str, context: str) -> str:
    logger.info(f"调用 Ollama 模型: {settings.ollama_model}")
    url = f"{settings.ollama_base}/api/chat"
    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": f"你是知识库助手，只根据以下知识回答：\n{context}"},
            {"role": "user", "content": query}
        ],
        "stream": False
    }
    logger.info(f"[ollama] system prompt: 你是知识库助手，只根据以下知识回答：\n{context[:500]}{'...(截断)' if len(context) > 500 else ''}")
    logger.info(f"[ollama] user query: {query}")
    resp = requests.post(url, json=payload, timeout=60)
    logger.info(f"Ollama 调用完成")
    return resp.json()["message"]["content"]

def ask_llm(query: str, context: str) -> tuple:
    model_used = "qwen-max-api"
    answer = ""
    logger.info(f"[ask_llm] qwen_api_key={'已配置' if settings.qwen_api_key else '未配置'}")
    if settings.qwen_api_key:
        try:
            answer = call_qwen_api(query, context)
        except Exception as e:
            logger.warning(f"qwen-max API 调用失败: {e}, 降级到 Ollama")
            answer = call_ollama(query, context)
            model_used = settings.ollama_model
    else:
        logger.warning("未检测到 QWEN_API_KEY，使用 Ollama")
        answer = call_ollama(query, context)
        model_used = settings.ollama_model
    return answer, model_used
