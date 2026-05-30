import asyncio
import json
import os
import re
from typing import Any, Dict, List, Type, TypeVar

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

from schemas import EndingOut, FlagDelta, OpeningOut, Option, OptionsOut, PlanOut, StepOut, WorldOut

load_dotenv()

TEXT_API_KEY = os.getenv("OPENAI_API_KEY", "")
TEXT_BASE_URL = (os.getenv("OPENAI_BASE_URL", "") or "").strip()
TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4.1-mini"
IMAGE_API_KEY = os.getenv("OPENAI_IMAGE_API_KEY", "") or TEXT_API_KEY
IMAGE_BASE_URL = (os.getenv("OPENAI_IMAGE_BASE_URL", "") or "").strip() or TEXT_BASE_URL
IMAGE_MODEL = (os.getenv("OPENAI_IMAGE_MODEL", "") or "").strip() or "gpt-image-1"
MOCK_AI = (os.getenv("MOCK_AI", "false") or "").strip().lower() in {"1", "true", "yes", "on"}


def _read_image_timeout() -> float:
    try:
        return max(1.0, float(os.getenv("IMAGE_TIMEOUT_SECONDS", "60") or 60))
    except ValueError:
        return 60.0


IMAGE_TIMEOUT_SECONDS = _read_image_timeout()


def _create_openai_client(api_key: str, base_url: str, max_retries: int | None = None) -> OpenAI:
    params = {"api_key": api_key}
    if base_url:
        params["base_url"] = base_url
    if max_retries is not None:
        params["max_retries"] = max_retries
    return OpenAI(**params)


text_client = None if MOCK_AI else _create_openai_client(TEXT_API_KEY, TEXT_BASE_URL)

T = TypeVar("T", bound=BaseModel)

_ALLOWED_EFFECT_KEYS = {"bravery", "wisdom", "kindness", "ambition", "chaos", "danger", "truth"}

_DEFAULT_OPTIONS = {
    "A": {"text": "直接冲进去", "style": "brave", "effects": {"bravery": 1, "danger": 1}},
    "B": {"text": "先躲起来观察", "style": "cautious", "effects": {"wisdom": 1, "danger": -1}},
    "C": {"text": "救下眼前的人", "style": "kind", "effects": {"kindness": 1, "truth": 1}},
    "D": {"text": "赌一把大的", "style": "ambitious", "effects": {"ambition": 1, "chaos": 1}},
}

def strip_inline_options(question: str) -> str:
    """Remove accidental inline A/B/C/D choices from a question."""
    if not question:
        return ""

    option_marker = re.search(r"(?<![A-Za-z0-9])[A-DＡ-Ｄ]\s*[.．、:：)]", question)
    cleaned = question[: option_marker.start()] if option_marker else question
    return re.sub(r"\s+", " ", cleaned).strip()


def _truncate_text(text: str, max_length: int) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    return cleaned[:max_length]


def _extract_generated_image_url(response: Any) -> str:
    if not response.data:
        return ""

    image = response.data[0]
    image_url = getattr(image, "url", None)
    image_base64 = getattr(image, "b64_json", None)
    if isinstance(image, dict):
        image_url = image_url or image.get("url")
        image_base64 = image_base64 or image.get("b64_json")

    if image_url:
        return image_url
    if image_base64:
        return f"data:image/png;base64,{image_base64}"
    return ""


def _image_prompt(scene_text: str, style_mode: str) -> str:
    chars = re.findall(r"[\u4e00-\u9fff]", scene_text or "")
    if chars:
        return "".join(chars[:10])
    return _truncate_text(scene_text, 10)


def _is_retryable_image_error(error: Exception) -> bool:
    error_name = type(error).__name__
    error_text = str(error)
    retry_markers = (
        "APIConnectionError",
        "Connection error",
        "timeout",
        "Request timed out",
    )
    combined = f"{error_name}: {error_text}"
    return any(marker.lower() in combined.lower() for marker in retry_markers)


