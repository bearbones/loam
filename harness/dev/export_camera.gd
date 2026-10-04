extends SceneTree
## Export the film's camera, frame by frame, so the rulers can put a world point
## on the rendered pixel without re-implementing the director
## (docs/goals/the-players.md, Acceptance, ruler 2; tools/players/r_screen.py).
##
## Regenerate it (render/ is gitignored: camera.json is a regenerable artifact,
## stale whenever harness/film_director.gd, the score's camera cues or the bake
## change):
##
##   godot --headless --path harness -s dev/export_camera.gd
##   godot --headless --path harness -s dev/export_camera.gd -- --out=PATH --score=PATH --asset=NAME --fps=30 --size=1920x1080
##
## (--out relative to the repository root; the expanded asset would be
## --asset=clockwork_expanded --score=<repo>/render/clockwork/score.json, though
## the film is the chamber's.) tools/players_reel.sh before also freezes a copy
## in render/players/before/camera.json.
##
## The camera is set up exactly as harness/performance.gd sets it up under
## --film: FilmDirector.setup(bake, layout, score), then per frame
## `camera.fov = c.fov; camera.look_at_from_position(c.pos, c.target, UP)` on a
## default Camera3D (keep_aspect KEEP_HEIGHT, so fov is the VERTICAL field of
## view) under the scene root, whose transform is the identity. The camera
## lives in a SubViewport the size of the film's frame, so Godot's own
## Camera3D.unproject_position gives the pixel the renderer puts a point on.
##
## Writes render/film/camera.json:
##   {format: "loam-camera/1", fps, width, height, keep_aspect: "KEEP_HEIGHT",
##    fov_axis: "vertical", near, far, total_s, asset, score, score_sha256,
##    bake_sha256 (the .motion.bin it followed), director_sha256,
##    projection: <the formula, for the reader>,
##    frames: [{k, t, shot, position: [x,y,z], basis: [x_axis, y_axis, z_axis]
##              (the camera's world axes, columns of its Basis; it looks along
##              -z_axis), target: [x,y,z], up: [0,1,0], fov_deg}, ...]
##              for every t = k/fps, k = 0 .. floor(total_s*fps),
##    probes: [{k, aid, p: [x,y,z], px: [u,v]}, ...]: each arm's baked tool
##              point every PROBE_EVERY frames, put on the frame by Godot's
##              unproject_position, so a reader can check its projection.}
## Pixels: u right from the left edge, v down from the top edge, in a
## width x height frame (scale both for a smaller capture of the same aspect).
const PROBE_EVERY := 15

var _done := false

# Nodes added to the root are in the tree (so look_at_from_position and
# unproject_position work) once the main loop runs: everything runs on the
# first frame, once.
func _process(_delta: float) -> bool:
	if _done: return true
	_done=true
	_export()
	return true

func _export() -> void:
	var repo := ProjectSettings.globalize_path("res://").path_join("..").simplify_path()
	var out := repo.path_join("render/film/camera.json")
	var asset := "clockwork"
	var fps := 30.0
	var width := 1920; var height := 1080
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="): out=a.substr(6) if a.substr(6).is_absolute_path() else repo.path_join(a.substr(6))
		elif a.begins_with("--asset="): asset=a.substr(8)
		elif a.begins_with("--fps="): fps=float(a.substr(6))
		elif a.begins_with("--size="):
			var wh := a.substr(7).split("x",false)
			width=int(wh[0]); height=int(wh[1])
	var score := ScoreDoc.new()
	if not score.load(ScoreDoc.default_path()):
		printerr("CAMERA: ",score.errors); quit(1); return
	var manifest_path := "res://assets/"+asset+".json"
	var layout = JSON.parse_string(FileAccess.get_file_as_string(manifest_path))
	if not layout is Dictionary:
		printerr("CAMERA: invalid model manifest ",manifest_path); quit(1); return
	var bake := MotionBake.new()
	if not bake.load(MotionBake.path_for(score.path,asset),score.path,manifest_path):
		printerr("CAMERA: ",bake.errors); quit(1); return
	var director := FilmDirector.new()
	director.setup(bake,layout,score)
	# The harness's camera, in a viewport the film's size.
	var viewport := SubViewport.new()
	viewport.size=Vector2i(width,height)
	viewport.render_target_update_mode=SubViewport.UPDATE_DISABLED
	root.add_child(viewport)
	var camera := Camera3D.new(); camera.fov=43
	viewport.add_child(camera); camera.current=true
	var keep := "KEEP_HEIGHT" if camera.keep_aspect==Camera3D.KEEP_HEIGHT else "KEEP_WIDTH"
	var frames: Array = []; var probes: Array = []
	var n := int(floor(score.total_s*fps+1e-9))
	for k in range(n+1):
		var t := k/fps
		var c := director.camera_at(t)
		camera.fov=float(c["fov"])
		camera.look_at_from_position(c["pos"],c["target"],Vector3.UP)
		var xf := camera.global_transform
		var target: Vector3=c["target"]
		frames.append({"k": k, "t": t, "shot": c["name"],
			"position": [xf.origin.x,xf.origin.y,xf.origin.z],
			"basis": [[xf.basis.x.x,xf.basis.x.y,xf.basis.x.z],[xf.basis.y.x,xf.basis.y.y,xf.basis.y.z],[xf.basis.z.x,xf.basis.z.y,xf.basis.z.z]],
			"target": [target.x,target.y,target.z], "up": [0.0,1.0,0.0], "fov_deg": camera.fov})
		if k%PROBE_EVERY==0:
			for aid in bake.arms:
				var p: Vector3=bake.pose(aid,t)["felt"]
				if camera.is_position_behind(p): continue
				var q := camera.unproject_position(p)
				probes.append({"k": k, "aid": aid, "p": [p.x,p.y,p.z], "px": [q.x,q.y]})
	var doc := {"format": "loam-camera/1", "fps": fps, "width": width, "height": height,
		"keep_aspect": keep, "fov_axis": "vertical" if keep=="KEEP_HEIGHT" else "horizontal",
		"near": camera.near, "far": camera.far, "total_s": score.total_s, "asset": asset,
		"score": score.path, "score_sha256": FileAccess.get_sha256(score.path),
		# what the camera was made from: the director follows the baked tools,
		# so a re-baked motion or a re-directed film makes this file stale
		"bake_sha256": FileAccess.get_sha256(MotionBake.path_for(score.path,asset).get_base_dir().path_join(str(bake.header["data"]))),
		"director_sha256": FileAccess.get_sha256("res://film_director.gd"),
		"director": "harness/film_director.gd", "exported_by": "harness/dev/export_camera.gd",
		"projection": "q = R^T (p - position), R = [x_axis y_axis z_axis] as columns; f = (height/2)/tan(fov_deg/2); u = width/2 + f*q.x/(-q.z); v = height/2 - f*q.y/(-q.z); in front iff q.z < 0",
		"frames": frames, "probes": probes}
	DirAccess.make_dir_recursive_absolute(out.get_base_dir())
	var file := FileAccess.open(out,FileAccess.WRITE)
	if file==null:
		printerr("CAMERA: cannot write ",out); quit(1); return
	file.store_string(JSON.stringify(doc,"",false,true))
	file.close()
	print("CAMERA: %d frames at %s fps, %dx%d, %s -> %s" % [frames.size(),fps,width,height,keep,out])
	quit(0)
