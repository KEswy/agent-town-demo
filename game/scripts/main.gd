extends Node2D

const CHAT_URL := "http://127.0.0.1:8000/chat"
const MEMORY_URL := "http://127.0.0.1:8000/memory"
const CONFIG_RELOAD_URL := "http://127.0.0.1:8000/admin/reload-config"
const WOLF_GAME_START_URL := "http://127.0.0.1:8000/api/game/start"
const WOLF_GAME_STATE_URL_PREFIX := "http://127.0.0.1:8000/api/game/"
const WOLF_NIGHT_ACTION_URL := "http://127.0.0.1:8000/api/night/action"
const WOLF_NIGHT_RESOLVE_URL := "http://127.0.0.1:8000/api/night/resolve"
const WOLF_HUNTER_SHOT_URL := "http://127.0.0.1:8000/api/hunter/shot"
const WOLF_PLAYER_SPEECH_URL := "http://127.0.0.1:8000/api/day/player-speech"
const WOLF_NPC_SPEECH_URL := "http://127.0.0.1:8000/api/day/npc-speech"
const WOLF_END_FREE_ACTIVITY_URL := "http://127.0.0.1:8000/api/day/end-free-activity"
const WOLF_PRIVATE_CHAT_URL := "http://127.0.0.1:8000/api/day/private-chat"
const WOLF_SHERIFF_SIGNUP_URL := "http://127.0.0.1:8000/api/sheriff/signup"
const WOLF_SHERIFF_PLAYER_SPEECH_URL := "http://127.0.0.1:8000/api/sheriff/player-speech"
const WOLF_SHERIFF_NPC_SPEECH_URL := "http://127.0.0.1:8000/api/sheriff/npc-speech"
const WOLF_SHERIFF_WITHDRAW_URL := "http://127.0.0.1:8000/api/sheriff/withdraw"
const WOLF_SHERIFF_VOTE_URL := "http://127.0.0.1:8000/api/sheriff/vote"
const WOLF_SHERIFF_MEETING_ORDER_URL := "http://127.0.0.1:8000/api/sheriff/meeting-order"
const WOLF_SHERIFF_NOMINATE_URL := "http://127.0.0.1:8000/api/sheriff/nominate"
const WOLF_SHERIFF_TRANSFER_URL := "http://127.0.0.1:8000/api/sheriff/transfer"
const WOLF_COMBINED_VOTE_URL := "http://127.0.0.1:8000/api/vote/submit-and-resolve"
const PLAYER_ID := "player"
const WOLF_MENU_WIDTH := 520.0
const WOLF_MENU_TOP := 16.0
const WOLF_MENU_COLLAPSED_HEIGHT := 44.0
const WOLF_MENU_MIN_EXPANDED_HEIGHT := 500.0
const WOLF_MENU_MAX_EXPANDED_HEIGHT := 760.0
const CHARACTER_SKIN_PATHS := {
	"梅西": "res://assets/characters/messi.svg",
	"C罗": "res://assets/characters/ronaldo.svg",
	"周深": "res://assets/characters/zhou_shen.svg",
	"梅长苏": "res://assets/characters/mei_changsu.svg",
	"塞尔达": "res://assets/characters/zelda.svg",
	"小骑士": "res://assets/characters/little_knight.svg",
	"大黄蜂": "res://assets/characters/hornet.svg",
	"喜羊羊": "res://assets/characters/pleasant_goat.svg",
	"懒羊羊": "res://assets/characters/lazy_goat.svg",
	"洛洛": "res://assets/characters/luoluo.svg",
	"奇异博士": "res://assets/characters/doctor_strange.svg",
}

@onready var dialog_box: Control = $UI/DialogBox
@onready var player: CharacterBody2D = $Player
@onready var wolf_panel: Control = $UI/WolfPanel
@onready var wolf_content_panel: PanelContainer = $UI/WolfPanel/ContentPanel
@onready var wolf_scroll_container: ScrollContainer = $UI/WolfPanel/ContentPanel/ScrollContainer
@onready var wolf_menu_summary_label: Label = $UI/WolfPanel/HeaderPanel/HeaderMargin/HeaderRow/MenuSummaryLabel
@onready var wolf_menu_toggle_button: Button = $UI/WolfPanel/HeaderPanel/HeaderMargin/HeaderRow/ToggleButton
@onready var player_identity_block: VBoxContainer = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/PlayerIdentityBlock
@onready var player_role_label: Label = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/PlayerIdentityBlock/RoleLabel
@onready var wolf_teammates_label: Label = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/PlayerIdentityBlock/WolfTeammatesLabel
@onready var player_action_history_block: VBoxContainer = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/PlayerActionHistoryBlock
@onready var player_action_history_text: TextEdit = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/PlayerActionHistoryBlock/HistoryText
@onready var wolf_status_label: Label = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/StatusLabel
@onready var player_name_input: LineEdit = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/PlayerNameRow/PlayerNameInput
@onready var start_game_button: Button = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/PlayerNameRow/StartGameButton
@onready var player_role_option: OptionButton = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/PlayerRoleRow/PlayerRoleOption
@onready var llm_enabled_toggle: CheckButton = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/LLMSettingsRow/LLMEnabledToggle
@onready var refresh_state_button: Button = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/StateActionRow/RefreshStateButton
@onready var review_game_button: Button = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/StateActionRow/ReviewGameButton
@onready var wolf_game_info_label: Label = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/GameInfoLabel
@onready var sheriff_overview_label: Label = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/SheriffOverviewLabel
@onready var night_action_label: Label = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/NightActionLabel
@onready var night_action_row: HBoxContainer = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/NightActionRow
@onready var night_action_option: OptionButton = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/NightActionRow/NightActionOption
@onready var night_target_option: OptionButton = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/NightActionRow/NightTargetOption
@onready var submit_night_action_button: Button = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/NightActionRow/SubmitNightActionButton
@onready var resolve_night_button: Button = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/NightActionRow/ResolveNightButton
@onready var hunter_action_label: Label = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/HunterActionLabel
@onready var hunter_action_row: HBoxContainer = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/HunterActionRow
@onready var hunter_target_option: OptionButton = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/HunterActionRow/HunterTargetOption
@onready var hunter_shoot_button: Button = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/HunterActionRow/HunterShootButton
@onready var hunter_pass_button: Button = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/HunterActionRow/HunterPassButton
@onready var sheriff_action_label: Label = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/SheriffActionLabel
@onready var sheriff_choice_row: HBoxContainer = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/SheriffChoiceRow
@onready var sheriff_option: OptionButton = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/SheriffChoiceRow/SheriffOption
@onready var sheriff_action_button: Button = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/SheriffChoiceRow/SheriffActionButton
@onready var sheriff_withdrawal_row: HBoxContainer = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/SheriffWithdrawalRow
@onready var sheriff_continue_button: Button = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/SheriffWithdrawalRow/ContinueButton
@onready var sheriff_withdraw_button: Button = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/SheriffWithdrawalRow/WithdrawButton
@onready var sheriff_speech_input: LineEdit = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/SheriffSpeechRow/SheriffSpeechInput
@onready var sheriff_speech_button: Button = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/SheriffSpeechRow/SheriffSpeechButton
@onready var sheriff_speech_row: HBoxContainer = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/SheriffSpeechRow
@onready var day_speech_label: Label = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/DaySpeechLabel
@onready var temporary_nomination_row: HBoxContainer = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/TemporaryNominationRow
@onready var temporary_nomination_option: OptionButton = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/TemporaryNominationRow/TemporaryNominationOption
@onready var day_speech_row: HBoxContainer = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/DaySpeechRow
@onready var player_speech_input: LineEdit = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/DaySpeechRow/PlayerSpeechInput
@onready var submit_speech_button: Button = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/DaySpeechRow/SubmitSpeechButton
@onready var end_free_activity_button: Button = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/DaySpeechRow/EndFreeActivityButton
@onready var vote_action_label: Label = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/VoteActionLabel
@onready var vote_reason_input: LineEdit = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/VoteReasonInput
@onready var vote_action_row: HBoxContainer = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/VoteActionRow
@onready var vote_target_option: OptionButton = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/VoteActionRow/VoteTargetOption
@onready var submit_vote_button: Button = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/VoteActionRow/SubmitVoteButton
@onready var vote_result_label: Label = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/VoteResultLabel
@onready var character_grid: GridContainer = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/CharacterGrid
@onready var public_log_label: Label = $UI/WolfPanel/ContentPanel/ScrollContainer/Margin/VBox/PublicLogLabel
@onready var game_summary_overlay: Control = $UI/GameSummaryOverlay
@onready var game_summary_close_button: Button = $UI/GameSummaryOverlay/Panel/Margin/VBox/HeaderRow/CloseButton
@onready var game_summary_winner_label: Label = $UI/GameSummaryOverlay/Panel/Margin/VBox/WinnerLabel
@onready var game_summary_tabs: TabContainer = $UI/GameSummaryOverlay/Panel/Margin/VBox/SummaryTabs
@onready var game_summary_character_list: VBoxContainer = $UI/GameSummaryOverlay/Panel/Margin/VBox/SummaryTabs/CharacterReview/Margin/CharacterList
@onready var game_summary_timeline_label: Label = $UI/GameSummaryOverlay/Panel/Margin/VBox/SummaryTabs/TimelineReview/Margin/TimelineLabel
@onready var chat_request: HTTPRequest = $ChatRequest
@onready var memory_view_request: HTTPRequest = $MemoryViewRequest
@onready var memory_reset_request: HTTPRequest = $MemoryResetRequest
@onready var config_reload_request: HTTPRequest = $ConfigReloadRequest
@onready var game_start_request: HTTPRequest = $GameStartRequest
@onready var game_state_request: HTTPRequest = $GameStateRequest
@onready var night_action_request: HTTPRequest = $NightActionRequest
@onready var night_resolve_request: HTTPRequest = $NightResolveRequest
@onready var hunter_shot_request: HTTPRequest = $HunterShotRequest
@onready var player_speech_request: HTTPRequest = $PlayerSpeechRequest
@onready var npc_speech_request: HTTPRequest = $NpcSpeechRequest
@onready var end_free_activity_request: HTTPRequest = $EndFreeActivityRequest
@onready var private_chat_request: HTTPRequest = $PrivateChatRequest
@onready var sheriff_action_request: HTTPRequest = $SheriffActionRequest
@onready var sheriff_speech_request: HTTPRequest = $SheriffSpeechRequest
@onready var combined_vote_request: HTTPRequest = $CombinedVoteRequest
@onready var game_summary_request: HTTPRequest = $GameSummaryRequest

var _fallback_npc_name := ""
var _fallback_dialog_text := ""
var _current_npc_name := ""
var _current_npc_character_id := 0
var _is_requesting := false
var _is_viewing_memory := false
var _is_resetting_memory := false
var _is_reloading_config := false
var _is_starting_wolf_game := false
var _is_loading_wolf_state := false
var _is_submitting_night_action := false
var _is_resolving_night := false
var _is_submitting_hunter_shot := false
var _is_submitting_player_speech := false
var _is_generating_npc_speeches := false
var _is_ending_free_activity := false
var _is_private_chat_requesting := false
var _is_sheriff_action_requesting := false
var _is_sheriff_speech_requesting := false
var _is_submitting_vote := false
var _is_loading_game_summary := false
var _current_wolf_game_id := ""
var _current_wolf_phase := ""
var _current_wolf_day := 1
var _current_player_character_id := 0
var _current_player_role := ""
var _current_player_alive := false
var _current_meeting_speaker_id := 0
var _current_meeting_order: Array[int] = []
var _current_meeting_direction := ""
var _current_sheriff_speaker_id := 0
var _current_sheriff_id := 0
var _current_sheriff_data: Dictionary = {}
var _pending_sheriff_action := ""
var _wolf_character_names := {}
var _wolf_character_alive := {}
var _wolf_private_question_used := {}
var _wolf_campaign_status := {}
var _preserve_wolf_game_info_once := false
var _wolf_menu_expanded := false
var _wolf_menu_tween: Tween
var _summary_requested_game_id := ""
var _game_summary_data: Dictionary = {}
var _latest_wolf_game_data: Dictionary = {}
var _pending_player_speech_text := ""
var _pending_sheriff_speech_text := ""
var _pending_vote_reason_text := ""


func _ready() -> void:
	for npc in get_tree().get_nodes_in_group("npc"):
		npc.connect("dialog_requested", Callable(self, "_on_npc_dialog_requested"))
	chat_request.request_completed.connect(_on_chat_request_completed)
	memory_view_request.request_completed.connect(_on_memory_view_request_completed)
	memory_reset_request.request_completed.connect(_on_memory_reset_request_completed)
	config_reload_request.request_completed.connect(_on_config_reload_request_completed)
	game_start_request.request_completed.connect(_on_game_start_request_completed)
	game_state_request.request_completed.connect(_on_game_state_request_completed)
	night_action_request.request_completed.connect(_on_night_action_request_completed)
	night_resolve_request.request_completed.connect(_on_night_resolve_request_completed)
	hunter_shot_request.request_completed.connect(_on_hunter_shot_request_completed)
	player_speech_request.request_completed.connect(_on_player_speech_request_completed)
	npc_speech_request.request_completed.connect(_on_npc_speech_request_completed)
	end_free_activity_request.request_completed.connect(_on_end_free_activity_request_completed)
	private_chat_request.request_completed.connect(_on_private_chat_request_completed)
	sheriff_action_request.request_completed.connect(_on_sheriff_action_request_completed)
	sheriff_speech_request.request_completed.connect(_on_sheriff_speech_request_completed)
	combined_vote_request.request_completed.connect(_on_combined_vote_request_completed)
	game_summary_request.request_completed.connect(_on_game_summary_request_completed)
	start_game_button.pressed.connect(_on_start_game_button_pressed)
	refresh_state_button.pressed.connect(_on_refresh_state_button_pressed)
	review_game_button.pressed.connect(_on_review_game_button_pressed)
	submit_night_action_button.pressed.connect(_on_submit_night_action_button_pressed)
	resolve_night_button.pressed.connect(_on_resolve_night_button_pressed)
	night_action_option.item_selected.connect(_on_night_action_option_selected)
	hunter_shoot_button.pressed.connect(_on_hunter_shoot_button_pressed)
	hunter_pass_button.pressed.connect(_on_hunter_pass_button_pressed)
	sheriff_action_button.pressed.connect(_on_sheriff_action_button_pressed)
	sheriff_continue_button.pressed.connect(_on_sheriff_continue_button_pressed)
	sheriff_withdraw_button.pressed.connect(_on_sheriff_withdraw_button_pressed)
	sheriff_speech_button.pressed.connect(_on_sheriff_speech_button_pressed)
	sheriff_speech_input.text_submitted.connect(_on_sheriff_speech_input_submitted)
	submit_speech_button.pressed.connect(_on_submit_speech_button_pressed)
	player_speech_input.text_submitted.connect(_on_player_speech_input_submitted)
	end_free_activity_button.pressed.connect(_on_end_free_activity_button_pressed)
	submit_vote_button.pressed.connect(_on_submit_vote_button_pressed)
	vote_reason_input.text_submitted.connect(_on_vote_reason_input_submitted)
	wolf_menu_toggle_button.pressed.connect(_on_wolf_menu_toggle_button_pressed)
	game_summary_close_button.pressed.connect(_hide_game_summary)
	get_viewport().size_changed.connect(_on_viewport_size_changed)
	dialog_box.call("connect", "message_submitted", Callable(self, "_on_dialog_message_submitted"))
	dialog_box.call("connect", "memory_view_requested", Callable(self, "_on_memory_view_requested"))
	dialog_box.call("connect", "memory_reset_requested", Callable(self, "_on_memory_reset_requested"))
	dialog_box.call("connect", "config_reload_requested", Callable(self, "_on_config_reload_requested"))
	_configure_wolf_panel_focus()
	game_summary_tabs.set_tab_title(0, "角色复盘")
	game_summary_tabs.set_tab_title(1, "对局时间线")
	_populate_player_role_options()
	_update_contextual_panel_visibility()
	_set_wolf_menu_expanded(false, false)


