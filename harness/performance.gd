extends Node3D
## Clockwork performance, with the original 2D harness retained as main.tscn.
## Every moving part of one arm, as named in the GLB (aid + "__" + part). The
## parallelogram pairs (upper/upper2, lower/lower2) and the crossheads
## (carriage, elbowhead, wristhead) are posed from the same IK as the pins.
const PART_NAMES := ["carriage","upper","upper2","lower","lower2","elbowhead","wristhead","shoulder","elbow","wrist","tool","shank","gear"]
var score := ScoreDoc.new()
var motion := ClockworkMotion.new()
var look := ClockworkLook.new()
var layout: Dictionary
var model: Node3D
var parts: Dictionary = {}
var gear_home: Dictionary = {}   # each pinion's imported basis: the disc in its mount's plane, unspun
var wheel_home: Dictionary = {}  # the flywheel, hub and pulleys: node -> imported basis, unspun
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
var follow_sid := ""
var follow_since := -1e9

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
		for part in PART_NAMES:
			parts[aid][part]=model.find_child(aid+"__"+part,true,false)
			if parts[aid][part]==null:
				push_error("Missing GLB pivot "+aid+"__"+part); get_tree().quit(1); return
		gear_home[aid]=parts[aid]["gear"].basis
	# The chamber's flywheel, its axle pulley and the belt pulley turn about z
	# (formlab.layout.flywheel_plan); their imported bases are the unspun home.
	for label in ["Chamber flywheel","Chamber hub","Chamber drive pulley","Chamber belt pulley"]:
		var node: Node3D=model.find_child(label,true,false)
		if node!=null: wheel_home[node]=node.basis
	for sid in layout["strings"]:
		hits[sid]=[]
		if not layout["strings"][sid]["struck"]:
			strings[sid]=_make_string(sid)
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

const WIRE := preload("res://shaders/wire_string.gdshader")
const STRING_NODES := 24

## A string is a static shaded tube along its own +Y (z = the pluck direction,
## world Z). The wire shader bends it each frame from the baked shape frames;
## a second, translucent copy is a sheath widened to the recent peak excursion —
## the blur a vibrating wire actually presents to the eye. Gauge follows pitch
## (a display gauge: true wire would be sub-pixel) and the strings are strung by
## register as a harp is (string_family), C strings red and F strings dark.
func _make_string(sid: String) -> Node3D:
	var s: Dictionary=layout["strings"][sid]
	var a := motion.v(s["a"]); var b := motion.v(s["b"])
	var length := a.distance_to(b)
	var midi := float(s["midi"])
	var radius := .0035*pow(2.0,(64.0-midi)/18.0)
	var family := string_family(midi)
	var holder := Node3D.new(); holder.name=sid+" string"
	holder.transform=Transform3D(ClockworkMotion.link_basis(a,b),a)
	var colour := string_colour(s["mid"],midi,family)
	var mesh := _wire_mesh(length,radius,48,10)
	for sheath in [false,true]:
		var node := MeshInstance3D.new(); node.mesh=mesh
		var mat := ShaderMaterial.new(); mat.shader=WIRE
		mat.set_shader_parameter("radius",radius); mat.set_shader_parameter("length_m",length)
		mat.set_shader_parameter("albedo",colour); mat.set_shader_parameter("family",family)
		mat.set_shader_parameter("sheath",sheath)
		var zero := PackedFloat32Array(); zero.resize(STRING_NODES)
		mat.set_shader_parameter("disp",zero); mat.set_shader_parameter("envelope",zero)
		node.material_override=mat
		if sheath: node.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		holder.add_child(node)
	add_child(holder)
	if s.has("neck"): _make_dead_length(sid,s,radius,colour,family)
	return holder

## Past its speaking length a harp string runs on over the bridge pin to its
## tuning pin (formlab.layout.neck_plan, `neck` on the string): the same wire,
## drawn straight and never excited — a node beside the string, not under it,
## so the per-frame shape updates never touch it.
func _make_dead_length(sid: String, s: Dictionary, radius: float, colour: Color, family: int) -> void:
	var dead := Node3D.new(); dead.name=sid+" dead"
	var points: Array=[motion.v(s["b"]),motion.v(s["neck"]["bridge"]),motion.v(s["neck"]["pin"])]
	for i in range(points.size()-1):
		var p: Vector3=points[i]; var q: Vector3=points[i+1]; var length: float=p.distance_to(q)
		var node := MeshInstance3D.new(); node.mesh=_wire_mesh(length,radius,4,10)
		node.transform=Transform3D(ClockworkMotion.link_basis(p,q),p)
		var mat := ShaderMaterial.new(); mat.shader=WIRE
		mat.set_shader_parameter("radius",radius); mat.set_shader_parameter("length_m",length)
		mat.set_shader_parameter("albedo",colour); mat.set_shader_parameter("family",family)
		mat.set_shader_parameter("sheath",false)
		var zero := PackedFloat32Array(); zero.resize(STRING_NODES)
		mat.set_shader_parameter("disp",zero); mat.set_shader_parameter("envelope",zero)
		node.material_override=mat
		dead.add_child(node)
	add_child(dead)