async def image_agent(scene_text: str, style_mode: str = "classic") -> Dict[str, Any]:
    prompt = _image_prompt(scene_text, style_mode)
    print("[image_agent] scene_text:", scene_text)
    print("[image_agent] 10_char_prompt:", prompt)
    last_error: Exception | None = None
    image_client = _create_openai_client(IMAGE_API_KEY, IMAGE_BASE_URL, max_retries=0)

    for attempt in range(1, 4):
        try:
            response = await asyncio.to_thread(
                image_client.images.generate,
                model=IMAGE_MODEL,
                prompt=prompt,
                n=1,
                size="1024x1024",
                timeout=IMAGE_TIMEOUT_SECONDS,
            )
            image_url = _extract_generated_image_url(response)
            if not image_url:
                raise RuntimeError("image response has no usable image")
            print(
                "[image_agent] result:",
                {
                    "success": True,
                    "image_url_length": len(image_url),
                    "debug_message": "",
                },
            )
            return {
                "success": True,
                "image_url": image_url,
                "debug_message": "",
            }
        except Exception as e:
            last_error = e
            print("[image_agent] attempt", attempt, "failed:", repr(e))
            if attempt >= 3 or not _is_retryable_image_error(e):
                print("[image_agent] model:", IMAGE_MODEL)
                print("[image_agent] base_url:", IMAGE_BASE_URL)
                print("[image_agent] prompt:", prompt)
                print("[image_agent] error:", repr(e))
                print(
                    "[image_agent] result:",
                    {
                        "success": False,
                        "image_url_length": 0,
                        "debug_message": f"{type(e).__name__}: {e}",
                    },
                )
                return {
                    "success": False,
                    "image_url": "",
                    "debug_message": f"{type(e).__name__}: {e}",
                }
            await asyncio.sleep(2)

    debug_message = f"{type(last_error).__name__}: {last_error}" if last_error else "Unknown image generation error"
    return {
        "success": False,
        "image_url": "",
        "debug_message": debug_message,
    }


def _normalize_world(data: WorldOut) -> WorldOut:
    values = data.model_dump()
    values["world_background"] = _truncate_text(values["world_background"], 220)
    values["world_rules"] = [_truncate_text(item, 60) for item in values["world_rules"][:3]]
    values["core_conflict"] = _truncate_text(values["core_conflict"], 80)
    values["main_forces"] = [_truncate_text(item, 50) for item in values["main_forces"][:2]]
    values["danger_sources"] = [_truncate_text(item, 50) for item in values["danger_sources"][:2]]
    values["tone"] = _truncate_text(values["tone"], 60)
    return WorldOut.model_validate(values)


def _mock_world(world_input: str, style_mode: str) -> WorldOut:
    return WorldOut(
        world_background=(
            f"这是一个围绕“{world_input}”展开的短篇互动世界。"
            "秩序表面仍在运转，但一场突发事件正在逼近。"
            "你将从事件中心醒来，立刻做出决定，并承担选择带来的结果。"
        ),
        world_rules=["选择会立刻改变局势", "每次行动都会留下后果", "故事可能自然提前结束"],
        core_conflict="你必须在局势失控前决定如何应对眼前危机。",
        main_forces=["维持现状的一方", "试图打破现状的一方"],
        danger_sources=["不断升级的突发事件", "错误选择带来的连锁后果"],
        tone=f"{style_mode} 模式下的短篇快速叙事。",
    )


def _normalize_plan(data: PlanOut) -> PlanOut:
    values = data.model_dump()
    profile = values["player_profile"]
    profile["identity"] = _truncate_text(profile["identity"], 30)
    profile["background"] = _truncate_text(profile["background"], 100)
    profile["goal"] = _truncate_text(profile["goal"], 80)
    profile["traits"] = [_truncate_text(item, 20) for item in profile["traits"][:3]]
    values["main_conflict"] = _truncate_text(values["main_conflict"], 100)
    values["phase_plan"] = {
        key: _truncate_text(value, 60)
        for key, value in values["phase_plan"].items()
    }
    values["possible_endings"] = [_truncate_text(item, 80) for item in values["possible_endings"][:3]]
    values["important_mystery"] = _truncate_text(values["important_mystery"], 60)
    values["must_resolve_before_end"] = [
        _truncate_text(item, 60) for item in values["must_resolve_before_end"][:2]
    ]
    return PlanOut.model_validate(values)


def _normalize_ending(data: EndingOut) -> EndingOut:
    values = data.model_dump()
    values["ending_title"] = _truncate_text(values["ending_title"], 30)
    values["ending_type"] = _truncate_text(values["ending_type"], 30)
    values["player_title"] = _truncate_text(values["player_title"], 30)
    values["ending_summary"] = _truncate_text(values["ending_summary"], 180)
    values["world_after_effect"] = _truncate_text(values["world_after_effect"], 180)
    values["choice_analysis"] = _truncate_text(values["choice_analysis"], 180)
    values["full_story"] = _truncate_text(values["full_story"], 500)
    return EndingOut.model_validate(values)