func _on_wolf_menu_toggle_button_pressed() -> void:
	_set_wolf_menu_expanded(not _wolf_menu_expanded)


func _populate_player_role_options() -> void:
	player_role_option.clear()
	for option in [
		["随机身份", "random"],
		["狼人（测试）", "werewolf"],
		["预言家（测试）", "seer"],
		["女巫（测试）", "witch"],
		["猎人（测试）", "hunter"],
		["守卫（测试）", "guard"],
		["村民（测试）", "villager"],
	]:
		player_role_option.add_item(str(option[0]))
		player_role_option.set_item_metadata(player_role_option.get_item_count() - 1, option[1])


func _on_viewport_size_changed() -> void:
	_update_wolf_menu_size()


func _set_wolf_menu_expanded(expanded: bool, animate: bool = true) -> void:
	_wolf_menu_expanded = expanded
	if not expanded:
		_release_wolf_panel_focus()
		call_deferred("_release_wolf_panel_focus")
	if _wolf_menu_tween != null and _wolf_menu_tween.is_valid():
		_wolf_menu_tween.kill()

	var target_bottom := WOLF_MENU_TOP + _get_wolf_menu_target_height()
	if expanded:
		wolf_content_panel.visible = true

	if animate:
		_wolf_menu_tween = create_tween()
		_wolf_menu_tween.set_trans(Tween.TRANS_QUAD)
		_wolf_menu_tween.set_ease(Tween.EASE_OUT)
		_wolf_menu_tween.tween_property(wolf_panel, "offset_bottom", target_bottom, 0.22)
		if not expanded:
			_wolf_menu_tween.finished.connect(func(): wolf_content_panel.visible = false)
	else:
		wolf_panel.offset_bottom = target_bottom
		wolf_content_panel.visible = expanded

	wolf_menu_toggle_button.text = "▲" if expanded else "▼"
	wolf_menu_toggle_button.tooltip_text = "收起狼人杀面板" if expanded else "展开狼人杀面板"
	player.call("set_menu_safe_area", expanded, WOLF_MENU_WIDTH)


func _update_wolf_menu_size() -> void:
	var target_bottom := WOLF_MENU_TOP + _get_wolf_menu_target_height()
	if _wolf_menu_tween != null and _wolf_menu_tween.is_valid():
		_wolf_menu_tween.kill()
	wolf_panel.offset_bottom = target_bottom


func _get_wolf_menu_target_height() -> float:
	if not _wolf_menu_expanded:
		return WOLF_MENU_COLLAPSED_HEIGHT
	var viewport_height := float(get_viewport().get_visible_rect().size.y)
	return clampf(
		viewport_height * 0.82,
		WOLF_MENU_MIN_EXPANDED_HEIGHT,
		WOLF_MENU_MAX_EXPANDED_HEIGHT
	)


func _unhandled_input(event: InputEvent) -> void:
	if game_summary_overlay.visible:
		if event.is_action_pressed("ui_cancel"):
			_hide_game_summary()
			get_viewport().set_input_as_handled()
		return

	if event.is_action_pressed("ui_cancel") and dialog_box.call("is_open"):
		dialog_box.call("hide_dialog")
		get_viewport().set_input_as_handled()
		return

	if not event.is_action_pressed("interact"):
		return

	if dialog_box.call("is_open"):
		if dialog_box.call("has_text_focus"):
			return
		dialog_box.call("hide_dialog")
		get_viewport().set_input_as_handled()
		return

	var nearby_npc = _get_nearby_npc()
	if nearby_npc != null:
		nearby_npc.call("request_dialog")
		get_viewport().set_input_as_handled()


func _get_nearby_npc():
	for npc in get_tree().get_nodes_in_group("npc"):
		if npc.call("is_player_nearby"):
			return npc
	return null


func _on_npc_dialog_requested(npc_name: String, dialog_text: String, wolf_character_id: int) -> void:
	if _wolf_menu_expanded:
		_set_wolf_menu_expanded(false)
	_fallback_npc_name = npc_name
	_fallback_dialog_text = dialog_text
	_current_npc_name = npc_name
	_current_npc_character_id = wolf_character_id

	if _current_wolf_game_id.is_empty() or wolf_character_id <= 0:
		dialog_box.call("show_prompt", npc_name, "想问什么？输入问题后发送，后端会根据问题检索知识库。")
		return

	if not bool(_wolf_character_alive.get(wolf_character_id, true)):
		dialog_box.call("show_notice", npc_name, "我已经出局，不能再参与本局发言和投票。")
		return

	match _current_wolf_phase:
		"NIGHT":
			dialog_box.call("show_notice", npc_name, "现在是夜晚，不能进行普通交谈。请在控制面板完成夜晚行动。")
		"SHERIFF_SPEECH", "SHERIFF_RUNOFF_SPEECH":
			if wolf_character_id != _current_sheriff_speaker_id:
				var sheriff_speaker_name := str(_wolf_character_names.get(_current_sheriff_speaker_id, "当前候选人"))
				dialog_box.call("show_notice", npc_name, "还没轮到我进行警上发言。当前请先听 " + sheriff_speaker_name + "。")
			else:
				_request_current_npc_sheriff_speech(wolf_character_id, npc_name)
		"DAY_MEETING":
			if wolf_character_id != _current_meeting_speaker_id:
				var current_name := str(_wolf_character_names.get(_current_meeting_speaker_id, "当前角色"))
				dialog_box.call("show_notice", npc_name, "还没轮到我。当前请先听 " + current_name + " 发言。")
			else:
				_request_current_npc_meeting_speech(wolf_character_id, npc_name)
		"FREE_ACTIVITY":
			if not _current_player_alive:
				dialog_box.call("show_notice", npc_name, "你已经出局，不能进行私密追问。")
				return
			var used := bool(_wolf_private_question_used.get(wolf_character_id, false))
			var prompt := "这是今天第一次有效私密追问，你的说法会影响我的判断。"
			if used:
				prompt = "你今天已经向我进行过有效追问。可以继续问，但不会再次改变我的决策。"
			dialog_box.call("show_private_prompt", npc_name, prompt)
		"VOTE":
			dialog_box.call("show_notice", npc_name, "现在是投票阶段，请在控制面板完成投票。")
		"GAME_OVER":
			dialog_box.call("show_notice", npc_name, "本局游戏已经结束，可以在控制面板开始新游戏。")
		_:
			dialog_box.call("show_notice", npc_name, "当前阶段暂时不能交谈。")


func _request_current_npc_sheriff_speech(character_id: int, npc_name: String) -> void:
	if _is_sheriff_speech_requesting or _current_wolf_game_id.is_empty():
		return
	_is_sheriff_speech_requesting = true
	_update_sheriff_controls_from_current_state()
	wolf_status_label.text = "后端状态：正在生成 " + npc_name + " 的警上发言..."
	dialog_box.call("show_notice", npc_name, "正在整理警上竞选发言...")
	var body = {
		"game_id": _current_wolf_game_id,
		"character_id": character_id,
	}
	var headers = ["Content-Type: application/json"]
	var error = sheriff_speech_request.request(WOLF_SHERIFF_NPC_SPEECH_URL, headers, HTTPClient.METHOD_POST, JSON.stringify(body))
	if error != OK:
		_is_sheriff_speech_requesting = false
		_update_sheriff_controls_from_current_state()
		wolf_status_label.text = "后端状态：生成警上发言失败"
		dialog_box.call("show_notice", npc_name, "暂时无法生成警上发言，请确认后端已启动。")


func _request_current_npc_meeting_speech(character_id: int, npc_name: String) -> void:
	if _is_generating_npc_speeches or _current_wolf_game_id.is_empty():
		return

	_is_generating_npc_speeches = true
	_update_day_speech_controls_from_current_state()
	wolf_status_label.text = "后端状态：正在生成 " + npc_name + " 的发言..."
	dialog_box.call("show_notice", npc_name, "正在结合前序发言整理判断...")

	var body = {
		"game_id": _current_wolf_game_id,
		"character_id": character_id
	}
	var headers = ["Content-Type: application/json"]
	var error = npc_speech_request.request(WOLF_NPC_SPEECH_URL, headers, HTTPClient.METHOD_POST, JSON.stringify(body))
	if error != OK:
		_is_generating_npc_speeches = false
		_update_day_speech_controls_from_current_state()
		wolf_status_label.text = "后端状态：生成 NPC 发言失败"
		dialog_box.call("show_notice", npc_name, "无法连接 Python 后端。")


func _on_dialog_message_submitted(message: String) -> void:
	if _is_busy() or _current_npc_name.is_empty():
		return
	if _current_wolf_phase == "FREE_ACTIVITY" and _current_npc_character_id > 0:
		_submit_private_chat(message)
		return

	_is_requesting = true
	dialog_box.call("set_waiting")
	dialog_box.call("show_dialog", _current_npc_name, "正在连接 Python 后端...")

	var body = {
		"npc_name": _current_npc_name,
		"message": message,
		"player_id": PLAYER_ID
	}
	var headers = ["Content-Type: application/json"]
	var error = chat_request.request(CHAT_URL, headers, HTTPClient.METHOD_POST, JSON.stringify(body))
	if error != OK:
		dialog_box.call("show_dialog", _fallback_npc_name, _fallback_dialog_text)
		dialog_box.call("set_ready_for_input")
		_is_requesting = false


func _submit_private_chat(message: String) -> void:
	_is_private_chat_requesting = true
	dialog_box.call("set_waiting")
	dialog_box.call("show_dialog", _current_npc_name, "正在结合会议内容和私有记忆回答...")

	var body = {
		"game_id": _current_wolf_game_id,
		"npc_character_id": _current_npc_character_id,
		"question": message
	}
	var headers = ["Content-Type: application/json"]
	var error = private_chat_request.request(WOLF_PRIVATE_CHAT_URL, headers, HTTPClient.METHOD_POST, JSON.stringify(body))
	if error != OK:
		_is_private_chat_requesting = false
		dialog_box.call("show_private_prompt", _current_npc_name, "私密追问失败：无法连接 Python 后端。")


func _on_memory_view_requested() -> void:
	if _is_busy() or _current_npc_name.is_empty():
		return

	_is_viewing_memory = true
	dialog_box.call("set_waiting")
	dialog_box.call("show_dialog", _current_npc_name, "正在读取这个 NPC 对你的记忆...")

	var url = MEMORY_URL + "/" + PLAYER_ID.uri_encode() + "/" + _current_npc_name.uri_encode()
	var error = memory_view_request.request(url, [], HTTPClient.METHOD_GET)
	if error != OK:
		_is_viewing_memory = false
		dialog_box.call("set_ready_for_input")
		dialog_box.call("show_dialog", _current_npc_name, "查看记忆失败：无法连接 Python 后端。")


func _on_memory_reset_requested() -> void:
	if _is_busy() or _current_npc_name.is_empty():
		return

	_is_resetting_memory = true
	dialog_box.call("set_waiting")
	dialog_box.call("show_dialog", _current_npc_name, "正在清空这个 NPC 对你的记忆...")

	var url = MEMORY_URL + "/" + PLAYER_ID.uri_encode() + "/" + _current_npc_name.uri_encode()
	var error = memory_reset_request.request(url, [], HTTPClient.METHOD_DELETE)
	if error != OK:
		_is_resetting_memory = false
		dialog_box.call("set_ready_for_input")
		dialog_box.call("show_dialog", _current_npc_name, "清空记忆失败：无法连接 Python 后端。")


func _on_config_reload_requested() -> void:
	if _is_busy() or _current_npc_name.is_empty():
		return

	_is_reloading_config = true
	dialog_box.call("set_waiting")
	dialog_box.call("show_dialog", _current_npc_name, "正在重新加载 NPC 人设和知识库...")

	var error = config_reload_request.request(CONFIG_RELOAD_URL, [], HTTPClient.METHOD_POST)
	if error != OK:
		_is_reloading_config = false
		dialog_box.call("set_ready_for_input")
		dialog_box.call("show_dialog", _current_npc_name, "重载配置失败：无法连接 Python 后端。")


func _on_start_game_button_pressed() -> void:
	if _is_starting_wolf_game:
		return

	_is_starting_wolf_game = true
	_reset_game_summary()
	wolf_menu_summary_label.text = "正在开始..."
	start_game_button.disabled = true
	wolf_status_label.text = "后端状态：正在创建 12 人局..."
	wolf_game_info_label.text = "正在随机分配身份。"
	night_action_label.text = "夜晚行动：等待游戏创建。"
	sheriff_action_label.text = "警长操作：等待游戏创建。"
	day_speech_label.text = "白天发言：等待游戏创建。"
	vote_action_label.text = "白天投票：等待游戏创建。"
	vote_result_label.text = "票型：尚未公布"
	public_log_label.text = "公开日志：等待后端返回。"
	_disable_night_controls()
	_disable_sheriff_controls()
	_disable_day_speech_controls()
	_disable_vote_controls()
	_clear_character_grid()

	var player_name := player_name_input.text.strip_edges()
	if player_name.is_empty():
		player_name = "玩家"

	var body = {
		"player_name": player_name,
		"npc_count": 11,
		"player_role": str(_get_selected_option_metadata(player_role_option, "random")),
		"enable_llm": llm_enabled_toggle.button_pressed,
		"enable_rag": true
	}
	var headers = ["Content-Type: application/json"]
	var error = game_start_request.request(WOLF_GAME_START_URL, headers, HTTPClient.METHOD_POST, JSON.stringify(body))
	if error != OK:
		_is_starting_wolf_game = false
		start_game_button.disabled = false
		wolf_status_label.text = "后端状态：连接失败"
		wolf_game_info_label.text = "请先启动 FastAPI 后端。"
		night_action_label.text = "夜晚行动：后端未连接。"
		day_speech_label.text = "白天发言：后端未连接。"
		vote_action_label.text = "白天投票：后端未连接。"
		public_log_label.text = "公开日志：暂无"


