class_name MotionBake
extends RefCounted
## The performance baked (formlab/bake.py, format loam-motion/2): every moving
## value of the rig sampled over the piece by formlab.rig.Rig, the one
## implementation of the motion. The harness plays it back and owns no motion
## vocabulary of its own: pose(), the shudders and the pawl are lookups, and
## every moving part is posed from the header's joints table (frames_at, then
## MotionRig.apply).
##
## <asset>.motion.json (header) + <asset>.motion.bin (N float64 times, then N
## rows of `width` float32 values) sit next to the score. Between rows a value
## is linearly interpolated; the grid carries every contact and every corner of
## the path as a row of its own, so contacts land exactly. Before the first row
## and after the last the end row holds. tools/test_bake.py holds this reader to
## formlab.bake.Bake (and frames_at to formlab.kinematics.evaluate).
##
## The joints table (formlab/bake.py's docstring is the spec): each joint has a
## parent earlier in the list, a type (revolute / prismatic / fixed), an axis
## and origin in its parent's frame and a value (a source: a channel, a
## channel's component, an earlier joint, the time or a constant, then ops:
## add, mul, div, neg, wrap, pawl, table). A joint may carry pose-mode
## authority: a pin (a width-3 channel: its world position), an aim (a link
## frame toward another joint) or an orient (another joint's world basis).
## Pose mode renders; FK mode (fk = true) ignores the overrides, the chain rule
## from the values alone. A row this reader does not know (a type, source, op,
## symbol or body mode) refuses the bake, naming the joint: a new joint is data,
## a new operator is a reader change.

const FORMAT := "loam-motion/2"
const KINEMATICS_VERSION := 1
const TYPES := ["revolute", "prismatic", "fixed"]
const OPS := ["add", "mul", "div", "neg", "wrap", "pawl", "table"]
const MODES := ["frame", "rest", "world", "spin"]
const SYMBOLS := {"TAU": TAU, "-TAU": -TAU, "PI": PI, "-PI": -PI, "PI/2": PI/2}
const AXIS_TOL := 1e-6   # |axis| - 1: a joint axis is a unit vector (formlab.kinematics.AXIS_TOL)
enum {REVOLUTE, PRISMATIC, FIXED}
enum {SRC_CHANNEL, SRC_INDEX, SRC_JOINT, SRC_TIME, SRC_CONST}
enum {OP_ADD, OP_MUL, OP_DIV, OP_NEG, OP_WRAP, OP_PAWL, OP_TABLE}
enum {ARG_NUM, ARG_JOINT, ARG_CHANNEL}

var header: Dictionary
var times: PackedFloat64Array
var frames: PackedFloat32Array
var width: int = 0
var channels: Dictionary = {}   # "harp_arm0.tip" -> offset (float index into a row)
var arms: Dictionary = {}       # aid -> the header's per-arm record
var mechanisms: Dictionary = {}
var errors: PackedStringArray = []
var _pawl_table: PackedFloat32Array
var _pawl_pitch: float = 1.0
var _ride_angle: float = NAN    # pawl.ride_angle: the nose on a tooth's tip (NAN in an older bake)
# one row a time, cached: a frame asks for a dozen channels at the same t
var _row_t: float = NAN
var _row_i: int = 0
var _row_w: float = 0.0
# the joints table compiled (index = table order)
var _jid: PackedStringArray
var _index: Dictionary = {}       # id -> index
var _widths: Dictionary = {}      # channel name -> width
var _parent: PackedInt32Array     # -1: the world
var _type: PackedInt32Array       # REVOLUTE / PRISMATIC / FIXED
var _axis: PackedVector3Array
var _slot: PackedInt32Array       # a principal axis's component (a prismatic's slide), else -1
var _origin: PackedVector3Array   # a {"mean"} pivot resolved
var _ozero: PackedByteArray       # the origin is (0, 0, 0)
var _qhome: PackedFloat64Array
var _pin: PackedInt32Array        # a width-3 channel's offset, or -1
var _aim: PackedInt32Array        # the aimed-at joint, or -1
var _aim_ref: PackedVector3Array
var _aim_fb: PackedVector3Array
var _orient: PackedInt32Array     # the joint whose basis this one copies, or -1
var _src: PackedInt32Array        # SRC_*
var _src_arg: PackedFloat64Array  # a channel offset, a joint index or the constant
var _ops: Array = []              # per joint: [PackedFloat64Array [op, kind, value, kind, value], ...]
var _tables: Array = []           # a table op's [x, y, period (NAN: clamped)]
# one evaluation, cached on (t, fk): MotionRig.apply and joint_value read the same frames
var _ft: float = NAN
var _ffk: bool = false
var _P: PackedVector3Array
var _B: Array[Basis] = []
var _I: PackedByteArray
var _Q: PackedFloat64Array
var _S: PackedVector3Array