def _option_context(state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "world_background": state.get("world_background", ""),
        "player_profile": state.get("player_profile", {}),
        "current_scene": state.get("current_scene", ""),
        "current_question": state.get("current_question", ""),
        "flags": state.get("flags", {}),
        "turn_count": state.get("turn_count", 0),
        "style_mode": state.get("style_mode", "classic"),
        "recent_history": state.get("history", [])[-2:],
    }


def _transition_context(state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "world_background": state.get("world_background", ""),
        "player_profile": state.get("player_profile", {}),
        "current_scene": state.get("current_scene", ""),
        "flags": state.get("flags", {}),
        "turn_count": state.get("turn_count", 0),
        "max_turns": state.get("max_turns", 15),
        "recent_history": state.get("history", [])[-2:],
    }


def style_instruction(style_mode: str) -> str:
    if style_mode == "meme":
        return """
当前叙事模式：meme，轻松爽剧模式。

要求：
1. 短、轻松、有吐槽、有网感，但剧情仍然清楚。
2. 每轮立刻推进，不要长铺垫。
3. 一般 4 到 8 轮自然结束；骚操作形成结果时可以 should_finish=true。
4. 可以加入少量网络梗和反差梗，不要低俗，不要硬塞梗。
5. 输出必须是合法 JSON。
"""
    if style_mode == "chaos":
        return """
当前叙事模式：chaos，崩坏猎奇短剧模式。

要求：
1. 快、疯、抽象、离谱，可以跨时空串台，不要求严格现实因果。
2. 可以出现哈基米、外卖骑手、奇怪广播、广告牌、抽象 NPC、土味视频和弹幕吐槽。
3. 玩家可以因离谱理由失败、死亡、社死、被剧情踢出或被系统误删，但不要写血腥细节。
4. 第 2 次选择后就可以 should_finish=true，不要为了凑轮数强行续命。
5. 可以反高潮，但必须能看懂发生了什么。
6. 不要色情、仇恨或极端主义宣传；敏感历史只能采用荒诞反战讽刺视角。
7. 真实公众人物只能作为无害荒诞 cameo，不能造谣或侮辱。
8. 输出必须是合法 JSON。
"""
    return """
当前叙事模式：classic，短篇正剧模式。

要求：
1. 短、直接、沉浸，不玩梗，不吐槽。
2. 每轮立刻推进，不要强行史诗长篇。
3. 一般 5 到 10 轮自然结束；目标完成、失败、牺牲、逃离或真相揭露时可以 should_finish=true。
4. 输出必须是合法 JSON。
"""


def extract_json(text: str) -> Dict[str, Any]:
    if not text:
        raise ValueError("empty model response")

    cleaned = text.strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        while lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    if "```json" in cleaned or "```" in cleaned:
        cleaned = cleaned.replace("```json", "```")
        parts = cleaned.split("```")
        best = ""
        for part in parts:
            part = part.strip()
            if "{" in part and "}" in part:
                best = part
                break
        cleaned = best or cleaned

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start : end + 1]

    return json.loads(cleaned)


def _clean_effects(effects: Dict[str, Any]) -> Dict[str, int]:
    if isinstance(effects, BaseModel):
        effects = effects.model_dump(exclude_none=True)

    cleaned: Dict[str, int] = {}
    for key, value in (effects or {}).items():
        if key in _ALLOWED_EFFECT_KEYS:
            try:
                ivalue = int(value)
                cleaned[key] = max(-2, min(2, ivalue))
            except (TypeError, ValueError):
                continue
    return cleaned


def _ensure_four_options(data: OptionsOut) -> OptionsOut:
    by_id = {opt.id: opt for opt in data.options if opt.id in {"A", "B", "C", "D"}}
    final: List[Option] = []
    for oid in ["A", "B", "C", "D"]:
        if oid in by_id:
            existing = by_id[oid]
            text = _truncate_text(existing.text, 25) or _DEFAULT_OPTIONS[oid]["text"]
            final.append(Option(id=oid, text=text, style=existing.style, effects=_clean_effects(existing.effects)))
        else:
            fallback = _DEFAULT_OPTIONS[oid]
            final.append(Option(id=oid, text=fallback["text"], style=fallback["style"], effects=fallback["effects"]))
    return OptionsOut(options=final)


def _extract_text(response: Any) -> str:
    content = response.choices[0].message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
            else:
                text_val = getattr(item, "text", None)
                if text_val:
                    parts.append(text_val)
        return "".join(parts)
    return str(content)


