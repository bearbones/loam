class_name ScoreDoc
extends RefCounted
## A loam score export (docs/chamber-spec.md, format loam-score/1):
## score.json + stems/*.wav + shapes.f32, read at runtime with no
## import step. Everything the engine needs to move the machine,
## from the thing that decided every note.

var path: String
var dir: String
var doc: Dictionary
var events: Array = []
var cues: Array = []
var mechs: Array = []          # mechanism dicts, in instrument order
var mech_by_id: Dictionary = {}
var string_index: Dictionary = {}   # "harp05" -> 5
var stems: Dictionary = {}     # mech id -> AudioStreamWAV
var envelopes: Dictionary = {} # mech id -> PackedFloat32Array
var env_hz: float = 50.0
var shapes: PackedFloat32Array
var clips: Dictionary = {}     # clip id -> {nodes, rate_hz, frames, offset, t60_s, pick}
var duration_s: float = 0.0
var total_s: float = 0.0
var errors: PackedStringArray = []


static func default_path() -> String:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--score="):
			return a.substr(8)
	return ProjectSettings.globalize_path("res://").path_join("../render/chamber/score.json")


func load(p: String) -> bool:
	path = p
	dir = p.get_base_dir()
	if not FileAccess.file_exists(p):
		errors.append("no score at %s" % p)
		return false
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(p))
	if typeof(parsed) != TYPE_DICTIONARY:
		errors.append("score.json did not parse")
		return false
	doc = parsed
	if doc.get("format", "") != "loam-score/1":
		errors.append("unexpected format %s" % doc.get("format", "?"))
	events = doc.get("events", [])
	cues = doc.get("cues", [])
	duration_s = float(doc.get("duration_s", 0.0))
	total_s = float(doc.get("total_s", duration_s))
	for m in doc.get("instrument", {}).get("mechanisms", []):
		mechs.append(m)
		mech_by_id[m["id"]] = m
		var i := 0
		for s in m["strings"]:
			string_index[s["id"]] = i
			i += 1
	# stems in instrument order, then any bus-only stems (the chamber)
	var stem_files: Dictionary = doc.get("stems", {})
	for mid in stem_files:
		var wp: String = dir.path_join(stem_files[mid])
		if FileAccess.file_exists(wp):
			stems[mid] = AudioStreamWAV.load_from_file(wp)
		else:
			errors.append("missing stem %s" % wp)
	var envs: Dictionary = doc.get("envelopes", {})
	env_hz = float(envs.get("rate_hz", 50.0))
	for mid in envs.get("stems", {}):
		envelopes[mid] = PackedFloat32Array(envs["stems"][mid])
	var sh: Dictionary = doc.get("shapes", {})
	if not sh.is_empty():
		var sp: String = dir.path_join(sh.get("file", "shapes.f32"))
		var fa := FileAccess.open(sp, FileAccess.READ)
		if fa == null:
			errors.append("missing shapes %s" % sp)
		else:
			shapes = fa.get_buffer(fa.get_length()).to_float32_array()
			if shapes.size() != int(sh.get("total_floats", -1)):
				errors.append("shapes.f32 holds %d floats, header says %d"
						% [shapes.size(), int(sh.get("total_floats", -1))])
			for c in sh.get("clips", []):
				clips[c["id"]] = c
	return errors.is_empty()


func stem_ids() -> Array:
	var out: Array = []
	for m in mechs:
		if stems.has(m["id"]):
			out.append(m["id"])
	for mid in stems:
		if not out.has(mid):
			out.append(mid)
	return out


func envelope_at(mid: String, t: float) -> float:
	if not envelopes.has(mid):
		return 0.0
	var e: PackedFloat32Array = envelopes[mid]
	var i := int(t * env_hz)
	if i < 0 or i >= e.size():
		return 0.0
	return e[i]


## The string's displacement at `tau` seconds after its pluck, as
## `nodes` normalized samples (max |u| = 1 at the clip's peak), or
## an empty array once the clip has run out.
func shape_frame(clip_id: String, tau: float) -> PackedFloat32Array:
	if not clips.has(clip_id) or tau < 0.0:
		return PackedFloat32Array()
	var c: Dictionary = clips[clip_id]
	var fi := int(tau * float(c["rate_hz"]))
	if fi >= int(c["frames"]):
		return PackedFloat32Array()
	var n := int(c["nodes"])
	var off := int(c["offset"]) + fi * n
	return shapes.slice(off, off + n)


## Plan self-consistency, mirrored from loam.ruler.plan_consistent:
## per actuator no overlapping busy spans (each t_move at or after the
## previous t_head_free), t_move < t <= t_head_free <= t_free. A plan
## from before M1 carries no t_head_free, and t_free stands in.
func plan_consistent() -> Dictionary:
	var by_act: Dictionary = {}
	var bad := 0
	var unassigned := 0
	for e in events:
		if e.get("strings", []).is_empty():
			continue
		if e.get("actuator") == null:
			unassigned += 1
			continue
		var hf := float(e.get("t_head_free", e["t_free"]))
		if not (float(e["t_move"]) < float(e["t"]) and float(e["t"]) <= hf and hf <= float(e["t_free"])):
			bad += 1
		var k: String = "%s/%s" % [e["mech"], e["actuator"]]
		if not by_act.has(k):
			by_act[k] = []
		by_act[k].append(e)
	var overlaps := 0
	for k in by_act:
		var evs: Array = by_act[k]
		evs.sort_custom(func(a, b): return float(a["t"]) < float(b["t"]))
		for i in range(1, evs.size()):
			if float(evs[i]["t_move"]) < float(evs[i - 1].get("t_head_free", evs[i - 1]["t_free"])) - 1e-9:
				overlaps += 1
	return {"ok": overlaps == 0 and bad == 0 and unassigned == 0, "overlaps": overlaps,
			"bad_span": bad, "unassigned": unassigned, "actuators": by_act.size()}