func _on_refresh_state_button_pressed() -> void:
	if _is_loading_wolf_state:
		return

	if _current_wolf_game_id.is_empty():
		wolf_status_label.text = "后端状态：还没有可刷新的游戏"
		return

	_request_wolf_game_state()


func _on_review_game_button_pressed() -> void:
	if not _game_summary_data.is_empty():
		_show_game_summary()
	elif _current_wolf_phase == "GAME_OVER":
		_request_game_summary()


func _on_submit_night_action_button_pressed() -> void:
	if _is_submitting_night_action or _current_wolf_game_id.is_empty() or _current_player_character_id <= 0:
		return

	if _current_wolf_phase != "NIGHT":
		wolf_status_label.text = "后端状态：当前不是夜晚阶段"
		return

	var action_type := _get_selected_night_action_type()
	var target_id = null
	if _night_action_requires_target(action_type):
		if night_target_option.get_item_count() == 0:
			wolf_status_label.text = "后端状态：没有可选目标"
			return
		target_id = night_target_option.get_selected_id()

	_is_submitting_night_action = true
	_set_night_buttons_disabled(true)
	wolf_status_label.text = "后端状态：正在提交夜晚行动..."

	var body = {
		"game_id": _current_wolf_game_id,
		"character_id": _current_player_character_id,
		"action_type": action_type,
		"target_id": target_id
	}
	var headers = ["Content-Type: application/json"]
	var error = night_action_request.request(WOLF_NIGHT_ACTION_URL, headers, HTTPClient.METHOD_POST, JSON.stringify(body))
	if error != OK:
		_is_submitting_night_action = false
		_update_night_controls_from_current_state()
		wolf_status_label.text = "后端状态：提交夜晚行动失败"


func _on_night_action_option_selected(_index: int) -> void:
	if not _latest_wolf_game_data.is_empty():
		_refresh_night_target_options(_latest_wolf_game_data)


func _on_hunter_shoot_button_pressed() -> void:
	if hunter_target_option.get_item_count() == 0:
		wolf_status_label.text = "后端状态：猎人没有可选目标"
		return
	_submit_hunter_shot(hunter_target_option.get_selected_id())


func _on_hunter_pass_button_pressed() -> void:
	_submit_hunter_shot(null)


func _submit_hunter_shot(target_id: Variant) -> void:
	if (
		_is_submitting_hunter_shot
		or _current_wolf_game_id.is_empty()
		or _current_wolf_phase != "HUNTER_SHOT"
	):
		return
	_is_submitting_hunter_shot = true
	hunter_target_option.disabled = true
	hunter_shoot_button.disabled = true
	hunter_pass_button.disabled = true
	wolf_status_label.text = "后端状态：正在提交猎人选择..."
	var body = {
		"game_id": _current_wolf_game_id,
		"character_id": _current_player_character_id,
		"target_id": target_id
	}
	var headers = ["Content-Type: application/json"]
	var error = hunter_shot_request.request(
		WOLF_HUNTER_SHOT_URL,
		headers,
		HTTPClient.METHOD_POST,
		JSON.stringify(body)
	)
	if error != OK:
		_is_submitting_hunter_shot = false
		wolf_status_label.text = "后端状态：猎人选择提交失败"
		_update_hunter_controls(_latest_wolf_game_data)


func _on_resolve_night_button_pressed() -> void:
	if _is_resolving_night or _current_wolf_game_id.is_empty():
		return

	if _current_wolf_phase != "NIGHT":
		wolf_status_label.text = "后端状态：当前不是夜晚阶段"
		return

	_is_resolving_night = true
	_set_night_buttons_disabled(true)
	wolf_status_label.text = "后端状态：正在结算夜晚..."

	var body = {"game_id": _current_wolf_game_id}
	var headers = ["Content-Type: application/json"]
	var error = night_resolve_request.request(WOLF_NIGHT_RESOLVE_URL, headers, HTTPClient.METHOD_POST, JSON.stringify(body))
	if error != OK:
		_is_resolving_night = false
		_update_night_controls_from_current_state()
		wolf_status_label.text = "后端状态：结算夜晚失败"


func _on_submit_speech_button_pressed() -> void:
	if _is_submitting_player_speech or _current_wolf_game_id.is_empty() or _current_player_character_id <= 0:
		return

	if not _is_day_speech_phase():
		wolf_status_label.text = "后端状态：当前不是白天发言阶段"
		return

	if not _current_player_alive:
		wolf_status_label.text = "后端状态：玩家已出局，不能发言"
		return

	var speech := player_speech_input.text.strip_edges()
	if speech.is_empty():
		wolf_status_label.text = "后端状态：请输入白天发言"
		return

	_is_submitting_player_speech = true
	_set_day_speech_buttons_disabled(true)
	wolf_status_label.text = "后端状态：正在提交玩家发言..."

	var body = {
		"game_id": _current_wolf_game_id,
		"character_id": _current_player_character_id,
		"speech": speech,
		"temporary_nomination_target_id": null,
	}
	if _current_sheriff_id == _current_player_character_id:
		var temporary_target = _get_selected_option_metadata(temporary_nomination_option, 0)
		if int(temporary_target) > 0:
			body["temporary_nomination_target_id"] = int(temporary_target)
	_pending_player_speech_text = speech
	_finish_gameplay_text_submission(player_speech_input)
	var headers = ["Content-Type: application/json"]
	var error = player_speech_request.request(WOLF_PLAYER_SPEECH_URL, headers, HTTPClient.METHOD_POST, JSON.stringify(body))
	if error != OK:
		_is_submitting_player_speech = false
		_restore_failed_gameplay_text(player_speech_input, _pending_player_speech_text)
		_update_day_speech_controls_from_current_state()
		wolf_status_label.text = "后端状态：提交发言失败"


func _on_player_speech_input_submitted(_speech: String) -> void:
	_on_submit_speech_button_pressed()


func _on_end_free_activity_button_pressed() -> void:
	if _is_ending_free_activity or _current_wolf_game_id.is_empty():
		return

	if _current_wolf_phase != "FREE_ACTIVITY":
		wolf_status_label.text = "后端状态：当前不是自由活动阶段"
		return

	_is_ending_free_activity = true
	_update_day_speech_controls_from_current_state()
	wolf_status_label.text = "后端状态：正在结束自由活动..."

	var body = {"game_id": _current_wolf_game_id}
	var headers = ["Content-Type: application/json"]
	var error = end_free_activity_request.request(WOLF_END_FREE_ACTIVITY_URL, headers, HTTPClient.METHOD_POST, JSON.stringify(body))
	if error != OK:
		_is_ending_free_activity = false
		_update_day_speech_controls_from_current_state()
		wolf_status_label.text = "后端状态：结束自由活动失败"


func _on_sheriff_action_button_pressed() -> void:
	_submit_sheriff_action()


func _on_sheriff_continue_button_pressed() -> void:
	_submit_sheriff_action(false)


func _on_sheriff_withdraw_button_pressed() -> void:
	_submit_sheriff_action(true)


func _submit_sheriff_action(withdraw_choice: Variant = null) -> void:
	if _is_sheriff_action_requesting or _current_wolf_game_id.is_empty():
		return

	var body: Dictionary = {
		"game_id": _current_wolf_game_id,
		"character_id": _current_player_character_id,
	}
	var url := ""
	_pending_sheriff_action = _current_wolf_phase
	match _current_wolf_phase:
		"SHERIFF_SIGNUP":
			url = WOLF_SHERIFF_SIGNUP_URL
			body["run_for_sheriff"] = bool(_get_selected_option_metadata(sheriff_option, false))
		"SHERIFF_WITHDRAWAL":
			if withdraw_choice == null:
				return
			url = WOLF_SHERIFF_WITHDRAW_URL
			body["withdraw"] = bool(withdraw_choice)
		"SHERIFF_VOTE", "SHERIFF_RUNOFF_VOTE":
			url = WOLF_SHERIFF_VOTE_URL
			body["target_id"] = (
				_get_selected_option_metadata(sheriff_option, null)
				if bool(_current_sheriff_data.get("player_can_vote", false))
				else null
			)
		"MEETING_ORDER":
			url = WOLF_SHERIFF_MEETING_ORDER_URL
			body["side"] = str(_get_selected_option_metadata(sheriff_option, "left"))
		"SHERIFF_NOMINATION":
			url = WOLF_SHERIFF_NOMINATE_URL
			body["target_id"] = int(_get_selected_option_metadata(sheriff_option, 0))
		"BADGE_TRANSFER":
			url = WOLF_SHERIFF_TRANSFER_URL
			var transfer_target = _get_selected_option_metadata(sheriff_option, null)
			body["target_id"] = transfer_target if transfer_target != 0 else null
		_:
			return

	_is_sheriff_action_requesting = true
	_update_sheriff_controls_from_current_state()
	wolf_status_label.text = "后端状态：正在提交警长操作..."
	var headers = ["Content-Type: application/json"]
	var error = sheriff_action_request.request(url, headers, HTTPClient.METHOD_POST, JSON.stringify(body))
	if error != OK:
		_is_sheriff_action_requesting = false
		_update_sheriff_controls_from_current_state()
		wolf_status_label.text = "后端状态：警长操作提交失败"


func _on_sheriff_speech_button_pressed() -> void:
	if _is_sheriff_speech_requesting or _current_wolf_game_id.is_empty():
		return
	if _current_wolf_phase not in ["SHERIFF_SPEECH", "SHERIFF_RUNOFF_SPEECH"]:
		return
	if _current_sheriff_speaker_id != _current_player_character_id:
		wolf_status_label.text = "后端状态：当前不是你的警上发言回合"
		return
	var speech := sheriff_speech_input.text.strip_edges()
	if speech.is_empty():
		wolf_status_label.text = "后端状态：警上发言不能为空"
		return

	_is_sheriff_speech_requesting = true
	_update_sheriff_controls_from_current_state()
	var body = {
		"game_id": _current_wolf_game_id,
		"character_id": _current_player_character_id,
		"speech": speech,
	}
	_pending_sheriff_speech_text = speech
	_finish_gameplay_text_submission(sheriff_speech_input)
	var headers = ["Content-Type: application/json"]
	var error = sheriff_speech_request.request(WOLF_SHERIFF_PLAYER_SPEECH_URL, headers, HTTPClient.METHOD_POST, JSON.stringify(body))
	if error != OK:
		_is_sheriff_speech_requesting = false
		_restore_failed_gameplay_text(sheriff_speech_input, _pending_sheriff_speech_text)
		_update_sheriff_controls_from_current_state()
		wolf_status_label.text = "后端状态：提交警上发言失败"


func _on_sheriff_speech_input_submitted(_speech: String) -> void:
	_on_sheriff_speech_button_pressed()


func _on_submit_vote_button_pressed() -> void:
	if _is_submitting_vote or _current_wolf_game_id.is_empty() or _current_player_character_id <= 0:
		return

	if not _is_vote_phase():
		wolf_status_label.text = "后端状态：当前不是白天投票阶段"
		return

	if _current_player_alive and vote_target_option.get_item_count() == 0:
		wolf_status_label.text = "后端状态：没有可投票目标"
		return

	_is_submitting_vote = true
	_set_vote_buttons_disabled(true)
	wolf_status_label.text = "后端状态：正在同时生成并结算全部投票..."

	var vote_reason := vote_reason_input.text.strip_edges()
	var body = {
		"game_id": _current_wolf_game_id,
		"character_id": _current_player_character_id,
		"target_id": vote_target_option.get_selected_id() if _current_player_alive else null,
		"reason": vote_reason,
	}
	_pending_vote_reason_text = vote_reason
	_finish_gameplay_text_submission(vote_reason_input)
	var headers = ["Content-Type: application/json"]
	var error = combined_vote_request.request(WOLF_COMBINED_VOTE_URL, headers, HTTPClient.METHOD_POST, JSON.stringify(body))
	if error != OK:
		_is_submitting_vote = false
		_restore_failed_gameplay_text(vote_reason_input, _pending_vote_reason_text)
		_update_vote_controls_from_current_state()
		wolf_status_label.text = "后端状态：同时投票失败"


func _on_vote_reason_input_submitted(_reason: String) -> void:
	_on_submit_vote_button_pressed()


func _get_selected_option_metadata(option: OptionButton, fallback: Variant) -> Variant:
	if option.get_item_count() == 0 or option.selected < 0:
		return fallback
	var metadata = option.get_item_metadata(option.selected)
	return metadata if metadata != null else fallback


func _on_chat_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_requesting = false

	if not dialog_box.call("is_open"):
		return

	dialog_box.call("set_ready_for_input")

	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		dialog_box.call("show_dialog", _fallback_npc_name, _fallback_dialog_text)
		return

	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error != OK or typeof(json.data) != TYPE_DICTIONARY or not json.data.has("reply"):
		dialog_box.call("show_dialog", _fallback_npc_name, _fallback_dialog_text)
		return

	var response_npc_name = json.data.get("npc_name", _fallback_npc_name)
	var knowledge_titles = json.data.get("knowledge_titles", [])
	if knowledge_titles.is_empty() and json.data.get("knowledge_title", "") != "":
		knowledge_titles = [json.data["knowledge_title"]]
	var memory_count = json.data.get("memory_count", 0)
	var relationship_level = json.data.get("relationship_level", "")
	var retrieval_mode = str(json.data.get("retrieval_mode", "keyword"))
	dialog_box.call("show_response", response_npc_name, json.data["reply"], knowledge_titles, memory_count, relationship_level, retrieval_mode)


func _on_memory_view_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_viewing_memory = false

	if not dialog_box.call("is_open"):
		return

	dialog_box.call("set_ready_for_input")

	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		dialog_box.call("show_dialog", _current_npc_name, "查看记忆失败，请确认 Python 后端已启动。")
		return

	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error != OK or typeof(json.data) != TYPE_ARRAY:
		dialog_box.call("show_dialog", _current_npc_name, "查看记忆失败：后端返回的数据格式不正确。")
		return

	dialog_box.call("show_dialog", _current_npc_name, _format_memory_preview(json.data))


func _on_memory_reset_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_resetting_memory = false

	if not dialog_box.call("is_open"):
		return

	dialog_box.call("set_ready_for_input")

	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		dialog_box.call("show_dialog", _current_npc_name, "清空记忆失败，请确认 Python 后端已启动。")
		return

	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error != OK or typeof(json.data) != TYPE_DICTIONARY:
		dialog_box.call("show_dialog", _current_npc_name, "记忆已清空。")
		return

	var deleted_count = json.data.get("deleted_count", 0)
	dialog_box.call("show_dialog", _current_npc_name, "记忆已清空，共删除 " + str(deleted_count) + " 条记录。")