static func path_for(score_path: String, asset: String) -> String:
	return score_path.get_base_dir().path_join(asset+".motion.json")


## Each asset's score in this tree (formlab.bake.DEFAULT_SCORES, relative to the
## tree's root; ScoreDoc.default_path is clockwork's): --score=PATH when given,
## else the asset's own, "" for an asset with none (the caller asks for --score).
const DEFAULT_SCORES := {"clockwork": "render/chamber/score.json", "clockwork_expanded": "render/clockwork/score.json"}
static func default_score(asset: String) -> String:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--score="): return a.substr(8)
	if not DEFAULT_SCORES.has(asset): return ""
	return ProjectSettings.globalize_path("res://").path_join("../"+str(DEFAULT_SCORES[asset]))


## Loads the bake and refuses it when it was made from another score or
## another model: the header's fingerprints against the files on disk.
func load(json_path: String, score_path: String, manifest_path: String) -> bool:
	var fix := "run `python3 tools/bake_motion.py --asset=%s`" % json_path.get_file().get_slice(".", 0)
	if not FileAccess.file_exists(json_path):
		errors.append("no motion bake at %s — %s" % [json_path, fix]); return false
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(json_path))
	var fmt: String = str(parsed.get("format", "")) if typeof(parsed) == TYPE_DICTIONARY else ""
	if fmt != FORMAT:
		errors.append("%s is a %s bake; this harness reads loam-motion/2 (the joints table, per-arm head_l, declared segments) — %s"
				% [json_path, fmt if fmt != "" else "non-loam-motion", fix]); return false
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
	_pawl_table = PackedFloat32Array(header["pawl"]["table"])
	_pawl_pitch = float(header["pawl"]["pitch"])
	var ra = header["pawl"].get("ride_angle")
	_ride_angle = NAN if ra == null else float(ra)
	if not _compile_joints(): return false
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
## theta (formlab.rig.head_offset): the hinge is head_length above the origin
## and the face swings on it toward the arm's own rail. Zero for a rigid tool.
func head_offset(aid: String, theta: float) -> Vector3:
	if not hammer(aid): return Vector3.ZERO
	var l := head_length(aid)
	return Vector3(0, l*(1.0-cos(theta)), l*sin(theta)*flip_sign(aid))


## The arm's hinged head's pin above its tool frame (m): the header's per-arm
## head_l (rig.HAMMER's today; per arm from M5).
func head_length(aid: String) -> float: return float(arms[aid]["head_l"])


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


## Link frame: y along the link, x the pin axis (world X projected, or a
## joint's aim ref), z = x × y; the fallback when the axis lies along the link.
## Meshes are built at true length in this frame (formlab.linkage), never scaled.
static func link_basis(a: Vector3, b: Vector3, axis := Vector3.RIGHT, fallback := Vector3.FORWARD) -> Basis:
	var y := (b-a).normalized()
	var x := axis - y*y.dot(axis)
	if x.length_squared()<.000001: x=fallback
	x=x.normalized()
	return Basis(x,y,x.cross(y))



# ------------------------------------------------------------ the joints table
func _fail(msg: String) -> bool:
	errors.append(msg); return false


func _unknown(jid: String, what: String, name) -> String:
	return "joint %s uses %s '%s' this reader does not know (loam-motion/2 kinematics v%d) — update the harness" \
			% [jid, what, str(name), KINEMATICS_VERSION]


static func _is_num(x) -> bool:
	return typeof(x) == TYPE_FLOAT or typeof(x) == TYPE_INT


## A width-checked channel offset (width 0: any), or -1 with the error recorded.
func _channel(jid: String, name, width: int, role: String) -> int:
	var c := str(name)
	if not channels.has(c):
		_fail("joint %s's %s reads channel %s, which the bake lacks" % [jid, role, c]); return -1
	var w: int = _widths[c]
	var bad: bool = (w < 1) if width == 0 else (w != width)
	if bad:
		_fail("joint %s's %s reads channel %s of width %d, not %d" % [jid, role, c, w, width]); return -1
	return channels[c]


