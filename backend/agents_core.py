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
IMAGE_MODEL = (os.getenv("OPENAI_IMAGE_MODEL", "") or "").strip()
MOCK_AI = (os.getenv("MOCK_AI", "false") or "").strip().lower() in {"1", "true", "yes", "on"}
MOCK_IMAGE = (os.getenv("MOCK_IMAGE", "false") or "").strip().lower() in {"1", "true", "yes", "on"}


def _read_image_timeout() -> float:
    try:
        return max(1.0, min(float(os.getenv("IMAGE_TIMEOUT_SECONDS", "10")), 10.0))
    except ValueError:
        return 10.0


IMAGE_TIMEOUT_SECONDS = _read_image_timeout()


def _create_openai_client(api_key: str, base_url: str, max_retries: int | None = None) -> OpenAI:
    params = {"api_key": api_key}
    if base_url:
        params["base_url"] = base_url
    if max_retries is not None:
        params["max_retries"] = max_retries
    return OpenAI(**params)


text_client = None if MOCK_AI else _create_openai_client(TEXT_API_KEY, TEXT_BASE_URL)
image_client = None if MOCK_IMAGE or not IMAGE_MODEL else _create_openai_client(IMAGE_API_KEY, IMAGE_BASE_URL, max_retries=0)

T = TypeVar("T", bound=BaseModel)

_ALLOWED_EFFECT_KEYS = {"bravery", "wisdom", "kindness", "ambition", "chaos", "danger", "truth"}

_DEFAULT_OPTIONS = {
    "A": {"text": "直接冲进去", "style": "brave", "effects": {"bravery": 1, "danger": 1}},
    "B": {"text": "先躲起来观察", "style": "cautious", "effects": {"wisdom": 1, "danger": -1}},
    "C": {"text": "救下眼前的人", "style": "kind", "effects": {"kindness": 1, "truth": 1}},
    "D": {"text": "赌一把大的", "style": "ambitious", "effects": {"ambition": 1, "chaos": 1}},
}

_SCENE_TYPE_RULES = {
    "ruined_city": ("废弃街区", "废城", "废墟", "破败", "荒废", "残垣", "断壁", "坍塌", "倒塌", "崩塌", "裂开", "腐朽", "涂鸦"),
    "cyberpunk_city": ("赛博", "霓虹", "无人机", "芯片", "义体", "电子屏", "数据", "未来都市", "巡逻机", "机械都市"),
    "battlefield": ("战场", "壕沟", "战壕", "炮火", "阵地", "士兵", "炮弹", "枪声", "轰炸", "军队"),
    "campus": ("校园", "学校", "教室", "学生", "宿舍", "操场", "教学楼", "图书馆", "大学"),
    "indoor_ruin": ("废弃室内", "走廊", "地下室", "仓库", "实验室", "大厅", "隧道", "地铁站", "楼梯间"),
    "desert": ("沙漠", "沙丘", "沙地", "荒野", "荒漠", "戈壁", "黄沙", "烈日"),
    "forest": ("森林", "树林", "林地", "树海", "丛林"),
    "coast": ("海边", "海岸", "沙滩", "码头", "海面", "礁石"),
    "night_street": ("夜晚街头", "夜街", "深夜街道", "雨夜街道", "小巷", "街灯"),
    "urban_city": ("城市", "都市", "街区", "街道", "高楼", "建筑"),
}

