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
## --score=PATH --asset=NAME pick the pair; a stale bake prints its error.
func _init() -> void:
	var sd := ScoreDoc.new()
	if not sd.load(ScoreDoc.default_path()):
		print(sd.errors); quit(1); return
	var asset := "clockwork"
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--asset="): asset=a.substr(8)
	var bake := MotionBake.new()
	if not bake.load(MotionBake.path_for(sd.path,asset),sd.path,"res://assets/"+asset+".json"):
		print("ERROR ",bake.errors); quit(1); return
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
	quit(0)
