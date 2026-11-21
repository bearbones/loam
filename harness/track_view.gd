class_name TrackView
extends Control
## The annotated track: one lane per stem; events as ticks (pitch up,
## amp = height, actuator = colour), motion [t_move, t] and recover
## [t, t_free] spans as bars under the tick, cues as full-height
## lines, the stem envelope as a grey fill, and the playhead. The
## picture loam's Score.plot draws, live.

class Lane:
	var id: String
	var events: Array = []
	var onsets := PackedFloat64Array()
	var colors: Dictionary
	var envelope: ArrayMesh
	var low := INF
	var high := -INF

var _lanes: Array[Lane] = []
var score: ScoreDoc:
	set(value):
		score = value
		_bind_score()
		queue_redraw()
var time: float = 0.0
var zoom_s: float = 24.0          # seconds across the view
var muted: Dictionary = {}
const PALETTE := [Color("#7ccbc0"), Color("#dfad74"), Color("#a9afdf"),
		Color("#dc8d88"), Color("#abc58b"), Color("#aa9cca")]
const BACKGROUND := Color("#0c1c20")
const LANE_GAP := 6.0
const LEFT := 64.0


func _actuator_colors(mid: String) -> Dictionary:
	var out := {}
	if not score.mech_by_id.has(mid):
		return out
	var k := 0
	for a in score.mech_by_id[mid]["actuators"]:
		out[a["id"]] = PALETTE[k % PALETTE.size()]
		k += 1
	return out


func _bind_score() -> void:
	_lanes.clear()
	if score == null: return
	clip_contents = true
	var by_id := {}
	for mid in score.stem_ids():
		var lane := Lane.new()
		lane.id = mid
		lane.colors = _actuator_colors(mid)
		if score.envelopes.has(mid):
			lane.envelope = _envelope_mesh(score.envelopes[mid], score.env_hz)
		by_id[mid] = lane
		_lanes.append(lane)
	for event in score.events:
		var lane: Lane = by_id.get(event["mech"])
		if lane == null: continue
		lane.events.append(event)
		for pitch in event.get("midis", []):
			lane.low = minf(lane.low, pitch)
			lane.high = maxf(lane.high, pitch)
	for lane in _lanes:
		lane.events.sort_custom(func(a, b): return a["t"] < b["t"])
		for event in lane.events:
			lane.onsets.append(event["t"])
		if lane.low == INF: lane.low = 0.0; lane.high = 0.0
		lane.low -= 1.0
		lane.high += 1.0

## One immutable strip in seconds × amplitude. Pan and zoom change only the
## draw transform. Silent stretches are valid degenerate strip triangles.
static func _envelope_mesh(samples: PackedFloat32Array, rate: float) -> ArrayMesh:
	if samples.size() < 2: return null
	var points := PackedVector2Array()
	points.resize(2*samples.size())
	for i in samples.size():
		var x := float(i)/rate
		points[2*i] = Vector2(x, 0.0)
		points[2*i+1] = Vector2(x, samples[i])
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = points
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLE_STRIP, arrays)
	return mesh

