extends Node3D
## Clockwork performance, with the original 2D harness retained as main.tscn.
var score := ScoreDoc.new()
var motion := ClockworkMotion.new()
var look := ClockworkLook.new()
var layout: Dictionary
var model: Node3D
var parts: Dictionary = {}
var strings: Dictionary = {}
var hits: Dictionary = {}
var camera: Camera3D
var player := AudioStreamPlayer.new()
var stem_players: Array = []
var time := -1.0
var playing := true
var auto_camera := true
var view := 0
var form_style := "carved"
var header: Label
var footer: Label
var track: TrackView
var seek: HSlider
var updating_seek := false
var shot := ""
var capture_dir := ""
var frame := 0
var warmup_frames := 0
var capture_start := 45.5
var capture_seconds := 8.0
var capture_fps := 30.0
var fixed_time := 48.0
var clock_started := false
var silent := false
var audio_mode := "master"

func option(key: String, fallback: String) -> String:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--"+key+"="):
			return a.substr(key.length()+3)
	return fallback

func _ready() -> void:
	var expanded := OS.get_cmdline_user_args().has("--expanded")
	var score_path := option("score",ProjectSettings.globalize_path("res://../render/clockwork/score.json") if expanded else ScoreDoc.default_path())
	if not score.load(score_path):
		push_error(str(score.errors)); get_tree().quit(1); return
	var asset := option("asset","clockwork_expanded" if expanded else "clockwork")
	var manifest_path := "res://assets/"+asset+".json"
	if not FileAccess.file_exists(manifest_path):
		push_error("Missing model manifest: "+manifest_path); get_tree().quit(1); return
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(manifest_path))
	if not parsed is Dictionary:
		push_error("Invalid model manifest: "+manifest_path); get_tree().quit(1); return
	layout=parsed
	for m in score.mechs:
		for s in m["strings"]:
			if not layout.get("strings",{}).has(s["id"]):
				push_error("Rebuild the model for score element "+s["id"]); get_tree().quit(1); return
		for a in m["actuators"]:
			if not layout.get("arms",{}).has(a["id"]):
				push_error("Rebuild the model for score arm "+a["id"]); get_tree().quit(1); return
	motion.setup(score,layout)
	model=load("res://assets/"+asset+".glb").instantiate()
	add_child(model)
	look.apply(model)
	form_style=option("form","carved")
	_set_form(form_style)
	for aid in layout["arms"]:
		parts[aid]={}
		for part in ["carriage","upper","lower","shoulder","elbow","wrist","tool","gear"]:
			parts[aid][part]=model.find_child(aid+"__"+part,true,false)
			if parts[aid][part]==null:
				push_error("Missing GLB pivot "+aid+"__"+part); get_tree().quit(1); return
	for sid in layout["strings"]:
		hits[sid]=[]
		if not layout["strings"][sid]["struck"]:
			var node := MeshInstance3D.new()
			node.mesh=ImmediateMesh.new()
			var mat := StandardMaterial3D.new()
			mat.albedo_color=Color(.72,.8,.78)
			if layout["strings"][sid]["mid"]=="harp":
				var pitch_class := int(layout["strings"][sid]["midi"])%12
				mat.albedo_color=Color("b74636") if pitch_class==0 else (Color("303a42") if pitch_class==5 else Color("d4c6a3"))
			mat.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED
			node.material_override=mat
			add_child(node); strings[sid]=node
	for e in score.events:
		for k in range(e.get("strings",[]).size()):
			var sid: String=e["strings"][k]
			hits[sid].append({"t":float(e["t"])+k*float(e.get("spread_s",0)),"event":e})
	_environment()
	_ui()
	add_child(player)
	var master_path := score.dir.path_join("chamber.wav")
	if FileAccess.file_exists(master_path):
		player.stream=AudioStreamWAV.load_from_file(master_path)
	else:
		audio_mode="stems"
	for mid in score.stem_ids():
		var p := AudioStreamPlayer.new(); p.stream=score.stems[mid]; add_child(p); stem_players.append(p)
	shot=OS.get_environment("SHOT")
	fixed_time=float(option("time","48"))
	capture_dir=option("capture","")
	capture_start=float(option("start","45.5"))
	capture_seconds=float(option("seconds","8"))
	capture_fps=float(option("fps","30"))
	view=int(option("view","0"))
	auto_camera=option("camera","auto")=="auto"
	silent=OS.get_cmdline_user_args().has("--silent")
	if shot!="": playing=false; time=fixed_time
	if capture_dir!="":
		DirAccess.make_dir_recursive_absolute(capture_dir); playing=false; time=capture_start
	print("CLOCKWORK: loaded ",score.events.size()," events, ",parts.size()," rigs; ",audio_mode," audio")