func _on_config_reload_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_reloading_config = false

	if not dialog_box.call("is_open"):
		return

	dialog_box.call("set_ready_for_input")

	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		dialog_box.call("show_dialog", _current_npc_name, "重载配置失败，请确认 Python 后端已启动。")
		return

	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error != OK or typeof(json.data) != TYPE_DICTIONARY:
		dialog_box.call("show_dialog", _current_npc_name, "配置已重新加载。")
		return

	var npc_count = json.data.get("npc_count", 0)
	var knowledge_count = json.data.get("knowledge_count", 0)
	dialog_box.call("show_dialog", _current_npc_name, "配置已重新加载：NPC " + str(npc_count) + " 个，知识 " + str(knowledge_count) + " 条。")


func _on_game_start_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_starting_wolf_game = false
	start_game_button.disabled = false

	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		wolf_status_label.text = "后端状态：创建游戏失败"
		wolf_game_info_label.text = "请确认 FastAPI 后端已启动。"
		return

	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error != OK or typeof(json.data) != TYPE_DICTIONARY:
		wolf_status_label.text = "后端状态：响应格式错误"
		wolf_game_info_label.text = "后端没有返回有效的游戏数据。"
		return

	_render_wolf_game(json.data)
	_current_wolf_game_id = str(json.data.get("game_id", ""))
	refresh_state_button.disabled = _current_wolf_game_id.is_empty()
	if not _current_wolf_game_id.is_empty():
		_request_wolf_game_state()


func _on_game_state_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_loading_wolf_state = false
	refresh_state_button.disabled = _current_wolf_game_id.is_empty()

	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		_preserve_wolf_game_info_once = false
		wolf_status_label.text = "后端状态：刷新状态失败"
		return

	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error != OK or typeof(json.data) != TYPE_DICTIONARY:
		_preserve_wolf_game_info_once = false
		wolf_status_label.text = "后端状态：状态响应格式错误"
		return

	_render_wolf_game(json.data)


func _on_night_action_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_submitting_night_action = false
	_update_night_controls_from_current_state()

	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		wolf_status_label.text = "后端状态：提交夜晚行动失败"
		return

	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error == OK and typeof(json.data) == TYPE_DICTIONARY:
		wolf_status_label.text = "后端状态：" + str(json.data.get("message", "行动已记录。"))
	else:
		wolf_status_label.text = "后端状态：行动已记录"


func _on_night_resolve_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_resolving_night = false
	_update_night_controls_from_current_state()

	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		wolf_status_label.text = "后端状态：结算夜晚失败"
		return

	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error == OK and typeof(json.data) == TYPE_DICTIONARY:
		var public_message = json.data.get("public_message", "夜晚已结算。")
		var private_result = _format_player_private_night_result(json.data.get("player_private_result", {}))
		wolf_game_info_label.text = str(public_message) + private_result
	else:
		wolf_game_info_label.text = "夜晚已结算。"

	_request_wolf_game_state()


func _on_hunter_shot_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_submitting_hunter_shot = false
	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		wolf_status_label.text = "后端状态：猎人选择提交失败"
		_update_hunter_controls(_latest_wolf_game_data)
		return

	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error == OK and typeof(json.data) == TYPE_DICTIONARY:
		wolf_status_label.text = "后端状态：" + str(json.data.get("message", "猎人选择已结算。"))
	else:
		wolf_status_label.text = "后端状态：猎人选择已结算"
	_request_wolf_game_state()


func _on_player_speech_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_submitting_player_speech = false
	_update_day_speech_controls_from_current_state()

	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		_restore_failed_gameplay_text(player_speech_input, _pending_player_speech_text)
		wolf_status_label.text = "后端状态：提交发言失败"
		return

	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error == OK and typeof(json.data) == TYPE_DICTIONARY:
		wolf_status_label.text = "后端状态：玩家发言已记录"
		wolf_game_info_label.text = _format_player_speech_result(json.data)
	else:
		wolf_status_label.text = "后端状态：玩家发言已记录"
		wolf_game_info_label.text = "玩家发言已记录。"

	_pending_player_speech_text = ""
	_request_wolf_game_state(true)


func _on_npc_speech_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_generating_npc_speeches = false
	_update_day_speech_controls_from_current_state()

	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		wolf_status_label.text = "后端状态：生成 NPC 发言失败"
		if dialog_box.call("is_open"):
			dialog_box.call("show_notice", _current_npc_name, _get_http_error_message(body, "当前不能生成这名 NPC 的发言。"))
		return

	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error == OK and typeof(json.data) == TYPE_DICTIONARY:
		var speech_data = json.data.get("speech", {})
		if typeof(speech_data) == TYPE_DICTIONARY:
			var speaker_name := str(speech_data.get("name", _current_npc_name))
			var speech_text := str(speech_data.get("speech", "暂时没有发言。"))
			var evidence_titles = speech_data.get("evidence_titles", [])
			var retrieval_mode := str(speech_data.get("retrieval_mode", "keyword"))
			var llm_used := bool(speech_data.get("llm_used", false))
			var llm_provider := str(speech_data.get("llm_provider", "rule"))
			var llm_fallback_reason := str(speech_data.get("llm_fallback_reason", ""))
			wolf_status_label.text = "后端状态：" + speaker_name + " 已完成发言"
			wolf_game_info_label.text = speaker_name + "：" + speech_text
			if dialog_box.call("is_open"):
					dialog_box.call(
					"show_public_evidence_notice",
					speaker_name,
					speech_text,
					evidence_titles,
					retrieval_mode,
					llm_used,
					llm_provider,
					llm_fallback_reason,
					speech_data.get("llm_validation_failure", {})
				)
	else:
		wolf_status_label.text = "后端状态：NPC 发言已生成"

	_request_wolf_game_state(true)


func _on_end_free_activity_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_ending_free_activity = false
	_update_day_speech_controls_from_current_state()

	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		wolf_status_label.text = "后端状态：结束自由活动失败"
		return

	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error == OK and typeof(json.data) == TYPE_DICTIONARY:
		wolf_status_label.text = "后端状态：" + str(json.data.get("message", "已进入投票阶段。"))
	else:
		wolf_status_label.text = "后端状态：已进入投票阶段"

	_request_wolf_game_state()


func _on_private_chat_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_private_chat_requesting = false

	if not dialog_box.call("is_open"):
		return

	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		dialog_box.call("show_private_prompt", _current_npc_name, _get_http_error_message(body, "私密追问失败，请稍后重试。"))
		return

	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error != OK or typeof(json.data) != TYPE_DICTIONARY:
		dialog_box.call("show_private_prompt", _current_npc_name, "后端返回的私密回答格式不正确。")
		return

	var npc_name := str(json.data.get("npc_name", _current_npc_name))
	var reply := str(json.data.get("reply", "暂时没有回答。"))
	var effective := bool(json.data.get("effective", false))
	var can_influence_again := bool(json.data.get("can_influence_again", false))
	var knowledge_titles = json.data.get("knowledge_titles", [])
	var retrieval_mode := str(json.data.get("retrieval_mode", "keyword"))
	var llm_used := bool(json.data.get("llm_used", false))
	var llm_provider := str(json.data.get("llm_provider", "rule"))
	var llm_fallback_reason := str(json.data.get("llm_fallback_reason", ""))
	var easter_egg_triggered := bool(json.data.get("easter_egg_triggered", false))
	var easter_egg_first_time := bool(json.data.get("easter_egg_first_time", false))
	var effect_note := "\n\n本次追问已影响该 NPC 的判断。"
	if easter_egg_triggered:
		effect_note = (
			"\n\n发现新的角色彩蛋。本次不会消耗今天的有效追问机会。"
			if easter_egg_first_time
			else "\n\n这个角色彩蛋已经触发过。本次仍不会消耗有效追问机会。"
		)
	elif not effective and can_influence_again:
		effect_note = "\n\n本次追问尚未影响该 NPC 的判断，明确对象后仍可进行今天的有效追问。"
	elif not effective:
		effect_note = "\n\n本次是追加追问，不会再次改变该 NPC 的决策。"
	if effective:
		_wolf_private_question_used[_current_npc_character_id] = true
	dialog_box.call(
		"show_private_response",
		npc_name,
		reply + effect_note,
		knowledge_titles,
		retrieval_mode,
		llm_used,
		llm_provider,
		llm_fallback_reason,
		json.data.get("llm_validation_failure", {})
	)
	_request_wolf_game_state()


func _on_sheriff_action_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_sheriff_action_requesting = false
	_update_sheriff_controls_from_current_state()
	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		wolf_status_label.text = "后端状态：" + _get_http_error_message(body, "警长操作失败")
		return

	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error == OK and typeof(json.data) == TYPE_DICTIONARY:
		wolf_status_label.text = "后端状态：" + str(json.data.get("message", "警长操作已完成。"))
		if _pending_sheriff_action in ["SHERIFF_VOTE", "SHERIFF_RUNOFF_VOTE"]:
			wolf_game_info_label.text = _format_sheriff_vote_result(json.data)
	else:
		wolf_status_label.text = "后端状态：警长操作已完成"
	_pending_sheriff_action = ""
	_request_wolf_game_state(true)


func _on_sheriff_speech_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_sheriff_speech_requesting = false
	_update_sheriff_controls_from_current_state()
	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		if not _pending_sheriff_speech_text.is_empty():
			_restore_failed_gameplay_text(sheriff_speech_input, _pending_sheriff_speech_text)
		wolf_status_label.text = "后端状态：" + _get_http_error_message(body, "警上发言失败")
		if dialog_box.call("is_open"):
			dialog_box.call("show_notice", _current_npc_name, _get_http_error_message(body, "警上发言失败，请稍后重试。"))
		return

	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error == OK and typeof(json.data) == TYPE_DICTIONARY:
		var speech = json.data.get("speech", {})
		if typeof(speech) == TYPE_DICTIONARY:
			var speaker_name := str(speech.get("name", _current_npc_name))
			var content := str(speech.get("speech", "警上发言已完成。"))
			if dialog_box.call("is_open"):
					dialog_box.call(
					"show_public_evidence_notice",
					speaker_name,
					content,
					speech.get("evidence_titles", []),
					str(speech.get("retrieval_mode", "keyword")),
					bool(speech.get("llm_used", false)),
					str(speech.get("llm_provider", "rule")),
					str(speech.get("llm_fallback_reason", "")),
					speech.get("llm_validation_failure", {})
				)
		_pending_sheriff_speech_text = ""
		sheriff_speech_input.text = ""
		wolf_status_label.text = "后端状态：警上发言已记录"
	else:
		wolf_status_label.text = "后端状态：警上发言已记录"
	_request_wolf_game_state(true)


func _on_combined_vote_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_submitting_vote = false
	_update_vote_controls_from_current_state()
	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		_restore_failed_gameplay_text(vote_reason_input, _pending_vote_reason_text)
		wolf_status_label.text = "后端状态：" + _get_http_error_message(body, "同时投票失败")
		return

	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error == OK and typeof(json.data) == TYPE_DICTIONARY:
		vote_result_label.text = _format_combined_vote_result(json.data)
		wolf_game_info_label.text = str(json.data.get("public_message", "投票已结算。"))
		wolf_status_label.text = "后端状态：全部票型已同时公布并结算"
		_pending_vote_reason_text = ""
		vote_reason_input.text = ""
	else:
		vote_result_label.text = "票型：后端返回格式不正确"
		wolf_status_label.text = "后端状态：投票已结算"
	_request_wolf_game_state(true)


func _on_game_summary_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_is_loading_game_summary = false
	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		_summary_requested_game_id = ""
		review_game_button.disabled = false
		wolf_status_label.text = "后端状态：读取本局复盘失败"
		return

	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error != OK or typeof(json.data) != TYPE_DICTIONARY:
		_summary_requested_game_id = ""
		review_game_button.disabled = false
		wolf_status_label.text = "后端状态：复盘数据格式错误"
		return

	_game_summary_data = json.data
	_render_game_summary(_game_summary_data)
	review_game_button.disabled = false
	_show_game_summary()


func _is_busy() -> bool:
	return (
		_is_requesting
		or _is_viewing_memory
		or _is_resetting_memory
		or _is_reloading_config
		or _is_starting_wolf_game
		or _is_loading_wolf_state
		or _is_submitting_night_action
		or _is_resolving_night
		or _is_submitting_hunter_shot
		or _is_submitting_player_speech
		or _is_generating_npc_speeches
		or _is_ending_free_activity
		or _is_private_chat_requesting
		or _is_sheriff_action_requesting
		or _is_sheriff_speech_requesting
		or _is_submitting_vote
		or _is_loading_game_summary
	)


func _request_wolf_game_state(preserve_info: bool = false) -> void:
	_is_loading_wolf_state = true
	_preserve_wolf_game_info_once = preserve_info
	refresh_state_button.disabled = true
	wolf_status_label.text = "后端状态：正在刷新状态..."

	var url = WOLF_GAME_STATE_URL_PREFIX + _current_wolf_game_id.uri_encode() + "/state"
	var error = game_state_request.request(url, [], HTTPClient.METHOD_GET)
	if error != OK:
		_is_loading_wolf_state = false
		_preserve_wolf_game_info_once = false
		refresh_state_button.disabled = false
		wolf_status_label.text = "后端状态：刷新状态失败"


func _request_game_summary() -> void:
	if _is_loading_game_summary or _current_wolf_game_id.is_empty():
		return
	_is_loading_game_summary = true
	_summary_requested_game_id = _current_wolf_game_id
	review_game_button.disabled = true
	wolf_status_label.text = "后端状态：正在生成本局复盘..."
	var url = WOLF_GAME_STATE_URL_PREFIX + _current_wolf_game_id.uri_encode() + "/summary"
	var error = game_summary_request.request(url, [], HTTPClient.METHOD_GET)
	if error != OK:
		_is_loading_game_summary = false
		_summary_requested_game_id = ""
		review_game_button.disabled = false
		wolf_status_label.text = "后端状态：读取本局复盘失败"


