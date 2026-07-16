#!/usr/bin/env python3
"""Run a small local smoke check for the Agent Town demo."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
GAME_DIR = ROOT_DIR / "game"
MAIN_SCENE = "res://scenes/Main.tscn"
MAIN_SCENE_FILE = GAME_DIR / "scenes" / "Main.tscn"
MAIN_SCRIPT_FILE = GAME_DIR / "scripts" / "main.gd"
DIALOG_SCENE_FILE = GAME_DIR / "scenes" / "DialogBox.tscn"
DIALOG_SCRIPT_FILE = GAME_DIR / "scripts" / "dialog_box.gd"
DIALOG_FONT_FILE = GAME_DIR / "assets" / "fonts" / "NotoSansSC-Variable.ttf"
DIALOG_FONT_LICENSE_FILE = GAME_DIR / "assets" / "fonts" / "OFL.txt"
NPC_SCENE_FILE = GAME_DIR / "scenes" / "NPC.tscn"
NPC_SCRIPT_FILE = GAME_DIR / "scripts" / "npc.gd"
PLAYER_SCENE_FILE = GAME_DIR / "scenes" / "Player.tscn"
PLAYER_SCRIPT_FILE = GAME_DIR / "scripts" / "player.gd"
CHARACTER_ASSET_DIR = GAME_DIR / "assets" / "characters"
POLICE_BADGE_FILE = GAME_DIR / "assets" / "ui" / "police_badge.svg"
EXPECTED_CHARACTER_ASSETS = {
    "player.svg",
    "messi.svg",
    "ronaldo.svg",
    "zhou_shen.svg",
    "mei_changsu.svg",
    "zelda.svg",
    "little_knight.svg",
    "hornet.svg",
    "pleasant_goat.svg",
    "lazy_goat.svg",
    "luoluo.svg",
    "doctor_strange.svg",
}
PROJECT_FILE = GAME_DIR / "project.godot"
KNOWLEDGE_FILE = BACKEND_DIR / "config" / "knowledge_base.json"
NPC_PROFILES_FILE = BACKEND_DIR / "config" / "npc_profiles.json"
BACKEND_MAIN_FILE = BACKEND_DIR / "app" / "main.py"
BACKEND_VENV_PYTHON = BACKEND_DIR / ".venv" / "bin" / "python"
MIN_KNOWLEDGE_COUNT = 100


def main() -> int:
    checks = [
        check_json_files,
        check_backend_compiles,
        check_llm_adapter,
        check_backend_search,
        check_wolf_game_start,
        check_godot_ui_layout,
        check_godot_loads,
    ]

    print("Agent Town smoke check")
    print("======================")

    for check in checks:
        try:
            check()
        except SmokeCheckError as exc:
            print(f"[FAIL] {exc}")
            return 1

    print("[OK] Smoke check passed.")
    return 0


def check_json_files() -> None:
    knowledge_items = load_json_list(KNOWLEDGE_FILE, "knowledge base")
    npc_profiles = load_json_list(NPC_PROFILES_FILE, "NPC profiles")
    expected_trigger_profiles = {
        "梅西", "C罗", "周深", "梅长苏", "塞尔达", "小骑士",
        "大黄蜂", "喜羊羊", "懒羊羊", "洛洛", "奇异博士",
    }
    trigger_profile_names = set()
    trigger_egg_ids = set()
    role_reveal_profiles = set()

    if len(knowledge_items) < MIN_KNOWLEDGE_COUNT:
        raise SmokeCheckError(
            f"knowledge base has {len(knowledge_items)} items, expected at least {MIN_KNOWLEDGE_COUNT}"
        )

    titles = [str(item.get("title", "")).strip() for item in knowledge_items]
    duplicate_titles = sorted({title for title in titles if titles.count(title) > 1})
    if duplicate_titles:
        raise SmokeCheckError("knowledge base has duplicate titles: " + ", ".join(duplicate_titles))

    for index, item in enumerate(knowledge_items, start=1):
        require_keys(item, {"npc_name", "title", "content", "keywords"}, f"knowledge item #{index}")
        if not isinstance(item["keywords"], list):
            raise SmokeCheckError(f"knowledge item #{index} keywords must be a list")

    for index, item in enumerate(npc_profiles, start=1):
        require_keys(item, {"npc_name", "role", "personality", "knowledge"}, f"NPC profile #{index}")
        if not isinstance(item["knowledge"], list):
            raise SmokeCheckError(f"NPC profile #{index} knowledge must be a list")
        if item["npc_name"] not in {"Guide", "Archivist"}:
            require_keys(
                item,
                {"speech_style", "catchphrases", "easter_eggs", "trigger_easter_eggs"},
                f"wolf-game NPC profile #{index}",
            )
            if not item["speech_style"] or not item["catchphrases"] or not item["easter_eggs"]:
                raise SmokeCheckError(f"wolf-game NPC profile #{index} voice data must not be empty")
            trigger_eggs = item["trigger_easter_eggs"]
            if not isinstance(trigger_eggs, list) or len(trigger_eggs) != 1:
                raise SmokeCheckError(f"wolf-game NPC profile #{index} must have one trigger easter egg")
            trigger_egg = trigger_eggs[0]
            require_keys(
                trigger_egg,
                {"egg_id", "triggers", "reply", "repeat_reply"},
                f"trigger easter egg for {item['npc_name']}",
            )
            if (
                not trigger_egg["egg_id"]
                or not isinstance(trigger_egg["triggers"], list)
                or not trigger_egg["triggers"]
                or not trigger_egg["reply"]
                or not trigger_egg["repeat_reply"]
            ):
                raise SmokeCheckError(f"trigger easter egg for {item['npc_name']} is incomplete")
            if trigger_egg["egg_id"] in trigger_egg_ids:
                raise SmokeCheckError(f"duplicate trigger easter egg id: {trigger_egg['egg_id']}")
            trigger_profile_names.add(item["npc_name"])
            trigger_egg_ids.add(trigger_egg["egg_id"])
            if bool(trigger_egg.get("reveal_self_role", False)):
                role_reveal_profiles.add(item["npc_name"])
                if "{role}" not in trigger_egg["reply"]:
                    raise SmokeCheckError("role-reveal easter egg must contain the {role} placeholder")

    if trigger_profile_names != expected_trigger_profiles:
        raise SmokeCheckError("trigger easter eggs must cover all eleven wolf-game NPCs")
    if role_reveal_profiles != {"梅长苏"}:
        raise SmokeCheckError("only 梅长苏 may reveal a real role through a trigger easter egg")

    for path in [KNOWLEDGE_FILE, NPC_PROFILES_FILE, BACKEND_MAIN_FILE]:
        if "\ufffd" in path.read_text(encoding="utf-8"):
            raise SmokeCheckError(f"Unicode replacement character found in {path.relative_to(ROOT_DIR)}")

    print(f"[OK] JSON config valid: {len(knowledge_items)} knowledge items, {len(npc_profiles)} NPC profiles.")


def check_backend_compiles() -> None:
    run_command(
        [sys.executable, "-m", "py_compile", str(BACKEND_MAIN_FILE)],
        cwd=ROOT_DIR,
        fail_message="backend/app/main.py failed to compile",
    )
    print("[OK] Backend Python file compiles.")


def check_llm_adapter() -> None:
    python_bin = BACKEND_VENV_PYTHON if BACKEND_VENV_PYTHON.exists() else Path(sys.executable)
    smoke_code = r'''
import json

import httpx

from app.llm import LLMClient, LLMSettings

fallback = "规则模板回答。"

disabled_client = LLMClient(LLMSettings(enabled=False))
disabled_result = disabled_client.generate_json_text("system", {"task": "test"}, fallback)
if disabled_result.used_llm or disabled_result.text != fallback:
    raise SystemExit("disabled LLM should use the rule fallback")

mock_client = LLMClient(LLMSettings(enabled=True, provider="mock"))
mock_result = mock_client.generate_json_text("system", {"task": "test"}, fallback)
if mock_result.used_llm or mock_result.text != fallback:
    raise SystemExit("mock provider should stay deterministic and key-free")

def success_handler(request: httpx.Request) -> httpx.Response:
    if request.headers.get("Authorization") != "Bearer test-key":
        raise AssertionError("LLM request should use bearer authentication")
    payload = json.loads(request.content.decode("utf-8"))
    if payload.get("model") != "cheap-model":
        raise AssertionError("LLM request should include the configured model")
    return httpx.Response(
        200,
        json={"choices": [{"message": {"content": '{"text":"自然生成的回答。"}'}}]},
    )

settings = LLMSettings(
    enabled=True,
    provider="openai_compatible",
    base_url="https://example.invalid/v1",
    api_key="test-key",
    model="cheap-model",
    max_retries=0,
    retry_delay_seconds=0,
)
client = LLMClient(settings, transport=httpx.MockTransport(success_handler))
result = client.generate_json_text("system", {"task": "test"}, fallback)
if not result.used_llm or result.text != "自然生成的回答。":
    raise SystemExit("OpenAI-compatible adapter should parse JSON text")
status = client.status()
if "api_key" in status or "test-key" in json.dumps(status):
    raise SystemExit("LLM status must never expose the API key")

def deepseek_handler(request: httpx.Request) -> httpx.Response:
    payload = json.loads(request.content.decode("utf-8"))
    if payload.get("thinking") != {"type": "disabled"}:
        raise AssertionError("DeepSeek rewrite requests should disable thinking mode")
    if payload.get("response_format") != {"type": "json_object"}:
        raise AssertionError("DeepSeek requests should enforce JSON object output")
    return httpx.Response(
        200,
        json={"choices": [{"message": {"content": '{"text":"DeepSeek JSON 回答。"}'}}]},
    )

deepseek_settings = LLMSettings(
    enabled=True,
    provider="deepseek",
    base_url="https://api.deepseek.com",
    api_key="test-key",
    model="deepseek-v4-flash",
    max_retries=0,
    retry_delay_seconds=0,
)
deepseek_client = LLMClient(
    deepseek_settings,
    transport=httpx.MockTransport(deepseek_handler),
)
deepseek_result = deepseek_client.generate_json_text("system JSON", {}, fallback)
if not deepseek_result.used_llm or deepseek_result.text != "DeepSeek JSON 回答。":
    raise SystemExit("DeepSeek adapter should use non-thinking JSON mode")

flaky_attempts = {"count": 0}

def flaky_handler(_request: httpx.Request) -> httpx.Response:
    flaky_attempts["count"] += 1
    if flaky_attempts["count"] == 1:
        return httpx.Response(200, json={"choices": [{"message": {"content": "not-json"}}]})
    return httpx.Response(
        200,
        json={"choices": [{"message": {"content": '{"text":"重试成功。"}'}}]},
    )

retry_settings = LLMSettings(
    enabled=True,
    provider="deepseek",
    base_url="https://api.deepseek.com",
    api_key="test-key",
    model="deepseek-v4-flash",
    max_retries=1,
    retry_delay_seconds=0,
)
retry_client = LLMClient(retry_settings, transport=httpx.MockTransport(flaky_handler))
retry_result = retry_client.generate_json_text("system JSON", {}, fallback)
if not retry_result.used_llm or retry_result.text != "重试成功。" or flaky_attempts["count"] != 2:
    raise SystemExit("invalid JSON should retry once before using the rule fallback")

def malformed_handler(_request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": "not-json"}}]})

malformed_client = LLMClient(settings, transport=httpx.MockTransport(malformed_handler))
malformed_result = malformed_client.generate_json_text("system", {}, fallback)
if malformed_result.used_llm or malformed_result.text != fallback:
    raise SystemExit("invalid LLM JSON should use the rule fallback")

def limited_handler(_request: httpx.Request) -> httpx.Response:
    return httpx.Response(429, json={"error": {"message": "rate limited"}})

limited_client = LLMClient(settings, transport=httpx.MockTransport(limited_handler))
limited_result = limited_client.generate_json_text("system", {}, fallback)
if limited_result.used_llm or limited_result.text != fallback:
    raise SystemExit("LLM rate limits should use the rule fallback")

print("LLM adapter smoke test passed")
'''
    run_command(
        [str(python_bin), "-c", smoke_code],
        cwd=BACKEND_DIR,
        fail_message="LLM adapter smoke test failed",
    )
    print("[OK] LLM adapter success, mock, safety, and fallback paths work.")


def check_backend_search() -> None:
    python_bin = BACKEND_VENV_PYTHON if BACKEND_VENV_PYTHON.exists() else Path(sys.executable)
    smoke_code = """
from app.main import reload_config, search_knowledge
from app.main import get_relationship_hint, get_relationship_level
from app.rag import LocalVectorIndex
import os

reload_config()
cases = [
    ("Guide", "Godot 玩家移动怎么做"),
    ("Guide", "Top-K 检索是什么"),
    ("Archivist", "记忆文件保存在哪里"),
    ("Archivist", "资料馆是什么"),
]

for npc_name, message in cases:
    result = search_knowledge(npc_name=npc_name, message=message, limit=3)
    if not result.matched or not result.results:
        raise SystemExit(f"{npc_name} did not match knowledge for: {message}")

semantic_result = search_knowledge(
    npc_name="梅长苏",
    message="有什么办法确认别人属于哪个阵营",
    limit=5,
)
if semantic_result.retrieval_mode == "hybrid":
    semantic_titles = [result.item.title for result in semantic_result.results]
    if "预言家查验能力" not in semantic_titles:
        raise SystemExit("hybrid retrieval should semantically recall the seer-check knowledge")
elif semantic_result.retrieval_mode != "keyword":
    raise SystemExit(f"unknown retrieval mode: {semantic_result.retrieval_mode}")

os.environ["AGENT_TOWN_DISABLE_VECTOR_RAG"] = "1"
fallback_index = LocalVectorIndex()
fallback_index.configure(["预言家每晚可以查验一名玩家。"])
if fallback_index.search("怎么确认阵营"):
    raise SystemExit("disabled vector RAG should not return vector scores")