def _chat_structured(output_model: Type[T], system_prompt: str, user_prompt: str, temperature: float = 0.8) -> T:
    raw_content = ""
    parse_error = None

    for attempt in range(2):
        try:
            params = {
                "model": TEXT_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": temperature,
            }
            if attempt == 0:
                params["response_format"] = {"type": "json_object"}

            response = text_client.chat.completions.create(**params)
            raw_content = _extract_text(response)
            data = extract_json(raw_content)
            return output_model.model_validate(data)
        except Exception as e:
            parse_error = e
            if attempt == 0:
                continue

    preview = (raw_content or "")[:500]
    raise RuntimeError(f"LLM parse failed after 2 attempts: {parse_error}; raw={preview}")


def _json_only_guard() -> str:
    return "你必须只输出一个 JSON 对象。不要输出 markdown。不要输出解释。不要输出代码块。不能破坏 JSON 结构。"


async def world_agent(world_input: str, style_mode: str = "classic") -> WorldOut:
    if MOCK_AI:
        return _normalize_world(_mock_world(world_input, style_mode))

    system_prompt = (
        "你是互动叙事游戏的世界观设计 Agent。"
        "你不是在写百科设定，也不是在写长篇小说背景。"
        "你只需要根据玩家输入，生成一个短小、直接、能马上开局的世界草案。"
        "world_background 控制在 120 到 220 字，不要超过 220 字。"
        "world_rules 最多 3 条，main_forces 最多 2 个，danger_sources 最多 2 个。"
        "core_conflict 和 tone 各写一句话。"
        "不要补充太多复杂势力、历史、地理、宗教或科技体系。重点是：立刻能玩。"
        "内容不要违法、色情或极端血腥。\n"
        f"{style_instruction(style_mode)}\n"
        f"{_json_only_guard()}"
    )
    user_prompt = (
        f"玩家世界设定输入：\n{world_input}\n\n"
        "请严格返回如下 JSON 结构：\n"
        "{\n"
        "  \"world_background\": \"...\",\n"
        "  \"world_rules\": [\"...\"],\n"
        "  \"core_conflict\": \"...\",\n"
        "  \"main_forces\": [\"...\"],\n"
        "  \"danger_sources\": [\"...\"],\n"
        "  \"tone\": \"...\"\n"
        "}"
    )
    data = _chat_structured(WorldOut, system_prompt, user_prompt)
    return _normalize_world(data)


async def image_agent(scene_text: str, style_mode: str = "classic") -> dict:
    image_prompt = _extract_image_prompt(scene_text)
    if not image_prompt:
        image_prompt = _truncate_text(scene_text, 10)

    try:
        if not image_client:
            raise RuntimeError("image api key is missing")

        response = image_client.images.generate(
            model=IMAGE_MODEL,
            prompt=image_prompt,
            n=1,
        )
        item = response.data[0] if getattr(response, "data", None) else None
        if item is None:
            raise RuntimeError("image model returned no data")

        image_url = ""
        if isinstance(item, dict):
            image_url = item.get("url") or ""
            b64_json = item.get("b64_json") or ""
        else:
            image_url = getattr(item, "url", "") or ""
            b64_json = getattr(item, "b64_json", "") or ""

        if b64_json:
            image_url = f"data:image/png;base64,{b64_json}"

        if not image_url:
            raise RuntimeError("image model returned empty image")

        return {
            "success": True,
            "image_url": image_url,
            "debug_message": "",
        }
    except Exception as e:
        print("[image_agent] model:", IMAGE_MODEL)
        print("[image_agent] base_url:", IMAGE_BASE_URL)
        print("[image_agent] scene_text:", scene_text)
        print("[image_agent] image_prompt:", image_prompt)
        print("[image_agent] error:", repr(e))
        return {
            "success": False,
            "image_url": "",
            "debug_message": str(e),
        }