func _render_wolf_game(game_data: Dictionary) -> void:
	_latest_wolf_game_data = game_data.duplicate(true)
	var game_id = game_data.get("game_id", "")
	var day = game_data.get("day", 1)
	var phase = game_data.get("phase", "")
	var phase_changed := _current_wolf_phase != str(phase)
	var message = game_data.get("message", "游戏已开始。")
	var characters = game_data.get("characters", [])
	var public_logs = game_data.get("public_logs", [])
	var llm_enabled := bool(game_data.get("llm_enabled", false))

	_current_wolf_game_id = str(game_id)
	_current_wolf_phase = str(phase)
	_current_wolf_day = int(day)
	_update_player_private_state(game_data)
	_update_player_identity_display(game_data)
	_update_player_action_history(game_data)
	_update_sheriff_state(game_data)
	_update_meeting_state(game_data)
	_sync_world_npcs(characters)

	wolf_status_label.text = "后端状态：connected"
	if _preserve_wolf_game_info_once:
		_preserve_wolf_game_info_once = false
	else:
		var private_note := _format_player_private_state_note(game_data.get("player_private_info", {}))
		var llm_label := "LLM：已启用" if llm_enabled else "LLM：规则模板"
		wolf_game_info_label.text = "游戏 " + str(game_id) + " | 第 " + str(day) + " 天 | " + str(phase) + " | " + llm_label + "\n" + str(message) + private_note
	public_log_label.text = _format_public_logs(public_logs)
	_clear_character_grid()

	if typeof(characters) != TYPE_ARRAY:
		wolf_game_info_label.text = "角色数据格式不正确。"
		return

	for character in characters:
		if typeof(character) == TYPE_DICTIONARY:
			character_grid.add_child(_build_character_card(character))

	_update_night_controls(game_data)
	_update_hunter_controls(game_data)
	_update_sheriff_controls(game_data)
	_update_sheriff_overview()
	_update_day_speech_controls()
	_update_vote_controls(game_data)
	_update_contextual_panel_visibility()
	_update_wolf_menu_summary()
	if phase_changed:
		if _current_wolf_phase in [
			"SHERIFF_SIGNUP", "SHERIFF_SPEECH", "SHERIFF_WITHDRAWAL",
			"SHERIFF_VOTE", "SHERIFF_RUNOFF_SPEECH", "SHERIFF_RUNOFF_VOTE",
			"MEETING_ORDER", "SHERIFF_NOMINATION", "BADGE_TRANSFER",
		]:
			call_deferred("_keep_sheriff_controls_visible")
		else:
			call_deferred("_reset_wolf_panel_scroll")
	review_game_button.disabled = _current_wolf_phase != "GAME_OVER" or _is_loading_game_summary
	if (
		_current_wolf_phase == "GAME_OVER"
		and _game_summary_data.is_empty()
		and _summary_requested_game_id != _current_wolf_game_id
	):
		_request_game_summary()


func _update_wolf_menu_summary() -> void:
	if _current_wolf_game_id.is_empty():
		wolf_menu_summary_label.text = "等待开始"
		return

	match _current_wolf_phase:
		"NIGHT":
			wolf_menu_summary_label.text = "第 " + str(_current_wolf_day) + " 夜"
		"HUNTER_SHOT":
			wolf_menu_summary_label.text = "猎人开枪"
		"SHERIFF_SIGNUP":
			wolf_menu_summary_label.text = "警上报名"
		"SHERIFF_SPEECH":
			wolf_menu_summary_label.text = "警上发言"
		"SHERIFF_WITHDRAWAL":
			wolf_menu_summary_label.text = "退水阶段"
		"SHERIFF_VOTE":
			wolf_menu_summary_label.text = "警长投票"
		"SHERIFF_RUNOFF_SPEECH":
			wolf_menu_summary_label.text = "警上 PK"
		"SHERIFF_RUNOFF_VOTE":
			wolf_menu_summary_label.text = "PK 投票"
		"MEETING_ORDER":
			wolf_menu_summary_label.text = "警长选发言侧"
		"SHERIFF_NOMINATION":
			wolf_menu_summary_label.text = "警长归票"
		"BADGE_TRANSFER":
			wolf_menu_summary_label.text = "移交警徽"
		"DAY_MEETING":
			var speaker_name := str(_wolf_character_names.get(_current_meeting_speaker_id, "等待发言"))
			wolf_menu_summary_label.text = "会议 · " + speaker_name
		"FREE_ACTIVITY":
			wolf_menu_summary_label.text = "自由活动"
		"VOTE":
			wolf_menu_summary_label.text = "投票阶段"
		"GAME_OVER":
			wolf_menu_summary_label.text = "游戏结束"
		_:
			wolf_menu_summary_label.text = _current_wolf_phase


func _update_meeting_state(game_data: Dictionary) -> void:
	_current_meeting_speaker_id = 0
	_current_meeting_order.clear()
	_current_meeting_direction = ""

	var meeting = game_data.get("meeting", {})
	if typeof(meeting) != TYPE_DICTIONARY:
		return

	_current_meeting_speaker_id = int(meeting.get("current_speaker_id", 0))
	_current_meeting_direction = str(meeting.get("direction", ""))
	var order = meeting.get("order", [])
	if typeof(order) == TYPE_ARRAY:
		for character_id in order:
			_current_meeting_order.append(int(character_id))


func _update_sheriff_state(game_data: Dictionary) -> void:
	_current_sheriff_data.clear()
	_current_sheriff_speaker_id = 0
	_current_sheriff_id = 0
	var sheriff = game_data.get("sheriff", {})
	if typeof(sheriff) != TYPE_DICTIONARY:
		return
	_current_sheriff_data = sheriff.duplicate(true)
	_current_sheriff_speaker_id = int(sheriff.get("current_speaker_id", 0))
	var sheriff_id = sheriff.get("sheriff_id", null)
	if sheriff_id != null:
		_current_sheriff_id = int(sheriff_id)


func _sync_world_npcs(characters: Variant) -> void:
	_wolf_character_names.clear()
	_wolf_character_alive.clear()
	_wolf_private_question_used.clear()
	_wolf_campaign_status.clear()
	if typeof(characters) == TYPE_ARRAY:
		for character in characters:
			if typeof(character) != TYPE_DICTIONARY:
				continue
			var character_id := int(character.get("id", 0))
			_wolf_character_names[character_id] = str(character.get("name", "未知"))
			_wolf_character_alive[character_id] = bool(character.get("alive", true))
			_wolf_private_question_used[character_id] = bool(character.get("private_question_used_today", false))
			_wolf_campaign_status[character_id] = str(character.get("sheriff_campaign_status", ""))

	for npc in get_tree().get_nodes_in_group("npc"):
		var character_id := int(npc.call("get_wolf_character_id"))
		if character_id <= 0:
			continue
		var alive := bool(_wolf_character_alive.get(character_id, true))
		var is_current_speaker := (
			character_id == _current_meeting_speaker_id
			or character_id == _current_sheriff_speaker_id
		)
		npc.call(
			"set_wolf_game_state",
			alive,
			is_current_speaker,
			character_id == _current_sheriff_id,
			str(_wolf_campaign_status.get(character_id, ""))
		)
	if _current_player_character_id > 0:
		player.call(
			"set_wolf_game_state",
			_current_player_alive,
			_current_player_character_id == _current_sheriff_id,
			str(_wolf_campaign_status.get(_current_player_character_id, ""))
		)


func _update_player_private_state(game_data: Dictionary) -> void:
	_current_player_character_id = 0
	_current_player_role = ""
	_current_player_alive = false

	var characters = game_data.get("characters", [])
	if typeof(characters) == TYPE_ARRAY:
		for character in characters:
			if typeof(character) != TYPE_DICTIONARY or not character.get("is_player", false):
				continue
			_current_player_character_id = int(character.get("id", 0))
			_current_player_alive = bool(character.get("alive", true))
			var visible_role = character.get("role_visible_to_player", null)
			if visible_role != null:
				_current_player_role = str(visible_role)

	var private_info = game_data.get("player_private_info", {})
	if typeof(private_info) == TYPE_DICTIONARY:
		var role = private_info.get("role", "")
		if not str(role).is_empty():
			_current_player_role = str(role)


func _update_player_identity_display(game_data: Dictionary) -> void:
	player_identity_block.visible = not _current_wolf_game_id.is_empty() and not _current_player_role.is_empty()
	if not player_identity_block.visible:
		wolf_teammates_label.visible = false
		return

	player_role_label.text = "你的身份：" + _format_role_name(_current_player_role)
	match _current_player_role:
		"werewolf":
			player_role_label.add_theme_color_override("font_color", Color(1.0, 0.46, 0.46, 1.0))
		"seer", "witch", "hunter", "guard":
			player_role_label.add_theme_color_override("font_color", Color(0.42, 0.86, 1.0, 1.0))
		_:
			player_role_label.add_theme_color_override("font_color", Color(0.62, 0.9, 0.66, 1.0))

	wolf_teammates_label.visible = _current_player_role == "werewolf"
	if not wolf_teammates_label.visible:
		return

	var teammate_parts: Array[String] = []
	var private_info = game_data.get("player_private_info", {})
	var teammates = private_info.get("wolf_teammates", []) if typeof(private_info) == TYPE_DICTIONARY else []
	if typeof(teammates) == TYPE_ARRAY:
		for teammate in teammates:
			if typeof(teammate) == TYPE_DICTIONARY:
				teammate_parts.append(str(teammate.get("id", "?")) + "号 " + str(teammate.get("name", "未知")))
	if teammate_parts.is_empty():
		var characters = game_data.get("characters", [])
		if typeof(characters) == TYPE_ARRAY:
			for character in characters:
				if (
					typeof(character) == TYPE_DICTIONARY
					and not bool(character.get("is_player", false))
					and str(character.get("role_visible_to_player", "")) == "werewolf"
				):
					teammate_parts.append(str(character.get("id", "?")) + "号 " + str(character.get("name", "未知")))
	wolf_teammates_label.text = "狼队友：" + ("、".join(teammate_parts) if not teammate_parts.is_empty() else "等待状态同步")


func _update_player_action_history(game_data: Dictionary) -> void:
	player_action_history_block.visible = not _current_wolf_game_id.is_empty()
	if not player_action_history_block.visible:
		player_action_history_text.text = "暂无行动记录。"
		return

	var private_info = game_data.get("player_private_info", {})
	var history = private_info.get("action_history", []) if typeof(private_info) == TYPE_DICTIONARY else []
	var lines: Array[String] = []
	if typeof(history) == TYPE_ARRAY:
		for item in history:
			var item_text := str(item).strip_edges()
			if not item_text.is_empty():
				lines.append(item_text)
	player_action_history_text.text = "\n".join(lines) if not lines.is_empty() else "暂无行动记录。"
	call_deferred("_scroll_player_action_history_to_end")


func _scroll_player_action_history_to_end() -> void:
	if player_action_history_block.visible:
		player_action_history_text.scroll_vertical = player_action_history_text.get_line_count()


func _reset_wolf_panel_scroll() -> void:
	wolf_scroll_container.scroll_vertical = 0


func _keep_sheriff_controls_visible() -> void:
	if not sheriff_action_label.visible:
		return
	wolf_scroll_container.ensure_control_visible(sheriff_action_label)
	if sheriff_withdrawal_row.visible:
		wolf_scroll_container.ensure_control_visible(sheriff_withdrawal_row)
	elif sheriff_choice_row.visible:
		wolf_scroll_container.ensure_control_visible(sheriff_choice_row)
	elif sheriff_speech_row.visible:
		wolf_scroll_container.ensure_control_visible(sheriff_speech_row)


func _update_contextual_panel_visibility() -> void:
	var has_game := not _current_wolf_game_id.is_empty()
	var night_visible := has_game and _current_wolf_phase == "NIGHT"
	var hunter_visible := has_game and _current_wolf_phase == "HUNTER_SHOT" and _current_player_role == "hunter"
	var sheriff_visible := _current_wolf_phase in [
		"SHERIFF_SIGNUP", "SHERIFF_SPEECH", "SHERIFF_WITHDRAWAL",
		"SHERIFF_VOTE", "SHERIFF_RUNOFF_SPEECH", "SHERIFF_RUNOFF_VOTE",
		"MEETING_ORDER", "SHERIFF_NOMINATION", "BADGE_TRANSFER",
	]
	var sheriff_speech_visible := _current_wolf_phase in ["SHERIFF_SPEECH", "SHERIFF_RUNOFF_SPEECH"]
	var sheriff_withdrawal_visible := false
	if _current_wolf_phase == "SHERIFF_WITHDRAWAL":
		var candidates = _current_sheriff_data.get("candidates", [])
		var withdrawn = _current_sheriff_data.get("withdrawn", [])
		sheriff_withdrawal_visible = (
			_array_has_int(candidates, _current_player_character_id)
			and not _array_has_int(withdrawn, _current_player_character_id)
		)
	var day_visible := _current_wolf_phase in ["DAY_MEETING", "FREE_ACTIVITY"]
	var vote_visible := _current_wolf_phase == "VOTE"

	night_action_label.visible = night_visible
	night_action_row.visible = night_visible
	hunter_action_label.visible = hunter_visible
	hunter_action_row.visible = hunter_visible
	sheriff_action_label.visible = sheriff_visible
	sheriff_choice_row.visible = (
		sheriff_visible
		and not sheriff_speech_visible
		and _current_wolf_phase != "SHERIFF_WITHDRAWAL"
	)
	sheriff_withdrawal_row.visible = sheriff_withdrawal_visible
	sheriff_speech_row.visible = sheriff_visible and sheriff_speech_visible
	day_speech_label.visible = day_visible
	day_speech_row.visible = day_visible
	player_speech_input.visible = _current_wolf_phase == "DAY_MEETING"
	submit_speech_button.visible = _current_wolf_phase == "DAY_MEETING"
	end_free_activity_button.visible = _current_wolf_phase == "FREE_ACTIVITY"
	temporary_nomination_row.visible = (
		_current_wolf_phase == "DAY_MEETING"
		and _current_meeting_speaker_id == _current_player_character_id
		and _current_sheriff_id == _current_player_character_id
		and _current_player_alive
	)
	vote_action_label.visible = vote_visible
	vote_reason_input.visible = vote_visible
	vote_action_row.visible = vote_visible
	vote_result_label.visible = vote_visible or vote_result_label.text != "票型：尚未公布"


func _update_night_controls(game_data: Dictionary) -> void:
	night_action_option.clear()
	night_target_option.clear()

	if _current_wolf_game_id.is_empty():
		_disable_night_controls()
		night_action_label.text = "夜晚行动：开始游戏后可用"
		return

	if _current_wolf_phase != "NIGHT":
		_disable_night_controls()
		night_action_label.text = "夜晚行动：当前阶段不是 NIGHT"
		return

	_populate_night_action_options(game_data)
	_refresh_night_target_options(game_data)
	var action_type := _get_selected_night_action_type()
	var action_name := _format_night_action_name(action_type)
	night_action_label.text = "夜晚行动：" + action_name
	var has_active_night_skill := _current_player_alive and _current_player_role in ["werewolf", "seer", "witch", "guard"]
	night_action_option.visible = has_active_night_skill
	night_target_option.visible = has_active_night_skill
	submit_night_action_button.visible = has_active_night_skill
	resolve_night_button.visible = true
	if not has_active_night_skill:
		night_action_label.text = "夜晚行动：今夜没有主动技能，可以直接结算"
	if _current_player_role == "witch" and has_active_night_skill:
		var private_info = game_data.get("player_private_info", {})
		if typeof(private_info) == TYPE_DICTIONARY:
			var attacked = private_info.get("witch_attacked_target", null)
			var attacked_text := "今晚没有明确刀口"
			if typeof(attacked) == TYPE_DICTIONARY:
				attacked_text = "今晚刀口：" + str(attacked.get("id", "?")) + "号 " + str(attacked.get("name", "未知"))
			var antidote_text := "解药可用" if bool(private_info.get("witch_antidote_available", false)) else "解药已用"
			var poison_text := "毒药可用" if bool(private_info.get("witch_poison_available", false)) else "毒药已用"
			night_action_label.text = "女巫行动：" + attacked_text + " | " + antidote_text + " | " + poison_text

	submit_night_action_button.disabled = (
		not _current_player_alive
		or _is_submitting_night_action
		or _is_resolving_night
		or (_night_action_requires_target(action_type) and night_target_option.get_item_count() == 0)
	)
	resolve_night_button.disabled = _is_submitting_night_action or _is_resolving_night


