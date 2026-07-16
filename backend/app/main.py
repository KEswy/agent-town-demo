import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .llm import LLM_CLIENT, LLMGeneration
from .rag import HYBRID_INDEX


app = FastAPI(title="Agent Town Backend")

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
MEMORY_FILE = DATA_DIR / "memory.json"
CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
NPC_PROFILES_FILE = CONFIG_DIR / "npc_profiles.json"
KNOWLEDGE_BASE_FILE = CONFIG_DIR / "knowledge_base.json"
LLM_VALIDATION_LOG_FILE = DATA_DIR / "llm_validation_failures.jsonl"
MAX_LLM_VALIDATION_ATTEMPTS = 5
VALID_ELIMINATION_SOURCES = {
    "night_kill": "werewolf_kill",
    "witch_poison": "witch_poison",
    "hunter_shot": "hunter_shot",
    "exiled": "day_vote",
}

DEFAULT_WOLF_ROLES = {
    "werewolf": 4,
    "seer": 1,
    "witch": 1,
    "hunter": 1,
    "guard": 1,
    "villager": 4,
}
ROLE_LABELS = {
    "werewolf": "狼人",
    "seer": "预言家",
    "witch": "女巫",
    "hunter": "猎人",
    "guard": "守卫",
    "villager": "村民",
}
CAMP_BY_ROLE = {
    "werewolf": "werewolf",
    "seer": "good",
    "witch": "good",
    "hunter": "good",
    "guard": "good",
    "villager": "good",
}
GOD_ROLES = {"seer", "witch", "hunter", "guard"}
NPC_NAMES = [
    "梅西",
    "C罗",
    "周深",
    "梅长苏",
    "塞尔达",
    "小骑士",
    "大黄蜂",
    "喜羊羊",
    "懒羊羊",
    "洛洛",
    "奇异博士",
]
FIXED_NPC_COUNT = 11

NPC_PERSONALITIES = {
    "梅西": {
        "aggressiveness": 0.24,
        "cautiousness": 0.76,
        "deception": 0.34,
        "logic": 0.78,
        "empathy": 0.68,
        "leadership": 0.50,
    },
    "C罗": {
        "aggressiveness": 0.78,
        "cautiousness": 0.34,
        "deception": 0.50,
        "logic": 0.62,
        "empathy": 0.38,
        "leadership": 0.84,
    },
    "周深": {
        "aggressiveness": 0.20,
        "cautiousness": 0.68,
        "deception": 0.32,
        "logic": 0.66,
        "empathy": 0.88,
        "leadership": 0.42,
    },
    "梅长苏": {
        "aggressiveness": 0.38,
        "cautiousness": 0.88,
        "deception": 0.82,
        "logic": 0.95,
        "empathy": 0.52,
        "leadership": 0.76,
    },
    "塞尔达": {
        "aggressiveness": 0.52,
        "cautiousness": 0.72,
        "deception": 0.34,
        "logic": 0.72,
        "empathy": 0.70,
        "leadership": 0.68,
    },
    "小骑士": {
        "aggressiveness": 0.30,
        "cautiousness": 0.82,
        "deception": 0.45,
        "logic": 0.74,
        "empathy": 0.48,
        "leadership": 0.35,
    },
    "大黄蜂": {
        "aggressiveness": 0.74,
        "cautiousness": 0.70,
        "deception": 0.58,
        "logic": 0.78,
        "empathy": 0.46,
        "leadership": 0.72,
    },
    "喜羊羊": {
        "aggressiveness": 0.48,
        "cautiousness": 0.72,
        "deception": 0.60,
        "logic": 0.86,
        "empathy": 0.76,
        "leadership": 0.82,
    },
    "懒羊羊": {
        "aggressiveness": 0.16,
        "cautiousness": 0.50,
        "deception": 0.38,
        "logic": 0.50,
        "empathy": 0.80,
        "leadership": 0.28,
    },
    "洛洛": {
        "aggressiveness": 0.44,
        "cautiousness": 0.66,
        "deception": 0.52,
        "logic": 0.90,
        "empathy": 0.54,
        "leadership": 0.64,
    },
    "奇异博士": {
        "aggressiveness": 0.36,
        "cautiousness": 0.88,
        "deception": 0.74,
        "logic": 0.94,
        "empathy": 0.58,
        "leadership": 0.78,
    },
}


class TriggerEasterEgg(BaseModel):
    egg_id: str
    triggers: list[str]
    reply: str
    repeat_reply: str
    reveal_self_role: bool = False


class NPCProfile(BaseModel):
    npc_name: str
    role: str
    personality: str
    knowledge: list[str]
    speech_style: str = ""
    catchphrases: list[str] = Field(default_factory=list)
    easter_eggs: list[str] = Field(default_factory=list)
    trigger_easter_eggs: list[TriggerEasterEgg] = Field(default_factory=list)


class KnowledgeItem(BaseModel):
    npc_name: str
    title: str
    content: str
    keywords: list[str]


class ScoredKnowledgeItem(BaseModel):
    score: int
    keyword_score: int = 0
    vector_score: float = 0.0
    item: KnowledgeItem


class KnowledgeSearchResponse(BaseModel):
    npc_name: str
    message: str
    matched: bool
    score: int
    item: Optional[KnowledgeItem] = None
    results: list[ScoredKnowledgeItem] = Field(default_factory=list)
    retrieval_mode: str = "keyword"
    vector_model: str = ""


class ChatRequest(BaseModel):
    npc_name: str = "Guide"
    message: str = "你好"
    player_id: str = "player"


class ChatResponse(BaseModel):
    npc_name: str
    reply: str
    memory_count: int
    relationship_level: str
    knowledge_title: str = ""
    knowledge_titles: list[str] = Field(default_factory=list)
    retrieval_mode: str = "keyword"


class ClearMemoryResponse(BaseModel):
    deleted_count: int
    message: str


class ReloadConfigResponse(BaseModel):
    npc_count: int
    knowledge_count: int
    message: str


class MemoryItem(BaseModel):
    player_id: str
    npc_name: str
    player_message: str
    npc_reply: str
    created_at: str


class ApiHealthResponse(BaseModel):
    status: str
    llm_enabled: bool
    rag_enabled: bool
    provider: str


class LLMStatusResponse(BaseModel):
    enabled: bool
    provider: str
    model: str
    configured: bool
    base_url: str = ""


class RagStatusResponse(BaseModel):
    mode: str
    model_name: str
    dependency_available: bool
    initialized: bool
    document_count: int
    error: str = ""


class GameStartRequest(BaseModel):
    player_name: str = "玩家"
    npc_count: int = FIXED_NPC_COUNT
    roles: dict[str, int] = Field(default_factory=lambda: dict(DEFAULT_WOLF_ROLES))
    player_role: str = "random"
    enable_llm: bool = False
    enable_rag: bool = False


class CharacterState(BaseModel):
    id: int
    name: str
    is_player: bool
    role: str
    camp: str
    alive: bool = True
    personality: dict[str, float] = Field(default_factory=dict)
    emotion: dict[str, float] = Field(default_factory=dict)
    suspicion: dict[str, int] = Field(default_factory=dict)
    relationships: dict[str, dict[str, object]] = Field(default_factory=dict)
    memory_summary: str = ""


class CharacterView(BaseModel):
    id: int
    name: str
    is_player: bool
    alive: bool
    role_visible_to_player: Optional[str] = None
    suspicion_score: int = 0
    suspicion_level: str = "无"
    trust_to_player: Optional[float] = None
    trust_level: str = ""
    memory_count: int = 0
    private_question_used_today: bool = False
    claimed_role: Optional[str] = None
    public_claims: list[str] = Field(default_factory=list)
    is_sheriff: bool = False
    sheriff_campaign_status: str = ""


class PlayerPrivateInfo(BaseModel):
    role: str
    camp: str
    last_check_result: Optional[dict[str, object]] = None
    wolf_teammates: list[dict[str, object]] = Field(default_factory=list)
    witch_attacked_target: Optional[dict[str, object]] = None
    witch_antidote_available: bool = False
    witch_poison_available: bool = False
    hunter_can_shoot: bool = False
    action_history: list[str] = Field(default_factory=list)


class NightActionState(BaseModel):
    day: int
    actor_id: int
    action_type: str
    target_id: Optional[int] = None


class VoteState(BaseModel):
    day: int
    voter_id: int
    target_id: int
    reason: str = ""
    evidence_titles: list[str] = Field(default_factory=list)
    retrieval_mode: str = "keyword"
    weight: float = 1.0


class SpeechState(BaseModel):
    day: int
    character_id: int
    name: str
    speech: str
    is_player: bool
    evidence_titles: list[str] = Field(default_factory=list)
    retrieval_mode: str = "keyword"
    llm_used: bool = False
    llm_provider: str = "rule"
    llm_fallback_reason: str = ""
    phase: str = "DAY_MEETING"
    round: int = 0
    llm_validation_failure_id: str = ""


class PrivateConversationState(BaseModel):
    day: int
    npc_character_id: int
    question: str
    reply: str
    effective: bool
    llm_validation_failure_id: str = ""
    easter_egg_id: str = ""
    easter_egg_first_time: bool = False
    revealed_role: Optional[str] = None


class EliminationState(BaseModel):
    day: int
    character_id: int
    cause: str
    source_action: str
    source_actor_ids: list[int] = Field(default_factory=list)
    source_target_id: int


class LLMValidationAttemptState(BaseModel):
    attempt: int
    raw_text: str
    display_text: str
    rejection_reason: str
    passed: bool = False
    sensitive: bool = False


class LLMValidationFailureState(BaseModel):
    failure_id: str
    day: int
    character_id: int
    context_kind: str
    attempts: list[LLMValidationAttemptState] = Field(default_factory=list)


class LLMValidationAttemptView(BaseModel):
    attempt: int
    text: str
    rejection_reason: str
    sensitive: bool = False


class LLMValidationFailureView(BaseModel):
    failure_id: str
    character_id: int
    context_kind: str
    attempts: list[LLMValidationAttemptView] = Field(default_factory=list)


class NightResolutionState(BaseModel):
    day: int
    attacked_target_id: Optional[int] = None
    protected_ids: list[int] = Field(default_factory=list)
    saved_target_id: Optional[int] = None
    poisoned_target_id: Optional[int] = None
    dead_character_ids: list[int] = Field(default_factory=list)


class HunterShotState(BaseModel):
    day: int
    hunter_id: int
    target_id: Optional[int] = None
    trigger: str


class PublicClaimState(BaseModel):
    day: int
    character_id: int
    claim_type: str
    claimed_role: Optional[str] = None
    target_id: Optional[int] = None
    result: str = ""
    source: str = "speech"


class DayMeetingState(BaseModel):
    day: int
    direction: str
    order: list[int] = Field(default_factory=list)
    current_index: int = 0
    completed: bool = False
    order_source: str = "random"
    anchor_character_id: Optional[int] = None
    sheriff_id: Optional[int] = None
    temporary_nomination_target_id: Optional[int] = None
    nomination_target_id: Optional[int] = None


class DayMeetingView(BaseModel):
    active: bool
    direction: str = ""
    order: list[int] = Field(default_factory=list)
    current_speaker_id: Optional[int] = None
    current_position: int = 0
    total_speakers: int = 0
    completed: bool = False
    order_source: str = "random"
    anchor_character_id: Optional[int] = None
    sheriff_id: Optional[int] = None
    temporary_nomination_target_id: Optional[int] = None
    nomination_target_id: Optional[int] = None


class SheriffElectionState(BaseModel):
    day: int = 1
    candidates: list[int] = Field(default_factory=list)
    withdrawn: list[int] = Field(default_factory=list)
    speech_order: list[int] = Field(default_factory=list)
    current_index: int = 0
    runoff_round: int = 0
    runoff_candidates: list[int] = Field(default_factory=list)
    votes: list[VoteState] = Field(default_factory=list)
    completed: bool = False


class SheriffEventState(BaseModel):
    day: int
    event_type: str
    actor_id: Optional[int] = None
    target_id: Optional[int] = None
    detail: str = ""


class SheriffView(BaseModel):
    sheriff_id: Optional[int] = None
    badge_destroyed: bool = False
    candidates: list[int] = Field(default_factory=list)
    active_candidates: list[int] = Field(default_factory=list)
    withdrawn: list[int] = Field(default_factory=list)
    current_speaker_id: Optional[int] = None
    speech_order: list[int] = Field(default_factory=list)
    current_position: int = 0
    runoff_round: int = 0
    runoff_candidates: list[int] = Field(default_factory=list)
    player_can_vote: bool = False
    player_vote_ineligible_reason: str = ""
    vote_targets: list[int] = Field(default_factory=list)
    order_anchor_id: Optional[int] = None
    order_anchor_type: str = ""
    order_options: list[str] = Field(default_factory=list)
    temporary_nomination_target_id: Optional[int] = None
    nomination_target_id: Optional[int] = None
    pending_transfer_from_id: Optional[int] = None


class WolfGameState(BaseModel):
    game_id: str
    day: int
    phase: str
    player_character_id: int
    characters: list[CharacterState]
    night_actions: list[NightActionState] = Field(default_factory=list)
    votes: list[VoteState] = Field(default_factory=list)
    speeches: list[SpeechState] = Field(default_factory=list)
    private_conversations: list[PrivateConversationState] = Field(default_factory=list)
    eliminations: list[EliminationState] = Field(default_factory=list)
    pending_first_night_eliminations: list[EliminationState] = Field(default_factory=list)
    first_night_result_pending: bool = False
    night_resolutions: list[NightResolutionState] = Field(default_factory=list)
    hunter_shots: list[HunterShotState] = Field(default_factory=list)
    public_claims: list[PublicClaimState] = Field(default_factory=list)
    meeting: Optional[DayMeetingState] = None
    sheriff_id: Optional[int] = None
    sheriff_election: Optional[SheriffElectionState] = None
    sheriff_events: list[SheriffEventState] = Field(default_factory=list)
    badge_destroyed: bool = False
    meeting_order_anchor_id: Optional[int] = None
    meeting_order_anchor_type: str = ""
    pending_badge_transfer_from_id: Optional[int] = None
    pending_badge_continuation: str = ""
    wolf_checked_wolf_used: bool = False
    public_logs: list[str] = Field(default_factory=list)
    player_private_info: dict[str, object] = Field(default_factory=dict)
    role_resources: dict[str, dict[str, object]] = Field(default_factory=dict)
    pending_hunter_id: Optional[int] = None
    pending_hunter_trigger: str = ""
    pending_hunter_continuation: str = ""
    wolf_fake_seer_id: Optional[int] = None
    llm_validation_failures: list[LLMValidationFailureState] = Field(default_factory=list)
    winner: Optional[str] = None
    winner_reason: str = ""
    llm_enabled: bool = False
    rag_enabled: bool = False
    created_at: str
    updated_at: str


class GameStartResponse(BaseModel):
    game_id: str
    day: int
    phase: str
    player_character_id: int
    characters: list[CharacterView]
    message: str
    llm_enabled: bool = False


class GameStateResponse(BaseModel):
    game_id: str
    day: int
    phase: str
    characters: list[CharacterView]
    public_logs: list[str]
    player_private_info: PlayerPrivateInfo
    meeting: DayMeetingView
    sheriff: SheriffView
    winner: Optional[str] = None
    llm_enabled: bool = False


class GameSummaryEvent(BaseModel):
    day: int
    phase: str
    character_ids: list[int] = Field(default_factory=list)
    text: str
    is_private: bool = False


class CharacterGameSummary(BaseModel):
    character_id: int
    name: str
    role: str
    role_label: str
    camp: str
    camp_label: str
    outcome: str
    actions: list[GameSummaryEvent] = Field(default_factory=list)


class GameSummaryResponse(BaseModel):
    game_id: str
    total_days: int
    winner: str
    winner_label: str
    winner_message: str
    characters: list[CharacterGameSummary]
    timeline: list[GameSummaryEvent]
    llm_validation_failures: list[LLMValidationFailureView] = Field(default_factory=list)


class NightActionRequest(BaseModel):
    game_id: str
    character_id: int
    action_type: str
    target_id: Optional[int] = None


class NightActionResponse(BaseModel):
    success: bool
    message: str


class NightResolveRequest(BaseModel):
    game_id: str


class NightResolveResponse(BaseModel):
    game_id: str
    day: int
    dead_characters: list[int]
    is_peaceful_night: Optional[bool]
    result_pending: bool = False
    public_message: str
    player_private_result: dict[str, object] = Field(default_factory=dict)


class HunterShotRequest(BaseModel):
    game_id: str
    character_id: int
    target_id: Optional[int] = None


class HunterShotResponse(BaseModel):
    success: bool
    hunter_id: int
    target_id: Optional[int] = None
    message: str
    phase: str
    is_game_over: bool
    winner: Optional[str] = None


class ParsedPlayerSpeech(BaseModel):
    mentioned_characters: list[int] = Field(default_factory=list)
    accusations: list[dict[str, object]] = Field(default_factory=list)
    claims: list[dict[str, object]] = Field(default_factory=list)
    tone: str = "neutral"


class PlayerSpeechRequest(BaseModel):
    game_id: str
    character_id: int
    speech: str
    temporary_nomination_target_id: Optional[int] = None


class PlayerSpeechResponse(BaseModel):
    parsed: ParsedPlayerSpeech
    public_log: str
    state_updates: dict[str, object] = Field(default_factory=dict)


class SheriffSignupRequest(BaseModel):
    game_id: str
    character_id: int
    run_for_sheriff: bool


class SheriffSignupResponse(BaseModel):
    success: bool
    message: str
    candidates: list[int]
    next_speaker_id: Optional[int] = None


class SheriffSpeechRequest(BaseModel):
    game_id: str
    character_id: int
    speech: str = ""


class SheriffWithdrawalRequest(BaseModel):
    game_id: str
    character_id: int
    withdraw: bool = False


class SheriffWithdrawalResponse(BaseModel):
    success: bool
    message: str
    active_candidates: list[int]
    phase: str


class SheriffVoteRequest(BaseModel):
    game_id: str
    character_id: int
    target_id: Optional[int] = None


class SheriffBallot(BaseModel):
    voter_id: int
    target_id: int


class SheriffVoteResponse(BaseModel):
    ballots: list[SheriffBallot]
    winner_id: Optional[int] = None
    tied_candidate_ids: list[int] = Field(default_factory=list)
    phase: str
    message: str


class SheriffMeetingOrderRequest(BaseModel):
    game_id: str
    character_id: int
    side: str


class SheriffNominationRequest(BaseModel):
    game_id: str
    character_id: int
    target_id: int


class BadgeTransferRequest(BaseModel):
    game_id: str
    character_id: int
    target_id: Optional[int] = None


class SheriffActionResponse(BaseModel):
    success: bool
    message: str
    phase: str


class NpcSpeechItem(BaseModel):
    character_id: int
    name: str
    speech: str
    evidence_titles: list[str] = Field(default_factory=list)
    retrieval_mode: str = "keyword"
    llm_used: bool = False
    llm_provider: str = "rule"
    llm_fallback_reason: str = ""
    llm_validation_failure: Optional[LLMValidationFailureView] = None


class SheriffSpeechResponse(BaseModel):
    speech: NpcSpeechItem
    next_speaker_id: Optional[int] = None
    speeches_completed: bool = False


class NpcMemoryUpdate(BaseModel):
    owner_character_id: int
    content: str


class NpcSpeechesRequest(BaseModel):
    game_id: str
    day: Optional[int] = None
    respond_to_player: bool = True


class NpcSpeechesResponse(BaseModel):
    speeches: list[NpcSpeechItem]
    memory_updates: list[NpcMemoryUpdate] = Field(default_factory=list)


class NpcSpeechRequest(BaseModel):
    game_id: str
    character_id: int


class NpcSpeechResponse(BaseModel):
    speech: NpcSpeechItem
    memory_update: NpcMemoryUpdate
    next_speaker_id: Optional[int] = None
    meeting_completed: bool = False


class EndFreeActivityRequest(BaseModel):
    game_id: str


class EndFreeActivityResponse(BaseModel):
    success: bool
    message: str


class PrivateChatRequest(BaseModel):
    game_id: str
    npc_character_id: int
    question: str


class PrivateChatResponse(BaseModel):
    npc_character_id: int
    npc_name: str
    reply: str
    effective: bool
    can_influence_again: bool = False
    knowledge_titles: list[str] = Field(default_factory=list)
    retrieval_mode: str = "keyword"
    llm_used: bool = False
    llm_provider: str = "rule"
    llm_fallback_reason: str = ""
    llm_validation_failure: Optional[LLMValidationFailureView] = None
    easter_egg_triggered: bool = False
    easter_egg_first_time: bool = False


class NpcVoteDecision(BaseModel):
    character_id: int
    target_id: int
    reason: str
    evidence_titles: list[str] = Field(default_factory=list)
    retrieval_mode: str = "keyword"


class NpcVoteDecisionsRequest(BaseModel):
    game_id: str


class NpcVoteDecisionsResponse(BaseModel):
    npc_votes: list[NpcVoteDecision]


class PlayerVoteRequest(BaseModel):
    game_id: str
    character_id: int
    target_id: Optional[int] = None
    reason: str = ""


class PlayerVoteResponse(BaseModel):
    success: bool
    message: str


class VoteResolveRequest(BaseModel):
    game_id: str


class VoteResolveResponse(BaseModel):
    exiled_character_id: Optional[int]
    vote_result: dict[str, int]
    public_message: str
    is_game_over: bool
    winner: Optional[str] = None


class VoteBallotDetail(BaseModel):
    voter_id: int
    voter_name: str
    target_id: int
    target_name: str
    reason: str
    weight: float = 1.0
    is_sheriff: bool = False
    evidence_titles: list[str] = Field(default_factory=list)
    retrieval_mode: str = "keyword"


class SubmitAndResolveVoteResponse(BaseModel):
    exiled_character_id: Optional[int]
    ballots: list[VoteBallotDetail]
    vote_totals: dict[str, float]
    public_message: str
    is_game_over: bool
    phase: str
    winner: Optional[str] = None


DEFAULT_NPC_PROFILE = NPCProfile(
    npc_name="Guide",
    role="小镇向导",
    personality="友好、耐心，喜欢用简单的话解释新系统。",
    knowledge=[
        "这个 Demo 使用 Godot 4 负责 2D 交互。",
        "Python FastAPI 后端负责 NPC 对话、记忆和未来的 RAG。",
        "后续会加入知识库，让 NPC 能回答更多小镇相关问题。",
    ],
)

NPC_PROFILES: dict[str, NPCProfile] = {}
KNOWLEDGE_BASE: list[KnowledgeItem] = []

MEMORY_STORE: dict[str, list[MemoryItem]] = {}
MEMORY_LOCK = Lock()
GAME_STORE: dict[str, WolfGameState] = {}
GAME_LOCK = Lock()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/health", response_model=ApiHealthResponse)
def api_health() -> ApiHealthResponse:
    rag_status = HYBRID_INDEX.status()
    dependency_available = bool(rag_status["dependency_available"])
    return ApiHealthResponse(
        status="ok",
        llm_enabled=bool(LLM_CLIENT.status()["enabled"]),
        rag_enabled=dependency_available,
        provider=str(LLM_CLIENT.status()["provider"]),
    )


@app.get("/api/llm/status", response_model=LLMStatusResponse)
def get_llm_status() -> LLMStatusResponse:
    return LLMStatusResponse(**LLM_CLIENT.status())


@app.get("/api/rag/status", response_model=RagStatusResponse)
def get_rag_status() -> RagStatusResponse:
    return RagStatusResponse(**HYBRID_INDEX.status())


@app.post("/api/game/start", response_model=GameStartResponse)
def start_wolf_game(request: GameStartRequest) -> GameStartResponse:
    if request.npc_count != FIXED_NPC_COUNT:
        raise HTTPException(
            status_code=400,
            detail="当前版本固定为 1 名玩家 + 11 名 NPC。",
        )

    role_pool = build_role_pool(request.roles)
    total_character_count = request.npc_count + 1
    if len(role_pool) != total_character_count:
        raise HTTPException(
            status_code=400,
            detail=f"身份数量必须等于角色总数 {total_character_count}。",
        )

    requested_player_role = request.player_role.strip().lower()
    if requested_player_role in {"", "random"}:
        random.shuffle(role_pool)
    else:
        if requested_player_role not in CAMP_BY_ROLE:
            raise HTTPException(status_code=400, detail=f"未知玩家身份：{request.player_role}")
        if requested_player_role not in role_pool:
            raise HTTPException(status_code=400, detail="指定的玩家身份不在本局身份池中。")
        role_pool.remove(requested_player_role)
        random.shuffle(role_pool)
        role_pool.insert(0, requested_player_role)
    now = datetime.now(timezone.utc).isoformat()

    with GAME_LOCK:
        game_id = build_game_id()
        characters = build_characters(request.player_name, role_pool)
        game_state = WolfGameState(
            game_id=game_id,
            day=1,
            phase="NIGHT",
            player_character_id=1,
            characters=characters,
            public_logs=["游戏开始，12 名角色已入场。", "第 1 夜开始。"],
            player_private_info={},
            llm_enabled=(
                request.enable_llm
                and bool(LLM_CLIENT.status()["enabled"])
                and bool(LLM_CLIENT.status()["configured"])
            ),
            rag_enabled=request.enable_rag,
            created_at=now,
            updated_at=now,
        )
        game_state.wolf_fake_seer_id = choose_designated_fake_seer(game_state.characters)
        initialize_role_resources(game_state)
        ensure_npc_night_actions(game_state)
        game_state.player_private_info = build_player_private_info_dict(game_state)
        GAME_STORE[game_id] = game_state

    player = get_character(game_state, game_state.player_character_id)
    return GameStartResponse(
        game_id=game_state.game_id,
        day=game_state.day,
        phase=game_state.phase,
        player_character_id=game_state.player_character_id,
        characters=build_character_views(game_state),
        message=(
            f"游戏开始，你的身份是{ROLE_LABELS.get(player.role, player.role)}。"
            + ("本局已启用 LLM 表达。" if game_state.llm_enabled else "本局使用规则模板表达。")
        ),
        llm_enabled=game_state.llm_enabled,
    )


@app.get("/api/game/{game_id}/state", response_model=GameStateResponse)
def get_wolf_game_state(game_id: str) -> GameStateResponse:
    with GAME_LOCK:
        game_state = GAME_STORE.get(game_id)

    if game_state is None:
        raise HTTPException(status_code=404, detail="未找到这局游戏。")

    player = get_character(game_state, game_state.player_character_id)
    private_info = build_player_private_info_dict(game_state)
    game_state.player_private_info = private_info
    return GameStateResponse(
        game_id=game_state.game_id,
        day=game_state.day,
        phase=game_state.phase,
        characters=build_character_views(game_state),
        public_logs=list(game_state.public_logs),
        player_private_info=PlayerPrivateInfo(**private_info),
        meeting=build_day_meeting_view(game_state),
        sheriff=build_sheriff_view(game_state),
        winner=game_state.winner,
        llm_enabled=game_state.llm_enabled,
    )


@app.get("/api/game/{game_id}/summary", response_model=GameSummaryResponse)
def get_game_summary(game_id: str) -> GameSummaryResponse:
    with GAME_LOCK:
        game_state = get_game_state_or_404(game_id)
        if game_state.phase != "GAME_OVER" or game_state.winner is None:
            raise HTTPException(status_code=400, detail="只有游戏结束后才能查看完整复盘。")
        return build_game_summary(game_state)


@app.post("/api/night/action", response_model=NightActionResponse)
def submit_night_action(request: NightActionRequest) -> NightActionResponse:
    with GAME_LOCK:
        game_state = get_game_state_or_404(request.game_id)
        ensure_phase(game_state, "NIGHT")
        actor = get_character(game_state, request.character_id)
        validate_night_action(game_state, actor, request.action_type, request.target_id)
        upsert_night_action(
            game_state,
            NightActionState(
                day=game_state.day,
                actor_id=actor.id,
                action_type=request.action_type,
                target_id=request.target_id,
            ),
        )
        if actor.role == "werewolf":
            refresh_npc_witch_action(game_state)
        game_state.player_private_info = build_player_private_info_dict(game_state)
        game_state.updated_at = datetime.now(timezone.utc).isoformat()

    return NightActionResponse(success=True, message="行动已记录。")