async def planner_agent(world_background: str, world_rules: List[str], style_mode: str = "classic") -> PlanOut:
    system_prompt = (
        "你是互动剧情规划 Agent。"
        "生成短小的后台剧情计划，不直接展示给玩家。"
        "不要设计复杂的 15 轮大纲，不要设计长线伏笔，不要求每轮完成固定任务。"
        "player_profile 简短，main_conflict 一句话，phase_plan 每项一句短句。"
        "possible_endings 最多 3 个，每项一句话；must_resolve_before_end 最多 2 条。"
        "important_mystery 可以写“无”。"
        "普通故事允许在 5 到 10 轮自然结束，chaos 允许在 2 到 5 轮荒诞结束。"
        "玩家选择必须影响结局。\n"
        f"{style_instruction(style_mode)}\n"
        f"{_json_only_guard()}"
    )
    user_prompt = (
        f"世界背景：\n{world_background}\n\n"
        f"世界规则：\n{json.dumps(world_rules, ensure_ascii=False)}\n\n"
        "请严格返回如下 JSON 结构：\n"
        "{\n"
        "  \"player_profile\": {\n"
        "    \"identity\": \"...\",\n"
        "    \"background\": \"...\",\n"
        "    \"goal\": \"...\",\n"
        "    \"traits\": [\"...\"]\n"
        "  },\n"
        "  \"main_conflict\": \"...\",\n"
        "  \"phase_plan\": {\"opening\": \"...\", \"rising\": \"...\", \"crisis\": \"...\", \"climax\": \"...\", \"ending\": \"...\"},\n"
        "  \"possible_endings\": [\"...\"],\n"
        "  \"important_mystery\": \"...\",\n"
        "  \"must_resolve_before_end\": [\"...\"]\n"
        "}"
    )
    data = _chat_structured(PlanOut, system_prompt, user_prompt)
    return _normalize_plan(data)


async def opening_agent(world_background: str, plan: Dict[str, Any], style_mode: str = "classic") -> OpeningOut:
    system_prompt = (
        "你是开场剧情 Agent。"
        "直接把玩家扔进事件里，不要长铺垫。"
        "用第二人称“你”。scene 控制在 80 到 150 字，question 只能写一句简短提问。"
        "scene 和 question 都不能写 A/B/C/D 选项，也不能列举方案，选项只能由 option_agent 生成。"
        "不能提前剧透最终结局。\n"
        f"{style_instruction(style_mode)}\n"
        f"{_json_only_guard()}"
    )
    user_prompt = (
        f"世界背景：\n{world_background}\n\n"
        f"隐藏计划：\n{json.dumps(plan, ensure_ascii=False)}\n\n"
        "请严格返回如下 JSON 结构：\n"
        "{\n"
        "  \"scene\": \"...\",\n"
        "  \"question\": \"...\"\n"
        "}"
    )
    data = _chat_structured(OpeningOut, system_prompt, user_prompt)
    validated = OpeningOut.model_validate(data.model_dump())
    validated.scene = strip_inline_options(_truncate_text(validated.scene, 150))
    validated.question = strip_inline_options(_truncate_text(validated.question, 60))
    return validated


async def option_agent(state: Dict[str, Any]) -> OptionsOut:
    style_mode = state.get("style_mode", "classic")
    system_prompt = (
        "你是选项生成 Agent。必须正好输出 4 个选项，id 必须是 A/B/C/D。"
        "A 偏勇敢硬刚，B 偏苟住观察，C 偏救人或讲良心，D 偏作死、梭哈、搞事。"
        "每个 text 不超过 25 字，只写短促、可点击的一步动作，不要剧透后果。"
        "effects 只能用 bravery,wisdom,kindness,ambition,chaos,danger,truth，值通常在 -2 到 2。"
        "chaos 模式下 D 可以非常离谱，effects 可以是 ambition=1,chaos=2,danger=2。\n"
        f"{style_instruction(style_mode)}\n"
        f"{_json_only_guard()}"
    )
    user_prompt = (
        f"当前游戏状态：\n{json.dumps(_option_context(state), ensure_ascii=False)}\n\n"
        "请严格返回如下 JSON 结构：\n"
        "{\n"
        "  \"options\": [\n"
        "    {\"id\": \"A\", \"text\": \"...\", \"style\": \"...\", \"effects\": {\"bravery\": 1}},\n"
        "    {\"id\": \"B\", \"text\": \"...\", \"style\": \"...\", \"effects\": {\"wisdom\": 1}},\n"
        "    {\"id\": \"C\", \"text\": \"...\", \"style\": \"...\", \"effects\": {\"kindness\": 1}},\n"
        "    {\"id\": \"D\", \"text\": \"...\", \"style\": \"...\", \"effects\": {\"ambition\": 1}}\n"
        "  ]\n"
        "}"
    )
    try:
        result = _chat_structured(OptionsOut, system_prompt, user_prompt)
        validated = OptionsOut.model_validate(result.model_dump())
    except Exception:
        validated = OptionsOut(options=[])
    return _ensure_four_options(validated)


