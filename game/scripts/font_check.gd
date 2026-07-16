extends SceneTree

const FONT_PATH := "res://assets/fonts/NotoSansSC-Variable.ttf"
const REQUIRED_TEXT := "狼人杀固定人物座次梅西C罗周深梅长苏塞尔达小骑士大黄蜂喜羊羊懒羊羊洛洛奇异博士公开依据向量关键词警上竞选退水警长警徽暂时归票最终调整出局左右投票并公布女巫解药毒药狼队友"


func _initialize() -> void:
	var font: Font = load(FONT_PATH)
	if font == null:
		push_error("Failed to load dialog font: " + FONT_PATH)
		quit(1)
		return

	var missing_characters: Array[String] = []
	for character in REQUIRED_TEXT:
		if not font.has_char(character.unicode_at(0)):
			missing_characters.append(character)

	if not missing_characters.is_empty():
		push_error("Dialog font is missing characters: " + "、".join(missing_characters))
		quit(1)
		return

	print("Dialog font glyph check passed.")
	quit()