## The flywheel's angle at time t: one turn per bar of the score's tempo,
## the wheel's +x face turning down toward the house (a negative turn about z).
func flywheel_angle(t: float) -> float:
	return -TAU*t*float(score.doc.get("bpm",84.0))/240.0

## A harp is strung by register: wound wire below C4, gut through the middle,
## nylon from C5 up (the wire shader's `family`: 0 steel, 1 wound, 2 gut, 3 nylon).
static func string_family(midi: float) -> int:
	if midi<60.0: return 1
	if midi>=72.0: return 3
	return 2

## Wound strings are silver-plated on the harp and bronze on the rake; gut is
## warm ivory, nylon near clear. Every C is red; F is black on gut and wire,
## blue on nylon, as harp makers colour them.
static func string_colour(mid: String, midi: float, family: int) -> Color:
	var colour := Color(.80,.82,.84)
	if family==1: colour=Color(.84,.83,.80) if mid=="harp" else Color(.72,.56,.40)
	elif family==2: colour=Color(.87,.78,.60)
	elif family==3: colour=Color(.94,.93,.90)
	if mid=="harp":
		var pitch_class := int(midi)%12
		if pitch_class==0: colour=Color("c8483a")
		elif pitch_class==5: colour=Color("2f4f9a") if family==3 else Color("2c3540")
	return colour

## Tube along +Y from 0 to `length`: `rings` samples along it (UV.x = fraction,
## so the shader can interpolate the 24 shape nodes smoothly), `sides` around.
static func _wire_mesh(length: float, radius: float, rings: int, sides: int) -> ArrayMesh:
	var verts := PackedVector3Array(); var norms := PackedVector3Array(); var uvs := PackedVector2Array(); var idx := PackedInt32Array()
	for j in rings+1:
		var y := length*float(j)/rings
		for k in sides+1:
			var th := TAU*float(k)/sides
			verts.append(Vector3(radius*cos(th),y,radius*sin(th)))
			norms.append(Vector3(cos(th),0,sin(th)))
			uvs.append(Vector2(float(j)/rings,float(k)/sides))
	for j in rings:
		for k in sides:
			var p := j*(sides+1)+k
			idx.append_array([p,p+1,p+sides+1, p+1,p+sides+2,p+sides+1])
	var arrays := []; arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX]=verts; arrays[Mesh.ARRAY_NORMAL]=norms; arrays[Mesh.ARRAY_TEX_UV]=uvs; arrays[Mesh.ARRAY_INDEX]=idx
	var mesh := ArrayMesh.new(); mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	return mesh