if fallback_index.status()["mode"] != "keyword":
    raise SystemExit("disabled vector RAG should stay in keyword mode")
del os.environ["AGENT_TOWN_DISABLE_VECTOR_RAG"]

expected_relationships = {
    1: "初次见面",
    2: "熟悉",
    4: "信任",
    7: "老朋友",
}
for memory_count, expected_level in expected_relationships.items():
    actual_level = get_relationship_level(memory_count)
    if actual_level != expected_level:
        raise SystemExit(f"relationship level mismatch: {memory_count} -> {actual_level}")

relationship_hints = []
for memory_count in expected_relationships:
    relationship_hint = get_relationship_hint(memory_count)
    if not relationship_hint:
        raise SystemExit(f"missing relationship hint for: {memory_count}")
    relationship_hints.append(relationship_hint)

if len(set(relationship_hints)) != len(relationship_hints):
    raise SystemExit("relationship hints should differ by relationship stage")

print("backend search matched", len(cases), "cases")
"""
    run_command(
        [str(python_bin), "-c", smoke_code],
        cwd=BACKEND_DIR,
        fail_message=(
            "backend search smoke test failed. "
            "If dependencies are missing, run: cd backend && source .venv/bin/activate && pip install -r requirements.txt"
        ),
    )
    print("[OK] Backend knowledge search works.")


def check_wolf_game_start() -> None:
    python_bin = BACKEND_VENV_PYTHON if BACKEND_VENV_PYTHON.exists() else Path(sys.executable)
    smoke_code = """
from collections import Counter
from pathlib import Path

from fastapi import HTTPException

import app.main as main_module
from app.llm import LLMGeneration
from app.main import DayMeetingState, EliminationState, GAME_STORE, GameStartRequest
from app.main import HunterShotRequest
from app.main import NightActionRequest, NightActionState, NightResolutionState, NightResolveRequest
from app.main import EndFreeActivityRequest, NpcSpeechRequest
from app.main import PlayerSpeechRequest
from app.main import PlayerVoteRequest, PrivateChatRequest, PrivateConversationState
from app.main import BadgeTransferRequest, SheriffElectionState, SheriffMeetingOrderRequest, SheriffNominationRequest
from app.main import SheriffSignupRequest, SheriffSpeechRequest, SheriffVoteRequest
from app.main import SheriffWithdrawalRequest, SpeechState, VoteState
from app.main import build_public_decision_rag_context, end_free_activity
from app.main import generate_npc_sheriff_campaign_speech, generate_npc_speech, private_chat
from app.main import get_game_summary, get_wolf_game_state, initialize_social_state
from app.main import resolve_hunter_shot, resolve_night
from app.main import start_wolf_game, submit_night_action
from app.main import submit_and_resolve_all_votes, submit_and_resolve_sheriff_vote
from app.main import submit_player_sheriff_speech, submit_player_speech
from app.main import submit_sheriff_meeting_order, submit_sheriff_nomination
from app.main import submit_badge_transfer, submit_sheriff_signup, submit_sheriff_withdrawal

forced_witch_response = start_wolf_game(
    GameStartRequest(player_name="女巫测试玩家", player_role="witch")
)
forced_witch_state = GAME_STORE[forced_witch_response.game_id]
forced_witch_player = forced_witch_state.characters[0]
if forced_witch_player.role != "witch":
    raise SystemExit("specified player role should assign witch to the player")
if Counter(character.role for character in forced_witch_state.characters) != Counter(main_module.DEFAULT_WOLF_ROLES):
    raise SystemExit("specified player role must preserve the twelve-player role pool")
witch_private = get_wolf_game_state(forced_witch_response.game_id).player_private_info
if not witch_private.witch_antidote_available or not witch_private.witch_poison_available:
    raise SystemExit("player witch should receive both potion resources")

response = start_wolf_game(GameStartRequest(player_name="测试玩家"))
if response.day != 1 or response.phase != "NIGHT":
    raise SystemExit("new game should start at day 1 NIGHT")
if len(response.characters) != 12:
    raise SystemExit("new game should create 12 characters")

player_view = next(character for character in response.characters if character.is_player)
npc_views = [character for character in response.characters if not character.is_player]
game_state = GAME_STORE[response.game_id]
player = next(character for character in game_state.characters if character.is_player)
if player_view.role_visible_to_player is None:
    raise SystemExit("player role should be visible to player")
visible_npc_ids = {
    character.id
    for character in npc_views
    if character.role_visible_to_player is not None
}
if player_view.role_visible_to_player == "werewolf":
    expected_visible_npc_ids = {
        character.id
        for character in game_state.characters
        if character.role == "werewolf" and not character.is_player
    }
    if visible_npc_ids != expected_visible_npc_ids:
        raise SystemExit("werewolf player should see exactly the three wolf teammates")
elif visible_npc_ids:
    raise SystemExit("non-werewolf player should not see NPC roles")

role_counts = Counter(character.role for character in game_state.characters)
expected_roles = {
    "werewolf": 4,
    "seer": 1,
    "witch": 1,
    "hunter": 1,
    "guard": 1,
    "villager": 4,
}
if dict(role_counts) != expected_roles:
    raise SystemExit(f"unexpected role assignment: {role_counts}")

state_response = get_wolf_game_state(response.game_id)
if state_response.player_private_info.role != player_view.role_visible_to_player:
    raise SystemExit("state response should keep player private role")
if len(state_response.characters) != 12:
    raise SystemExit("state response should include 12 character views")
if not state_response.public_logs:
    raise SystemExit("state response should include public logs")
if player.role == "werewolf" and len(state_response.player_private_info.wolf_teammates) != 3:
    raise SystemExit("werewolf private state should list three teammates")

alive_targets = [
    character
    for character in game_state.characters
    if character.alive and character.id != player.id
]
stable_night_target = next(
    character
    for character in alive_targets
    if character.role == "villager"
)
game_state.night_actions = [
    NightActionState(
        day=1,
        actor_id=character.id,
        action_type="werewolf_kill" if character.role == "werewolf" else "none",
        target_id=stable_night_target.id if character.role == "werewolf" else None,
    )
    for character in game_state.characters
    if not character.is_player
]

if player.role == "werewolf":
    target = stable_night_target
    action = NightActionRequest(
        game_id=response.game_id,
        character_id=player.id,
        action_type="werewolf_kill",
        target_id=target.id,
    )
elif player.role == "seer":
    target = alive_targets[0]
    action = NightActionRequest(
        game_id=response.game_id,
        character_id=player.id,
        action_type="seer_check",
        target_id=target.id,
    )
elif player.role == "guard":
    target = alive_targets[0]
    action = NightActionRequest(
        game_id=response.game_id,
        character_id=player.id,
        action_type="guard_protect",
        target_id=target.id,
    )
elif player.role == "witch":
    action = NightActionRequest(
        game_id=response.game_id,
        character_id=player.id,
        action_type="none",
        target_id=None,
    )
else:
    action = NightActionRequest(
        game_id=response.game_id,
        character_id=player.id,
        action_type="none",
        target_id=None,
    )

action_response = submit_night_action(action)
if not action_response.success:
    raise SystemExit("night action should be accepted")

resolve_response = resolve_night(NightResolveRequest(game_id=response.game_id))
if resolve_response.game_id != response.game_id:
    raise SystemExit("night resolve should keep game id")
if GAME_STORE[response.game_id].phase != "SHERIFF_SIGNUP":
    raise SystemExit("first night should enter SHERIFF_SIGNUP before the day meeting")
if not resolve_response.public_message:
    raise SystemExit("night resolve should return a public message")
if player.role == "seer" and "seer_check" not in resolve_response.player_private_result:
    raise SystemExit("seer player should receive private check result")

expected_npc_names = [
    "梅西", "C罗", "周深", "梅长苏", "塞尔达", "小骑士",
    "大黄蜂", "喜羊羊", "懒羊羊", "洛洛", "奇异博士",
]
if [character.name for character in game_state.characters[1:]] != expected_npc_names:
    raise SystemExit("wolf game should use the eleven fixed town NPC names")

signup_response = submit_sheriff_signup(
    SheriffSignupRequest(
        game_id=response.game_id,
        character_id=player.id,
        run_for_sheriff=True,
    )
)
if not signup_response.success or player.id not in signup_response.candidates:
    raise SystemExit("player sheriff signup should add the player to candidate list")
if game_state.phase != "SHERIFF_SPEECH":
    raise SystemExit("completed sheriff signup should enter SHERIFF_SPEECH")

sheriff_speech_order = list(game_state.sheriff_election.speech_order)
while game_state.phase == "SHERIFF_SPEECH":
    current_speaker_id = main_module.get_current_sheriff_speaker_id(game_state)
    current_speaker = main_module.get_character(game_state, current_speaker_id)
    if current_speaker.is_player:
        campaign_response = submit_player_sheriff_speech(
            SheriffSpeechRequest(
                game_id=response.game_id,
                character_id=current_speaker.id,
                speech="我上警竞选，会结合后续票型给出判断。",
            )
        )
    else:
        campaign_response = generate_npc_sheriff_campaign_speech(
            SheriffSpeechRequest(
                game_id=response.game_id,
                character_id=current_speaker.id,
            )
        )
        if not campaign_response.speech.evidence_titles:
            raise SystemExit("NPC sheriff speech should expose public RAG evidence")
    if campaign_response.speech.character_id != current_speaker.id:
        raise SystemExit("sheriff speech should follow the candidate order")

if game_state.phase != "SHERIFF_WITHDRAWAL":
    raise SystemExit("sheriff speeches should always enter the withdrawal phase")
withdraw_response = submit_sheriff_withdrawal(
    SheriffWithdrawalRequest(
        game_id=response.game_id,
        character_id=player.id,
        withdraw=False,
    )
)
if not withdraw_response.success:
    raise SystemExit("withdrawal phase should accept the player's stay decision")
if player.id in game_state.sheriff_election.withdrawn:
    raise SystemExit("continue campaign should keep the player in the active sheriff candidates")

while game_state.phase in {"SHERIFF_VOTE", "SHERIFF_RUNOFF_SPEECH", "SHERIFF_RUNOFF_VOTE"}:
    if game_state.phase == "SHERIFF_RUNOFF_SPEECH":
        current_speaker_id = main_module.get_current_sheriff_speaker_id(game_state)
        current_speaker = main_module.get_character(game_state, current_speaker_id)
        if current_speaker.is_player:
            submit_player_sheriff_speech(
                SheriffSpeechRequest(
                    game_id=response.game_id,
                    character_id=current_speaker.id,
                    speech="PK 阶段我继续坚持自己的警徽流判断。",
                )
            )
        else:
            generate_npc_sheriff_campaign_speech(
                SheriffSpeechRequest(
                    game_id=response.game_id,
                    character_id=current_speaker.id,
                )
            )
        continue
    active_candidates = main_module.get_active_sheriff_candidates(game_state)
    player_can_vote = player.alive and player.id not in active_candidates
    sheriff_vote_response = submit_and_resolve_sheriff_vote(
        SheriffVoteRequest(
            game_id=response.game_id,
            character_id=player.id,
            target_id=active_candidates[0] if player_can_vote else None,
        )
    )
    if not sheriff_vote_response.ballots:
        raise SystemExit("sheriff vote should reveal all eligible ballots together")

if game_state.sheriff_election is None or not game_state.sheriff_election.completed:
    raise SystemExit("sheriff election should finish before the town meeting")
if game_state.phase == "MEETING_ORDER":
    order_view = get_wolf_game_state(response.game_id).sheriff
    if not order_view.order_options:
        raise SystemExit("player sheriff should receive left/right meeting-order choices")
    submit_sheriff_meeting_order(
        SheriffMeetingOrderRequest(
            game_id=response.game_id,
            character_id=player.id,
            side="left",
        )
    )
if game_state.phase != "DAY_MEETING":
    raise SystemExit("sheriff election should continue into DAY_MEETING")

meeting_state = get_wolf_game_state(response.game_id).meeting
alive_ids = {character.id for character in game_state.characters if character.alive}
if set(meeting_state.order) != alive_ids or len(meeting_state.order) != len(alive_ids):
    raise SystemExit("meeting order should contain each alive character exactly once")
if meeting_state.direction not in {"clockwise", "counterclockwise"}:
    raise SystemExit("meeting direction should be clockwise or counterclockwise")

spoken_order = []
player_speech_target = next(
    (character for character in game_state.characters if character.alive and not character.is_player),
    None,
)
while game_state.phase == "DAY_MEETING":
    current_speaker_id = game_state.meeting.order[game_state.meeting.current_index]
    current_speaker = game_state.characters[current_speaker_id - 1]
    spoken_order.append(current_speaker_id)

    if current_speaker.is_player:
        speech_text = "目前信息还少，我先听大家发言。"
        if player_speech_target is not None:
            speech_text = f"我觉得{player_speech_target.id}号很可疑，今天需要解释一下。"
        speech_response = submit_player_speech(
            PlayerSpeechRequest(
                game_id=response.game_id,
                character_id=current_speaker.id,
                speech=speech_text,
            )
        )
        if player_speech_target is not None and player_speech_target.id not in speech_response.parsed.mentioned_characters:
            raise SystemExit("player speech parser should detect mentioned character")
    else:
        npc_speech_response = generate_npc_speech(
            NpcSpeechRequest(
                game_id=response.game_id,
                character_id=current_speaker.id,
            )
        )
        if npc_speech_response.speech.character_id != current_speaker.id:
            raise SystemExit("only the current NPC speaker should produce a speech")
        if not npc_speech_response.speech.evidence_titles:
            raise SystemExit("NPC public speech should expose RAG evidence titles")
        if not any(marker in npc_speech_response.speech.speech for marker in ["参考", "结合知识"]):
            raise SystemExit("NPC public speech should incorporate retrieved evidence")
        if "\ufffd" in npc_speech_response.speech.speech:
            raise SystemExit("NPC public speech must not contain Unicode replacement characters")
        if any("私有记忆" in title for title in npc_speech_response.speech.evidence_titles):
            raise SystemExit("NPC public speech must not expose private-memory evidence")
        if npc_speech_response.speech.llm_used:
            raise SystemExit("default wolf-game smoke test should not call a real LLM")

