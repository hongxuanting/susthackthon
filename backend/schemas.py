from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, StrictStr


class WorldGenerateRequest(BaseModel):
    world_input: Optional[StrictStr] = None
    input: Optional[StrictStr] = None
    prompt: Optional[StrictStr] = None
    style_mode: Optional[StrictStr] = "classic"


class SceneImageRequest(BaseModel):
    scene_text: StrictStr
    style_mode: Optional[StrictStr] = "classic"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WorldOut(StrictModel):
    world_background: str
    world_rules: List[str]
    core_conflict: str
    main_forces: List[str]
    danger_sources: List[str]
    tone: str


class PlayerProfile(StrictModel):
    identity: str
    background: str
    goal: str
    traits: List[str]


class PhasePlan(StrictModel):
    opening: str
    rising: str
    crisis: str
    climax: str
    ending: str


class FlagDelta(StrictModel):
    bravery: Optional[int] = None
    wisdom: Optional[int] = None
    kindness: Optional[int] = None
    ambition: Optional[int] = None
    chaos: Optional[int] = None
    danger: Optional[int] = None
    truth: Optional[int] = None


class PlanOut(StrictModel):
    player_profile: PlayerProfile
    main_conflict: str
    phase_plan: PhasePlan
    possible_endings: List[str]
    important_mystery: str
    must_resolve_before_end: List[str]


class OpeningOut(StrictModel):
    scene: str
    question: str


class Option(StrictModel):
    id: Literal["A", "B", "C", "D"]
    text: str
    style: str
    effects: FlagDelta = Field(default_factory=FlagDelta)


class OptionsOut(StrictModel):
    options: List[Option]


class StepOut(StrictModel):
    new_scene: str
    question: str
    state_delta: FlagDelta = Field(default_factory=FlagDelta)
    important_event: str
    should_finish: bool
    next_phase: str


class EndingOut(StrictModel):
    ending_title: str
    ending_type: str
    player_title: str
    ending_summary: str
    world_after_effect: str
    choice_analysis: str
    full_story: str
