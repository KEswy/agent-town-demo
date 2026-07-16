extends Area2D

signal dialog_requested(npc_name: String, dialog_text: String, wolf_character_id: int)

@export var npc_name: String = "Guide"
@export_multiline var dialog_text: String = "你好，我是第一个 AI NPC。后面我会接入记忆和知识库。"
@export var wolf_character_id: int = 0
@export var body_color: Color = Color(0.95, 0.58, 0.2, 1)

const SKIN_PATHS := {
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

var _player_nearby := false
var _alive := true
var _is_current_speaker := false
var _is_sheriff := false
var _campaign_status := ""

@onready var body_shape: Polygon2D = $Body
@onready var character_sprite: Sprite2D = $CharacterSprite
@onready var sheriff_badge: Polygon2D = $SheriffBadge
@onready var campaign_badge: Sprite2D = $CampaignBadge
@onready var campaign_pk_label: Label = $CampaignPKLabel
@onready var nearby_marker: Polygon2D = $NearbyMarker
@onready var turn_indicator: Polygon2D = $TurnIndicator
@onready var speech_hint: Node2D = $SpeechHint
@onready var name_label: Label = $NameLabel


func _ready() -> void:
	add_to_group("npc")
	body_entered.connect(_on_body_entered)
	body_exited.connect(_on_body_exited)
	nearby_marker.visible = false
	turn_indicator.visible = false
	speech_hint.visible = false
	body_shape.color = body_color
	_load_character_skin()
	_update_visual_state()


func is_player_nearby() -> bool:
	return _player_nearby


func request_dialog() -> void:
	if _player_nearby:
		dialog_requested.emit(npc_name, dialog_text, wolf_character_id)


func get_wolf_character_id() -> int:
	return wolf_character_id


func set_wolf_game_state(
	alive: bool,
	is_current_speaker: bool,
	is_sheriff: bool = false,
	campaign_status: String = ""
) -> void:
	_alive = alive
	_is_current_speaker = is_current_speaker
	_is_sheriff = is_sheriff
	_campaign_status = campaign_status
	_update_visual_state()


func _load_character_skin() -> void:
	var path := str(SKIN_PATHS.get(npc_name, ""))
	if path.is_empty() or not ResourceLoader.exists(path):
		character_sprite.visible = false
		body_shape.visible = true
		return
	var texture = load(path)
	if texture is Texture2D:
		character_sprite.texture = texture
		character_sprite.visible = true
		body_shape.visible = false


func _update_visual_state() -> void:
	var title := npc_name
	if wolf_character_id > 0:
		title += " [" + str(wolf_character_id) + "号]"
	if not _alive:
		title += "\n已出局"
	elif _is_current_speaker:
		title += "\n轮到发言"
	elif _is_sheriff:
		title += "\n警长"

	name_label.text = title
	body_shape.color = Color(0.42, 0.42, 0.42, 1) if not _alive else body_color
	character_sprite.modulate = Color(0.42, 0.42, 0.42, 0.62) if not _alive else Color.WHITE
	name_label.modulate = Color(0.65, 0.65, 0.65, 1) if not _alive else Color.WHITE
	nearby_marker.color = Color(1, 0.84, 0.2, 1) if _is_current_speaker else Color(1, 0.9, 0.32, 1)
	nearby_marker.scale = Vector2(1.35, 1.35) if _is_current_speaker else Vector2.ONE
	turn_indicator.visible = _alive and _is_current_speaker
	sheriff_badge.visible = _alive and _is_sheriff
	campaign_badge.visible = _alive and _campaign_status in ["candidate", "withdrawn"]
	campaign_badge.modulate = (
		Color(0.48, 0.52, 0.56, 1)
		if _campaign_status == "withdrawn"
		else Color(0.24, 0.68, 0.94, 1)
	)
	campaign_pk_label.visible = _alive and _campaign_status == "pk"


func _process(_delta: float) -> void:
	if turn_indicator.visible:
		turn_indicator.position.y = -56.0 + sin(Time.get_ticks_msec() / 180.0) * 4.0


func _on_body_entered(body: Node) -> void:
	if body.is_in_group("player"):
		_player_nearby = true
		nearby_marker.visible = true
		speech_hint.visible = true


func _on_body_exited(body: Node) -> void:
	if body.is_in_group("player"):
		_player_nearby = false
		nearby_marker.visible = false
		speech_hint.visible = false