if spoken_order != meeting_state.order:
    raise SystemExit("characters should speak in the generated meeting order")
if game_state.phase == "SHERIFF_NOMINATION":
    nomination_target = next(
        character
        for character in game_state.characters
        if character.alive and character.id != player.id
    )
    submit_sheriff_nomination(
        SheriffNominationRequest(
            game_id=response.game_id,
            character_id=player.id,
            target_id=nomination_target.id,
        )
    )
if game_state.phase != "FREE_ACTIVITY":
    raise SystemExit("completed meeting and sheriff nomination should enter FREE_ACTIVITY")
if player.alive and player_speech_target is not None:
    state_after_speech = get_wolf_game_state(response.game_id)
    target_view = next(
        character
        for character in state_after_speech.characters
        if character.id == player_speech_target.id
    )
    if target_view.suspicion_score <= 0:
        raise SystemExit("mentioned character should expose a positive suspicion score")

free_activity_response = end_free_activity(EndFreeActivityRequest(game_id=response.game_id))
if not free_activity_response.success or game_state.phase != "VOTE":
    raise SystemExit("ending free activity should enter VOTE")

social_snapshot = {}
for character in game_state.characters:
    if character.is_player:
        continue
    social_snapshot[character.id] = {
        "suspicion": dict(character.suspicion),
        "trust": {
            character_id: float(relationship.get("trust", 0.5))
            for character_id, relationship in character.relationships.items()
        },
    }

vote_target_id = None
if player.alive:
    if game_state.sheriff_id == player.id and game_state.meeting is not None:
        vote_target_id = game_state.meeting.nomination_target_id
    if vote_target_id is None:
        vote_target_id = next(
            character.id
            for character in game_state.characters
            if character.alive and character.id != player.id
        )
sheriff_before_vote = game_state.sheriff_id
vote_resolve_response = submit_and_resolve_all_votes(
    PlayerVoteRequest(
        game_id=response.game_id,
        character_id=player.id,
        target_id=vote_target_id,
        reason="这是玩家同时提交的投票理由。",
    )
)
if not vote_resolve_response.public_message:
    raise SystemExit("vote resolve should return a public message")
if not vote_resolve_response.ballots or not vote_resolve_response.vote_totals:
    raise SystemExit("combined vote should return ballot summary and weighted totals")
for vote in vote_resolve_response.ballots:
    if vote.voter_id != player.id and not vote.evidence_titles:
        raise SystemExit("NPC vote reason should expose RAG evidence titles")
    if "\ufffd" in vote.reason or any("私有记忆" in title for title in vote.evidence_titles):
        raise SystemExit("combined vote evidence must be clean and public-safe")
if sheriff_before_vote is not None:
    sheriff_ballot = next(
        (vote for vote in vote_resolve_response.ballots if vote.voter_id == sheriff_before_vote),
        None,
    )
    if sheriff_ballot is not None and sheriff_ballot.weight != 1.5:
        raise SystemExit("sheriff ballot should count as 1.5 votes")
if GAME_STORE[response.game_id].phase not in {"NIGHT", "GAME_OVER"}:
    raise SystemExit("vote resolve should move game to next NIGHT or GAME_OVER")

social_changed = False
for character in GAME_STORE[response.game_id].characters:
    if character.is_player:
        continue
    before = social_snapshot.get(character.id)
    if before is None:
        continue
    current_trust = {
        character_id: float(relationship.get("trust", 0.5))
        for character_id, relationship in character.relationships.items()
    }
    if before["suspicion"] != character.suspicion or before["trust"] != current_trust:
        social_changed = True
        break
if not social_changed:
    raise SystemExit("vote resolve should update NPC suspicion or trust state")

state_after_vote = get_wolf_game_state(response.game_id)
if any(character.trust_to_player is None for character in state_after_vote.characters if not character.is_player):
    raise SystemExit("NPC character views should expose trust_to_player")

def make_rule_test_game(roles):
    if len(roles) > 12:
        raise SystemExit("rule test role list cannot exceed 12 characters")
    expanded_roles = list(roles) + ["villager"] * (12 - len(roles))
    response = start_wolf_game(GameStartRequest(player_name="规则测试"))
    game_state = GAME_STORE[response.game_id]
    for index, role in enumerate(expanded_roles):
        character = game_state.characters[index]
        character.role = role
        character.camp = "werewolf" if role == "werewolf" else "good"
        character.alive = True
        character.memory_summary = ""
    initialize_social_state(game_state.characters)
    game_state.day = 1
    game_state.phase = "NIGHT"
    game_state.night_actions = []
    game_state.votes = []
    game_state.speeches = []
    game_state.private_conversations = []
    game_state.eliminations = []
    game_state.pending_first_night_eliminations = []
    game_state.first_night_result_pending = False
    game_state.night_resolutions = []
    game_state.hunter_shots = []
    game_state.public_claims = []
    game_state.public_logs = []
    game_state.sheriff_id = None
    game_state.sheriff_election = SheriffElectionState(completed=True)
    game_state.sheriff_events = []
    game_state.badge_destroyed = True
    game_state.meeting_order_anchor_id = None
    game_state.meeting_order_anchor_type = ""
    game_state.pending_badge_transfer_from_id = None
    game_state.pending_badge_continuation = ""
    game_state.wolf_checked_wolf_used = False
    game_state.llm_validation_failures = []
    game_state.pending_hunter_id = None
    game_state.pending_hunter_trigger = ""
    game_state.pending_hunter_continuation = ""
    game_state.winner = None
    game_state.winner_reason = ""
    game_state.wolf_fake_seer_id = main_module.choose_designated_fake_seer(game_state.characters)
    main_module.initialize_role_resources(game_state)
    player = game_state.characters[0]
    game_state.player_private_info = main_module.build_player_private_info_dict(game_state)
    return game_state

saved_first_night_state = make_rule_test_game(
    ["witch", "villager", "werewolf", "villager", "seer", "hunter", "guard"]
)
saved_first_night_state.sheriff_election = None
saved_first_night_state.badge_destroyed = False
saved_first_night_state.night_actions = [
    NightActionState(day=1, actor_id=1, action_type="witch_save", target_id=4),
    NightActionState(day=1, actor_id=3, action_type="werewolf_kill", target_id=4),
    NightActionState(day=1, actor_id=5, action_type="none", target_id=None),
    NightActionState(day=1, actor_id=6, action_type="none", target_id=None),
    NightActionState(day=1, actor_id=7, action_type="none", target_id=None),
]
saved_first_night_result = resolve_night(
    NightResolveRequest(game_id=saved_first_night_state.game_id)
)
if not saved_first_night_result.result_pending or saved_first_night_result.dead_characters:
    raise SystemExit("first-night result must stay hidden until the sheriff election finishes")
if saved_first_night_state.pending_first_night_eliminations:
    raise SystemExit("a witch-saved target must not enter the pending elimination list")
if not all(character.alive for character in saved_first_night_state.characters):
    raise SystemExit("a successful first-night save must not eliminate any unrelated character")

pending_first_night_state = make_rule_test_game(
    ["villager", "villager", "werewolf", "villager", "seer", "witch", "hunter", "guard"]
)
pending_first_night_state.sheriff_election = None
pending_first_night_state.badge_destroyed = False
pending_first_night_state.night_actions = [
    NightActionState(day=1, actor_id=3, action_type="werewolf_kill", target_id=4),
    NightActionState(day=1, actor_id=5, action_type="none", target_id=None),
    NightActionState(day=1, actor_id=6, action_type="none", target_id=None),
    NightActionState(day=1, actor_id=7, action_type="none", target_id=None),
    NightActionState(day=1, actor_id=8, action_type="none", target_id=None),
]
pending_result = resolve_night(
    NightResolveRequest(game_id=pending_first_night_state.game_id)
)
if pending_result.dead_characters or not pending_first_night_state.characters[3].alive:
    raise SystemExit("first-night victim must remain in play during the sheriff election")
if [item.character_id for item in pending_first_night_state.pending_first_night_eliminations] != [4]:
    raise SystemExit("first-night pending result should contain only the legally attacked target")
main_module.finish_sheriff_election(
    pending_first_night_state,
    2,
    "2号测试警长当选。",
)
if pending_first_night_state.characters[3].alive:
    raise SystemExit("pending first-night victim should be eliminated after the election")
if any(not character.alive for character in pending_first_night_state.characters if character.id != 4):
    raise SystemExit("night resolution must never eliminate an unrelated character")
night_elimination = pending_first_night_state.eliminations[-1]
if (
    night_elimination.source_action != "werewolf_kill"
    or night_elimination.source_actor_ids != [3]
    or night_elimination.source_target_id != 4
):
    raise SystemExit("every elimination should keep a legal, traceable source")

first_night_sheriff_hunter_state = make_rule_test_game(
    ["hunter", "villager", "werewolf", "villager", "seer", "witch", "guard"]
)
first_night_sheriff_hunter_state.sheriff_election = None
first_night_sheriff_hunter_state.badge_destroyed = False
first_night_sheriff_hunter_state.night_actions = [
    NightActionState(day=1, actor_id=3, action_type="werewolf_kill", target_id=1),
    NightActionState(day=1, actor_id=5, action_type="none", target_id=None),
    NightActionState(day=1, actor_id=6, action_type="none", target_id=None),
    NightActionState(day=1, actor_id=7, action_type="none", target_id=None),
]
resolve_night(NightResolveRequest(game_id=first_night_sheriff_hunter_state.game_id))
main_module.finish_sheriff_election(
    first_night_sheriff_hunter_state,
    1,
    "1号玩家当选警长。",
)
if first_night_sheriff_hunter_state.phase != "HUNTER_SHOT":
    raise SystemExit("first-night sheriff hunter must resolve the shot before badge transfer")
resolve_hunter_shot(
    HunterShotRequest(
        game_id=first_night_sheriff_hunter_state.game_id,
        character_id=1,
        target_id=2,
    )
)
if first_night_sheriff_hunter_state.phase != "BADGE_TRANSFER":
    raise SystemExit("first-night sheriff hunter should transfer the badge after shooting")
submit_badge_transfer(
    BadgeTransferRequest(
        game_id=first_night_sheriff_hunter_state.game_id,
        character_id=1,
        target_id=4,
    )
)
if (
    first_night_sheriff_hunter_state.sheriff_id != 4
    or first_night_sheriff_hunter_state.phase != "DAY_MEETING"
):
    raise SystemExit("first-night badge transfer should finish before winner and meeting checks")

withdrawn_vote_state = make_rule_test_game(
    ["villager", "seer", "werewolf", "villager", "witch", "hunter", "guard"]
)
withdrawn_vote_state.phase = "SHERIFF_VOTE"
withdrawn_vote_state.sheriff_election = SheriffElectionState(
    candidates=[1, 2, 3],
    withdrawn=[1],
    speech_order=[1, 2, 3],
)
withdrawn_vote_view = main_module.build_sheriff_view(withdrawn_vote_state)
if withdrawn_vote_view.player_can_vote or "退水者" not in withdrawn_vote_view.player_vote_ineligible_reason:
    raise SystemExit("a withdrawn candidate must remain ineligible for sheriff voting")
withdrawn_vote_result = submit_and_resolve_sheriff_vote(
    SheriffVoteRequest(
        game_id=withdrawn_vote_state.game_id,
        character_id=1,
        target_id=None,
    )
)
candidate_voters = {ballot.voter_id for ballot in withdrawn_vote_result.ballots} & {1, 2, 3}
if candidate_voters:
    raise SystemExit("all sheriff-election participants, including withdrawn candidates, must not vote")

class StubLLMClient:
    def __init__(self):
        self.public_attempts = 0

    def status(self):
        return {
            "enabled": True,
            "provider": "stub",
            "model": "stub-model",
            "configured": True,
            "base_url": "",
        }

    def generate_json_text(self, _system_prompt, context, fallback_text, max_attempts=None):
        if context.get("task") == "rewrite_public_speech":
            self.public_attempts += 1
            target = context.get("focus_target") or {}
            target_name = target.get("name", "目标")
            if self.public_attempts == 1:
                text = "结合公开证据，我暂时保留意见。"
            else:
                text = f"结合公开证据，我会继续观察{target_name}的解释。"
        else:
            text = fallback_text.replace("我会", "我会认真地", 1)
        return LLMGeneration(
            text=text,
            used_llm=True,
            provider="stub",
            model="stub-model",
        )

