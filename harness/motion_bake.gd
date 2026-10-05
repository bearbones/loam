class_name MotionBake
extends RefCounted
## The performance baked (formlab/bake.py, format loam-motion/1): every moving
## value of the rig sampled over the piece by formlab.rig.Rig, the one
## implementation of the motion. The harness plays it back and owns no motion
## vocabulary of its own: pose(), the shudders and the pawl are lookups.
##
## <asset>.motion.json (header) + <asset>.motion.bin (N float64 times, then N
## rows of `width` float32 values) sit next to the score. Between rows a value
## is linearly interpolated; the grid carries every contact and every corner of
## the path as a row of its own, so contacts land exactly. Before the first row
## and after the last the end row holds. tools/test_bake.py holds this reader to
## formlab.bake.Bake.

var header: Dictionary
var times: PackedFloat64Array
var frames: PackedFloat32Array
var width: int = 0
var channels: Dictionary = {}   # "harp_arm0.tip" -> offset (float index into a row)
var arms: Dictionary = {}       # aid -> the header's per-arm record
var mechanisms: Dictionary = {}
var head_l: float = .12
var errors: PackedStringArray = []
var _pawl_table: PackedFloat32Array
var _pawl_pitch: float = 1.0
var _ride_angle: float = NAN    # pawl.ride_angle: the nose on a tooth's tip (NAN in an older bake)
# one row a time, cached: a frame asks for a dozen channels at the same t
var _row_t: float = NAN
var _row_i: int = 0
var _row_w: float = 0.0


static func path_for(score_path: String, asset: String) -> String:
	return score_path.get_base_dir().path_join(asset+".motion.json")


## Loads the bake and refuses it when it was made from another score or
## another model: the header's fingerprints against the files on disk.
func load(json_path: String, score_path: String, manifest_path: String) -> bool:
	var fix := "run `python3 tools/bake_motion.py --asset=%s`" % json_path.get_file().get_slice(".", 0)
	if not FileAccess.file_exists(json_path):
		errors.append("no motion bake at %s — %s" % [json_path, fix]); return false
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(json_path))
	if typeof(parsed) != TYPE_DICTIONARY or parsed.get("format", "") != "loam-motion/1":
		errors.append("%s is not a loam-motion/1 bake — %s" % [json_path, fix]); return false
	header = parsed
	if FileAccess.get_sha256(score_path) != header["score_sha256"]:
		errors.append("stale motion bake: %s changed since it was baked — %s" % [score_path, fix]); return false
	if FileAccess.get_sha256(manifest_path) != header["manifest_sha256"]:
		errors.append("stale motion bake: %s changed since it was baked — %s" % [manifest_path, fix]); return false
	var fa := FileAccess.open(json_path.get_base_dir().path_join(header["data"]), FileAccess.READ)
	if fa == null:
		errors.append("missing %s — %s" % [header["data"], fix]); return false
	var n := int(header["samples"])
	width = int(header["width"])
	times = fa.get_buffer(int(header["times_bytes"])).to_float64_array()
	frames = fa.get_buffer(int(header["frames_bytes"])).to_float32_array()
	if times.size() != n or frames.size() != n*width:
		errors.append("%s holds %d times / %d values, header says %d x %d — %s"
				% [header["data"], times.size(), frames.size(), n, width, fix]); return false
	for c in header["channels"]: channels[c["name"]] = int(c["offset"])
	arms = header["arms"]
	mechanisms = header["mechanisms"]
	head_l = float(header["constants"]["HEAD_L"])
	_pawl_table = PackedFloat32Array(header["pawl"]["table"])
	_pawl_pitch = float(header["pawl"]["pitch"])
	var ra = header["pawl"].get("ride_angle")
	_ride_angle = NAN if ra == null else float(ra)
	return true


func constant(name: String) -> float:
	return float(header["constants"][name])


func _locate(t: float) -> void:
	if t == _row_t: return
	_row_t = t
	var i := times.bsearch(t, true)
	if i <= 0: _row_i = 1; _row_w = 0.0
	elif i >= times.size(): _row_i = times.size()-1; _row_w = 1.0
	else: _row_i = i; _row_w = (t-times[i-1])/(times[i]-times[i-1])


func _at(offset: int, t: float) -> float:
	_locate(t)
	var a := frames[(_row_i-1)*width+offset]
	return a+(frames[_row_i*width+offset]-a)*_row_w


func value(name: String, t: float) -> float:
	return _at(channels[name], t)


func vec(name: String, t: float) -> Vector3:
	var o: int = channels[name]
	return Vector3(_at(o, t), _at(o+1, t), _at(o+2, t))


## One arm at t: the carriage's pin (root), elbow, wrist, the tool frame's
## origin (tip), a hinged hammer's flip angle (head) and the felt face it
## carries (felt, derived: see head_offset).
func pose(aid: String, t: float) -> Dictionary:
	var tip := vec(aid+".tip", t)
	var theta := value(aid+".head", t)
	return {"root": vec(aid+".root", t), "elbow": vec(aid+".elbow", t), "wrist": vec(aid+".wrist", t),
		"tip": tip, "felt": tip+head_offset(aid, theta), "head": theta}