@app.post("/api/night/resolve", response_model=NightResolveResponse)
def resolve_night(request: NightResolveRequest) -> NightResolveResponse:
    with GAME_LOCK:
        game_state = get_game_state_or_404(request.game_id)
        ensure_phase(game_state, "NIGHT")
        ensure_npc_night_actions(game_state)

        night_actions = [
            action
            for action in game_state.night_actions
            if action.day == game_state.day
        ]
        protected_ids = {
            action.target_id
            for action in night_actions
            if action.action_type == "guard_protect" and action.target_id is not None
        }
        killed_target = choose_wolf_kill_target(game_state, night_actions)
        saved_target_id = next(
            (
                action.target_id
                for action in night_actions
                if action.action_type == "witch_save" and action.target_id is not None
            ),
            None,
        )
        poisoned_target_id = next(
            (
                action.target_id
                for action in night_actions
                if action.action_type == "witch_poison" and action.target_id is not None
            ),
            None,
        )
        dead_characters: list[int] = []
        delay_first_night_result = (
            game_state.day == 1 and game_state.sheriff_election is None
        )
        wolf_actor_ids = [
            action.actor_id
            for action in night_actions
            if action.action_type == "werewolf_kill"
            and action.target_id == killed_target
        ]
        poison_actor_ids = [
            action.actor_id
            for action in night_actions
            if action.action_type == "witch_poison"
            and action.target_id == poisoned_target_id
        ]

        if killed_target is not None:
            guard_saved = killed_target in protected_ids
            witch_saved = saved_target_id == killed_target
            double_protection_failed = guard_saved and witch_saved
            if double_protection_failed or not (guard_saved or witch_saved):
                if resolve_or_queue_night_elimination(
                    game_state,
                    killed_target,
                    "night_kill",
                    "werewolf_kill",
                    wolf_actor_ids,
                    delay_first_night_result,
                ):
                    dead_characters.append(killed_target)

        if poisoned_target_id is not None:
            if resolve_or_queue_night_elimination(
                game_state,
                poisoned_target_id,
                "witch_poison",
                "witch_poison",
                poison_actor_ids,
                delay_first_night_result,
            ):
                dead_characters.append(poisoned_target_id)

        consume_night_role_resources(game_state, night_actions)

        game_state.night_resolutions.append(
            NightResolutionState(
                day=game_state.day,
                attacked_target_id=killed_target,
                protected_ids=sorted(protected_ids),
                saved_target_id=saved_target_id,
                poisoned_target_id=poisoned_target_id,
                dead_character_ids=list(dead_characters),
            )
        )
        player_private_result = build_player_private_night_result(game_state, night_actions)
        if player_private_result:
            game_state.player_private_info["last_check_result"] = player_private_result.get("seer_check")

        apply_night_role_results(
            game_state,
            night_actions,
            killed_target,
            protected_ids,
            saved_target_id,
        )
        if delay_first_night_result:
            game_state.first_night_result_pending = True
            public_message = "首夜行动已经完成，出局结果将在警长竞选结束后公布。"
            game_state.public_logs.append(public_message)
            start_sheriff_signup(game_state)
        else:
            hunter_message = handle_hunter_trigger(
                game_state,
                dead_characters,
                trigger="night",
                poisoned_character_id=poisoned_target_id,
                continuation="after_night",
            )
            public_message = build_night_public_message(game_state, dead_characters)
            game_state.public_logs.append(public_message)
            if hunter_message:
                game_state.public_logs.append(hunter_message)
                public_message += "\n" + hunter_message
            if game_state.phase != "HUNTER_SHOT":
                continue_after_elimination(game_state, "after_night")
        game_state.player_private_info = build_player_private_info_dict(game_state)
        game_state.updated_at = datetime.now(timezone.utc).isoformat()

    return NightResolveResponse(
        game_id=game_state.game_id,
        day=game_state.day,
        dead_characters=[] if delay_first_night_result else dead_characters,
        is_peaceful_night=(None if delay_first_night_result else len(dead_characters) == 0),
        result_pending=delay_first_night_result,
        public_message=public_message,
        player_private_result=player_private_result,
    )


@app.post("/api/hunter/shot", response_model=HunterShotResponse)
def resolve_hunter_shot(request: HunterShotRequest) -> HunterShotResponse:
    with GAME_LOCK:
        game_state = get_game_state_or_404(request.game_id)
        ensure_phase(game_state, "HUNTER_SHOT")
        if game_state.pending_hunter_id != request.character_id:
            raise HTTPException(status_code=400, detail="当前不是这名猎人的开枪时机。")

        hunter = get_character(game_state, request.character_id)
        if not hunter.is_player:
            raise HTTPException(status_code=400, detail="NPC 猎人由后端自动处理。")

        target_id = request.target_id
        if target_id is not None:
            target = get_character(game_state, target_id)
            if not target.alive:
                raise HTTPException(status_code=400, detail="猎人只能选择仍在场的角色。")
            if target.id == hunter.id:
                raise HTTPException(status_code=400, detail="猎人不能选择自己。")

        game_state.hunter_shots.append(
            HunterShotState(
                day=game_state.day,
                hunter_id=hunter.id,
                target_id=target_id,
                trigger=game_state.pending_hunter_trigger,
            )
        )
        if target_id is None:
            message = f"{hunter.name}出局后选择不开枪。"
        else:
            target = get_character(game_state, target_id)
            eliminate_character(
                game_state,
                target.id,
                "hunter_shot",
                source_action="hunter_shot",
                source_actor_ids=[hunter.id],
                source_target_id=target.id,
            )
            message = f"猎人{hunter.name}开枪，{target.name}出局。"
        game_state.public_logs.append(message)

        continuation = game_state.pending_hunter_continuation
        clear_pending_hunter(game_state)
        continue_after_elimination(game_state, continuation)
        game_state.player_private_info = build_player_private_info_dict(game_state)
        game_state.updated_at = datetime.now(timezone.utc).isoformat()

    return HunterShotResponse(
        success=True,
        hunter_id=hunter.id,
        target_id=target_id,
        message=message,
        phase=game_state.phase,
        is_game_over=game_state.phase == "GAME_OVER",
        winner=game_state.winner,
    )


def eliminate_character(
    game_state: WolfGameState,
    character_id: int,
    cause: str,
    source_action: str,
    source_actor_ids: list[int],
    source_target_id: int,
) -> bool:
    validate_elimination_source(
        game_state,
        character_id,
        cause,
        source_action,
        source_actor_ids,
        source_target_id,
    )
    character = get_character(game_state, character_id)
    if not character.alive:
        return False
    character.alive = False
    game_state.eliminations.append(
        EliminationState(
            day=game_state.day,
            character_id=character.id,
            cause=cause,
            source_action=source_action,
            source_actor_ids=list(dict.fromkeys(source_actor_ids)),
            source_target_id=source_target_id,
        )
    )
    return True


def validate_elimination_source(
    game_state: WolfGameState,
    character_id: int,
    cause: str,
    source_action: str,
    source_actor_ids: list[int],
    source_target_id: int,
) -> None:
    expected_action = VALID_ELIMINATION_SOURCES.get(cause)
    if expected_action is None or source_action != expected_action:
        raise ValueError(f"Invalid elimination source: {cause}/{source_action}")
    if source_target_id != character_id:
        raise ValueError("Elimination source target does not match eliminated character")
    if not source_actor_ids:
        raise ValueError("Elimination must contain at least one source actor")

    expected_roles = {
        "werewolf_kill": {"werewolf"},
        "witch_poison": {"witch"},
        "hunter_shot": {"hunter"},
    }
    for actor_id in source_actor_ids:
        actor = get_character(game_state, actor_id)
        allowed_roles = expected_roles.get(source_action)
        if allowed_roles is not None and actor.role not in allowed_roles:
            raise ValueError(f"{actor.name} cannot cause {source_action}")

    if source_action in {"werewolf_kill", "witch_poison"}:
        matching_actions = {
            action.actor_id
            for action in game_state.night_actions
            if action.day == game_state.day
            and action.action_type == source_action
            and action.target_id == character_id
        }
        if not set(source_actor_ids).issubset(matching_actions):
            raise ValueError("Night elimination has no matching submitted action")
    elif source_action == "hunter_shot":
        if not any(
            shot.day == game_state.day
            and shot.hunter_id in source_actor_ids
            and shot.target_id == character_id
            for shot in game_state.hunter_shots
        ):
            raise ValueError("Hunter elimination has no matching shot")
    elif source_action == "day_vote":
        matching_voters = {
            vote.voter_id
            for vote in game_state.votes
            if vote.day == game_state.day and vote.target_id == character_id
        }
        if not set(source_actor_ids).issubset(matching_voters):
            raise ValueError("Vote elimination has no matching ballot")


def build_elimination_record(
    game_state: WolfGameState,
    character_id: int,
    cause: str,
    source_action: str,
    source_actor_ids: list[int],
) -> EliminationState:
    validate_elimination_source(
        game_state,
        character_id,
        cause,
        source_action,
        source_actor_ids,
        character_id,
    )
    return EliminationState(
        day=game_state.day,
        character_id=character_id,
        cause=cause,
        source_action=source_action,
        source_actor_ids=list(dict.fromkeys(source_actor_ids)),
        source_target_id=character_id,
    )


def resolve_or_queue_night_elimination(
    game_state: WolfGameState,
    character_id: int,
    cause: str,
    source_action: str,
    source_actor_ids: list[int],
    delay_result: bool,
) -> bool:
    if not delay_result:
        return eliminate_character(
            game_state,
            character_id,
            cause,
            source_action=source_action,
            source_actor_ids=source_actor_ids,
            source_target_id=character_id,
        )

    record = build_elimination_record(
        game_state,
        character_id,
        cause,
        source_action,
        source_actor_ids,
    )
    existing_index = next(
        (
            index
            for index, pending in enumerate(game_state.pending_first_night_eliminations)
            if pending.character_id == character_id
        ),
        None,
    )
    if existing_index is None:
        game_state.pending_first_night_eliminations.append(record)
        return True
    if cause == "witch_poison":
        game_state.pending_first_night_eliminations[existing_index] = record
    return False


def consume_night_role_resources(
    game_state: WolfGameState,
    night_actions: list[NightActionState],
) -> None:
    for action in night_actions:
        actor = get_character(game_state, action.actor_id)
        resources = get_role_resources(game_state, actor.id)
        if action.action_type == "guard_protect":
            resources["last_protected_target_id"] = action.target_id
            resources["last_protected_day"] = game_state.day
        elif action.action_type == "witch_save":
            resources["antidote_available"] = False
        elif action.action_type == "witch_poison":
            resources["poison_available"] = False


def handle_hunter_trigger(
    game_state: WolfGameState,
    eliminated_character_ids: list[int],
    trigger: str,
    continuation: str,
    poisoned_character_id: Optional[int] = None,
) -> str:
    hunter = next(
        (
            get_character(game_state, character_id)
            for character_id in eliminated_character_ids
            if get_character(game_state, character_id).role == "hunter"
            and character_id != poisoned_character_id
        ),
        None,
    )
    if hunter is None:
        return ""

    if hunter.is_player:
        game_state.pending_hunter_id = hunter.id
        game_state.pending_hunter_trigger = trigger
        game_state.pending_hunter_continuation = continuation
        game_state.phase = "HUNTER_SHOT"
        return f"猎人{hunter.name}已出局，正在等待他决定是否开枪。"

    target_id = choose_npc_hunter_target(game_state, hunter)
    game_state.hunter_shots.append(
        HunterShotState(
            day=game_state.day,
            hunter_id=hunter.id,
            target_id=target_id,
            trigger=trigger,
        )
    )
    if target_id is None:
        return f"猎人{hunter.name}出局后选择不开枪。"

    target = get_character(game_state, target_id)
    if eliminate_character(
        game_state,
        target.id,
        "hunter_shot",
        source_action="hunter_shot",
        source_actor_ids=[hunter.id],
        source_target_id=target.id,
    ):
        eliminated_character_ids.append(target.id)
    return f"猎人{hunter.name}开枪，{target.name}出局。"


def choose_npc_hunter_target(
    game_state: WolfGameState,
    hunter: CharacterState,
) -> Optional[int]:
    candidates = [
        character
        for character in game_state.characters
        if character.alive and character.id != hunter.id
    ]
    if not candidates:
        return None
    highest_suspicion = max(
        hunter.suspicion.get(str(character.id), 0)
        for character in candidates
    )
    likely_targets = [
        character
        for character in candidates
        if hunter.suspicion.get(str(character.id), 0) == highest_suspicion
    ]
    return random.choice(likely_targets).id


def clear_pending_hunter(game_state: WolfGameState) -> None:
    game_state.pending_hunter_id = None
    game_state.pending_hunter_trigger = ""
    game_state.pending_hunter_continuation = ""


def get_active_sheriff_candidates(game_state: WolfGameState) -> list[int]:
    election = game_state.sheriff_election
    if election is None:
        return []
    candidate_ids = (
        election.runoff_candidates
        if election.runoff_round > 0 and election.runoff_candidates
        else election.candidates
    )
    return [
        character_id
        for character_id in candidate_ids
        if character_id not in election.withdrawn
        and get_character(game_state, character_id).alive
    ]


def get_current_sheriff_speaker_id(game_state: WolfGameState) -> Optional[int]:
    election = game_state.sheriff_election
    if (
        election is None
        or game_state.phase not in {"SHERIFF_SPEECH", "SHERIFF_RUNOFF_SPEECH"}
        or election.current_index >= len(election.speech_order)
    ):
        return None
    return election.speech_order[election.current_index]


def build_sheriff_view(game_state: WolfGameState) -> SheriffView:
    election = game_state.sheriff_election
    active_candidates = get_active_sheriff_candidates(game_state)
    player = get_character(game_state, game_state.player_character_id)
    player_can_vote = (
        game_state.phase in {"SHERIFF_VOTE", "SHERIFF_RUNOFF_VOTE"}
        and player.alive
        and (
            election is None
            or player.id not in election.candidates
        )
    )
    player_vote_ineligible_reason = ""
    if game_state.phase in {"SHERIFF_VOTE", "SHERIFF_RUNOFF_VOTE"}:
        if not player.alive:
            player_vote_ineligible_reason = "出局角色不能参与警长投票"
        elif election is not None and player.id in election.candidates:
            player_vote_ineligible_reason = "参加过竞选的角色（含退水者）不能参与警长投票"
    order_options = []
    if game_state.phase == "MEETING_ORDER":
        prefix = "out" if game_state.meeting_order_anchor_type == "out" else "sheriff"
        order_options = [f"{prefix}_left", f"{prefix}_right"]
    return SheriffView(
        sheriff_id=game_state.sheriff_id,
        badge_destroyed=game_state.badge_destroyed,
        candidates=list(election.candidates) if election is not None else [],
        active_candidates=active_candidates,
        withdrawn=list(election.withdrawn) if election is not None else [],
        current_speaker_id=get_current_sheriff_speaker_id(game_state),
        speech_order=list(election.speech_order) if election is not None else [],
        current_position=(
            min(election.current_index + 1, len(election.speech_order))
            if election is not None and election.speech_order
            else 0
        ),
        runoff_round=election.runoff_round if election is not None else 0,
        runoff_candidates=(list(election.runoff_candidates) if election is not None else []),
        player_can_vote=player_can_vote,
        player_vote_ineligible_reason=player_vote_ineligible_reason,
        vote_targets=active_candidates if player_can_vote else [],
        order_anchor_id=game_state.meeting_order_anchor_id,
        order_anchor_type=game_state.meeting_order_anchor_type,
        order_options=order_options,
        temporary_nomination_target_id=(
            game_state.meeting.temporary_nomination_target_id
            if game_state.meeting is not None
            else None
        ),
        nomination_target_id=(
            game_state.meeting.nomination_target_id
            if game_state.meeting is not None
            else None
        ),
        pending_transfer_from_id=game_state.pending_badge_transfer_from_id,
    )


def choose_initial_npc_sheriff_candidates(game_state: WolfGameState) -> list[int]:
    candidates = []
    true_seer = next(
        (
            character
            for character in game_state.characters
            if not character.is_player and character.alive and character.role == "seer"
        ),
        None,
    )
    if true_seer is not None:
        candidates.append(true_seer.id)

    if game_state.wolf_fake_seer_id is not None:
        fake_seer = get_character(game_state, game_state.wolf_fake_seer_id)
        if fake_seer.alive and fake_seer.id not in candidates:
            candidates.append(fake_seer.id)

    extra_candidates = sorted(
        [
            character
            for character in game_state.characters
            if not character.is_player
            and character.alive
            and character.role != "werewolf"
            and character.id not in candidates
            and character.personality.get("leadership", 0.5) >= 0.72
        ],
        key=lambda character: (
            character.personality.get("leadership", 0.5)
            + character.personality.get("logic", 0.5) * 0.35,
            -character.id,
        ),
        reverse=True,
    )
    candidates.extend(character.id for character in extra_candidates[:2])
    return candidates


def build_circular_subset_order(
    game_state: WolfGameState,
    character_ids: list[int],
) -> list[int]:
    if not character_ids:
        return []
    seat_ids = [character.id for character in game_state.characters]
    selected = set(character_ids)
    first_id = random.choice(character_ids)
    direction = random.choice([1, -1])
    first_index = seat_ids.index(first_id)
    order = []
    for offset in range(len(seat_ids)):
        character_id = seat_ids[(first_index + direction * offset) % len(seat_ids)]
        if character_id in selected:
            order.append(character_id)
    return order


def start_sheriff_signup(game_state: WolfGameState) -> None:
    game_state.sheriff_election = SheriffElectionState(
        day=game_state.day,
        candidates=choose_initial_npc_sheriff_candidates(game_state),
    )
    game_state.public_logs.append("第一天警上竞选开始，等待玩家决定是否上警。")
    player = get_character(game_state, game_state.player_character_id)
    if player.alive:
        game_state.phase = "SHERIFF_SIGNUP"
        return
    finalize_sheriff_signup(game_state, False)


def finalize_sheriff_signup(game_state: WolfGameState, player_runs: bool) -> None:
    election = game_state.sheriff_election
    if election is None:
        raise HTTPException(status_code=400, detail="当前没有警上竞选。")
    player = get_character(game_state, game_state.player_character_id)
    if player_runs and player.alive and player.id not in election.candidates:
        election.candidates.append(player.id)
        game_state.public_logs.append(f"{player.id}号{player.name}报名竞选警长。")
    else:
        game_state.public_logs.append(f"{player.id}号{player.name}选择不上警。")

    election.candidates = [
        character_id
        for character_id in dict.fromkeys(election.candidates)
        if get_character(game_state, character_id).alive
    ]
    election.speech_order = build_circular_subset_order(game_state, election.candidates)
    election.current_index = 0
    if not election.speech_order:
        finish_sheriff_election(game_state, None, "无人报名，警徽被撕毁。")
        return
    game_state.phase = "SHERIFF_SPEECH"
    labels = [format_full_character_name(get_character(game_state, character_id)) for character_id in election.speech_order]
    game_state.public_logs.append("警上发言顺序：" + " → ".join(labels) + "。")


def ensure_sheriff_speech_turn(game_state: WolfGameState, character_id: int) -> None:
    if game_state.phase not in {"SHERIFF_SPEECH", "SHERIFF_RUNOFF_SPEECH"}:
        raise HTTPException(status_code=400, detail="当前不是警上发言阶段。")
    current_speaker_id = get_current_sheriff_speaker_id(game_state)
    if current_speaker_id != character_id:
        if current_speaker_id is None:
            raise HTTPException(status_code=400, detail="本轮警上发言已经结束。")
        current = get_character(game_state, current_speaker_id)
        raise HTTPException(status_code=400, detail=f"当前轮到{current.id}号{current.name}进行警上发言。")


def get_forced_sheriff_claims(
    game_state: WolfGameState,
    speaker: CharacterState,
) -> list[PublicClaimState]:
    if speaker.role == "seer":
        claims = []
        if get_public_role_claim(game_state, speaker.id) is None:
            claims.append(
                PublicClaimState(
                    day=game_state.day,
                    character_id=speaker.id,
                    claim_type="role",
                    claimed_role="seer",
                    source="sheriff_true_seer",
                )
            )
        for check_day, target_id, result in get_character_seer_checks(game_state, speaker.id):
            if has_matching_public_claim(game_state, speaker.id, "seer_check", target_id):
                continue
            claims.append(
                PublicClaimState(
                    day=game_state.day,
                    character_id=speaker.id,
                    claim_type="seer_check",
                    claimed_role="seer",
                    target_id=target_id,
                    result=result,
                    source=f"sheriff_night_{check_day}",
                )
            )
        return claims

    if speaker.role != "werewolf" or speaker.id != game_state.wolf_fake_seer_id:
        return []

    player = get_character(game_state, game_state.player_character_id)
    player_claim = get_public_role_claim(game_state, player.id)
    player_check_claim = any(
        claim.character_id == player.id and claim.claim_type == "seer_check"
        for claim in game_state.public_claims
    )
    if player.role == "werewolf" and player_claim is not None and player_claim.claimed_role == "seer" and player_check_claim:
        return []

    claims = []
    if get_public_role_claim(game_state, speaker.id) is None:
        claims.append(
            PublicClaimState(
                day=game_state.day,
                character_id=speaker.id,
                claim_type="role",
                claimed_role="seer",
                source="sheriff_wolf_fake_seer",
            )
        )
    if not has_matching_public_claim(game_state, speaker.id, "seer_check", day=game_state.day):
        fake_check = choose_fake_seer_check(game_state, speaker)
        if fake_check is not None:
            target_id, result = fake_check
            claims.append(
                PublicClaimState(
                    day=game_state.day,
                    character_id=speaker.id,
                    claim_type="seer_check",
                    claimed_role="seer",
                    target_id=target_id,
                    result=result,
                    source="sheriff_wolf_fake_seer",
                )
            )
    return claims


def record_sheriff_speech(
    game_state: WolfGameState,
    speaker: CharacterState,
    speech_item: NpcSpeechItem,
    is_player: bool,
) -> None:
    round_number = game_state.sheriff_election.runoff_round if game_state.sheriff_election else 0
    phase_name = "SHERIFF_RUNOFF_SPEECH" if round_number > 0 else "SHERIFF_SPEECH"
    game_state.speeches.append(
        SpeechState(
            day=game_state.day,
            character_id=speaker.id,
            name=speaker.name,
            speech=speech_item.speech,
            is_player=is_player,
            evidence_titles=list(speech_item.evidence_titles),
            retrieval_mode=speech_item.retrieval_mode,
            llm_used=speech_item.llm_used,
            llm_provider=speech_item.llm_provider,
            llm_fallback_reason=speech_item.llm_fallback_reason,
            phase=phase_name,
            round=round_number,
            llm_validation_failure_id=(
                speech_item.llm_validation_failure.failure_id
                if speech_item.llm_validation_failure is not None
                else ""
            ),
        )
    )
    stage_label = "警上 PK" if round_number > 0 else "警上"
    game_state.public_logs.append(f"{speaker.id}号{speaker.name}{stage_label}发言：{speech_item.speech}")
    if not is_player:
        parsed = parse_player_speech(game_state, speech_item.speech)
        apply_npc_speech_updates(game_state, speaker, parsed)
    append_character_memory(speaker, f"第 {game_state.day} 天{stage_label}发言：{speech_item.speech}")


def generate_npc_sheriff_speech(
    game_state: WolfGameState,
    speaker: CharacterState,
) -> NpcSpeechItem:
    planned_claims = get_forced_sheriff_claims(game_state, speaker)
    target = get_primary_claim_target(game_state, planned_claims)
    if target is None:
        target = choose_speech_focus_target(game_state, speaker)
    rag_context = build_public_decision_rag_context(game_state, speaker, target, "警上竞选")
    evidence = choose_public_decision_evidence(rag_context)
    if planned_claims:
        rule_speech = build_public_claim_speech(game_state, speaker, planned_claims)
        rule_speech += "我竞选警长，会用后续发言和票型证明这套信息。"
    elif speaker.role == "werewolf" and speaker.id == game_state.wolf_fake_seer_id:
        rule_speech = "我先不争预言家身份，这轮警上更想观察已经起跳的人能否把逻辑说完整。"
    else:
        target_text = format_full_character_name(target) if target is not None else "场上的身份声明"
        rule_speech = f"我上警是想整理信息，目前会重点观察{target_text}，也会对自己的判断负责。"
    rule_speech = append_public_rag_evidence(rule_speech, evidence)
    rule_speech = apply_npc_voice(game_state, speaker, rule_speech, "meeting")
    llm_result = generate_public_speech_llm_text(
        game_state,
        speaker,
        target,
        rule_speech,
        rag_context,
        planned_claims,
    )
    speech_item = NpcSpeechItem(
        character_id=speaker.id,
        name=speaker.name,
        speech=llm_result.text,
        evidence_titles=get_safe_rag_titles(rag_context),
        retrieval_mode=str(HYBRID_INDEX.status()["mode"]),
        llm_used=llm_result.used_llm,
        llm_provider=llm_result.provider if llm_result.used_llm else "rule",
        llm_fallback_reason=llm_result.fallback_reason,
        llm_validation_failure=build_llm_validation_failure_view(
            game_state,
            llm_result.validation_failure_id,
        ),
    )
    register_public_claims(game_state, planned_claims)
    record_sheriff_speech(game_state, speaker, speech_item, False)
    return speech_item


def advance_sheriff_speech(game_state: WolfGameState) -> None:
    election = game_state.sheriff_election
    if election is None:
        raise HTTPException(status_code=400, detail="当前没有警上竞选。")
    election.current_index += 1
    if election.current_index < len(election.speech_order):
        return
    if election.runoff_round > 0:
        game_state.phase = "SHERIFF_RUNOFF_VOTE"
        game_state.public_logs.append("警上 PK 发言结束，进入第二轮警长投票。")
    else:
        game_state.phase = "SHERIFF_WITHDRAWAL"
        game_state.public_logs.append("警上发言结束，进入退水阶段。")
        player = get_character(game_state, game_state.player_character_id)
        if player.id not in election.candidates:
            apply_npc_sheriff_withdrawals(game_state)
            complete_sheriff_withdrawal(game_state)


def apply_npc_sheriff_withdrawals(game_state: WolfGameState) -> None:
    election = game_state.sheriff_election
    if election is None:
        return
    player = get_character(game_state, game_state.player_character_id)
    player_claim = get_public_role_claim(game_state, player.id)
    player_has_check = any(
        claim.character_id == player.id and claim.claim_type == "seer_check"
        for claim in game_state.public_claims
    )
    seer_claimants = set(get_public_role_claimants(game_state, "seer"))
    for candidate_id in list(election.candidates):
        candidate = get_character(game_state, candidate_id)
        if candidate.is_player or candidate.id in election.withdrawn or not candidate.alive:
            continue
        should_withdraw = False
        if candidate.role == "seer":
            should_withdraw = False
        elif candidate.role == "werewolf" and candidate.id == game_state.wolf_fake_seer_id:
            player_claim_is_strong = bool(
                player.role == "werewolf"
                and player_claim is not None
                and player_claim.claimed_role == "seer"
                and player_has_check
            )
            strategy_score = (
                candidate.personality.get("deception", 0.5)
                + candidate.personality.get("leadership", 0.5)
            )
            should_withdraw = player_claim_is_strong and (
                candidate.id not in seer_claimants or strategy_score < 1.55
            )
        elif candidate.id not in seer_claimants and seer_claimants:
            should_withdraw = candidate.personality.get("leadership", 0.5) < 0.82
        if should_withdraw:
            election.withdrawn.append(candidate.id)
            detail = f"{candidate.id}号{candidate.name}选择退水。"
            game_state.public_logs.append(detail)
            game_state.sheriff_events.append(
                SheriffEventState(day=game_state.day, event_type="withdraw", actor_id=candidate.id, detail=detail)
            )


def complete_sheriff_withdrawal(game_state: WolfGameState) -> None:
    active_candidates = get_active_sheriff_candidates(game_state)
    if not active_candidates:
        finish_sheriff_election(game_state, None, "所有候选人均已退水，警徽被撕毁。")
    elif len(active_candidates) == 1:
        winner = get_character(game_state, active_candidates[0])
        finish_sheriff_election(game_state, winner.id, f"退水结束，仅剩{winner.id}号{winner.name}，自动当选警长。")
    else:
        game_state.phase = "SHERIFF_VOTE"
        labels = [format_full_character_name(get_character(game_state, character_id)) for character_id in active_candidates]
        game_state.public_logs.append("退水结束，警下玩家将在以下候选人中投票：" + "、".join(labels) + "。")


def choose_npc_sheriff_vote_target(
    game_state: WolfGameState,
    voter: CharacterState,
    candidate_ids: list[int],
) -> int:
    candidates = [get_character(game_state, character_id) for character_id in candidate_ids]
    if voter.role == "werewolf":
        wolf_candidates = [candidate for candidate in candidates if candidate.role == "werewolf"]
        if wolf_candidates:
            return max(
                wolf_candidates,
                key=lambda candidate: (
                    get_public_role_claim(game_state, candidate.id) is not None,
                    candidate.personality.get("leadership", 0.5),
                ),
            ).id
    return max(
        candidates,
        key=lambda candidate: (
            float(voter.relationships.get(str(candidate.id), {}).get("trust", 0.5)) * 60
            + candidate.personality.get("leadership", 0.5) * 30
            - voter.suspicion.get(str(candidate.id), 0)
            + (8 if get_public_role_claim(game_state, candidate.id) is not None else 0),
            -candidate.id,
        ),
    ).id


def tally_sheriff_votes(votes: list[VoteState]) -> tuple[Optional[int], list[int]]:
    if not votes:
        return None, []
    counts: dict[int, int] = {}
    for vote in votes:
        counts[vote.target_id] = counts.get(vote.target_id, 0) + 1
    highest = max(counts.values())
    tied = sorted(target_id for target_id, count in counts.items() if count == highest)
    return (tied[0] if len(tied) == 1 else None), tied


def finish_sheriff_election(
    game_state: WolfGameState,
    winner_id: Optional[int],
    message: str,
) -> None:
    election = game_state.sheriff_election
    if election is not None:
        election.completed = True
    game_state.public_logs.append(message)
    if winner_id is None:
        game_state.sheriff_id = None
        game_state.badge_destroyed = True
        game_state.sheriff_events.append(
            SheriffEventState(day=game_state.day, event_type="badge_destroyed", detail=message)
        )
        reveal_first_night_results(game_state)
        return
    game_state.sheriff_id = winner_id
    game_state.badge_destroyed = False
    game_state.sheriff_events.append(
        SheriffEventState(day=game_state.day, event_type="elected", actor_id=winner_id, detail=message)
    )
    reveal_first_night_results(game_state)