original_llm_client = main_module.LLM_CLIENT
recovered_validation_log_path = Path("/tmp/agent-town-llm-recovered-smoke.jsonl")
original_recovered_validation_log_path = main_module.LLM_VALIDATION_LOG_FILE
try:
    recovered_validation_log_path.unlink(missing_ok=True)
    main_module.LLM_VALIDATION_LOG_FILE = recovered_validation_log_path
    llm_game_state = make_rule_test_game(
        ["villager", "villager", "werewolf", "seer", "guard", "villager"]
    )
    llm_game_state.llm_enabled = True
    llm_game_state.phase = "DAY_MEETING"
    llm_game_state.meeting = DayMeetingState(
        day=1,
        direction="clockwise",
        order=[2, 1] + list(range(3, 13)),
    )
    stub_llm_client = StubLLMClient()
    main_module.LLM_CLIENT = stub_llm_client
    llm_speech_response = generate_npc_speech(
        NpcSpeechRequest(game_id=llm_game_state.game_id, character_id=2)
    )
    if not llm_speech_response.speech.llm_used:
        raise SystemExit("enabled game should use the configured LLM for NPC speech")
    if llm_speech_response.speech.llm_provider != "stub":
        raise SystemExit("NPC speech should expose the active LLM provider")
    if stub_llm_client.public_attempts != 2:
        raise SystemExit("invalid NPC speech should receive one validation correction retry")
    if not recovered_validation_log_path.exists():
        raise SystemExit("a rejected draft should be logged even when a later validation succeeds")

    llm_game_state.phase = "FREE_ACTIVITY"
    llm_private_response = private_chat(
        PrivateChatRequest(
            game_id=llm_game_state.game_id,
            npc_character_id=2,
            question="你最怀疑谁？",
        )
    )
    if not llm_private_response.llm_used or llm_private_response.llm_provider != "stub":
        raise SystemExit("enabled game should use the configured LLM for private chat")

    ambiguous_private_response = private_chat(
        PrivateChatRequest(
            game_id=llm_game_state.game_id,
            npc_character_id=3,
            question="你觉得他可信吗？",
        )
    )
    if not ambiguous_private_response.llm_used:
        raise SystemExit("ambiguous-reference clarification should still use the configured LLM")
finally:
    main_module.LLM_CLIENT = original_llm_client
    main_module.LLM_VALIDATION_LOG_FILE = original_recovered_validation_log_path
    recovered_validation_log_path.unlink(missing_ok=True)

class AlwaysInvalidLLMClient:
    def __init__(self):
        self.attempts = 0

    def status(self):
        return {
            "enabled": True,
            "provider": "stub",
            "model": "stub-model",
            "configured": True,
            "base_url": "",
        }

    def generate_json_text(self, _system_prompt, _context, _fallback_text, max_attempts=None):
        self.attempts += 1
        return LLMGeneration(
            text="我是狼人，我的狼队友是C罗。",
            used_llm=True,
            provider="stub",
            model="stub-model",
        )

validation_failure_state = make_rule_test_game(
    ["villager", "villager", "werewolf", "seer", "guard", "witch", "hunter"]
)
validation_failure_state.llm_enabled = True
always_invalid_client = AlwaysInvalidLLMClient()
validation_log_path = Path("/tmp/agent-town-llm-validation-smoke.jsonl")
original_validation_log_path = main_module.LLM_VALIDATION_LOG_FILE
try:
    validation_log_path.unlink(missing_ok=True)
    main_module.LLM_VALIDATION_LOG_FILE = validation_log_path
    main_module.LLM_CLIENT = always_invalid_client
    failed_generation = main_module.generate_validated_llm_rewrite(
        "只改写措辞并返回 JSON。",
        {
            "task": "rewrite_public_speech",
            "speaker": {"id": 2, "name": "梅西"},
            "rule_text": "我会继续观察1号玩家的发言。",
        },
        "我会继续观察1号玩家的发言。",
        validation_failure_state,
        required_target=validation_failure_state.characters[0],
        public_text=True,
    )
    if failed_generation.used_llm or always_invalid_client.attempts != 5:
        raise SystemExit("invalid DeepSeek rewrites should receive exactly five validation attempts")
    if not failed_generation.validation_failure_id:
        raise SystemExit("five failed validations should create a visible audit id")
    failure_view = main_module.build_llm_validation_failure_view(
        validation_failure_state,
        failed_generation.validation_failure_id,
    )
    if failure_view is None or len(failure_view.attempts) != 5:
        raise SystemExit("validation failure view should expose all five attempts")
    if not all("狼队友" in attempt.text for attempt in failure_view.attempts):
        raise SystemExit("debug in-game validation audit should expose every rejected raw output")
    full_failure_view = main_module.build_llm_validation_failure_view(
        validation_failure_state,
        failed_generation.validation_failure_id,
        reveal_sensitive=True,
    )
    if full_failure_view is None or not any("狼队友" in attempt.text for attempt in full_failure_view.attempts):
        raise SystemExit("post-game validation audit should retain the original DeepSeek output")
    if not validation_log_path.exists():
        raise SystemExit("validation failures should also be written to the backend JSONL log")
finally:
    main_module.LLM_CLIENT = original_llm_client
    main_module.LLM_VALIDATION_LOG_FILE = original_validation_log_path
    validation_log_path.unlink(missing_ok=True)

meeting_influence_state = make_rule_test_game(
    ["villager", "villager", "werewolf", "villager", "guard", "seer"]
)
meeting_influence_state.phase = "DAY_MEETING"
meeting_influence_state.meeting = DayMeetingState(
    day=1,
    direction="clockwise",
    order=list(range(1, 13)),
)
submit_player_speech(
    PlayerSpeechRequest(
        game_id=meeting_influence_state.game_id,
        character_id=1,
        speech="我觉得3号很可疑。",
    )
)
later_listener = meeting_influence_state.characters[3]
before_npc_speech = later_listener.suspicion.get("3", 0)
generate_npc_speech(
    NpcSpeechRequest(
        game_id=meeting_influence_state.game_id,
        character_id=2,
    )
)
if later_listener.suspicion.get("3", 0) <= before_npc_speech:
    raise SystemExit("an earlier NPC speech should affect later NPC suspicion")

meeting_influence_state.phase = "FREE_ACTIVITY"
private_npc = meeting_influence_state.characters[1]
private_target = meeting_influence_state.characters[2]
public_logs_before_private_chat = list(meeting_influence_state.public_logs)
suspicion_before_private_chat = private_npc.suspicion.get(str(private_target.id), 0)
first_private_response = private_chat(
    PrivateChatRequest(
        game_id=meeting_influence_state.game_id,
        npc_character_id=private_npc.id,
        question=f"我觉得{private_target.id}号很可疑，我们一起合作。",
    )
)
if not first_private_response.effective:
    raise SystemExit("the first daily private question should affect NPC decisions")
if private_npc.suspicion.get(str(private_target.id), 0) <= suspicion_before_private_chat:
    raise SystemExit("an effective private question should update the target NPC suspicion")
if meeting_influence_state.public_logs != public_logs_before_private_chat:
    raise SystemExit("private chat must not be written to public logs")
if first_private_response.retrieval_mode not in {"hybrid", "keyword"}:
    raise SystemExit("private chat should expose the active retrieval mode")
if any("私有记忆" in title for title in first_private_response.knowledge_titles):
    raise SystemExit("private RAG source titles must not leak private memory")
private_view = next(
    character
    for character in get_wolf_game_state(meeting_influence_state.game_id).characters
    if character.id == private_npc.id
)
if not private_view.private_question_used_today:
    raise SystemExit("character view should expose that today's effective private question was used")

decision_snapshot = (
    dict(private_npc.suspicion),
    dict(private_npc.relationships[str(meeting_influence_state.player_character_id)]),
    private_npc.memory_summary,
)
second_private_response = private_chat(
    PrivateChatRequest(
        game_id=meeting_influence_state.game_id,
        npc_character_id=private_npc.id,
        question=f"你再想想{private_target.id}号。",
    )
)
if second_private_response.effective:
    raise SystemExit("a second private question to the same NPC should not affect decisions")
if decision_snapshot != (
    dict(private_npc.suspicion),
    dict(private_npc.relationships[str(meeting_influence_state.player_character_id)]),
    private_npc.memory_summary,
):
    raise SystemExit("follow-up private questions should not update decision state again")
if meeting_influence_state.public_logs != public_logs_before_private_chat:
    raise SystemExit("follow-up private chat must remain private")

private_npc.memory_summary += "\\n绝密私有记忆：3号的隐藏身份。"
public_decision_context = build_public_decision_rag_context(
    meeting_influence_state,
    private_npc,
    private_target,
    "公开发言",
)
if any(context.get("kind") == "private" for context in public_decision_context):
    raise SystemExit("public-decision RAG must not retrieve private-memory items")
if any("绝密私有记忆" in str(context.get("content", "")) for context in public_decision_context):
    raise SystemExit("public-decision RAG leaked private memory content")

perspective_state = make_rule_test_game(
    ["villager", "villager", "werewolf", "seer", "guard", "villager"]
)
perspective_state.phase = "FREE_ACTIVITY"
perspective_npc = perspective_state.characters[1]
perspective_response = private_chat(
    PrivateChatRequest(
        game_id=perspective_state.game_id,
        npc_character_id=perspective_npc.id,
        question="我怀疑你，你最怀疑谁？",
    )
)
if not perspective_response.effective or "你直接怀疑我" not in perspective_response.reply:
    raise SystemExit("directly accusing the current NPC should use the private-chat perspective")
if perspective_state.characters[0].name in perspective_response.reply or perspective_npc.name in perspective_response.reply:
    raise SystemExit("private reply should call the player 你 and the current NPC 我")

reference_state = make_rule_test_game(
    ["villager", "villager", "werewolf", "seer", "guard", "villager"]
)
reference_state.phase = "FREE_ACTIVITY"
ambiguous_response = private_chat(
    PrivateChatRequest(
        game_id=reference_state.game_id,
        npc_character_id=2,
        question="他是不是狼？",
    )
)
if ambiguous_response.effective or not ambiguous_response.can_influence_again:
    raise SystemExit("an unresolved pronoun should not consume the effective private question")
if "哪位角色" not in ambiguous_response.reply:
    raise SystemExit("an unresolved pronoun should ask the player to name a character")
private_chat(
    PrivateChatRequest(
        game_id=reference_state.game_id,
        npc_character_id=2,
        question="我想问3号C罗。",
    )
)
followup_response = private_chat(
    PrivateChatRequest(
        game_id=reference_state.game_id,
        npc_character_id=2,
        question="我怀疑他。",
    )
)
if "3号 C罗" not in followup_response.reply:
    raise SystemExit("a follow-up pronoun should resolve to the latest explicit third party")

guard_state = make_rule_test_game(["guard", "villager", "werewolf", "villager", "villager", "villager"])
guard_state.night_actions = [
    NightActionState(day=1, actor_id=1, action_type="guard_protect", target_id=2),
    NightActionState(day=1, actor_id=3, action_type="werewolf_kill", target_id=2),
]
guard_result = resolve_night(NightResolveRequest(game_id=guard_state.game_id))
if guard_result.dead_characters:
    raise SystemExit("guarded character should survive wolf kill")
if not guard_result.is_peaceful_night:
    raise SystemExit("guard protection should create a peaceful night")
if not guard_state.characters[1].alive:
    raise SystemExit("guarded target should remain alive")
if "成功挡下狼刀" not in guard_state.characters[0].memory_summary:
    raise SystemExit("guard should remember successful protection")

player_seer_state = make_rule_test_game(["seer", "villager", "werewolf", "villager", "villager", "villager"])
player_seer_state.night_actions = [
    NightActionState(day=1, actor_id=1, action_type="seer_check", target_id=3),
    NightActionState(day=1, actor_id=3, action_type="none", target_id=None),
]
player_seer_result = resolve_night(NightResolveRequest(game_id=player_seer_state.game_id))
seer_check = player_seer_result.player_private_result.get("seer_check", {})
if seer_check.get("target_id") != 3 or seer_check.get("result") != "werewolf":
    raise SystemExit("player seer should learn checked target camp")
state_after_player_seer = get_wolf_game_state(player_seer_state.game_id)
last_check = state_after_player_seer.player_private_info.last_check_result or {}
if last_check.get("target_id") != 3 or last_check.get("result") != "werewolf":
    raise SystemExit("player seer check should persist in private state")
if not any(
    "第1夜 · 预言家：查验3号 C罗 → 狼人" in item
    for item in state_after_player_seer.player_private_info.action_history
):
    raise SystemExit("player action history should show resolved seer checks")
if "查验" not in player_seer_state.characters[0].memory_summary:
    raise SystemExit("player seer should remember check result")

full_player_speech = "这是需要完整保留在玩家行动记录中的公开发言。"
player_seer_state.speeches.append(
    SpeechState(
        day=1,
        character_id=1,
        name="规则测试",
        speech=full_player_speech,
        is_player=True,
        phase="DAY_MEETING",
    )
)
player_seer_state.private_conversations.append(
    PrivateConversationState(
        day=1,
        npc_character_id=2,
        question="你如何评价3号？",
        reply="我会继续观察。",
        effective=True,
    )
)
player_seer_state.votes.append(
    VoteState(day=1, voter_id=1, target_id=3, reason="我的公开投票理由。")
)
complete_player_history = get_wolf_game_state(
    player_seer_state.game_id
).player_private_info.action_history
if not any(full_player_speech in item for item in complete_player_history):
    raise SystemExit("player action history should retain the full public speech")
if not any("私聊2号 梅西：你如何评价3号？" in item for item in complete_player_history):
    raise SystemExit("player action history should retain private questions")
if not any("投给3号 C罗；理由：我的公开投票理由。" in item for item in complete_player_history):
    raise SystemExit("player action history should retain vote targets and reasons")

npc_seer_state = make_rule_test_game(["villager", "seer", "werewolf", "villager", "villager", "villager"])
npc_seer_state.night_actions = [
    NightActionState(day=1, actor_id=2, action_type="seer_check", target_id=3),
    NightActionState(day=1, actor_id=3, action_type="none", target_id=None),
]
resolve_night(NightResolveRequest(game_id=npc_seer_state.game_id))
npc_seer = npc_seer_state.characters[1]
if npc_seer.suspicion.get("3", 0) < 100:
    raise SystemExit("NPC seer should strongly suspect checked werewolf")
if "查验" not in npc_seer.memory_summary:
    raise SystemExit("NPC seer should remember check result")
npc_seer_view = next(
    character
    for character in get_wolf_game_state(npc_seer_state.game_id).characters
    if character.id == 2
)
if npc_seer_view.memory_count <= 0:
    raise SystemExit("character view should expose memory count")