func _set_form(style: String) -> void:
	if not style in ["carved","ribbed","shell"]: style="carved"
	form_style=style
	for node in model.find_children("form_*","Node3D",true,false):
		node.visible=String(node.name).ends_with("_"+style) or String(node.name)=="form_bars_stand" or String(node.name).ends_with("_soundboard") or String(node.name).ends_with("_actionplate")

func _environment() -> void:
	look.light_rig(self)
	camera=Camera3D.new(); camera.fov=43; add_child(camera); camera.current=true

func _ui() -> void:
	var canvas := CanvasLayer.new(); add_child(canvas)
	canvas.visible=not OS.get_cmdline_user_args().has("--clean")
	var root := Control.new(); root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT); root.mouse_filter=Control.MOUSE_FILTER_IGNORE; canvas.add_child(root)
	header=Label.new(); header.position=Vector2(36,24); header.add_theme_font_size_override("font_size",25); root.add_child(header)
	footer=Label.new(); footer.position=Vector2(36,64); footer.add_theme_color_override("font_color",Color(.7,.74,.72)); root.add_child(footer)
	track=TrackView.new(); track.score=score; track.visible=false; track.position=Vector2(24,560); track.size=Vector2(1550,270); root.add_child(track)
	seek=HSlider.new(); seek.min_value=-1; seek.max_value=score.total_s; seek.step=.001; root.add_child(seek)
	get_viewport().size_changed.connect(_layout_ui)
	_layout_ui()
	seek.value_changed.connect(func(t):
		if not updating_seek: _seek(t))

func _layout_ui() -> void:
	var size := get_viewport().get_visible_rect().size
	seek.position=Vector2(36,size.y-38); seek.size=Vector2(size.x-72,22)
	track.position=Vector2(24,size.y-290); track.size=Vector2(size.x-48,235)

func _seek(t: float) -> void:
	time=clampf(t,-1,score.total_s); clock_started=false
	player.stop()
	for p in stem_players: p.stop()

func _start_audio() -> void:
	if audio_mode=="master": player.play(maxf(time,0))
	else:
		for p in stem_players: p.play(maxf(time,0))
	clock_started=true

func rod(node: Node3D, a: Vector3, b: Vector3) -> void:
	var y := (b-a).normalized()
	var x := y.cross(Vector3.FORWARD).normalized()
	if x.length_squared()<.01: x=Vector3.RIGHT
	node.transform=Transform3D(Basis(x,y*a.distance_to(b),x.cross(y).normalized()),(a+b)/2)

func evaluate(t: float) -> void:
	for aid in parts:
		var pose := motion.pose(aid,t)
		var p: Dictionary=parts[aid]
		p["carriage"].position=pose["root"]
		p["shoulder"].position=pose["root"]
		p["elbow"].position=pose["elbow"]
		p["wrist"].position=pose["tip"]+Vector3(0,.15,0)
		p["tool"].position=pose["tip"]
		rod(p["upper"],pose["root"],pose["elbow"])
		rod(p["lower"],pose["elbow"],pose["tip"]+Vector3(0,.15,0))
		p["gear"].position=pose["root"]+Vector3(0,0,.12)
		p["gear"].rotation.z=-pose["root"].x/.13
	for sid in strings:
		var s: Dictionary=layout["strings"][sid]
		var a := motion.v(s["a"]); var b := motion.v(s["b"])
		var displacement := PackedFloat32Array(); displacement.resize(24)
		for hit in hits[sid]:
			var tau := t-float(hit["t"])
			var e: Dictionary=hit["event"]
			if tau<0 or tau>5 or e.get("shape")==null: continue
			var values := score.shape_frame(e["shape"],tau)
			for i in mini(values.size(),24): displacement[i]+=values[i]*float(e["amp"])*.035
		var mesh: ImmediateMesh=strings[sid].mesh; mesh.clear_surfaces(); mesh.surface_begin(Mesh.PRIMITIVE_LINE_STRIP)
		for i in 24: mesh.surface_add_vertex(a.lerp(b,float(i)/23)+Vector3(0,0,displacement[i]))
		mesh.surface_end()
	for sid in hits:
		if not layout["strings"][sid]["struck"]: continue
		var energy := 0.0
		for hit in hits[sid]:
			var tau := t-float(hit["t"])
			if tau>=0 and tau<3: energy+=float(hit["event"]["amp"])*exp(-tau*8)*sin(tau*80)
		var element: Node3D=model.find_child(sid+" bar",true,false)
		if element!=null: element.position.y=motion.v(layout["strings"][sid]["a"]).y-.055+energy*.006
	var lamp: MeshInstance3D=model.find_child("chamber__lamp",true,false)
	lamp.scale=Vector3.ONE
	look.breathe(score.envelope_at("chamber",t))
	_camera_at(t)