func _set_form(style: String) -> void:
	if not style in ["carved","ribbed","shell"]: style="carved"
	form_style=style
	# Frame variants share a name stem and are switched here; everything else
	# built by build_forms.py (the stands, soundboards, action plates, the rail
	# gantries and heads with their racks) is not a variant and stays visible.
	for node in model.find_children("form_*","Node3D",true,false):
		var n := String(node.name)
		node.visible=n.ends_with("_"+style) or n.ends_with("_stand") or n.ends_with("_soundboard") or n.ends_with("_actionplate") or n.ends_with("_gantry") or n.ends_with("_railhead")

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
		var cfg: Dictionary=layout["arms"][aid]
		var o1 := motion.v(cfg["o1"]); var o2 := motion.v(cfg["o2"])
		var root: Vector3=pose["root"]; var elbow: Vector3=pose["elbow"]; var wrist: Vector3=pose["wrist"]
		# Crossheads and pins keep a fixed orientation: that is what the parallelograms guarantee.
		p["carriage"].position=root; p["shoulder"].position=root
		p["elbowhead"].position=elbow; p["elbow"].position=elbow
		p["wristhead"].position=wrist; p["wrist"].position=wrist
		p["tool"].position=pose["tip"]; p["shank"].position=pose["tip"]
		var upper := ClockworkMotion.link_basis(root,elbow)
		var lower := ClockworkMotion.link_basis(elbow,wrist)
		p["upper"].transform=Transform3D(upper,root)
		p["upper2"].transform=Transform3D(upper,root+o1)
		p["lower"].transform=Transform3D(lower,elbow)
		p["lower2"].transform=Transform3D(lower,elbow+o2)
		# The pinion rides its axle on the carriage and rolls on the rack
		# (formlab.clearance.PINION / MOUNTS, formlab.gantry.rack): in front of
		# or behind the carriage it is upright under a rack above it; above or
		# below the carriage it lies flat against a rack behind the rail. Either
		# way +x travel turns it by x / pitch radius (.12) about its axle.
		# The spin composes on the imported basis: setting one Euler component of
		# a basis that is a quarter turn about X hits gimbal lock and tilted the disc.
		var mount: String=str(cfg.get("pinion","back"))
		var flat := mount=="up" or mount=="down"
		p["gear"].position=root+(Vector3(0,(.17 if mount=="up" else -.17),-.10) if flat else Vector3(0,0,(.195 if mount=="front" else -.195)))
		p["gear"].basis=Basis(Vector3.UP if flat else Vector3(0,0,1),root.x/.12)*gear_home[aid]
	# The flywheel turns once a bar; the belt pulley turns with it, faster by the
	# pulleys' radii, the same way round (an open belt).
	var spin: float=flywheel_angle(t)
	for node in wheel_home:
		var k: float=1.0
		if node.name=="Chamber belt pulley" and layout.has("flywheel"):
			var f: Dictionary=layout["flywheel"]; k=float(f["cyls"]["drive pulley"][2])/float(f["cyls"]["belt pulley"][2])
		node.basis=Basis(Vector3(0,0,1),spin*k)*wheel_home[node]
	for sid in strings:
		var displacement := PackedFloat32Array(); displacement.resize(STRING_NODES)
		var envelope := PackedFloat32Array(); envelope.resize(STRING_NODES)
		for hit in hits[sid]:
			var tau := t-float(hit["t"])
			var e: Dictionary=hit["event"]
			if tau<0 or tau>5 or e.get("shape")==null: continue
			var gain := float(e["amp"])*.035
			var values := score.shape_frame(e["shape"],tau)
			for i in mini(values.size(),STRING_NODES): displacement[i]+=values[i]*gain
			# The sheath holds the peak excursion over the last 1/30 s — the
			# eye integrates a few cycles of a wire, so the blur, not the instant.
			var step := 1.0/float(score.clips[e["shape"]]["rate_hz"])
			for k in range(1,5):
				var past := score.shape_frame(e["shape"],tau-k*step)
				for i in mini(past.size(),STRING_NODES): envelope[i]=maxf(envelope[i],absf(past[i]*gain))
		var peak := 0.0
		for i in STRING_NODES:
			envelope[i]=maxf(envelope[i],absf(displacement[i])); peak=maxf(peak,envelope[i])
		# A sounding string glows with its energy (a full-amplitude pluck peaks near 0.035 m).
		var excitation := clampf(peak/.02,0.0,1.0)
		for child in strings[sid].get_children():
			var mat: ShaderMaterial=child.material_override
			mat.set_shader_parameter("disp",displacement); mat.set_shader_parameter("envelope",envelope)
			mat.set_shader_parameter("excitation",excitation)
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
	elif chosen==9:
		# Joint close-up: follow the second harp arm's elbow from behind the string plane.
		var aid: String="harp_arm1" if layout["arms"].has("harp_arm1") else layout["arms"].keys()[0]
		var pose := motion.pose(aid,t)
		target=(pose["elbow"]+pose["wrist"])/2; pos=target+Vector3(1.5,.45,-1.9)
	elif chosen==10:
		# String close-up: the most recently sounded unstruck string, seen from
		# 45° off its pluck axis so both the bend and the blur read. The camera
		# latches for a while so a run of plucks does not throw it about.
		var best_t := -1e9; var best_sid := ""
		for sid in hits:
			if layout["strings"][sid]["struck"]: continue
			for hit in hits[sid]:
				if float(hit["t"])<=t and float(hit["t"])>best_t: best_t=float(hit["t"]); best_sid=sid
		if best_sid=="": best_sid=hits.keys()[0]
		if follow_sid=="" or t<follow_since or t-follow_since>1.5: follow_sid=best_sid; follow_since=t
		var s: Dictionary=layout["strings"][follow_sid]
		var a := motion.v(s["a"]); var b := motion.v(s["b"])
		target=a.lerp(b,.3); pos=target+Vector3(.85,.3,.85)
	elif chosen==11:
		# Bar frame close-up: the treble end's rails, cord posts and resonator mouths, from low in front.
		var c := motion.v(layout["mechanisms"]["bars"]["center"]) if layout["mechanisms"].has("bars") else Vector3(4.5,1.35,1.2)
		target=c+Vector3(.8,-.17,0); pos=c+Vector3(-.6,-.3,1.7)
	elif chosen==12:
		# The harp's action from the string side: the plate on the neck's string-side
		# face, the discs and fork pins straddling the strings, bridge and tuning pins
		# and the dead lengths, seen from behind the string plane where the arms work.
		var c := motion.v(layout["mechanisms"]["harp"]["center"]) if layout["mechanisms"].has("harp") else Vector3(0,3.3,0)
		target=Vector3(c.x-.1,3.35,c.z); pos=target+Vector3(1.05,.15,-1.45)
	elif chosen==13:
		# The flywheel drive: wheel, plummer blocks, pedestals, the belt to the cabinet's end.
		var f: Vector3=motion.v(layout["flywheel"]["centre"]) if layout.has("flywheel") else Vector3(-2.4,.53,-1.5)
		target=f+Vector3(.2,-.05,-.1); pos=f+Vector3(-.75,.55,1.75)
	elif chosen==14:
		# The harp's string feet from the string side: the eyelets on the ferrule
		# mouths along the soundbox, looking down the feet line from the treble end.
		var e: Vector3=motion.v(layout["eyelets"]["harp07"]["centre"]) if layout.has("eyelets") and layout["eyelets"].has("harp07") else Vector3(0,1.45,0)
		target=e+Vector3(-.15,.02,0); pos=e+Vector3(.85,.55,-.9)
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