async def transition_agent(state: Dict[str, Any], choice: Dict[str, Any]) -> StepOut:
    style_mode = state.get("style_mode", "classic")
    extra = ""
    if style_mode == "chaos":
        extra = (
            "当前是 chaos 崩坏猎奇模式。"
            "你可以不严格遵守现实因果，允许哈基米、外卖骑手、广告牌、奇怪广播、抽象 NPC、现代梗与跨时代乱入。"
            "从第 2 次选择后可提前结束；玩家可因离谱倒霉事件失败、社死或被剧情踢出。"
            "若选择 D 或 flags.chaos/flags.danger 高，更易触发提前结局。"
            "若 should_finish=true，new_scene 要写清离谱事件，important_event 总结荒诞下线原因，"
            "question 可写“你的故事以一种很难评价的方式结束了。”"
        )

    system_prompt = (
        "你是剧情推进 Agent。必须承接玩家选择和最近历史，不能无视上下文。"
        "玩家选了什么，就立刻给结果。每一轮必须有明显事件推进。"
        "new_scene 使用第二人称“你”，控制在 100 到 180 字。question 只能写一句简短提问。"
        "不要复杂推导，不要长心理描写，不要铺垫十层因果，不要继续堆世界观。"
        "new_scene 和 question 都不能写 A/B/C/D 选项，选项只能由 option_agent 生成。"
        "你不需要强行把故事拖到第 15 轮。"
        "如果当前剧情已经形成明确结果、失败、胜利、死亡、逃脱、反转、崩坏、真相揭露或主线完成，可以让 should_finish=true。"
        "但必须保证 new_scene 说明清楚这一轮发生了什么。"
        "不要为了凑满 15 轮而继续水剧情。\n"
        f"{style_instruction(style_mode)}\n"
        f"{extra}\n"
        f"{_json_only_guard()}"
    )
    user_prompt = (
        f"精简状态：\n{json.dumps(_transition_context(state), ensure_ascii=False)}\n\n"
        f"玩家选择：\n{json.dumps(choice, ensure_ascii=False)}\n\n"
        "请严格返回如下 JSON 结构：\n"
        "{\n"
        "  \"new_scene\": \"...\",\n"
        "  \"question\": \"...\",\n"
        "  \"state_delta\": {\"bravery\": 0, \"wisdom\": 0, \"kindness\": 0, \"ambition\": 0, \"chaos\": 0, \"danger\": 0, \"truth\": 0},\n"
        "  \"important_event\": \"...\",\n"
        "  \"should_finish\": false,\n"
        "  \"next_phase\": \"opening|rising|crisis|climax|ending\"\n"
        "}"
    )
    result = _chat_structured(StepOut, system_prompt, user_prompt)
    validated = StepOut.model_validate(result.model_dump())
    validated.state_delta = _clean_effects(validated.state_delta)
    validated.new_scene = strip_inline_options(_truncate_text(validated.new_scene, 180))
    validated.question = strip_inline_options(_truncate_text(validated.question, 60))
    return validated


async def ending_agent(state: Dict[str, Any]) -> EndingOut:
    style_mode = state.get("style_mode", "classic")
    system_prompt = (
        "你是结局 Agent。请生成有记忆点的结局标题、玩家称号、结局类型、总结、世界影响、选择分析和完整故事。"
        "结局要短、狠、有记忆点，不要长篇升华，不要写成论文总结。"
        "ending_title 和 player_title 要短。ending_summary 控制在 100 到 180 字。"
        "world_after_effect 和 choice_analysis 各控制在 1 到 2 句话。full_story 控制在 300 到 500 字。"
        "chaos 模式允许损一点、荒诞、失败、反高潮和抽象称号，但必须可读且无血腥细节。\n"
        f"{style_instruction(style_mode)}\n"
        f"{_json_only_guard()}"
    )
    user_prompt = (
        f"完整状态：\n{json.dumps(state, ensure_ascii=False)}\n\n"
        "请严格返回如下 JSON 结构：\n"
        "{\n"
        "  \"ending_title\": \"...\",\n"
        "  \"ending_type\": \"...\",\n"
        "  \"player_title\": \"...\",\n"
        "  \"ending_summary\": \"...\",\n"
        "  \"world_after_effect\": \"...\",\n"
        "  \"choice_analysis\": \"...\",\n"
        "  \"full_story\": \"...\"\n"
        "}"
    )
    data = _chat_structured(EndingOut, system_prompt, user_prompt)
    return _normalize_ending(data)
