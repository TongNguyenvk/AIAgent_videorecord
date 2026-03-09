from pydantic import BaseModel, Field
from typing import Literal, Optional
from enum import Enum


class ActionType(str, Enum):
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    PAUSE = "pause"
    KEY = "key"


class ParsedAction(BaseModel):
    """Action parsed from natural language input."""
    action: ActionType
    target: Optional[str] = None
    url: Optional[str] = None
    text: Optional[str] = None
    direction: Optional[Literal["up", "down"]] = None
    ms: Optional[int] = None
    key: Optional[str] = None  # For key action (e.g., "Enter", "Escape")


class Coordinates(BaseModel):
    """Pixel coordinates returned by Vision AI."""
    x: int
    y: int
    confidence: float
    reasoning: Optional[str] = None


class ResolvedAction(BaseModel):
    """Action with resolved CSS selector after Vision AI + DOM lookup."""
    action: ActionType
    target: Optional[str] = None
    url: Optional[str] = None
    text: Optional[str] = None
    direction: Optional[Literal["up", "down"]] = None
    ms: Optional[int] = None
    key: Optional[str] = None  # For key action
    selector: Optional[str] = None
    coordinates: Optional[Coordinates] = None


class WebreelStep(BaseModel):
    """A single step in a webreel config."""
    action: str
    selector: Optional[str] = None
    url: Optional[str] = None
    text: Optional[str] = None
    ms: Optional[int] = None
    y: Optional[int] = None
    delay: Optional[int] = None
    charDelay: Optional[int] = None
    key: Optional[str] = None  # For key action


class WebreelVideo(BaseModel):
    """Config for a single video."""
    url: str
    viewport: dict = Field(default_factory=lambda: {"width": 1920, "height": 1080})
    defaultDelay: int = 400
    steps: list[WebreelStep]


class WebreelConfig(BaseModel):
    """Full webreel.config.json structure."""
    schema_url: str = Field(
        default="https://webreel.dev/schema/v1.json",
        alias="$schema"
    )
    videos: dict[str, WebreelVideo]

    model_config = {"populate_by_name": True}

    def to_dict(self) -> dict:
        """Serialize to dict with correct $schema key."""
        data = self.model_dump(by_alias=True, exclude_none=True)
        return data