func _populate_night_action_options(game_data: Dictionary) -> void:
	night_action_option.clear()
	if _current_player_role == "witch":
		var private_info = game_data.get("player_private_info", {})
		if typeof(private_info) == TYPE_DICTIONARY:
			var attacked = private_info.get("witch_attacked_target", null)
			if bool(private_info.get("witch_antidote_available", false)) and typeof(attacked) == TYPE_DICTIONARY:
				_add_night_action_option("使用解药", "witch_save")
			if bool(private_info.get("witch_poison_available", false)):
				_add_night_action_option("使用毒药", "witch_poison")
		_add_night_action_option("不使用药", "none")
	else:
		var action_type := _get_player_night_action_type(_current_player_role)
		_add_night_action_option(_format_night_action_name(action_type), action_type)
	night_action_option.disabled = night_action_option.get_item_count() <= 1


func _add_night_action_option(label: String, action_type: String) -> void:
	var index := night_action_option.get_item_count()
	night_action_option.add_item(label)
	night_action_option.set_item_metadata(index, action_type)


func _get_selected_night_action_type() -> String:
	if night_action_option.get_item_count() == 0:
		return _get_player_night_action_type(_current_player_role)
	var metadata = night_action_option.get_item_metadata(night_action_option.selected)
	return str(metadata) if metadata != null else "none"


func _refresh_night_target_options(game_data: Dictionary) -> void:
	night_target_option.clear()
	var action_type := _get_selected_night_action_type()
	if not _night_action_requires_target(action_type):
		night_target_option.add_item("无需选择目标", 0)
		night_target_option.disabled = true
		return

	var private_info = game_data.get("player_private_info", {})
	var witch_save_target_id := 0
	if action_type == "witch_save" and typeof(private_info) == TYPE_DICTIONARY:
		var attacked = private_info.get("witch_attacked_target", null)
		if typeof(attacked) == TYPE_DICTIONARY:
			witch_save_target_id = int(attacked.get("id", 0))

	var characters = game_data.get("characters", [])
	if typeof(characters) == TYPE_ARRAY:
		for character in characters:
			if typeof(character) != TYPE_DICTIONARY or not character.get("alive", true):
				continue
			var character_id := int(character.get("id", 0))
			if action_type == "witch_save" and character_id != witch_save_target_id:
				continue
			if action_type in ["seer_check", "witch_poison"] and character_id == _current_player_character_id:
				continue
			if action_type == "werewolf_kill" and str(character.get("role_visible_to_player", "")) == "werewolf":
				continue
			night_target_option.add_item(
				str(character_id) + "号 " + str(character.get("name", "未知")),
				character_id
			)
	night_target_option.disabled = night_target_option.get_item_count() == 0


func _update_night_controls_from_current_state() -> void:
	if _current_wolf_phase == "NIGHT":
		var action_type := _get_selected_night_action_type()
		submit_night_action_button.disabled = (
			not _current_player_alive
			or _is_submitting_night_action
			or _is_resolving_night
			or (_night_action_requires_target(action_type) and night_target_option.get_item_count() == 0)
		)
		resolve_night_button.disabled = _is_submitting_night_action or _is_resolving_night
	else:
		_disable_night_controls()


func _disable_night_controls() -> void:
	night_action_option.clear()
	night_action_option.disabled = true
	night_target_option.clear()
	night_target_option.disabled = true
	submit_night_action_button.disabled = true
	resolve_night_button.disabled = true


func _set_night_buttons_disabled(disabled: bool) -> void:
	night_action_option.disabled = disabled or night_action_option.get_item_count() <= 1
	night_target_option.disabled = disabled or not _night_action_requires_target(_get_selected_night_action_type())
	submit_night_action_button.disabled = disabled
	resolve_night_button.disabled = disabled


func _update_hunter_controls(game_data: Dictionary) -> void:
	hunter_target_option.clear()
	var private_info = game_data.get("player_private_info", {})
	var can_shoot := (
		_current_wolf_phase == "HUNTER_SHOT"
		and typeof(private_info) == TYPE_DICTIONARY
		and bool(private_info.get("hunter_can_shoot", false))
	)
	if not can_shoot:
		hunter_action_label.text = "猎人开枪：出局后可用"
		hunter_target_option.disabled = true
		hunter_shoot_button.disabled = true
		hunter_pass_button.disabled = true
		return

	var characters = game_data.get("characters", [])
	if typeof(characters) == TYPE_ARRAY:
		for character in characters:
			if typeof(character) != TYPE_DICTIONARY or not character.get("alive", true):
				continue
			var character_id := int(character.get("id", 0))
			if character_id == _current_player_character_id:
				continue
			hunter_target_option.add_item(
				str(character_id) + "号 " + str(character.get("name", "未知")),
				character_id
			)
	hunter_action_label.text = "猎人开枪：选择一名仍在场的角色，或选择不开枪"
	hunter_target_option.disabled = _is_submitting_hunter_shot or hunter_target_option.get_item_count() == 0
	hunter_shoot_button.disabled = _is_submitting_hunter_shot or hunter_target_option.get_item_count() == 0
	hunter_pass_button.disabled = _is_submitting_hunter_shot


func _update_sheriff_controls(game_data: Dictionary) -> void:
	sheriff_option.clear()
	sheriff_speech_input.editable = false
	sheriff_speech_button.disabled = true
	sheriff_action_button.disabled = true
	sheriff_option.disabled = true
	sheriff_continue_button.disabled = true
	sheriff_withdraw_button.disabled = true

	var busy := _is_sheriff_action_requesting or _is_sheriff_speech_requesting
	var characters = game_data.get("characters", [])
	match _current_wolf_phase:
		"SHERIFF_SIGNUP":
			sheriff_action_label.text = "警上报名：选择是否参加第一天警长竞选"
			_add_sheriff_option("上警竞选", true)
			_add_sheriff_option("不上警", false)
			sheriff_action_button.text = "确认报名"
			sheriff_option.disabled = busy or not _current_player_alive
			sheriff_action_button.disabled = busy or not _current_player_alive
		"SHERIFF_SPEECH", "SHERIFF_RUNOFF_SPEECH":
			var current_name := str(_wolf_character_names.get(_current_sheriff_speaker_id, "当前候选人"))
			var stage_name := "警上 PK" if _current_wolf_phase == "SHERIFF_RUNOFF_SPEECH" else "警上竞选"
			if _current_sheriff_speaker_id == _current_player_character_id:
				sheriff_action_label.text = stage_name + "：轮到你发言"
				sheriff_speech_input.editable = not busy
				sheriff_speech_button.disabled = busy
			else:
				sheriff_action_label.text = stage_name + "：请走近 " + current_name + " 按 E"
		"SHERIFF_WITHDRAWAL":
			var candidates = _current_sheriff_data.get("candidates", [])
			var withdrawn = _current_sheriff_data.get("withdrawn", [])
			var player_is_candidate := _array_has_int(candidates, _current_player_character_id)
			var player_withdrawn := _array_has_int(withdrawn, _current_player_character_id)
			if player_is_candidate and not player_withdrawn:
				sheriff_action_label.text = "退水阶段：请选择继续竞选或退水"
				sheriff_continue_button.disabled = busy
				sheriff_withdraw_button.disabled = busy
			elif player_withdrawn:
				sheriff_action_label.text = "退水阶段：你已退水，正在等待其他候选人"
			else:
				sheriff_action_label.text = "退水阶段：正在自动结算候选人的选择"
		"SHERIFF_VOTE", "SHERIFF_RUNOFF_VOTE":
			var can_vote := bool(_current_sheriff_data.get("player_can_vote", false))
			var ineligible_reason := str(_current_sheriff_data.get("player_vote_ineligible_reason", ""))
			sheriff_action_label.text = "警长投票：票型将在提交后同时公布"
			if can_vote:
				_add_character_options(sheriff_option, characters, _current_sheriff_data.get("vote_targets", []))
			else:
				_add_sheriff_option(
					ineligible_reason if not ineligible_reason.is_empty() else "当前不能参与警长投票",
					null
				)
			sheriff_action_button.text = "投警长并公布" if can_vote else "公布警长票型"
			sheriff_option.disabled = busy or not can_vote
			sheriff_action_button.disabled = busy or (can_vote and sheriff_option.get_item_count() == 0)
		"MEETING_ORDER":
			var anchor_type := str(_current_sheriff_data.get("order_anchor_type", "sheriff"))
			var anchor_id := int(_current_sheriff_data.get("order_anchor_id", 0))
			var anchor_name := str(_wolf_character_names.get(anchor_id, "警长"))
			var prefix := "出局" if anchor_type == "out" else "警"
			sheriff_action_label.text = "发言顺序：锚点为 " + str(anchor_id) + "号 " + anchor_name
			_add_sheriff_option(prefix + "左发言", "left")
			_add_sheriff_option(prefix + "右发言", "right")
			sheriff_action_button.text = "确认发言侧"
			sheriff_option.disabled = busy
			sheriff_action_button.disabled = busy
		"SHERIFF_NOMINATION":
			sheriff_action_label.text = "警长归票：你的正式投票将锁定为同一目标"
			_add_alive_character_options(sheriff_option, characters, [_current_sheriff_id])
			sheriff_action_button.text = "确认归票"
			sheriff_option.disabled = busy or sheriff_option.get_item_count() == 0
			sheriff_action_button.disabled = busy or sheriff_option.get_item_count() == 0
		"BADGE_TRANSFER":
			sheriff_action_label.text = "警徽移交：先完成猎人技能，再选择继任者或撕毁"
			_add_alive_character_options(sheriff_option, characters, [])
			_add_sheriff_option("撕毁警徽", 0)
			sheriff_action_button.text = "确认警徽去向"
			sheriff_option.disabled = busy
			sheriff_action_button.disabled = busy
		_:
			if _current_sheriff_id > 0:
				var sheriff_name := str(_wolf_character_names.get(_current_sheriff_id, "未知"))
				sheriff_action_label.text = "当前警长：" + str(_current_sheriff_id) + "号 " + sheriff_name
			else:
				sheriff_action_label.text = "警长操作：当前没有可执行操作"


func _update_sheriff_controls_from_current_state() -> void:
	if not _latest_wolf_game_data.is_empty():
		_update_sheriff_controls(_latest_wolf_game_data)
		_update_sheriff_overview()


func _update_sheriff_overview() -> void:
	var sheriff_phases := [
		"SHERIFF_SIGNUP",
		"SHERIFF_SPEECH",
		"SHERIFF_WITHDRAWAL",
		"SHERIFF_VOTE",
		"SHERIFF_RUNOFF_SPEECH",
		"SHERIFF_RUNOFF_VOTE",
	]
	sheriff_overview_label.visible = _current_wolf_phase in sheriff_phases
	if not sheriff_overview_label.visible:
		return

	var lines: Array[String] = []
	lines.append("上警名单：" + _format_sheriff_character_ids(_current_sheriff_data.get("candidates", [])))
	lines.append("发言顺序：" + _format_sheriff_character_ids(_current_sheriff_data.get("speech_order", []), " → "))
	var current_speaker_id := int(_current_sheriff_data.get("current_speaker_id", 0))
	if current_speaker_id > 0:
		lines.append("当前发言：" + _format_sheriff_character_ids([current_speaker_id]))
	var withdrawn = _current_sheriff_data.get("withdrawn", [])
	if typeof(withdrawn) == TYPE_ARRAY and not withdrawn.is_empty():
		lines.append("已退水：" + _format_sheriff_character_ids(withdrawn))
	var runoff_candidates = _current_sheriff_data.get("runoff_candidates", [])
	if typeof(runoff_candidates) == TYPE_ARRAY and not runoff_candidates.is_empty():
		lines.append("PK名单：" + _format_sheriff_character_ids(runoff_candidates))
	sheriff_overview_label.text = "\n".join(lines)


func _format_sheriff_character_ids(values: Variant, separator: String = "、") -> String:
	if typeof(values) != TYPE_ARRAY or values.is_empty():
		return "暂无"
	var labels: Array[String] = []
	for value in values:
		var character_id := int(value)
		labels.append(
			str(character_id) + "号" + str(_wolf_character_names.get(character_id, "未知"))
		)
	return separator.join(labels)


func _disable_sheriff_controls() -> void:
	sheriff_option.clear()
	sheriff_option.disabled = true
	sheriff_action_button.disabled = true
	sheriff_speech_input.editable = false
	sheriff_speech_button.disabled = true


func _add_sheriff_option(label: String, metadata: Variant) -> void:
	var index := sheriff_option.get_item_count()
	sheriff_option.add_item(label)
	sheriff_option.set_item_metadata(index, metadata)


func _add_character_options(option: OptionButton, characters: Variant, allowed_ids: Variant) -> void:
	if typeof(characters) != TYPE_ARRAY or typeof(allowed_ids) != TYPE_ARRAY:
		return
	for character in characters:
		if typeof(character) != TYPE_DICTIONARY:
			continue
		var character_id := int(character.get("id", 0))
		if not _array_has_int(allowed_ids, character_id):
			continue
		option.add_item(str(character_id) + "号 " + str(character.get("name", "未知")))
		option.set_item_metadata(option.get_item_count() - 1, character_id)


func _add_alive_character_options(option: OptionButton, characters: Variant, excluded_ids: Array) -> void:
	if typeof(characters) != TYPE_ARRAY:
		return
	for character in characters:
		if typeof(character) != TYPE_DICTIONARY or not bool(character.get("alive", true)):
			continue
		var character_id := int(character.get("id", 0))
		if _array_has_int(excluded_ids, character_id):
			continue
		option.add_item(str(character_id) + "号 " + str(character.get("name", "未知")))
		option.set_item_metadata(option.get_item_count() - 1, character_id)


func _array_has_int(values: Variant, target: int) -> bool:
	if typeof(values) != TYPE_ARRAY:
		return false
	for value in values:
		if int(value) == target:
			return true
	return false


