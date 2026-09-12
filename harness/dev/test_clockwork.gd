extends SceneTree
## Verify EVERY score contact and every arm across the full piece, not just a screenshot.
func _init() -> void:
	var sd := ScoreDoc.new()
	if not sd.load(ScoreDoc.default_path()):
		print(sd.errors); quit(1); return
	var asset := "clockwork"
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--asset="): asset=a.substr(8)
	var layout: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/"+asset+".json"))
	var rig := ClockworkMotion.new(); rig.setup(sd,layout)
	var failures: Array=[]
	var contacts := 0
	var worst_contact := 0.0
	var worst_link := 0.0
	var worst_boundary := 0.0
	var unreachable := 0
	for e in sd.events:
		if e.get("actuator")==null: failures.append("unassigned event"); continue
		var aid: String=e["actuator"]
		for k in range(e["strings"].size()):
			var t := float(e["t"])+k*float(e.get("spread_s",0))
			var actual := rig.tip_at(aid,t)
			var expected := rig.contact(e["strings"][k],e.get("pick"))
			worst_contact=maxf(worst_contact,actual.distance_to(expected)); contacts+=1
		for key in ["t_move","t","t_free"]:
			var t := float(e[key])
			worst_boundary=maxf(worst_boundary,rig.tip_at(aid,t-.000001).distance_to(rig.tip_at(aid,t+.000001)))
	for aid in rig.acts:
		var cfg: Dictionary=layout["arms"][aid]
		for frame in range(-120,int(sd.total_s*120)):
			var t := frame/120.0
			var p := rig.pose(aid,t)
			if not p["reachable"]: unreachable+=1
			worst_link=maxf(worst_link,absf(p["root"].distance_to(p["elbow"])-float(cfg["l1"])))
			worst_link=maxf(worst_link,absf(p["elbow"].distance_to(p["tip"]+Vector3(0,.15,0))-float(cfg["l2"])))
		# An intervening backwards seek must have no effect on a later pose.
		var before := rig.pose(aid,48)
		rig.pose(aid,2)
		if before!=rig.pose(aid,48): failures.append("seek changed pose "+aid)
	if worst_contact>.00001: failures.append("contact miss")
	if worst_link>.00001: failures.append("link length changed")
	if worst_boundary>.001: failures.append("pose discontinuity")
	if unreachable>0: failures.append("unreachable targets")
	print("  contacts=%d worst=%.9f m; link error=%.9f m; boundary step=%.9f m; unreachable=%d" % [contacts,worst_contact,worst_link,worst_boundary,unreachable])
	print("CLOCKWORK RIG: PASS" if failures.is_empty() else str(failures))
	quit(0 if failures.is_empty() else 1)
