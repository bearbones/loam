class_name TrackView
extends Control
## The annotated track: one lane per stem; events as ticks (pitch up,
## amp = height, actuator = colour), motion [t_move, t] and recover
## [t, t_free] spans as bars under the tick, cues as full-height
## lines, the stem envelope as a grey fill, and the playhead. The
## picture loam's Score.plot draws, live.

var score: ScoreDoc
var time: float = 0.0
var zoom_s: float = 24.0          # seconds across the view
var muted: Dictionary = {}
const PALETTE := [Color(0.12, 0.47, 0.71), Color(1.0, 0.50, 0.05),
		Color(0.17, 0.63, 0.17), Color(0.84, 0.15, 0.16),
		Color(0.58, 0.40, 0.74), Color(0.55, 0.34, 0.29)]
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


func _draw() -> void:
	if score == null:
		return
	var font := ThemeDB.fallback_font
	var ids := score.stem_ids()
	var w := size.x
	var h := size.y
	var lane_h: float = (h - LANE_GAP * (ids.size() + 1)) / float(maxi(ids.size(), 1))
	var t0 := clampf(time - zoom_s * 0.35, 0.0, maxf(score.total_s - zoom_s, 0.0))
	var t1 := t0 + zoom_s
	var px_per_s := (w - LEFT) / zoom_s
	draw_rect(Rect2(0, 0, w, h), Color(0.09, 0.09, 0.1))
	var y := LANE_GAP
	for mid in ids:
		var lane := Rect2(LEFT, y, w - LEFT, lane_h)
		var dim: bool = muted.get(mid, false)
		draw_rect(lane, Color(0.13, 0.13, 0.15) if not dim else Color(0.11, 0.11, 0.12))
		# envelope fill
		if score.envelopes.has(mid):
			var pts := PackedVector2Array()
			pts.append(Vector2(LEFT, y + lane_h))
			var e: PackedFloat32Array = score.envelopes[mid]
			var i0 := maxi(int(t0 * score.env_hz), 0)
			var i1 := mini(int(t1 * score.env_hz) + 1, e.size())
			for i in range(i0, i1):
				var x := LEFT + (float(i) / score.env_hz - t0) * px_per_s
				pts.append(Vector2(x, y + lane_h - e[i] * lane_h * 0.9))
			pts.append(Vector2(LEFT + (float(i1) / score.env_hz - t0) * px_per_s, y + lane_h))
			if pts.size() >= 3:
				draw_colored_polygon(pts, Color(0.3, 0.3, 0.33, 0.55 if not dim else 0.2))
		# events
		var evs: Array = []
		var lo := 1e9
		var hi := -1e9
		for e in score.events:
			if e["mech"] != mid:
				continue
			evs.append(e)
			for m in e.get("midis", []):
				lo = minf(lo, float(m))
				hi = maxf(hi, float(m))
		if evs.size() > 0:
			lo -= 1.0
			hi += 1.0
			var cols := _actuator_colors(mid)
			for e in evs:
				var t: float = float(e["t"])
				var tf: float = float(e.get("t_free", t))
				var tm: float = float(e.get("t_move", t))
				if t < t0 or t > t1:
					continue
				var c: Color = cols.get(e.get("actuator"), Color(0.6, 0.6, 0.6))
				if dim:
					c.a = 0.3
				var midis: Array = e.get("midis", [])
				var ym: float = y + lane_h * (1.0 - ((float(midis[0]) if midis.size() > 0 else (lo + hi) * 0.5) - lo) / (hi - lo))
				if e.get("actuator") != null:
					var x_m := LEFT + (tm - t0) * px_per_s
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