def reveal_first_night_results(game_state: WolfGameState) -> None:
    if not game_state.first_night_result_pending:
        prepare_sheriff_meeting_order(game_state)
        return

    pending_records = list(game_state.pending_first_night_eliminations)
    game_state.pending_first_night_eliminations = []
    game_state.first_night_result_pending = False
    dead_character_ids = []
    for record in pending_records:
        if eliminate_character(
            game_state,
            record.character_id,
            record.cause,
            source_action=record.source_action,
            source_actor_ids=record.source_actor_ids,
            source_target_id=record.source_target_id,
        ):
            dead_character_ids.append(record.character_id)

    public_message = build_night_public_message(game_state, dead_character_ids)
    game_state.public_logs.append(public_message)
    night_resolution = next(
        (
            resolution
            for resolution in reversed(game_state.night_resolutions)
            if resolution.day == 1
        ),
        None,
    )
    poisoned_character_id = (
        night_resolution.poisoned_target_id
        if night_resolution is not None
        else None
    )
    hunter_message = handle_hunter_trigger(
        game_state,
        dead_character_ids,
        trigger="night",
        poisoned_character_id=poisoned_character_id,
        continuation="after_first_night_reveal",
    )
    if hunter_message:
        game_state.public_logs.append(hunter_message)
    if game_state.phase != "HUNTER_SHOT":
        continue_after_first_night_reveal(game_state)


def get_current_night_eliminated_ids(game_state: WolfGameState) -> list[int]:
    ids = []
    for elimination in game_state.eliminations:
        if elimination.day != game_state.day:
            continue
        if elimination.cause in {"night_kill", "witch_poison"}:
            ids.append(elimination.character_id)
    for shot in game_state.hunter_shots:
        if shot.day == game_state.day and shot.trigger == "night" and shot.target_id is not None:
            ids.append(shot.target_id)
    return list(dict.fromkeys(ids))


def prepare_sheriff_meeting_order(game_state: WolfGameState) -> None:
    if game_state.sheriff_id is None:
        start_day_meeting(game_state)
        return
    sheriff = get_character(game_state, game_state.sheriff_id)
    if not sheriff.alive:
        start_day_meeting(game_state)
        return
    night_out_ids = get_current_night_eliminated_ids(game_state)
    if night_out_ids:
        game_state.meeting_order_anchor_id = random.choice(night_out_ids)
        game_state.meeting_order_anchor_type = "out"
        anchor = get_character(game_state, game_state.meeting_order_anchor_id)
        game_state.public_logs.append(f"本轮以昨夜出局的{anchor.id}号{anchor.name}为发言锚点。")
    else:
        game_state.meeting_order_anchor_id = sheriff.id
        game_state.meeting_order_anchor_type = "sheriff"
        game_state.public_logs.append("昨夜无人出局，本轮由警长选择警左或警右发言。")
    if sheriff.is_player:
        game_state.phase = "MEETING_ORDER"
        return
    side = "left" if (game_state.day + sheriff.id) % 2 == 0 else "right"
    set_sheriff_meeting_order(game_state, sheriff, side)


def set_sheriff_meeting_order(
    game_state: WolfGameState,
    sheriff: CharacterState,
    side: str,
) -> None:
    if side not in {"left", "right"}:
        raise HTTPException(status_code=400, detail="发言方向只能选择 left 或 right。")
    if game_state.meeting_order_anchor_id is None:
        raise HTTPException(status_code=400, detail="当前没有可用的发言锚点。")
    seat_ids = [character.id for character in game_state.characters]
    alive_ids = {character.id for character in game_state.characters if character.alive}
    anchor_index = seat_ids.index(game_state.meeting_order_anchor_id)
    step = -1 if side == "left" else 1
    order = []
    sheriff_speaks_last = game_state.meeting_order_anchor_type == "sheriff"
    for offset in range(1, len(seat_ids) + 1):
        character_id = seat_ids[(anchor_index + step * offset) % len(seat_ids)]
        if character_id in alive_ids and (not sheriff_speaks_last or character_id != sheriff.id):
            order.append(character_id)
    if sheriff.alive and sheriff_speaks_last:
        order.append(sheriff.id)
    direction = "counterclockwise" if side == "left" else "clockwise"
    source = f"{game_state.meeting_order_anchor_type}_{side}"
    game_state.meeting = DayMeetingState(
        day=game_state.day,
        direction=direction,
        order=order,
        order_source=source,
        anchor_character_id=game_state.meeting_order_anchor_id,
        sheriff_id=sheriff.id,
    )
    game_state.phase = "DAY_MEETING"
    side_label = "左侧" if side == "left" else "右侧"
    anchor_label = "出局者" if game_state.meeting_order_anchor_type == "out" else "警长"
    first = get_character(game_state, order[0])
    if sheriff_speaks_last:
        order_detail = "警长最后发言。"
    else:
        sheriff_position = order.index(sheriff.id) + 1
        order_detail = f"警长按自然座次在第{sheriff_position}位发言，并可提出暂时归票。"
    detail = f"警长{format_full_character_name(sheriff)}选择从{anchor_label}{side_label}发言，{format_full_character_name(first)}首先发言，{order_detail}"
    game_state.public_logs.append(detail)
    game_state.sheriff_events.append(
        SheriffEventState(day=game_state.day, event_type="meeting_order", actor_id=sheriff.id, target_id=game_state.meeting_order_anchor_id, detail=detail)
    )


def choose_npc_sheriff_nomination(game_state: WolfGameState, sheriff: CharacterState) -> Optional[int]:
    return choose_npc_vote_target(game_state, sheriff, ignore_sheriff_lock=True)


def set_temporary_sheriff_nomination(
    game_state: WolfGameState,
    sheriff: CharacterState,
    target_id: int,
) -> str:
    if game_state.meeting is None:
        raise HTTPException(status_code=400, detail="当前没有进行中的小镇会议。")
    target = get_character(game_state, target_id)
    if not target.alive or target.id == sheriff.id:
        raise HTTPException(status_code=400, detail="警长只能暂时归票给另一名存活角色。")
    game_state.meeting.temporary_nomination_target_id = target.id
    detail = f"警长{sheriff.id}号{sheriff.name}暂时归票给{target.id}号{target.name}，最终归票可在全员发言后调整。"
    game_state.public_logs.append(detail)
    game_state.sheriff_events.append(
        SheriffEventState(
            day=game_state.day,
            event_type="temporary_nomination",
            actor_id=sheriff.id,
            target_id=target.id,
            detail=detail,
        )
    )
    return detail


def set_sheriff_nomination(
    game_state: WolfGameState,
    sheriff: CharacterState,
    target_id: int,
) -> str:
    if game_state.meeting is None:
        raise HTTPException(status_code=400, detail="当前没有进行中的小镇会议。")
    target = get_character(game_state, target_id)
    if not target.alive or target.id == sheriff.id:
        raise HTTPException(status_code=400, detail="警长必须归票给另一名存活角色。")
    game_state.meeting.nomination_target_id = target.id
    previous_target_id = game_state.meeting.temporary_nomination_target_id
    if previous_target_id is None:
        changed_text = "，此前未提出暂时归票"
    elif previous_target_id == target.id:
        changed_text = "，与暂时归票一致"
    else:
        changed_text = "，已调整暂时归票"
    detail = f"警长{sheriff.id}号{sheriff.name}最终归票给{target.id}号{target.name}{changed_text}，警长本轮投票将锁定该目标。"
    game_state.public_logs.append(detail)
    game_state.sheriff_events.append(
        SheriffEventState(day=game_state.day, event_type="nomination", actor_id=sheriff.id, target_id=target.id, detail=detail)
    )
    return detail


def enter_free_activity(game_state: WolfGameState) -> None:
    game_state.phase = "FREE_ACTIVITY"
    game_state.public_logs.append("小镇会议结束，进入会后自由活动。")


def choose_npc_badge_heir(game_state: WolfGameState, sheriff: CharacterState) -> Optional[int]:
    candidates = [character for character in game_state.characters if character.alive]
    if not candidates:
        return None
    if sheriff.role == "werewolf":
        wolf_candidates = [character for character in candidates if character.role == "werewolf"]
        if wolf_candidates:
            return max(wolf_candidates, key=lambda character: character.personality.get("leadership", 0.5)).id
    return max(
        candidates,
        key=lambda character: (
            float(sheriff.relationships.get(str(character.id), {}).get("trust", 0.5))
            - sheriff.suspicion.get(str(character.id), 0) / 100.0,
            character.personality.get("leadership", 0.5),
        ),
    ).id


def apply_badge_transfer(
    game_state: WolfGameState,
    old_sheriff: CharacterState,
    target_id: Optional[int],
) -> str:
    if target_id is None:
        game_state.sheriff_id = None
        game_state.badge_destroyed = True
        detail = f"{old_sheriff.id}号{old_sheriff.name}出局后撕毁了警徽。"
        event_type = "badge_destroyed"
    else:
        target = get_character(game_state, target_id)
        if not target.alive:
            raise HTTPException(status_code=400, detail="警徽只能移交给仍然存活的角色。")
        game_state.sheriff_id = target.id
        detail = f"{old_sheriff.id}号{old_sheriff.name}将警徽移交给{target.id}号{target.name}。"
        event_type = "badge_transfer"
    game_state.public_logs.append(detail)
    game_state.sheriff_events.append(
        SheriffEventState(day=game_state.day, event_type=event_type, actor_id=old_sheriff.id, target_id=target_id, detail=detail)
    )
    return detail


def maybe_start_badge_transfer(game_state: WolfGameState, continuation: str) -> bool:
    if game_state.sheriff_id is None or game_state.badge_destroyed:
        return False
    sheriff = get_character(game_state, game_state.sheriff_id)
    if sheriff.alive:
        return False
    alive_candidates = [character for character in game_state.characters if character.alive]
    if not alive_candidates:
        apply_badge_transfer(game_state, sheriff, None)
        return False
    if sheriff.is_player:
        game_state.pending_badge_transfer_from_id = sheriff.id
        game_state.pending_badge_continuation = continuation
        game_state.phase = "BADGE_TRANSFER"
        game_state.public_logs.append("玩家警长已出局，请先移交或撕毁警徽。")
        return True
    apply_badge_transfer(game_state, sheriff, choose_npc_badge_heir(game_state, sheriff))
    return False


def continue_after_elimination_without_badge(
    game_state: WolfGameState,
    continuation: str,
) -> None:
    if continuation == "after_first_night_reveal":
        winner, winner_reason = get_winner_result(game_state)
        if winner is not None:
            game_state.winner = winner
            game_state.winner_reason = winner_reason
            game_state.phase = "GAME_OVER"
            game_state.public_logs.append(build_winner_message(winner, winner_reason))
        elif game_state.sheriff_id is not None:
            prepare_sheriff_meeting_order(game_state)
        else:
            start_day_meeting(game_state)
        return
    if continuation == "after_night":
        if game_state.day == 1 and game_state.sheriff_election is None and not game_state.badge_destroyed:
            start_sheriff_signup(game_state)
        elif game_state.sheriff_id is not None:
            prepare_sheriff_meeting_order(game_state)
        else:
            start_day_meeting(game_state)
        return
    if continuation == "after_vote":
        game_state.day += 1
        game_state.phase = "NIGHT"
        game_state.meeting = None
        game_state.meeting_order_anchor_id = None
        game_state.meeting_order_anchor_type = ""
        game_state.public_logs.append(f"第 {game_state.day} 夜开始。")
        ensure_npc_night_actions(game_state)
        return
    raise ValueError(f"Unknown post-elimination continuation: {continuation}")


def continue_after_first_night_reveal(game_state: WolfGameState) -> None:
    if maybe_start_badge_transfer(game_state, "after_first_night_reveal"):
        return
    continue_after_elimination_without_badge(game_state, "after_first_night_reveal")


def continue_after_elimination(game_state: WolfGameState, continuation: str) -> None:
    if continuation == "after_first_night_reveal":
        continue_after_first_night_reveal(game_state)
        return
    winner, winner_reason = get_winner_result(game_state)
    if winner is not None:
        game_state.winner = winner
        game_state.winner_reason = winner_reason
        game_state.phase = "GAME_OVER"
        game_state.public_logs.append(build_winner_message(winner, winner_reason))
        return

    if maybe_start_badge_transfer(game_state, continuation):
        return
    continue_after_elimination_without_badge(game_state, continuation)


@app.post("/api/sheriff/signup", response_model=SheriffSignupResponse)
def submit_sheriff_signup(request: SheriffSignupRequest) -> SheriffSignupResponse:
    with GAME_LOCK:
        game_state = get_game_state_or_404(request.game_id)
        ensure_phase(game_state, "SHERIFF_SIGNUP")
        player = get_character(game_state, request.character_id)
        if not player.is_player or player.id != game_state.player_character_id:
            raise HTTPException(status_code=400, detail="只能由玩家提交自己的警上报名。")
        finalize_sheriff_signup(game_state, request.run_for_sheriff)
        signup_detail = (
            f"{player.id}号{player.name}报名竞选警长。"
            if request.run_for_sheriff
            else f"{player.id}号{player.name}选择不上警。"
        )
        game_state.sheriff_events.append(
            SheriffEventState(
                day=game_state.day,
                event_type="signup" if request.run_for_sheriff else "skip_signup",
                actor_id=player.id,
                detail=signup_detail,
            )
        )
        game_state.updated_at = datetime.now(timezone.utc).isoformat()
        election = game_state.sheriff_election
        candidates = list(election.candidates) if election is not None else []
    return SheriffSignupResponse(
        success=True,
        message="警上报名已确认。",
        candidates=candidates,
        next_speaker_id=get_current_sheriff_speaker_id(game_state),
    )


@app.post("/api/sheriff/player-speech", response_model=SheriffSpeechResponse)
def submit_player_sheriff_speech(request: SheriffSpeechRequest) -> SheriffSpeechResponse:
    speech = request.speech.strip()
    if not speech:
        raise HTTPException(status_code=400, detail="警上发言不能为空。")
    with GAME_LOCK:
        game_state = get_game_state_or_404(request.game_id)
        ensure_sheriff_speech_turn(game_state, request.character_id)
        speaker = get_character(game_state, request.character_id)
        if not speaker.is_player:
            raise HTTPException(status_code=400, detail="该接口只接受玩家警上发言。")
        parsed = parse_player_speech(game_state, speech)
        register_public_claims(
            game_state,
            parsed_claims_to_public_claims(game_state, speaker.id, parsed.claims),
        )
        apply_player_speech_updates(game_state, parsed)
        speech_item = NpcSpeechItem(character_id=speaker.id, name=speaker.name, speech=speech)
        record_sheriff_speech(game_state, speaker, speech_item, True)
        advance_sheriff_speech(game_state)
        game_state.updated_at = datetime.now(timezone.utc).isoformat()
    return SheriffSpeechResponse(
        speech=speech_item,
        next_speaker_id=get_current_sheriff_speaker_id(game_state),
        speeches_completed=game_state.phase not in {"SHERIFF_SPEECH", "SHERIFF_RUNOFF_SPEECH"},
    )


@app.post("/api/sheriff/npc-speech", response_model=SheriffSpeechResponse)
def generate_npc_sheriff_campaign_speech(request: SheriffSpeechRequest) -> SheriffSpeechResponse:
    with GAME_LOCK:
        game_state = get_game_state_or_404(request.game_id)
        ensure_sheriff_speech_turn(game_state, request.character_id)
        speaker = get_character(game_state, request.character_id)
        if speaker.is_player:
            raise HTTPException(status_code=400, detail="轮到玩家时，请在警长操作区提交发言。")
        speech_item = generate_npc_sheriff_speech(game_state, speaker)
        advance_sheriff_speech(game_state)
        game_state.updated_at = datetime.now(timezone.utc).isoformat()
    return SheriffSpeechResponse(
        speech=speech_item,
        next_speaker_id=get_current_sheriff_speaker_id(game_state),
        speeches_completed=game_state.phase not in {"SHERIFF_SPEECH", "SHERIFF_RUNOFF_SPEECH"},
    )


@app.post("/api/sheriff/withdraw", response_model=SheriffWithdrawalResponse)
def submit_sheriff_withdrawal(request: SheriffWithdrawalRequest) -> SheriffWithdrawalResponse:
    with GAME_LOCK:
        game_state = get_game_state_or_404(request.game_id)
        ensure_phase(game_state, "SHERIFF_WITHDRAWAL")
        player = get_character(game_state, request.character_id)
        if not player.is_player:
            raise HTTPException(status_code=400, detail="只能提交玩家自己的退水选择。")
        election = game_state.sheriff_election
        if election is None:
            raise HTTPException(status_code=400, detail="当前没有警上竞选。")
        if request.withdraw and player.id in election.candidates and player.id not in election.withdrawn:
            election.withdrawn.append(player.id)
            detail = f"{player.id}号{player.name}选择退水。"
            game_state.public_logs.append(detail)
            game_state.sheriff_events.append(
                SheriffEventState(day=game_state.day, event_type="withdraw", actor_id=player.id, detail=detail)
            )
        elif player.id in election.candidates:
            detail = f"{player.id}号{player.name}选择继续竞选。"
            game_state.public_logs.append(detail)
            game_state.sheriff_events.append(
                SheriffEventState(
                    day=game_state.day,
                    event_type="continue_campaign",
                    actor_id=player.id,
                    detail=detail,
                )
            )
        apply_npc_sheriff_withdrawals(game_state)
        complete_sheriff_withdrawal(game_state)
        game_state.updated_at = datetime.now(timezone.utc).isoformat()
        active_candidates = get_active_sheriff_candidates(game_state)
        phase = game_state.phase
    return SheriffWithdrawalResponse(
        success=True,
        message="退水阶段已完成。",
        active_candidates=active_candidates,
        phase=phase,
    )


@app.post("/api/sheriff/vote", response_model=SheriffVoteResponse)
def submit_and_resolve_sheriff_vote(request: SheriffVoteRequest) -> SheriffVoteResponse:
    with GAME_LOCK:
        game_state = get_game_state_or_404(request.game_id)
        if game_state.phase not in {"SHERIFF_VOTE", "SHERIFF_RUNOFF_VOTE"}:
            raise HTTPException(status_code=400, detail="当前不是警长投票阶段。")
        election = game_state.sheriff_election
        if election is None:
            raise HTTPException(status_code=400, detail="当前没有警上竞选。")
        active_candidates = get_active_sheriff_candidates(game_state)
        player = get_character(game_state, request.character_id)
        if not player.is_player:
            raise HTTPException(status_code=400, detail="只能由玩家触发警长投票。")
        votes = []
        election_participants = set(election.candidates)
        if player.alive and player.id not in election_participants:
            if request.target_id not in active_candidates:
                raise HTTPException(status_code=400, detail="请选择仍在竞选的警长候选人。")
            votes.append(VoteState(day=game_state.day, voter_id=player.id, target_id=int(request.target_id), reason="玩家警长票。"))
        elif request.target_id is not None:
            raise HTTPException(status_code=400, detail="参加过竞选的角色（含退水者）或出局玩家不能参与警长投票。")

        for voter in game_state.characters:
            if voter.is_player or not voter.alive or voter.id in election_participants:
                continue
            target_id = choose_npc_sheriff_vote_target(game_state, voter, active_candidates)
            votes.append(VoteState(day=game_state.day, voter_id=voter.id, target_id=target_id, reason="NPC 警长票。"))
        election.votes = votes
        ballots = [SheriffBallot(voter_id=vote.voter_id, target_id=vote.target_id) for vote in votes]
        winner_id, tied_ids = tally_sheriff_votes(votes)
        if winner_id is not None:
            winner = get_character(game_state, winner_id)
            message = f"警长投票结束，{winner.id}号{winner.name}当选警长。"
            finish_sheriff_election(game_state, winner.id, message)
        elif election.runoff_round == 0 and tied_ids:
            election.runoff_round = 1
            election.runoff_candidates = tied_ids
            election.speech_order = build_circular_subset_order(game_state, tied_ids)
            election.current_index = 0
            game_state.phase = "SHERIFF_RUNOFF_SPEECH"
            message = "警长票平票，进入 PK 发言：" + "、".join(format_full_character_name(get_character(game_state, character_id)) for character_id in tied_ids) + "。"
            game_state.public_logs.append(message)
        else:
            message = "第二轮警长票仍然平票，警徽被撕毁。"
            finish_sheriff_election(game_state, None, message)
        for ballot in ballots:
            game_state.sheriff_events.append(
                SheriffEventState(day=game_state.day, event_type="sheriff_vote", actor_id=ballot.voter_id, target_id=ballot.target_id, detail=f"{ballot.voter_id}号投给{ballot.target_id}号。")
            )
        game_state.updated_at = datetime.now(timezone.utc).isoformat()
        phase = game_state.phase
    return SheriffVoteResponse(
        ballots=ballots,
        winner_id=winner_id,
        tied_candidate_ids=tied_ids if winner_id is None else [],
        phase=phase,
        message=message,
    )


@app.post("/api/sheriff/meeting-order", response_model=SheriffActionResponse)
def submit_sheriff_meeting_order(request: SheriffMeetingOrderRequest) -> SheriffActionResponse:
    with GAME_LOCK:
        game_state = get_game_state_or_404(request.game_id)
        ensure_phase(game_state, "MEETING_ORDER")
        sheriff = get_character(game_state, request.character_id)
        if sheriff.id != game_state.sheriff_id or not sheriff.is_player:
            raise HTTPException(status_code=400, detail="只有玩家警长可以提交本轮发言方向。")
        set_sheriff_meeting_order(game_state, sheriff, request.side)
        game_state.updated_at = datetime.now(timezone.utc).isoformat()
    return SheriffActionResponse(success=True, message="本轮发言顺序已确定。", phase=game_state.phase)


@app.post("/api/sheriff/nominate", response_model=SheriffActionResponse)
def submit_sheriff_nomination(request: SheriffNominationRequest) -> SheriffActionResponse:
    with GAME_LOCK:
        game_state = get_game_state_or_404(request.game_id)
        ensure_phase(game_state, "SHERIFF_NOMINATION")
        sheriff = get_character(game_state, request.character_id)
        if sheriff.id != game_state.sheriff_id or not sheriff.is_player:
            raise HTTPException(status_code=400, detail="只有玩家警长可以提交归票。")
        message = set_sheriff_nomination(game_state, sheriff, request.target_id)
        enter_free_activity(game_state)
        game_state.updated_at = datetime.now(timezone.utc).isoformat()
    return SheriffActionResponse(success=True, message=message, phase=game_state.phase)


@app.post("/api/sheriff/transfer", response_model=SheriffActionResponse)
def submit_badge_transfer(request: BadgeTransferRequest) -> SheriffActionResponse:
    with GAME_LOCK:
        game_state = get_game_state_or_404(request.game_id)
        ensure_phase(game_state, "BADGE_TRANSFER")
        if request.character_id != game_state.pending_badge_transfer_from_id:
            raise HTTPException(status_code=400, detail="当前不是这名警长移交警徽。")
        old_sheriff = get_character(game_state, request.character_id)
        message = apply_badge_transfer(game_state, old_sheriff, request.target_id)
        continuation = game_state.pending_badge_continuation
        game_state.pending_badge_transfer_from_id = None
        game_state.pending_badge_continuation = ""
        continue_after_elimination_without_badge(game_state, continuation)
        game_state.updated_at = datetime.now(timezone.utc).isoformat()
    return SheriffActionResponse(success=True, message=message, phase=game_state.phase)


@app.post("/api/day/player-speech", response_model=PlayerSpeechResponse)
def submit_player_speech(request: PlayerSpeechRequest) -> PlayerSpeechResponse:
    speech = request.speech.strip()
    if not speech:
        raise HTTPException(status_code=400, detail="发言不能为空。")

    with GAME_LOCK:
        game_state = get_game_state_or_404(request.game_id)
        ensure_day_speech_phase(game_state)
        speaker = get_character(game_state, request.character_id)
        if speaker.id != game_state.player_character_id:
            raise HTTPException(status_code=400, detail="当前版本只允许玩家提交自己的发言。")
        if not speaker.alive:
            raise HTTPException(status_code=400, detail="出局角色不能发言。")
        ensure_current_meeting_speaker(game_state, speaker.id)

        public_speech = speech
        if speaker.id == game_state.sheriff_id:
            temporary_target_id = request.temporary_nomination_target_id
            if temporary_target_id is not None:
                set_temporary_sheriff_nomination(game_state, speaker, temporary_target_id)
                temporary_target = get_character(game_state, temporary_target_id)
                if "暂时归票" not in public_speech or temporary_target.name not in public_speech:
                    public_speech = public_speech.rstrip("。") + f"。我暂时归票给{format_full_character_name(temporary_target)}。"
        elif request.temporary_nomination_target_id is not None:
            raise HTTPException(status_code=400, detail="只有警长能在发言时提出暂时归票。")

        parsed = parse_player_speech(game_state, public_speech)
        added_public_claims = register_public_claims(
            game_state,
            parsed_claims_to_public_claims(game_state, speaker.id, parsed.claims),
        )
        apply_player_speech_updates(game_state, parsed)
        public_log = f"{speaker.id}号{speaker.name}：{public_speech}"
        game_state.speeches.append(
            SpeechState(
                day=game_state.day,
                character_id=speaker.id,
                name=speaker.name,
                speech=public_speech,
                is_player=True,
            )
        )
        game_state.public_logs.append(public_log)
        advance_day_meeting(game_state)
        game_state.updated_at = datetime.now(timezone.utc).isoformat()

    return PlayerSpeechResponse(
        parsed=parsed,
        public_log=public_log,
        state_updates={
            "discussion_focus": parsed.mentioned_characters,
            "public_claims": [
                build_public_claim_label(game_state, claim)
                for claim in added_public_claims
            ],
            "next_speaker_id": get_current_meeting_speaker_id(game_state),
            "meeting_completed": game_state.phase == "FREE_ACTIVITY",
        },
    )


@app.post("/api/day/npc-speech", response_model=NpcSpeechResponse)
def generate_npc_speech(request: NpcSpeechRequest) -> NpcSpeechResponse:
    with GAME_LOCK:
        game_state = get_game_state_or_404(request.game_id)
        ensure_day_speech_phase(game_state)
        ensure_current_meeting_speaker(game_state, request.character_id)
        speaker = get_character(game_state, request.character_id)
        if speaker.is_player:
            raise HTTPException(status_code=400, detail="轮到玩家时，请在控制面板提交发言。")

        if (
            game_state.sheriff_id == speaker.id
            and game_state.meeting is not None
            and game_state.meeting.temporary_nomination_target_id is None
        ):
            nomination_target_id = choose_npc_sheriff_nomination(game_state, speaker)
            if nomination_target_id is not None:
                set_temporary_sheriff_nomination(game_state, speaker, nomination_target_id)

        speech_item, memory_update = generate_current_npc_meeting_speech(game_state, speaker)
        advance_day_meeting(game_state)
        game_state.updated_at = datetime.now(timezone.utc).isoformat()

    return NpcSpeechResponse(
        speech=speech_item,
        memory_update=memory_update,
        next_speaker_id=get_current_meeting_speaker_id(game_state),
        meeting_completed=game_state.phase == "FREE_ACTIVITY",
    )


@app.post("/api/day/npc-speeches", response_model=NpcSpeechesResponse)
def generate_npc_speeches(request: NpcSpeechesRequest) -> NpcSpeechesResponse:
    with GAME_LOCK:
        game_state = get_game_state_or_404(request.game_id)
        ensure_day_speech_phase(game_state)
        if request.day is not None and request.day != game_state.day:
            raise HTTPException(status_code=400, detail="请求的天数和当前游戏天数不一致。")

        current_speaker_id = get_current_meeting_speaker_id(game_state)
        if current_speaker_id is None:
            raise HTTPException(status_code=400, detail="小镇会议已经结束。")
        speaker = get_character(game_state, current_speaker_id)
        if speaker.is_player:
            raise HTTPException(status_code=400, detail="当前轮到玩家发言。")

        speech_item, memory_update = generate_current_npc_meeting_speech(game_state, speaker)
        advance_day_meeting(game_state)
        game_state.updated_at = datetime.now(timezone.utc).isoformat()

    return NpcSpeechesResponse(speeches=[speech_item], memory_updates=[memory_update])


@app.post("/api/day/end-free-activity", response_model=EndFreeActivityResponse)
def end_free_activity(request: EndFreeActivityRequest) -> EndFreeActivityResponse:
    with GAME_LOCK:
        game_state = get_game_state_or_404(request.game_id)
        ensure_phase(game_state, "FREE_ACTIVITY")
        game_state.phase = "VOTE"
        game_state.public_logs.append("会后自由活动结束，进入投票阶段。")
        game_state.updated_at = datetime.now(timezone.utc).isoformat()

    return EndFreeActivityResponse(success=True, message="自由活动已结束，可以开始投票。")


