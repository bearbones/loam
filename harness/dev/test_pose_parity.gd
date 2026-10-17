extends SceneTree
## Pose parity (PLAYERS M3, ruler 26): the joints table poses every moving part
## exactly as the M2 harness did. performance.tscn is instantiated as
## test_performance.gd does (playing=false); at every t below, every bound node
## is reset to its home and posed three ways, and the transforms are compared
## with == (bitwise):
##   - scene.evaluate(t), the shipped path (MotionRig.apply since M3);
##   - scene.rig.apply(t), the joints table alone;
##   - oracle_m2(scene, t), the M2 code: performance.gd:567-659 of the M2 tree
##     verbatim between the markers, with only three substitutions (members
##     prefixed `s.`; s.motion.head_l -> s.motion.head_length(aid), the same
##     double 0.12; flywheel_angle(t) -> its M2 body). The gate re-derives the
##     block from the M2 tree and diffs it.
## Times: every capture time start + k*speed/fps of the gate moments (m2, m7,
## m2q, m5 and, --expanded, m10 at players_reel.sh's blow start), a 30 Hz sweep
## over [-1, total_s + 1], every bake row within 5 ms of a contact, every row in
## [13.5, 14.4] and [54.29, 56.79] (and the m10 window).
## The oracle poses the M2 nodes: the hand lookups (parts, screw_nodes,
## wheel_home, stand_nodes, the shudder bars and frames), every one of which
## must be bound, and each is held to it. A node bound only by the table (a
## body a later milestone adds as data: a crank, a finger, a pendulum) has no
## M2 pose: it is held to shipped == table alone and reported as INFO, so a
## body added as data needs no change here.
## Also: the camera's and the director's reads through joint_origin /
## joint_value are bitwise the M2 reads; and the cost of apply and of the
## oracle a frame (warned above 2 ms on the chamber, failed above 8 ms).
## Retired in M5: rewritten in the same commit as the wrist and hammer change,
## never deleted quietly.
##   godot --headless --path harness -s dev/test_pose_parity.gd [-- --expanded]
const PerformanceScript := preload("res://performance.gd")
const MotionRigScript := preload("res://motion_rig.gd")   # by path: no class-cache dependency
const WARN_US := 2000.0
const FAIL_US := 8000.0


func _init() -> void:
	call_deferred("run")