## An operand: [kind, value] (a number, a symbol, a ratio [num, den], an
## earlier joint, a width-1 channel), or [] with the error recorded.
func _operand(jid: String, x) -> Array:
	if _is_num(x): return [ARG_NUM, float(x)]
	if typeof(x) == TYPE_STRING:
		if not SYMBOLS.has(x): _fail(_unknown(jid, "symbol", x)); return []
		return [ARG_NUM, float(SYMBOLS[x])]
	if typeof(x) == TYPE_ARRAY and x.size() == 2 and _is_num(x[0]) and _is_num(x[1]):
		return [ARG_NUM, float(x[0])/float(x[1])]
	if typeof(x) == TYPE_DICTIONARY and x.size() == 1 and x.has("joint"):
		if not _index.has(x["joint"]):
			_fail("joint %s's operand %s is not an earlier joint of the table" % [jid, str(x["joint"])]); return []
		return [ARG_JOINT, float(_index[x["joint"]])]
	if typeof(x) == TYPE_DICTIONARY and x.size() == 1 and x.has("channel"):
		var off := _channel(jid, x["channel"], 1, "operand")
		if off < 0: return []
		return [ARG_CHANNEL, float(off)]
	_fail("joint %s has an operand %s this reader does not know (loam-motion/2 kinematics v%d) — update the harness"
			% [jid, str(x), KINEMATICS_VERSION]); return []


