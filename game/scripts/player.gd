extends CharacterBody2D

@export var speed: float = 180.0

@onready var camera: Camera2D = $Camera2D
@onready var character_sprite: Sprite2D = $CharacterSprite
@onready var sheriff_badge: Polygon2D = $SheriffBadge
@onready var campaign_badge: Sprite2D = $CampaignBadge
@onready var campaign_pk_label: Label = $CampaignPKLabel

var _camera_tween: Tween
var _movement_release_lock := false


func _ready() -> void:
	add_to_group("player")


func _physics_process(_delta: float) -> void:
	if _movement_release_lock:
		velocity = Vector2.ZERO
		move_and_slide()
		if not _is_any_movement_key_physically_pressed():
			_movement_release_lock = false
		return

	if not get_tree().get_nodes_in_group("dialog_open").is_empty() or _has_text_input_focus():
		velocity = Vector2.ZERO
		move_and_slide()
		return

	var direction := Input.get_vector("move_left", "move_right", "move_up", "move_down")
	velocity = direction * speed
	move_and_slide()


func _has_text_input_focus() -> bool:
	var focus_owner := get_viewport().gui_get_focus_owner()
	if focus_owner is LineEdit:
		return focus_owner.is_visible_in_tree() and focus_owner.editable
	if focus_owner is TextEdit:
		return focus_owner.is_visible_in_tree() and focus_owner.editable
	return false


func lock_movement_until_release() -> void:
	_movement_release_lock = _is_any_movement_key_physically_pressed()
	velocity = Vector2.ZERO
	for action in ["move_left", "move_right", "move_up", "move_down"]:
		if InputMap.has_action(action):
			Input.action_release(action)


func _is_any_movement_key_physically_pressed() -> bool:
	for keycode in [KEY_W, KEY_A, KEY_S, KEY_D, KEY_LEFT, KEY_RIGHT, KEY_UP, KEY_DOWN]:
		if Input.is_physical_key_pressed(keycode):
			return true
	return false


func set_wolf_game_state(alive: bool, is_sheriff: bool, campaign_status: String = "") -> void:
	character_sprite.modulate = Color(0.42, 0.42, 0.42, 0.62) if not alive else Color.WHITE
	sheriff_badge.visible = alive and is_sheriff
	campaign_badge.visible = alive and campaign_status in ["candidate", "withdrawn"]
	campaign_badge.modulate = (
		Color(0.48, 0.52, 0.56, 1)
		if campaign_status == "withdrawn"
		else Color(0.24, 0.68, 0.94, 1)
	)
	campaign_pk_label.visible = alive and campaign_status == "pk"


func set_menu_safe_area(menu_expanded: bool, menu_width: float) -> void:
	if _camera_tween != null and _camera_tween.is_valid():
		_camera_tween.kill()

	var target_offset := Vector2(menu_width * 0.75, 0.0) if menu_expanded else Vector2.ZERO
	_camera_tween = create_tween()
	_camera_tween.set_trans(Tween.TRANS_QUAD)
	_camera_tween.set_ease(Tween.EASE_OUT)
	_camera_tween.tween_property(camera, "offset", target_offset, 0.22)