func oracle_m2(s: PerformanceScript, t: float) -> void:
# --- M2 oracle begin
	for aid in s.parts:
		var pose := s.motion.pose(aid,t)
		var p: Dictionary=s.parts[aid]
		var cfg: Dictionary=s.layout["arms"][aid]
		var o1 := MotionBake.v(cfg["o1"]); var o2 := MotionBake.v(cfg["o2"])
		var root: Vector3=pose["root"]; var elbow: Vector3=pose["elbow"]; var wrist: Vector3=pose["wrist"]
		# Crossheads and pins keep a fixed orientation: that is what the parallelograms guarantee.
		p["carriage"].position=root; p["shoulder"].position=root
		p["elbowhead"].position=elbow; p["elbow"].position=elbow
		p["wristhead"].position=wrist; p["wrist"].position=wrist
		p["tool"].position=pose["tip"]; p["shank"].position=pose["tip"]
		# A hinged hammer's head turns on the flange's pin, HEAD_L above the tool
		# frame's origin. The head's mesh is built at the blow (angle 0, the felt
		# face straight down), and the flip is one rotation about the pin axis:
		# -angle*sign, the same rotation formlab.rig.head_offset applies to
		# the felt face — which is why the blow lands exactly on the scored point.
		if p.has("head"):
			p["head"].position=pose["tip"]+Vector3(0,s.motion.head_length(aid),0)
			p["head"].basis=Basis(Vector3.RIGHT,-float(pose["head"])*s.motion.flip_sign(aid))*s.head_home[aid]
		var upper := MotionBake.link_basis(root,elbow)
		var lower := MotionBake.link_basis(elbow,wrist)
		p["upper"].transform=Transform3D(upper,root)
		p["upper2"].transform=Transform3D(upper,root+o1)
		p["lower"].transform=Transform3D(lower,elbow)
		p["lower2"].transform=Transform3D(lower,elbow+o2)
		# The pinion rides its axle on the carriage and rolls on the rack
		# (formlab.clearance.PINION / MOUNTS, formlab.gantry.rack): in front of
		# or behind the carriage it is upright under a rack above it; above or
		# below the carriage it lies flat against a rack behind the rail. Either
		# way +x travel turns it by x / pitch radius (.12) about its axle.
		# The spin composes on the imported basis: setting one Euler component of
		# a basis that is a quarter turn about X hits gimbal lock and tilted the disc.
		var mount: String=str(cfg.get("pinion","back"))
		var flat := mount=="up" or mount=="down"
		# A servo arm's leadscrew turns instead: a right-hand thread, so +x travel
		# of the nut is a negative turn about +x, 2π per pitch (formlab.gantry.
		# screw_geometry); the shaft's mesh is in world space, so the spin is
		# taken about the axis line through (0, y, z).
		if s.screw_nodes.has(aid):
			var sc: Dictionary=cfg["screw"]
			var c := Vector3(0,float(sc["y"]),float(sc["z"]))
			var turn := Basis(Vector3.RIGHT,wrapf(-TAU*root.x/float(sc["pitch"]),-PI,PI))  # wrapped in double first: a Basis takes a 32-bit angle, and a screw 4 m down its rail has turned ~3000 rad
			s.screw_nodes[aid].transform=Transform3D(turn,c-turn*c)*s.screw_home[aid]
			continue
		p["gear"].position=root+(Vector3(0,(.17 if mount=="up" else -.17),-.10) if flat else Vector3(0,0,(.195 if mount=="front" else -.195)))
		# A pinion with a pawl is spun with a phase (formlab.pawl.dip_offset) that
		# seats the roller in a dip when the arm parks at its home.
		var phase: float=float(cfg["pawl"].get("phase",0.0)) if cfg.has("pawl") else 0.0
		p["gear"].basis=Basis(Vector3.UP if flat else Vector3(0,0,1),(root.x+phase)/.12)*s.gear_home[aid]
		# The roller detent pawl (formlab.pawl) hangs on its pivot off the carriage
		# and turns about z so its roller rides the spun teeth: lifted (positive
		# angle) on a tip, dropped into the gap between. The mirror of pawl.angle.
		# The roller sits on the pawl's axle and rolls on the tips: ROLLER_SPIN
		# radians a metre of rail, the other way from the disc.
		# Above PAWL_RIDE teeth a second the pawl rides the tips: the bake's .ride
		# channel leans the table's angle toward pawl.ride_angle (formlab.bake.Bake.pawl).
		if p.has("pawl"):
			var swing := Basis(Vector3(0,0,1),-s.motion.pawl_angle(root.x+phase,s.motion.ride(aid,t)))
			p["pawl"].position=root+MotionBake.v(cfg["pawl"]["pivot"])
			p["pawl"].basis=swing*s.pawl_home[aid]
			p["roller"].position=p["pawl"].position+swing*MotionBake.v(cfg["pawl"]["nose"])
			p["roller"].basis=swing*Basis(Vector3(0,0,1),float(cfg["pawl"].get("roller_spin",0.0))*root.x)*s.roller_home[aid]
	# The blow shakes the assembly, not only the arm: the stand thumps, the rail
	# sags under the carriage and rings, and the gantry sways about its plinths.
	# All three come off the same recoil bus the arm's own recoil does and are
	# exactly zero at the blow they answer (formlab.rig.Rig._shudder, baked).
	for mid in s.stand_nodes:
		var st: Dictionary=s.stand_nodes[mid]
		var sh: Transform3D=st["home"]
		st["node"].transform=Transform3D(sh.basis,sh.origin+Vector3(0,s.motion.stand_thump(mid,t),0))
	for aid in s.shudder_nodes:
		var sh: Dictionary=s.shudder_nodes[aid]
		# The guide bars are rigid meshes, so they carry the sag at mid-span; the
		# deflection's SHAPE lives in the carriage, which follows the sag at its
		# own x (formlab.rig.Rig.pose), so links and pawl move with the bar.
		var sag := s.motion.rail_sag(aid,t)
		for b in sh["bars"]:
			var bh: Transform3D=b["home"]
			b["node"].transform=Transform3D(bh.basis,bh.origin+Vector3(0,sag,0))
		# A sway is a tilt ACROSS the rail (about world X, through both plinth
		# feet): the braces stiffen the gantry along the rail, and a rotation on
		# that axis gives no mast a lever arm down the span.
		var tilt := Basis(Vector3.RIGHT,s.motion.mast_sway(aid,t))
		var pivot: Vector3=sh["pivot"]
		for f in sh["frame"]: f["node"].transform=Transform3D(tilt,pivot-tilt*pivot)*f["home"]
	# The flywheel turns once a bar; the belt pulley turns with it, faster by the
	# pulleys' radii, the same way round (an open belt).
	var spin: float=-TAU*t*float(s.score.doc.get("bpm",84.0))/240.0
	for node in s.wheel_home:
		var k: float=1.0
		if node.name=="Chamber belt pulley" and s.layout.has("flywheel"):
			var f: Dictionary=s.layout["flywheel"]; k=float(f["wraps"][0][1])/float(f["wraps"][1][1]) if f.has("wraps") else float(f["cyls"]["drive pulley"][2])/float(f["cyls"]["belt pulley"][2])
		node.basis=Basis(Vector3(0,0,1),spin*k)*s.wheel_home[node]