@app.post("/api/day/private-chat", response_model=PrivateChatResponse)
def private_chat(request: PrivateChatRequest) -> PrivateChatResponse:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="私密追问不能为空。")

    with GAME_LOCK:
        game_state = get_game_state_or_404(request.game_id)
        ensure_phase(game_state, "FREE_ACTIVITY")
        player = get_character(game_state, game_state.player_character_id)
        if not player.alive:
            raise HTTPException(status_code=400, detail="玩家已出局，不能进行私密追问。")

        npc = get_character(game_state, request.npc_character_id)
        if npc.is_player:
            raise HTTPException(status_code=400, detail="私密追问目标必须是 NPC。")
        if not npc.alive:
            raise HTTPException(status_code=400, detail="出局 NPC 不能接受私密追问。")

        triggered_easter_egg = find_triggered_easter_egg(npc, question)
        easter_egg_id = ""
        easter_egg_first_time = False
        revealed_role: Optional[str] = None
        if triggered_easter_egg is not None:
            easter_egg_id = triggered_easter_egg.egg_id
            easter_egg_first_time = not has_triggered_easter_egg(
                game_state,
                npc.id,
                easter_egg_id,
            )
            effective = False
            rag_context = []
            rule_reply = build_triggered_easter_egg_reply(
                npc,
                triggered_easter_egg,
                easter_egg_first_time,
            )
            if triggered_easter_egg.reveal_self_role and easter_egg_first_time:
                revealed_role = npc.role
            llm_result = generate_private_chat_llm_text(
                game_state,
                npc,
                question,
                rule_reply,
                [],
                required_self_role=revealed_role,
                easter_egg_id=easter_egg_id,
            )
            reply = render_private_perspective_text(game_state, npc, llm_result.text)
        else:
            parsed_question, unresolved_reference = parse_private_question(game_state, npc, question)
            effective = (
                not unresolved_reference
                and not has_effective_private_question(game_state, npc.id)
            )
            if effective:
                apply_private_question_effect(game_state, npc, question, parsed_question)
            rag_context = (
                []
                if unresolved_reference
                else build_private_rag_context(game_state, npc, question)
            )
            if unresolved_reference:
                rule_reply = "你说的‘他/她/TA’目前没有明确对象。你指的是哪位角色？请告诉我号码或名字。"
                llm_result = generate_private_chat_llm_text(
                    game_state,
                    npc,
                    question,
                    rule_reply,
                    [],
                )
                reply = render_private_perspective_text(game_state, npc, llm_result.text)
            else:
                rule_reply = build_private_chat_reply(
                    game_state,
                    npc,
                    question,
                    effective,
                    rag_context,
                    parsed_question,
                )
                rule_reply = apply_npc_voice(game_state, npc, rule_reply, "private")
                llm_result = generate_private_chat_llm_text(
                    game_state,
                    npc,
                    question,
                    rule_reply,
                    rag_context,
                )
                reply = render_private_perspective_text(game_state, npc, llm_result.text)
        game_state.private_conversations.append(
            PrivateConversationState(
                day=game_state.day,
                npc_character_id=npc.id,
                question=question,
                reply=reply,
                effective=effective,
                llm_validation_failure_id=llm_result.validation_failure_id,
                easter_egg_id=easter_egg_id,
                easter_egg_first_time=easter_egg_first_time,
                revealed_role=revealed_role,
            )
        )
        game_state.updated_at = datetime.now(timezone.utc).isoformat()

    return PrivateChatResponse(
        npc_character_id=npc.id,
        npc_name=npc.name,
        reply=reply,
        effective=effective,
        can_influence_again=not has_effective_private_question(game_state, npc.id),
        knowledge_titles=get_safe_rag_titles(rag_context),
        retrieval_mode=str(HYBRID_INDEX.status()["mode"]),
        llm_used=llm_result.used_llm,
        llm_provider=llm_result.provider if llm_result.used_llm else "rule",
        llm_fallback_reason=llm_result.fallback_reason,
        llm_validation_failure=build_llm_validation_failure_view(
            game_state,
            llm_result.validation_failure_id,
        ),
        easter_egg_triggered=triggered_easter_egg is not None,
        easter_egg_first_time=easter_egg_first_time,
    )


@app.post("/api/vote/npc-decisions", response_model=NpcVoteDecisionsResponse)
def generate_npc_vote_decisions(request: NpcVoteDecisionsRequest) -> NpcVoteDecisionsResponse:
    with GAME_LOCK:
        game_state = get_game_state_or_404(request.game_id)
        ensure_vote_phase(game_state)
        npc_votes = ensure_npc_vote_decisions(game_state)
        game_state.phase = "VOTE"
        game_state.updated_at = datetime.now(timezone.utc).isoformat()

    return NpcVoteDecisionsResponse(npc_votes=npc_votes)


@app.post("/api/vote/player", response_model=PlayerVoteResponse)
def submit_player_vote(request: PlayerVoteRequest) -> PlayerVoteResponse:
    with GAME_LOCK:
        game_state = get_game_state_or_404(request.game_id)
        ensure_vote_phase(game_state)
        voter = get_character(game_state, request.character_id)
        if voter.id != game_state.player_character_id:
            raise HTTPException(status_code=400, detail="当前版本只允许玩家提交自己的投票。")
        if request.target_id is None:
            raise HTTPException(status_code=400, detail="请选择玩家的投票目标。")
        validate_vote(game_state, voter, request.target_id)
        if (
            game_state.sheriff_id == voter.id
            and game_state.meeting is not None
            and game_state.meeting.nomination_target_id is not None
            and request.target_id != game_state.meeting.nomination_target_id
        ):
            raise HTTPException(status_code=400, detail="警长的投票必须与公开归票目标一致。")
        target = get_character(game_state, request.target_id)
        upsert_vote(
            game_state,
            VoteState(
                day=game_state.day,
                voter_id=voter.id,
                target_id=target.id,
                reason=request.reason.strip() or "玩家投票。",
                weight=1.5 if game_state.sheriff_id == voter.id else 1.0,
            ),
        )
        game_state.phase = "VOTE"
        game_state.updated_at = datetime.now(timezone.utc).isoformat()

    return PlayerVoteResponse(success=True, message="投票已记录。")


@app.post("/api/vote/resolve", response_model=VoteResolveResponse)
def resolve_vote(request: VoteResolveRequest) -> VoteResolveResponse:
    with GAME_LOCK:
        game_state = get_game_state_or_404(request.game_id)
        ensure_vote_phase(game_state)
        ensure_npc_vote_decisions(game_state)
        exiled_character_id, current_votes, public_message = finalize_current_vote(game_state)
        vote_result = {str(vote.voter_id): vote.target_id for vote in current_votes}
        game_state.updated_at = datetime.now(timezone.utc).isoformat()

    return VoteResolveResponse(
        exiled_character_id=exiled_character_id,
        vote_result=vote_result,
        public_message=public_message,
        is_game_over=game_state.phase == "GAME_OVER",
        winner=game_state.winner,
    )


@app.post("/api/vote/submit-and-resolve", response_model=SubmitAndResolveVoteResponse)
def submit_and_resolve_all_votes(request: PlayerVoteRequest) -> SubmitAndResolveVoteResponse:
    with GAME_LOCK:
        game_state = get_game_state_or_404(request.game_id)
        ensure_vote_phase(game_state)
        player = get_character(game_state, request.character_id)
        if not player.is_player or player.id != game_state.player_character_id:
            raise HTTPException(status_code=400, detail="只能由玩家触发本轮同时投票。")

        game_state.votes = [vote for vote in game_state.votes if vote.day != game_state.day]
        if player.alive:
            if request.target_id is None:
                raise HTTPException(status_code=400, detail="请选择玩家的投票目标。")
            validate_vote(game_state, player, request.target_id)
            if (
                game_state.sheriff_id == player.id
                and game_state.meeting is not None
                and game_state.meeting.nomination_target_id is not None
                and request.target_id != game_state.meeting.nomination_target_id
            ):
                raise HTTPException(status_code=400, detail="警长的投票必须与公开归票目标一致。")
            target = get_character(game_state, request.target_id)
            upsert_vote(
                game_state,
                VoteState(
                    day=game_state.day,
                    voter_id=player.id,
                    target_id=target.id,
                    reason=request.reason.strip() or "这是我的公开投票判断。",
                    weight=1.5 if game_state.sheriff_id == player.id else 1.0,
                ),
            )
        elif request.target_id is not None:
            raise HTTPException(status_code=400, detail="玩家已经出局，不能提交投票目标。")

        ensure_npc_vote_decisions(game_state)
        current_votes = get_current_valid_votes(game_state)
        ballot_details = build_vote_ballot_details(game_state, current_votes)
        vote_totals = build_vote_totals(current_votes)
        exiled_character_id, _resolved_votes, public_message = finalize_current_vote(game_state)
        game_state.updated_at = datetime.now(timezone.utc).isoformat()
        phase = game_state.phase

    return SubmitAndResolveVoteResponse(
        exiled_character_id=exiled_character_id,
        ballots=ballot_details,
        vote_totals=vote_totals,
        public_message=public_message,
        is_game_over=phase == "GAME_OVER",
        phase=phase,
        winner=game_state.winner,
    )


@app.get("/npcs", response_model=list[NPCProfile])
def list_npcs() -> list[NPCProfile]:
    return list(NPC_PROFILES.values())


@app.get("/knowledge", response_model=list[KnowledgeItem])
def list_knowledge() -> list[KnowledgeItem]:
    return KNOWLEDGE_BASE


@app.get("/knowledge/search", response_model=KnowledgeSearchResponse)
def search_knowledge(npc_name: str, message: str, limit: int = 3) -> KnowledgeSearchResponse:
    results = find_scored_knowledge(npc_name, message, limit)
    top_result = results[0] if results else None
    return KnowledgeSearchResponse(
        npc_name=npc_name,
        message=message,
        matched=top_result is not None,
        score=top_result.score if top_result else 0,
        item=top_result.item if top_result else None,
        results=results,
        retrieval_mode=str(HYBRID_INDEX.status()["mode"]),
        vector_model=str(HYBRID_INDEX.status()["model_name"]),
    )


