extends SceneTree
const LINK_TOL := .0001   # 0.1 mm: the chord a link loses between two rows of the bake
const FK_TOL := .000005   # 5 um: the joints table's FK chains in float32 against their pins, at rows
## Verify EVERY score contact and every arm across the full piece, not just a
## screenshot — as the harness plays it: through the motion bake (MotionBake,
## formlab/bake.py), read and interpolated the way performance.gd does.
## The links are held through the bake's joints table (formlab/kinematics.py), row
## by row, so a joint added to the table is checked with no change here:
##   C1 every aimed joint with extra.length keeps |P(target) - P| - length, and
##      every extra.closes pair closes, |P + B*(0, L, 0) - (P(target) + offset)|,
##      within LINK_TOL at 120 Hz (between rows a link loses the chord);
##   C2 a pose.orient joint's basis == its target's, bitwise;
##   C3 a pinned joint's P == its channel, and == the pose() key it names
##      (carriage root, elbowhead elbow, wristhead wrist, tool tip), bitwise;
##   C4 FK at every 7th row (t = times[i]: the stored float32 exactly): every
##      pinned joint's FK P within FK_TOL of its pin;
##   C5 seek invariance over the whole table: frames_at(48), frames_at(2),
##      frames_at(48) again gives the same P, B and q of every joint, both modes;
##   C6 a head joint's origin == tip_at + (0, head_length, 0), bitwise.
func _init() -> void:
	var asset := "clockwork"
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--asset="): asset=a.substr(8)
	var score_path := MotionBake.default_score(asset)
	if score_path == "":
		print("ERROR no default score for asset %s (known: %s): pass --score=PATH" % [asset, str(MotionBake.DEFAULT_SCORES.keys())]); quit(1); return
	var sd := ScoreDoc.new()
	if not sd.load(score_path):
		print(sd.errors); quit(1); return
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
			var hw: bool=e.get("window_lo")!=null and e["strings"].size()==1
			var expected := MotionBake.contact(layout,str(e["window_lo"]) if hw else str(e["strings"][k]),null if hw else e.get("pick"))
			worst_contact=maxf(worst_contact,actual.distance_to(expected)); contacts+=1
		for key in ["t_move","t","t_free"]:
			var t := float(e[key])
			worst_boundary=maxf(worst_boundary,rig.tip_at(aid,t-.000001).distance_to(rig.tip_at(aid,t+.000001)))
	for aid in rig.arms:
		unreachable+=int(rig.arms[aid]["unreachable"])
		# An intervening backwards seek must have no effect on a later pose.
		var before := rig.pose(aid,48)
		rig.pose(aid,2)
		if before!=rig.pose(aid,48): failures.append("seek changed pose "+aid)
	# The joints table's structure, read off its rows.
	var aimed: Array=[]    # [joint, target, length]
	var pairs: Array=[]    # [joint, target, offset, length]
	var orients: Array=[]  # [joint, target]
	var pins: Array=[]     # [joint, channel, the pose() key it names, aid]
	var heads: Array=[]    # arms with a head joint
	var rows: Array=rig.header.get("joints",[])
	for i in rows.size():
		var jt: Dictionary=rows[i]
		var extra: Dictionary=jt["extra"] if jt.get("extra") is Dictionary else {}
		var pz: Dictionary=jt["pose"] if jt.get("pose") is Dictionary else {}
		if pz.get("aim") is Dictionary and extra.has("length"):
			aimed.append([i,rig.joint_index(str(pz["aim"]["joint"])),float(extra["length"])])
		if pz.get("orient")!=null: orients.append([i,rig.joint_index(str(pz["orient"]))])
		if pz.get("pin")!=null:
			var pin: String=str(pz["pin"])
			pins.append([i,pin,pin.get_slice(".",1),pin.get_slice(".",0)])
		if extra.get("closes") is Dictionary:
			var c: Dictionary=extra["closes"]
			pairs.append([i,rig.joint_index(str(c["joint"])),MotionBake.v(c["offset"]),float(c["length"])])
	for aid in rig.arms:
		if rig.has_joint(aid+"/head"): heads.append(aid)
	for group in [aimed,pairs,orients]:
		for a in group:
			if int(a[1])<0: failures.append("a joints row names a target not in the table: "+rig.joint_ids()[int(a[0])])
	if aimed.is_empty() or pairs.is_empty() or pins.is_empty(): failures.append("the joints table has no aimed links, pairs or pins")
	# C1-C3, C6 at 120 Hz: frames fall between the bake's rows, so this is the
	# interpolated pose and a link may shorten by the chord of its arc.
	var off_orient := 0; var off_pin := 0; var off_head := 0; var samples := 0
	for frame in range(-120,int(sd.total_s*120)):
		var t := frame/120.0
		rig.frames_at(t); samples+=1
		for a in aimed:
			worst_link=maxf(worst_link,absf(rig.frame_p(a[1]).distance_to(rig.frame_p(a[0]))-float(a[2])))
		for a in pairs:
			var end: Vector3=rig.frame_p(a[0])+rig.frame_b(a[0])*Vector3(0,float(a[3]),0)
			worst_link=maxf(worst_link,end.distance_to(rig.frame_p(a[1])+(a[2] as Vector3)))
		for a in orients:
			if rig.frame_b(a[0])!=rig.frame_b(a[1]): off_orient+=1
		var poses := {}
		for a in pins:
			var at: Vector3=rig.frame_p(a[0])
			if at!=rig.vec(a[1],t): off_pin+=1
			if not rig.arms.has(a[3]): continue
			if not poses.has(a[3]): poses[a[3]]=rig.pose(a[3],t)
			if poses[a[3]].has(a[2]) and at!=poses[a[3]][a[2]]: off_pin+=1
		for aid in heads:
			if rig.joint_origin(aid+"/head",t)!=rig.tip_at(aid,t)+Vector3(0,rig.head_length(aid),0): off_head+=1
	if off_orient>0: failures.append("%d oriented frames are not their target's basis" % off_orient)
	if off_pin>0: failures.append("%d pinned joint origins are not their channel / pose" % off_pin)
	if off_head>0: failures.append("%d head origins are not tip_at + head_length" % off_head)
	# C4: FK at rows (a stepped arm's tool is pinned to .tip in pose mode while M5's
	# whip-and-lag separates wrist and tip dynamically).
	var worst_fk := 0.0; var fk_rows := 0
	for r in range(0,rig.times.size(),7):
		var t: float=rig.times[r]
		rig.frames_at(t,true); fk_rows+=1
		for a in pins:
			if rows[a[0]]["type"]=="fixed" and rig.arms.has(a[3]) and (rig.stepped(a[3]) or rig.arms[a[3]]["kind"]=="pick"): continue
			worst_fk=maxf(worst_fk,rig.frame_p(a[0]).distance_to(rig.vec(a[1],t)))
	if worst_fk>FK_TOL: failures.append("the joints table's FK misses its pins by %.9f m" % worst_fk)
	# C5: an intervening backwards seek must have no effect on the table either.
	for fk in [false,true]:
		rig.frames_at(48.0,fk)
		var snap := _frames(rig)
		rig.frames_at(2.0,fk); rig.frames_at(48.0,fk)
		if snap!=_frames(rig): failures.append("seek changed the joints table's frames (fk %s)" % str(fk))
	print("  joints table: %d aimed links, %d pairs, %d orients, %d pins, %d heads at %d samples; FK at %d rows worst=%.9f m" % [aimed.size(),pairs.size(),orients.size(),pins.size(),heads.size(),samples,fk_rows,worst_fk])
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


## Every joint's frame and value as the table holds them now.
func _frames(rig: MotionBake) -> Array:
	var out: Array=[]
	for i in rig.joint_count(): out.append([rig.frame_p(i),rig.frame_b(i),rig.frame_q(i)])
	return out