_VISUAL_ELEMENT_RULES = {
    "drone": ("无人机", "巡逻机", "飞行器"),
    "fire": ("火焰", "着火", "燃烧", "火光"),
    "explosion": ("爆炸", "炸开", "爆裂", "炮弹", "轰炸"),
    "pipe": ("管道", "管线", "管道口", "管道入口", "破口"),
    "water_hint": ("水源", "流水", "水痕", "水滴", "井盖", "寻水", "干涸", "供水"),
    "rain": ("雨", "暴雨", "雨夜", "雨幕"),
    "neon": ("霓虹", "灯牌", "电子屏"),
    "buildings": ("建筑", "高楼", "街区", "楼房", "墙壁"),
    "dust": ("尘土", "黄沙", "灰尘", "干燥", "腐朽"),
    "monster": ("怪物", "异变", "触手", "巨兽", "古神"),
    "idol": ("神像", "雕像", "祭坛"),
    "orange": ("橙子", "橘子"),
    "cat_like": ("哈基米", "猫", "猫咪"),
    "rider": ("骑手", "外卖员", "外卖小哥"),
    "graffiti": ("涂鸦", "警告", "标记"),
    "chip": ("芯片", "密钥", "数据盘"),
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


def build_scene_image_prompt(
    scene_summary: str,
    visual_keywords: List[str],
    style_mode: str = "classic",
) -> str:
    keyword_text = "、".join(visual_keywords[:5])
    suffix = {
        "classic": "数字插画，电影感，游戏剧情CG，光影明显，快速生成。",
        "meme": "轻夸张，漫画感，剧情插图，快速生成。",
        "chaos": "荒诞猎奇，混乱感，戏剧性强，快速生成。",
    }.get(style_mode, "数字插画，电影感，游戏剧情CG，光影明显，快速生成。")
    return f"{scene_summary}。画面包含：{keyword_text}。{suffix}"


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def extract_scene_visual_features(
    scene: str,
    style_mode: str = "classic",
    player_identity: str = "",
) -> Dict[str, Any]:
    """Extract fast, deterministic visual cues without another model call."""
    scene_text = scene or ""
    scores = {
        scene_type: sum(3 for keyword in keywords if keyword in scene_text)
        for scene_type, keywords in _SCENE_TYPE_RULES.items()
    }
    scene_type = max(scores, key=scores.get) if max(scores.values(), default=0) else "generic_mystery"
    visual_elements = [
        name for name, keywords in _VISUAL_ELEMENT_RULES.items()
        if _contains_any(scene_text, keywords)
    ]

    if "夜" in scene_text or "深夜" in scene_text:
        time_of_day = "night"
    elif _contains_any(scene_text, ("黄昏", "傍晚", "夕阳")):
        time_of_day = "twilight"
    else:
        time_of_day = "day"

    if "rain" in visual_elements:
        weather = "rain"
    elif "dust" in visual_elements:
        weather = "dry"
    elif _contains_any(scene_text, ("雾", "烟雾", "迷雾")):
        weather = "fog"
    else:
        weather = "clear"

    if style_mode == "chaos" or _contains_any(scene_text, ("荒诞", "离谱", "抽象", "乱入")):
        mood = "chaotic"
    elif _contains_any(scene_text, ("追逐", "追杀", "警报", "威胁", "包围", "心跳", "对峙", "逃")):
        mood = "tense"
    elif _contains_any(scene_text, ("废弃", "荒凉", "干涸", "腐朽", "尘土", "破败")):
        mood = "desolate"
    elif _contains_any(scene_text, ("线索", "隐藏", "秘密", "微弱", "神秘", "未知")):
        mood = "mysterious"
    elif style_mode == "meme" or _contains_any(scene_text, ("搞笑", "轻松", "滑稽")):
        mood = "playful"
    else:
        mood = "tense"

    if _contains_any(scene_text, ("追逐", "追杀", "逃跑", "冲刺", "狂奔", "逼近")):
        action = "chase"
    elif "explosion" in visual_elements:
        action = "explosion"
    elif _contains_any(scene_text, ("对峙", "包围", "拦住", "迎战", "争夺", "争吵", "冲突")):
        action = "confrontation"
    elif _contains_any(scene_text, ("发现", "线索", "吸引", "微弱", "注意")):
        action = "discovery"
    elif _contains_any(scene_text, ("进入", "步入", "走进", "踏入", "潜入")):
        action = "entering"
    elif _contains_any(scene_text, ("异变", "突变", "扭曲")):
        action = "anomaly"
    else:
        action = "exploration"

    if "water_hint" in visual_elements or "pipe" in visual_elements:
        focus_object, focus_label = "water_source", "水源线索"
    elif "chip" in visual_elements:
        focus_object, focus_label = "chip", "芯片交接"
    elif "explosion" in visual_elements:
        focus_object, focus_label = "explosion", "爆炸冲击"
    elif "monster" in visual_elements:
        focus_object, focus_label = "monster", "异常威胁"
    elif "idol" in visual_elements:
        focus_object, focus_label = "idol", "神像异变"
    else:
        focus_object, focus_label = "clue", "未知线索"

    if "drone" in visual_elements:
        threat = "drone"
    elif "monster" in visual_elements:
        threat = "monster"
    elif "explosion" in visual_elements or "fire" in visual_elements:
        threat = "blast"
    elif _contains_any(scene_text, ("追兵", "敌人", "士兵", "包围")):
        threat = "enemy"
    else:
        threat = "unknown"

    title_by_scene_type = {
        "ruined_city": "废弃街区",
        "cyberpunk_city": "霓虹追逃" if action == "chase" else "赛博都市",
        "battlefield": "壕沟异变" if action == "anomaly" else "战场危机",
        "campus": "教室异变" if action == "anomaly" else "校园事件",
        "indoor_ruin": "废弃走廊",
        "desert": "荒野线索",
        "forest": "林地迷踪",
        "coast": "海岸异动",
        "night_street": "夜街追踪",
        "urban_city": "城市危机",
        "generic_mystery": "未知现场",
    }
    accent_color = {
        "classic": "#8fb3ff",
        "meme": "#facc15",
        "chaos": "#fb923c",
    }.get(style_mode, "#8fb3ff")
    if focus_object == "water_source":
        accent_color = "#67e8f9"

    return {
        "scene_type": scene_type,
        "time_of_day": time_of_day,
        "mood": mood,
        "weather": weather,
        "location_keywords": [
            keyword for keyword in _SCENE_TYPE_RULES.get(scene_type, ())
            if keyword in scene_text
        ][:4],
        "visual_elements": visual_elements,
        "focus_object": focus_object,
        "focus_label": focus_label,
        "threat": threat,
        "action": action,
        "player_role": _truncate_text(player_identity, 24) or "主角",
        "accent_color": accent_color,
        "title": title_by_scene_type[scene_type],
        "style_mode": style_mode,
    }


def _local_scene_summary(scene: str, style_mode: str, player_identity: str = "") -> str:
    features = extract_scene_visual_features(scene, style_mode, player_identity)
    elements = set(features["visual_elements"])
    scene_text = scene or ""

    if "钟楼" in scene_text:
        if "碎片" in scene_text or "发光" in scene_text:
            return "钟楼深处发光碎片悬浮"
        if "齿轮" in scene_text or "停滞" in scene_text:
            return "古老钟楼深处齿轮骤停"
        return "钟楼深处古老钟盘静默"
    if "cat_like" in elements and "rider" in elements:
        return "外卖骑手与猫咪荒诞乱入"
    if "广场" in scene_text and _contains_any(scene_text, ("居民", "人群", "小镇")):
        return "小镇广场居民诡异静默"
    if _contains_any(scene_text, ("雨夜", "霓虹")) and "chip" in elements:
        return "雨夜霓虹街头芯片追逃"
    if features["focus_object"] == "water_source":
        if features["action"] == "confrontation":
            return "废墟阴影中争夺供水站"
        if "pipe" in elements:
            return "地下管道深处泛起蓝光"
        return "暗巷深处浮现隐秘水源"
    if features["focus_object"] == "chip":
        return "暗巷霓虹下芯片交接追逃"
    if features["threat"] == "drone" and features["action"] == "chase":
        return "霓虹雨夜无人机紧张追逃"
    if _contains_any(scene_text, ("枪战", "枪声", "追杀")):
        return "街巷枪战中警戒灯闪烁"
    if features["scene_type"] == "battlefield" and features["action"] == "explosion":
        return "壕沟炮火中爆炸骤然升起"
    if features["scene_type"] == "campus" and features["action"] == "anomaly":
        return "校园教室内突发诡异异变"
    if features["threat"] == "monster":
        return "怪物逼近时现场彻底失控"
    if features["action"] == "chase":
        return "街头阴影中追兵步步逼近"
    if features["action"] == "confrontation":
        return "危机现场双方紧张对峙"
    if features["scene_type"] == "ruined_city":
        return "裂街废墟中残楼危险倾斜"
    if features["scene_type"] == "indoor_ruin":
        return "废弃走廊深处暗藏线索"
    if features["scene_type"] == "desert":
        return "荒野深处微光线索浮现"
    return "暗处神秘线索发出微光"


def _extract_visual_keywords(
    scene: str,
    style_mode: str = "classic",
    player_identity: str = "",
) -> List[str]:
    features = extract_scene_visual_features(scene, style_mode, player_identity)
    elements = set(features["visual_elements"])
    keywords: List[str] = []

    def add(*values: str) -> None:
        for value in values:
            if value and value not in keywords and len(keywords) < 5:
                keywords.append(value)

    if "钟楼" in scene:
        add("古老钟楼")
        if _contains_any(scene, ("碎片", "发光")):
            add("发光碎片")
        elif _contains_any(scene, ("齿轮", "停滞")):
            add("停滞齿轮")
        else:
            add("巨大钟盘")
        add("昏暗楼梯")
    if _contains_any(scene, ("小镇", "广场")):
        add("小镇广场", "居民剪影")
    if features["scene_type"] == "ruined_city":
        add("城市废墟", "残破建筑")
    elif features["scene_type"] == "cyberpunk_city":
        add("霓虹街道", "未来都市")
    elif features["scene_type"] == "battlefield":
        add("战场壕沟", "炮火硝烟")
    elif features["scene_type"] == "campus":
        add("校园建筑", "教室走廊")
    elif features["scene_type"] == "indoor_ruin":
        add("昏暗室内", "破败走廊")
    elif features["scene_type"] == "desert":
        add("荒野沙地", "干燥尘土")
    elif features["scene_type"] == "forest":
        add("幽暗树林", "斑驳树影")
    elif features["scene_type"] == "coast":
        add("海岸礁石", "翻涌海面")
    elif features["scene_type"] == "night_street":
        add("夜色街巷", "昏暗路灯")

    if "water_hint" in elements:
        add("供水设施", "蓝色水光")
    if "pipe" in elements:
        add("地下管道", "蓝色水光")
    if "rain" in elements:
        add("密集雨线")
    if "neon" in elements:
        add("霓虹灯光")
    if "chip" in elements:
        add("发光芯片")
    if "drone" in elements:
        add("追踪无人机")
    if _contains_any(scene, ("枪战", "枪声")):
        add("枪战火光", "红色警戒灯")
    if "monster" in elements:
        add("逼近怪物")
    if "idol" in elements:
        add("诡异神像")
    if features["action"] == "chase":
        add("紧张追逃")
    elif features["action"] == "confrontation":
        add("紧张对峙")
    elif features["action"] == "explosion":
        add("爆炸火光")
    elif features["action"] == "discovery":
        add("神秘微光")
    elif features["action"] == "entering":
        add("探索身影")

    mood_keyword = {
        "chaotic": "混乱危机",
        "tense": "紧张气氛",
        "desolate": "荒凉阴影",
        "mysterious": "神秘阴影",
        "playful": "夸张气氛",
    }.get(features["mood"], "剧情危机")
    add(mood_keyword, "前景人物", "环境光影")
    return keywords[:5]


def summarize_scene_for_image(
    scene: str,
    style_mode: str = "classic",
    player_identity: str = "",
) -> Dict[str, Any]:
    """Compress one scene into a short visual description and 3-5 concrete cues."""
    return {
        "scene_summary": _local_scene_summary(scene, style_mode, player_identity),
        "visual_keywords": _extract_visual_keywords(scene, style_mode, player_identity),
    }


_FALLBACK_SCENE_IMAGE_URL = "/story-fallback.png"


def _fallback_scene_image_result(
    scene_summary: str,
    visual_keywords: List[str],
    style_mode: str,
    image_prompt: str = "",
    debug_message: str = "using static fallback illustration",
) -> Dict[str, Any]:
    prompt = image_prompt or build_scene_image_prompt(scene_summary, visual_keywords, style_mode)
    return {
        "image_url": _FALLBACK_SCENE_IMAGE_URL,
        "source": "fallback",
        "scene_summary": scene_summary,
        "visual_keywords": visual_keywords,
        "image_prompt": prompt,
        "debug_message": debug_message,
    }


def generate_fallback_scene_image_result(
    scene: str,
    style_mode: str = "classic",
    debug_message: str = "using static fallback illustration",
) -> Dict[str, Any]:
    visual_summary = summarize_scene_for_image(scene, style_mode)
    return _fallback_scene_image_result(
        visual_summary["scene_summary"],
        visual_summary["visual_keywords"],
        style_mode,
        debug_message=debug_message,
    )


def _extract_generated_image_url(response: Any) -> str:
    if not response.data:
        raise RuntimeError("image API returned no image data")

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
    raise RuntimeError("image API response did not include url or base64 data")


def _build_image_generation_params(prompt: str) -> Dict[str, Any]:
    is_gpt_image_model = IMAGE_MODEL.startswith("gpt-image") or IMAGE_MODEL == "chatgpt-image-latest"
    params: Dict[str, Any] = {
        "model": IMAGE_MODEL,
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024" if is_gpt_image_model else "512x512",
        "timeout": IMAGE_TIMEOUT_SECONDS,
    }
    if is_gpt_image_model:
        params["quality"] = "low"
    return params


def _format_image_generation_error(error: Exception, attempt: int) -> str:
    raw_error = str(error).strip() or repr(error)
    lowered = raw_error.lower()
    if isinstance(error, TimeoutError) or "timeout" in lowered or "timed out" in lowered:
        reason = f"timeout after {IMAGE_TIMEOUT_SECONDS:g}s"
    elif "model not found" in lowered or ("model" in lowered and "not found" in lowered):
        reason = "model not found"
    elif "unsupported endpoint" in lowered or "not supported" in lowered or "unsupported" in lowered:
        reason = "unsupported endpoint or parameter"
    else:
        reason = raw_error
    return (
        f"model={IMAGE_MODEL or '<empty>'}; attempt={attempt}/2; "
        f"reason={reason}; error={type(error).__name__}: {raw_error}"
    )


async def scene_image_agent(
    scene: str,
    style_mode: str = "classic",
    player_identity: str = "",
) -> Dict[str, Any]:
    visual_summary = summarize_scene_for_image(scene, style_mode, player_identity)
    scene_summary = visual_summary["scene_summary"]
    visual_keywords = visual_summary["visual_keywords"]
    prompt = build_scene_image_prompt(scene_summary, visual_keywords, style_mode)
    if MOCK_IMAGE:
        return _fallback_scene_image_result(
            scene_summary,
            visual_keywords,
            style_mode,
            prompt,
            f"model={IMAGE_MODEL or '<empty>'}; reason=MOCK_IMAGE enabled; using static fallback illustration",
        )
    if not IMAGE_MODEL:
        return _fallback_scene_image_result(
            scene_summary,
            visual_keywords,
            style_mode,
            prompt,
            "model=<empty>; reason=OPENAI_IMAGE_MODEL is empty; using static fallback illustration",
        )

    failure_messages = []
    for attempt in range(1, 3):
        try:
            if image_client is None:
                raise RuntimeError("image client is not configured")
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    image_client.images.generate,
                    **_build_image_generation_params(prompt),
                ),
                timeout=IMAGE_TIMEOUT_SECONDS,
            )
            return {
                "image_url": _extract_generated_image_url(response),
                "source": "generated",
                "debug_message": f"model={IMAGE_MODEL}; generated on attempt={attempt}/2",
                "scene_summary": scene_summary,
                "visual_keywords": visual_keywords,
                "image_prompt": prompt,
            }
        except Exception as e:
            debug_message = _format_image_generation_error(e, attempt)
            failure_messages.append(debug_message)
            print("[scene-image] image generation failed:", debug_message)

    return _fallback_scene_image_result(
        scene_summary,
        visual_keywords,
        style_mode,
        prompt,
        "; ".join(failure_messages) + "; using static fallback illustration",
    )


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