@app.post("/admin/reload-config", response_model=ReloadConfigResponse)
def reload_config() -> ReloadConfigResponse:
    load_config_files()
    return ReloadConfigResponse(
        npc_count=len(NPC_PROFILES),
        knowledge_count=len(KNOWLEDGE_BASE),
        message="已重新加载 NPC 人设和知识库配置。",
    )


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    profile = NPC_PROFILES.get(request.npc_name, DEFAULT_NPC_PROFILE)
    memory_key = make_memory_key(request.player_id, profile.npc_name)
    matched_knowledge = find_knowledge(profile.npc_name, request.message, limit=2)

    with MEMORY_LOCK:
        memories = MEMORY_STORE.setdefault(memory_key, [])
        memory_count = len(memories) + 1
        reply = build_reply(
            profile,
            request.message,
            memory_count,
            matched_knowledge,
            memories,
        )
        memories.append(
            MemoryItem(
                player_id=request.player_id,
                npc_name=profile.npc_name,
                player_message=request.message,
                npc_reply=reply,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
        )
        save_memory_store()

    knowledge_title = matched_knowledge[0].title if matched_knowledge else ""
    knowledge_titles = [item.title for item in matched_knowledge]
    return ChatResponse(
        npc_name=profile.npc_name,
        reply=reply,
        memory_count=memory_count,
        relationship_level=get_relationship_level(memory_count),
        knowledge_title=knowledge_title,
        knowledge_titles=knowledge_titles,
        retrieval_mode=str(HYBRID_INDEX.status()["mode"]),
    )


@app.get("/memory/{player_id}/{npc_name}", response_model=list[MemoryItem])
def get_memory(player_id: str, npc_name: str) -> list[MemoryItem]:
    memory_key = make_memory_key(player_id, npc_name)
    with MEMORY_LOCK:
        return list(MEMORY_STORE.get(memory_key, []))


@app.delete("/memory", response_model=ClearMemoryResponse)
def clear_all_memory() -> ClearMemoryResponse:
    with MEMORY_LOCK:
        deleted_count = count_memory_items(MEMORY_STORE)
        MEMORY_STORE.clear()
        save_memory_store()

    return ClearMemoryResponse(
        deleted_count=deleted_count,
        message="已清空全部 NPC 记忆。",
    )


@app.delete("/memory/{player_id}", response_model=ClearMemoryResponse)
def clear_player_memory(player_id: str) -> ClearMemoryResponse:
    with MEMORY_LOCK:
        memory_keys = [
            memory_key
            for memory_key in MEMORY_STORE.keys()
            if memory_key.startswith(f"{player_id}::")
        ]
        deleted_count = sum(len(MEMORY_STORE[memory_key]) for memory_key in memory_keys)
        for memory_key in memory_keys:
            del MEMORY_STORE[memory_key]
        save_memory_store()

    return ClearMemoryResponse(
        deleted_count=deleted_count,
        message=f"已清空玩家 {player_id} 的全部 NPC 记忆。",
    )


@app.delete("/memory/{player_id}/{npc_name}", response_model=ClearMemoryResponse)
def clear_npc_memory(player_id: str, npc_name: str) -> ClearMemoryResponse:
    memory_key = make_memory_key(player_id, npc_name)

    with MEMORY_LOCK:
        deleted_count = len(MEMORY_STORE.get(memory_key, []))
        MEMORY_STORE.pop(memory_key, None)
        save_memory_store()

    return ClearMemoryResponse(
        deleted_count=deleted_count,
        message=f"已清空玩家 {player_id} 与 NPC {npc_name} 的记忆。",
    )


def build_reply(
    profile: NPCProfile,
    message: str,
    memory_count: int,
    matched_knowledge: list[KnowledgeItem],
    memories: list[MemoryItem],
) -> str:
    if memory_count == 1:
        memory_hint = "这是我们第一次聊天。"
    else:
        last_memory = memories[-1]
        memory_hint = (
            f"这是我们第 {memory_count} 次聊天。"
            f"我记得你上次说过：{last_memory.player_message}。"
        )

    if matched_knowledge:
        knowledge_lines = [
            f"《{item.title}》：{item.content}"
            for item in matched_knowledge
        ]
        knowledge_hint = "我检索到这些资料：" + " ".join(knowledge_lines)
    else:
        profile_knowledge = profile.knowledge[0] if profile.knowledge else "我还没有可用知识。"
        knowledge_hint = f"暂时没有检索到更精确的资料，我先根据人设知识回答：{profile_knowledge}"

    relationship_hint = get_relationship_hint(memory_count)

    return (
        f"你好，我是 {profile.npc_name}，身份是{profile.role}。"
        f"{memory_hint}"
        f"{relationship_hint}"
        f"你刚才说：{message}。"
        f"我现在的人设是：{profile.personality}"
        f"{knowledge_hint}"
    )


def find_knowledge(npc_name: str, message: str, limit: int = 2) -> list[KnowledgeItem]:
    return [
        result.item
        for result in find_scored_knowledge(npc_name, message, limit)
    ]


def find_scored_knowledge(npc_name: str, message: str, limit: int = 3) -> list[ScoredKnowledgeItem]:
    scored_items = []
    vector_scores = HYBRID_INDEX.search(message)

    for index, item in enumerate(KNOWLEDGE_BASE):
        if item.npc_name not in (npc_name, "*"):
            continue

        keyword_score = score_knowledge_item(item, message)
        vector_score = max(0.0, vector_scores.get(index, 0.0))
        if keyword_score <= 0 and vector_score < 0.35:
            continue

        combined_score = int(round(keyword_score * 12 + vector_score * 100))
        scored_items.append(
            ScoredKnowledgeItem(
                score=combined_score,
                keyword_score=keyword_score,
                vector_score=round(vector_score, 4),
                item=item,
            )
        )

    scored_items.sort(key=lambda result: result.score, reverse=True)
    return scored_items[:max(limit, 1)]


def score_knowledge_item(item: KnowledgeItem, message: str) -> int:
    message_lower = message.lower()
    score = 0

    for keyword in item.keywords:
        if keyword.lower() in message_lower:
            score += 3

    if item.title.lower() in message_lower:
        score += 2

    for word in message_lower.split():
        if word and word in item.content.lower():
            score += 1

    return score


def make_memory_key(player_id: str, npc_name: str) -> str:
    return f"{player_id}::{npc_name}"


def count_memory_items(memory_store: dict[str, list[MemoryItem]]) -> int:
    return sum(len(items) for items in memory_store.values())


def get_relationship_level(memory_count: int) -> str:
    if memory_count <= 1:
        return "初次见面"
    if memory_count <= 3:
        return "熟悉"
    if memory_count <= 6:
        return "信任"
    return "老朋友"


def get_relationship_hint(memory_count: int) -> str:
    relationship_level = get_relationship_level(memory_count)
    if relationship_level == "初次见面":
        return "我们刚认识，我会先用清楚、基础的方式回答。"
    if relationship_level == "熟悉":
        return "我们已经有点熟了，我会结合之前的交流继续说明。"
    if relationship_level == "信任":
        return "我们已经建立了信任，我会更主动地帮你梳理下一步。"
    return "我们已经是老朋友了，我会直接给你更贴近当前 Demo 的建议。"


def get_game_state_or_404(game_id: str) -> WolfGameState:
    game_state = GAME_STORE.get(game_id)
    if game_state is None:
        raise HTTPException(status_code=404, detail="未找到这局游戏。")
    return game_state


def ensure_phase(game_state: WolfGameState, expected_phase: str) -> None:
    if game_state.phase != expected_phase:
        raise HTTPException(
            status_code=400,
            detail=f"当前阶段是 {game_state.phase}，不能执行 {expected_phase} 阶段操作。",
        )


def initialize_role_resources(game_state: WolfGameState) -> None:
    resources: dict[str, dict[str, object]] = {}
    for character in game_state.characters:
        if character.role == "witch":
            resources[str(character.id)] = {
                "antidote_available": True,
                "poison_available": True,
            }
        elif character.role == "guard":
            resources[str(character.id)] = {
                "last_protected_target_id": None,
                "last_protected_day": 0,
            }
    game_state.role_resources = resources


def get_role_resources(
    game_state: WolfGameState,
    character_id: int,
) -> dict[str, object]:
    return game_state.role_resources.setdefault(str(character_id), {})


def build_player_private_info_dict(game_state: WolfGameState) -> dict[str, object]:
    player = get_character(game_state, game_state.player_character_id)
    last_check_result = game_state.player_private_info.get("last_check_result")
    wolf_teammates = []
    if player.role == "werewolf":
        wolf_teammates = [
            {
                "id": character.id,
                "name": character.name,
                "alive": character.alive,
            }
            for character in game_state.characters
            if character.role == "werewolf" and character.id != player.id
        ]

    witch_attacked_target = None
    antidote_available = False
    poison_available = False
    if player.role == "witch":
        resources = get_role_resources(game_state, player.id)
        antidote_available = bool(resources.get("antidote_available", False))
        poison_available = bool(resources.get("poison_available", False))
        if game_state.phase == "NIGHT" and player.alive:
            attacked_target_id = get_current_wolf_target(game_state)
            if attacked_target_id is not None:
                attacked_target = get_character(game_state, attacked_target_id)
                witch_attacked_target = {
                    "id": attacked_target.id,
                    "name": attacked_target.name,
                }

    return {
        "role": player.role,
        "camp": player.camp,
        "last_check_result": (
            last_check_result if isinstance(last_check_result, dict) else None
        ),
        "wolf_teammates": wolf_teammates,
        "witch_attacked_target": witch_attacked_target,
        "witch_antidote_available": antidote_available,
        "witch_poison_available": poison_available,
        "hunter_can_shoot": (
            game_state.phase == "HUNTER_SHOT"
            and game_state.pending_hunter_id == player.id
        ),
        "action_history": build_player_action_history(game_state),
    }


def build_player_action_history(game_state: WolfGameState) -> list[str]:
    player = get_character(game_state, game_state.player_character_id)
    items: list[tuple[int, int, int, str]] = []
    sequence = 0

    def add_item(day: int, phase_order: int, text: str) -> None:
        nonlocal sequence
        items.append((day, phase_order, sequence, text))
        sequence += 1

    resolutions = {
        resolution.day: resolution
        for resolution in game_state.night_resolutions
    }
    for action in game_state.night_actions:
        if action.actor_id != player.id:
            continue
        add_item(
            action.day,
            10,
            build_player_night_action_history_text(
                game_state,
                player,
                action,
                resolutions.get(action.day),
            ),
        )

    for shot in game_state.hunter_shots:
        if shot.hunter_id != player.id:
            continue
        if shot.target_id is None:
            text = f"第{shot.day}天 · 猎人：选择不开枪"
        else:
            target = get_character(game_state, shot.target_id)
            text = f"第{shot.day}天 · 猎人：向{format_full_character_name(target)}开枪"
        add_item(shot.day, 20, text)

    for event in game_state.sheriff_events:
        if event.actor_id != player.id:
            continue
        event_label = {
            "signup": "警上报名",
            "skip_signup": "警上报名",
            "withdraw": "退水",
            "continue_campaign": "退水",
            "sheriff_vote": "警长投票",
            "elected": "当选警长",
            "meeting_order": "发言顺序",
            "temporary_nomination": "暂时归票",
            "nomination": "最终归票",
            "badge_transfer": "警徽移交",
            "badge_destroyed": "撕毁警徽",
        }.get(event.event_type, "警长操作")
        add_item(event.day, 30, f"第{event.day}天 · {event_label}：{event.detail}")

    for speech in game_state.speeches:
        if speech.character_id != player.id:
            continue
        phase_label = {
            "SHERIFF_SPEECH": "警上发言",
            "SHERIFF_RUNOFF_SPEECH": "警上 PK 发言",
            "DAY_MEETING": "公开发言",
        }.get(speech.phase, "公开发言")
        add_item(
            speech.day,
            35 if speech.phase.startswith("SHERIFF") else 40,
            f"第{speech.day}天 · {phase_label}：{speech.speech}",
        )

    for conversation in game_state.private_conversations:
        npc = get_character(game_state, conversation.npc_character_id)
        if conversation.easter_egg_id:
            if not conversation.easter_egg_first_time:
                continue
            detail = f"发现{npc.name}的关键词彩蛋"
            if conversation.revealed_role:
                detail += "；对方向你透露本局身份是" + ROLE_LABELS.get(
                    conversation.revealed_role,
                    conversation.revealed_role,
                )
            add_item(
                conversation.day,
                45,
                f"第{conversation.day}天 · 彩蛋：{detail}",
            )
            continue
        add_item(
            conversation.day,
            45,
            f"第{conversation.day}天 · 私聊{format_full_character_name(npc)}：{conversation.question}",
        )

    for vote in game_state.votes:
        if vote.voter_id != player.id:
            continue
        target = get_character(game_state, vote.target_id)
        reason = f"；理由：{vote.reason}" if vote.reason else ""
        add_item(
            vote.day,
            50,
            f"第{vote.day}天 · 放逐投票：投给{format_full_character_name(target)}{reason}",
        )

    items.sort(key=lambda item: (item[0], item[1], item[2]))
    return [item[3] for item in items]


def build_player_night_action_history_text(
    game_state: WolfGameState,
    player: CharacterState,
    action: NightActionState,
    resolution: Optional[NightResolutionState],
) -> str:
    prefix = f"第{action.day}夜 · {ROLE_LABELS.get(player.role, player.role)}："
    target = (
        get_character(game_state, action.target_id)
        if action.target_id is not None
        else None
    )
    target_label = format_full_character_name(target) if target is not None else "无目标"
    pending_suffix = "（等待结算）" if resolution is None else ""

    if action.action_type == "seer_check" and target is not None:
        if resolution is None:
            return prefix + f"查验{target_label}{pending_suffix}"
        result = "狼人" if target.role == "werewolf" else "好人"
        return prefix + f"查验{target_label} → {result}"
    if action.action_type == "witch_save" and target is not None:
        return prefix + f"使用解药救{target_label}{pending_suffix}"
    if action.action_type == "witch_poison" and target is not None:
        return prefix + f"对{target_label}使用毒药{pending_suffix}"
    if action.action_type == "guard_protect" and target is not None:
        if resolution is None:
            return prefix + f"守护{target_label}{pending_suffix}"
        if resolution.attacked_target_id == target.id:
            return prefix + f"守护{target_label} → 挡下狼刀"
        return prefix + f"守护{target_label} → 当夜未遭狼刀"
    if action.action_type == "werewolf_kill" and target is not None:
        if resolution is None:
            return prefix + f"选择刀{target_label}{pending_suffix}"
        final_target = (
            get_character(game_state, resolution.attacked_target_id)
            if resolution.attacked_target_id is not None
            else None
        )
        if final_target is None:
            return prefix + f"选择刀{target_label} → 狼队没有形成刀口"
        final_label = format_full_character_name(final_target)
        return prefix + f"选择刀{target_label} → 最终狼队刀口为{final_label}"
    if action.action_type == "none":
        return prefix + "选择不使用夜间技能"
    return prefix + f"执行{action.action_type}，目标为{target_label}{pending_suffix}"


def validate_night_action(
    game_state: WolfGameState,
    actor: CharacterState,
    action_type: str,
    target_id: Optional[int],
) -> None:
    if not actor.alive:
        raise HTTPException(status_code=400, detail="出局角色不能行动。")

    allowed_actions = get_allowed_night_actions(actor)
    if action_type not in allowed_actions:
        raise HTTPException(
            status_code=400,
            detail=f"{ROLE_LABELS.get(actor.role, actor.role)} 不能执行 {action_type}。",
        )

    if action_type == "none":
        return

    if target_id is None:
        raise HTTPException(status_code=400, detail="这个行动需要选择目标。")

    target = get_character(game_state, target_id)
    if not target.alive:
        raise HTTPException(status_code=400, detail="不能选择已出局角色。")
    if action_type == "werewolf_kill":
        if target.role == "werewolf":
            raise HTTPException(status_code=400, detail="狼人不能袭击狼队友。")
        return
    if action_type == "seer_check" and target.id == actor.id:
        raise HTTPException(status_code=400, detail="预言家不能查验自己。")
    if action_type == "guard_protect":
        resources = get_role_resources(game_state, actor.id)
        if (
            resources.get("last_protected_target_id") == target.id
            and int(resources.get("last_protected_day", 0)) == game_state.day - 1
        ):
            raise HTTPException(status_code=400, detail="守卫不能连续两晚守护同一角色。")
        return
    if action_type == "witch_save":
        resources = get_role_resources(game_state, actor.id)
        if not bool(resources.get("antidote_available", False)):
            raise HTTPException(status_code=400, detail="女巫的解药已经使用。")
        attacked_target_id = get_current_wolf_target(game_state)
        if attacked_target_id is None or target.id != attacked_target_id:
            raise HTTPException(status_code=400, detail="解药只能用于本夜被狼人袭击的角色。")
        if target.id == actor.id and game_state.day != 1:
            raise HTTPException(status_code=400, detail="女巫只有第一夜可以自救。")
        return
    if action_type == "witch_poison":
        resources = get_role_resources(game_state, actor.id)
        if not bool(resources.get("poison_available", False)):
            raise HTTPException(status_code=400, detail="女巫的毒药已经使用。")
        if target.id == actor.id:
            raise HTTPException(status_code=400, detail="女巫不能毒自己。")


def get_allowed_night_actions(actor: CharacterState) -> set[str]:
    if actor.role == "werewolf":
        return {"werewolf_kill", "none"}
    if actor.role == "seer":
        return {"seer_check", "none"}
    if actor.role == "witch":
        return {"witch_save", "witch_poison", "none"}
    if actor.role == "guard":
        return {"guard_protect", "none"}
    return {"none"}


def upsert_night_action(game_state: WolfGameState, new_action: NightActionState) -> None:
    game_state.night_actions = [
        action
        for action in game_state.night_actions
        if not (action.day == new_action.day and action.actor_id == new_action.actor_id)
    ]
    game_state.night_actions.append(new_action)


def ensure_npc_night_actions(game_state: WolfGameState) -> None:
    for actor in game_state.characters:
        if (
            actor.is_player
            or not actor.alive
            or actor.role != "werewolf"
            or has_night_action(game_state, actor.id)
        ):
            continue
        target_id = choose_npc_night_target(game_state, actor, "werewolf_kill")
        upsert_night_action(
            game_state,
            NightActionState(
                day=game_state.day,
                actor_id=actor.id,
                action_type="werewolf_kill",
                target_id=target_id,
            ),
        )

    for actor in game_state.characters:
        if actor.is_player or not actor.alive or actor.role in {"werewolf", "witch"}:
            continue

        if has_night_action(game_state, actor.id):
            continue

        action_type = choose_npc_night_action_type(actor)
        target_id = choose_npc_night_target(game_state, actor, action_type)
        upsert_night_action(
            game_state,
            NightActionState(
                day=game_state.day,
                actor_id=actor.id,
                action_type=action_type,
                target_id=target_id,
            ),
        )

    ensure_npc_witch_actions(game_state)


def ensure_npc_witch_actions(game_state: WolfGameState) -> None:
    attacked_target_id = get_current_wolf_target(game_state)
    for actor in game_state.characters:
        if (
            actor.is_player
            or not actor.alive
            or actor.role != "witch"
            or has_night_action(game_state, actor.id)
        ):
            continue
        action_type, target_id = choose_npc_witch_action(
            game_state,
            actor,
            attacked_target_id,
        )
        upsert_night_action(
            game_state,
            NightActionState(
                day=game_state.day,
                actor_id=actor.id,
                action_type=action_type,
                target_id=target_id,
            ),
        )


def refresh_npc_witch_action(game_state: WolfGameState) -> None:
    npc_witch_ids = {
        character.id
        for character in game_state.characters
        if not character.is_player and character.alive and character.role == "witch"
    }
    game_state.night_actions = [
        action
        for action in game_state.night_actions
        if not (action.day == game_state.day and action.actor_id in npc_witch_ids)
    ]
    ensure_npc_witch_actions(game_state)


def has_night_action(game_state: WolfGameState, actor_id: int) -> bool:
    return any(
        action.day == game_state.day and action.actor_id == actor_id
        for action in game_state.night_actions
    )


def choose_npc_night_action_type(actor: CharacterState) -> str:
    if actor.role == "werewolf":
        return "werewolf_kill"
    if actor.role == "seer":
        return "seer_check"
    if actor.role == "guard":
        return "guard_protect"
    return "none"


def choose_npc_night_target(
    game_state: WolfGameState,
    actor: CharacterState,
    action_type: str,
) -> Optional[int]:
    if action_type == "none":
        return None

    candidates = [
        character
        for character in game_state.characters
        if character.alive and character.id != actor.id
    ]
    if action_type == "werewolf_kill":
        candidates = [
            character
            for character in candidates
            if character.role != "werewolf"
        ]

    if not candidates:
        return None
    return random.choice(candidates).id


def choose_npc_witch_action(
    game_state: WolfGameState,
    witch: CharacterState,
    attacked_target_id: Optional[int],
) -> tuple[str, Optional[int]]:
    resources = get_role_resources(game_state, witch.id)
    if attacked_target_id is not None and bool(resources.get("antidote_available", False)):
        attacked_target = get_character(game_state, attacked_target_id)
        relationship = witch.relationships.get(str(attacked_target.id), {})
        trust = float(relationship.get("trust", 0.5))
        suspicion = witch.suspicion.get(str(attacked_target.id), 0)
        can_self_save = attacked_target.id != witch.id or game_state.day == 1
        save_threshold = 0.42 + witch.personality.get("empathy", 0.5) * 0.2
        if can_self_save and (attacked_target.id == witch.id or (trust >= save_threshold and suspicion < 45)):
            return "witch_save", attacked_target.id

    if bool(resources.get("poison_available", False)):
        candidates = [
            character
            for character in game_state.characters
            if character.alive and character.id != witch.id
        ]
        if candidates:
            target = max(
                candidates,
                key=lambda character: witch.suspicion.get(str(character.id), 0),
            )
            if witch.suspicion.get(str(target.id), 0) >= 65:
                return "witch_poison", target.id

    return "none", None


def choose_wolf_kill_target(
    game_state: WolfGameState,
    night_actions: list[NightActionState],
) -> Optional[int]:
    player = get_character(game_state, game_state.player_character_id)
    if player.alive and player.role == "werewolf":
        player_action = next(
            (
                action
                for action in night_actions
                if action.day == game_state.day
                and action.actor_id == player.id
                and action.action_type == "werewolf_kill"
                and action.target_id is not None
            ),
            None,
        )
        if player_action is not None:
            return player_action.target_id

    wolf_targets = [
        action.target_id
        for action in night_actions
        if action.day == game_state.day
        and action.action_type == "werewolf_kill"
        and action.target_id is not None
    ]
    if not wolf_targets:
        return None

    target_counts = {
        target_id: wolf_targets.count(target_id)
        for target_id in set(wolf_targets)
    }
    highest_count = max(target_counts.values())
    tied_targets = [
        target_id
        for target_id, count in target_counts.items()
        if count == highest_count
    ]
    return random.choice(tied_targets)


def get_current_wolf_target(game_state: WolfGameState) -> Optional[int]:
    night_actions = [
        action
        for action in game_state.night_actions
        if action.day == game_state.day
    ]
    return choose_wolf_kill_target(game_state, night_actions)


def build_player_private_night_result(
    game_state: WolfGameState,
    night_actions: list[NightActionState],
) -> dict[str, object]:
    player_id = game_state.player_character_id
    result: dict[str, object] = {}
    for action in night_actions:
        if action.actor_id != player_id:
            continue
        if action.action_type == "seer_check" and action.target_id is not None:
            target = get_character(game_state, action.target_id)
            result["seer_check"] = {
                "target_id": target.id,
                "result": "werewolf" if target.role == "werewolf" else "good",
            }
        elif action.action_type in {"witch_save", "witch_poison"}:
            result["witch_action"] = {
                "action_type": action.action_type,
                "target_id": action.target_id,
            }
        elif action.action_type == "werewolf_kill":
            result["wolf_kill_target_id"] = action.target_id

    return result


def apply_night_role_results(
    game_state: WolfGameState,
    night_actions: list[NightActionState],
    killed_target: Optional[int],
    protected_ids: set[int],
    saved_target_id: Optional[int],
) -> None:
    for action in night_actions:
        actor = get_character(game_state, action.actor_id)
        if action.action_type == "seer_check" and action.target_id is not None:
            target = get_character(game_state, action.target_id)
            result = "狼人" if target.role == "werewolf" else "好人"
            append_character_memory(actor, f"第 {game_state.day} 夜查验 {target.name}：{result}。")
            if not actor.is_player:
                if target.role == "werewolf":
                    actor.suspicion[str(target.id)] = 100
                    adjust_relationship_trust(actor, target.id, -0.25, "预言家查验为狼人")
                else:
                    adjust_suspicion(actor, target.id, -20)
                    adjust_relationship_trust(actor, target.id, 0.12, "预言家查验为好人")
            continue

        if action.action_type == "guard_protect" and action.target_id is not None:
            target = get_character(game_state, action.target_id)
            if (
                killed_target == target.id
                and target.id in protected_ids
                and saved_target_id != target.id
            ):
                append_character_memory(actor, f"第 {game_state.day} 夜守护 {target.name}，成功挡下狼刀。")
            elif killed_target == target.id and saved_target_id == target.id:
                append_character_memory(actor, f"第 {game_state.day} 夜守护 {target.name}，但同守同救导致保护失效。")
            else:
                append_character_memory(actor, f"第 {game_state.day} 夜守护 {target.name}。")
            continue

        if action.action_type == "witch_save" and action.target_id is not None:
            target = get_character(game_state, action.target_id)
            if target.id in protected_ids:
                append_character_memory(actor, f"第 {game_state.day} 夜对 {target.name} 使用解药，但同守同救导致保护失效。")
            else:
                append_character_memory(actor, f"第 {game_state.day} 夜对 {target.name} 使用解药并成功救下。")
            continue

        if action.action_type == "witch_poison" and action.target_id is not None:
            target = get_character(game_state, action.target_id)
            append_character_memory(actor, f"第 {game_state.day} 夜对 {target.name} 使用毒药。")


def build_night_public_message(game_state: WolfGameState, dead_characters: list[int]) -> str:
    if not dead_characters:
        return f"第 {game_state.day} 夜结束，昨晚是平安夜。"

    names = [
        get_character(game_state, character_id).name
        for character_id in dead_characters
    ]
    return f"第 {game_state.day} 夜结束，昨晚 " + "、".join(names) + " 出局了。"


def ensure_day_speech_phase(game_state: WolfGameState) -> None:
    if game_state.phase != "DAY_MEETING":
        raise HTTPException(
            status_code=400,
            detail=f"当前阶段是 {game_state.phase}，只能在小镇会议阶段发言。",
        )


def start_day_meeting(game_state: WolfGameState) -> None:
    seat_ids = [character.id for character in game_state.characters]
    alive_ids = [character.id for character in game_state.characters if character.alive]
    first_speaker_id = random.choice(alive_ids)
    direction = random.choice(["clockwise", "counterclockwise"])
    step = 1 if direction == "clockwise" else -1
    first_index = seat_ids.index(first_speaker_id)
    order = []

    for offset in range(len(seat_ids)):
        character_id = seat_ids[(first_index + step * offset) % len(seat_ids)]
        if character_id in alive_ids:
            order.append(character_id)

    game_state.meeting = DayMeetingState(
        day=game_state.day,
        direction=direction,
        order=order,
        order_source="random",
    )
    game_state.phase = "DAY_MEETING"
    first_speaker = get_character(game_state, first_speaker_id)
    direction_label = "顺时针" if direction == "clockwise" else "逆时针"
    game_state.public_logs.append(
        f"第 {game_state.day} 天小镇会议开始，本轮从{first_speaker.id}号"
        f"{first_speaker.name}起按{direction_label}发言。"
    )


def build_day_meeting_view(game_state: WolfGameState) -> DayMeetingView:
    meeting = game_state.meeting
    if meeting is None:
        return DayMeetingView(active=False)

    return DayMeetingView(
        active=game_state.phase == "DAY_MEETING" and not meeting.completed,
        direction=meeting.direction,
        order=list(meeting.order),
        current_speaker_id=get_current_meeting_speaker_id(game_state),
        current_position=min(meeting.current_index + 1, len(meeting.order)),
        total_speakers=len(meeting.order),
        completed=meeting.completed,
        order_source=meeting.order_source,
        anchor_character_id=meeting.anchor_character_id,
        sheriff_id=meeting.sheriff_id,
        temporary_nomination_target_id=meeting.temporary_nomination_target_id,
        nomination_target_id=meeting.nomination_target_id,
    )


def get_current_meeting_speaker_id(game_state: WolfGameState) -> Optional[int]:
    meeting = game_state.meeting
    if meeting is None or meeting.completed or meeting.current_index >= len(meeting.order):
        return None
    return meeting.order[meeting.current_index]


def ensure_current_meeting_speaker(game_state: WolfGameState, character_id: int) -> None:
    current_speaker_id = get_current_meeting_speaker_id(game_state)
    if current_speaker_id != character_id:
        if current_speaker_id is None:
            raise HTTPException(status_code=400, detail="小镇会议已经结束。")
        current_speaker = get_character(game_state, current_speaker_id)
        raise HTTPException(
            status_code=400,
            detail=f"当前轮到{current_speaker.id}号{current_speaker.name}发言。",
        )


def advance_day_meeting(game_state: WolfGameState) -> None:
    meeting = game_state.meeting
    if meeting is None:
        raise HTTPException(status_code=400, detail="当前没有进行中的小镇会议。")

    meeting.current_index += 1
    if meeting.current_index >= len(meeting.order):
        meeting.completed = True
        if game_state.sheriff_id is not None:
            sheriff = get_character(game_state, game_state.sheriff_id)
            if sheriff.alive and meeting.nomination_target_id is None:
                if sheriff.is_player:
                    game_state.phase = "SHERIFF_NOMINATION"
                    game_state.public_logs.append("全员发言结束，请玩家警长确认或调整最终归票。")
                    return
                target_id = choose_npc_sheriff_nomination(game_state, sheriff)
                if target_id is not None:
                    set_sheriff_nomination(game_state, sheriff, target_id)
        enter_free_activity(game_state)


def normalize_easter_egg_text(text: str) -> str:
    return re.sub(r"[\W_]+", "", text, flags=re.UNICODE).casefold()


def find_triggered_easter_egg(
    npc: CharacterState,
    question: str,
) -> Optional[TriggerEasterEgg]:
    profile = NPC_PROFILES.get(npc.name)
    if profile is None:
        return None
    normalized_question = normalize_easter_egg_text(question)
    for easter_egg in profile.trigger_easter_eggs:
        for trigger in easter_egg.triggers:
            normalized_trigger = normalize_easter_egg_text(trigger)
            if normalized_trigger and normalized_trigger in normalized_question:
                return easter_egg
    return None


def has_triggered_easter_egg(
    game_state: WolfGameState,
    npc_character_id: int,
    easter_egg_id: str,
) -> bool:
    return any(
        conversation.npc_character_id == npc_character_id
        and conversation.easter_egg_id == easter_egg_id
        for conversation in game_state.private_conversations
    )


def build_triggered_easter_egg_reply(
    npc: CharacterState,
    easter_egg: TriggerEasterEgg,
    first_time: bool,
) -> str:
    template = easter_egg.reply if first_time else easter_egg.repeat_reply
    return template.replace("{role}", ROLE_LABELS.get(npc.role, npc.role))


def has_effective_private_question(game_state: WolfGameState, npc_character_id: int) -> bool:
    return any(
        conversation.day == game_state.day
        and conversation.npc_character_id == npc_character_id
        and conversation.effective
        for conversation in game_state.private_conversations
    )


def parse_private_question(
    game_state: WolfGameState,
    npc: CharacterState,
    question: str,
) -> tuple[ParsedPlayerSpeech, bool]:
    parsed = parse_player_speech(game_state, question)
    mentioned_ids = list(parsed.mentioned_characters)
    accusation_ids = {
        int(accusation["target_id"])
        for accusation in parsed.accusations
        if "target_id" in accusation
    }
    player_id = game_state.player_character_id

    if "你" in question and npc.id not in mentioned_ids:
        mentioned_ids.append(npc.id)
    if any(keyword in question for keyword in ["我", "自己"]) and player_id not in mentioned_ids:
        mentioned_ids.append(player_id)

    direct_npc_accusation = any(
        keyword in question
        for keyword in ["怀疑你", "你可疑", "你是狼", "你在骗", "你撒谎", "不信你"]
    )
    if direct_npc_accusation:
        accusation_ids.add(npc.id)

    third_party_ids = [
        character_id
        for character_id in parsed.mentioned_characters
        if character_id not in {player_id, npc.id}
    ]
    normalized_question = question.replace("其他", "")
    has_third_person_pronoun = bool(
        re.search(r"[他她]", normalized_question)
        or re.search(r"(?i)(?<![a-z])ta(?![a-z])", normalized_question)
    )
    unresolved_reference = False
    if has_third_person_pronoun and not third_party_ids:
        previous_target_id = get_previous_private_third_party_id(game_state, npc.id)
        if previous_target_id is None:
            unresolved_reference = True
        else:
            third_party_ids.append(previous_target_id)
            if previous_target_id not in mentioned_ids:
                mentioned_ids.append(previous_target_id)
            if private_pronoun_is_accusation(normalized_question):
                accusation_ids.add(previous_target_id)

    accusations = list(parsed.accusations)
    existing_accusation_ids = {
        int(accusation["target_id"])
        for accusation in accusations
        if "target_id" in accusation
    }
    for target_id in accusation_ids - existing_accusation_ids:
        if target_id == player_id:
            continue
        accusations.append(
            {
                "target_id": target_id,
                "reason": "玩家私聊中直接表达怀疑。",
                "intensity": 0.7,
            }
        )

    tone = "suspicious" if accusations else parsed.tone
    return (
        ParsedPlayerSpeech(
            mentioned_characters=mentioned_ids,
            accusations=accusations,
            claims=parsed.claims,
            tone=tone,
        ),
        unresolved_reference,
    )


def get_previous_private_third_party_id(
    game_state: WolfGameState,
    npc_character_id: int,
) -> Optional[int]:
    for conversation in reversed(game_state.private_conversations):
        if conversation.day != game_state.day or conversation.npc_character_id != npc_character_id:
            continue
        parsed = parse_player_speech(
            game_state,
            conversation.question + "\n" + conversation.reply,
        )
        for character_id in parsed.mentioned_characters:
            if character_id not in {game_state.player_character_id, npc_character_id}:
                return character_id
    return None


def private_pronoun_is_accusation(question: str) -> bool:
    return bool(
        re.search(r"(?:我)?(?:有点|比较|很|最)?怀疑[他她]", question)
        or re.search(r"[他她](?:很|最|比较)?可疑", question)
        or re.search(r"[他她](?:可能|就是|是)?狼", question)
        or re.search(r"(?i)(?:怀疑|可疑|是狼).{0,3}ta", question)
    )


def apply_private_question_effect(
    game_state: WolfGameState,
    npc: CharacterState,
    question: str,
    parsed: ParsedPlayerSpeech,
) -> None:
    accused_ids = {
        int(accusation["target_id"])
        for accusation in parsed.accusations
        if "target_id" in accusation
    }
    for target_id in parsed.mentioned_characters:
        if target_id in {npc.id, game_state.player_character_id}:
            continue
        target = get_character(game_state, target_id)
        if not target.alive:
            continue

        increment = 14 if target_id in accused_ids else 5
        if npc.role == "werewolf" and target.role == "werewolf":
            increment = 0
        adjust_suspicion(npc, target_id, increment)

    directly_accused_npc = npc.id in accused_ids
    if directly_accused_npc:
        adjust_suspicion(npc, game_state.player_character_id, 14)
        adjust_relationship_trust(npc, game_state.player_character_id, -0.1, "玩家私下直接怀疑我")

    hostile_keywords = ["你是狼", "你在骗", "你撒谎", "怀疑你", "你可疑", "不信你"]
    cooperative_keywords = ["相信你", "信任你", "合作", "一起"]
    if not directly_accused_npc and any(keyword in question for keyword in hostile_keywords):
        adjust_suspicion(npc, game_state.player_character_id, 10)
        adjust_relationship_trust(npc, game_state.player_character_id, -0.08, "玩家私下质疑我")
    elif any(keyword in question for keyword in cooperative_keywords):
        adjust_relationship_trust(npc, game_state.player_character_id, 0.06, "玩家私下表达合作")
    else:
        adjust_relationship_trust(npc, game_state.player_character_id, 0.02, "玩家私下交换信息")

    append_character_memory(npc, f"第 {game_state.day} 天玩家私下问我：{question}")


def build_private_chat_reply(
    game_state: WolfGameState,
    npc: CharacterState,
    question: str,
    effective: bool,
    rag_context: list[dict[str, object]],
    parsed: ParsedPlayerSpeech,
) -> str:
    prefix = "我会把你的看法记下来。" if effective else "我今天已经考虑过你的意见，核心判断暂时不会再改变。"
    accused_ids = {
        int(accusation["target_id"])
        for accusation in parsed.accusations
        if "target_id" in accusation
    }
    if npc.id in accused_ids:
        prefix += "你直接怀疑我，这会降低我对你的信任。"

    def finalize(text: str) -> str:
        reply = append_safe_rag_context(text, question, rag_context, game_state, npc)
        return render_private_perspective_text(game_state, npc, reply)

    mentioned_targets = [
        get_character(game_state, character_id)
        for character_id in parsed.mentioned_characters
        if character_id not in {npc.id, game_state.player_character_id}
        and get_character(game_state, character_id).alive
    ]
    focus = mentioned_targets[0] if mentioned_targets else choose_rag_focus_target(game_state, npc, rag_context)
    if focus is None:
        focus = choose_speech_focus_target(game_state, npc)

    if npc.role == "werewolf":
        non_wolf_targets = [
            character
            for character in game_state.characters
            if character.alive and character.id != npc.id and character.role != "werewolf"
        ]
        if non_wolf_targets:
            focus = max(
                non_wolf_targets,
                key=lambda character: npc.suspicion.get(str(character.id), 0),
            )
        if focus is None:
            return finalize(prefix + "现在还没有值得公开追打的目标。")
        return finalize(
            prefix
            + f"我更希望你观察{private_character_reference(game_state, npc, focus)}，"
            + f"{private_character_possessive_reference(game_state, npc, focus)}发言还有解释空间。"
        )

    trust_to_player = get_trust_to_player(game_state, npc) or 0.5
    if npc.role == "seer":
        latest_check = get_latest_seer_check(game_state, npc.id)
        disclosure_threshold = 0.62 + npc.personality.get("cautiousness", 0.5) * 0.12
        if latest_check is not None and trust_to_player >= disclosure_threshold:
            target = get_character(game_state, int(latest_check["target_id"]))
            result = "狼人" if latest_check["result"] == "werewolf" else "好人"
            return finalize(
                prefix
                + f"我愿意私下告诉你：我查验过{private_character_reference(game_state, npc, target)}，"
                + f"结果是{result}。先不要急着公开。"
            )
        return finalize(
            prefix + "我手里可能有比公开发言更多的信息，但现在还不准备把身份和结果说透。"
        )

    if npc.role == "guard":
        if focus is None:
            return finalize(prefix + "我会继续观察大家的行动，但不会透露守护目标。")
        return finalize(
            prefix
            + f"我会留意{private_character_reference(game_state, npc, focus)}接下来的选择，"
            + "但守护信息现在不能公开。"
        )

    if npc.role == "witch":
        resources = get_role_resources(game_state, npc.id)
        medicine_state = (
            "我仍然保留着关键手段"
            if bool(resources.get("antidote_available", False))
            or bool(resources.get("poison_available", False))
            else "我的关键手段已经用完"
        )
        return finalize(prefix + medicine_state + "，但现在不会公开具体使用情况。")

    if npc.role == "hunter":
        if focus is None:
            return finalize(prefix + "如果我必须为判断负责，我会根据目前最可信的线索行动。")
        return finalize(
            prefix
            + f"如果局势突然变化，我会优先重新判断{private_character_reference(game_state, npc, focus)}。"
        )

    if focus is None:
        return finalize(prefix + "目前没有足够线索，我更想先看投票。")
    suspicion = npc.suspicion.get(str(focus.id), 0)
    if suspicion >= 18:
        return finalize(
            prefix
            + f"我目前确实比较怀疑{private_character_reference(game_state, npc, focus)}，"
            + f"投票前会重点看{private_character_possessive_reference(game_state, npc, focus)}解释。"
        )
    return finalize(
        prefix
        + f"我会观察{private_character_reference(game_state, npc, focus)}，"
        + f"但现阶段还不能确定{private_character_possessive_reference(game_state, npc, focus)}身份。"
    )


def build_private_rag_context(
    game_state: WolfGameState,
    npc: CharacterState,
    question: str,
) -> list[dict[str, object]]:
    contexts = [
        {
            "kind": "knowledge",
            "title": result.item.title,
            "content": result.item.content,
            "score": float(result.score),
            "safe_to_show": True,
        }
        for result in find_scored_knowledge(npc.name, question, limit=2)
    ]

    dynamic_items: list[dict[str, object]] = []
    for index, log in enumerate(game_state.public_logs[-8:], start=1):
        dynamic_items.append(
            {
                "kind": "public",
                "title": f"公开记录 {index}",
                "content": log,
                "safe_to_show": True,
            }
        )
    for index, memory in enumerate(
        [line for line in npc.memory_summary.split("\n") if line.strip()][-8:],
        start=1,
    ):
        dynamic_items.append(
            {
                "kind": "private",
                "title": f"{npc.name}私有记忆 {index}",
                "content": memory,
                "safe_to_show": False,
            }
        )

    dynamic_texts = [str(item["content"]) for item in dynamic_items]
    vector_scores = HYBRID_INDEX.rank_texts(question, dynamic_texts)
    for index, item in enumerate(dynamic_items):
        vector_score = max(0.0, vector_scores.get(index, 0.0))
        overlap_score = score_text_overlap(question, str(item["content"]))
        if vector_score < 0.30 and overlap_score <= 0:
            continue
        item["score"] = round(vector_score * 100 + overlap_score * 8, 2)
        contexts.append(item)

    contexts.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
    return contexts[:5]


def score_text_overlap(query: str, text: str) -> int:
    query_lower = query.lower()
    text_lower = text.lower()
    terms = {
        term
        for term in re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]{2,}", query_lower)
        if len(term) >= 2
    }
    character_pairs = {
        query_lower[index:index + 2]
        for index in range(max(0, len(query_lower) - 1))
        if "\u4e00" <= query_lower[index] <= "\u9fff"
    }
    return sum(2 for term in terms if term in text_lower) + sum(
        1 for pair in character_pairs if pair in text_lower
    )


def choose_rag_focus_target(
    game_state: WolfGameState,
    npc: CharacterState,
    rag_context: list[dict[str, object]],
) -> Optional[CharacterState]:
    for context in rag_context:
        if context.get("kind") not in {"public", "private"}:
            continue
        parsed = parse_player_speech(game_state, str(context.get("content", "")))
        for character_id in parsed.mentioned_characters:
            if character_id == npc.id:
                continue
            target = get_character(game_state, character_id)
            if target.alive:
                return target
    return None


def get_safe_rag_titles(rag_context: list[dict[str, object]]) -> list[str]:
    return [
        str(context["title"])
        for context in rag_context
        if bool(context.get("safe_to_show", False))
    ][:3]


def append_safe_rag_context(
    reply: str,
    question: str,
    rag_context: list[dict[str, object]],
    game_state: WolfGameState,
    npc: CharacterState,
) -> str:
    rule_context = next(
        (context for context in rag_context if context.get("kind") == "knowledge"),
        None,
    )
    if rule_context is not None and any(
        keyword in question for keyword in ["规则", "身份", "技能", "怎么", "为什么", "胜利", "投票"]
    ):
        return reply + f" 相关规则：{rule_context['content']}"

    public_context = next(
        (context for context in rag_context if context.get("kind") == "public"),
        None,
    )
    if public_context is not None and any(
        keyword in question for keyword in ["刚才", "会议", "发言", "昨晚", "公开"]
    ):
        public_text = render_private_perspective_text(
            game_state,
            npc,
            str(public_context["content"]),
        )
        return reply + f" 结合公开记录：{public_text}"
    return reply


def private_character_reference(
    game_state: WolfGameState,
    npc: CharacterState,
    character: CharacterState,
) -> str:
    if character.id == game_state.player_character_id:
        return "你"
    if character.id == npc.id:
        return "我"
    return format_full_character_name(character)


def private_character_possessive_reference(
    game_state: WolfGameState,
    npc: CharacterState,
    character: CharacterState,
) -> str:
    if character.id == game_state.player_character_id:
        return "你的"
    if character.id == npc.id:
        return "我的"
    return format_full_character_name(character) + "的"


def render_private_perspective_text(
    game_state: WolfGameState,
    npc: CharacterState,
    text: str,
) -> str:
    player = get_character(game_state, game_state.player_character_id)
    rendered = text

    for character, replacement in [(player, "你"), (npc, "我")]:
        rendered = rendered.replace(f"{character.id}号 {character.name}", replacement)
        rendered = rendered.replace(f"{character.id}号{character.name}", replacement)
        rendered = rendered.replace(character.name, replacement)

    for character in game_state.characters:
        if character.id in {player.id, npc.id}:
            continue
        full_name = format_full_character_name(character)
        rendered = re.sub(
            rf"(?<!\d号 )(?<!\d号){re.escape(character.name)}",
            full_name,
            rendered,
        )
    return rendered


def get_latest_seer_check(
    game_state: WolfGameState,
    seer_character_id: int,
) -> Optional[dict[str, object]]:
    for action in reversed(game_state.night_actions):
        if (
            action.actor_id == seer_character_id
            and action.action_type == "seer_check"
            and action.target_id is not None
        ):
            target = get_character(game_state, action.target_id)
            return {
                "target_id": target.id,
                "result": "werewolf" if target.role == "werewolf" else "good",
            }
    return None


def choose_designated_fake_seer(characters: list[CharacterState]) -> Optional[int]:
    npc_wolves = [
        character
        for character in characters
        if not character.is_player and character.role == "werewolf"
    ]
    if not npc_wolves:
        return None
    return max(
        npc_wolves,
        key=lambda character: (
            character.personality.get("deception", 0.5)
            + character.personality.get("leadership", 0.5)
            + character.personality.get("logic", 0.5) * 0.5
        ),
    ).id


def get_public_role_claim(
    game_state: WolfGameState,
    character_id: int,
) -> Optional[PublicClaimState]:
    return next(
        (
            claim
            for claim in reversed(game_state.public_claims)
            if claim.character_id == character_id and claim.claim_type == "role"
        ),
        None,
    )


def get_public_role_claimants(
    game_state: WolfGameState,
    claimed_role: str,
) -> list[int]:
    return sorted(
        {
            claim.character_id
            for claim in game_state.public_claims
            if claim.claim_type == "role" and claim.claimed_role == claimed_role
        }
    )


def has_matching_public_claim(
    game_state: WolfGameState,
    character_id: int,
    claim_type: str,
    target_id: Optional[int] = None,
    day: Optional[int] = None,
) -> bool:
    return any(
        claim.character_id == character_id
        and claim.claim_type == claim_type
        and (target_id is None or claim.target_id == target_id)
        and (day is None or claim.day == day)
        for claim in game_state.public_claims
    )


def register_public_claims(
    game_state: WolfGameState,
    claims: list[PublicClaimState],
) -> list[PublicClaimState]:
    added_claims = []
    for claim in claims:
        duplicate = any(
            existing.day == claim.day
            and existing.character_id == claim.character_id
            and existing.claim_type == claim.claim_type
            and existing.claimed_role == claim.claimed_role
            and existing.target_id == claim.target_id
            and existing.result == claim.result
            for existing in game_state.public_claims
        )
        if duplicate:
            continue
        game_state.public_claims.append(claim)
        apply_public_claim_updates(game_state, claim)
        added_claims.append(claim)
    return added_claims


