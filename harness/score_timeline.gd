extends HSlider
## A seekable overview of the exported stem envelopes. Rasterize the bars
## when the layout changes, then tint two regions of the same texture.

const PLAYED := Color("#deb879")
const AHEAD := Color("#537377")
const HEIGHT := 24
const PITCH := 4

var _levels := PackedFloat32Array()
var _texture: ImageTexture
var _sections := PackedFloat64Array()
var _names := PackedStringArray()
var _rate := 50.0

func bind(score: ScoreDoc) -> void:
	min_value = -1.0
	max_value = score.total_s
	step = .001
	_rate = score.env_hz
	scrollable = false
	tooltip_text = "Seek through the score"
	custom_minimum_size.y = HEIGHT
	var empty := StyleBoxEmpty.new()
	for style in ["slider", "grabber_area", "grabber_area_highlight"]:
		add_theme_stylebox_override(style, empty)
	var blank := ImageTexture.create_from_image(Image.create_empty(1, 1, false, Image.FORMAT_RGBA8))
	for icon in ["grabber", "grabber_highlight", "grabber_disabled"]:
		add_theme_icon_override(icon, blank)
	for stem in score.envelopes:
		var samples: PackedFloat32Array = score.envelopes[stem]
		if samples.size() > _levels.size(): _levels.resize(samples.size())
		for i in samples.size():
			_levels[i] = maxf(_levels[i], samples[i])
	var cues := score.cues.filter(func(c): return c["kind"] == "section")
	cues.sort_custom(func(a, b): return a["t"] < b["t"])
	for cue in cues:
		_sections.append(cue["t"])
		_names.append(str(cue.get("name", "")).replace("+", " + ").replace("-", " ").capitalize())
	resized.connect(_rasterize)
	_rasterize()

func section_at(t: float) -> String:
	var end := _sections.bsearch(t, false)
	if end == 0: return "Pre-roll" if t < 0 else ""
	return _names[end-1]

func _rasterize() -> void:
	var w := floori(size.x)
	if w < 1: return
	var img := Image.create_empty(w, HEIGHT, false, Image.FORMAT_RGBA8)
	for x in range(0, w, PITCH):
		var start := clampi(floori(lerpf(min_value, max_value, float(x)/w)*_rate), 0, _levels.size())
		var end := clampi(ceili(lerpf(min_value, max_value, float(x+PITCH)/w)*_rate), 0, _levels.size())
		var level := 0.0
		for i in range(start, end):
			level = maxf(level, _levels[i])
		var half_h := 1 + roundi(sqrt(clampf(level, 0.0, 1.0)) * (HEIGHT*.5-3))
		img.fill_rect(Rect2i(x, HEIGHT/2-half_h, mini(2, w-x), half_h*2), Color.WHITE)
	_texture = ImageTexture.create_from_image(img)
	queue_redraw()

func _draw() -> void:
	if _texture == null: return
	var w := float(_texture.get_width())
	var y := roundf((size.y-HEIGHT)*.5)
	var x := clampf(ratio, 0.0, 1.0)*w
	draw_texture_rect_region(_texture, Rect2(0,y,x,HEIGHT), Rect2(0,0,x,HEIGHT), PLAYED)
	draw_texture_rect_region(_texture, Rect2(x,y,w-x,HEIGHT), Rect2(x,0,w-x,HEIGHT), AHEAD)
	for t in _sections:
		var mark := inverse_lerp(min_value, max_value, t)*w
		draw_line(Vector2(mark, y), Vector2(mark, y+HEIGHT), Color("#b8b8a783"))
	draw_line(Vector2(x,y), Vector2(x,y+HEIGHT), Color("#ffebbb"), 2.0)
