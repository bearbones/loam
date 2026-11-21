extends Control

signal seek_requested(t: float)
signal command_requested(key: Key)
signal camera_selected(view: int)

const Timeline := preload("res://score_timeline.gd")
const GOLD := Color("#e1bd83")
const PAPER := Color("#f0eadc")
const DIM := Color("#a8bbb8")
const VIEWS := ["Ensemble", "Harp", "Rake", "Bars", "Overhead", "Rear gallery",
	"Harp neck", "String face", "Pedal base", "Harp joint", "Sounding string",
	"Bar frame", "Neck action", "Flywheel", "Eyelets", "Ratchet", "Bass winding",
	"Soundbox ports", "Sympathetic chamber"]

var timeline := Timeline.new()
var track := TrackView.new()
var _title := Label.new()
var _signature := Label.new()
var _tempo := Label.new()
var _panel := PanelContainer.new()
var _row := BoxContainer.new()
var _readout := HBoxContainer.new()
var _modes := GridContainer.new()
var _play := Button.new()
var _clock := Label.new()
var _section := Label.new()
var _camera := OptionButton.new()
var _form := Button.new()
var _mix := Button.new()
var _score_button := Button.new()
var _end_time: String
var _tenth := -999
var _shown_form := ""
var _shown_mix := ""

func _style(fill: Color, border: Color, radius: int, dx: int, dy: int) -> StyleBoxFlat:
	var box := StyleBoxFlat.new()
	box.bg_color = fill
	box.border_color = border
	box.set_border_width_all(1)
	box.set_corner_radius_all(radius)
	box.content_margin_left = dx
	box.content_margin_right = dx
	box.content_margin_top = dy
	box.content_margin_bottom = dy
	return box

func bind(score: ScoreDoc) -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	var skin := Theme.new()
	skin.default_font_size = 14
	var normal := _style(Color("#15292c"), Color("#49605d"), 5, 11, 5)
	var hover := _style(Color("#233a3c"), GOLD, 5, 11, 5)
	for control in ["Button", "OptionButton"]:
		skin.set_stylebox("normal", control, normal)
		skin.set_stylebox("hover", control, hover)
		skin.set_stylebox("pressed", control, hover)
		skin.set_color("font_color", control, PAPER)
	theme = skin
	for label in [_signature, _title, _tempo]:
		add_child(label)
		label.add_theme_color_override("font_shadow_color", Color("#061114"))
		label.add_theme_constant_override("shadow_offset_y", 2)
	_signature.text = "L O A M     /     C L O C K W O R K"
	_signature.add_theme_font_size_override("font_size", 12)
	_signature.add_theme_color_override("font_color", GOLD)
	_title.text = str(score.doc.get("name", "The Chamber"))
	var serif := SystemFont.new()
	serif.font_names = PackedStringArray(["Instrument Serif", "Georgia", "DejaVu Serif"])
	_title.add_theme_font_override("font", serif)
	_title.add_theme_font_size_override("font_size", 40)
	_title.add_theme_color_override("font_color", PAPER)
	_tempo.text = "%s BPM" % str(score.doc.get("bpm", 84.0)).trim_suffix(".0")
	_tempo.add_theme_color_override("font_color", DIM)
	_tempo.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	add_child(track)
	track.score = score
	track.hide()
	add_child(_panel)
	_panel.add_theme_stylebox_override("panel", _style(Color("#0c1c20f5"), Color("#50615b"), 9, 16, 10))
	var stack := VBoxContainer.new()
	stack.add_theme_constant_override("separation", 6)
	_panel.add_child(stack)
	stack.add_child(_row)
	_row.add_theme_constant_override("separation", 8)
	_row.add_child(_readout)
	_readout.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_readout.add_theme_constant_override("separation", 12)
	_readout.add_child(_play)
	_play.custom_minimum_size.x = 66
	_play.tooltip_text = "Play or pause (Space). Home restarts with pre-roll."
	_play.pressed.connect(func(): command_requested.emit(KEY_SPACE))
	_readout.add_child(_clock)
	_clock.add_theme_color_override("font_color", PAPER)
	_readout.add_child(_section)
	_section.add_theme_color_override("font_color", GOLD)
	_modes.columns = 4
	_row.add_child(_modes)
	_modes.add_child(_camera)
	_camera.add_item("Auto camera")
	for title in VIEWS: _camera.add_item(title)
	_camera.fit_to_longest_item = false
	_camera.tooltip_text = "Select a camera (C cycles, A follows the score)"
	_camera.item_selected.connect(func(i: int): camera_selected.emit(i-1))
	_add_button(_form, "Cycle the frame form (F)", KEY_F)
	_add_button(_mix, "Switch master or dry stems (M). Keys 1–9 mute stems.", KEY_M)
	_add_button(_score_button, "Show the annotated score (T)", KEY_T)
	_score_button.text = "Score"
	_score_button.toggle_mode = true
	stack.add_child(timeline)
	timeline.bind(score)
	timeline.value_changed.connect(func(t: float): seek_requested.emit(t))
	_end_time = _stamp(score.total_s)
	resized.connect(_layout)
	_panel.minimum_size_changed.connect(_layout)
	_layout()

func _add_button(button: Button, hint: String, key: Key) -> void:
	_modes.add_child(button)
	button.tooltip_text = hint
	button.pressed.connect(func(): command_requested.emit(key))

func _layout() -> void:
	var margin := 14.0 if size.x < 720 else 28.0
	_signature.position = Vector2(margin, margin*.76)
	_title.position = _signature.position + Vector2(-1, 16)
	_tempo.position = Vector2(size.x-margin-120, margin*.76)
	_tempo.size.x = 120
	_tempo.visible = size.x >= 460
	_row.vertical = size.x < 720
	_modes.columns = 2 if size.x < 480 else 4
	_section.visible = size.x >= 380
	_panel.size = Vector2(size.x-margin*2.0, _panel.get_combined_minimum_size().y)
	_panel.position = Vector2(margin, size.y-_panel.size.y-margin*.65)
	var track_height := minf(230, maxf(65, _panel.position.y-110))
	track.position = Vector2(margin, _panel.position.y-track_height-8)
	track.size = Vector2(_panel.size.x, track_height)

static func _stamp(t: float) -> String:
	var tenths := floori(absf(t)*10)
	return "%s%d:%02d.%d" % ["−" if t < 0 else "", tenths/600, (tenths/10)%60, tenths%10]

func update_playback(t: float, playing: bool, view: int, form: String, mix: String) -> void:
	if not is_visible_in_tree(): return
	if _tenth != floori(t*10):
		_tenth = floori(t*10)
		_clock.text = "%s  /  %s" % [_stamp(t), _end_time]
	_section.text = timeline.section_at(t)
	_play.text = "Pause" if playing else ("Replay" if t >= timeline.max_value else "Play")
	var selection := view+1 if view >= -1 and view < VIEWS.size() else -1
	if _camera.selected != selection: _camera.select(selection)
	if form != _shown_form:
		_shown_form = form
		_form.text = form.capitalize()
	if mix != _shown_mix:
		_shown_mix = mix
		_mix.text = mix.capitalize()
	_score_button.set_pressed_no_signal(track.visible)
	if track.visible and track.time != t:
		track.time = t
		track.queue_redraw()
	if not is_equal_approx(timeline.value, t):
		timeline.set_value_no_signal(t)
		timeline.queue_redraw()