func _update_day_speech_controls() -> void:
	temporary_nomination_option.clear()
	if _current_wolf_game_id.is_empty():
		_disable_day_speech_controls()
		day_speech_label.text = "小镇会议：开始游戏后可用"
		return

	if _current_wolf_phase == "GAME_OVER":
		_disable_day_speech_controls()
		day_speech_label.text = "小镇会议：游戏已结束"
		return

	if _current_wolf_phase == "FREE_ACTIVITY":
		player_speech_input.editable = false
		submit_speech_button.disabled = true
		end_free_activity_button.disabled = _is_ending_free_activity
		day_speech_label.text = "会后自由活动：走近存活 NPC 按 E 私密追问"
		return

	if _current_wolf_phase != "DAY_MEETING":
		_disable_day_speech_controls()
		day_speech_label.text = "小镇会议：当前阶段不可发言"
		return

	var current_name := str(_wolf_character_names.get(_current_meeting_speaker_id, "未知角色"))
	var direction_label := "顺时针" if _current_meeting_direction == "clockwise" else "逆时针"
	if _current_meeting_speaker_id == _current_player_character_id and _current_player_alive:
		day_speech_label.text = "小镇会议（" + direction_label + "）：轮到你公开发言"
	else:
		day_speech_label.text = "小镇会议（" + direction_label + "）：请走近 " + current_name + " 按 E"

	var is_player_turn := _current_meeting_speaker_id == _current_player_character_id and _current_player_alive
	var can_temporarily_nominate := is_player_turn and _current_sheriff_id == _current_player_character_id
	if can_temporarily_nominate:
		temporary_nomination_option.add_item("暂不提出归票")
		temporary_nomination_option.set_item_metadata(0, 0)
		_add_alive_character_options(
			temporary_nomination_option,
			_latest_wolf_game_data.get("characters", []),
			[_current_player_character_id]
		)
	temporary_nomination_option.disabled = not can_temporarily_nominate or _is_day_speech_requesting()
	player_speech_input.editable = is_player_turn and not _is_day_speech_requesting()
	submit_speech_button.disabled = not is_player_turn or _is_day_speech_requesting()
	end_free_activity_button.disabled = true


func _update_day_speech_controls_from_current_state() -> void:
	if _current_wolf_phase == "FREE_ACTIVITY":
		player_speech_input.editable = false
		submit_speech_button.disabled = true
		end_free_activity_button.disabled = _is_ending_free_activity
		return
	if _current_wolf_phase != "DAY_MEETING":
		_disable_day_speech_controls()
		return

	var is_player_turn := _current_meeting_speaker_id == _current_player_character_id and _current_player_alive
	player_speech_input.editable = is_player_turn and not _is_day_speech_requesting()
	submit_speech_button.disabled = not is_player_turn or _is_day_speech_requesting()
	temporary_nomination_option.disabled = (
		not is_player_turn
		or _current_sheriff_id != _current_player_character_id
		or _is_day_speech_requesting()
	)
	end_free_activity_button.disabled = true


func _disable_day_speech_controls() -> void:
	player_speech_input.editable = false
	submit_speech_button.disabled = true
	end_free_activity_button.disabled = true
	temporary_nomination_option.disabled = true


func _set_day_speech_buttons_disabled(disabled: bool) -> void:
	var is_player_turn := _current_meeting_speaker_id == _current_player_character_id and _current_player_alive
	player_speech_input.editable = not disabled and is_player_turn
	submit_speech_button.disabled = disabled or not is_player_turn
	end_free_activity_button.disabled = true
	temporary_nomination_option.disabled = disabled or not is_player_turn or _current_sheriff_id != _current_player_character_id


func _is_day_speech_phase() -> bool:
	return _current_wolf_phase == "DAY_MEETING"


func _is_day_speech_requesting() -> bool:
	return _is_submitting_player_speech or _is_generating_npc_speeches or _is_ending_free_activity


func _update_vote_controls(game_data: Dictionary) -> void:
	vote_target_option.clear()

	if _current_wolf_game_id.is_empty():
		_disable_vote_controls()
		vote_action_label.text = "白天投票：开始游戏后可用"
		return

	if _current_wolf_phase == "GAME_OVER":
		_disable_vote_controls()
		vote_action_label.text = "白天投票：游戏已结束"
		return

	if not _is_vote_phase():
		_disable_vote_controls()
		vote_action_label.text = "白天投票：当前阶段不是白天"
		return

	var locked_nomination_id := 0
	var meeting = game_data.get("meeting", {})
	if _current_sheriff_id == _current_player_character_id and typeof(meeting) == TYPE_DICTIONARY:
		var nomination_target = meeting.get("nomination_target_id", null)
		if nomination_target != null:
			locked_nomination_id = int(nomination_target)

	var characters = game_data.get("characters", [])
	if typeof(characters) == TYPE_ARRAY:
		for character in characters:
			if typeof(character) != TYPE_DICTIONARY:
				continue
			if not character.get("alive", true):
				continue
			var character_id := int(character.get("id", 0))
			if character_id == _current_player_character_id:
				continue
			if locked_nomination_id > 0 and character_id != locked_nomination_id:
				continue
			vote_target_option.add_item(
				str(character_id) + "号 " + str(character.get("name", "未知")),
				character_id
			)

	if _current_player_alive:
		vote_action_label.text = "白天投票：填写理由后一次性公布全部票型"
		if locked_nomination_id > 0:
			vote_action_label.text = "白天投票：警长票已锁定为公开归票目标"
	else:
		vote_action_label.text = "白天投票：玩家已出局，可直接公布并结算 NPC 票型"

	vote_target_option.disabled = (
		not _current_player_alive
		or vote_target_option.get_item_count() == 0
		or _is_vote_requesting()
	)
	vote_reason_input.editable = _current_player_alive and not _is_vote_requesting()
	submit_vote_button.disabled = _is_vote_requesting() or (_current_player_alive and vote_target_option.get_item_count() == 0)


func _update_vote_controls_from_current_state() -> void:
	if _is_vote_phase():
		_update_vote_controls(_latest_wolf_game_data)
	else:
		_disable_vote_controls()


func _disable_vote_controls() -> void:
	vote_target_option.clear()
	vote_target_option.disabled = true
	vote_reason_input.editable = false
	submit_vote_button.disabled = true


func _set_vote_buttons_disabled(disabled: bool) -> void:
	vote_target_option.disabled = disabled or not _current_player_alive or vote_target_option.get_item_count() == 0
	vote_reason_input.editable = not disabled and _current_player_alive
	submit_vote_button.disabled = disabled or (_current_player_alive and vote_target_option.get_item_count() == 0)


func _is_vote_phase() -> bool:
	return _current_wolf_phase == "VOTE"


func _is_vote_requesting() -> bool:
	return _is_submitting_vote


func _get_player_night_action_type(role: String) -> String:
	match role:
		"werewolf":
			return "werewolf_kill"
		"seer":
			return "seer_check"
		"guard":
			return "guard_protect"
		"witch":
			return "none"
		_:
			return "none"


func _night_action_requires_target(action_type: String) -> bool:
	return action_type in ["werewolf_kill", "seer_check", "guard_protect", "witch_save", "witch_poison"]


func _format_night_action_name(action_type: String) -> String:
	match action_type:
		"werewolf_kill":
			return "狼人袭击"
		"seer_check":
			return "预言家查验"
		"guard_protect":
			return "守卫保护"
		"witch_save":
			return "女巫使用解药"
		"witch_poison":
			return "女巫使用毒药"
		_:
			return "无行动"


func _format_player_private_night_result(player_private_result: Variant) -> String:
	if typeof(player_private_result) != TYPE_DICTIONARY:
		return ""

	var seer_check = player_private_result.get("seer_check", null)
	if typeof(seer_check) == TYPE_DICTIONARY:
		var target_id = seer_check.get("target_id", "?")
		var result = "狼人" if seer_check.get("result", "") == "werewolf" else "好人"
		return "\n查验结果：" + str(target_id) + "号是" + result + "。"
	var witch_action = player_private_result.get("witch_action", null)
	if typeof(witch_action) == TYPE_DICTIONARY:
		return "\n女巫行动已结算：" + _format_night_action_name(str(witch_action.get("action_type", "none"))) + "。"
	return ""


func _format_player_private_state_note(private_info: Variant) -> String:
	if typeof(private_info) != TYPE_DICTIONARY:
		return ""

	var notes: Array[String] = []
	var last_check_result = private_info.get("last_check_result", null)
	if typeof(last_check_result) == TYPE_DICTIONARY:
		var target_id = last_check_result.get("target_id", "?")
		var result = "狼人" if last_check_result.get("result", "") == "werewolf" else "好人"
		notes.append("最近查验：" + str(target_id) + "号是" + result + "。")

	var wolf_teammates = private_info.get("wolf_teammates", [])
	if typeof(wolf_teammates) == TYPE_ARRAY and not wolf_teammates.is_empty():
		var teammate_parts: Array[String] = []
		for teammate in wolf_teammates:
			if typeof(teammate) != TYPE_DICTIONARY:
				continue
			var state := "存活" if bool(teammate.get("alive", true)) else "已出局"
			teammate_parts.append(str(teammate.get("id", "?")) + "号 " + str(teammate.get("name", "未知")) + "（" + state + "）")
		if not teammate_parts.is_empty():
			notes.append("狼队友：" + _join_inline(teammate_parts))

	if _current_player_role == "witch":
		var antidote := "可用" if bool(private_info.get("witch_antidote_available", false)) else "已使用"
		var poison := "可用" if bool(private_info.get("witch_poison_available", false)) else "已使用"
		notes.append("女巫药品：解药" + antidote + "，毒药" + poison + "。")
	return "" if notes.is_empty() else "\n" + _join_lines(notes)


func _format_player_speech_result(speech_data: Dictionary) -> String:
	var lines: Array[String] = ["玩家发言已记录。"]
	var public_log = str(speech_data.get("public_log", ""))
	if not public_log.is_empty():
		lines.append(public_log)

	var parsed = speech_data.get("parsed", {})
	if typeof(parsed) == TYPE_DICTIONARY:
		var mentioned = parsed.get("mentioned_characters", [])
		if typeof(mentioned) == TYPE_ARRAY and not mentioned.is_empty():
			var mentioned_parts: Array[String] = []
			for character_id in mentioned:
				mentioned_parts.append(str(character_id) + "号")
			lines.append("提到角色：" + _join_inline(mentioned_parts))
		lines.append("语气：" + _format_speech_tone(str(parsed.get("tone", "neutral"))))

	return _join_lines(lines)


func _format_speech_tone(tone: String) -> String:
	match tone:
		"suspicious":
			return "怀疑"
		"claiming":
			return "身份声明"
		_:
			return "中性"


func _format_rag_retrieval_mode(retrieval_mode: String) -> String:
	return "向量 + 关键词" if retrieval_mode == "hybrid" else "关键词降级"


func _format_npc_speeches(speeches: Variant) -> String:
	if typeof(speeches) != TYPE_ARRAY or speeches.is_empty():
		return "NPC 发言：暂无可显示的发言。"

	var lines: Array[String] = ["NPC 发言："]
	for speech in speeches:
		if typeof(speech) != TYPE_DICTIONARY:
			continue

		var character_id = speech.get("character_id", "?")
		var character_name = speech.get("name", "未知")
		var content = str(speech.get("speech", ""))
		lines.append(str(character_id) + "号 " + str(character_name) + "：" + content)

	if lines.size() == 1:
		return "NPC 发言：后端已返回，但格式暂时无法显示。"

	return _join_lines(lines)


func _format_npc_vote_decisions(npc_votes: Variant) -> String:
	if typeof(npc_votes) != TYPE_ARRAY or npc_votes.is_empty():
		return "NPC 投票：暂无可显示的投票。"

	var lines: Array[String] = ["NPC 投票："]
	for vote in npc_votes:
		if typeof(vote) != TYPE_DICTIONARY:
			continue

		var voter_id = vote.get("character_id", "?")
		var target_id = vote.get("target_id", "?")
		var reason = str(vote.get("reason", ""))
		lines.append(str(voter_id) + "号 -> " + str(target_id) + "号：" + reason)
		var evidence_titles = vote.get("evidence_titles", [])
		if typeof(evidence_titles) == TYPE_ARRAY and not evidence_titles.is_empty():
			var evidence_parts: Array[String] = []
			for title in evidence_titles:
				evidence_parts.append(str(title))
			var mode := _format_rag_retrieval_mode(str(vote.get("retrieval_mode", "keyword")))
			lines.append("依据：" + _join_inline(evidence_parts) + " | " + mode)

	if lines.size() == 1:
		return "NPC 投票：后端已返回，但格式暂时无法显示。"

	return _join_lines(lines)


func _format_sheriff_vote_result(vote_data: Dictionary) -> String:
	var lines: Array[String] = ["警长票型："]
	var ballots = vote_data.get("ballots", [])
	if typeof(ballots) == TYPE_ARRAY:
		for ballot in ballots:
			if typeof(ballot) != TYPE_DICTIONARY:
				continue
			lines.append(str(ballot.get("voter_id", "?")) + "号 -> " + str(ballot.get("target_id", "?")) + "号")
	lines.append(str(vote_data.get("message", "警长投票已完成。")))
	return _join_lines(lines)


func _format_combined_vote_result(vote_data: Dictionary) -> String:
	var lines: Array[String] = ["票型总览"]
	var ballots = vote_data.get("ballots", [])
	if typeof(ballots) == TYPE_ARRAY:
		for ballot in ballots:
			if typeof(ballot) != TYPE_DICTIONARY:
				continue
			var weight := float(ballot.get("weight", 1.0))
			var sheriff_mark := " [警长 " + str(weight) + "票]" if bool(ballot.get("is_sheriff", false)) else ""
			lines.append(
				str(ballot.get("voter_id", "?")) + "号 " + str(ballot.get("voter_name", "未知"))
				+ " -> " + str(ballot.get("target_id", "?")) + "号 " + str(ballot.get("target_name", "未知"))
				+ sheriff_mark
			)

	var totals = vote_data.get("vote_totals", {})
	if typeof(totals) == TYPE_DICTIONARY and not totals.is_empty():
		var total_parts: Array[String] = []
		var total_ids = totals.keys()
		total_ids.sort_custom(func(a, b): return int(a) < int(b))
		for target_id in total_ids:
			total_parts.append(str(target_id) + "号=" + str(totals[target_id]) + "票")
		lines.append("合计：" + _join_inline(total_parts))

	lines.append("")
	lines.append("详细理由")
	if typeof(ballots) == TYPE_ARRAY:
		for ballot in ballots:
			if typeof(ballot) != TYPE_DICTIONARY:
				continue
			lines.append(
				str(ballot.get("voter_id", "?")) + "号投给" + str(ballot.get("target_id", "?"))
				+ "号：" + str(ballot.get("reason", "未提供理由。"))
			)
			var evidence_titles = ballot.get("evidence_titles", [])
			if typeof(evidence_titles) == TYPE_ARRAY and not evidence_titles.is_empty():
				var evidence_parts: Array[String] = []
				for title in evidence_titles:
					evidence_parts.append(str(title))
				lines.append(
					"依据：" + _join_inline(evidence_parts)
					+ " | " + _format_rag_retrieval_mode(str(ballot.get("retrieval_mode", "keyword")))
				)
	lines.append(str(vote_data.get("public_message", "投票已结算。")))
	return _join_lines(lines)