player_claim_state = make_rule_test_game(
    ["villager", "seer", "werewolf", "guard", "witch", "hunter"]
)
player_claim_state.phase = "DAY_MEETING"
player_claim_state.meeting = DayMeetingState(
    day=1,
    direction="clockwise",
    order=list(range(1, 13)),
)
player_claim_response = submit_player_speech(
    PlayerSpeechRequest(
        game_id=player_claim_state.game_id,
        character_id=1,
        speech="我是预言家，昨晚查验3号C罗是狼人。",
    )
)
if len(player_claim_response.parsed.claims) != 2:
    raise SystemExit("player speech should parse role and seer-check claims")
player_claim_view = get_wolf_game_state(player_claim_state.game_id).characters[0]
if player_claim_view.claimed_role != "seer":
    raise SystemExit("player public role claim should appear in the character view")
if not any("称验3号 C罗为狼人" in label for label in player_claim_view.public_claims):
    raise SystemExit("player claimed check should appear as a neutral public label")

true_seer_claim_state = make_rule_test_game(
    ["villager", "seer", "werewolf", "guard", "witch", "hunter"]
)
true_seer_claim_state.night_actions = [
    NightActionState(day=1, actor_id=2, action_type="seer_check", target_id=3),
    NightActionState(day=1, actor_id=3, action_type="none", target_id=None),
]
true_seer_claim_state.phase = "DAY_MEETING"
true_seer_claim_state.meeting = DayMeetingState(
    day=1,
    direction="clockwise",
    order=[2],
)
true_seer_speech = generate_npc_speech(
    NpcSpeechRequest(game_id=true_seer_claim_state.game_id, character_id=2)
).speech.speech
if "预言家" not in true_seer_speech or "C罗" not in true_seer_speech or "狼人" not in true_seer_speech:
    raise SystemExit("true NPC seer should claim and report a wolf check")
true_seer_claims = [
    claim
    for claim in true_seer_claim_state.public_claims
    if claim.character_id == 2
]
if {claim.claim_type for claim in true_seer_claims} != {"role", "seer_check"}:
    raise SystemExit("true NPC seer claims should be stored structurally")

fake_seer_state = make_rule_test_game(
    ["villager", "werewolf", "seer", "werewolf", "guard", "witch", "hunter"]
)
fake_seer_state.wolf_fake_seer_id = 2
main_module.register_public_claims(
    fake_seer_state,
    [
        main_module.PublicClaimState(
            day=1,
            character_id=3,
            claim_type="role",
            claimed_role="seer",
            source="true_role",
        ),
        main_module.PublicClaimState(
            day=1,
            character_id=3,
            claim_type="seer_check",
            claimed_role="seer",
            target_id=2,
            result="werewolf",
            source="night_1",
        ),
    ],
)
fake_seer_state.phase = "DAY_MEETING"
fake_seer_state.meeting = DayMeetingState(
    day=1,
    direction="clockwise",
    order=[2],
)
generate_npc_speech(
    NpcSpeechRequest(game_id=fake_seer_state.game_id, character_id=2)
)
day_one_fake_checks = [
    claim
    for claim in fake_seer_state.public_claims
    if claim.character_id == 2 and claim.claim_type == "seer_check"
]
if len(day_one_fake_checks) != 1 or day_one_fake_checks[0].source != "wolf_fake_seer":
    raise SystemExit("designated NPC wolf should counterclaim seer with a fake check")
fake_target_id = day_one_fake_checks[0].target_id
good_listener = fake_seer_state.characters[4]
if good_listener.suspicion.get(str(fake_target_id), 0) <= 0:
    raise SystemExit("a fake wolf check should influence ordinary NPC suspicion")

fake_seer_state.day = 2
fake_seer_state.phase = "DAY_MEETING"
fake_seer_state.meeting = DayMeetingState(
    day=2,
    direction="clockwise",
    order=[2],
)
generate_npc_speech(
    NpcSpeechRequest(game_id=fake_seer_state.game_id, character_id=2)
)
all_fake_checks = [
    claim
    for claim in fake_seer_state.public_claims
    if claim.character_id == 2 and claim.claim_type == "seer_check"
]
if len(all_fake_checks) != 2 or len({claim.target_id for claim in all_fake_checks}) != 2:
    raise SystemExit("fake seer should maintain a new, non-contradictory check each day")

wolf_check_wolf_state = make_rule_test_game(
    ["villager", "werewolf", "seer", "werewolf", "werewolf", "werewolf"]
)
wolf_check_wolf_state.wolf_fake_seer_id = 2
for listener in wolf_check_wolf_state.characters[5:]:
    listener.suspicion["4"] = 10
wolf_check_target = main_module.choose_fake_seer_check(
    wolf_check_wolf_state,
    wolf_check_wolf_state.characters[1],
)
if wolf_check_target != (4, "werewolf") or not wolf_check_wolf_state.wolf_checked_wolf_used:
    raise SystemExit("a pressured wolf teammate should enable the once-per-game wolf-checks-wolf strategy")

witch_claim_state = make_rule_test_game(
    ["villager", "villager", "witch", "werewolf", "villager", "seer", "guard", "hunter"]
)
witch_claim_state.night_actions = [
    NightActionState(day=1, actor_id=3, action_type="witch_poison", target_id=4),
]
witch_claim_types = {
    claim.claim_type
    for claim in main_module.plan_npc_public_claims(
        witch_claim_state,
        witch_claim_state.characters[2],
    )
}
if witch_claim_types != {"role", "witch_poison"}:
    raise SystemExit("a bold NPC witch should be able to reveal a used potion")

guard_claim_state = make_rule_test_game(
    ["villager", "villager", "guard", "werewolf", "villager", "seer", "witch", "hunter"]
)
guard_claim_state.night_actions = [
    NightActionState(day=1, actor_id=3, action_type="guard_protect", target_id=5),
]
guard_claim_state.night_resolutions = [
    NightResolutionState(day=1, attacked_target_id=5, protected_ids=[5], dead_character_ids=[]),
]
guard_claim_types = {
    claim.claim_type
    for claim in main_module.plan_npc_public_claims(
        guard_claim_state,
        guard_claim_state.characters[2],
    )
}
if guard_claim_types != {"role", "guard_success"}:
    raise SystemExit("a bold NPC guard should be able to reveal a successful protection")

hunter_claim_state = make_rule_test_game(
    ["villager", "villager", "hunter", "werewolf", "villager", "seer", "witch", "guard"]
)
for observer in hunter_claim_state.characters:
    if not observer.is_player and observer.id != 3:
        observer.suspicion["3"] = 10
hunter_claims = main_module.plan_npc_public_claims(
    hunter_claim_state,
    hunter_claim_state.characters[2],
)
if not any(claim.claimed_role == "hunter" for claim in hunter_claims):
    raise SystemExit("an NPC hunter under pressure should be able to reveal the role")

voice_state = make_rule_test_game(["villager"])
voice_npc = voice_state.characters[1]
voice_profile = main_module.get_npc_voice_profile(voice_npc.name)
if not voice_profile["speech_style"] or not voice_profile["catchphrases"] or not voice_profile["easter_eggs"]:
    raise SystemExit("wolf-game NPC should expose configured voice and easter-egg data")
voice_changed = False
for test_day in range(1, 12):
    voice_state.day = test_day
    if main_module.apply_npc_voice(voice_state, voice_npc, "基础判断。", "meeting") != "基础判断。":
        voice_changed = True
        break
if not voice_changed:
    raise SystemExit("configured NPC voice should occasionally affect rule speech")

easter_egg_state = make_rule_test_game(["villager"])
easter_egg_state.phase = "FREE_ACTIVITY"
mei_changsu = next(
    character for character in easter_egg_state.characters
    if character.name == "梅长苏"
)
mei_changsu.role = "guard"
mei_changsu.camp = "good"
easter_egg_response = private_chat(
    PrivateChatRequest(
        game_id=easter_egg_state.game_id,
        npc_character_id=mei_changsu.id,
        question="林殊！",
    )
)
if not easter_egg_response.easter_egg_triggered or not easter_egg_response.easter_egg_first_time:
    raise SystemExit("梅长苏 should recognize the 林殊 trigger with punctuation")
if easter_egg_response.effective or not easter_egg_response.can_influence_again:
    raise SystemExit("a trigger easter egg must not consume the effective private question")
if "我是守卫" not in easter_egg_response.reply:
    raise SystemExit("梅长苏's 林殊 easter egg must reveal the real game role")

repeat_easter_egg_response = private_chat(
    PrivateChatRequest(
        game_id=easter_egg_state.game_id,
        npc_character_id=mei_changsu.id,
        question="你真的是林殊吗？",
    )
)
if not repeat_easter_egg_response.easter_egg_triggered or repeat_easter_egg_response.easter_egg_first_time:
    raise SystemExit("a repeated trigger should use the repeat easter-egg response")
easter_egg_history = get_wolf_game_state(easter_egg_state.game_id).player_private_info.action_history
if sum("发现梅长苏的关键词彩蛋" in item for item in easter_egg_history) != 1:
    raise SystemExit("a trigger easter egg should appear once in player private history")
if not any("本局身份是守卫" in item for item in easter_egg_history):
    raise SystemExit("the privately revealed role should be saved in player action history")

for trigger_npc in easter_egg_state.characters:
    if trigger_npc.is_player or trigger_npc.id == mei_changsu.id:
        continue
    trigger_profile = main_module.NPC_PROFILES[trigger_npc.name]
    trigger_text = trigger_profile.trigger_easter_eggs[0].triggers[0]
    trigger_response = private_chat(
        PrivateChatRequest(
            game_id=easter_egg_state.game_id,
            npc_character_id=trigger_npc.id,
            question=f"试试这个口令：{trigger_text}！",
        )
    )
    if not trigger_response.easter_egg_triggered or not trigger_response.easter_egg_first_time:
        raise SystemExit(f"{trigger_npc.name} trigger easter egg should work in private chat")
    if trigger_response.effective:
        raise SystemExit(f"{trigger_npc.name} trigger easter egg must not affect decisions")

post_easter_egg_question = private_chat(
    PrivateChatRequest(
        game_id=easter_egg_state.game_id,
        npc_character_id=mei_changsu.id,
        question="我怀疑2号梅西，他的发言需要解释。",
    )
)
if not post_easter_egg_question.effective:
    raise SystemExit("a normal private question should remain effective after an easter egg")

easter_egg_rule_text = main_module.build_triggered_easter_egg_reply(
    mei_changsu,
    main_module.NPC_PROFILES["梅长苏"].trigger_easter_eggs[0],
    True,
)
authorized_role_rewrite = main_module.validate_llm_rewrite(
    LLMGeneration(
        text="你既然认出了林殊，我便直说：我是守卫，这件事暂且不要公开。",
        used_llm=True,
        provider="stub",
        model="stub",
    ),
    easter_egg_rule_text,
    easter_egg_state,
    speaker=mei_changsu,
    required_self_role="guard",
)
if not authorized_role_rewrite.used_llm:
    raise SystemExit("validator should accept the authorized true self-role easter egg")

for invalid_text in [
    "你既然认出了林殊，这件事暂且不要公开。",
    "你既然认出了林殊，我便直说：我是狼人。",
    "你既然认出了林殊，我是守卫，但我也继续以预言家身份行动。",
]:
    invalid_role_rewrite = main_module.validate_llm_rewrite(
        LLMGeneration(
            text=invalid_text,
            used_llm=True,
            provider="stub",
            model="stub",
        ),
        easter_egg_rule_text,
        easter_egg_state,
        speaker=mei_changsu,
        required_self_role="guard",
    )
    if invalid_role_rewrite.used_llm:
        raise SystemExit("validator should reject an omitted or changed easter-egg role")

wolf_team_state = make_rule_test_game(
    [
        "werewolf", "werewolf", "werewolf", "werewolf",
        "seer", "witch", "hunter", "guard",
        "villager", "villager", "villager", "villager",
    ]
)
wolf_team_view = get_wolf_game_state(wolf_team_state.game_id)
if len(wolf_team_view.player_private_info.wolf_teammates) != 3:
    raise SystemExit("werewolf player should receive all living wolf teammates")
visible_wolf_ids = {
    character.id
    for character in wolf_team_view.characters
    if character.role_visible_to_player == "werewolf"
}
if visible_wolf_ids != {1, 2, 3, 4}:
    raise SystemExit("werewolf player should see all four wolf identities")
for wolf in wolf_team_state.characters[:4]:
    teammate_ids = {1, 2, 3, 4} - {wolf.id}
    if any(
        wolf.relationships[str(teammate_id)].get("alliance") != "wolf_teammate"
        for teammate_id in teammate_ids
    ):
        raise SystemExit("NPC wolves should internally recognize every wolf teammate")

wolf_speaker = wolf_team_state.characters[1]
low_pressure_focus = main_module.choose_speech_focus_target(wolf_team_state, wolf_speaker)
if low_pressure_focus is None or low_pressure_focus.role == "werewolf":
    raise SystemExit("NPC wolf should avoid exposing a low-pressure teammate")
high_pressure_teammate = wolf_team_state.characters[2]
for observer in wolf_team_state.characters:
    if observer.is_player or observer.id == high_pressure_teammate.id:
        continue
    observer.suspicion[str(high_pressure_teammate.id)] = 20
if not main_module.should_wolf_sell_teammate(
    wolf_team_state,
    wolf_speaker,
    high_pressure_teammate,
):
    raise SystemExit("NPC wolf should allow a strategic sell under high public pressure")
if main_module.choose_speech_focus_target(wolf_team_state, wolf_speaker).id != high_pressure_teammate.id:
    raise SystemExit("NPC wolf speech should focus the high-pressure teammate when selling")
if main_module.choose_npc_vote_target(wolf_team_state, wolf_speaker) != high_pressure_teammate.id:
    raise SystemExit("NPC wolf vote should be able to sell the high-pressure teammate")

