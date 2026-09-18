extends Node3D
## Clockwork performance, with the original 2D harness retained as main.tscn.
## Every moving part of one arm, as named in the GLB (aid + "__" + part). The
## parallelogram pairs (upper/upper2, lower/lower2) and the crossheads
## (carriage, elbowhead, wristhead) are posed from the same IK as the pins.
const PART_NAMES := ["carriage","upper","upper2","lower","lower2","elbowhead","wristhead","shoulder","elbow","wrist","tool","shank"]
var screw_nodes: Dictionary = {} # each servo arm's leadscrew shaft (form_<aid>_screw), spun about its axis
var screw_home: Dictionary = {}  # ...and its imported transform
var score := ScoreDoc.new()
var motion := ClockworkMotion.new()
var look := ClockworkLook.new()
var layout: Dictionary
var model: Node3D
var parts: Dictionary = {}
var gear_home: Dictionary = {}   # each pinion's imported basis: the disc in its mount's plane, unspun
var pawl_home: Dictionary = {}   # each mallet arm's roller detent pawl (formlab.pawl), imported basis
var roller_home: Dictionary = {} # the pawl's roller, imported basis
var wheel_home: Dictionary = {}  # the flywheel, hub and pulleys: node -> imported basis, unspun
var head_home: Dictionary = {}   # each hinged hammer's head (formlab.linkage.hammer_tool), imported basis
var stand_nodes: Dictionary = {}    # mid -> the instrument's stand and its imported home
var shudder_nodes: Dictionary = {}  # aid -> the rail's bars and the gantry it stands on, and the sway pivot
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
var capture_speed := 1.0         # score seconds a video second: 0.25 is quarter speed
var focus := ""                  # --focus=<aid>: frame that arm's mechanism, not the room
var focus_span := 2.4            # metres of rail across the frame (a minimum)
var focus_dir := Vector3.ZERO    # --focus_dir=x,y,z: stand-off direction; zero = derive it
var focus_at := ""               # --focus_at=tip|root|head: frame THAT point, focus_span the true width
var fixed_time := 48.0
var clock_started := false
var silent := false
var audio_mode := "master"
var follow_sid := ""
var follow_since := -1e9
# The ratchet's click has a sound (docs/plans/pawl-follow-ups.md, item 2): one
# sample, synthesised once, played from each pawl's roller at every click the
# rig makes (ClockworkMotion.click_times), CLICK_DB under the instruments.
const CLICK_DB := -12.0
var click_stream: AudioStreamWAV
var clicks: Dictionary = {}        # aid -> the arm's clicks, in time order
var click_players: Dictionary = {} # aid -> AudioStreamPlayer3D on the roller
var click_next: Dictionary = {}    # aid -> index of the first click not yet played
var prev_time := -1.0

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
		# A stepped arm's carriage carries a pinion on a rack; a servo arm's rides a
		# leadscrew (formlab.clearance.drive_kind, docs/plans/leadscrew-servo-drive.md):
		# the shaft is a world form turned about its own axis as the carriage travels.
		if str(layout["arms"][aid].get("drive","rack"))=="rack":
			parts[aid]["gear"]=model.find_child(aid+"__gear",true,false)
			if parts[aid]["gear"]==null:
				push_error("Missing GLB pivot "+aid+"__gear"); get_tree().quit(1); return
			gear_home[aid]=parts[aid]["gear"].basis
		else:
			var screw: Node3D=model.find_child("form_"+aid+"_screw",true,false)
			if screw==null:
				push_error("Missing GLB leadscrew form_"+aid+"_screw"); get_tree().quit(1); return
			screw_nodes[aid]=screw; screw_home[aid]=screw.transform
		# A hinged hammer's head is its own part, turning on the flange's pin
		# (formlab.linkage.hammer_tool, ClockworkMotion.head_angle).
		if layout["arms"][aid].has("head"):
			parts[aid]["head"]=model.find_child(aid+"__head",true,false)
			if parts[aid]["head"]==null:
				push_error("Missing GLB pivot "+aid+"__head"); get_tree().quit(1); return
			head_home[aid]=parts[aid]["head"].basis
		# A mallet arm's pinion carries a roller detent pawl (formlab.pawl), posed at
		# its pivot on the carriage and turned to ride the teeth.
		if layout["arms"][aid].has("pawl"):
			parts[aid]["pawl"]=model.find_child(aid+"__pawl",true,false)
			if parts[aid]["pawl"]==null:
				push_error("Missing GLB pivot "+aid+"__pawl"); get_tree().quit(1); return
			pawl_home[aid]=parts[aid]["pawl"].basis
			parts[aid]["roller"]=model.find_child(aid+"__roller",true,false)
			if parts[aid]["roller"]==null:
				push_error("Missing GLB pivot "+aid+"__roller"); get_tree().quit(1); return
			roller_home[aid]=parts[aid]["roller"].basis
			# ...and a click: the sample on a player that rides with the roller, so the
			# sound comes from the pawl wherever the carriage is along its rail.
			if click_stream==null: click_stream=click_sample()
			clicks[aid]=motion.click_times(aid)
			var cp := AudioStreamPlayer3D.new()
			cp.name="click"; cp.stream=click_stream; cp.volume_db=CLICK_DB
			cp.attenuation_model=AudioStreamPlayer3D.ATTENUATION_DISABLED; cp.max_polyphony=4
			parts[aid]["roller"].add_child(cp); click_players[aid]=cp; click_next[aid]=0
	# The chamber's flywheel, its axle pulley and the belt pulley turn about z
	# (formlab.layout.flywheel_plan); their imported bases are the unspun home.
	for label in ["Chamber flywheel","Chamber hub","Chamber drive pulley","Chamber belt pulley"]:
		var node: Node3D=model.find_child(label,true,false)
		if node!=null: wheel_home[node]=node.basis
	_assembly_nodes()
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
	# A slow-motion capture takes capture_fps frames a VIDEO second while score
	# time runs at capture_speed: at 60 fps and 0.25, a 90 ms click fills 22
	# frames. --seconds stays the score window, so the frame count grows.
	capture_speed=maxf(float(option("speed","1")),.001)
	focus=option("focus","")
	focus_span=maxf(float(option("focus_span","2.4")),.1)
	focus_at=option("focus_at","")
	var fd: PackedStringArray=option("focus_dir","").split(",",false)
	if fd.size()==3: focus_dir=Vector3(float(fd[0]),float(fd[1]),float(fd[2]))
	view=int(option("view","0"))
	auto_camera=option("camera","auto")=="auto"
	silent=OS.get_cmdline_user_args().has("--silent")
	if shot!="": playing=false; time=fixed_time
	if capture_dir!="":
		DirAccess.make_dir_recursive_absolute(capture_dir); playing=false; time=capture_start
	print("CLOCKWORK: loaded ",score.events.size()," events, ",parts.size()," rigs; ",audio_mode," audio")

