extends SceneTree
const LINK_TOL := .0001   # 0.1 mm: the chord a link loses between two rows of the bake
## Verify EVERY score contact and every arm across the full piece, not just a
## screenshot — as the harness plays it: through the motion bake (MotionBake,
## formlab/bake.py), read and interpolated the way performance.gd does.
func _init() -> void:
	var sd := ScoreDoc.new()
	if not sd.load(ScoreDoc.default_path()):
		print(sd.errors); quit(1); return
	var asset := "clockwork"
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--asset="): asset=a.substr(8)
	var layout: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/"+asset+".json"))
	var rig := MotionBake.new()
	if not rig.load(MotionBake.path_for(sd.path,asset),sd.path,"res://assets/"+asset+".json"):
		print(rig.errors); quit(1); return
	var failures: Array=[]
	var contacts := 0
	var worst_contact := 0.0
	var worst_link := 0.0
	var worst_boundary := 0.0
	var unreachable := 0
	for e in sd.events:
		if e.get("actuator")==null: failures.append("unassigned event"); continue
		var aid: String=e["actuator"]
		var ts: Array=ScoreDoc.string_times(e)   # a rake roll's at its own onsets
		for k in range(e["strings"].size()):
			var t: float=ts[k]
			var actual := rig.tip_at(aid,t)
			var expected := MotionBake.contact(layout,e["strings"][k],e.get("pick"))
			worst_contact=maxf(worst_contact,actual.distance_to(expected)); contacts+=1
		for key in ["t_move","t","t_free"]:
			var t := float(e[key])
			worst_boundary=maxf(worst_boundary,rig.tip_at(aid,t-.000001).distance_to(rig.tip_at(aid,t+.000001)))
	for aid in rig.arms:
		var cfg: Dictionary=layout["arms"][aid]
		unreachable+=int(rig.arms[aid]["unreachable"])
		# 120 Hz frames fall between the bake's rows, so this is the
		# interpolated pose: a link may shorten by the chord of its arc.
		for frame in range(-120,int(sd.total_s*120)):
			var t := frame/120.0
			var p := rig.pose(aid,t)
			worst_link=maxf(worst_link,absf(p["root"].distance_to(p["elbow"])-float(cfg["l1"])))
			worst_link=maxf(worst_link,absf(p["elbow"].distance_to(p["wrist"])-float(cfg["l2"])))
			# The parallel bar of each segment must keep the same length as its primary.
			if cfg.has("o1"):
				var o1: Vector3=MotionBake.v(cfg["o1"]); var o2: Vector3=MotionBake.v(cfg["o2"])
				worst_link=maxf(worst_link,absf((p["root"]+o1).distance_to(p["elbow"]+o1)-float(cfg["l1"])))
				worst_link=maxf(worst_link,absf((p["elbow"]+o2).distance_to(p["wrist"]+o2)-float(cfg["l2"])))
		# An intervening backwards seek must have no effect on a later pose.
		var before := rig.pose(aid,48)
		rig.pose(aid,2)
		if before!=rig.pose(aid,48): failures.append("seek changed pose "+aid)
	# The planner promised arms of one mechanism stay arm_clearance_m apart
	# along x at every moment (they are 0.24 m wide); the rendered rig must keep it.
	var arm_ids: Array=rig.arms.keys()
	var worst_gap := INF
	for i in arm_ids.size():
		for j in range(i+1,arm_ids.size()):
			var a: String=arm_ids[i]; var b: String=arm_ids[j]
			var ma: String=layout["arms"][a]["mid"]
			if ma!=layout["arms"][b]["mid"]: continue
			var need := float(layout["mechanisms"][ma].get("arm_clearance_m",0.0))
			if need<=0.0: continue
			for frame in range(-120,int(sd.total_s*120)):
				var t := frame/120.0
				var gap := absf(rig.tip_at(a,t).x-rig.tip_at(b,t).x)
				worst_gap=minf(worst_gap,gap-need)
	if worst_gap<-.000001: failures.append("arms of one mechanism closer than their clearance by %.3f m" % -worst_gap)
	print("  cross-arm x margin beyond promised clearance: %.3f m" % worst_gap)
	if worst_contact>.00001: failures.append("contact miss")
	if worst_link>LINK_TOL: failures.append("link length changed")
	if worst_boundary>.001: failures.append("pose discontinuity")
	if unreachable>0: failures.append("unreachable targets")
	print("  contacts=%d worst=%.9f m; link error=%.9f m; boundary step=%.9f m; unreachable=%d" % [contacts,worst_contact,worst_link,worst_boundary,unreachable])
	print("CLOCKWORK RIG: PASS" if failures.is_empty() else str(failures))
	quit(0 if failures.is_empty() else 1)