## The header's joints and bodies validated and compiled into packed arrays
## (formlab.kinematics.Compiled is the mirror): every refusal names the joint.
func _compile_joints() -> bool:
	var kin = header.get("kinematics", {})
	var ver = kin.get("version", 1) if typeof(kin) == TYPE_DICTIONARY else 1
	if not _is_num(ver) or float(ver) > KINEMATICS_VERSION:
		return _fail("the bake's kinematics version %s is newer than this reader's (loam-motion/2 kinematics v%d) — update the harness"
				% [str(ver), KINEMATICS_VERSION])
	_widths = {}
	for c in header["channels"]: _widths[c["name"]] = int(c["width"])
	var rows: Array = header.get("joints", [])
	var n := rows.size()
	_jid.resize(n); _parent.resize(n); _type.resize(n); _axis.resize(n); _slot.resize(n); _origin.resize(n)
	_ozero.resize(n); _qhome.resize(n); _pin.resize(n); _aim.resize(n); _aim_ref.resize(n); _aim_fb.resize(n)
	_orient.resize(n); _src.resize(n); _src_arg.resize(n)
	_ops = []; _ops.resize(n); _tables = []; _index = {}
	var aims: Array = []
	for i in n:
		var jt: Dictionary = rows[i]
		var jid := str(jt.get("id", ""))
		if jid == "": return _fail("joints row %d has no id" % i)
		if _index.has(jid): return _fail("joint %s is listed twice" % jid)
		_jid[i] = jid
		var typ = jt.get("type")
		var ti := TYPES.find(typ)
		if ti < 0: return _fail(_unknown(jid, "type", typ))
		_type[i] = ti
		var par = jt.get("parent")
		if par == null: _parent[i] = -1
		elif _index.has(par): _parent[i] = _index[par]
		else: return _fail("joint %s's parent %s is not an earlier joint of the table" % [jid, str(par)])
		var ax = jt.get("axis")
		_axis[i] = Vector3.ZERO; _slot[i] = -1
		if ti != FIXED:
			if typeof(ax) != TYPE_ARRAY or ax.size() != 3: return _fail("joint %s (%s) has no axis" % [jid, typ])
			_axis[i] = Vector3(float(ax[0]), float(ax[1]), float(ax[2]))
			var al := sqrt(float(ax[0])*float(ax[0])+float(ax[1])*float(ax[1])+float(ax[2])*float(ax[2]))
			if not absf(al-1.0) <= AXIS_TOL:   # Basis(axis, angle) takes a unit axis (another: an error and identity)
				return _fail("joint %s has a non-unit axis %s (|axis| %.9f): an axis is a unit vector in the parent frame"
						% [jid, str(ax), al])
			var nz: Array = []
			for k in 3:
				if float(ax[k]) != 0.0: nz.append(k)
			if nz.size() == 1 and float(ax[nz[0]]) == 1.0: _slot[i] = nz[0]
		var o = jt.get("origin", [0.0, 0.0, 0.0])
		if typeof(o) == TYPE_DICTIONARY:
			if o.size() != 1 or not o.has("mean"): return _fail("joint %s has an origin %s this reader does not know" % [jid, str(o.keys())])
			if _parent[i] >= 0: return _fail("joint %s has a {\"mean\"} origin but is not a root joint" % jid)
			# performance.gd's M2 pivot: accumulated and divided as Vector3s
			var ends: Array = o["mean"]
			var pivot := Vector3.ZERO
			for e in ends: pivot += Vector3(float(e[0]), float(e[1]), float(e[2]))
			if ends.size() > 0: pivot /= float(ends.size())
			_origin[i] = pivot; _ozero[i] = 0
		else:
			if typeof(o) != TYPE_ARRAY or o.size() != 3: return _fail("joint %s has no origin" % jid)
			_origin[i] = Vector3(float(o[0]), float(o[1]), float(o[2]))
			_ozero[i] = 1 if float(o[0]) == 0.0 and float(o[1]) == 0.0 and float(o[2]) == 0.0 else 0
		_qhome[i] = float(jt.get("q_home", 0.0))
		_pin[i] = -1; _aim[i] = -1; _orient[i] = -1
		_aim_ref[i] = Vector3.RIGHT; _aim_fb[i] = Vector3.FORWARD
		var pose = jt.get("pose")
		if typeof(pose) == TYPE_DICTIONARY:
			if pose.get("pin") != null:
				var off := _channel(jid, pose["pin"], 3, "pin")
				if off < 0: return false
				_pin[i] = off
			if pose.get("orient") != null:
				if not _index.has(pose["orient"]):
					return _fail("joint %s's orient %s is not an earlier joint of the table" % [jid, str(pose["orient"])])
				_orient[i] = _index[pose["orient"]]
			var aim = pose.get("aim")
			if typeof(aim) == TYPE_DICTIONARY:
				aims.append([i, str(aim.get("joint", ""))])
				var r: Array = aim.get("ref", [1.0, 0.0, 0.0]); var f: Array = aim.get("fallback", [0.0, 0.0, -1.0])
				_aim_ref[i] = Vector3(float(r[0]), float(r[1]), float(r[2]))
				_aim_fb[i] = Vector3(float(f[0]), float(f[1]), float(f[2]))
		var ops: Array = []
		var val = jt.get("value")
		if val == null:
			_src[i] = SRC_CONST; _src_arg[i] = 0.0
		else:
			var src: Dictionary = val.get("src", {})
			var keys: Array = src.keys(); keys.sort()
			if src.has("channel") and (keys == ["channel"] or keys == ["channel", "index"]):
				if src.has("index"):
					var off := _channel(jid, src["channel"], 0, "source")
					if off < 0: return false
					var k := int(src["index"])
					if k < 0 or k >= int(_widths[str(src["channel"])]):
						return _fail("joint %s's source reads component %d of %s, which has width %d"
								% [jid, k, str(src["channel"]), int(_widths[str(src["channel"])])])
					_src[i] = SRC_INDEX; _src_arg[i] = off+k
				else:
					var off := _channel(jid, src["channel"], 1, "source")
					if off < 0: return false
					_src[i] = SRC_CHANNEL; _src_arg[i] = off
			elif keys == ["joint"]:
				if not _index.has(src["joint"]):
					return _fail("joint %s's source %s is not an earlier joint of the table" % [jid, str(src["joint"])])
				_src[i] = SRC_JOINT; _src_arg[i] = _index[src["joint"]]
			elif keys == ["time"]:
				_src[i] = SRC_TIME; _src_arg[i] = 0.0
			elif keys == ["const"] and _is_num(src["const"]):
				_src[i] = SRC_CONST; _src_arg[i] = float(src["const"])
			else:
				return _fail(_unknown(jid, "source", "/".join(PackedStringArray(keys)) if keys.size() > 0 else "none"))
			for op in val.get("ops", []):
				if typeof(op) != TYPE_ARRAY or op.is_empty() or not OPS.has(op[0]):
					return _fail(_unknown(jid, "op", op[0] if typeof(op) == TYPE_ARRAY and not op.is_empty() else op))
				var code := OPS.find(op[0])
				var rec := PackedFloat64Array([code, 0.0, 0.0, 0.0, 0.0])
				if code == OP_ADD or code == OP_MUL or code == OP_DIV:
					if op.size() != 2: return _fail("joint %s's op %s takes one operand" % [jid, str(op)])
					var a := _operand(jid, op[1])
					if a.is_empty(): return false
					rec[1] = a[0]; rec[2] = a[1]
				elif code == OP_WRAP:
					if op.size() != 3: return _fail("joint %s's op %s takes two operands" % [jid, str(op)])
					var a := _operand(jid, op[1])
					if a.is_empty(): return false
					var b := _operand(jid, op[2])
					if b.is_empty(): return false
					rec[1] = a[0]; rec[2] = a[1]; rec[3] = b[0]; rec[4] = b[1]
				elif code == OP_PAWL:
					if op.size() != 2: return _fail("joint %s's op %s takes one channel or null" % [jid, str(op)])
					rec[2] = -1.0
					if op[1] != null:
						var off := _channel(jid, op[1], 1, "pawl ride")
						if off < 0: return false
						rec[2] = off
				elif code == OP_TABLE:
					var tb = op[1] if op.size() == 2 and typeof(op[1]) == TYPE_DICTIONARY else {}
					var x := PackedFloat64Array(tb.get("x", [])); var y := PackedFloat64Array(tb.get("y", []))
					var per = tb.get("period")
					var ok := x.size() >= 2 and x.size() == y.size() and (per == null or (_is_num(per) and float(per) > 0.0))
					for k in range(1, x.size()):
						if not x[k] > x[k-1]: ok = false
					if not ok:
						return _fail("joint %s's table op needs increasing x and y of one length (>= 2) and a positive period or null" % jid)
					rec[2] = _tables.size(); _tables.append([x, y, NAN if per == null else float(per)])
				ops.append(rec)
		_ops[i] = ops
		_index[jid] = i
	for a in aims:
		var i: int = a[0]; var tgt: String = a[1]
		if not _index.has(tgt): return _fail("joint %s aims at %s, which the table lacks" % [_jid[i], tgt])
		var ti: int = _index[tgt]
		if ti >= i and _pin[ti] < 0:
			return _fail("joint %s aims at %s, which is neither pinned nor earlier in the table" % [_jid[i], tgt])
		_aim[i] = ti
	for b in header.get("bodies", []):
		var jid = b.get("joint")
		if not _index.has(jid):
			return _fail("body %s is bound to joint %s, which the table lacks" % [str(b.get("node")), str(jid)])
		if not MODES.has(b.get("mode")): return _fail(_unknown(str(jid), "mode", b.get("mode")))
		if b["mode"] == "world" and _parent[_index[jid]] >= 0:
			return _fail("joint %s has a world body (%s) but is not a root joint" % [str(jid), str(b.get("node"))])
	_P.resize(n); _I.resize(n); _Q.resize(n); _S.resize(n); _B.resize(n); _B.fill(Basis.IDENTITY)
	_ft = NAN
	return true