## A hinged head's felt face relative to the tool frame's origin at flip angle
## theta (formlab.rig.head_offset): the hinge is head_l above the origin and
## the face swings on it toward the arm's own rail. Zero for a rigid tool.
func head_offset(aid: String, theta: float) -> Vector3:
	if not hammer(aid): return Vector3.ZERO
	return Vector3(0, head_l*(1.0-cos(theta)), head_l*sin(theta)*flip_sign(aid))


func tip_at(aid: String, t: float) -> Vector3:
	return vec(aid+".tip", t)


func stepped(aid: String) -> bool: return bool(arms[aid]["stepped"])
func hammer(aid: String) -> bool: return bool(arms[aid]["hammer"])
func flip_sign(aid: String) -> float: return float(arms[aid]["flip_sign"])
func mech_of(aid: String) -> String: return str(arms[aid]["mech"])


## The blow shakes the assembly: the stand's thump, the rail's sag at mid-span
## and the gantry's sway, each exactly zero at the blow it answers.
func stand_thump(mid: String, t: float) -> float:
	return value(mid+".stand", t) if channels.has(mid+".stand") else 0.0
func rail_sag(aid: String, t: float) -> float: return value(aid+".sag", t)
func mast_sway(aid: String, t: float) -> float: return value(aid+".sway", t)


## How far the arm's pawl rides the rack's tips at t, in [0, 1] (its `.ride`
## channel, formlab.rig.Rig.pawl_ride); 0 for an arm that has none (a servo
## arm, an older bake). The hammer's is all 0.
func ride(aid: String, t: float) -> float:
	return value(aid+".ride", t) if channels.has(aid+".ride") else 0.0


## A stepped arm's clicks: [{t, teeth, pawl, step}] in time order; a servo arm
## has none. pawl 0 drops into the gap, 1 rides the tips (a fast freewheel);
## step 1 a stepped or homing landing (and every hammer click), 0 a freewheel's
## crossing of a tooth. An older bake's are all drop and step (formlab.bake.Bake.clicks).
func click_times(aid: String) -> Array:
	var out: Array = []
	var cs: Array = arms[aid]["clicks"]
	var pawl: Array = arms[aid].get("click_pawl", [])
	var step: Array = arms[aid].get("click_step", [])
	for i in cs.size():
		var c: Array = cs[i]
		out.append({"t": float(c[0]), "teeth": float(c[1]), "aid": aid,
			"pawl": int(pawl[i]) if i < pawl.size() else 0, "step": int(step[i]) if i < step.size() else 1})
	return out


## Each blow on an arm: [{t, gate_end, x, energy}] (gate_end null for the last);
## a mallet's also carry its stroke's v_in and e (read them with .get / has:
## the hammer's have neither). A mallet's gate_end is its next stroke's apex.
func blows(aid: String) -> Array: return arms[aid]["blows"]


## The roller detent pawl's angle for a carriage at rail position x (the arm's
## phase already added): one tooth of formlab.pawl.angle, periodic in the pitch,
## leaned toward pawl.ride_angle (the nose on a tip) by `ride` in [0, 1]. Every
## angle between the two is clear of the teeth. ride 0 is the table alone.
## The mirror of formlab.bake.Bake.pawl_angle.
func pawl_angle(x: float, ride_amount: float = 0.0) -> float:
	var n := _pawl_table.size()
	var u: float = fposmod(x, _pawl_pitch)/_pawl_pitch*n
	var k: int = int(floor(u))
	var w: float = u-floor(u)
	var a: float = lerpf(_pawl_table[k%n], _pawl_table[(k+1)%n], w)
	if ride_amount == 0.0: return a
	return a+((a if is_nan(_ride_angle) else _ride_angle)-a)*ride_amount


## The arm's pawl angle at t as the player poses it: the table at the
## carriage's x (the baked root) plus the arm's phase, ridden by its `.ride`
## channel (formlab.bake.Bake.pawl). NAN for an arm without a pawl. x is read
## in double precision (a Vector3 is float32: 0.5 µm at 4 m of rail is 1.4e-5 rad
## on the table's steepest flank).
func pawl(aid: String, t: float) -> float:
	var phase = arms[aid].get("pawl_phase")
	if phase == null: return NAN
	return pawl_angle(_at(channels[aid+".root"], t)+float(phase), ride(aid, t))


static func v(a: Array) -> Vector3:
	return Vector3(a[0], a[1], a[2])


## Where a string is struck or plucked: a struck bar at its middle, a string at
## the event's pick (or its own). Geometry, not motion.
static func contact(layout: Dictionary, sid: String, pick = null) -> Vector3:
	var s: Dictionary = layout["strings"][sid]
	var u := .5 if s["struck"] else float(s["pick"] if pick == null else pick)
	return v(s["a"]).lerp(v(s["b"]), u)


## Link frame: y along the link, x the pin axis (world X projected), z = x × y.
## Meshes are built at true length in this frame (formlab.linkage), never scaled.
static func link_basis(a: Vector3, b: Vector3) -> Basis:
	var y := (b-a).normalized()
	var x := Vector3.RIGHT - y*y.dot(Vector3.RIGHT)
	if x.length_squared()<.000001: x=Vector3.FORWARD
	x=x.normalized()
	return Basis(x,y,x.cross(y))