## The blow shakes the ASSEMBLY, not only the arm (docs/motion-design.md): the
## nodes the recoil bus moves, cached with their imported homes. A struck
## instrument's stand thumps vertically; the arm's two guide bars (and its rack,
## where the build packs it as a form of its own) carry the rail's sag; the
## gantry and its heads sway about the line through the plinth feet. The harp's
## and the rake's frames are NOT on the bus: those are servo arms and nothing
## there is struck.
func _assembly_nodes() -> void:
	for mid in layout.get("mechanisms",{}):
		var stand: Node3D=model.find_child("form_"+mid+"_stand",true,false)
		if stand!=null: stand_nodes[mid]={"node":stand,"home":stand.transform}
	for aid in layout["arms"]:
		if not motion.stepped(aid): continue
		var bars: Array=[]
		# Both guide bars are exported as "<aid> rail" and "<aid> rail_001"; each
		# carries the beam's own rotation, so the whole transform is the home.
		for node in model.find_children(aid+" rail*","Node3D",true,false): bars.append({"node":node,"home":node.transform})
		var rack: Node3D=model.find_child("form_"+aid+"_rack",true,false)
		if rack!=null: bars.append({"node":rack,"home":rack.transform})
		var frame: Array=[]
		for label in ["form_"+aid+"_gantry","form_"+aid+"_railhead"]:
			var node: Node3D=model.find_child(label,true,false)
			if node!=null: frame.append({"node":node,"home":node.transform})
		var ends: Array=layout["arms"][aid].get("gantry",{}).get("ends",[])
		var pivot := Vector3.ZERO
		for e in ends: pivot+=Vector3(float(e["x_col"]),float(e["foot_y"]),float(e["mast_z"]))
		if ends.size()>0: pivot/=float(ends.size())
		shudder_nodes[aid]={"bars":bars,"frame":frame,"pivot":pivot}

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
		mat.set_shader_parameter("aniso",string_aniso(family))
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
	# the winding (and a gut's twist) runs on continuously over the bridge: each
	# tube tells the shader how much wire came before it, else the ridges restart
	# their phase at every joint and a ring seam shows at the bridge pin
	var wound: float=motion.v(s["a"]).distance_to(motion.v(s["b"]))
	for i in range(points.size()-1):
		var p: Vector3=points[i]; var q: Vector3=points[i+1]; var length: float=p.distance_to(q)
		var node := MeshInstance3D.new(); node.mesh=_wire_mesh(length,radius,4,10)
		node.transform=Transform3D(ClockworkMotion.link_basis(p,q),p)
		var mat := ShaderMaterial.new(); mat.shader=WIRE
		mat.set_shader_parameter("radius",radius); mat.set_shader_parameter("length_m",length)
		mat.set_shader_parameter("offset_m",wound); wound+=length
		mat.set_shader_parameter("albedo",colour); mat.set_shader_parameter("family",family)
		mat.set_shader_parameter("aniso",string_aniso(family))
		mat.set_shader_parameter("sheath",false)
		var zero := PackedFloat32Array(); zero.resize(STRING_NODES)
		mat.set_shader_parameter("disp",zero); mat.set_shader_parameter("envelope",zero)
		node.material_override=mat
		dead.add_child(node)
	# ...and winds on the tuning pin (formlab.layout.pin_wrap): from the contact on
	# the pin's +x side up over the pin, coil beside coil toward the neck, a wire's
	# diameter a turn — or finer, if the room short of the plate is less. The coil is
	# a tube along a helix, not the straight tube the wire shader bends, so it wears
	# a plain material of the wire's colour: metal for wire, matte for gut.
	if s["neck"].has("wrap"):
		var w: Dictionary=s["neck"]["wrap"]; var turns: float=float(w["turns"])
		var R: float=float(w["r"])+radius; var pitch: float=minf(2.0*radius,(float(w["room"])-radius)/turns)
		var pts := PackedVector3Array(); var n := int(ceil(turns*24.0))
		for i in n+1:
			var th := TAU*turns*float(i)/n
			pts.append(Vector3(R*cos(th),R*sin(th),pitch*th/TAU))
		var coil := MeshInstance3D.new(); coil.name=sid+" coil"; coil.mesh=_tube_along(pts,radius,8)
		coil.position=motion.v(w["centre"])
		var pm := StandardMaterial3D.new(); pm.albedo_color=colour
		pm.metallic=1.0 if family<=1 else 0.0; pm.roughness=.35 if family<=1 else (.6 if family==2 else .3)
		coil.material_override=pm
		dead.add_child(coil)
	add_child(dead)

