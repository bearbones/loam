class_name StringsView
extends Control
## The machine, seen: each mechanism's strings from the exported
## geometry, vibrating with the shape clip the simulation baked
## (fdstring.fdshape) — the vertex data the game will use, seen
## early. Struck bars flash and fade with their t60; the chamber
## glows with its stem envelope. Arms are dots that slide between
## strings along the exported plan (t_move -> t -> t_free).

var score: ScoreDoc
var time: float = 0.0
const VIS_GAIN := 22.0            # px of displacement per unit amp
const PALETTE := TrackView.PALETTE

var _world_min := Vector2(-2.2, -0.9)
var _world_max := Vector2(2.2, 0.9)


func _to_screen(p: Vector3) -> Vector2:
	var u := (p.x - _world_min.x) / (_world_max.x - _world_min.x)
	var v := (p.y - _world_min.y) / (_world_max.y - _world_min.y)
	return Vector2(u * size.x, size.y * (1.0 - v))


func _string_ends(m: Dictionary, s: Dictionary) -> Array:
	# a string is a segment of `length` centred on its pos, perpendicular
	# to the mechanism axis (in the x-y plane)
	var mp: Array = m["pos"]
	var sp: Array = s["pos"]
	var ax: Array = m["axis"]
	var base := Vector3(mp[0] + sp[0], mp[1] + sp[1], mp[2] + sp[2])
	var perp := Vector3(-ax[1], ax[0], 0.0).normalized()
	var half := perp * float(s["length"]) * 0.5
	return [base - half, base + half, perp]


func _draw() -> void:
	if score == null:
		return
	var font := ThemeDB.fallback_font
	draw_rect(Rect2(Vector2.ZERO, size), Color(0.06, 0.06, 0.07))
	# the chamber's glow
	var glow := score.envelope_at("chamber", time)
	if glow > 0.0:
		draw_rect(Rect2(Vector2.ZERO, size), Color(0.35, 0.22, 0.08, clampf(glow * 1.6, 0.0, 0.5)))
	# recent events per string: the latest pluck of each string
	var last_hit: Dictionary = {}
	var arm_pos: Dictionary = {}      # actuator id -> (string id, alpha, colour)
	for e in score.events:
		var t: float = float(e["t"])
		if t > time:
			continue
		for sid in e.get("strings", []):
			var prev = last_hit.get(sid)
			if prev == null or float(prev["t"]) < t:
				last_hit[sid] = e
	for m in score.mechs:
		var mid: String = m["id"]
		var cols := {}
		var k := 0
		for a in m["actuators"]:
			cols[a["id"]] = PALETTE[k % PALETTE.size()]
			arm_pos[a["id"]] = {"string": a["home"], "col": cols[a["id"]], "mech": mid, "lift": 1.0}
			k += 1
		var mat: String = m["material"]
		var struck: bool = m["kind"] == "struck"
		var mp: Array = m["pos"]
		draw_string(font, _to_screen(Vector3(mp[0], mp[1] + 0.42, 0)) + Vector2(-20, 0),
				"%s (%s)" % [mid, mat], HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color(0.7, 0.7, 0.7))
		for s in m["strings"]:
			var ends := _string_ends(m, s)
			var a: Vector3 = ends[0]
			var b: Vector3 = ends[1]
			var pa := _to_screen(a)
			var pb := _to_screen(b)
			var hit = last_hit.get(s["id"])
			var tau := -1.0
			var amp := 0.0
			var col := Color(0.55, 0.55, 0.6)
			if hit != null:
				# the string's own contact time (a rake roll's at its onset)
				var idx: int = hit["strings"].find(s["id"])
				tau = time - float(ScoreDoc.string_times(hit)[idx])
				amp = float(hit.get("amp", 1.0))
				if hit.get("actuator") != null and cols.has(hit["actuator"]):
					col = cols[hit["actuator"]]
			if struck:
				var t60 := 1.4
				var lit := 0.0
				if tau >= 0.0:
					lit = pow(10.0, -3.0 * tau / t60)
				var wpx := 14.0
				var r := Rect2(pa - Vector2(wpx * 0.5, 0), Vector2(wpx, (pb - pa).y))
				draw_rect(r, Color(0.45, 0.28, 0.18).lerp(Color(1.0, 0.85, 0.5), lit * amp))
				draw_rect(r, Color(0.2, 0.15, 0.1), false, 1.0)
			else:
				var frame := PackedFloat32Array()
				if hit != null and tau >= 0.0 and hit.get("shape") != null:
					frame = score.shape_frame(hit["shape"], tau)
				if frame.is_empty():
					draw_line(pa, pb, col if tau < 0.0 else col.darkened(0.2), 1.5)
				else:
					var pts := PackedVector2Array()
					var n := frame.size()
					var dir := (pb - pa)
					var nrm := Vector2(-dir.y, dir.x).normalized()
					for i in range(n):
						var u := float(i) / float(n - 1)
						pts.append(pa + dir * u + nrm * frame[i] * amp * VIS_GAIN)
					draw_polyline(pts, col.lightened(0.3), 2.0, true)
			# the arm resting here (or moving to here)?
		# arms: interpolate along the plan
		for e in score.events:
			if e["mech"] != mid or e.get("actuator") == null:
				continue
			var tm: float = float(e["t_move"])
			var tf: float = float(e["t_free"])
			if time < tm or time > tf + 2.0:
				continue
			var aid: String = e["actuator"]
			var st: Dictionary = arm_pos[aid]
			if time <= float(e["t"]):
				var u := (time - tm) / maxf(float(e["t"]) - tm, 1e-3)
				st["from"] = e.get("from_string", e["strings"][0])
				st["string"] = e["strings"][0]
				st["u"] = u
				st["lift"] = 1.0 - u * u        # dives in
			else:
				st["from"] = e["strings"][0]
				st["string"] = e["strings"][-1]
				st["u"] = 1.0
				st["lift"] = clampf((time - float(e["t"])) / 0.15, 0.0, 1.0)
		for aid in arm_pos:
			var st: Dictionary = arm_pos[aid]
			if st["mech"] != mid:
				continue
			var sid: String = st["string"]
			var s_to: Dictionary = m["strings"][score.string_index[sid]]
			var p_to := _to_screen(_string_ends(m, s_to)[1] + Vector3(0, 0.06, 0))
			var p := p_to
			if st.has("from") and st.has("u") and st["u"] < 1.0 and score.string_index.has(st["from"]):
				var s_from: Dictionary = m["strings"][score.string_index[st["from"]]]
				var p_from := _to_screen(_string_ends(m, s_from)[1] + Vector3(0, 0.06, 0))
				var u: float = st["u"]
				u = u * u * (3.0 - 2.0 * u)
				p = p_from.lerp(p_to, u)
			p.y -= 10.0 * float(st["lift"])
			draw_circle(p, 6.0, st["col"])
			draw_circle(p, 6.0, Color.BLACK, false, 1.0)
