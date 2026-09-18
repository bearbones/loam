extends SceneTree
## Print the rendered rig's tool path so tools/test_motion.py can hold
## formlab/rig.py to it: one "TIP aid t x y z" line per arm per 1/240 s; the
## assembly's shudder off the recoil bus ("SHUD aid t stand rail mast", the rail
## sag taken at mid-span, per stepped arm per 1/120 s); a hinged hammer's flip
## angle and felt face ("HEAD aid t angle fx fy fz"); and the pawl's angle over
## the rail ("PAWL x angle") for tools/test_pawl.py.
func _init() -> void:
	var sd := ScoreDoc.new()
	if not sd.load(ScoreDoc.default_path()):
		print(sd.errors); quit(1); return
	var asset := "clockwork"
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--asset="): asset=a.substr(8)
	var layout: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/"+asset+".json"))
	var rig := ClockworkMotion.new(); rig.setup(sd,layout)
	for aid in rig.acts:
		for frame in range(-240,int(sd.total_s*240)):
			var t := frame/240.0
			var p := rig.tip_at(aid,t)
			print("TIP %s %.9f %.9f %.9f %.9f" % [aid,t,p.x,p.y,p.z])
	# A hinged hammer's flip and the felt face it carries ("HEAD aid t angle fx fy fz").
	for aid in rig.acts:
		if not rig.hammer(aid): continue
		for frame in range(-240,int(sd.total_s*240)):
			var t := frame/240.0
			var f := rig.pose(aid,t)
			print("HEAD %s %.9f %.12f %.9f %.9f %.9f" % [aid,t,f["head"],f["felt"].x,f["felt"].y,f["felt"].z])
	for aid in rig.acts:
		if not rig.stepped(aid): continue
		var span: Array = rig.rail_span(aid)
		var mid: float = (span[0]+span[1])/2.0
		for frame in range(-120,int(sd.total_s*120)):
			var t := frame/120.0
			print("SHUD %s %.9f %.12f %.12f %.12f" % [aid,t,rig.stand_thump(rig.mech_of[aid],t),rig.rail_sag(aid,t,mid),rig.mast_sway(aid,t)])
	for k in range(4001):
		var x := -.2+k*.0001
		print("PAWL %.9f %.12f" % [x,ClockworkMotion.pawl_angle(x)])
	quit(0)