## A tube of the wire's gauge along a polyline (the tuning-pin coil): rings in
## parallel-transported frames, so the tube neither twists nor pinches round the
## turns; the same ring winding as _wire_mesh.
static func _tube_along(points: PackedVector3Array, radius: float, sides: int) -> ArrayMesh:
	var verts := PackedVector3Array(); var norms := PackedVector3Array(); var uvs := PackedVector2Array(); var idx := PackedInt32Array()
	var n := points.size()
	var t0: Vector3=(points[1]-points[0]).normalized()
	var u: Vector3=t0.cross(Vector3.BACK)
	if u.length()<.1: u=t0.cross(Vector3.UP)
	u=u.normalized()
	for j in n:
		var t: Vector3
		if j==0: t=t0
		elif j==n-1: t=(points[j]-points[j-1]).normalized()
		else: t=((points[j]-points[j-1]).normalized()+(points[j+1]-points[j]).normalized()).normalized()
		u=(u-t*u.dot(t)).normalized(); var v: Vector3=u.cross(t)
		for k in sides+1:
			var th := TAU*float(k)/sides; var nrm: Vector3=u*cos(th)+v*sin(th)
			verts.append(points[j]+nrm*radius); norms.append(nrm); uvs.append(Vector2(float(j)/(n-1),float(k)/sides))
	for j in n-1:
		for k in sides:
			var p := j*(sides+1)+k
			idx.append_array([p,p+1,p+sides+1, p+1,p+sides+2,p+sides+1])
	var arrays := []; arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX]=verts; arrays[Mesh.ARRAY_NORMAL]=norms; arrays[Mesh.ARRAY_TEX_UV]=uvs; arrays[Mesh.ARRAY_INDEX]=idx
	var mesh := ArrayMesh.new(); mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	return mesh

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