unsafe_role_rewrite = main_module.validate_llm_rewrite(
    LLMGeneration(text="我是女巫，今晚有完整信息。", used_llm=True, provider="stub", model="stub"),
    "我会继续观察。",
    wolf_team_state,
)
if unsafe_role_rewrite.used_llm or "role claim" not in unsafe_role_rewrite.fallback_reason:
    raise SystemExit("LLM validator should reject unsupported witch or hunter role claims")
unsafe_team_rewrite = main_module.validate_llm_rewrite(
    LLMGeneration(text="C罗是我的队友。", used_llm=True, provider="stub", model="stub"),
    "我会继续观察C罗。",
    wolf_team_state,
)
if unsafe_team_rewrite.used_llm or "wolf-team" not in unsafe_team_rewrite.fallback_reason:
    raise SystemExit("LLM validator should reject hidden wolf-team disclosure")

semantic_validation_state = make_rule_test_game(
    ["villager", "villager", "werewolf", "villager", "seer", "witch", "hunter"]
)
semantic_speaker = semantic_validation_state.characters[4]
semantic_target = semantic_validation_state.characters[2]
semantic_claims = [
    main_module.PublicClaimState(
        day=1,
        character_id=semantic_speaker.id,
        claim_type="role",
        claimed_role="seer",
        source="sheriff_true_seer",
    ),
    main_module.PublicClaimState(
        day=1,
        character_id=semantic_speaker.id,
        claim_type="seer_check",
        claimed_role="seer",
        target_id=semantic_target.id,
        result="good",
        source="sheriff_night_1",
    ),
]
semantic_rule_text = main_module.build_public_claim_speech(
    semantic_validation_state,
    semantic_speaker,
    semantic_claims,
)
real_deepseek_good_rewrite = main_module.validate_llm_rewrite(
    LLMGeneration(
        text=(
            "1号的发言很谨慎，说等预言家。那我就不绕了，我是预言家，"
            "昨晚验了3号C罗，他是好人。我会竞选警长，后续用发言和票型来印证这个信息。"
        ),
        used_llm=True,
        provider="stub",
        model="stub",
    ),
    semantic_rule_text,
    semantic_validation_state,
    speaker=semantic_speaker,
    required_target=semantic_target,
    required_claims=semantic_claims,
    public_text=True,
)
if not real_deepseek_good_rewrite.used_llm:
    raise SystemExit(
        "semantic validator should accept natural '我是预言家/验了/好人' wording: "
        + real_deepseek_good_rewrite.fallback_reason
    )

fake_speaker = semantic_validation_state.characters[2]
fake_target = semantic_validation_state.characters[3]
fake_claims = [
    main_module.PublicClaimState(
        day=1,
        character_id=fake_speaker.id,
        claim_type="role",
        claimed_role="seer",
        source="sheriff_wolf_fake_seer",
    ),
    main_module.PublicClaimState(
        day=1,
        character_id=fake_speaker.id,
        claim_type="seer_check",
        claimed_role="seer",
        target_id=fake_target.id,
        result="werewolf",
        source="sheriff_wolf_fake_seer",
    ),
]
fake_rule_text = main_module.build_public_claim_speech(
    semantic_validation_state,
    fake_speaker,
    fake_claims,
)
real_deepseek_wolf_rewrite = main_module.validate_llm_rewrite(
    LLMGeneration(
        text=(
            "冷静，Calma。场上有人起跳，但我也把话讲清楚。我是预言家，"
            "验了4号周深是狼人。我竞选警长，会用后续发言和票型证明这套信息。"
        ),
        used_llm=True,
        provider="stub",
        model="stub",
    ),
    fake_rule_text,
    semantic_validation_state,
    speaker=fake_speaker,
    required_target=fake_target,
    required_claims=fake_claims,
    public_text=True,
)
if not real_deepseek_wolf_rewrite.used_llm:
    raise SystemExit(
        "semantic validator should accept a rule-approved fake-seer wolf check: "
        + real_deepseek_wolf_rewrite.fallback_reason
    )

attributed_speaker = semantic_validation_state.characters[9]
attributed_target = semantic_validation_state.characters[3]
referenced_claimant = semantic_validation_state.characters[4]
referenced_target = semantic_validation_state.characters[7]
main_module.register_public_claims(
    semantic_validation_state,
    [
        main_module.PublicClaimState(
            day=1,
            character_id=referenced_claimant.id,
            claim_type="seer_check",
            claimed_role="seer",
            target_id=referenced_target.id,
            result="good",
            source="public_reference",
        )
    ],
)
attributed_claims = [
    main_module.PublicClaimState(
        day=1,
        character_id=attributed_speaker.id,
        claim_type="role",
        claimed_role="seer",
        source="sheriff_true_seer",
    ),
    main_module.PublicClaimState(
        day=1,
        character_id=attributed_speaker.id,
        claim_type="seer_check",
        claimed_role="seer",
        target_id=attributed_target.id,
        result="good",
        source="sheriff_night_1",
    ),
]
attributed_rule_text = main_module.build_public_claim_speech(
    semantic_validation_state,
    attributed_speaker,
    attributed_claims,
)
real_attribution_rewrite = main_module.validate_llm_rewrite(
    LLMGeneration(
        text=(
            "先别催，我都听着呢。5号起跳给8号金水，3号也接了话。"
            "那我也把话说清楚：我验了4号周深，是好人。我上警竞选警长。"
        ),
        used_llm=True,
        provider="stub",
        model="stub",
    ),
    attributed_rule_text,
    semantic_validation_state,
    speaker=attributed_speaker,
    required_target=attributed_target,
    required_claims=attributed_claims,
    public_text=True,
)
if not real_attribution_rewrite.used_llm:
    raise SystemExit(
        "semantic validator should distinguish cited claimant 5 from checked target 8 "
        "and treat '我验了' as a seer claim: "
        + real_attribution_rewrite.fallback_reason
    )

changed_check_result = main_module.validate_llm_rewrite(
    LLMGeneration(
        text="我是预言家，昨晚验了3号C罗，他是狼人。",
        used_llm=True,
        provider="stub",
        model="stub",
    ),
    semantic_rule_text,
    semantic_validation_state,
    speaker=semantic_speaker,
    required_target=semantic_target,
    required_claims=semantic_claims,
    public_text=True,
)
if changed_check_result.used_llm or "changed an approved seer-check result" not in changed_check_result.fallback_reason:
    raise SystemExit("semantic validator should reject a changed seer-check result")

invented_check = main_module.validate_llm_rewrite(
    LLMGeneration(
        text=(
            "我是预言家，昨晚验了3号C罗，他是好人。除此之外，"
            "我还验了4号周深，他是狼人。"
        ),
        used_llm=True,
        provider="stub",
        model="stub",
    ),
    semantic_rule_text,
    semantic_validation_state,
    speaker=semantic_speaker,
    required_target=semantic_target,
    required_claims=semantic_claims,
    public_text=True,
)
if invented_check.used_llm or "unapproved seer check" not in invented_check.fallback_reason:
    raise SystemExit("semantic validator should reject an invented second seer check")

unsupported_power_identity = main_module.validate_llm_rewrite(
    LLMGeneration(
        text="我会观察4号周深，但4号周深就是女巫。",
        used_llm=True,
        provider="stub",
        model="stub",
    ),
    "我会继续观察4号周深。",
    semantic_validation_state,
    speaker=semantic_speaker,
    required_target=fake_target,
    public_text=True,
)
if unsupported_power_identity.used_llm or "unsupported character identity" not in unsupported_power_identity.fallback_reason:
    raise SystemExit("semantic validator should reject an unapproved categorical power-role identity")

speculative_power_read = main_module.validate_llm_rewrite(
    LLMGeneration(
        text="我会观察4号周深，我觉得4号周深可能是女巫。",
        used_llm=True,
        provider="stub",
        model="stub",
    ),
    "我会继续观察4号周深。",
    semantic_validation_state,
    speaker=semantic_speaker,
    required_target=fake_target,
    public_text=True,
)
if not speculative_power_read.used_llm:
    raise SystemExit("semantic validator should allow a clearly speculative role read")

wolf_team_state.night_actions = [
    NightActionState(day=1, actor_id=2, action_type="werewolf_kill", target_id=9),
    NightActionState(day=1, actor_id=3, action_type="werewolf_kill", target_id=10),
    NightActionState(day=1, actor_id=4, action_type="werewolf_kill", target_id=10),
]
submit_night_action(
    NightActionRequest(
        game_id=wolf_team_state.game_id,
        character_id=1,
        action_type="werewolf_kill",
        target_id=11,
    )
)
if main_module.get_current_wolf_target(wolf_team_state) != 11:
    raise SystemExit("player werewolf target should override the NPC wolf majority")

witch_state = make_rule_test_game(
    [
        "witch", "guard", "werewolf", "werewolf", "villager", "hunter",
        "seer", "villager", "villager", "villager", "villager", "villager",
    ]
)
witch_state.night_actions = [
    NightActionState(day=1, actor_id=1, action_type="witch_save", target_id=5),
    NightActionState(day=1, actor_id=2, action_type="guard_protect", target_id=5),
    NightActionState(day=1, actor_id=3, action_type="werewolf_kill", target_id=5),
    NightActionState(day=1, actor_id=4, action_type="werewolf_kill", target_id=5),
]
witch_result = resolve_night(NightResolveRequest(game_id=witch_state.game_id))
if 5 not in witch_result.dead_characters or witch_state.characters[4].alive:
    raise SystemExit("guard and antidote on the same wolf target should still eliminate it")
if main_module.get_role_resources(witch_state, 1).get("antidote_available", True):
    raise SystemExit("witch antidote should be consumed after use")

hunter_state = make_rule_test_game(
    [
        "hunter", "werewolf", "werewolf", "seer", "guard", "villager",
        "villager", "villager", "villager", "villager", "villager", "villager",
    ]
)
hunter_state.night_actions = [
    NightActionState(
        day=1,
        actor_id=character.id,
        action_type="werewolf_kill" if character.role == "werewolf" else "none",
        target_id=1 if character.role == "werewolf" else None,
    )
    for character in hunter_state.characters
    if not character.is_player
]
hunter_night_result = resolve_night(NightResolveRequest(game_id=hunter_state.game_id))
if hunter_state.phase != "HUNTER_SHOT" or 1 not in hunter_night_result.dead_characters:
    raise SystemExit("eliminated player hunter should pause the game for a shot")
if not get_wolf_game_state(hunter_state.game_id).player_private_info.hunter_can_shoot:
    raise SystemExit("player hunter private state should enable the shot control")
hunter_shot_result = resolve_hunter_shot(
    HunterShotRequest(game_id=hunter_state.game_id, character_id=1, target_id=2)
)
if not hunter_shot_result.success or hunter_state.characters[1].alive:
    raise SystemExit("player hunter shot should eliminate the selected target")
if hunter_state.phase != "DAY_MEETING":
    raise SystemExit("hunter shot should resume the interrupted night flow")

poisoned_hunter_state = make_rule_test_game(
    [
        "hunter", "werewolf", "witch", "seer", "guard", "villager",
        "villager", "villager", "villager", "villager", "villager", "villager",
    ]
)
poisoned_hunter_state.night_actions = [
    NightActionState(day=1, actor_id=2, action_type="werewolf_kill", target_id=6),
    NightActionState(day=1, actor_id=3, action_type="witch_poison", target_id=1),
    NightActionState(day=1, actor_id=4, action_type="none", target_id=None),
    NightActionState(day=1, actor_id=5, action_type="none", target_id=None),
]
resolve_night(NightResolveRequest(game_id=poisoned_hunter_state.game_id))
if poisoned_hunter_state.phase == "HUNTER_SHOT" or poisoned_hunter_state.hunter_shots:
    raise SystemExit("poisoned hunter must not receive a shot")

player_freedom_state = make_rule_test_game(
    ["seer", "werewolf", "werewolf", "werewolf", "werewolf", "villager"]
)
player_freedom_state.badge_destroyed = False
player_freedom_state.sheriff_election = None
main_module.start_sheriff_signup(player_freedom_state)
freedom_signup = submit_sheriff_signup(
    SheriffSignupRequest(
        game_id=player_freedom_state.game_id,
        character_id=1,
        run_for_sheriff=False,
    )
)
if 1 in freedom_signup.candidates:
    raise SystemExit("player seer must be free to stay off the sheriff election")

npc_only_withdrawal_state = make_rule_test_game(
    ["villager", "seer", "werewolf", "villager", "villager", "villager"]
)
npc_only_withdrawal_state.badge_destroyed = False
npc_only_withdrawal_state.sheriff_election = SheriffElectionState(
    candidates=[2, 3],
    speech_order=[2, 3],
    current_index=1,
)
npc_only_withdrawal_state.phase = "SHERIFF_SPEECH"
main_module.advance_sheriff_speech(npc_only_withdrawal_state)
if npc_only_withdrawal_state.phase == "SHERIFF_WITHDRAWAL":
    raise SystemExit("a player who stayed off sheriff should not have to complete NPC withdrawals")

wolf_coordination_state = make_rule_test_game(
    ["werewolf", "seer", "werewolf", "werewolf", "werewolf", "villager"]
)
wolf_coordination_state.badge_destroyed = False
wolf_coordination_state.night_actions = [
    NightActionState(day=1, actor_id=2, action_type="seer_check", target_id=3),
]
wolf_coordination_state.wolf_fake_seer_id = main_module.choose_designated_fake_seer(
    wolf_coordination_state.characters
)
fake_seer_id = wolf_coordination_state.wolf_fake_seer_id
wolf_coordination_state.sheriff_election = SheriffElectionState(
    candidates=[1, fake_seer_id, 2],
    speech_order=[1, fake_seer_id, 2],
)
wolf_coordination_state.phase = "SHERIFF_SPEECH"
submit_player_sheriff_speech(
    SheriffSpeechRequest(
        game_id=wolf_coordination_state.game_id,
        character_id=1,
        speech="我是预言家，昨晚查验4号是好人，我来带队。",
    )
)
fake_campaign = generate_npc_sheriff_campaign_speech(
    SheriffSpeechRequest(
        game_id=wolf_coordination_state.game_id,
        character_id=fake_seer_id,
    )
)
if "起跳预言家" in fake_campaign.speech.speech:
    raise SystemExit("NPC wolf should be able to yield when a wolf player already makes a strong seer claim")