# --- M2 oracle end


func _reset(nodes: Array, rig: MotionRigScript) -> void:
	for n in nodes: n.transform = rig.home(n)


func _snap(nodes: Array) -> Array:
	var out: Array = []
	for n in nodes: out.append(n.transform)
	return out


func _rows_in(motion: MotionBake, lo: float, hi: float, into: Array) -> void:
	var i := motion.times.bsearch(lo, true)
	while i < motion.times.size() and motion.times[i] <= hi:
		into.append(motion.times[i]); i += 1


func run() -> void:
	var expanded := OS.get_cmdline_user_args().has("--expanded")
	var scene: PerformanceScript = load("res://performance.tscn").instantiate()
	root.add_child(scene)
	scene.playing = false
	var failures: Array = []
	if scene.model == null or scene.rig == null:
		print("POSE PARITY: FAIL (the scene did not load: ", scene.motion.errors, ")"); quit(1); return
	var motion: MotionBake = scene.motion
	var rig: MotionRigScript = scene.rig
	var sd: ScoreDoc = scene.score
	# --- the times
	var T: Array = []
	var moments: Array = [["13.50", 0.9, 1.0], ["54.29", 2.5, 1.0], ["13.50", 0.9, 0.25], ["39.5", 1.0, 1.0]]
	if expanded:
		var first := INF
		for e in sd.events:
			if str(e.get("actuator", "")) == "blocks_arm0": first = minf(first, float(e["t"]))
		if is_finite(first):
			moments.append(["%.3f" % (first-1.0), 1.6, 1.0])
			_rows_in(motion, float("%.3f" % (first-1.0)), float("%.3f" % (first-1.0))+1.6, T)
		else: failures.append("no blocks_arm0 event in the expanded score")
	for m in moments:
		var start := float(m[0]); var speed: float = maxf(float(m[2]), .001); var fps := 30.0
		var count := roundi(float(m[1])*fps/speed)
		T.append(start)                                   # the warmup frames
		for k in count: T.append(start+k*speed/fps)       # performance.gd's capture time
	for k in range(int((sd.total_s+2.0)*30.0)+1): T.append(-1.0+k/30.0)
	for e in sd.events:
		for ts in ScoreDoc.string_times(e): _rows_in(motion, float(ts)-.005, float(ts)+.005, T)
	_rows_in(motion, 13.5, 14.4, T); _rows_in(motion, 54.29, 56.79, T)
	# --- the node sets
	var nodes: Array = rig.bound_nodes()
	var bound := {}
	for n in nodes: bound[n] = true
	var hand := {}
	for aid in scene.parts:
		for part in scene.parts[aid]: hand[scene.parts[aid][part]] = true
	for aid in scene.screw_nodes: hand[scene.screw_nodes[aid]] = true
	for n in scene.wheel_home: hand[n] = true
	for mid in scene.stand_nodes: hand[scene.stand_nodes[mid]["node"]] = true
	for aid in scene.shudder_nodes:
		for b in scene.shudder_nodes[aid]["bars"]: hand[b["node"]] = true
		for f in scene.shudder_nodes[aid]["frame"]: hand[f["node"]] = true
	var unbound: Array = []
	for n in hand:
		if not bound.has(n): unbound.append(str(n.name))
	if not unbound.is_empty():
		failures.append("%d of the %d hand-lookup nodes are not bound by the joints table, first %s" % [unbound.size(), hand.size(), str(unbound.slice(0, 5))])
	var m2 := PackedByteArray(); m2.resize(nodes.size())   # 1: the oracle poses it
	var extra: Array = []
	for k in nodes.size():
		m2[k] = 1 if hand.has(nodes[k]) else 0
		if m2[k] == 0: extra.append(str(nodes[k].name))
	if not extra.is_empty():
		print("INFO %d nodes bound by the table alone (no M2 pose: held to shipped == table): %s" % [extra.size(), str(extra.slice(0, 8))])
	# --- the poses
	var bad: Array = []; var nbad := 0; var nshipped := 0; var ntable := 0; var transforms := 0; var xtransforms := 0
	var us_apply := 0; var us_oracle := 0
	for t in T:
		_reset(nodes, rig); scene.evaluate(t)
		var a := _snap(nodes)
		_reset(nodes, rig); motion.frames_at(t, true)    # evict the cached pose frames: apply pays for its own
		var u0 := Time.get_ticks_usec(); rig.apply(t); us_apply += Time.get_ticks_usec()-u0
		var g := _snap(nodes)
		_reset(nodes, rig)
		u0 = Time.get_ticks_usec(); oracle_m2(scene, t); us_oracle += Time.get_ticks_usec()-u0
		var o := _snap(nodes)
		for k in nodes.size():
			if m2[k] == 0:                                # the table's alone: shipped == table
				xtransforms += 1
				if a[k] != g[k]:
					nbad += 1; nshipped += 1
					if bad.size() < 10:
						bad.append("%s at t=%.9f (table only): shipped %s, table %s" % [nodes[k].name, t, str(a[k]), str(g[k])])
				continue
			transforms += 1
			if a[k] != o[k] or g[k] != o[k]:
				nbad += 1
				if a[k] != o[k]: nshipped += 1
				if g[k] != o[k]: ntable += 1
				if bad.size() < 10:
					bad.append("%s at t=%.9f: oracle %s, shipped %s, table %s" % [nodes[k].name, t, str(o[k]), str(a[k]), str(g[k])])
	_reset(nodes, rig)
	if nbad > 0:
		failures.append("%d node transforms differ (%d shipped, %d table) of %d" % [nbad, nshipped, ntable, transforms+xtransforms])
		for b in bad: failures.append("  "+b)
	# --- the camera's and the director's reads (bitwise)
	var reads := 0; var off_reads: Array = []
	var bpm := float(sd.doc.get("bpm", 84.0))
	for t in T:
		for aid in motion.arms:
			reads += 3
			if motion.joint_origin(aid+"/tool", t) != motion.tip_at(aid, t): off_reads.append("%s/tool at %.6f" % [aid, t])
			var r := motion.joint_origin(aid+"/carriage", t)
			if r != motion.vec(aid+".root", t) or r != motion.pose(aid, t)["root"]: off_reads.append("%s/carriage at %.6f" % [aid, t])
			if motion.has_joint(aid+"/head"):
				reads += 1
				if motion.joint_origin(aid+"/head", t) != motion.tip_at(aid, t)+Vector3(0, motion.head_length(aid), 0):
					off_reads.append("%s/head at %.6f" % [aid, t])
		reads += 2
		if motion.joint_value("chamber/flywheel", t) != -TAU*t*bpm/240.0: off_reads.append("chamber/flywheel at %.6f" % t)
		if scene.flywheel_angle(t) != -TAU*t*float(sd.doc.get("bpm",84.0))/240.0: off_reads.append("flywheel_angle at %.6f" % t)
	if not off_reads.is_empty():
		failures.append("%d of %d camera / director reads differ, first %s" % [off_reads.size(), reads, str(off_reads.slice(0, 5))])
	# --- the cost
	var a_us := float(us_apply)/T.size(); var o_us := float(us_oracle)/T.size()
	if a_us > FAIL_US: failures.append("rig.apply costs %.0f us a frame (fail above %.0f)" % [a_us, FAIL_US])
	elif a_us > WARN_US and not expanded: print("WARN rig.apply costs %.0f us a frame (above %.0f)" % [a_us, WARN_US])
	print("POSE PARITY: %s, %d nodes bound (%d the M2 oracle poses, %d the table alone), %d times, %d camera / director reads"
			% ["expanded" if expanded else "chamber", nodes.size(), nodes.size()-extra.size(), extra.size(), T.size(), reads])
	if xtransforms > 0: print("INFO %d table-only node transforms, shipped == table" % xtransforms)
	if failures.is_empty():
		print("POSE PARITY: PASS (%d times, %d node transforms, 0 mismatches; apply %.0f us, oracle %.0f us)" % [T.size(), transforms, a_us, o_us])
		quit(0)
	else:
		for f in failures: print("  FAIL ", f)
		print("POSE PARITY: FAIL (%d)" % failures.size())
		quit(1)
