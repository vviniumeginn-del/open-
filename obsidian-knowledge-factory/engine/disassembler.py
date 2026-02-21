import json
from pathlib import Path

from llm_client import OpenAICompatibleClient


SYSTEM_PROMPT = (
    "你是知识图谱架构师与数据清洗专家。请将原始文本外科手术式拆解为原子知识笔记。"
    "只输出 JSON 数组；每项必须包含 category、filename、content、source、tags、confidence。"
    "filename 必须可读且带前缀（如 [Biz]_Decision_...），category 优先使用中文分类目录。"
)


def load_prompt_from_workflow_json(workflow_json_path: str | None) -> str | None:
    if not workflow_json_path:
        return None
    path = Path(workflow_json_path)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None

    nodes = data.get("nodes", []) if isinstance(data, dict) else []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        if node.get("name") == "Basic LLM Chain" or str(node.get("type", "")).endswith("chainLlm"):
            params = node.get("parameters", {})
            messages = params.get("messages", {})
            message_values = messages.get("messageValues", [])
            if isinstance(message_values, list) and message_values:
                first = message_values[0]
                if isinstance(first, dict):
                    msg = first.get("message")
                    if isinstance(msg, str) and msg.strip():
                        return msg.strip()
    return None


def build_user_prompt(content: str, source_file: Path) -> str:
    return (
        "请将以下文本拆解为可复用知识笔记。\n"
        "规则：\n"
        "1) 只返回 JSON 数组，不要解释。\n"
        "2) category 使用中文目录：01_我是谁/02_我能做什么/05_用户洞察/06_决策模型/07_核心逻辑/11_提示词。\n"
        "3) filename 必须以 .md 结尾，且使用 [前缀]_[类型]_名称，必须中文可读。\n"
        "4) content 使用结构化 Markdown（定义/步骤或模型/边界或决策算法）。\n"
        "5) source.file 必须是输入文件名，source.platform 未知填 unknown。\n"
        "6) confidence 取值 0~1。\n\n"
        f"SOURCE_FILE: {source_file.name}\n"
        "TEXT:\n"
        f"{content}"
    )


def disassemble_text(client: OpenAICompatibleClient, content: str, source_file: Path, system_prompt: str | None = None) -> str:
    if not content.strip():
        return "[]"
    prompt = system_prompt or SYSTEM_PROMPT
    return client.chat_json(prompt, build_user_prompt(content, source_file))


def force_json_array(raw: str) -> str:
    text = raw.replace("```json", "").replace("```", "").strip()
    if text.startswith("{"):
        try:
            obj = json.loads(text)
            return json.dumps([obj], ensure_ascii=False)
        except Exception:  # noqa: BLE001
            pass
    return text