func _camera_at(t: float) -> void:
	var target := Vector3(0,1.55,.2)
	var pos := Vector3(7.8,5.8,12.8)
	var chosen := view
	if auto_camera:
		var cue := "wide-dark"
		for c in score.cues:
			if c["kind"]=="camera" and float(c["t"])<=t: cue=c.get("name","")
		if cue in ["arm0-close","arm2-run"]: chosen=1
		elif cue=="rake-close": chosen=2
		elif cue=="bars-close": chosen=3
		elif cue=="overhead": chosen=4
	if chosen in [1,2,3]:
		var mid: String=["harp","rake","bars"][chosen-1]
		target=motion.v(layout["mechanisms"][mid]["center"])
		if chosen in [1,2]: target.y=1.95 if chosen==1 else 1.55
		pos=target+Vector3(2.6,2.0,5.8) if chosen!=1 else Vector3(2.8,3.25,7.8)
	elif chosen==4: pos=Vector3(.01,13,4)
	elif chosen==5: target=Vector3(.1,1.8,-2.55); pos=Vector3(.1,7,1.0)
	elif chosen==6: target=Vector3(-.15,3.3,.25); pos=target+Vector3(.65,.28,3.5)
	elif chosen==7: target=Vector3(0,1.95,0); pos=Vector3(0,1.95,6.6)
	elif chosen==8: target=Vector3(-.9,.35,.2); pos=target+Vector3(1.3,.8,2.2)
	camera.position=pos; camera.look_at(target)

func _process(dt: float) -> void:
	if model==null: return
	if playing:
		if time<0 or silent: time+=dt
		else:
			if not clock_started: _start_audio()
			var p: AudioStreamPlayer=player if audio_mode=="master" else stem_players[0]
			if p.playing: time=maxf(time,p.get_playback_position()+AudioServer.get_time_since_last_mix()-AudioServer.get_output_latency())
			else: time=score.total_s
		if time>=score.total_s: time=score.total_s; playing=false
	if capture_dir!="": time=capture_start+frame/capture_fps
	evaluate(time)
	var section := "pre-roll"
	for c in score.cues:
		if c["kind"]=="section" and float(c["t"])<=time: section=c.get("name","")
	header.text="L O A M    /    THE CLOCKWORK CHAMBER"
	footer.text="%s   ·   %05.2f s   ·   %s frame   ·   %s\nSpace  play/pause    ← →  seek    Home  restart    C  camera    F  frame    T  score    M  master/stems    1–9  mute stems" % [section.to_upper(),time,form_style,audio_mode]
	track.time=time; track.queue_redraw()
	updating_seek=true; seek.value=time; updating_seek=false
	if shot!="" or capture_dir!="":
		await RenderingServer.frame_post_draw
		warmup_frames+=1
		if warmup_frames<12: return
		var path := shot if shot!="" else capture_dir.path_join("%05d.png" % frame)
		get_viewport().get_texture().get_image().save_png(path)
		frame+=1
		if shot!="" or frame>=int(capture_seconds*capture_fps): get_tree().quit()

func _unhandled_key_input(event: InputEvent) -> void:
	if not event is InputEventKey or not event.pressed or event.echo: return
	match event.keycode:
		KEY_SPACE:
			playing=not playing
			_seek(time)
		KEY_HOME: _seek(-1)
		KEY_LEFT: _seek(time-2)
		KEY_RIGHT: _seek(time+2)
		KEY_C: auto_camera=false; view=(view+1)%6
		KEY_F: _set_form(["carved","ribbed","shell"][( ["carved","ribbed","shell"].find(form_style)+1)%3])
		KEY_A: auto_camera=true
		KEY_T: track.visible=not track.visible
		KEY_M:
			audio_mode="stems" if audio_mode=="master" else "master"
			if player.stream==null: audio_mode="stems"
			_seek(time)
		_:
			if event.keycode>=KEY_1 and event.keycode<=KEY_9:
				var index: int=event.keycode-KEY_1
				if index<stem_players.size():
					stem_players[index].volume_db=0 if stem_players[index].volume_db<-40 else -80
					if audio_mode!="stems": audio_mode="stems"; _seek(time)