generate_npc_sheriff_campaign_speech(
    SheriffSpeechRequest(
        game_id=wolf_coordination_state.game_id,
        character_id=2,
    )
)
true_seer_claims = [
    claim
    for claim in wolf_coordination_state.public_claims
    if claim.character_id == 2
]
if not any(claim.claim_type == "role" and claim.claimed_role == "seer" for claim in true_seer_claims):
    raise SystemExit("NPC true seer must claim seer during the sheriff election")
if not any(claim.claim_type == "seer_check" and claim.target_id == 3 and claim.result == "werewolf" for claim in true_seer_claims):
    raise SystemExit("NPC true seer must reveal the real first-night check")
submit_sheriff_withdrawal(
    SheriffWithdrawalRequest(
        game_id=wolf_coordination_state.game_id,
        character_id=1,
        withdraw=False,
    )
)
if fake_seer_id not in wolf_coordination_state.sheriff_election.withdrawn:
    raise SystemExit("NPC fake seer should support the explicit withdrawal flow after yielding")

runoff_state = make_rule_test_game(
    ["villager", "seer", "werewolf", "villager", "villager", "villager"]
)
runoff_state.badge_destroyed = False
runoff_state.sheriff_election = SheriffElectionState(candidates=[2, 3])
runoff_state.phase = "SHERIFF_VOTE"
original_sheriff_vote_chooser = main_module.choose_npc_sheriff_vote_target
try:
    def force_first_round_tie(_game_state, voter, _candidate_ids):
        return 2 if voter.id <= 7 else 3

    main_module.choose_npc_sheriff_vote_target = force_first_round_tie
    first_sheriff_vote = submit_and_resolve_sheriff_vote(
        SheriffVoteRequest(
            game_id=runoff_state.game_id,
            character_id=1,
            target_id=2,
        )
    )
    if runoff_state.phase != "SHERIFF_RUNOFF_SPEECH" or sorted(first_sheriff_vote.tied_candidate_ids) != [2, 3]:
        raise SystemExit("a tied first sheriff vote should enter one PK speech round")
    while runoff_state.phase == "SHERIFF_RUNOFF_SPEECH":
        speaker_id = main_module.get_current_sheriff_speaker_id(runoff_state)
        generate_npc_sheriff_campaign_speech(
            SheriffSpeechRequest(game_id=runoff_state.game_id, character_id=speaker_id)
        )

    def force_runoff_winner(_game_state, _voter, _candidate_ids):
        return 2

    main_module.choose_npc_sheriff_vote_target = force_runoff_winner
    runoff_result = submit_and_resolve_sheriff_vote(
        SheriffVoteRequest(
            game_id=runoff_state.game_id,
            character_id=1,
            target_id=2,
        )
    )
    if runoff_result.winner_id != 2 or runoff_state.sheriff_id != 2:
        raise SystemExit("the single runoff should elect the second-round winner")
finally:
    main_module.choose_npc_sheriff_vote_target = original_sheriff_vote_chooser

meeting_anchor_state = make_rule_test_game(
    ["villager", "seer", "werewolf", "villager", "witch", "villager"]
)
meeting_anchor_state.badge_destroyed = False
meeting_anchor_state.sheriff_id = 1
meeting_anchor_state.eliminations = [
    EliminationState(
        day=1,
        character_id=4,
        cause="night_kill",
        source_action="werewolf_kill",
        source_actor_ids=[3],
        source_target_id=4,
    ),
    EliminationState(
        day=1,
        character_id=6,
        cause="witch_poison",
        source_action="witch_poison",
        source_actor_ids=[5],
        source_target_id=6,
    ),
]
meeting_anchor_state.characters[3].alive = False
meeting_anchor_state.characters[5].alive = False
main_module.prepare_sheriff_meeting_order(meeting_anchor_state)
if meeting_anchor_state.phase != "MEETING_ORDER" or meeting_anchor_state.meeting_order_anchor_id not in {4, 6}:
    raise SystemExit("multiple night eliminations should pick one public meeting anchor")
submit_sheriff_meeting_order(
    SheriffMeetingOrderRequest(
        game_id=meeting_anchor_state.game_id,
        character_id=1,
        side="right",
    )
)
if meeting_anchor_state.meeting.order[-1] == 1 or meeting_anchor_state.meeting.order_source != "out_right":
    raise SystemExit("sheriff should keep the natural seat position after choosing an eliminated-player side")
if meeting_anchor_state.meeting.order.count(1) != 1:
    raise SystemExit("natural meeting order should contain the sheriff exactly once")

temporary_nomination_state = make_rule_test_game(
    ["villager", "seer", "werewolf", "villager", "villager", "villager"]
)
temporary_nomination_state.badge_destroyed = False
temporary_nomination_state.sheriff_id = 1
temporary_nomination_state.meeting = DayMeetingState(
    day=1,
    direction="clockwise",
    order=list(range(1, 13)),
    sheriff_id=1,
)
temporary_nomination_state.phase = "DAY_MEETING"
temporary_speech = submit_player_speech(
    PlayerSpeechRequest(
        game_id=temporary_nomination_state.game_id,
        character_id=1,
        speech="我先听后面的发言。",
        temporary_nomination_target_id=3,
    )
)
if temporary_nomination_state.meeting.temporary_nomination_target_id != 3:
    raise SystemExit("player sheriff speech should record a temporary nomination")
if "暂时归票" not in temporary_speech.public_log:
    raise SystemExit("temporary sheriff nomination should be included in the public speech")
if main_module.choose_speech_focus_target(
    temporary_nomination_state,
    temporary_nomination_state.characters[1],
).id != 3:
    raise SystemExit("later NPC speech should react to the sheriff's temporary nomination")
temporary_nomination_state.meeting.current_index = len(temporary_nomination_state.meeting.order)
temporary_nomination_state.meeting.completed = True
temporary_nomination_state.phase = "SHERIFF_NOMINATION"
submit_sheriff_nomination(
    SheriffNominationRequest(
        game_id=temporary_nomination_state.game_id,
        character_id=1,
        target_id=4,
    )
)
if temporary_nomination_state.meeting.nomination_target_id != 4:
    raise SystemExit("player sheriff should be able to change the final nomination after all speeches")
if temporary_nomination_state.phase != "FREE_ACTIVITY":
    raise SystemExit("final sheriff nomination should continue to free activity")

locked_vote_state = make_rule_test_game(
    ["villager", "seer", "werewolf", "villager", "villager", "villager"]
)
locked_vote_state.badge_destroyed = False
locked_vote_state.sheriff_id = 1
locked_vote_state.meeting = DayMeetingState(
    day=1,
    direction="clockwise",
    order=list(range(2, 13)) + [1],
    sheriff_id=1,
    nomination_target_id=3,
    completed=True,
)
locked_vote_state.phase = "VOTE"
try:
    submit_and_resolve_all_votes(
        PlayerVoteRequest(
            game_id=locked_vote_state.game_id,
            character_id=1,
            target_id=4,
            reason="尝试偏离归票。",
        )
    )
    raise SystemExit("sheriff should not be allowed to vote away from the nomination")
except HTTPException as exc:
    if exc.status_code != 400:
        raise

edge_win_state = make_rule_test_game(
    [
        "werewolf", "werewolf", "werewolf", "werewolf",
        "seer", "witch", "hunter", "guard",
        "villager", "villager", "villager", "villager",
    ]
)
for character in edge_win_state.characters:
    if character.role == "villager":
        character.alive = False
if main_module.check_winner(edge_win_state) != "werewolf":
    raise SystemExit("wolves should win when the villager side is fully eliminated")
for character in edge_win_state.characters:
    character.alive = character.role != "werewolf"
if main_module.check_winner(edge_win_state) != "good":
    raise SystemExit("good camp should win when all wolves are eliminated")
for character in edge_win_state.characters:
    character.alive = character.role not in main_module.GOD_ROLES
if main_module.check_winner(edge_win_state) != "werewolf":
    raise SystemExit("wolves should win when the god side is fully eliminated")

control_win_state = make_rule_test_game(
    [
        "werewolf", "werewolf", "werewolf", "werewolf",
        "seer", "witch", "hunter", "guard",
        "villager", "villager", "villager", "villager",
    ]
)
for character in control_win_state.characters:
    character.alive = character.id in {1, 2, 5, 9}
control_winner, control_reason = main_module.get_winner_result(control_win_state)
if control_winner != "werewolf" or control_reason != "wolf_control":
    raise SystemExit("wolves should win after reaching equal numbers with the good camp")
if "控场" not in main_module.build_winner_message(control_winner, control_reason):
    raise SystemExit("wolf-control winner message should explain the trigger")

hunter_priority_state = make_rule_test_game(
    [
        "hunter", "werewolf", "werewolf", "seer", "villager",
        "villager", "villager", "villager", "villager", "villager", "villager", "villager",
    ]
)
for character in hunter_priority_state.characters:
    character.alive = character.id <= 5
hunter_priority_state.night_actions = [
    NightActionState(day=1, actor_id=2, action_type="werewolf_kill", target_id=1),
    NightActionState(day=1, actor_id=3, action_type="werewolf_kill", target_id=1),
    NightActionState(day=1, actor_id=4, action_type="none", target_id=None),
]
resolve_night(NightResolveRequest(game_id=hunter_priority_state.game_id))
if hunter_priority_state.phase != "HUNTER_SHOT":
    raise SystemExit("hunter shot must take priority over an immediate wolf-control win")
resolve_hunter_shot(
    HunterShotRequest(
        game_id=hunter_priority_state.game_id,
        character_id=1,
        target_id=2,
    )
)
if hunter_priority_state.phase != "DAY_MEETING" or hunter_priority_state.winner is not None:
    raise SystemExit("hunter should be able to break wolf control before winner evaluation")

badge_hunter_state = make_rule_test_game(
    [
        "hunter", "werewolf", "werewolf", "seer", "villager",
        "villager", "villager", "villager", "villager", "villager", "villager", "villager",
    ]
)
for character in badge_hunter_state.characters:
    character.alive = character.id <= 5
badge_hunter_state.badge_destroyed = False
badge_hunter_state.sheriff_id = 1
badge_hunter_state.night_actions = [
    NightActionState(day=1, actor_id=2, action_type="werewolf_kill", target_id=1),
    NightActionState(day=1, actor_id=3, action_type="werewolf_kill", target_id=1),
    NightActionState(day=1, actor_id=4, action_type="none", target_id=None),
]
resolve_night(NightResolveRequest(game_id=badge_hunter_state.game_id))
if badge_hunter_state.phase != "HUNTER_SHOT":
    raise SystemExit("sheriff hunter should resolve the shot before badge transfer")
resolve_hunter_shot(
    HunterShotRequest(
        game_id=badge_hunter_state.game_id,
        character_id=1,
        target_id=2,
    )
)
if badge_hunter_state.phase != "BADGE_TRANSFER":
    raise SystemExit("player sheriff should transfer the badge after finishing the hunter shot")
submit_badge_transfer(
    BadgeTransferRequest(
        game_id=badge_hunter_state.game_id,
        character_id=1,
        target_id=4,
    )
)
if badge_hunter_state.sheriff_id != 4 or badge_hunter_state.phase != "DAY_MEETING":
    raise SystemExit("badge heir should immediately control the next meeting order")

summary_state = make_rule_test_game(
    ["seer", "guard", "werewolf", "werewolf", "villager", "villager"]
)
try:
    get_game_summary(summary_state.game_id)
    raise SystemExit("game summary should be hidden before GAME_OVER")
except HTTPException as exc:
    if exc.status_code != 400:
        raise

summary_state.day = 2
summary_state.night_actions = [
    NightActionState(day=1, actor_id=1, action_type="seer_check", target_id=3),
    NightActionState(day=1, actor_id=2, action_type="guard_protect", target_id=5),
    NightActionState(day=1, actor_id=3, action_type="werewolf_kill", target_id=5),
]
summary_state.night_resolutions = [
    NightResolutionState(day=1, attacked_target_id=5, protected_ids=[5], dead_character_ids=[]),
]
summary_state.speeches = [
    SpeechState(day=1, character_id=1, name="规则测试", speech="我查到了线索。", is_player=True),
]
summary_state.public_claims = [
    main_module.PublicClaimState(
        day=1,
        character_id=1,
        claim_type="role",
        claimed_role="seer",
        source="player_speech",
    ),
]
summary_state.private_conversations = [
    PrivateConversationState(
        day=1,
        npc_character_id=2,
        question="你相信谁？",
        reply="我会继续观察。",
        effective=True,
    ),
]
summary_state.votes = [
    VoteState(day=1, voter_id=1, target_id=3, reason="查验结果指向狼人。"),
]
summary_state.eliminations = [
    EliminationState(
        day=1,
        character_id=3,
        cause="exiled",
        source_action="day_vote",
        source_actor_ids=[1],
        source_target_id=3,
    ),
]
summary_state.characters[2].alive = False
summary_state.phase = "GAME_OVER"
summary_state.winner = "good"
summary = get_game_summary(summary_state.game_id)
if len(summary.characters) != 12 or summary.winner != "good":
    raise SystemExit("game summary should reveal all twelve roles and the winner")
