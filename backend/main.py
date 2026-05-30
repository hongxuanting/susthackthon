import uuid
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agents_core import ending_agent, generate_fallback_scene_image_result, opening_agent, option_agent, planner_agent, scene_image_agent, transition_agent, world_agent
from schemas import SceneImageRequest, WorldGenerateRequest
from store import delete_session, get_session, save_session

app = FastAPI(title="WorldForge Agent Game API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class InitInput(BaseModel):
    world_background: str
    world_rules: List[str] = Field(default_factory=list)
    style_mode: str = "classic"


class ChoiceInput(BaseModel):
    session_id: str
    choice_id: str


class RestartInput(BaseModel):
    session_id: str


def get_phase(turn_count):
    if turn_count <= 3:
        return "opening"
    if turn_count <= 6:
        return "rising"
    if turn_count <= 10:
        return "crisis"
    if turn_count <= 13:
        return "climax"
    return "ending"


def normalize_style_mode(style_mode: str | None):
    if style_mode in ["classic", "meme", "chaos"]:
        return style_mode
    return "classic"


def _default_flags() -> Dict[str, int]:
    return {
        "bravery": 0,
        "wisdom": 0,
        "kindness": 0,
        "ambition": 0,
        "chaos": 0,
        "danger": 0,
        "truth": 0,
    }


def _merge_flags(flags: Dict[str, int], delta: Dict[str, Any]) -> Dict[str, int]:
    if isinstance(delta, BaseModel):
        delta = delta.model_dump(exclude_none=True)

    for key, value in (delta or {}).items():
        if key in flags:
            try:
                flags[key] += int(value)
            except (TypeError, ValueError):
                continue
    return flags


@app.post("/api/world/generate")
async def generate_world(payload: WorldGenerateRequest):
    raw_input = payload.world_input or payload.input or payload.prompt or ""
    world_input = raw_input.strip()
    if not world_input:
        raise HTTPException(status_code=400, detail="world_input is required")

    try:
        style_mode = normalize_style_mode(payload.style_mode)
        data = await world_agent(world_input, style_mode)
        return data.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"world_agent error: {str(e)}")


@app.post("/api/story/init")
async def init_story(payload: InitInput):
    try:
        style_mode = normalize_style_mode(payload.style_mode)
        session_id = str(uuid.uuid4())
        plan = await planner_agent(payload.world_background, payload.world_rules, style_mode)
        opening = await opening_agent(payload.world_background, plan.model_dump(), style_mode)

        state = {
            "session_id": session_id,
            "world_background": payload.world_background,
            "world_rules": payload.world_rules,
            "plan": plan.model_dump(exclude_none=True),
            "player_profile": plan.player_profile.model_dump(exclude_none=True),
            "current_scene": opening.scene,
            "current_question": opening.question,
            "current_options": [],
            "history": [],
            "flags": _default_flags(),
            "turn_count": 0,
            "max_turns": 15,
            "phase": "opening",
            "is_finished": False,
            "ending": None,
            "style_mode": style_mode,
        }

        options = await option_agent(state)
        state["current_options"] = [o.model_dump(exclude_none=True) for o in options.options]
        save_session(session_id, state)

        return {
            "session_id": session_id,
            "player_profile": state["player_profile"],
            "scene": state["current_scene"],
            "question": state["current_question"],
            "options": state["current_options"],
            "turn_count": state["turn_count"],
            "max_turns": state["max_turns"],
            "phase": state["phase"],
            "style_mode": state["style_mode"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"story_init error: {str(e)}")


@app.post("/api/story/scene-image")
async def generate_scene_image(payload: SceneImageRequest):
    scene = payload.scene.strip()
    if not scene:
        raise HTTPException(status_code=400, detail="scene is required")

    style_mode = normalize_style_mode(payload.style_mode)
    try:
        return await scene_image_agent(
            scene=scene,
            style_mode=style_mode,
            player_identity=(payload.player_identity or "").strip(),
        )
    except Exception as e:
        print("[scene-image] unexpected failure:", repr(e))
        return generate_fallback_scene_image_result(
            scene,
            style_mode,
            f"scene image agent failed: {type(e).__name__}: {e}; using static fallback illustration",
        )


@app.post("/api/story/choose")
async def choose(payload: ChoiceInput):
    state = get_session(payload.session_id)
    if not state:
        raise HTTPException(status_code=404, detail="session not found")

    try:
        choice = None
        for opt in state.get("current_options", []):
            if opt.get("id") == payload.choice_id:
                choice = opt
                break

        if not choice:
            raise HTTPException(status_code=400, detail="invalid choice_id")

        step = await transition_agent(state, choice)

        _merge_flags(state["flags"], choice.get("effects", {}))
        _merge_flags(state["flags"], step.state_delta)

        state["history"].append(
            {
                "turn": state["turn_count"] + 1,
                "scene": state["current_scene"],
                "question": state["current_question"],
                "choice": choice,
                "result": step.new_scene,
                "important_event": step.important_event,
            }
        )

        state["turn_count"] += 1
        state["phase"] = get_phase(state["turn_count"])
        state["current_scene"] = step.new_scene
        state["current_question"] = step.question

        can_finish = False
        if state["turn_count"] >= state["max_turns"]:
            can_finish = True
        elif state["style_mode"] == "chaos" and state["turn_count"] >= 2 and step.should_finish:
            can_finish = True
        elif state["style_mode"] == "meme" and state["turn_count"] >= 4 and step.should_finish:
            can_finish = True
        elif state["style_mode"] == "classic" and state["turn_count"] >= 5 and step.should_finish:
            can_finish = True

        if can_finish:
            ending = await ending_agent(state)
            state["is_finished"] = True
            state["ending"] = ending.model_dump(exclude_none=True)
            save_session(state["session_id"], state)
            return {
                "is_finished": True,
                "ending": state["ending"],
                "turn_count": state["turn_count"],
                "max_turns": state["max_turns"],
                "style_mode": state["style_mode"],
            }

        options = await option_agent(state)
        state["current_options"] = [o.model_dump(exclude_none=True) for o in options.options]
        save_session(state["session_id"], state)

        return {
            "is_finished": False,
            "scene": state["current_scene"],
            "question": state["current_question"],
            "options": state["current_options"],
            "turn_count": state["turn_count"],
            "max_turns": state["max_turns"],
            "phase": state["phase"],
            "style_mode": state["style_mode"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"story_choose error: {str(e)}")


@app.get("/api/story/{session_id}")
async def get_story(session_id: str):
    state = get_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="session not found")
    return state


@app.post("/api/story/restart")
async def restart(payload: RestartInput):
    delete_session(payload.session_id)
    return {"ok": True}
