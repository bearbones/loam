extends SceneTree
## Sample authoritative tool origins for offline box/sphere clearance checks
## (tools/check_form_clearance.py): every arm's tool joint (the joints table's
## `<aid>/tool`, MotionBake.joint_origin) on a 120 Hz grid and at every contact.
## --asset=NAME picks the manifest (default clockwork), --score=PATH the score
## (default the asset's own in this tree: MotionBake.default_score), --out=PATH
## the file (default render/form-study/motion.json).
func _init() -> void:
	var asset := "clockwork"
	var out := "res://../render/form-study/motion.json"
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--asset="): asset=a.substr(8)
		if a.begins_with("--out="): out=a.substr(6)
	var score_path := MotionBake.default_score(asset)
	if score_path == "":
		print("ERROR no default score for asset %s (known: %s): pass --score=PATH" % [asset, str(MotionBake.DEFAULT_SCORES.keys())]); quit(1); return
	var sd := ScoreDoc.new()
	if not sd.load(score_path): print(sd.errors); quit(1); return
	var motion := MotionBake.new()
	if not motion.load(MotionBake.path_for(sd.path,asset),sd.path,"res://assets/"+asset+".json"):
		print(motion.errors); quit(1); return
	var rows: Array=[]
	var aids: Array=motion.arms.keys()
	# Include exact contacts as well as the uniform time grid.
	var times: Array=[]
	for f in range(-120,int(sd.total_s*120)+1): times.append(f/120.0)
	for e in sd.events:
		times.append_array(ScoreDoc.string_times(e))   # a rake roll's at its own onsets
	times.sort()
	for aid in aids:
		for t in times:
			var tip: Vector3=motion.joint_origin(aid+"/tool",t)
			# Radius tags distinguish mallets from picks in the offline surface checker.
			var struck: bool=motion.stepped(aid)   # a stepped arm strikes a bar; a servo plucks
			rows.append([aid,t,[tip.x,tip.y,tip.z],.077 if struck else .029])
	var path := ProjectSettings.globalize_path(out)
	var file := FileAccess.open(path,FileAccess.WRITE)
	file.store_string(JSON.stringify({"hz":120,"segment_spacing_m":.01,"rows":rows}))
	print("MOTION: ",rows.size()," tool poses including exact contacts -> ",path)
	quit()
