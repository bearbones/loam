extends SceneTree
## Sample authoritative tool origins for offline box/sphere clearance checks.
func _init() -> void:
	var sd := ScoreDoc.new()
	if not sd.load(ScoreDoc.default_path()): quit(1); return
	var layout: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://assets/clockwork.json"))
	var motion := ClockworkMotion.new(); motion.setup(sd,layout)
	var rows: Array=[]
	var aids: Array=motion.acts.keys()
	# Include exact contacts as well as the uniform time grid.
	var times: Array=[]
	for f in range(-120,int(sd.total_s*120)+1): times.append(f/120.0)
	for e in sd.events:
		for k in e["strings"].size(): times.append(float(e["t"])+k*float(e.get("spread_s",0)))
	times.sort()
	for aid in aids:
		for t in times:
			var p := motion.pose(aid,t)
			var tip: Vector3=p["tip"]
			# Radius tags distinguish mallets from picks in the offline surface checker.
			var struck: bool=layout["strings"][motion.acts[aid]["home"]]["struck"]
			rows.append([aid,t,[tip.x,tip.y,tip.z],.077 if struck else .029])
	var path := ProjectSettings.globalize_path("res://../render/form-study/motion.json")
	var file := FileAccess.open(path,FileAccess.WRITE)
	file.store_string(JSON.stringify({"hz":120,"segment_spacing_m":.01,"rows":rows}))
	print("MOTION: ",rows.size()," tool poses including exact contacts -> ",path)
	quit()