func _arg(rec: PackedFloat64Array, k: int, t: float) -> float:
	var kind := int(rec[k])
	if kind == ARG_NUM: return rec[k+1]
	if kind == ARG_JOINT: return _Q[int(rec[k+1])]
	return _at(int(rec[k+1]), t)


func _table(ti: int, q: float) -> float:
	var tb: Array = _tables[ti]
	var x: PackedFloat64Array = tb[0]; var y: PackedFloat64Array = tb[1]; var per: float = tb[2]
	if not is_nan(per): q = x[0]+fposmod(q-x[0], per)
	else: q = clampf(q, x[0], x[x.size()-1])
	var k := clampi(x.bsearch(q, true), 1, x.size()-1)
	var w := (q-x[k-1])/(x[k]-x[k-1])
	return y[k-1]+(y[k]-y[k-1])*w


## Every joint's frame at t, in table order (formlab/bake.py's evaluator; the
## mirror is formlab.kinematics.evaluate): q a double from its source and ops; P,
## B (and whether B is the world's identity) from the parent's, or from the
## pose-mode overrides unless fk. Cached on (t, fk); read with frame_p / frame_b
## / frame_ident / frame_slide / frame_q.
func frames_at(t: float, fk := false) -> void:
	if t == _ft and fk == _ffk: return
	_ft = t; _ffk = fk
	for i in _jid.size():
		var q: float
		var sk := _src[i]
		if sk == SRC_CHANNEL: q = _at(int(_src_arg[i]), t)
		elif sk == SRC_INDEX: q = Vector3(_at(int(_src_arg[i]), t), 0, 0).x   # a component as the Vector3 holds it
		elif sk == SRC_JOINT: q = _Q[int(_src_arg[i])]
		elif sk == SRC_TIME: q = t
		else: q = _src_arg[i]
		for rec in _ops[i]:
			var code := int(rec[0])
			if code == OP_ADD: q = q+_arg(rec, 1, t)
			elif code == OP_MUL: q = q*_arg(rec, 1, t)
			elif code == OP_DIV: q = q/_arg(rec, 1, t)
			elif code == OP_NEG: q = -q
			elif code == OP_WRAP: q = wrapf(q, _arg(rec, 1, t), _arg(rec, 3, t))
			elif code == OP_PAWL: q = pawl_angle(q, _at(int(rec[2]), t) if rec[2] >= 0.0 else 0.0)
			else: q = _table(int(rec[2]), q)
		_Q[i] = q
		var qq := q-_qhome[i]
		var par := _parent[i]; var typ := _type[i]
		var Pp := Vector3.ZERO; var Bp := Basis.IDENTITY; var Ip := true
		if par >= 0: Pp = _P[par]; Bp = _B[par]; Ip = _I[par] == 1
		var S := Vector3.ZERO
		if typ == PRISMATIC:
			var sl := _slot[i]
			if sl == 0: S = Vector3(qq, 0, 0)
			elif sl == 1: S = Vector3(0, qq, 0)
			elif sl == 2: S = Vector3(0, 0, qq)
			else: S = _axis[i]*qq
		_S[i] = S
		var O := _origin[i]
		var P: Vector3
		if not fk and _pin[i] >= 0:
			var o := _pin[i]; P = Vector3(_at(o, t), _at(o+1, t), _at(o+2, t))
		elif par < 0: P = O+S if typ == PRISMATIC else O
		elif typ != PRISMATIC and _ozero[i] == 1: P = Pp
		elif Ip: P = Pp+(O+S) if typ == PRISMATIC else Pp+O
		else: P = Pp+Bp*(O+S) if typ == PRISMATIC else Pp+Bp*O
		var B: Basis; var I: bool
		if not fk and _orient[i] >= 0:
			B = _B[_orient[i]]; I = _I[_orient[i]] == 1
		elif not fk and _aim[i] >= 0:
			var ti := _aim[i]; var tgt: Vector3
			if _pin[ti] >= 0:
				var o := _pin[ti]; tgt = Vector3(_at(o, t), _at(o+1, t), _at(o+2, t))
			else: tgt = _P[ti]
			B = link_basis(P, tgt, _aim_ref[i] if Ip else Bp*_aim_ref[i], _aim_fb[i]); I = false
		elif typ == REVOLUTE:
			var R := Basis(_axis[i], qq)
			B = R if Ip else Bp*R; I = false
		else:
			B = Bp; I = Ip
		_P[i] = P; _B[i] = B; _I[i] = 1 if I else 0