func _format_vote_resolve_result(vote_data: Dictionary) -> String:
	var lines: Array[String] = [str(vote_data.get("public_message", "投票已结算。"))]
	var vote_result = vote_data.get("vote_result", {})
	if typeof(vote_result) == TYPE_DICTIONARY and not vote_result.is_empty():
		var vote_parts: Array[String] = []
		for voter_id in vote_result.keys():
			vote_parts.append(str(voter_id) + "->" + str(vote_result[voter_id]))
		lines.append("投票结果：" + _join_inline(vote_parts))

	var winner = vote_data.get("winner", null)
	if winner != null:
		lines.append("胜利阵营：" + _format_winner_name(str(winner)))

	return _join_lines(lines)


func _format_winner_name(winner: String) -> String:
	match winner:
		"good":
			return "好人阵营"
		"werewolf":
			return "狼人阵营"
		_:
			return winner


func _format_public_logs(public_logs: Variant) -> String:
	if typeof(public_logs) != TYPE_ARRAY or public_logs.is_empty():
		return "公开日志：暂无"

	var lines: Array[String] = ["公开日志："]
	var start_index = max(0, public_logs.size() - 4)
	for index in range(start_index, public_logs.size()):
		lines.append("- " + str(public_logs[index]))

	var output := ""
	for line_index in range(lines.size()):
		if line_index > 0:
			output += "\n"
		output += lines[line_index]
	return output


func _join_lines(lines: Array[String]) -> String:
	var output := ""
	for line_index in range(lines.size()):
		if line_index > 0:
			output += "\n"
		output += lines[line_index]
	return output


func _join_inline(parts: Array[String]) -> String:
	var output := ""
	for part_index in range(parts.size()):
		if part_index > 0:
			output += ", "
		output += parts[part_index]
	return output


func _get_http_error_message(body: PackedByteArray, fallback: String) -> String:
	var json = JSON.new()
	var parse_error = json.parse(body.get_string_from_utf8())
	if parse_error == OK and typeof(json.data) == TYPE_DICTIONARY:
		var detail := str(json.data.get("detail", "")).strip_edges()
		if not detail.is_empty():
			return detail
	return fallback


func _reset_game_summary() -> void:
	_is_loading_game_summary = false
	_summary_requested_game_id = ""
	_game_summary_data.clear()
	review_game_button.disabled = true
	_hide_game_summary()
	_clear_control_children(game_summary_character_list)
	game_summary_timeline_label.text = "暂无时间线。"


func _show_game_summary() -> void:
	if _game_summary_data.is_empty():
		return
	if dialog_box.call("is_open"):
		dialog_box.call("hide_dialog")
	if _wolf_menu_expanded:
		_set_wolf_menu_expanded(false)
	game_summary_overlay.visible = true
	game_summary_overlay.add_to_group("dialog_open")
	game_summary_tabs.current_tab = 0
	game_summary_close_button.grab_focus()


func _hide_game_summary() -> void:
	game_summary_overlay.visible = false
	game_summary_overlay.remove_from_group("dialog_open")
	game_summary_close_button.release_focus()
	_release_movement_actions()


func _render_game_summary(summary: Dictionary) -> void:
	var winner_label := str(summary.get("winner_label", "未知阵营"))
	var total_days := int(summary.get("total_days", 0))
	var winner_message := str(summary.get("winner_message", "游戏结束。"))
	game_summary_winner_label.text = (
		winner_label + "胜利 | 共 " + str(total_days) + " 天\n" + winner_message
	)

	_clear_control_children(game_summary_character_list)
	var characters = summary.get("characters", [])
	if typeof(characters) == TYPE_ARRAY:
		for character in characters:
			if typeof(character) == TYPE_DICTIONARY:
				game_summary_character_list.add_child(_build_summary_character_item(character))

	var timeline = summary.get("timeline", [])
	var timeline_lines: Array[String] = []
	if typeof(timeline) == TYPE_ARRAY:
		for event in timeline:
			if typeof(event) == TYPE_DICTIONARY:
				timeline_lines.append(_format_summary_event(event))
	var validation_failures = summary.get("llm_validation_failures", [])
	if typeof(validation_failures) == TYPE_ARRAY and not validation_failures.is_empty():
		timeline_lines.append(_format_summary_llm_failures(validation_failures))
	game_summary_timeline_label.text = (
		"暂无行动记录。" if timeline_lines.is_empty() else "\n\n".join(timeline_lines)
	)


func _format_summary_llm_failures(failures: Array) -> String:
	var lines: Array[String] = ["LLM 校验失败完整记录"]
	for failure in failures:
		if typeof(failure) != TYPE_DICTIONARY:
			continue
		var character_id := int(failure.get("character_id", 0))
		var character_name := str(_wolf_character_names.get(character_id, "未知"))
		lines.append(
			str(character_id) + "号" + character_name + " | "
			+ str(failure.get("context_kind", "npc_text"))
		)
		var attempts = failure.get("attempts", [])
		if typeof(attempts) != TYPE_ARRAY:
			continue
		for attempt in attempts:
			if typeof(attempt) != TYPE_DICTIONARY:
				continue
			lines.append(
				"第 " + str(attempt.get("attempt", "?")) + " 次："
				+ str(attempt.get("text", "[无返回内容]"))
				+ "\n原因：" + str(attempt.get("rejection_reason", "未知"))
			)
	return "\n\n".join(lines)


func _build_summary_character_item(character: Dictionary) -> Control:
	var panel := PanelContainer.new()
	panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.12, 0.145, 0.17, 0.96)
	style.border_width_left = 1
	style.border_width_top = 1
	style.border_width_right = 1
	style.border_width_bottom = 1
	style.border_color = Color(0.34, 0.41, 0.48, 1)
	style.corner_radius_top_left = 6
	style.corner_radius_top_right = 6
	style.corner_radius_bottom_right = 6
	style.corner_radius_bottom_left = 6
	panel.add_theme_stylebox_override("panel", style)

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 10)
	margin.add_theme_constant_override("margin_top", 8)
	margin.add_theme_constant_override("margin_right", 10)
	margin.add_theme_constant_override("margin_bottom", 8)
	panel.add_child(margin)

	var content := VBoxContainer.new()
	content.add_theme_constant_override("separation", 6)
	margin.add_child(content)

	var title := (
		str(character.get("character_id", "?")) + "号 "
		+ str(character.get("name", "未知")) + " | "
		+ str(character.get("role_label", "未知身份")) + " | "
		+ str(character.get("camp_label", "未知阵营")) + " | "
		+ str(character.get("outcome", "未知结果"))
	)
	var header := Button.new()
	header.text = "▶ " + title
	header.alignment = HORIZONTAL_ALIGNMENT_LEFT
	header.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.set_meta("summary_title", title)
	content.add_child(header)

	var actions_label := Label.new()
	actions_label.visible = false
	actions_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	actions_label.add_theme_color_override("font_color", Color(0.84, 0.88, 0.9, 1))
	actions_label.add_theme_font_size_override("font_size", 13)
	var action_lines: Array[String] = []
	var actions = character.get("actions", [])
	if typeof(actions) == TYPE_ARRAY:
		for action in actions:
			if typeof(action) == TYPE_DICTIONARY:
				action_lines.append(_format_summary_event(action))
	actions_label.text = "本局没有单独行动记录。" if action_lines.is_empty() else "\n\n".join(action_lines)
	content.add_child(actions_label)
	header.pressed.connect(_toggle_summary_character_item.bind(header, actions_label))
	return panel


func _toggle_summary_character_item(header: Button, actions_label: Label) -> void:
	actions_label.visible = not actions_label.visible
	var marker := "▼ " if actions_label.visible else "▶ "
	header.text = marker + str(header.get_meta("summary_title", "角色复盘"))


func _format_summary_event(event: Dictionary) -> String:
	var day := int(event.get("day", 0))
	var phase := _format_summary_phase(str(event.get("phase", "")))
	var private_mark := " [私密]" if bool(event.get("is_private", false)) else ""
	return "第 " + str(day) + " 天 · " + phase + private_mark + "\n" + str(event.get("text", ""))


func _format_summary_phase(phase: String) -> String:
	match phase:
		"NIGHT":
			return "夜晚行动"
		"NIGHT_RESULT":
			return "夜晚结果"
		"HUNTER_SHOT":
			return "猎人开枪"
		"SHERIFF", "SHERIFF_SPEECH":
			return "警上竞选"
		"SHERIFF_RUNOFF_SPEECH":
			return "警上 PK"
		"DAY_MEETING":
			return "小镇会议"
		"FREE_ACTIVITY":
			return "会后私聊"
		"VOTE":
			return "投票"
		"VOTE_RESULT":
			return "放逐结果"
		"GAME_OVER":
			return "游戏结果"
		_:
			return phase


func _clear_control_children(container: Control) -> void:
	for child in container.get_children():
		child.queue_free()


func _release_movement_actions() -> void:
	for action in ["move_left", "move_right", "move_up", "move_down"]:
		if InputMap.has_action(action):
			Input.action_release(action)
	_lock_player_movement_until_release()


func _finish_gameplay_text_submission(input: LineEdit) -> void:
	input.clear()
	input.release_focus()
	_release_wolf_panel_focus()
	call_deferred("_release_wolf_panel_focus")
	_release_movement_actions()


func _restore_failed_gameplay_text(input: LineEdit, text: String) -> void:
	if text.is_empty():
		return
	input.text = text
	input.grab_focus()
	_lock_player_movement_until_release()


func _lock_player_movement_until_release() -> void:
	if player.has_method("lock_movement_until_release"):
		player.call("lock_movement_until_release")


func _configure_wolf_panel_focus() -> void:
	for node in wolf_panel.find_children("*", "BaseButton", true, false):
		if node is Control:
			node.focus_mode = Control.FOCUS_NONE
	player_action_history_text.focus_mode = Control.FOCUS_NONE


func _release_wolf_panel_focus() -> void:
	var focus_owner := get_viewport().gui_get_focus_owner()
	if focus_owner == null:
		return
	if focus_owner == wolf_panel or wolf_panel.is_ancestor_of(focus_owner):
		focus_owner.release_focus()
		get_viewport().gui_release_focus()


func _build_character_card(character: Dictionary) -> Control:
	var card := PanelContainer.new()
	card.custom_minimum_size = Vector2(164, 218)
	card.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.13, 0.16, 0.19, 0.94)
	style.border_width_left = 1
	style.border_width_top = 1
	style.border_width_right = 1
	style.border_width_bottom = 1
	style.border_color = Color(0.38, 0.46, 0.55, 1)
	style.corner_radius_top_left = 6
	style.corner_radius_top_right = 6
	style.corner_radius_bottom_right = 6
	style.corner_radius_bottom_left = 6

	if character.get("is_player", false):
		style.bg_color = Color(0.2, 0.17, 0.09, 0.96)
		style.border_color = Color(0.98, 0.84, 0.45, 1)

	card.add_theme_stylebox_override("panel", style)

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 8)
	margin.add_theme_constant_override("margin_top", 6)
	margin.add_theme_constant_override("margin_right", 8)
	margin.add_theme_constant_override("margin_bottom", 6)
	card.add_child(margin)

	var content := VBoxContainer.new()
	content.add_theme_constant_override("separation", 4)
	margin.add_child(content)

	var portrait := TextureRect.new()
	portrait.custom_minimum_size = Vector2(52, 52)
	portrait.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	portrait.expand_mode = TextureRect.EXPAND_FIT_WIDTH_PROPORTIONAL
	portrait.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	var skin_path := "res://assets/characters/player.svg" if character.get("is_player", false) else str(CHARACTER_SKIN_PATHS.get(str(character.get("name", "")), ""))
	if not skin_path.is_empty() and ResourceLoader.exists(skin_path):
		var skin_texture = load(skin_path)
		if skin_texture is Texture2D:
			portrait.texture = skin_texture
	portrait.modulate = Color(0.45, 0.45, 0.45, 0.65) if not character.get("alive", true) else Color.WHITE
	content.add_child(portrait)

	var label := Label.new()
	label.text = _format_character_card_text(character)
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.add_theme_color_override("font_color", Color(0.94, 0.96, 0.96, 1))
	label.add_theme_font_size_override("font_size", 12)
	content.add_child(label)

	return card


func _format_character_card_text(character: Dictionary) -> String:
	var character_id = character.get("id", "?")
	var character_name = character.get("name", "未知")
	var sheriff_text := " [警长]" if character.get("is_sheriff", false) else ""
	var alive_text = "存活" if character.get("alive", true) else "出局"
	var role = character.get("role_visible_to_player", null)
	var role_text = "身份：隐藏"
	if role != null:
		role_text = "身份：" + _format_role_name(str(role))
	var suspicion_score := int(character.get("suspicion_score", 0))
	var suspicion_level := str(character.get("suspicion_level", "无"))
	var suspicion_text := "关注：" + suspicion_level
	if suspicion_score > 0:
		suspicion_text += "(" + str(suspicion_score) + ")"
	var trust_text := "信任：自己"
	if not character.get("is_player", false):
		var trust_level := str(character.get("trust_level", "中"))
		var trust_value = character.get("trust_to_player", null)
		trust_text = "信任：" + trust_level
		if trust_value != null:
			trust_text += "(" + str(snapped(float(trust_value), 0.01)) + ")"
	var memory_text := "记忆：" + str(int(character.get("memory_count", 0)))
	var private_chat_text := "私聊：自己"
	if not character.get("is_player", false):
		private_chat_text = "私聊：已影响" if character.get("private_question_used_today", false) else "私聊：未追问"
	var claim_text := "公开：无身份声明"
	var public_claims = character.get("public_claims", [])
	if typeof(public_claims) == TYPE_ARRAY and not public_claims.is_empty():
		var claim_parts: Array[String] = []
		for claim in public_claims:
			claim_parts.append(str(claim))
		claim_text = "公开：" + "；".join(claim_parts)

	return str(character_id) + "号 " + str(character_name) + sheriff_text + "\n" + role_text + " | " + alive_text + "\n" + claim_text + "\n" + suspicion_text + "\n" + trust_text + "\n" + memory_text + " | " + private_chat_text


func _format_role_name(role: String) -> String:
	match role:
		"werewolf":
			return "狼人"
		"seer":
			return "预言家"
		"witch":
			return "女巫"
		"hunter":
			return "猎人"
		"guard":
			return "守卫"
		"villager":
			return "村民"
		_:
			return role


func _clear_character_grid() -> void:
	for child in character_grid.get_children():
		child.queue_free()


func _format_memory_preview(memories: Array) -> String:
	if memories.is_empty():
		return "这个 NPC 还没有记住任何对话。"

	var start_index = max(0, memories.size() - 3)
	var lines: Array[String] = ["最近记忆："]
	for index in range(start_index, memories.size()):
		var memory = memories[index]
		if typeof(memory) != TYPE_DICTIONARY:
			continue

		var message = str(memory.get("player_message", "")).strip_edges()
		if message.is_empty():
			message = "空消息"
		lines.append(str(index + 1) + ". 你说：" + message)

	if lines.size() == 1:
		return "这个 NPC 有记忆记录，但暂时无法显示内容。"

	var output := ""
	for line_index in range(lines.size()):
		if line_index > 0:
			output += "\n"
		output += lines[line_index]
	return output
