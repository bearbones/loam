extends SceneTree
## Print the motion bake as the harness reads it (MotionBake), so
## tools/test_bake.py can hold this reader to formlab.bake.Bake: every arm's
## pose at 97 Hz — off the bake's 240 Hz grid, so the interpolation is what is
## measured — ("POSE aid t rx ry rz ex ey ez wx wy wz tx ty tz fx fy fz head", the felt
## face derived as the harness derives it),
## the assembly's shudder ("SHUD aid t stand sag sway"), a stepped arm's pawl
## ride and its pawl as posed ("RIDE aid t ride angle": MotionBake.ride / .pawl),
## the clicks ("CLICK aid t teeth pawl step"), the pawl's angle over the rail
## ("PAWL x angle") and leaned by a ride ("PAWLR x ride angle").
## The /2 joints table (held to formlab.kinematics.evaluate): the load's time
## ("LOADMS ms"), each arm's head_length ("HEADL aid l"), every joint's frame
## at 13 Hz, off the grid ("JOINT id t q px py pz bxx bxy bxz byx byy byz bzx
## bzy bzz": the basis as its columns x, y, z) and in FK mode at every 50th row
## ("JOINTFK ..."), and the declared structure ("SEG aid t0 t1 event tag law",
## the law last since it may hold a space; "KNOT aid t kind event"; "RING aid
## name channel amp f tau"; an unbounded t0 / t1 prints null).
## --score=PATH --asset=NAME pick the pair (the score defaults to the asset's
## own, MotionBake.default_score); a stale or refused bake prints its
## error. --joints_only prints only LOADMS and the JOINT lines.
func _init() -> void:
	var asset := "clockwork"
	var joints_only := false
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--asset="): asset=a.substr(8)
		if a == "--joints_only": joints_only = true
	var score_path := MotionBake.default_score(asset)
	if score_path == "":
		print("ERROR no default score for asset %s (known: %s): pass --score=PATH" % [asset, str(MotionBake.DEFAULT_SCORES.keys())]); quit(1); return
	var sd := ScoreDoc.new()
	if not sd.load(score_path):
		print(sd.errors); quit(1); return
	var bake := MotionBake.new()
	var t_load := Time.get_ticks_usec()
	if not bake.load(MotionBake.path_for(sd.path,asset),sd.path,"res://assets/"+asset+".json"):
		print("ERROR ",bake.errors); quit(1); return
	print("LOADMS %.3f" % ((Time.get_ticks_usec()-t_load)/1000.0))
	if joints_only:
		_joints(bake, sd, false); quit(0); return
	for aid in bake.arms:
		for frame in range(-97,int(sd.total_s*97)+1):
			var t := frame/97.0
			var p := bake.pose(aid,t)
			var line := "POSE %s %.9f" % [aid,t]
			for k in ["root","elbow","wrist","tip","felt"]:
				var q: Vector3=p[k]; line+=" %.9f %.9f %.9f" % [q.x,q.y,q.z]
			print(line+" %.12f" % p["head"])
			print("SHUD %s %.9f %.12f %.12f %.12f" % [aid,t,bake.stand_thump(bake.mech_of(aid),t),bake.rail_sag(aid,t),bake.mast_sway(aid,t)])
			if bake.channels.has(aid+".ride"):
				print("RIDE %s %.9f %.12f %.12f" % [aid,t,bake.ride(aid,t),bake.pawl(aid,t)])
		for c in bake.click_times(aid):
			print("CLICK %s %.9f %.6f %d %d" % [aid,float(c["t"]),float(c["teeth"]),int(c["pawl"]),int(c["step"])])
	for k in range(4001):
		var x := -.2+k*.0001
		print("PAWL %.9f %.12f" % [x,bake.pawl_angle(x)])
		if k%4==0:
			for r in [.25,.5,.9,1.0]: print("PAWLR %.9f %.3f %.12f" % [x,r,bake.pawl_angle(x,r)])
	_joints(bake, sd, true)
	quit(0)


func _frame_line(kind: String, bake: MotionBake, i: int, id: String, t: float) -> String:
	var p := bake.frame_p(i); var b := bake.frame_b(i)
	return "%s %s %.9f %.12f %.9f %.9f %.9f %.9f %.9f %.9f %.9f %.9f %.9f %.9f %.9f %.9f" % [kind, id, t, bake.frame_q(i),
		p.x, p.y, p.z, b.x.x, b.x.y, b.x.z, b.y.x, b.y.y, b.y.z, b.z.x, b.z.y, b.z.z]


static func _t(x) -> String: return "null" if x == null else "%.9f" % float(x)


func _joints(bake: MotionBake, sd: ScoreDoc, all: bool) -> void:
	var ids := bake.joint_ids()
	for f in range(-13, int(sd.total_s*13)+1):
		var t := f/13.0
		bake.frames_at(t)
		var lines := PackedStringArray()
		for i in ids.size(): lines.append(_frame_line("JOINT", bake, i, ids[i], t))
		print("\n".join(lines))
	if not all: return
	for r in range(0, bake.times.size(), 50):
		var t: float = bake.times[r]
		bake.frames_at(t, true)
		var lines := PackedStringArray()
		for i in ids.size(): lines.append(_frame_line("JOINTFK", bake, i, ids[i], t))
		print("\n".join(lines))
	for aid in bake.arms:
		print("HEADL %s %.12f" % [aid, bake.head_length(aid)])
		var d := bake.declared(aid)
		var lines := PackedStringArray()
		for g in d.get("segments", []):
			lines.append("SEG %s %s %s %d %s %s" % [aid, _t(g["t0"]), _t(g["t1"]), int(g["event"]), str(g["tag"]), str(g["law"])])
		for k in d.get("knots", []):
			lines.append("KNOT %s %.9f %s %d" % [aid, float(k["t"]), str(k["kind"]), int(k["event"])])
		for r in d.get("rings", []):
			lines.append("RING %s %s %s %.12f %.12f %.12f" % [aid, str(r["name"]), str(r["channel"]), float(r["amp"]), float(r["f"]), float(r["tau"])])
		if lines.size() > 0: print("\n".join(lines))
