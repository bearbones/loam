extends Control
## loam chamber harness — a debug visual for a loam score export.
##   godot --path harness [-- --score=/path/to/score.json]
## Space play/pause · Home restart · ←/→ seek 2 s · Z/X zoom track ·
## 1..9 mute stem N · S screenshot to SHOT env path (or shot.png).
## SHOT=<png> godot --path harness  captures one frame at 48 s and quits.

var score := ScoreDoc.new()
var players: Dictionary = {}
var playing := false
var scrub_t := 0.0
var track: TrackView
var strings: StringsView
var header: Label
var _shot_path := ""
var _shot_frames := 0


func _ready() -> void:
	var ok := score.load(ScoreDoc.default_path())
	for e in score.errors:
		push_warning(e)
	strings = StringsView.new()
	strings.score = score
	add_child(strings)
	track = TrackView.new()
	track.score = score
	add_child(track)
	header = Label.new()
	header.add_theme_font_size_override("font_size", 13)
	header.add_theme_color_override("font_color", Color(0.9, 0.9, 0.9))
	add_child(header)
	_layout()
	resized.connect(_layout)
	for mid in score.stem_ids():
		var p := AudioStreamPlayer.new()
		p.stream = score.stems[mid]
		add_child(p)
		players[mid] = p
	_shot_path = OS.get_environment("SHOT")
	if _shot_path != "":
		scrub_t = 48.0
	elif ok:
		_play_from(0.0)
	print("harness: %s — %d events, %d cues, %d stems, %d clips%s" % [
			score.doc.get("name", "?"), score.events.size(), score.cues.size(),
			score.stems.size(), score.clips.size(),
			"" if ok else " (with errors)"])


func _layout() -> void:
	var h := size.y
	header.position = Vector2(8, 4)
	header.size = Vector2(size.x - 16, 20)
	strings.position = Vector2(0, 26)
	strings.size = Vector2(size.x, h * 0.55 - 26)
	track.position = Vector2(0, h * 0.55)
	track.size = Vector2(size.x, h * 0.45)


func _play_from(t: float) -> void:
	scrub_t = t
	for mid in players:
		players[mid].play(t)
	playing = true


func _stop() -> void:
	scrub_t = _clock()
	for mid in players:
		players[mid].stop()
	playing = false


func _clock() -> float:
	if not playing or players.is_empty():
		return scrub_t
	var p: AudioStreamPlayer = players.values()[0]
	if not p.playing:
		return scrub_t
	return p.get_playback_position() + AudioServer.get_time_since_last_mix() \
			- AudioServer.get_output_latency()


func _section_at(t: float) -> String:
	var name := ""
	for c in score.cues:
		if c["kind"] == "section" and float(c["t"]) <= t:
			name = c.get("name", "")
	return name


func _process(_dt: float) -> void:
	var t := _clock()
	if playing and t >= score.total_s:
		_stop()
		scrub_t = 0.0
	track.time = t
	strings.time = t
	track.queue_redraw()
	strings.queue_redraw()
	var live := 0
	for e in score.events:
		if float(e["t"]) <= t and t < float(e["t"]) + float(e.get("dur", 0.0)):
			live += 1
	header.text = "%s   %6.2f s   bar %5.2f   section %-10s   %d ringing   [space] play/pause  [←→] seek  [1-9] mute  [Z/X] zoom" % [
			score.doc.get("name", "?"), t, t / (60.0 / float(score.doc.get("bpm", 120.0))) / 4.0,
			_section_at(t), live]
	if _shot_path != "":
		_shot_frames += 1
		if _shot_frames == 3:
			var img := get_viewport().get_texture().get_image()
			img.save_png(_shot_path)
			print("harness: wrote %s" % _shot_path)
			get_tree().quit()


func _unhandled_key_input(ev: InputEvent) -> void:
	if not ev.is_pressed():
		return
	match ev.keycode:
		KEY_SPACE:
			if playing:
				_stop()
			else:
				_play_from(scrub_t)
		KEY_HOME:
			_play_from(0.0)
		KEY_LEFT:
			_play_from(maxf(_clock() - 2.0, 0.0))
		KEY_RIGHT:
			_play_from(minf(_clock() + 2.0, score.total_s - 0.1))
		KEY_Z:
			track.zoom_s = maxf(track.zoom_s * 0.7, 3.0)
		KEY_X:
			track.zoom_s = minf(track.zoom_s / 0.7, score.total_s)
		KEY_S:
			var p := _shot_path if _shot_path != "" else "shot.png"
			get_viewport().get_texture().get_image().save_png(p)
			print("harness: wrote %s" % p)
		_:
			if ev.keycode >= KEY_1 and ev.keycode <= KEY_9:
				var ids := score.stem_ids()
				var i: int = ev.keycode - KEY_1
				if i < ids.size():
					var mid: String = ids[i]
					var m: bool = not track.muted.get(mid, false)
					track.muted[mid] = m
					players[mid].volume_db = -80.0 if m else 0.0
