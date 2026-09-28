extends SceneTree
## Sample authoritative tool origins for offline box/sphere clearance checks.
func _init() -> void:
	var sd := ScoreDoc.new()
	if not sd.load(ScoreDoc.default_path()): quit(1); return
	var motion := MotionBake.new()
	if not motion.load(MotionBake.path_for(sd.path,"clockwork"),sd.path,"res://assets/clockwork.json"):
		print(motion.errors); quit(1); return
	var rows: Array=[]
	var aids: Array=motion.arms.keys()
	# Include exact contacts as well as the uniform time grid.
	var times: Array=[]
	for f in range(-120,int(sd.total_s*120)+1): times.append(f/120.0)
	for e in sd.events:
		for k in e["strings"].size(): times.append(float(e["t"])+k*float(e.get("spread_s",0)))
	times.sort()
	for aid in aids:
		for t in times:
			var tip: Vector3=motion.tip_at(aid,t)
			# Radius tags distinguish mallets from picks in the offline surface checker.
			var struck: bool=motion.stepped(aid)   # a stepped arm strikes a bar; a servo plucks
			rows.append([aid,t,[tip.x,tip.y,tip.z],.077 if struck else .029])
	var path := ProjectSettings.globalize_path("res://../render/form-study/motion.json")
	var file := FileAccess.open(path,FileAccess.WRITE)
	file.store_string(JSON.stringify({"hz":120,"segment_spacing_m":.01,"rows":rows}))
	print("MOTION: ",rows.size()," tool poses including exact contacts -> ",path)
	quit()
