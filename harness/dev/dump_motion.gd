extends SceneTree
## Print the rendered rig's tool path so tools/test_motion.py can hold
## formlab/rig.py to it: one "TIP aid t x y z" line per arm per 1/240 s; and
## the pawl's angle over the rail ("PAWL x angle") for tools/test_pawl.py.
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
	for k in range(4001):
		var x := -.2+k*.0001
		print("PAWL %.9f %.12f" % [x,ClockworkMotion.pawl_angle(x)])
	quit(0)