func has_joint(id: String) -> bool: return _index.has(id)
func joint_ids() -> PackedStringArray: return _jid
func joint_index(id: String) -> int: return int(_index.get(id, -1))
func joint_count() -> int: return _jid.size()
func joint_type(i: int) -> int: return _type[i]
func frame_p(i: int) -> Vector3: return _P[i]
func frame_b(i: int) -> Basis: return _B[i]
func frame_ident(i: int) -> bool: return _I[i] == 1
func frame_slide(i: int) -> Vector3: return _S[i]
func frame_q(i: int) -> float: return _Q[i]
## The header's body rows: {joint, node, mode, optional, mass, com, inertia}.
func bodies() -> Array: return header.get("bodies", [])
## The arm's declared structure (the header's arms[aid].declared: segments with
## null for an unbounded t0 / t1, knots, rings, prep; formlab.bake.Bake.declared).
func declared(aid: String) -> Dictionary: return arms[aid].get("declared", {})


## A joint's value at t (pose mode).
func joint_value(id: String, t: float) -> float:
	frames_at(t); return _Q[_index[id]]


## A joint's world frame at t.
func joint_frame(id: String, t: float, fk := false) -> Transform3D:
	frames_at(t, fk); var i: int = _index[id]
	return Transform3D(_B[i], _P[i])


## A joint's world position at t (pose mode). A pinned joint's is its channel
## read directly, the same call vec / pose / tip_at make: no tree walk, and the
## frames cache is left as it was.
func joint_origin(id: String, t: float) -> Vector3:
	var i: int = _index[id]
	if _pin[i] >= 0:
		var o := _pin[i]; return Vector3(_at(o, t), _at(o+1, t), _at(o+2, t))
	frames_at(t); return _P[i]