## How far a family's highlight stretches along the string (the wire shader's
## `aniso`): a winding or a gut's twist grooves the wire around, so the
## reflection runs along it; a plain drawn wire is scratched along its length,
## so its highlight spreads a little across instead; nylon is smooth.
static func string_aniso(family: int) -> float:
	if family==1: return .7
	if family==2: return .45
	if family==3: return 0.0
	return -.3

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
	# gantries and heads with their racks, the servo arms' leadscrews) is not a
	# variant and stays visible.
	for node in model.find_children("form_*","Node3D",true,false):
		var n := String(node.name)
		node.visible=n.ends_with("_"+style) or n.ends_with("_stand") or n.ends_with("_soundboard") or n.ends_with("_actionplate") or n.ends_with("_gantry") or n.ends_with("_railhead") or n.ends_with("_screw")

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
	prev_time=time
	for aid in clicks:
		var i := 0
		while i<clicks[aid].size() and float(clicks[aid][i]["t"])<=time: i+=1
		click_next[aid]=i

## Play every click that landed in (t0, t1]: the clock advanced from t0 to t1.
func _play_clicks(t0: float, t1: float) -> void:
	for aid in clicks:
		var list: Array=clicks[aid]
		var i: int=click_next[aid]
		while i<list.size() and float(list[i]["t"])<=t1:
			if float(list[i]["t"])>t0: click_players[aid].play()
			i+=1
		click_next[aid]=i