def apply_public_claim_updates(
    game_state: WolfGameState,
    claim: PublicClaimState,
) -> None:
    claimant = get_character(game_state, claim.character_id)
    target = (
        get_character(game_state, claim.target_id)
        if claim.target_id is not None
        else None
    )
    for listener in game_state.characters:
        if listener.is_player or not listener.alive or listener.id == claimant.id:
            continue

        if claim.claim_type == "role" and claim.claimed_role:
            competing_ids = [
                character_id
                for character_id in get_public_role_claimants(game_state, claim.claimed_role)
                if character_id != claimant.id
            ]
            if listener.role == claim.claimed_role:
                adjust_suspicion(listener, claimant.id, 36)
                continue
            if listener.role == "werewolf":
                if claimant.role == "werewolf":
                    adjust_relationship_trust(listener, claimant.id, 0.06, "狼队公开身份策略")
                else:
                    adjust_suspicion(listener, claimant.id, 18)
                continue
            if competing_ids:
                claimant_trust = float(
                    listener.relationships.get(str(claimant.id), {}).get("trust", 0.5)
                )
                strongest_competitor = max(
                    competing_ids,
                    key=lambda character_id: float(
                        listener.relationships.get(str(character_id), {}).get("trust", 0.5)
                    ),
                )
                competitor_trust = float(
                    listener.relationships.get(str(strongest_competitor), {}).get("trust", 0.5)
                )
                if claimant_trust < competitor_trust:
                    adjust_suspicion(listener, claimant.id, 10)
                else:
                    adjust_suspicion(listener, strongest_competitor, 7)
            continue

        if claim.claim_type != "seer_check" or target is None:
            continue

        if listener.role == "seer":
            own_check = next(
                (
                    action
                    for action in reversed(game_state.night_actions)
                    if action.actor_id == listener.id
                    and action.action_type == "seer_check"
                    and action.target_id == target.id
                ),
                None,
            )
            if own_check is not None:
                actual_result = "werewolf" if target.role == "werewolf" else "good"
                if actual_result != claim.result:
                    adjust_suspicion(listener, claimant.id, 45)
                    continue

        if listener.role == "werewolf":
            if claimant.role == "werewolf":
                continue
            if target.role == "werewolf" and claim.result == "werewolf":
                adjust_suspicion(listener, claimant.id, 28)
            continue

        trust = float(listener.relationships.get(str(claimant.id), {}).get("trust", 0.5))
        influence = max(8, int(8 + trust * 20))
        if claim.result == "werewolf":
            adjust_suspicion(listener, target.id, influence)
        elif claim.result == "good":
            adjust_suspicion(listener, target.id, -max(6, influence // 2))


def build_public_claim_label(
    game_state: WolfGameState,
    claim: PublicClaimState,
) -> str:
    if claim.claim_type == "role" and claim.claimed_role:
        return "自称" + ROLE_LABELS.get(claim.claimed_role, claim.claimed_role)
    target = (
        get_character(game_state, claim.target_id)
        if claim.target_id is not None
        else None
    )
    target_label = format_full_character_name(target) if target is not None else "未知目标"
    if claim.claim_type == "seer_check":
        result = "狼人" if claim.result == "werewolf" else "好人"
        return f"称验{target_label}为{result}"
    if claim.claim_type == "witch_save":
        return f"称对{target_label}用过解药"
    if claim.claim_type == "witch_poison":
        return f"称对{target_label}用过毒药"
    if claim.claim_type == "guard_success":
        return f"称守护{target_label}成功"
    return "公开了身份信息"


def get_character_public_claim_labels(
    game_state: WolfGameState,
    character_id: int,
    limit: int = 3,
) -> list[str]:
    labels = []
    for claim in game_state.public_claims:
        if claim.character_id != character_id:
            continue
        label = build_public_claim_label(game_state, claim)
        if label not in labels:
            labels.append(label)
    return labels[-limit:]


def parsed_claims_to_public_claims(
    game_state: WolfGameState,
    character_id: int,
    parsed_claims: list[dict[str, object]],
) -> list[PublicClaimState]:
    claims = []
    for parsed_claim in parsed_claims:
        claims.append(
            PublicClaimState(
                day=game_state.day,
                character_id=character_id,
                claim_type=str(parsed_claim.get("claim_type", "role")),
                claimed_role=(
                    str(parsed_claim.get("claimed_role"))
                    if parsed_claim.get("claimed_role")
                    else None
                ),
                target_id=(
                    int(parsed_claim["target_id"])
                    if parsed_claim.get("target_id") is not None
                    else None
                ),
                result=str(parsed_claim.get("result", "")),
                source="player_speech",
            )
        )
    return claims


def parse_player_speech(game_state: WolfGameState, speech: str) -> ParsedPlayerSpeech:
    mentioned_ids = []
    for character in game_state.characters:
        id_pattern = rf"{character.id}\s*号"
        if re.search(id_pattern, speech) or character.name in speech:
            mentioned_ids.append(character.id)

    accusation_keywords = ["狼", "可疑", "奇怪", "跟票", "带节奏", "怀疑", "不解释", "冲票", "防御"]
    role_claim_phrases = {
        "werewolf": ["我是狼人"],
        "seer": ["我是预言家", "我跳预言家", "我起跳预言家"],
        "witch": ["我是女巫", "我跳女巫"],
        "hunter": ["我是猎人", "我跳猎人"],
        "guard": ["我是守卫", "我跳守卫"],
        "villager": ["我是村民", "我是好人"],
    }
    has_accusation = any(keyword in speech for keyword in accusation_keywords)
    claims = []
    for role, phrases in role_claim_phrases.items():
        if any(phrase in speech for phrase in phrases):
            claims.append(
                {
                    "claim": ROLE_LABELS.get(role, role),
                    "claim_type": "role",
                    "claimed_role": role,
                    "source": "player_speech",
                }
            )

    for sentence in re.split(r"[。！？!?；;\n]", speech):
        if not any(keyword in sentence for keyword in ["查验", "验了", "验过", "验人", "查杀", "金水"]):
            continue
        for character in game_state.characters:
            if character.id == game_state.player_character_id:
                continue
            if not (re.search(rf"{character.id}\s*号", sentence) or character.name in sentence):
                continue
            result = ""
            if any(keyword in sentence for keyword in ["金水", "好人", "不是狼"]):
                result = "good"
            elif any(keyword in sentence for keyword in ["查杀", "是狼", "狼人"]):
                result = "werewolf"
            if result:
                claims.append(
                    {
                        "claim": "查验结果",
                        "claim_type": "seer_check",
                        "claimed_role": "seer",
                        "target_id": character.id,
                        "result": result,
                        "source": "player_speech",
                    }
                )

    accusations = []
    if has_accusation:
        for character_id in mentioned_ids:
            if character_id == game_state.player_character_id:
                continue
            accusations.append(
                {
                    "target_id": character_id,
                    "reason": "玩家发言中出现怀疑或攻击性关键词。",
                    "intensity": 0.7,
                }
            )

    tone = "suspicious" if has_accusation else "claiming" if claims else "neutral"
    return ParsedPlayerSpeech(
        mentioned_characters=mentioned_ids,
        accusations=accusations,
        claims=claims,
        tone=tone,
    )


def apply_player_speech_updates(game_state: WolfGameState, parsed: ParsedPlayerSpeech) -> None:
    if not parsed.mentioned_characters:
        return

    accused_ids = {
        int(accusation["target_id"])
        for accusation in parsed.accusations
        if "target_id" in accusation
    }
    for npc in game_state.characters:
        if npc.is_player or not npc.alive:
            continue

        for target_id in parsed.mentioned_characters:
            if target_id == npc.id:
                continue

            target = get_character(game_state, target_id)
            if not target.alive:
                continue

            increment = 18 if target_id in accused_ids else 6
            if npc.role == "werewolf" and target.role == "werewolf":
                increment = 0
            npc.suspicion[str(target_id)] = npc.suspicion.get(str(target_id), 0) + increment


def apply_npc_speech_updates(
    game_state: WolfGameState,
    speaker: CharacterState,
    parsed: ParsedPlayerSpeech,
) -> None:
    if not parsed.mentioned_characters:
        return

    accused_ids = {
        int(accusation["target_id"])
        for accusation in parsed.accusations
        if "target_id" in accusation
    }
    for listener in game_state.characters:
        if listener.is_player or not listener.alive or listener.id == speaker.id:
            continue

        for target_id in parsed.mentioned_characters:
            if target_id == listener.id:
                continue
            target = get_character(game_state, target_id)
            if not target.alive:
                continue

            increment = 12 if target_id in accused_ids else 4
            if listener.role == "werewolf" and target.role == "werewolf":
                increment = 0
            adjust_suspicion(listener, target_id, increment)


def get_character_seer_checks(
    game_state: WolfGameState,
    character_id: int,
) -> list[tuple[int, int, str]]:
    checks = []
    for action in game_state.night_actions:
        if (
            action.actor_id != character_id
            or action.action_type != "seer_check"
            or action.target_id is None
        ):
            continue
        target = get_character(game_state, action.target_id)
        checks.append(
            (
                action.day,
                target.id,
                "werewolf" if target.role == "werewolf" else "good",
            )
        )
    return checks


def should_true_seer_claim(
    game_state: WolfGameState,
    speaker: CharacterState,
    checks: list[tuple[int, int, str]],
) -> bool:
    if get_public_role_claim(game_state, speaker.id) is not None:
        return True
    competing_claimants = [
        character_id
        for character_id in get_public_role_claimants(game_state, "seer")
        if character_id != speaker.id
    ]
    if competing_claimants or any(result == "werewolf" for _day, _target, result in checks):
        return True
    if get_public_suspicion_score(game_state, speaker.id) >= 50 or game_state.day >= 2:
        return True
    meeting = game_state.meeting
    return bool(
        meeting is not None
        and meeting.current_index >= max(1, len(meeting.order) * 2 // 3)
        and speaker.personality.get("leadership", 0.5) >= 0.65
    )


def should_fake_seer_claim(
    game_state: WolfGameState,
    speaker: CharacterState,
) -> bool:
    if get_public_role_claim(game_state, speaker.id) is not None:
        return True
    if any(
        character_id != speaker.id
        for character_id in get_public_role_claimants(game_state, "seer")
    ):
        return True
    if get_public_suspicion_score(game_state, speaker.id) >= 45 or game_state.day >= 2:
        return True
    meeting = game_state.meeting
    strategy_score = (
        speaker.personality.get("deception", 0.5)
        + speaker.personality.get("leadership", 0.5)
    )
    return bool(
        meeting is not None
        and meeting.current_index >= max(1, len(meeting.order) // 4)
        and strategy_score >= 1.45
    )


def choose_fake_seer_check(
    game_state: WolfGameState,
    speaker: CharacterState,
) -> Optional[tuple[int, str]]:
    already_checked_ids = {
        claim.target_id
        for claim in game_state.public_claims
        if claim.character_id == speaker.id
        and claim.claim_type == "seer_check"
        and claim.target_id is not None
    }
    candidates = [
        character
        for character in game_state.characters
        if character.alive
        and character.id != speaker.id
        and character.id not in already_checked_ids
    ]
    if not candidates:
        return None

    alive_wolves = [
        character
        for character in game_state.characters
        if character.alive and character.role == "werewolf"
    ]
    alive_good_count = sum(
        1
        for character in game_state.characters
        if character.alive and character.role != "werewolf"
    )
    wolf_check_candidates = [
        character
        for character in candidates
        if character.role == "werewolf"
    ]
    if (
        not game_state.wolf_checked_wolf_used
        and len(alive_wolves) >= 3
        and alive_good_count > len(alive_wolves) + 1
        and wolf_check_candidates
    ):
        highest_pressure_teammate = max(
            wolf_check_candidates,
            key=lambda character: get_public_suspicion_score(game_state, character.id),
        )
        teammate_pressure = get_public_suspicion_score(game_state, highest_pressure_teammate.id)
        if teammate_pressure >= 45 or random.random() < 0.12:
            game_state.wolf_checked_wolf_used = True
            return highest_pressure_teammate.id, "werewolf"

    shieldable_teammates = [
        character
        for character in candidates
        if character.role == "werewolf"
        and get_public_suspicion_score(game_state, character.id) < 55
    ]
    if shieldable_teammates and (game_state.day + speaker.id) % 2 == 0:
        target = min(
            shieldable_teammates,
            key=lambda character: get_public_suspicion_score(game_state, character.id),
        )
        return target.id, "good"

    non_wolves = [character for character in candidates if character.role != "werewolf"]
    if non_wolves:
        target = max(
            non_wolves,
            key=lambda character: (
                speaker.suspicion.get(str(character.id), 0),
                get_public_suspicion_score(game_state, character.id),
                -character.id,
            ),
        )
        return target.id, "werewolf"

    target = candidates[0]
    return target.id, "good"


def get_successful_guard_claim_target(
    game_state: WolfGameState,
    guard_id: int,
) -> Optional[tuple[int, int]]:
    for resolution in reversed(game_state.night_resolutions):
        if (
            resolution.attacked_target_id is None
            or resolution.attacked_target_id not in resolution.protected_ids
            or resolution.saved_target_id == resolution.attacked_target_id
        ):
            continue
        action = next(
            (
                action
                for action in game_state.night_actions
                if action.day == resolution.day
                and action.actor_id == guard_id
                and action.action_type == "guard_protect"
                and action.target_id == resolution.attacked_target_id
            ),
            None,
        )
        if action is not None:
            return resolution.day, resolution.attacked_target_id
    return None


def should_reveal_power_role(
    game_state: WolfGameState,
    speaker: CharacterState,
    successful_action: bool = False,
) -> bool:
    score = (
        speaker.personality.get("leadership", 0.5) * 28
        + speaker.personality.get("aggressiveness", 0.5) * 20
        - speaker.personality.get("cautiousness", 0.5) * 12
        + get_public_suspicion_score(game_state, speaker.id) * 0.65
        + (24 if successful_action else 0)
        + (10 if game_state.day >= 2 else 0)
    )
    return score >= 38


def plan_npc_public_claims(
    game_state: WolfGameState,
    speaker: CharacterState,
) -> list[PublicClaimState]:
    claims: list[PublicClaimState] = []

    if speaker.role == "werewolf" and speaker.id == game_state.wolf_fake_seer_id:
        if not should_fake_seer_claim(game_state, speaker):
            return claims
        if get_public_role_claim(game_state, speaker.id) is None:
            claims.append(
                PublicClaimState(
                    day=game_state.day,
                    character_id=speaker.id,
                    claim_type="role",
                    claimed_role="seer",
                    source="wolf_fake_seer",
                )
            )
        if not has_matching_public_claim(
            game_state,
            speaker.id,
            "seer_check",
            day=game_state.day,
        ):
            fake_check = choose_fake_seer_check(game_state, speaker)
            if fake_check is not None:
                target_id, result = fake_check
                claims.append(
                    PublicClaimState(
                        day=game_state.day,
                        character_id=speaker.id,
                        claim_type="seer_check",
                        claimed_role="seer",
                        target_id=target_id,
                        result=result,
                        source="wolf_fake_seer",
                    )
                )
        return claims

    if speaker.role == "seer":
        checks = get_character_seer_checks(game_state, speaker.id)
        if not checks or not should_true_seer_claim(game_state, speaker, checks):
            return claims
        if get_public_role_claim(game_state, speaker.id) is None:
            claims.append(
                PublicClaimState(
                    day=game_state.day,
                    character_id=speaker.id,
                    claim_type="role",
                    claimed_role="seer",
                    source="true_role",
                )
            )
        for check_day, target_id, result in checks:
            if has_matching_public_claim(game_state, speaker.id, "seer_check", target_id):
                continue
            claims.append(
                PublicClaimState(
                    day=game_state.day,
                    character_id=speaker.id,
                    claim_type="seer_check",
                    claimed_role="seer",
                    target_id=target_id,
                    result=result,
                    source=f"night_{check_day}",
                )
            )
        return claims

    if speaker.role == "witch":
        action = next(
            (
                action
                for action in reversed(game_state.night_actions)
                if action.actor_id == speaker.id
                and action.action_type in {"witch_save", "witch_poison"}
                and action.target_id is not None
                and not has_matching_public_claim(
                    game_state,
                    speaker.id,
                    action.action_type,
                    action.target_id,
                )
            ),
            None,
        )
        if action is not None and should_reveal_power_role(game_state, speaker, True):
            if get_public_role_claim(game_state, speaker.id) is None:
                claims.append(
                    PublicClaimState(
                        day=game_state.day,
                        character_id=speaker.id,
                        claim_type="role",
                        claimed_role="witch",
                        source="true_role",
                    )
                )
            claims.append(
                PublicClaimState(
                    day=game_state.day,
                    character_id=speaker.id,
                    claim_type=action.action_type,
                    claimed_role="witch",
                    target_id=action.target_id,
                    source=f"night_{action.day}",
                )
            )
        return claims

    if speaker.role == "guard":
        success = get_successful_guard_claim_target(game_state, speaker.id)
        if success is not None and should_reveal_power_role(game_state, speaker, True):
            success_day, target_id = success
            if not has_matching_public_claim(
                game_state,
                speaker.id,
                "guard_success",
                target_id,
            ):
                if get_public_role_claim(game_state, speaker.id) is None:
                    claims.append(
                        PublicClaimState(
                            day=game_state.day,
                            character_id=speaker.id,
                            claim_type="role",
                            claimed_role="guard",
                            source="true_role",
                        )
                    )
                claims.append(
                    PublicClaimState(
                        day=game_state.day,
                        character_id=speaker.id,
                        claim_type="guard_success",
                        claimed_role="guard",
                        target_id=target_id,
                        source=f"night_{success_day}",
                    )
                )
        return claims

    if (
        speaker.role == "hunter"
        and get_public_role_claim(game_state, speaker.id) is None
        and should_reveal_power_role(game_state, speaker)
    ):
        claims.append(
            PublicClaimState(
                day=game_state.day,
                character_id=speaker.id,
                claim_type="role",
                claimed_role="hunter",
                source="true_role",
            )
        )
    return claims


def get_primary_claim_target(
    game_state: WolfGameState,
    claims: list[PublicClaimState],
) -> Optional[CharacterState]:
    return next(
        (
            get_character(game_state, claim.target_id)
            for claim in claims
            if claim.target_id is not None
        ),
        None,
    )


def build_public_claim_speech(
    game_state: WolfGameState,
    speaker: CharacterState,
    claims: list[PublicClaimState],
) -> str:
    parts = []
    role_claim = next((claim for claim in claims if claim.claim_type == "role"), None)
    prior_role_claim = get_public_role_claim(game_state, speaker.id)
    claimed_role = (
        role_claim.claimed_role
        if role_claim is not None
        else prior_role_claim.claimed_role if prior_role_claim is not None else None
    )
    if role_claim is not None and claimed_role:
        if claimed_role == "seer":
            prefix = "场上已经有人起跳，但我也把话说清楚。" if get_public_role_claimants(game_state, "seer") else "我起跳预言家。"
            parts.append(prefix)
        else:
            parts.append(f"我把身份拍出来，我是{ROLE_LABELS.get(claimed_role, claimed_role)}。")
    elif claimed_role == "seer":
        parts.append("我继续以预言家身份更新验人。")

    for claim in claims:
        if claim.target_id is None:
            continue
        target = get_character(game_state, claim.target_id)
        target_label = format_full_character_name(target)
        if claim.claim_type == "seer_check":
            result = "狼人" if claim.result == "werewolf" else "好人"
            parts.append(f"我的验人是：{target_label}为{result}。")
        elif claim.claim_type == "witch_save":
            parts.append(f"我对{target_label}用过解药，这条夜间信息由我负责。")
        elif claim.claim_type == "witch_poison":
            parts.append(f"我对{target_label}用过毒药，这条行动可以和出局结果核对。")
        elif claim.claim_type == "guard_success":
            parts.append(f"我守护过{target_label}并挡下了狼刀，这个平安夜不是偶然。")
    if role_claim is not None and claimed_role == "hunter":
        parts.append("谁要推动放逐我，也要把我可能开枪的后果算进去。")
    return "".join(parts)


def generate_current_npc_meeting_speech(
    game_state: WolfGameState,
    speaker: CharacterState,
) -> tuple[NpcSpeechItem, NpcMemoryUpdate]:
    existing = next(
        (
            speech
            for speech in game_state.speeches
            if speech.day == game_state.day
            and speech.character_id == speaker.id
            and speech.phase == "DAY_MEETING"
        ),
        None,
    )
    if existing is not None:
        raise HTTPException(status_code=400, detail=f"{speaker.name}今天已经完成正式发言。")

    player_has_spoken = any(
        speech.day == game_state.day and speech.is_player
        for speech in game_state.speeches
    )
    planned_claims = plan_npc_public_claims(game_state, speaker)
    target = get_primary_claim_target(game_state, planned_claims)
    if target is None:
        target = choose_speech_focus_target(game_state, speaker)
    rag_context = build_public_decision_rag_context(
        game_state,
        speaker,
        target,
        "公开发言",
    )
    evidence = choose_public_decision_evidence(rag_context)
    evidence_titles = get_safe_rag_titles(rag_context)
    retrieval_mode = str(HYBRID_INDEX.status()["mode"])
    rule_speech = build_npc_public_speech(
        game_state,
        speaker,
        player_has_spoken,
        target,
        evidence,
        planned_claims,
    )
    rule_speech = apply_npc_voice(game_state, speaker, rule_speech, "meeting")
    llm_result = generate_public_speech_llm_text(
        game_state,
        speaker,
        target,
        rule_speech,
        rag_context,
        planned_claims,
    )
    speech = llm_result.text
    if (
        game_state.meeting is not None
        and game_state.sheriff_id == speaker.id
        and game_state.meeting.temporary_nomination_target_id is not None
    ):
        nomination_target = get_character(game_state, game_state.meeting.temporary_nomination_target_id)
        nomination_sentence = f"我暂时归票给{format_full_character_name(nomination_target)}，听完后面的发言还可以调整。"
        if nomination_target.name not in speech or "暂时归票" not in speech:
            speech = speech.rstrip("。") + "。" + nomination_sentence
    game_state.speeches.append(
        SpeechState(
            day=game_state.day,
            character_id=speaker.id,
            name=speaker.name,
            speech=speech,
            is_player=False,
            evidence_titles=evidence_titles,
            retrieval_mode=retrieval_mode,
            llm_used=llm_result.used_llm,
            llm_provider=llm_result.provider if llm_result.used_llm else "rule",
            llm_fallback_reason=llm_result.fallback_reason,
            llm_validation_failure_id=llm_result.validation_failure_id,
        )
    )
    game_state.public_logs.append(f"{speaker.id}号{speaker.name}：{speech}")
    register_public_claims(game_state, planned_claims)
    memory_content = f"{speaker.id}号在第 {game_state.day} 天公开发言：{speech}"
    append_character_memory(speaker, memory_content)
    parsed = parse_player_speech(game_state, speech)
    apply_npc_speech_updates(game_state, speaker, parsed)

    return (
        NpcSpeechItem(
            character_id=speaker.id,
            name=speaker.name,
            speech=speech,
            evidence_titles=evidence_titles,
            retrieval_mode=retrieval_mode,
            llm_used=llm_result.used_llm,
            llm_provider=llm_result.provider if llm_result.used_llm else "rule",
            llm_fallback_reason=llm_result.fallback_reason,
            llm_validation_failure=build_llm_validation_failure_view(
                game_state,
                llm_result.validation_failure_id,
            ),
        ),
        NpcMemoryUpdate(owner_character_id=speaker.id, content=memory_content),
    )


def build_npc_public_speech(
    game_state: WolfGameState,
    speaker: CharacterState,
    respond_to_player: bool,
    target: Optional[CharacterState],
    evidence: Optional[dict[str, object]],
    planned_claims: Optional[list[PublicClaimState]] = None,
) -> str:
    if planned_claims:
        return append_public_rag_evidence(
            build_public_claim_speech(game_state, speaker, planned_claims),
            evidence,
        )
    if target is None:
        return append_public_rag_evidence(
            "现在信息还不够，我先听听大家怎么说。",
            evidence,
        )

    suspicion_value = speaker.suspicion.get(str(target.id), 0)
    if speaker.role == "werewolf":
        if target.role == "werewolf":
            base_speech = f"{target.name}现在已经成为焦点，我不会无条件替他解释，他需要自己回应矛盾。"
        else:
            base_speech = f"我觉得{target.name}今天的发言有点模糊，可以先让他多解释一下。"
    elif suspicion_value >= 18:
        base_speech = f"我注意到{target.name}被提到得比较多，我也想听听他的解释。"
    elif respond_to_player and suspicion_value > 0:
        base_speech = f"1号玩家刚才提到{target.name}，这个点可以先记下来，但我还不想太快下结论。"
    elif speaker.role == "seer":
        base_speech = f"我会更关注发言逻辑，目前先观察{target.name}的表态。"
    elif speaker.role == "guard":
        base_speech = f"现在先稳一点，我会观察{target.name}和其他人的互动。"
    elif speaker.role == "witch":
        base_speech = f"夜晚信息需要谨慎处理，我先观察{target.name}今天是否能保持前后一致。"
    elif speaker.role == "hunter":
        base_speech = f"我会为自己的判断负责，目前重点看{target.name}接下来如何回应。"
    else:
        base_speech = f"目前线索还少，我先观察{target.name}的发言。"
    return append_public_rag_evidence(base_speech, evidence)


def build_public_decision_rag_context(
    game_state: WolfGameState,
    npc: CharacterState,
    target: Optional[CharacterState],
    decision_kind: str,
) -> list[dict[str, object]]:
    target_text = "暂未确定目标"
    if target is not None:
        target_text = format_full_character_name(target)
    query = f"{npc.name} {decision_kind} {target_text} 公开发言 证据 怀疑 判断"
    contexts = [
        {
            "kind": "knowledge",
            "title": result.item.title,
            "content": result.item.content,
            "score": float(result.score),
            "safe_to_show": True,
        }
        for result in find_scored_knowledge(npc.name, query, limit=2)
    ]

    public_items = []
    for speech in game_state.speeches[-12:]:
        speaker = get_character(game_state, speech.character_id)
        public_items.append(
            {
                "kind": "public",
                "title": f"第 {speech.day} 天 {format_full_character_name(speaker)}的公开发言",
                "content": speech.speech,
                "safe_to_show": True,
            }
        )

    public_texts = [str(item["content"]) for item in public_items]
    vector_scores = HYBRID_INDEX.rank_texts(query, public_texts)
    for index, item in enumerate(public_items):
        content = str(item["content"])
        vector_score = max(0.0, vector_scores.get(index, 0.0))
        overlap_score = score_text_overlap(query, content)
        if vector_score < 0.30 and overlap_score <= 0:
            continue
        item["score"] = round(vector_score * 100 + overlap_score * 8, 2)
        contexts.append(item)

    contexts.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
    return contexts[:5]


def choose_public_decision_evidence(
    rag_context: list[dict[str, object]],
) -> Optional[dict[str, object]]:
    return next(
        (context for context in rag_context if context.get("kind") == "public"),
        rag_context[0] if rag_context else None,
    )


def append_public_rag_evidence(
    text: str,
    evidence: Optional[dict[str, object]],
) -> str:
    if evidence is None:
        return text
    title = str(evidence.get("title", "公开证据"))
    if evidence.get("kind") == "public":
        content = truncate_display_text(str(evidence.get("content", "")), 52)
        return f"参考{title}：“{content}” {text}"
    return f"结合知识“{title}”中的判断原则，{text}"


def get_npc_voice_profile(npc_name: str) -> dict[str, object]:
    profile = NPC_PROFILES.get(npc_name)
    if profile is None:
        return {"speech_style": "", "catchphrases": [], "easter_eggs": []}
    return {
        "speech_style": profile.speech_style,
        "catchphrases": list(profile.catchphrases),
        "easter_eggs": list(profile.easter_eggs),
    }


def apply_npc_voice(
    game_state: WolfGameState,
    npc: CharacterState,
    text: str,
    context_kind: str,
) -> str:
    profile = NPC_PROFILES.get(npc.name)
    if profile is None:
        return text

    used_text = "\n".join(
        [speech.speech for speech in game_state.speeches]
        + [conversation.reply for conversation in game_state.private_conversations]
    )
    catchphrases = [phrase for phrase in profile.catchphrases if phrase not in used_text]
    easter_eggs = [phrase for phrase in profile.easter_eggs if phrase not in used_text]
    event_count = len(game_state.speeches) + len(game_state.private_conversations)
    seed = game_state.day * 31 + npc.id * 17 + event_count * 13
    if context_kind == "private":
        seed += 11
    roll = seed % 100
    catchphrase_limit = 45 if context_kind == "private" else 35
    easter_egg_limit = 65 if context_kind == "private" else 48

    if roll < catchphrase_limit and catchphrases:
        phrase = catchphrases[(seed // 7) % len(catchphrases)]
        return phrase + " " + text
    if roll < easter_egg_limit and easter_eggs:
        phrase = easter_eggs[(seed // 11) % len(easter_eggs)]
        return text + " " + phrase
    return text


def truncate_display_text(text: str, limit: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rstrip() + "..."


def generate_public_speech_llm_text(
    game_state: WolfGameState,
    speaker: CharacterState,
    target: Optional[CharacterState],
    rule_text: str,
    rag_context: list[dict[str, object]],
    required_claims: Optional[list[PublicClaimState]] = None,
) -> LLMGeneration:
    if not game_state.llm_enabled:
        return rule_llm_generation(rule_text, "LLM is disabled for this game")

    context = {
        "task": "rewrite_public_speech",
        "day": game_state.day,
        "speaker": {
            "id": speaker.id,
            "name": speaker.name,
            "personality": speaker.personality,
            "voice_profile": get_npc_voice_profile(speaker.name),
        },
        "focus_target": (
            {"id": target.id, "name": target.name}
            if target is not None
            else None
        ),
        "rule_text": rule_text,
        "public_evidence": build_llm_safe_evidence(rag_context),
        "recent_public_logs": game_state.public_logs[-6:],
    }
    system_prompt = (
        "你是狼人杀 NPC 的表达层。后端已经决定目标和事实，你只能改写措辞。"
        "保持 rule_text 的立场、目标、证据和确定程度，不新增人物、身份结论、查验结果或游戏事实。"
        "公开发言不得泄露隐藏身份或私密信息。使用自然简洁的中文，最多 220 个汉字。"
        "可以自然使用 voice_profile 中的语言习惯，但不要强行重复口头禅或解释彩蛋。"
        "只返回 JSON 对象，格式为 {\"text\": \"发言\"}。"
    )
    return generate_validated_llm_rewrite(
        system_prompt,
        context,
        rule_text,
        game_state,
        speaker=speaker,
        required_target=target,
        required_claims=required_claims,
        public_text=True,
    )


def generate_private_chat_llm_text(
    game_state: WolfGameState,
    npc: CharacterState,
    question: str,
    rule_text: str,
    rag_context: list[dict[str, object]],
    required_self_role: Optional[str] = None,
    easter_egg_id: str = "",
) -> LLMGeneration:
    if not game_state.llm_enabled:
        return rule_llm_generation(rule_text, "LLM is disabled for this game")

    context = {
        "task": "rewrite_private_reply",
        "day": game_state.day,
        "npc": {
            "id": npc.id,
            "name": npc.name,
            "personality": npc.personality,
            "voice_profile": get_npc_voice_profile(npc.name),
            "trust_to_player": get_trust_to_player(game_state, npc),
        },
        "player_question": question,
        "rule_text": rule_text,
        "safe_evidence": build_llm_safe_evidence(rag_context),
        "authorized_easter_egg": easter_egg_id or None,
    }
    system_prompt = (
        "你是狼人杀 NPC 的私聊表达层。rule_text 是后端批准的完整事实边界。"
        "只能让回答更符合人格，不得新增身份、查验、守护、票型或其他事实，也不得改变确定程度。"
        "NPC 用‘我’自称、用‘你’称玩家，第三方保留号码和名字。使用自然简洁中文，最多 240 个汉字。"
        "可以自然使用 voice_profile 中的表达习惯，但不要为了玩梗牺牲回答信息。"
        "只返回 JSON 对象，格式为 {\"text\": \"回答\"}。"
    )
    if required_self_role is not None:
        system_prompt += (
            " 本次 authorized_easter_egg 允许 NPC 私下透露且必须保留自己的真实身份；"
            "只允许透露 validation_contract.required_self_role，不得透露任何其他隐藏身份。"
        )
    return generate_validated_llm_rewrite(
        system_prompt,
        context,
        rule_text,
        game_state,
        speaker=npc,
        required_self_role=required_self_role,
    )


def generate_validated_llm_rewrite(
    system_prompt: str,
    context: dict[str, object],
    rule_text: str,
    game_state: WolfGameState,
    speaker: Optional[CharacterState] = None,
    required_target: Optional[CharacterState] = None,
    required_claims: Optional[list[PublicClaimState]] = None,
    public_text: bool = False,
    required_self_role: Optional[str] = None,
) -> LLMGeneration:
    validation_contract = build_llm_validation_contract(
        game_state,
        rule_text,
        speaker,
        required_target,
        required_claims or [],
        public_text,
        required_self_role,
    )
    base_context = dict(context)
    base_context["validation_contract"] = validation_contract
    attempts: list[dict[str, object]] = []
    last_reason = "LLM did not return a usable answer"

    for attempt_number in range(1, MAX_LLM_VALIDATION_ATTEMPTS + 1):
        attempt_context = dict(base_context)
        if attempts:
            attempt_context["validation_feedback"] = {
                "attempt": attempt_number,
                "previous_rejection": last_reason,
                "must_preserve": validation_contract,
                "instruction": "只修正上一轮问题，不得改动规则事实。",
            }
            attempt_context["previous_rejected_draft"] = truncate_display_text(
                str(attempts[-1].get("raw_text", "")),
                320,
            )
        prompt = system_prompt
        if attempts:
            prompt += (
                " 上一次回答未通过后端事实校验。validation_feedback 已列出必须保留的目标和声明，"
                "请逐项满足后再返回 JSON，不得新增 validation_contract 之外的游戏事实。"
            )

        result = LLM_CLIENT.generate_json_text(
            prompt,
            attempt_context,
            rule_text,
            max_attempts=1,
        )
        raw_text = result.raw_response_text or (result.text if result.used_llm else "")
        if not result.used_llm:
            last_reason = result.fallback_reason or "LLM request failed"
            if is_permanent_llm_fallback(last_reason):
                return result
            attempts.append(
                build_llm_validation_attempt(
                    attempt_number,
                    raw_text,
                    last_reason,
                    game_state,
                    rule_text,
                )
            )
            continue

        validation = validate_llm_rewrite(
            result,
            rule_text,
            game_state,
            speaker=speaker,
            required_target=required_target,
            required_claims=required_claims,
            public_text=public_text,
            required_self_role=required_self_role,
        )
        if validation.used_llm:
            attempts.append(
                {
                    "attempt": attempt_number,
                    "raw_text": raw_text,
                    "display_text": validation.text,
                    "rejection_reason": "",
                    "passed": True,
                    "sensitive": False,
                }
            )
            validation.validation_attempts = attempts
            if len(attempts) > 1:
                record_recovered_llm_validation_attempts(
                    game_state,
                    context,
                    attempts,
                )
            return validation

        last_reason = validation.fallback_reason
        attempts.append(
            build_llm_validation_attempt(
                attempt_number,
                raw_text,
                last_reason,
                game_state,
                rule_text,
            )
        )

    fallback = rule_llm_generation(
        rule_text,
        f"validation failed after {MAX_LLM_VALIDATION_ATTEMPTS} attempts: {last_reason}",
    )
    fallback.validation_attempts = attempts
    fallback.validation_failure_id = record_llm_validation_failure(
        game_state,
        context,
        attempts,
    )
    return fallback


def is_permanent_llm_fallback(reason: str) -> bool:
    normalized = reason.lower()
    return any(
        marker in normalized
        for marker in [
            "llm is disabled",
            "not fully configured",
            "mock provider",
            "httpstatuserror",
            "timeout",
            "network",
            "connecterror",
            "remoteprotocolerror",
        ]
    )


def build_llm_validation_contract(
    game_state: WolfGameState,
    rule_text: str,
    speaker: Optional[CharacterState],
    required_target: Optional[CharacterState],
    required_claims: list[PublicClaimState],
    public_text: bool,
    required_self_role: Optional[str] = None,
) -> dict[str, object]:
    allowed_role_claims = get_allowed_self_role_claims(
        game_state,
        speaker,
        rule_text,
        required_claims,
    )
    if required_self_role is not None:
        allowed_role_claims = {required_self_role}
    return {
        "required_target": build_character_validation_contract(
            game_state,
            required_target,
            public_text,
        ),
        "required_facts": [
            build_public_claim_validation_contract(game_state, claim)
            for claim in required_claims
        ],
        "allowed_self_role_claims": [
            ROLE_LABELS.get(role, role)
            for role in sorted(allowed_role_claims)
        ],
        "required_self_role": (
            ROLE_LABELS.get(required_self_role, required_self_role)
            if required_self_role is not None
            else None
        ),
        "public_text": public_text,
        "policy": (
            "Preserve each structured fact. Natural synonymous wording is allowed; "
            "do not add checks, skill actions, hidden identities, or wolf teammates."
        ),
    }


def build_character_validation_contract(
    game_state: WolfGameState,
    character: Optional[CharacterState],
    public_text: bool = True,
) -> Optional[dict[str, object]]:
    if character is None:
        return None
    aliases = [character.name, f"{character.id}号", f"{character.id} 号"]
    if not public_text and character.id == game_state.player_character_id:
        aliases.append("你")
    return {
        "id": character.id,
        "name": character.name,
        "accepted_references": aliases,
    }


def build_public_claim_validation_contract(
    game_state: WolfGameState,
    claim: PublicClaimState,
) -> dict[str, object]:
    contract: dict[str, object] = {"type": claim.claim_type}
    if claim.claimed_role:
        contract["claimed_role"] = ROLE_LABELS.get(claim.claimed_role, claim.claimed_role)
    if claim.target_id is not None:
        contract["target"] = build_character_validation_contract(
            game_state,
            get_character(game_state, claim.target_id),
        )
    if claim.claim_type == "seer_check":
        contract["result"] = {
            "value": claim.result,
            "accepted_expressions": get_seer_result_aliases(claim.result),
        }
    return contract


def build_llm_validation_attempt(
    attempt_number: int,
    raw_text: str,
    rejection_reason: str,
    game_state: WolfGameState,
    rule_text: str,
) -> dict[str, object]:
    sensitive = is_sensitive_llm_failure(
        rejection_reason,
        raw_text,
        game_state,
        rule_text,
    )
    return {
        "attempt": attempt_number,
        "raw_text": raw_text,
        "display_text": (
            "[隐藏信息已屏蔽]"
            if sensitive
            else (raw_text or "[DeepSeek 未返回可解析文本]")
        ),
        "rejection_reason": rejection_reason,
        "passed": False,
        "sensitive": sensitive,
    }


def is_sensitive_llm_failure(
    rejection_reason: str,
    raw_text: str,
    game_state: WolfGameState,
    rule_text: str,
) -> bool:
    normalized_reason = rejection_reason.lower()
    if any(
        marker in normalized_reason
        for marker in ["hidden", "private", "unsupported role"]
    ):
        return True
    return any(
        character.name in raw_text and character.name not in rule_text
        for character in game_state.characters
        if character.role == "werewolf"
    )


def record_llm_validation_failure(
    game_state: WolfGameState,
    context: dict[str, object],
    attempts: list[dict[str, object]],
) -> str:
    character_data = context.get("speaker") or context.get("npc") or {}
    character_id = int(character_data.get("id", 0)) if isinstance(character_data, dict) else 0
    failure_id = f"{game_state.game_id}-llm-{len(game_state.llm_validation_failures) + 1}"
    failure = LLMValidationFailureState(
        failure_id=failure_id,
        day=game_state.day,
        character_id=character_id,
        context_kind=str(context.get("task", "npc_text")),
        attempts=[LLMValidationAttemptState(**attempt) for attempt in attempts],
    )
    game_state.llm_validation_failures.append(failure)
    write_llm_validation_log_record(
        {
            "status": "fallback_after_five_attempts",
            **failure.model_dump(),
        }
    )
    return failure_id


def record_recovered_llm_validation_attempts(
    game_state: WolfGameState,
    context: dict[str, object],
    attempts: list[dict[str, object]],
) -> None:
    character_data = context.get("speaker") or context.get("npc") or {}
    character_id = int(character_data.get("id", 0)) if isinstance(character_data, dict) else 0
    write_llm_validation_log_record(
        {
            "status": "recovered_after_validation_retry",
            "game_id": game_state.game_id,
            "day": game_state.day,
            "character_id": character_id,
            "context_kind": str(context.get("task", "npc_text")),
            "attempts": attempts,
        }
    )


def write_llm_validation_log_record(record: dict[str, object]) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with LLM_VALIDATION_LOG_FILE.open("a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass


def build_llm_validation_failure_view(
    game_state: WolfGameState,
    failure_id: str,
    reveal_sensitive: bool = True,
) -> Optional[LLMValidationFailureView]:
    if not failure_id:
        return None
    failure = next(
        (
            item
            for item in game_state.llm_validation_failures
            if item.failure_id == failure_id
        ),
        None,
    )
    if failure is None:
        return None
    return LLMValidationFailureView(
        failure_id=failure.failure_id,
        character_id=failure.character_id,
        context_kind=failure.context_kind,
        attempts=[
            LLMValidationAttemptView(
                attempt=attempt.attempt,
                text=(attempt.raw_text if reveal_sensitive else attempt.display_text),
                rejection_reason=attempt.rejection_reason,
                sensitive=attempt.sensitive,
            )
            for attempt in failure.attempts
        ],
    )


def build_llm_safe_evidence(
    rag_context: list[dict[str, object]],
) -> list[dict[str, str]]:
    return [
        {
            "title": str(context.get("title", "")),
            "content": truncate_display_text(str(context.get("content", "")), 180),
        }
        for context in rag_context
        if bool(context.get("safe_to_show", False))
    ][:4]


def validate_llm_rewrite(
    result: LLMGeneration,
    rule_text: str,
    game_state: WolfGameState,
    speaker: Optional[CharacterState] = None,
    required_target: Optional[CharacterState] = None,
    required_claims: Optional[list[PublicClaimState]] = None,
    public_text: bool = False,
    required_self_role: Optional[str] = None,
) -> LLMGeneration:
    if not result.used_llm:
        return result

    candidate = " ".join(result.text.split()).strip()
    rejection_reasons: list[str] = []
    if required_self_role is not None and (
        speaker is None or speaker.role != required_self_role
    ):
        rejection_reasons.append("LLM private role-reveal authorization is invalid")
    if not candidate or len(candidate) > 320:
        rejection_reasons.append("LLM text length is invalid")
    if "\ufffd" in candidate:
        rejection_reasons.append("LLM text contains a replacement character")
    if required_target is not None and not text_mentions_required_target(
        candidate,
        required_target,
        game_state,
        public_text,
    ):
        rejection_reasons.append("LLM text omitted the rule-selected target")

    claims = required_claims or []
    allow_player_pronoun = not public_text
    candidate_checks = extract_seer_check_assertions(
        candidate,
        game_state,
        speaker,
        allow_player_pronoun,
    )
    candidate_roles = extract_self_role_claims(candidate)
    if speaker is not None and any(
        claimant_id == speaker.id
        for claimant_id, _target_id, _check_result in candidate_checks
    ):
        candidate_roles.add("seer")
    allowed_roles = get_allowed_self_role_claims(
        game_state,
        speaker,
        rule_text,
        claims,
    )
    if required_self_role is not None:
        allowed_roles = {required_self_role}
    required_roles = {
        claim.claimed_role
        for claim in claims
        if claim.claim_type == "role" and claim.claimed_role
    }
    if required_self_role is not None:
        required_roles.add(required_self_role)
    for role in sorted(required_roles - candidate_roles):
        rejection_reasons.append(
            f"LLM text omitted required self role claim: {ROLE_LABELS.get(role, role)}"
        )
    for role in sorted(candidate_roles - allowed_roles):
        rejection_reasons.append(
            f"LLM text introduced an unsupported role claim: {ROLE_LABELS.get(role, role)}"
        )

    allowed_checks = get_allowed_seer_checks(
        game_state,
        speaker,
        rule_text,
        claims,
        allow_player_pronoun,
    )
    required_checks = {
        (claim.character_id, claim.target_id, claim.result)
        for claim in claims
        if claim.claim_type == "seer_check" and claim.target_id is not None
    }
    for claimant_id, target_id, check_result in sorted(required_checks - candidate_checks):
        claimant = get_character(game_state, claimant_id)
        target = get_character(game_state, target_id)
        rejection_reasons.append(
            "LLM text omitted required seer check: "
            f"{claimant.id}号{claimant.name}→{target.id}号{target.name}="
            f"{format_seer_result(check_result)}"
        )
    for claimant_id, target_id, check_result in sorted(candidate_checks - allowed_checks):
        claimant = get_character(game_state, claimant_id)
        target = get_character(game_state, target_id)
        allowed_target_results = {
            result_value
            for allowed_claimant_id, allowed_target_id, result_value in allowed_checks
            if allowed_claimant_id == claimant_id and allowed_target_id == target_id
        }
        if allowed_target_results:
            rejection_reasons.append(
                "LLM text changed an approved seer-check result: "
                f"{claimant.id}号{claimant.name}→{target.id}号{target.name}="
                f"{format_seer_result(check_result)}"
            )
        else:
            rejection_reasons.append(
                "LLM text introduced an unapproved seer check: "
                f"{claimant.id}号{claimant.name}→{target.id}号{target.name}="
                f"{format_seer_result(check_result)}"
            )

    candidate_actions = extract_skill_action_assertions(
        candidate,
        game_state,
        allow_player_pronoun,
    )
    allowed_actions = get_allowed_skill_actions(
        game_state,
        speaker,
        rule_text,
        claims,
        allow_player_pronoun,
    )
    required_actions = {
        (claim.claim_type, claim.target_id)
        for claim in claims
        if claim.claim_type in {"witch_save", "witch_poison", "guard_success"}
        and claim.target_id is not None
    }
    for action_type, target_id in sorted(required_actions - candidate_actions):
        target = get_character(game_state, target_id)
        rejection_reasons.append(
            f"LLM text omitted required {action_type} fact: {target.id}号{target.name}"
        )
    for action_type, target_id in sorted(candidate_actions - allowed_actions):
        target = get_character(game_state, target_id)
        rejection_reasons.append(
            f"LLM text introduced an unapproved {action_type} fact: {target.id}号{target.name}"
        )

    if has_wolf_team_disclosure(candidate, game_state):
        rejection_reasons.append("LLM text introduced hidden wolf-team information")

    candidate_identity_claims = extract_character_power_role_assertions(candidate, game_state)
    allowed_identity_claims = extract_character_power_role_assertions(rule_text, game_state)
    allowed_identity_claims.update(
        (claim.character_id, claim.claimed_role)
        for claim in [*game_state.public_claims, *claims]
        if claim.claim_type == "role" and claim.claimed_role
    )
    for character_id, role in sorted(candidate_identity_claims - allowed_identity_claims):
        character = get_character(game_state, character_id)
        rejection_reasons.append(
            "LLM text introduced an unsupported character identity: "
            f"{character.id}号{character.name}={ROLE_LABELS.get(role, role)}"
        )

    rejection_reasons = list(dict.fromkeys(rejection_reasons))
    if rejection_reasons:
        return LLMGeneration(
            text=rule_text,
            used_llm=False,
            provider=result.provider,
            model=result.model,
            fallback_reason="; ".join(rejection_reasons),
            raw_response_text=result.raw_response_text,
        )
    result.text = candidate
    return result


def get_allowed_self_role_claims(
    game_state: WolfGameState,
    speaker: Optional[CharacterState],
    rule_text: str,
    required_claims: list[PublicClaimState],
) -> set[str]:
    roles = extract_self_role_claims(rule_text)
    roles.update(
        claim.claimed_role
        for claim in required_claims
        if claim.claimed_role
    )
    rule_checks = extract_seer_check_assertions(
        rule_text,
        game_state,
        speaker,
        True,
    )
    if speaker is not None and any(
        claimant_id == speaker.id
        for claimant_id, _target_id, _result in rule_checks
    ):
        roles.add("seer")
    if speaker is not None:
        roles.update(
            claim.claimed_role
            for claim in game_state.public_claims
            if claim.character_id == speaker.id
            and claim.claim_type == "role"
            and claim.claimed_role
        )
    return roles


def extract_self_role_claims(text: str) -> set[str]:
    role_group = "|".join(re.escape(label) for label in ROLE_LABELS.values())
    patterns = [
        rf"我\s*(?:是|就是|身份是|的身份是|拿到的是|底牌是)\s*({role_group})",
        rf"我\s*(?:起跳|跳|报|拍|认)\s*(?:一张|一个)?\s*({role_group})",
        rf"我\s*(?:(?:也|仍|还)\s*)?(?:继续\s*)?以\s*({role_group})\s*(?:身份|视角|牌)",
        rf"({role_group})\s*(?:牌)?\s*(?:在这里|在这儿|是我)",
    ]
    labels = {
        match.group(1)
        for pattern in patterns
        for match in re.finditer(pattern, text)
    }
    role_by_label = {label: role for role, label in ROLE_LABELS.items()}
    return {role_by_label[label] for label in labels}


def get_allowed_seer_checks(
    game_state: WolfGameState,
    speaker: Optional[CharacterState],
    rule_text: str,
    required_claims: list[PublicClaimState],
    allow_player_pronoun: bool,
) -> set[tuple[int, int, str]]:
    checks = extract_seer_check_assertions(
        rule_text,
        game_state,
        speaker,
        allow_player_pronoun,
    )
    checks.update(
        (claim.character_id, claim.target_id, claim.result)
        for claim in required_claims
        if claim.claim_type == "seer_check" and claim.target_id is not None
    )
    checks.update(
        (claim.character_id, claim.target_id, claim.result)
        for claim in game_state.public_claims
        if claim.claim_type == "seer_check" and claim.target_id is not None
    )
    return checks


def extract_seer_check_assertions(
    text: str,
    game_state: WolfGameState,
    speaker: Optional[CharacterState] = None,
    allow_player_pronoun: bool = False,
) -> set[tuple[int, int, str]]:
    checks: set[tuple[int, int, str]] = set()
    for sentence in re.split(r"[。！？!?；;\n]+", text):
        pending_relations: list[tuple[int, int]] = []
        for clause in re.split(r"[，,]+", sentence):
            relation = extract_seer_check_relation(
                clause,
                game_state,
                speaker,
                allow_player_pronoun,
            )
            results = extract_seer_results(clause)
            if relation:
                if results:
                    checks.update(
                        (claimant_id, target_id, result_value)
                        for claimant_id, target_id in relation
                        for result_value in results
                    )
                    pending_relations = []
                else:
                    pending_relations = relation
                continue
            if pending_relations and results:
                checks.update(
                    (claimant_id, target_id, result_value)
                    for claimant_id, target_id in pending_relations
                    for result_value in results
                )
                pending_relations = []
    return checks


def extract_seer_check_relation(
    clause: str,
    game_state: WolfGameState,
    speaker: Optional[CharacterState],
    allow_player_pronoun: bool,
) -> list[tuple[int, int]]:
    marker_match = re.search(
        r"查验过|查验了|查验|验人|验的是|验了|验过|验出|验到|摸了|摸过|摸的是|给|报了|报",
        clause,
    )
    if marker_match is not None:
        prefix = clause[:marker_match.start()]
        suffix = clause[marker_match.end():]
        target_ids = find_mentioned_character_ids(
            suffix,
            game_state,
            allow_player_pronoun,
        )
        if not target_ids:
            return []
        claimant_id = resolve_check_claimant_id(prefix, game_state, speaker)
        if claimant_id is None:
            return []
        return [(claimant_id, target_id) for target_id in target_ids if target_id != claimant_id]

    results = extract_seer_results(clause)
    target_ids = find_mentioned_character_ids(
        clause,
        game_state,
        allow_player_pronoun,
    )
    if results and speaker is not None and "我的" in clause and len(target_ids) == 1:
        return [(speaker.id, target_ids[0])]
    return []


def resolve_check_claimant_id(
    prefix: str,
    game_state: WolfGameState,
    speaker: Optional[CharacterState],
) -> Optional[int]:
    explicit_claimant_id, explicit_position = find_last_character_mention(prefix, game_state)
    self_position = prefix.rfind("我")
    if speaker is not None and self_position > explicit_position:
        return speaker.id
    if explicit_claimant_id is not None:
        return explicit_claimant_id
    return speaker.id if speaker is not None else None


def find_last_character_mention(
    text: str,
    game_state: WolfGameState,
) -> tuple[Optional[int], int]:
    latest_id: Optional[int] = None
    latest_position = -1
    for character in game_state.characters:
        name_position = text.rfind(character.name)
        if name_position > latest_position:
            latest_id = character.id
            latest_position = name_position
        for match in re.finditer(rf"(?<!\d){character.id}\s*号(?!\d)", text):
            if match.start() > latest_position:
                latest_id = character.id
                latest_position = match.start()
    return latest_id, latest_position


def extract_seer_results(text: str) -> set[str]:
    results: set[str] = set()
    if "查杀" in text or contains_positive_identity_term(text, ["狼人", "狼牌", "是狼"]):
        results.add("werewolf")
    if "金水" in text or contains_positive_identity_term(text, ["好人"]):
        results.add("good")
    return results


def contains_positive_identity_term(text: str, terms: list[str]) -> bool:
    for term in terms:
        for match in re.finditer(re.escape(term), text):
            prefix = text[max(0, match.start() - 6):match.start()]
            if re.search(r"(?:不是|并非|不像|未必是|不一定是|不认为)\s*$", prefix):
                continue
            return True
    return False


def get_seer_result_aliases(result: str) -> list[str]:
    return ["狼人", "查杀", "是狼", "狼牌"] if result == "werewolf" else ["好人", "金水"]


def format_seer_result(result: str) -> str:
    return "狼人" if result == "werewolf" else "好人"


SKILL_ACTION_MARKERS = {
    "witch_save": ["用过解药", "用了药", "解药救", "救过", "救了", "救下"],
    "witch_poison": ["用过毒药", "用了毒药", "毒过", "毒了", "撒毒", "用毒"],
    "guard_success": ["守护过", "守过", "守了", "挡下了狼刀", "挡住狼刀", "挡刀"],
}


def get_allowed_skill_actions(
    game_state: WolfGameState,
    speaker: Optional[CharacterState],
    rule_text: str,
    required_claims: list[PublicClaimState],
    allow_player_pronoun: bool,
) -> set[tuple[str, int]]:
    actions = extract_skill_action_assertions(
        rule_text,
        game_state,
        allow_player_pronoun,
    )
    actions.update(
        (claim.claim_type, claim.target_id)
        for claim in required_claims
        if claim.claim_type in SKILL_ACTION_MARKERS and claim.target_id is not None
    )
    if speaker is not None:
        actions.update(
            (claim.claim_type, claim.target_id)
            for claim in game_state.public_claims
            if claim.character_id == speaker.id
            and claim.claim_type in SKILL_ACTION_MARKERS
            and claim.target_id is not None
        )
    return actions


def extract_skill_action_assertions(
    text: str,
    game_state: WolfGameState,
    allow_player_pronoun: bool = False,
) -> set[tuple[str, int]]:
    actions: set[tuple[str, int]] = set()
    for sentence in re.split(r"[。！？!?；;\n]+", text):
        pending_action_types: list[str] = []
        for clause in re.split(r"[，,]+", sentence):
            target_ids = find_mentioned_character_ids(
                clause,
                game_state,
                allow_player_pronoun,
            )
            action_types = [
                action_type
                for action_type, markers in SKILL_ACTION_MARKERS.items()
                if any(marker in clause for marker in markers)
            ]
            if action_types and target_ids:
                actions.update(
                    (action_type, target_id)
                    for action_type in action_types
                    for target_id in target_ids
                )
                pending_action_types = []
            elif action_types:
                pending_action_types = action_types
            elif pending_action_types and target_ids:
                actions.update(
                    (action_type, target_id)
                    for action_type in pending_action_types
                    for target_id in target_ids
                )
                pending_action_types = []
    return actions


def find_mentioned_character_ids(
    text: str,
    game_state: WolfGameState,
    allow_player_pronoun: bool = False,
) -> list[int]:
    character_ids = [
        character.id
        for character in game_state.characters
        if text_mentions_character(text, character)
    ]
    if allow_player_pronoun and "你" in text:
        character_ids.append(game_state.player_character_id)
    return list(dict.fromkeys(character_ids))


def extract_character_power_role_assertions(
    text: str,
    game_state: WolfGameState,
) -> set[tuple[int, str]]:
    assertions: set[tuple[int, str]] = set()
    power_roles = ["seer", "witch", "hunter", "guard"]
    speculation_markers = [
        "觉得",
        "认为",
        "可能",
        "像",
        "疑似",
        "也许",
        "或许",
        "大概率",
        "应该",
        "怀疑",
        "相信",
        "不认为",
    ]
    for character in game_state.characters:
        reference_pattern = character_reference_pattern(character)
        for role in power_roles:
            label = ROLE_LABELS[role]
            pattern = rf"{reference_pattern}.{{0,8}}?(?:就是|是|身份为|身份是|底牌是)\s*{re.escape(label)}"
            for match in re.finditer(pattern, text):
                prefix = text[max(0, match.start() - 12):match.start()]
                if any(marker in prefix for marker in speculation_markers):
                    continue
                assertions.add((character.id, role))
    return assertions


def has_wolf_team_disclosure(text: str, game_state: WolfGameState) -> bool:
    direct_patterns = [
        r"我的(?:狼|狼人)?队友",
        r"狼队友",
        r"狼人同伴",
        r"我们(?:几个|四个|这些)?狼人",
        r"同为狼人",
        r"都是狼人阵营",
    ]
    if any(re.search(pattern, text) for pattern in direct_patterns):
        return True
    for character in game_state.characters:
        pattern = rf"{character_reference_pattern(character)}.{{0,5}}?(?:是|算是)\s*我的(?:狼|狼人)?队友"
        if re.search(pattern, text):
            return True
    return False


def character_reference_pattern(character: CharacterState) -> str:
    return (
        rf"(?:{re.escape(character.name)}|"
        rf"(?<!\d){character.id}\s*号(?!\d)(?:{re.escape(character.name)})?)"
    )


def text_mentions_character(text: str, character: CharacterState) -> bool:
    return character.name in text or bool(
        re.search(rf"(?<!\d){character.id}\s*号(?!\d)", text)
    )


def text_mentions_required_target(
    candidate: str,
    target: CharacterState,
    game_state: WolfGameState,
    public_text: bool,
) -> bool:
    if text_mentions_character(candidate, target):
        return True
    return not public_text and target.id == game_state.player_character_id and "你" in candidate


def rule_llm_generation(text: str, reason: str) -> LLMGeneration:
    return LLMGeneration(
        text=text,
        used_llm=False,
        provider="rule",
        model="rule-template",
        fallback_reason=reason,
    )


def choose_speech_focus_target(
    game_state: WolfGameState,
    speaker: CharacterState,
) -> Optional[CharacterState]:
    candidates = [
        character
        for character in game_state.characters
        if character.alive and character.id != speaker.id
    ]
    if speaker.role == "werewolf":
        sellable_teammates = [
            character
            for character in candidates
            if character.role == "werewolf"
            and should_wolf_sell_teammate(game_state, speaker, character)
        ]
        if sellable_teammates:
            return max(
                sellable_teammates,
                key=lambda character: get_public_suspicion_score(game_state, character.id),
            )
        non_wolf_candidates = [
            character
            for character in candidates
            if character.role != "werewolf"
        ]
        if non_wolf_candidates:
            candidates = non_wolf_candidates

    if not candidates:
        return None

    temporary_nomination_target_id = (
        game_state.meeting.temporary_nomination_target_id
        if game_state.meeting is not None
        else None
    )
    sheriff = (
        get_character(game_state, game_state.sheriff_id)
        if game_state.sheriff_id is not None
        else None
    )

    def focus_score(character: CharacterState) -> int:
        score = speaker.suspicion.get(str(character.id), 0)
        if sheriff is not None and character.id == temporary_nomination_target_id:
            sheriff_trust = float(
                speaker.relationships.get(str(sheriff.id), {}).get("trust", 0.5)
            )
            score += int(6 + 14 * sheriff_trust)
        return score

    highest_suspicion = max(focus_score(character) for character in candidates)
    if highest_suspicion > 0:
        candidates = [
            character
            for character in candidates
            if focus_score(character) == highest_suspicion
        ]

    return random.choice(candidates)


def should_wolf_sell_teammate(
    game_state: WolfGameState,
    wolf: CharacterState,
    teammate: CharacterState,
) -> bool:
    pressure = get_public_suspicion_score(game_state, teammate.id)
    strategic_score = (
        wolf.personality.get("deception", 0.5)
        + wolf.personality.get("logic", 0.5)
        + wolf.personality.get("aggressiveness", 0.5) * 0.5
    )
    threshold = max(55, int(115 - strategic_score * 30))
    return pressure >= threshold


def ensure_vote_phase(game_state: WolfGameState) -> None:
    if game_state.phase != "VOTE":
        raise HTTPException(
            status_code=400,
            detail=f"当前阶段是 {game_state.phase}，只能在白天投票阶段操作。",
        )


def validate_vote(game_state: WolfGameState, voter: CharacterState, target_id: int) -> None:
    if not voter.alive:
        raise HTTPException(status_code=400, detail="出局角色不能投票。")

    target = get_character(game_state, target_id)
    if not target.alive:
        raise HTTPException(status_code=400, detail="不能投给已出局角色。")
    if target.id == voter.id:
        raise HTTPException(status_code=400, detail="当前规则不允许投给自己。")


def upsert_vote(game_state: WolfGameState, new_vote: VoteState) -> None:
    game_state.votes = [
        vote
        for vote in game_state.votes
        if not (vote.day == new_vote.day and vote.voter_id == new_vote.voter_id)
    ]
    game_state.votes.append(new_vote)


def has_vote(game_state: WolfGameState, voter_id: int) -> bool:
    return any(
        vote.day == game_state.day and vote.voter_id == voter_id
        for vote in game_state.votes
    )


def ensure_npc_vote_decisions(game_state: WolfGameState) -> list[NpcVoteDecision]:
    for voter in game_state.characters:
        if voter.is_player or not voter.alive:
            continue

        if has_vote(game_state, voter.id):
            continue

        target_id = choose_npc_vote_target(game_state, voter)
        if target_id is None:
            continue

        target = get_character(game_state, target_id)
        rag_context = build_public_decision_rag_context(
            game_state,
            voter,
            target,
            "投票决定",
        )
        evidence = choose_public_decision_evidence(rag_context)
        reason = build_npc_vote_reason(voter, target, evidence)
        upsert_vote(
            game_state,
            VoteState(
                day=game_state.day,
                voter_id=voter.id,
                target_id=target.id,
                reason=reason,
                evidence_titles=get_safe_rag_titles(rag_context),
                retrieval_mode=str(HYBRID_INDEX.status()["mode"]),
                weight=1.5 if game_state.sheriff_id == voter.id else 1.0,
            ),
        )

    return [
        NpcVoteDecision(
            character_id=vote.voter_id,
            target_id=vote.target_id,
            reason=vote.reason,
            evidence_titles=list(vote.evidence_titles),
            retrieval_mode=vote.retrieval_mode,
        )
        for vote in game_state.votes
        if vote.day == game_state.day and is_alive_npc(game_state, vote.voter_id)
    ]


def choose_npc_vote_target(
    game_state: WolfGameState,
    voter: CharacterState,
    ignore_sheriff_lock: bool = False,
) -> Optional[int]:
    if (
        not ignore_sheriff_lock
        and game_state.sheriff_id == voter.id
        and game_state.meeting is not None
        and game_state.meeting.nomination_target_id is not None
    ):
        nomination_target = get_character(game_state, game_state.meeting.nomination_target_id)
        if nomination_target.alive and nomination_target.id != voter.id:
            return nomination_target.id

    candidates = [
        character
        for character in game_state.characters
        if character.alive and character.id != voter.id
    ]
    if voter.role == "werewolf":
        sellable_teammates = [
            character
            for character in candidates
            if character.role == "werewolf"
            and should_wolf_sell_teammate(game_state, voter, character)
        ]
        if sellable_teammates:
            return max(
                sellable_teammates,
                key=lambda character: get_public_suspicion_score(game_state, character.id),
            ).id
        non_wolf_candidates = [
            character
            for character in candidates
            if character.role != "werewolf"
        ]
        if non_wolf_candidates:
            candidates = non_wolf_candidates

    if not candidates:
        return None

    nomination_target_id = (
        game_state.meeting.nomination_target_id
        if game_state.meeting is not None
        else None
    )
    sheriff = (
        get_character(game_state, game_state.sheriff_id)
        if game_state.sheriff_id is not None
        else None
    )
    return max(
        candidates,
        key=lambda character: (
            voter.suspicion.get(str(character.id), 0)
            + (
                int(
                    8
                    + 18
                    * float(voter.relationships.get(str(sheriff.id), {}).get("trust", 0.5))
                )
                if sheriff is not None and character.id == nomination_target_id
                else 0
            ),
            get_public_suspicion_score(game_state, character.id),
            -character.id,
        ),
    ).id


def build_npc_vote_reason(
    voter: CharacterState,
    target: CharacterState,
    evidence: Optional[dict[str, object]],
) -> str:
    suspicion_value = voter.suspicion.get(str(target.id), 0)
    if suspicion_value > 0:
        reason = f"我对{target.name}的怀疑值最高，先投给他。"
    elif voter.role == "werewolf" and target.role == "werewolf":
        reason = f"{target.name}现在处在全场焦点，我不能忽略他没有解释清楚的部分。"
    elif voter.role == "werewolf":
        reason = f"我觉得{target.name}今天的站位比较模糊，先投给他。"
    else:
        reason = f"当前信息有限，我先投给{target.name}。"
    return append_public_rag_evidence(reason, evidence)


def is_alive_npc(game_state: WolfGameState, character_id: int) -> bool:
    character = get_character(game_state, character_id)
    return not character.is_player and character.alive


def get_current_valid_votes(game_state: WolfGameState) -> list[VoteState]:
    valid_votes = []
    for vote in game_state.votes:
        if vote.day != game_state.day:
            continue

        voter = get_character(game_state, vote.voter_id)
        target = get_character(game_state, vote.target_id)
        if voter.alive and target.alive:
            valid_votes.append(vote)

    return valid_votes


def resolve_vote_target(votes: list[VoteState]) -> Optional[int]:
    if not votes:
        return None

    vote_counts = {
        vote.target_id: 0.0
        for vote in votes
    }
    for vote in votes:
        vote_counts[vote.target_id] += vote.weight

    highest_count = max(vote_counts.values())
    tied_targets = [
        target_id
        for target_id, count in vote_counts.items()
        if count == highest_count
    ]
    return random.choice(tied_targets)


def build_vote_totals(votes: list[VoteState]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for vote in votes:
        key = str(vote.target_id)
        totals[key] = round(totals.get(key, 0.0) + vote.weight, 1)
    return totals


def build_vote_ballot_details(
    game_state: WolfGameState,
    votes: list[VoteState],
) -> list[VoteBallotDetail]:
    details = []
    for vote in sorted(votes, key=lambda item: item.voter_id):
        voter = get_character(game_state, vote.voter_id)
        target = get_character(game_state, vote.target_id)
        details.append(
            VoteBallotDetail(
                voter_id=voter.id,
                voter_name=voter.name,
                target_id=target.id,
                target_name=target.name,
                reason=vote.reason,
                weight=vote.weight,
                is_sheriff=game_state.sheriff_id == voter.id,
                evidence_titles=list(vote.evidence_titles),
                retrieval_mode=vote.retrieval_mode,
            )
        )
    return details


def finalize_current_vote(
    game_state: WolfGameState,
) -> tuple[Optional[int], list[VoteState], str]:
    current_votes = get_current_valid_votes(game_state)
    if not current_votes:
        raise HTTPException(status_code=400, detail="当前没有可结算的投票。")
    exiled_character_id = resolve_vote_target(current_votes)
    if exiled_character_id is not None:
        eliminate_character(
            game_state,
            exiled_character_id,
            "exiled",
            source_action="day_vote",
            source_actor_ids=[
                vote.voter_id
                for vote in current_votes
                if vote.target_id == exiled_character_id
            ],
            source_target_id=exiled_character_id,
        )

    apply_vote_social_updates(game_state, current_votes, exiled_character_id)
    append_vote_memory_summaries(game_state, current_votes, exiled_character_id)
    public_message = build_vote_public_message(game_state, exiled_character_id)
    game_state.public_logs.append(public_message)
    hunter_message = handle_hunter_trigger(
        game_state,
        [exiled_character_id] if exiled_character_id is not None else [],
        trigger="vote",
        continuation="after_vote",
    )
    if hunter_message:
        game_state.public_logs.append(hunter_message)
        public_message += "\n" + hunter_message
    if game_state.phase != "HUNTER_SHOT":
        continue_after_elimination(game_state, "after_vote")
    game_state.player_private_info = build_player_private_info_dict(game_state)
    return exiled_character_id, current_votes, public_message


def apply_vote_social_updates(
    game_state: WolfGameState,
    votes: list[VoteState],
    exiled_character_id: Optional[int],
) -> None:
    votes_by_voter = {
        vote.voter_id: vote.target_id
        for vote in votes
    }
    player_vote_target_id = votes_by_voter.get(game_state.player_character_id)

    for observer in game_state.characters:
        if observer.is_player or not observer.alive:
            continue

        observer_vote_target_id = votes_by_voter.get(observer.id)
        for vote in votes:
            voter = get_character(game_state, vote.voter_id)
            target = get_character(game_state, vote.target_id)
            if voter.id == observer.id:
                if target.alive:
                    adjust_suspicion(observer, target.id, 6)
                continue

            if voter.id == target.id:
                continue

            if vote.target_id == observer.id:
                adjust_suspicion(observer, voter.id, 12)
                adjust_relationship_trust(observer, voter.id, -0.08, "本轮投票给我")
                continue

            if observer_vote_target_id is not None and observer_vote_target_id == vote.target_id:
                adjust_suspicion(observer, voter.id, -4)
                adjust_relationship_trust(observer, voter.id, 0.05, "本轮投票一致")
                continue

            target_relationship = observer.relationships.get(str(target.id), {})
            target_trust = float(target_relationship.get("trust", 0.5))
            if target_trust >= 0.65:
                adjust_suspicion(observer, voter.id, 8)
                adjust_relationship_trust(observer, voter.id, -0.04, "本轮投给我信任的人")

        if player_vote_target_id is not None and observer.id != game_state.player_character_id:
            if player_vote_target_id == observer.id:
                adjust_suspicion(observer, game_state.player_character_id, 10)
                adjust_relationship_trust(observer, game_state.player_character_id, -0.1, "玩家本轮投票给我")
            elif observer_vote_target_id is not None and player_vote_target_id == observer_vote_target_id:
                adjust_relationship_trust(observer, game_state.player_character_id, 0.06, "玩家本轮和我投票一致")
            else:
                adjust_relationship_trust(observer, game_state.player_character_id, -0.03, "玩家本轮和我投票不同")

        if exiled_character_id is not None and exiled_character_id != observer.id:
            adjust_suspicion(observer, exiled_character_id, -10)


def append_vote_memory_summaries(
    game_state: WolfGameState,
    votes: list[VoteState],
    exiled_character_id: Optional[int],
) -> None:
    votes_by_voter = {
        vote.voter_id: vote.target_id
        for vote in votes
    }
    player_vote_target_id = votes_by_voter.get(game_state.player_character_id)
    exiled_name = "无人"
    if exiled_character_id is not None:
        exiled_name = get_character(game_state, exiled_character_id).name

    for character in game_state.characters:
        if not character.alive:
            continue

        own_vote_target_id = votes_by_voter.get(character.id)
        if own_vote_target_id is None:
            append_character_memory(character, f"第 {game_state.day} 天投票结束，{exiled_name} 被放逐。")
            continue

        own_target = get_character(game_state, own_vote_target_id)
        detail = f"第 {game_state.day} 天我投给 {own_target.name}，最终 {exiled_name} 被放逐。"
        if not character.is_player and player_vote_target_id is not None:
            if player_vote_target_id == own_vote_target_id:
                detail += " 玩家和我投票一致。"
            else:
                player_target = get_character(game_state, player_vote_target_id)
                detail += f" 玩家投给了 {player_target.name}。"
        append_character_memory(character, detail)


def append_character_memory(character: CharacterState, entry: str, limit: int = 8) -> None:
    existing_entries = [
        item.strip()
        for item in character.memory_summary.split("\n")
        if item.strip()
    ]
    existing_entries.append(entry)
    character.memory_summary = "\n".join(existing_entries[-limit:])


def count_character_memory(character: CharacterState) -> int:
    return len(
        [
            item
            for item in character.memory_summary.split("\n")
            if item.strip()
        ]
    )


def adjust_suspicion(observer: CharacterState, target_id: int, amount: int) -> None:
    key = str(target_id)
    observer.suspicion[key] = max(0, min(observer.suspicion.get(key, 0) + amount, 100))


def adjust_relationship_trust(
    observer: CharacterState,
    target_id: int,
    amount: float,
    note: str,
) -> None:
    key = str(target_id)
    relationship = observer.relationships.get(key)
    if relationship is None:
        relationship = {
            "trust": 0.5,
            "alliance": "none",
            "notes": "",
        }
        observer.relationships[key] = relationship

    relationship["trust"] = clamp_float(float(relationship.get("trust", 0.5)) + amount)
    relationship["notes"] = note


def build_vote_public_message(
    game_state: WolfGameState,
    exiled_character_id: Optional[int],
) -> str:
    if exiled_character_id is None:
        return f"第 {game_state.day} 天投票结束，没有角色被放逐。"

    character = get_character(game_state, exiled_character_id)
    return f"第 {game_state.day} 天投票结束，{character.name} 被放逐出局。"


def get_winner_result(game_state: WolfGameState) -> tuple[Optional[str], str]:
    alive_characters = [
        character
        for character in game_state.characters
        if character.alive
    ]
    alive_wolves = [
        character
        for character in alive_characters
        if character.role == "werewolf"
    ]
    alive_villagers = [
        character
        for character in alive_characters
        if character.role == "villager"
    ]
    alive_gods = [
        character
        for character in alive_characters
        if character.role in GOD_ROLES
    ]
    alive_good_characters = [
        character
        for character in alive_characters
        if character.role != "werewolf"
    ]

    if not alive_wolves:
        return "good", "all_wolves_eliminated"
    if not alive_villagers:
        return "werewolf", "villager_side_eliminated"
    if not alive_gods:
        return "werewolf", "god_side_eliminated"
    if len(alive_wolves) >= len(alive_good_characters):
        return "werewolf", "wolf_control"
    return None, ""


def check_winner(game_state: WolfGameState) -> Optional[str]:
    winner, _reason = get_winner_result(game_state)
    return winner


def build_winner_message(winner: str, reason: str = "") -> str:
    if winner == "good":
        return "好人阵营胜利，所有狼人都已出局。"
    if winner == "werewolf":
        if reason == "wolf_control":
            return "狼人阵营胜利：存活狼人数已不少于其他角色，狼人形成控场。"
        if reason == "villager_side_eliminated":
            return "狼人阵营胜利，所有村民都已出局。"
        if reason == "god_side_eliminated":
            return "狼人阵营胜利，所有神职都已出局。"
        return "狼人阵营胜利。"
    return "游戏结束。"


def build_game_summary(game_state: WolfGameState) -> GameSummaryResponse:
    timeline = build_game_summary_timeline(game_state)
    character_summaries = []
    for character in game_state.characters:
        character_summaries.append(
            CharacterGameSummary(
                character_id=character.id,
                name=character.name,
                role=character.role,
                role_label=ROLE_LABELS.get(character.role, character.role),
                camp=character.camp,
                camp_label="狼人阵营" if character.camp == "werewolf" else "好人阵营",
                outcome=build_character_outcome(game_state, character),
                actions=[
                    event
                    for event in timeline
                    if character.id in event.character_ids
                ],
            )
        )

    winner = game_state.winner or ""
    return GameSummaryResponse(
        game_id=game_state.game_id,
        total_days=game_state.day,
        winner=winner,
        winner_label="狼人阵营" if winner == "werewolf" else "好人阵营",
        winner_message=build_winner_message(winner, game_state.winner_reason),
        characters=character_summaries,
        timeline=timeline,
        llm_validation_failures=[
            view
            for failure in game_state.llm_validation_failures
            if (
                view := build_llm_validation_failure_view(
                    game_state,
                    failure.failure_id,
                    reveal_sensitive=True,
                )
            ) is not None
        ],
    )


def build_game_summary_timeline(game_state: WolfGameState) -> list[GameSummaryEvent]:
    ranked_events: list[tuple[int, int, int, GameSummaryEvent]] = []
    sequence = 0

    def add_event(
        day: int,
        phase_rank: int,
        phase: str,
        character_ids: list[int],
        text: str,
        is_private: bool = False,
    ) -> None:
        nonlocal sequence
        ranked_events.append(
            (
                day,
                phase_rank,
                sequence,
                GameSummaryEvent(
                    day=day,
                    phase=phase,
                    character_ids=character_ids,
                    text=text,
                    is_private=is_private,
                ),
            )
        )
        sequence += 1

    for action in game_state.night_actions:
        actor = get_character(game_state, action.actor_id)
        actor_name = format_full_character_name(actor)
        target = (
            get_character(game_state, action.target_id)
            if action.target_id is not None
            else None
        )
        target_name = format_full_character_name(target) if target is not None else "无目标"
        if action.action_type == "werewolf_kill":
            text = f"{actor_name}选择袭击{target_name}。"
        elif action.action_type == "seer_check" and target is not None:
            result = "狼人" if target.role == "werewolf" else "好人"
            text = f"{actor_name}查验{target_name}，结果为{result}。"
        elif action.action_type == "guard_protect" and target is not None:
            resolution = next(
                (
                    item
                    for item in game_state.night_resolutions
                    if item.day == action.day
                ),
                None,
            )
            blocked = (
                resolution is not None
                and resolution.attacked_target_id == target.id
                and target.id in resolution.protected_ids
                and resolution.saved_target_id != target.id
            )
            result = "，成功挡下狼刀" if blocked else ""
            text = f"{actor_name}守护{target_name}{result}。"
        elif action.action_type == "witch_save" and target is not None:
            text = f"{actor_name}对{target_name}使用解药。"
        elif action.action_type == "witch_poison" and target is not None:
            text = f"{actor_name}对{target_name}使用毒药。"
        else:
            text = f"{actor_name}本夜没有身份技能行动。"
        add_event(action.day, 10, "NIGHT", [actor.id], text, True)

    for shot in game_state.hunter_shots:
        hunter = get_character(game_state, shot.hunter_id)
        if shot.target_id is None:
            text = f"{format_full_character_name(hunter)}出局后选择不开枪。"
            character_ids = [hunter.id]
        else:
            target = get_character(game_state, shot.target_id)
            text = (
                f"{format_full_character_name(hunter)}出局后开枪，"
                f"{format_full_character_name(target)}出局。"
            )
            character_ids = [hunter.id, target.id]
        phase_rank = 16 if shot.trigger == "night" else 46
        add_event(shot.day, phase_rank, "HUNTER_SHOT", character_ids, text)

    for claim in game_state.public_claims:
        claimant = get_character(game_state, claim.character_id)
        claim_label = build_public_claim_label(game_state, claim)
        character_ids = [claimant.id]
        if claim.target_id is not None:
            character_ids.append(claim.target_id)
        add_event(
            claim.day,
            21,
            "PUBLIC_CLAIM",
            character_ids,
            f"{format_full_character_name(claimant)}公开声明：{claim_label}。",
        )

    for event in game_state.sheriff_events:
        character_ids = [
            character_id
            for character_id in [event.actor_id, event.target_id]
            if character_id is not None
        ]
        add_event(
            event.day,
            18,
            "SHERIFF",
            character_ids,
            event.detail,
        )

    for speech in game_state.speeches:
        speaker = get_character(game_state, speech.character_id)
        add_event(
            speech.day,
            17 if speech.phase.startswith("SHERIFF") else 20,
            speech.phase,
            [speaker.id],
            f"{format_full_character_name(speaker)}公开发言：{speech.speech}",
        )

    for conversation in game_state.private_conversations:
        npc = get_character(game_state, conversation.npc_character_id)
        player = get_character(game_state, game_state.player_character_id)
        effect_text = "影响了 NPC 决策" if conversation.effective else "未再次影响 NPC 决策"
        add_event(
            conversation.day,
            30,
            "FREE_ACTIVITY",
            [player.id, npc.id],
            (
                f"{format_full_character_name(player)}私下询问{format_full_character_name(npc)}："
                f"{conversation.question}\n{format_full_character_name(npc)}回答："
                f"{conversation.reply}\n结果：{effect_text}。"
            ),
            True,
        )

    for vote in game_state.votes:
        voter = get_character(game_state, vote.voter_id)
        target = get_character(game_state, vote.target_id)
        add_event(
            vote.day,
            40,
            "VOTE",
            [voter.id],
            (
                f"{format_full_character_name(voter)}投给{format_full_character_name(target)}。"
                f"票值：{vote.weight:g}。"
                f"理由：{vote.reason or '未提供理由。'}"
            ),
        )

    for elimination in game_state.eliminations:
        character = get_character(game_state, elimination.character_id)
        if elimination.cause == "night_kill":
            text = f"{format_full_character_name(character)}在夜间出局。"
            phase_rank = 15
            phase = "NIGHT_RESULT"
        elif elimination.cause == "witch_poison":
            text = f"{format_full_character_name(character)}被女巫使用毒药后出局。"
            phase_rank = 15
            phase = "NIGHT_RESULT"
        elif elimination.cause == "hunter_shot":
            text = f"{format_full_character_name(character)}被猎人开枪带走。"
            phase_rank = 16
            phase = "HUNTER_SHOT"
        else:
            text = f"{format_full_character_name(character)}在白天被投票放逐出局。"
            phase_rank = 45
            phase = "VOTE_RESULT"
        add_event(elimination.day, phase_rank, phase, [character.id], text)

    if game_state.winner is not None:
        add_event(
            game_state.day,
            50,
            "GAME_OVER",
            [],
            build_winner_message(game_state.winner, game_state.winner_reason),
        )

    ranked_events.sort(key=lambda item: (item[0], item[1], item[2]))
    return [item[3] for item in ranked_events]


def build_character_outcome(game_state: WolfGameState, character: CharacterState) -> str:
    result = "胜利" if character.camp == game_state.winner else "失败"
    elimination = next(
        (
            item
            for item in game_state.eliminations
            if item.character_id == character.id
        ),
        None,
    )
    if elimination is None:
        survival = "存活至游戏结束" if character.alive else "已出局"
        return f"{result} | {survival}"
    if elimination.cause == "night_kill":
        return f"{result} | 第 {elimination.day} 夜出局"
    if elimination.cause == "witch_poison":
        return f"{result} | 第 {elimination.day} 夜被毒出局"
    if elimination.cause == "hunter_shot":
        return f"{result} | 第 {elimination.day} 天被猎人带走"
    return f"{result} | 第 {elimination.day} 天被放逐出局"


def format_full_character_name(character: CharacterState) -> str:
    return f"{character.id}号 {character.name}"


def build_role_pool(roles: dict[str, int]) -> list[str]:
    role_pool = []
    for role, count in roles.items():
        if role not in CAMP_BY_ROLE:
            raise HTTPException(status_code=400, detail=f"未知身份：{role}")
        if count < 0:
            raise HTTPException(status_code=400, detail=f"身份数量不能为负数：{role}")
        role_pool.extend([role] * count)
    return role_pool


def build_game_id() -> str:
    return f"game_{len(GAME_STORE) + 1:03d}"


def get_character_by_id(characters: list[CharacterState], character_id: int) -> CharacterState:
    for character in characters:
        if character.id == character_id:
            return character
    raise HTTPException(status_code=404, detail=f"未找到角色：{character_id}")


def build_characters(player_name: str, role_pool: list[str]) -> list[CharacterState]:
    names = [player_name.strip() or "玩家"] + NPC_NAMES
    characters = []

    for index, role in enumerate(role_pool, start=1):
        characters.append(
            CharacterState(
                id=index,
                name=names[index - 1],
                is_player=index == 1,
                role=role,
                camp=CAMP_BY_ROLE[role],
                personality=build_default_personality(index, names[index - 1]),
                emotion=build_default_emotion(),
                memory_summary="",
            )
        )

    initialize_social_state(characters)
    return characters


def build_default_personality(character_id: int, character_name: str = "") -> dict[str, float]:
    if character_name in NPC_PERSONALITIES:
        return dict(NPC_PERSONALITIES[character_name])

    base_values = {
        "aggressiveness": 0.35,
        "cautiousness": 0.55,
        "deception": 0.4,
        "logic": 0.6,
        "empathy": 0.5,
        "leadership": 0.45,
    }
    offset = (character_id - 3) * 0.03
    return {
        key: clamp_float(value + offset)
        for key, value in base_values.items()
    }


def build_default_emotion() -> dict[str, float]:
    return {
        "trust": 0.5,
        "fear": 0.2,
        "anger": 0.1,
        "stress": 0.25,
        "confidence": 0.55,
    }


def initialize_social_state(characters: list[CharacterState]) -> None:
    wolf_ids = {
        character.id
        for character in characters
        if character.role == "werewolf"
    }

    for character in characters:
        suspicion = {}
        relationships = {}
        for other in characters:
            if other.id == character.id:
                continue

            suspicion[str(other.id)] = 0
            alliance = "none"
            trust = 0.5
            notes = ""
            if character.id in wolf_ids and other.id in wolf_ids:
                alliance = "wolf_teammate"
                trust = 0.9
                notes = "狼人队友"

            relationships[str(other.id)] = {
                "trust": trust,
                "alliance": alliance,
                "notes": notes,
            }

        character.suspicion = suspicion
        character.relationships = relationships


def get_sheriff_campaign_status(
    game_state: WolfGameState,
    character_id: int,
) -> str:
    election = game_state.sheriff_election
    if election is None or election.completed:
        return ""
    if (
        election.runoff_round > 0
        and character_id in election.runoff_candidates
        and character_id not in election.withdrawn
    ):
        return "pk"
    if character_id in election.withdrawn:
        return "withdrawn"
    if character_id in election.candidates:
        return "candidate"
    return ""


def build_character_views(game_state: WolfGameState) -> list[CharacterView]:
    views = []
    player = get_character(game_state, game_state.player_character_id)
    for character in game_state.characters:
        suspicion_score = get_public_suspicion_score(game_state, character.id)
        trust_to_player = get_trust_to_player(game_state, character)
        role_claim = get_public_role_claim(game_state, character.id)
        views.append(
            CharacterView(
                id=character.id,
                name=character.name,
                is_player=character.is_player,
                alive=character.alive,
                role_visible_to_player=(
                    character.role
                    if character.is_player
                    or (player.role == "werewolf" and character.role == "werewolf")
                    else None
                ),
                suspicion_score=suspicion_score,
                suspicion_level=get_public_suspicion_level(suspicion_score),
                trust_to_player=trust_to_player,
                trust_level=get_trust_level(trust_to_player),
                memory_count=count_character_memory(character),
                private_question_used_today=(
                    not character.is_player
                    and has_effective_private_question(game_state, character.id)
                ),
                claimed_role=(
                    role_claim.claimed_role if role_claim is not None else None
                ),
                public_claims=get_character_public_claim_labels(
                    game_state,
                    character.id,
                ),
                is_sheriff=game_state.sheriff_id == character.id,
                sheriff_campaign_status=get_sheriff_campaign_status(
                    game_state,
                    character.id,
                ),
            )
        )
    return views


def get_public_suspicion_score(game_state: WolfGameState, character_id: int) -> int:
    score = 0
    for observer in game_state.characters:
        if observer.is_player or not observer.alive or observer.id == character_id:
            continue
        score += observer.suspicion.get(str(character_id), 0)
    return score


def get_public_suspicion_level(score: int) -> str:
    if score <= 0:
        return "无"
    if score < 30:
        return "低"
    if score < 70:
        return "中"
    return "高"


def get_trust_to_player(
    game_state: WolfGameState,
    character: CharacterState,
) -> Optional[float]:
    if character.is_player:
        return None

    relationship = character.relationships.get(str(game_state.player_character_id))
    if relationship is None:
        return None

    return float(relationship.get("trust", 0.5))


def get_trust_level(trust: Optional[float]) -> str:
    if trust is None:
        return ""
    if trust < 0.35:
        return "低"
    if trust < 0.7:
        return "中"
    return "高"


def get_character(game_state: WolfGameState, character_id: int) -> CharacterState:
    for character in game_state.characters:
        if character.id == character_id:
            return character
    raise HTTPException(status_code=404, detail=f"未找到角色：{character_id}")


def clamp_float(value: float) -> float:
    return round(min(max(value, 0.0), 1.0), 2)


def load_memory_store() -> None:
    if not MEMORY_FILE.exists():
        return

    raw_data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    for memory_key, items in raw_data.items():
        MEMORY_STORE[memory_key] = [MemoryItem(**item) for item in items]


def load_npc_profiles() -> None:
    global NPC_PROFILES

    if not NPC_PROFILES_FILE.exists():
        NPC_PROFILES = {DEFAULT_NPC_PROFILE.npc_name: DEFAULT_NPC_PROFILE}
        return

    loaded_profiles = {}
    raw_profiles = json.loads(NPC_PROFILES_FILE.read_text(encoding="utf-8"))
    for raw_profile in raw_profiles:
        profile = NPCProfile(**raw_profile)
        loaded_profiles[profile.npc_name] = profile

    if DEFAULT_NPC_PROFILE.npc_name not in loaded_profiles:
        loaded_profiles[DEFAULT_NPC_PROFILE.npc_name] = DEFAULT_NPC_PROFILE

    NPC_PROFILES = loaded_profiles


def load_knowledge_base() -> None:
    global KNOWLEDGE_BASE

    if not KNOWLEDGE_BASE_FILE.exists():
        KNOWLEDGE_BASE = []
        HYBRID_INDEX.configure([])
        return

    loaded_items = []
    raw_items = json.loads(KNOWLEDGE_BASE_FILE.read_text(encoding="utf-8"))
    for raw_item in raw_items:
        loaded_items.append(KnowledgeItem(**raw_item))

    KNOWLEDGE_BASE = loaded_items
    HYBRID_INDEX.configure(
        [
            f"{item.title}\n{item.content}\n关键词：{'、'.join(item.keywords)}"
            for item in KNOWLEDGE_BASE
        ]
    )


def save_memory_store() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        memory_key: [item.model_dump() for item in items]
        for memory_key, items in MEMORY_STORE.items()
    }
    MEMORY_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_config_files() -> None:
    load_npc_profiles()
    load_knowledge_base()


load_config_files()
load_memory_store()