func _draw() -> void:
	if score == null:
		return
	var font := ThemeDB.fallback_font
	var w := size.x
	var h := size.y
	var lane_h: float = (h - 32.0 - LANE_GAP * (_lanes.size() + 1)) / float(maxi(_lanes.size(), 1))
	var t0 := clampf(time - zoom_s * 0.35, 0.0, maxf(score.total_s - zoom_s, 0.0))
	var t1 := t0 + zoom_s
	var px_per_s := (w - LEFT) / zoom_s
	draw_rect(Rect2(0, 0, w, h), BACKGROUND)
	if lane_h <= 0.0 or w <= LEFT: return
	var y := 26.0 + LANE_GAP
	for data in _lanes:
		var mid := data.id
		var lane := Rect2(LEFT, y, w - LEFT, lane_h)
		var dim: bool = muted.get(mid, false)
		draw_rect(lane, Color("#172d31") if not dim else Color("#122326"))
		if data.envelope != null:
			var transform := Transform2D(Vector2(px_per_s, 0), Vector2(0, -lane_h*.9),
					Vector2(LEFT-t0*px_per_s, y+lane_h))
			draw_mesh(data.envelope, null, transform, Color("#2b5052") if not dim else Color("#1a3134"))
			draw_rect(Rect2(0,y,LEFT,lane_h), BACKGROUND)
		var lo := data.low
		var hi := data.high
		var cols := data.colors
		if not data.events.is_empty():
			for index in range(data.onsets.bsearch(t0), data.onsets.bsearch(t1, false)):
				var e: Dictionary = data.events[index]
				var t: float = float(e["t"])
				var tf: float = float(e.get("t_free", t))
				var tm: float = float(e.get("t_move", t))
				var c: Color = cols.get(e.get("actuator"), Color(0.6, 0.6, 0.6))
				if dim:
					c.a = 0.3
				var midis: Array = e.get("midis", [])
				var ym: float = y + lane_h * (1.0 - ((float(midis[0]) if midis.size() > 0 else (lo + hi) * 0.5) - lo) / (hi - lo))
				if e.get("actuator") != null:
					var x_m := maxf(LEFT, LEFT + (tm - t0) * px_per_s)
					var x_t := LEFT + (t - t0) * px_per_s
					var x_f := LEFT + (tf - t0) * px_per_s
					draw_line(Vector2(x_m, ym), Vector2(x_t, ym), Color(c, c.a * 0.45), 4.0)
					draw_line(Vector2(x_t, ym), Vector2(x_f, ym), Color(c, c.a * 0.2), 4.0)
				elif not e.get("strings", []).is_empty():
					var x_t := LEFT + (t - t0) * px_per_s
					draw_line(Vector2(x_t - 5, ym - 5), Vector2(x_t + 5, ym + 5), Color.RED, 2.0)
					draw_line(Vector2(x_t - 5, ym + 5), Vector2(x_t + 5, ym - 5), Color.RED, 2.0)
				var amp: float = float(e.get("amp", 1.0))
				var x := LEFT + (t - t0) * px_per_s
				var lit := absf(time - t) < 0.12
				for m in midis:
					var yy: float = y + lane_h * (1.0 - (float(m) - lo) / (hi - lo))
					draw_line(Vector2(x, yy - 5.0 * amp - 2), Vector2(x, yy + 5.0 * amp + 2),
							Color.WHITE if lit else c, 3.0 if lit else 2.0)
			# legend
			var lx := LEFT + 6.0
			for aid in cols:
				draw_rect(Rect2(lx, y + 4, 10, 10), cols[aid])
				draw_string(font, Vector2(lx + 13, y + 13), aid, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, Color(0.8, 0.8, 0.8))
				lx += 90.0
		draw_string(font, Vector2(6, y + lane_h * 0.5 + 5), mid, HORIZONTAL_ALIGNMENT_LEFT, -1, 13,
				Color(0.9, 0.9, 0.9) if not dim else Color(0.5, 0.5, 0.5))
		y += lane_h + LANE_GAP
	# cues
	for c in score.cues:
		var t: float = float(c["t"])
		if t < t0 or t > t1:
			continue
		var x := LEFT + (t - t0) * px_per_s
		var col := Color(0.9, 0.85, 0.4, 0.8) if c["kind"] == "section" else Color(0.6, 0.8, 1.0, 0.5)
		draw_line(Vector2(x, 0), Vector2(x, h), col, 1.0)
		draw_string(font, Vector2(x + 3, 12 if c["kind"] == "section" else 24),
				"%s:%s" % [c["kind"], c.get("name", "")], HORIZONTAL_ALIGNMENT_LEFT, -1, 10, col)
	# time ruler
	var s0 := int(floor(t0))
	for s in range(s0, int(ceil(t1)) + 1):
		var x := LEFT + (float(s) - t0) * px_per_s
		draw_line(Vector2(x, h - 6), Vector2(x, h), Color(0.5, 0.5, 0.5))
		if s % 5 == 0:
			draw_string(font, Vector2(x + 2, h - 8), str(s), HORIZONTAL_ALIGNMENT_LEFT, -1, 10, Color(0.6, 0.6, 0.6))
	# playhead
	var xp := LEFT + (time - t0) * px_per_s
	draw_line(Vector2(xp, 0), Vector2(xp, h), Color(1, 1, 1, 0.9), 2.0)