## A ratchet's click: the pawl's roller dropping onto the next tooth. A 3 ms
## metallic tick — three inharmonic partials of a small steel part, each rung
## for a couple of milliseconds over a grain of noise — and under it the pawl's
## spring and lever ringing out against the carriage at RING_HZ: a low thump
## that beats at the ring rate and dies in RING_TAU, the ring the carriage's
## overshoot makes in ClockworkMotion.ratchet. Mono 16-bit at `rate`.
static func click_sample(rate: int = 44100) -> AudioStreamWAV:
	var n := int(.12*rate)
	var samples := PackedFloat32Array(); samples.resize(n)
	var rng := RandomNumberGenerator.new(); rng.seed=7
	var peak := 0.0
	for i in n:
		var t := float(i)/rate
		var tick := 0.0
		for p in [[3150.0,1.0],[4720.0,.6],[7060.0,.35]]:
			tick += p[1]*sin(TAU*p[0]*t)*exp(-t/.0012)
		tick += rng.randf_range(-1,1)*exp(-t/.0006)*.8
		var thump := sin(TAU*95.0*t)*exp(-t/ClockworkMotion.RING_TAU)*(1.0+.5*cos(TAU*ClockworkMotion.RING_HZ*t))*.35*(1.0-exp(-t/.002))
		samples[i]=tick+thump
		peak=maxf(peak,absf(samples[i]))
	var data := PackedByteArray(); data.resize(n*2)
	for i in n: data.encode_s16(i*2,int(round(samples[i]/peak*.8*32767.0)))
	var wav := AudioStreamWAV.new()
	wav.format=AudioStreamWAV.FORMAT_16_BITS; wav.mix_rate=rate; wav.stereo=false; wav.data=data
	return wav

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
		# A hinged hammer's head turns on the flange's pin, HEAD_L above the tool
		# frame's origin. The head's mesh is built at the blow (angle 0, the felt
		# face straight down), and the flip is one rotation about the pin axis:
		# -angle*sign, the same rotation ClockworkMotion.head_offset applies to
		# the felt face — which is why the blow lands exactly on the scored point.
		if p.has("head"):
			p["head"].position=pose["tip"]+Vector3(0,ClockworkMotion.HEAD_L,0)
			p["head"].basis=Basis(Vector3.RIGHT,-float(pose["head"])*motion.flip_sign(aid))*head_home[aid]
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
		# A servo arm's leadscrew turns instead: a right-hand thread, so +x travel
		# of the nut is a negative turn about +x, 2π per pitch (formlab.gantry.
		# screw_geometry); the shaft's mesh is in world space, so the spin is
		# taken about the axis line through (0, y, z).
		if screw_nodes.has(aid):
			var sc: Dictionary=cfg["screw"]
			var c := Vector3(0,float(sc["y"]),float(sc["z"]))
			var turn := Basis(Vector3.RIGHT,wrapf(-TAU*root.x/float(sc["pitch"]),-PI,PI))  # wrapped in double first: a Basis takes a 32-bit angle, and a screw 4 m down its rail has turned ~3000 rad
			screw_nodes[aid].transform=Transform3D(turn,c-turn*c)*screw_home[aid]
			continue
		p["gear"].position=root+(Vector3(0,(.17 if mount=="up" else -.17),-.10) if flat else Vector3(0,0,(.195 if mount=="front" else -.195)))
		# A pinion with a pawl is spun with a phase (formlab.pawl.dip_offset) that
		# seats the roller in a dip when the arm parks at its home.
		var phase: float=float(cfg["pawl"].get("phase",0.0)) if cfg.has("pawl") else 0.0
		p["gear"].basis=Basis(Vector3.UP if flat else Vector3(0,0,1),(root.x+phase)/.12)*gear_home[aid]
		# The roller detent pawl (formlab.pawl) hangs on its pivot off the carriage
		# and turns about z so its roller rides the spun teeth: lifted (positive
		# angle) on a tip, dropped into the gap between. The mirror of pawl.angle.
		# The roller sits on the pawl's axle and rolls on the tips: ROLLER_SPIN
		# radians a metre of rail, the other way from the disc.
		if p.has("pawl"):
			var swing := Basis(Vector3(0,0,1),-ClockworkMotion.pawl_angle(root.x+phase))
			p["pawl"].position=root+motion.v(cfg["pawl"]["pivot"])
			p["pawl"].basis=swing*pawl_home[aid]
			p["roller"].position=p["pawl"].position+swing*motion.v(cfg["pawl"]["nose"])
			p["roller"].basis=swing*Basis(Vector3(0,0,1),float(cfg["pawl"].get("roller_spin",0.0))*root.x)*roller_home[aid]
	# The blow shakes the assembly, not only the arm: the stand thumps, the rail
	# sags under the carriage and rings, and the gantry sways about its plinths.
	# All three come off the same recoil bus the arm's own recoil does and are
	# exactly zero at the blow they answer (ClockworkMotion._shudder).
	for mid in stand_nodes:
		var st: Dictionary=stand_nodes[mid]
		var sh: Transform3D=st["home"]
		st["node"].transform=Transform3D(sh.basis,sh.origin+Vector3(0,motion.stand_thump(mid,t),0))
	for aid in shudder_nodes:
		var sh: Dictionary=shudder_nodes[aid]
		var span: Array=motion.rail_span(aid)
		# The guide bars are rigid meshes, so they carry the sag at mid-span; the
		# deflection's SHAPE lives in the carriage, which follows the sag at its
		# own x (ClockworkMotion.pose), so links and pawl move with the bar.
		var sag := motion.rail_sag(aid,t,(span[0]+span[1])/2.0)
		for b in sh["bars"]:
			var bh: Transform3D=b["home"]
			b["node"].transform=Transform3D(bh.basis,bh.origin+Vector3(0,sag,0))
		# A sway is a tilt ACROSS the rail (about world X, through both plinth
		# feet): the braces stiffen the gantry along the rail, and a rotation on
		# that axis gives no mast a lever arm down the span.
		var tilt := Basis(Vector3.RIGHT,motion.mast_sway(aid,t))
		var pivot: Vector3=sh["pivot"]
		for f in sh["frame"]: f["node"].transform=Transform3D(tilt,pivot-tilt*pivot)*f["home"]
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
	# --focus=<aid> overrides every view: frame one arm's own mechanism so a clip
	# reads the carriage, the rack, the pawl and the tool rather than the room.
	#
	# An arm is about a metre from its carriage down to its tool, and a click
	# close-up has to hold BOTH ends — the pawl riding the pinion at the top and
	# the mallet's cocked drop at the bottom. So the frame covers the arm's own
	# root-to-tip box with a margin and `--focus_span` is a MINIMUM width, not
	# the answer: narrowing it past the arm's height only centres the shot
	# tighter, it cannot crop the tool out.
	#
	# Which side to stand on is not free either. The arms work behind their
	# instrument's string plane (see view 9), so the camera stands on the far
	# side of the carriage from the instrument's centre — otherwise a pick arm's
	# close-up is a picture of the strings it is hiding behind. `--focus_dir`
	# overrides the direction when a shot wants a particular angle.
	if focus!="" and layout.get("arms",{}).has(focus):
		var cfg: Dictionary=layout["arms"][focus]
		var pose := motion.pose(focus,t)
		var root: Vector3=pose["root"]; var tip: Vector3=pose["tip"]
		target=(root+tip)/2.0
		var size := get_viewport().get_visible_rect().size
		var aspect: float=size.x/maxf(size.y,1.0)
		var tan_half: float=maxf(tan(deg_to_rad(camera.fov)/2.0),.001)
		var half_w: float=maxf(focus_span,absf(root.x-tip.x)+.30)/2.0
		var half_h: float=(absf(root.y-tip.y)+.30)/2.0
		# --focus_at=tip (or root, or head — a hinged hammer's pin, HEAD_L above the
		# tool frame's origin) drops the whole-arm box and frames ONE end of
		# it, and then --focus_span is the frame's true width rather than a
		# minimum: a hinged hammer's head is 200 mm of mechanism on the end of a
		# 1.6 m arm, and no shot that holds the carriage can also show the check
		# catch the rebound.
		if focus_at!="":
			target=tip if focus_at=="tip" else root
			if focus_at=="head": target=tip+Vector3(0,ClockworkMotion.HEAD_L,0)   # a hinged head's pin
			half_w=focus_span/2.0; half_h=focus_span/2.0
		# The floor of 0.8 m is what keeps a whole-arm --focus shot outside the
		# mechanism; a --focus_at close-up asks to be inside it, so it gets the
		# camera's own near plane as its floor instead.
		var distance: float=maxf(maxf(half_w/(tan_half*aspect),half_h/tan_half),.8 if focus_at=="" else .30)
		var dir := focus_dir
		if dir==Vector3.ZERO:
			var mid: String=str(cfg.get("mid",""))
			var away := Vector3(0,0,1)
			if layout.get("mechanisms",{}).has(mid):
				var c := motion.v(layout["mechanisms"][mid]["center"])
				away=Vector3(root.x-c.x,0,root.z-c.z)
				if away.length()<.05: away=Vector3(0,0,1)
			dir=(away.normalized()+Vector3(0,.18,0)).normalized()
		camera.look_at_from_position(target+dir.normalized()*distance,target,Vector3.UP)
		return
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
	elif chosen==16:
		# A wound bass string at arm's length: the harp's lowest string a hand above
		# its eyelet, from the string side, for the winding, the highlight along the
		# wire and the darkening at the hardware (shaders/wire_string.gdshader).
		var low := ""; var low_midi := 1e9
		for sid in layout["strings"]:
			var s: Dictionary=layout["strings"][sid]
			if s["mid"]=="harp" and float(s["midi"])<low_midi: low=sid; low_midi=float(s["midi"])
		if low=="":
			for sid in layout["strings"]: low=sid; break
		var a: Vector3=motion.v(layout["strings"][low]["a"]); var b: Vector3=motion.v(layout["strings"][low]["b"])
		target=a+(b-a)*.12; pos=target+Vector3(.16,.05,-.28)
	elif chosen==15:
		# The ratchet's mechanism: the first mallet arm's pinion from behind and
		# below, with the roller detent pawl under it (formlab.pawl) and the rack above.
		var aid: String=""
		for a in layout["arms"]:
			if layout["arms"][a].has("pawl"): aid=a; break
		if aid=="": aid=layout["arms"].keys()[0]
		var pose := motion.pose(aid,t); var mount: String=str(layout["arms"][aid].get("pinion","back"))
		var disc: Vector3=pose["root"]+Vector3(0,0,(.195 if mount=="front" else -.195))
		target=disc+Vector3(.03,-.09,0); pos=target+Vector3(.55,-.25,-.85 if mount=="back" else .85)
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
	if capture_dir!="": time=capture_start+frame*capture_speed/capture_fps
	# The clicks that landed since the last frame sound now; a shot or a capture
	# (no audio) and --silent (no audio at all) stay quiet like the master does.
	if playing and not silent and shot=="" and capture_dir=="": _play_clicks(prev_time,time)
	prev_time=time
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
		if shot!="" or frame>=int(capture_seconds*capture_fps/capture_speed): get_tree().quit()

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
