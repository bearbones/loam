extends SceneTree
## Headless check of a loam score export against what the harness
## needs. Run (after `python3 songs/chamber.py` has rendered):
##   godot --headless --path harness -s dev/test_load.gd [-- --score=...]
## Prints HARNESS: PASS or the failures.

func _init() -> void:
	var fails := PackedStringArray()
	var sd := ScoreDoc.new()
	var ok := sd.load(ScoreDoc.default_path())
	if not ok:
		for e in sd.errors:
			fails.append(e)
	print("  score %s: %d events, %d cues, %d mechanisms, %d stems, %d clips (%d floats)" % [
			sd.doc.get("name", "?"), sd.events.size(), sd.cues.size(), sd.mechs.size(),
			sd.stems.size(), sd.clips.size(), sd.shapes.size()])
	if sd.events.size() != int(sd.doc.get("stats", {}).get("events", -1)):
		fails.append("event count %d != stats.events" % sd.events.size())
	# every event's strings resolve to its mechanism
	var bad_ref := 0
	for e in sd.events:
		for s in e.get("strings", []):
			if not sd.string_index.has(s):
				bad_ref += 1
	if bad_ref > 0:
		fails.append("%d string references unresolved" % bad_ref)
	# plan consistency — the engine's precondition, checked here too
	var pc := sd.plan_consistent()
	print("  plan: ok=%s overlaps=%d bad_span=%d unassigned=%d over %d actuators" % [
			pc["ok"], pc["overlaps"], pc["bad_span"], pc["unassigned"], pc["actuators"]])
	if not pc["ok"]:
		fails.append("plan inconsistent")
	# shape clips: every plucked event names a clip that exists, and a
	# frame reads back at the right size
	var named := 0
	var missing := 0
	for e in sd.events:
		var c = e.get("shape")
		if c == null:
			continue
		named += 1
		if not sd.clips.has(c):
			missing += 1
	if missing > 0:
		fails.append("%d events name a missing shape clip" % missing)
	for cid in sd.clips:
		var fr := sd.shape_frame(cid, 0.0)
		if fr.size() != int(sd.clips[cid]["nodes"]):
			fails.append("clip %s frame 0 has %d nodes, header says %d" % [cid, fr.size(), int(sd.clips[cid]["nodes"])])
		var peak := 0.0
		for v in fr:
			peak = maxf(peak, absf(v))
		if peak < 0.5:
			fails.append("clip %s frame 0 peak %.2f — the triangle should be near 1" % [cid, peak])
	print("  shapes: %d events named, %d clips" % [named, sd.clips.size()])
	# stems: length agrees with the score's total_s
	for mid in sd.stems:
		var st: AudioStreamWAV = sd.stems[mid]
		var secs := st.get_length()
		if absf(secs - sd.total_s) > 0.05:
			fails.append("stem %s is %.2f s, score says %.2f" % [mid, secs, sd.total_s])
	# envelopes present for every stem
	for mid in sd.stems:
		if not sd.envelopes.has(mid):
			fails.append("no envelope for stem %s" % mid)
	if fails.is_empty():
		print("HARNESS: PASS")
	else:
		for f in fails:
			print("  FAIL " + f)
		print("HARNESS: FAIL")
	quit(0 if fails.is_empty() else 1)