timeline_text = "\\n".join(event.text for event in summary.timeline)
for expected_text in ["查验", "成功挡下狼刀", "公开声明", "私下询问", "投给"]:
    if expected_text not in timeline_text:
        raise SystemExit(f"game summary is missing action detail: {expected_text}")
if not any(event.is_private for event in summary.timeline):
    raise SystemExit("game summary should mark hidden actions and private chats")

print("wolf game start smoke test passed")
"""
    run_command(
        [str(python_bin), "-c", smoke_code],
        cwd=BACKEND_DIR,
        fail_message="wolf game start smoke test failed",
    )
    print("[OK] Wolf game meeting, private chat, role, memory, social, and vote APIs work.")


def check_godot_loads() -> None:
    godot_bin = shutil.which("godot") or shutil.which("godot4")
    if godot_bin is None:
        raise SmokeCheckError("Godot CLI not found. On macOS, install it with: brew install --cask godot")

    run_command(
        [godot_bin, "--headless", "--editor", "--path", str(GAME_DIR), "--quit"],
        cwd=ROOT_DIR,
        fail_message="Godot failed to import project resources",
        forbidden_output=("SCRIPT ERROR", "Parse Error", "Failed to load script"),
    )
    run_command(
        [godot_bin, "--headless", "--path", str(GAME_DIR), "--script", "res://scripts/font_check.gd"],
        cwd=ROOT_DIR,
        fail_message="Godot dialog font glyph check failed",
        forbidden_output=("SCRIPT ERROR", "Parse Error", "Failed to load", "missing characters"),
    )
    run_command(
        [godot_bin, "--headless", "--path", str(GAME_DIR), MAIN_SCENE, "--quit"],
        cwd=ROOT_DIR,
        fail_message="Godot failed to load the main scene",
        forbidden_output=("SCRIPT ERROR", "Parse Error", "Failed to load script"),
    )
    print("[OK] Godot dialog font covers required glyphs and the main scene loads.")


def check_godot_ui_layout() -> None:
    try:
        scene_text = MAIN_SCENE_FILE.read_text(encoding="utf-8")
        script_text = MAIN_SCRIPT_FILE.read_text(encoding="utf-8")
        project_text = PROJECT_FILE.read_text(encoding="utf-8")
        dialog_scene_text = DIALOG_SCENE_FILE.read_text(encoding="utf-8")
        dialog_script_text = DIALOG_SCRIPT_FILE.read_text(encoding="utf-8")
        npc_scene_text = NPC_SCENE_FILE.read_text(encoding="utf-8")
        npc_script_text = NPC_SCRIPT_FILE.read_text(encoding="utf-8")
        player_scene_text = PLAYER_SCENE_FILE.read_text(encoding="utf-8")
        player_script_text = PLAYER_SCRIPT_FILE.read_text(encoding="utf-8")
    except OSError as exc:
        raise SmokeCheckError(f"could not read Godot UI files: {exc}") from exc

    required_scene_fragments = [
        '[node name="ScrollContainer" type="ScrollContainer"',
        'horizontal_scroll_mode = 0',
        'offset_left = -536.0',
        'default_font_size = 13',
        'columns = 2',
        'text = "RanRanHuaiHuaiKill"',
        '[node name="GameSummaryOverlay" type="Control"',
        '[node name="ReviewGameButton" type="Button"',
        '[node name="GameSummaryRequest" type="HTTPRequest"',
        '[node name="LLMEnabledToggle" type="CheckButton"',
        '[node name="LittleKnight" parent="." instance=ExtResource("3_npc_scene")]',
        '[node name="DoctorStrange" parent="." instance=ExtResource("3_npc_scene")]',
        '[node name="NightActionOption" type="OptionButton"',
        '[node name="HunterActionRow" type="HBoxContainer"',
        '[node name="HunterShotRequest" type="HTTPRequest"',
        '[node name="SheriffActionLabel" type="Label"',
        '[node name="SheriffOption" type="OptionButton"',
        '[node name="SheriffWithdrawalRow" type="HBoxContainer"',
        '[node name="ContinueButton" type="Button"',
        'text = "继续竞选"',
        '[node name="WithdrawButton" type="Button"',
        'text = "退水"',
        '[node name="SheriffSpeechInput" type="LineEdit"',
        '[node name="VoteReasonInput" type="LineEdit"',
        '[node name="VoteResultLabel" type="Label"',
        '[node name="CombinedVoteRequest" type="HTTPRequest"',
        '[ext_resource type="FontFile" path="res://assets/fonts/NotoSansSC-Variable.ttf" id="5_main_font"]',
        'theme = SubResource("Theme_main_cjk")',
        '[node name="PlayerIdentityBlock" type="VBoxContainer"',
        '[node name="PlayerActionHistoryBlock" type="VBoxContainer"',
        '[node name="HistoryText" type="TextEdit"',
        'custom_minimum_size = Vector2(0, 84)',
        'theme_override_font_sizes/font_size = 11',
        'text = "玩家行动记录"',
        '[node name="PlayerRoleOption" type="OptionButton"',
        '[node name="TemporaryNominationOption" type="OptionButton"',
        '[node name="SheriffOverviewLabel" type="Label"',
        'position = Vector2(350, -285)',
        'position = Vector2(657, 41)',
        'position = Vector2(182, -240)',
    ]
    for fragment in required_scene_fragments:
        if fragment not in scene_text:
            raise SmokeCheckError(f"Godot menu layout is missing: {fragment}")

    if 'card.custom_minimum_size = Vector2(164, 218)' not in script_text:
        raise SmokeCheckError("Godot character cards are not using the portrait two-column size")
    for fragment in [
        '@onready var wolf_scroll_container: ScrollContainer',
        'const WOLF_MENU_WIDTH := 520.0',
        'const WOLF_MENU_MIN_EXPANDED_HEIGHT := 500.0',
        'const WOLF_MENU_MAX_EXPANDED_HEIGHT := 760.0',
        'viewport_height * 0.82',
        'var phase_changed := _current_wolf_phase != str(phase)',
        'call_deferred("_keep_sheriff_controls_visible")',
        'wolf_scroll_container.ensure_control_visible(sheriff_withdrawal_row)',
        'player_action_history_text.text = "\\n".join(lines)',
        'wolf_scroll_container.scroll_vertical = 0',
        'var easter_egg_triggered := bool(json.data.get("easter_egg_triggered", false))',
        '发现新的角色彩蛋。本次不会消耗今天的有效追问机会。',
    ]:
        if fragment not in script_text:
            raise SmokeCheckError(f"Godot compact panel behavior is missing: {fragment}")
    for removed_fragment in [
        '[node name="GenerateNpcVoteButton"',
        '[node name="ResolveVoteButton"',
    ]:
        if removed_fragment in scene_text:
            raise SmokeCheckError(f"obsolete staged vote control is still present: {removed_fragment}")
    for script_fragment in [
        'func _render_game_summary(summary: Dictionary)',
        'func _request_game_summary()',
        'game_summary_tabs.set_tab_title(0, "角色复盘")',
        '"enable_llm": llm_enabled_toggle.button_pressed',
        '"npc_count": 11',
        'func _update_hunter_controls(game_data: Dictionary)',
        'private_info.get("wolf_teammates", [])',
        'character.get("public_claims", [])',
        'const WOLF_COMBINED_VOTE_URL',
        'func _update_sheriff_controls(game_data: Dictionary)',
        'func _on_sheriff_continue_button_pressed()',
        'func _on_sheriff_withdraw_button_pressed()',
        'func _submit_sheriff_action(withdraw_choice: Variant = null)',
        '"投警长并公布" if can_vote else "公布警长票型"',
        '"SHERIFF_WITHDRAWAL":',
        'func _format_combined_vote_result(vote_data: Dictionary)',
        '"reason": vote_reason',
        'str(_wolf_campaign_status.get(character_id, ""))',
        '"player_role": str(_get_selected_option_metadata(player_role_option, "random"))',
        'func _update_player_identity_display(game_data: Dictionary)',
        'func _update_player_action_history(game_data: Dictionary)',
        'func _configure_wolf_panel_focus()',
        'node.focus_mode = Control.FOCUS_NONE',
        'call_deferred("_release_wolf_panel_focus")',
        'private_info.get("wolf_teammates", [])',
        'func _update_contextual_panel_visibility()',
        'night_action_option.visible = has_active_night_skill',
        '"temporary_nomination_target_id": null',
        'func _update_sheriff_overview()',
        'func _finish_gameplay_text_submission(input: LineEdit)',
        'player_speech_input.text_submitted.connect(_on_player_speech_input_submitted)',
        'sheriff_speech_input.text_submitted.connect(_on_sheriff_speech_input_submitted)',
        'vote_reason_input.text_submitted.connect(_on_vote_reason_input_submitted)',
        'get_viewport().gui_release_focus()',
    ]:
        if script_fragment not in script_text:
            raise SmokeCheckError(f"Godot game summary UI is missing: {script_fragment}")
    if 'window/size/viewport_width=1280' not in project_text or 'window/size/viewport_height=720' not in project_text:
        raise SmokeCheckError("Godot default window should be 1280x720")
    for dialog_fragment in [
        '[ext_resource type="FontFile" path="res://assets/fonts/NotoSansSC-Variable.ttf"',
        'theme = SubResource("Theme_dialog_cjk")',
        '[node name="ValidationFailureButton" type="Button"',
    ]:
        if dialog_fragment not in dialog_scene_text:
            raise SmokeCheckError(f"Godot dialog font fallback is missing: {dialog_fragment}")
    for script_fragment in [
        "func _clean_display_text",
        "func show_public_evidence_notice",
        "func _format_llm_fallback_reason",
        "func _on_validation_failure_button_pressed",
    ]:
        if script_fragment not in dialog_script_text:
            raise SmokeCheckError(f"Godot dialog text protection is missing: {script_fragment}")
    if not DIALOG_FONT_FILE.exists() or DIALOG_FONT_FILE.stat().st_size < 10_000_000:
        raise SmokeCheckError("bundled Noto Sans SC font is missing or incomplete")
    if not DIALOG_FONT_LICENSE_FILE.exists():
        raise SmokeCheckError("bundled Noto Sans SC OFL license is missing")

    for scene_label, scene_source in [
        ("NPC", npc_scene_text),
        ("player", player_scene_text),
    ]:
        if 'node name="CharacterSprite" type="Sprite2D"' not in scene_source:
            raise SmokeCheckError(f"Godot {scene_label} scene is missing its character sprite")
        if 'node name="SheriffBadge" type="Polygon2D"' not in scene_source:
            raise SmokeCheckError(f"Godot {scene_label} scene is missing its sheriff badge")
        if 'node name="CampaignBadge" type="Sprite2D"' not in scene_source:
            raise SmokeCheckError(f"Godot {scene_label} scene is missing its sheriff campaign badge")
        if 'node name="CampaignPKLabel" type="Label"' not in scene_source:
            raise SmokeCheckError(f"Godot {scene_label} scene is missing its PK marker")
    if 'campaign_status: String = ""' not in npc_script_text:
        raise SmokeCheckError("Godot NPC state does not expose sheriff campaign visuals")
    if 'campaign_status: String = ""' not in player_script_text:
        raise SmokeCheckError("Godot player state does not expose sheriff campaign visuals")
    if 'func lock_movement_until_release()' not in player_script_text:
        raise SmokeCheckError("Godot player is missing the post-input movement release lock")
    if '_movement_release_lock = _is_any_movement_key_physically_pressed()' not in player_script_text:
        raise SmokeCheckError("Godot movement release lock should only capture keys held during submission")
    if 'focus_owner.is_visible_in_tree() and focus_owner.editable' not in player_script_text:
        raise SmokeCheckError("Godot player should ignore stale focus on disabled text inputs")
    if not POLICE_BADGE_FILE.exists():
        raise SmokeCheckError("Godot police campaign badge asset is missing")

    actual_assets = {path.name for path in CHARACTER_ASSET_DIR.glob("*.svg")}
    missing_assets = sorted(EXPECTED_CHARACTER_ASSETS - actual_assets)
    if missing_assets:
        raise SmokeCheckError("Godot character pixel assets are missing: " + ", ".join(missing_assets))
    for asset_name in EXPECTED_CHARACTER_ASSETS:
        asset_text = (CHARACTER_ASSET_DIR / asset_name).read_text(encoding="utf-8")
        if 'shape-rendering="crispEdges"' not in asset_text or "\ufffd" in asset_text:
            raise SmokeCheckError(f"Godot character asset is invalid: {asset_name}")

    print("[OK] Godot contextual role UI, temporary nomination, CJK theme, compact town, and pixel characters are present.")


def load_json_list(path: Path, label: str) -> list[dict]:
    try:
        with path.open(encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        raise SmokeCheckError(f"{label} JSON is invalid: {exc}") from exc
    except OSError as exc:
        raise SmokeCheckError(f"could not read {label}: {exc}") from exc

    if not isinstance(data, list):
        raise SmokeCheckError(f"{label} must be a JSON list")
    return data


def require_keys(item: dict, keys: set[str], label: str) -> None:
    missing_keys = sorted(key for key in keys if key not in item)
    if missing_keys:
        raise SmokeCheckError(f"{label} missing keys: {', '.join(missing_keys)}")


def run_command(
    command: list[str],
    cwd: Path,
    fail_message: str,
    forbidden_output: tuple[str, ...] = (),
) -> None:
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    combined_output = "\n".join([result.stdout, result.stderr])
    output_error = next(
        (pattern for pattern in forbidden_output if pattern in combined_output),
        "",
    )
    if result.returncode != 0 or output_error:
        details = "\n".join(part.strip() for part in [result.stdout, result.stderr] if part.strip())
        if output_error:
            details = f"forbidden output detected: {output_error}\n{details}"
        raise SmokeCheckError(f"{fail_message}\n{details}")


class SmokeCheckError(Exception):
    pass


if __name__ == "__main__":
    raise SystemExit(main())
