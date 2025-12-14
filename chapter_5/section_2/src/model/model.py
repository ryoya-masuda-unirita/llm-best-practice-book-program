from typing import Annotated, Sequence

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """Deep think agent state for novel generation."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_request: str
    theme: str | None
    outline: str | None
    draft: str | None
    final_novel: str | None
    thinking_depth: int


class NovelOutline(BaseModel):
    """Novel outline structure."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    title: str = Field(..., description="Title of the novel")
    theme: str = Field(..., description="Main theme of the novel")
    setting: str = Field(..., description="Time and place setting")
    characters: list[str] = Field(..., description="Main characters with brief descriptions")
    plot_points: list[str] = Field(..., description="Key plot points in order")
    tone: str = Field(..., description="Overall tone and style of the novel")


class NovelResult(BaseModel):
    """Final novel result."""

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    title: str = Field(..., description="Title of the novel")
    content: str = Field(..., description="Full novel content")
    word_count: int = Field(..., description="Total word count")
    theme: str = Field(..., description="Theme of the novel")

    def to_markdown(self) -> str:
        """Convert the novel to markdown format."""
        return f"""# {self.title}

---

{self.content}

---

**Theme**: {self.theme}
**Word Count**: {self.word_count}
"""


THEME_ELEMENTS: dict[str, dict] = {
    "loneliness": {
        "emotional_core": "Isolation and longing for connection",
        "symbols": ["Empty rooms", "Single footprints", "Unanswered calls", "Distant lights"],
        "metaphors": ["An island in a crowded sea", "Echo without response"],
        "conflicts": ["Self vs. Society", "Fear vs. Desire for connection"],
        "settings": ["Urban apartments", "Remote locations", "Crowded places where one feels alone"],
        "archetypes": ["The Outsider", "The Wanderer", "The Misunderstood"],
    },
    "redemption": {
        "emotional_core": "Transformation through acknowledgment and change",
        "symbols": ["Rising sun", "Water/cleansing", "Broken chains", "New growth"],
        "metaphors": ["Phoenix from ashes", "Light after darkness"],
        "conflicts": ["Past vs. Present", "Guilt vs. Forgiveness"],
        "settings": ["Places of past mistakes", "New beginnings", "Sacred spaces"],
        "archetypes": ["The Fallen Hero", "The Redeemer", "The Witness"],
    },
    "love": {
        "emotional_core": "Connection, vulnerability, and transformation",
        "symbols": ["Intertwined paths", "Shared warmth", "Bridges", "Mirrors"],
        "metaphors": ["Two flames becoming one", "Finding home in another"],
        "conflicts": ["Fear vs. Trust", "Independence vs. Union"],
        "settings": ["Chance meeting places", "Intimate spaces", "Transitional locations"],
        "archetypes": ["Star-crossed lovers", "The Unexpected Match", "The Devotee"],
    },
    "loss": {
        "emotional_core": "Grief, absence, and the search for meaning",
        "symbols": ["Empty chairs", "Fading photographs", "Autumn leaves", "Silence"],
        "metaphors": ["A missing piece of a puzzle", "Echo of what was"],
        "conflicts": ["Holding on vs. Letting go", "Memory vs. Moving forward"],
        "settings": ["Places of shared memories", "Transitional spaces", "Nature in flux"],
        "archetypes": ["The Mourner", "The Survivor", "The Memory Keeper"],
    },
    "growth": {
        "emotional_core": "Transformation through challenge and self-discovery",
        "symbols": ["Seeds/plants", "Mountains", "Doors/thresholds", "Seasons changing"],
        "metaphors": ["Caterpillar to butterfly", "Climbing toward light"],
        "conflicts": ["Comfort vs. Change", "Fear vs. Courage"],
        "settings": ["Journeys", "New environments", "Testing grounds"],
        "archetypes": ["The Hero", "The Mentor", "The Shadow Self"],
    },
}


CHARACTER_TEMPLATES: list[dict] = [
    {
        "role": "protagonist",
        "traits": ["determined", "flawed", "growing"],
        "template": {
            "want": "A clear external goal",
            "need": "An internal truth to discover",
            "flaw": "A weakness that creates obstacles",
            "strength": "A quality that will aid their journey",
        },
    },
    {
        "role": "catalyst",
        "traits": ["mysterious", "influential", "transformative"],
        "template": {
            "function": "Challenges or changes the protagonist",
            "connection": "How they relate to the main character",
            "secret": "Hidden depth or motivation",
        },
    },
    {
        "role": "mirror",
        "traits": ["contrasting", "reflective", "illuminating"],
        "template": {
            "function": "Shows alternative path or validates growth",
            "contrast": "How they differ from protagonist",
            "shared_element": "What connects them despite differences",
        },
    },
]


TONE_ELEMENTS: dict[str, dict[str, str]] = {
    "dramatic": {
        "opening": "Start with tension or a hook that promises conflict",
        "escalation": "Each scene raises stakes progressively",
        "climax": "Maximum tension, forced choice",
        "resolution": "Consequences of the climax unfold",
    },
    "hopeful": {
        "opening": "Begin in difficulty but with hints of possibility",
        "escalation": "Challenges met with growing resilience",
        "climax": "A moment of doubt before breakthrough",
        "resolution": "Earned optimism and forward momentum",
    },
    "bittersweet": {
        "opening": "Establish what is precious and at risk",
        "escalation": "Gains and losses intertwined",
        "climax": "A choice between two valued things",
        "resolution": "Acceptance of both joy and sorrow",
    },
    "dark": {
        "opening": "Foreshadow the inevitable with small details",
        "escalation": "Hope appears only to be undermined",
        "climax": "The darkest moment, truth revealed",
        "resolution": "Aftermath that lingers",
    },
    "uplifting": {
        "opening": "Show the character's struggle clearly",
        "escalation": "Small victories build momentum",
        "climax": "A test of everything learned",
        "resolution": "Transformation fully realized",
    },
}


STYLE_GUIDES: dict[str, dict[str, list[str]]] = {
    "literary": {
        "characteristics": ["Rich imagery", "Complex sentences", "Symbolic depth", "Careful word choice"],
        "techniques": [
            "Use metaphor and simile sparingly but powerfully",
            "Vary sentence structure for rhythm",
            "Choose specific nouns and active verbs",
            "Layer meaning through subtext",
        ],
        "avoid": ["Purple prose", "Over-explanation", "Clichés"],
    },
    "minimalist": {
        "characteristics": ["Economy of words", "Implication over statement", "White space", "Precise details"],
        "techniques": [
            "Cut unnecessary adjectives and adverbs",
            "Trust the reader to infer",
            "Use short, declarative sentences",
            "Let silence speak",
        ],
        "avoid": ["Overwriting", "Redundancy", "Excessive description"],
    },
    "lyrical": {
        "characteristics": ["Musical quality", "Emotional resonance", "Poetic imagery", "Flowing rhythm"],
        "techniques": [
            "Pay attention to sound and rhythm",
            "Use repetition for effect",
            "Create vivid sensory experiences",
            "Let language sing",
        ],
        "avoid": ["Forced poetry", "Sacrificing clarity for beauty", "Inconsistent voice"],
    },
    "contemporary": {
        "characteristics": ["Natural dialogue", "Modern sensibility", "Accessible prose", "Authentic voice"],
        "techniques": [
            "Write how people actually speak",
            "Ground abstract ideas in concrete details",
            "Balance description with action",
            "Maintain consistent, authentic voice",
        ],
        "avoid": ["Dated language", "Pretension", "Over-stylization"],
    },
}
