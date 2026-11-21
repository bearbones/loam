extends "res://performance_capture.gd"
## Clockwork performance, with the original 2D harness retained as main.tscn.
## Every moving part of one arm, as named in the GLB (aid + "__" + part). The
## parallelogram pairs (upper/upper2, lower/lower2) and the crossheads
## (carriage, elbowhead, wristhead) are posed from the same IK as the pins.
const PART_NAMES := ["carriage","upper","upper2","lower","lower2","elbowhead","wristhead","shoulder","elbow","wrist","tool","shank"]
var screw_nodes: Dictionary = {} # each servo arm's leadscrew shaft (form_<aid>_screw), spun about its axis
var screw_home: Dictionary = {}  # ...and its imported transform
var score := ScoreDoc.new()
var motion := MotionBake.new()
# preloaded by path, not named by class: a .godot class cache from before
# MotionRig existed (a checkout merged without --import) still parses this
const MotionRigScript := preload("res://motion_rig.gd")
var rig: MotionRigScript         # every moving part posed from the bake's joints table (MotionRig.apply)
var look := ClockworkLook.new()
var layout: Dictionary
var model: Node3D
var parts: Dictionary = {}
var gear_home: Dictionary = {}   # each pinion's imported basis: the disc in its mount's plane, unspun
var pawl_home: Dictionary = {}   # each mallet arm's roller detent pawl (formlab.pawl), imported basis
var roller_home: Dictionary = {} # the pawl's roller, imported basis
var wheel_home: Dictionary = {}  # the flywheel, hub and pulleys: node -> imported basis, unspun
var flywheel_pinion: Node3D = null # the flywheel's 16-tooth companion pinion
var flywheel_pinion_home := Basis.IDENTITY
var head_home: Dictionary = {}   # each hinged hammer's head (formlab.linkage.hammer_tool), imported basis
var drive_parts: Dictionary = {} # aid -> extra M4/M5 drive parts (shoulder_sector, shoulder_pinion, elbow_crank, elbow_rod, ...)
var spinion_home: Dictionary = {} # each arm's shoulder driver pinion imported basis
var wshaft_home: Dictionary = {}  # each mallet arm's hinged wrist shaft imported basis
var m2head_home: Dictionary = {}  # each two-mallet holder's second felt head imported basis
var m2shaft_home: Dictionary = {} # each two-mallet holder's second rosewood shaft imported basis
var splay_home: Dictionary = {}   # each two-mallet holder's splay sector gear imported basis
var hcam_home: Dictionary = {}    # each hammer arm's lift cam imported basis
var parm_home: Dictionary = {}    # each rake arm's pendulum forearm imported basis
var psec_home: Dictionary = {}    # each rake arm's pendulum sector gear imported basis
var ppin_home: Dictionary = {}    # each rake arm's pendulum driver pinion imported basis
var sheath_active: Dictionary = {} # periodic-feature blur sheath hysteresis state (key -> bool)
var stand_nodes: Dictionary = {}    # mid -> the instrument's stand and its imported home
var shudder_nodes: Dictionary = {}  # aid -> the rail's bars and the gantry it stands on, and the sway pivot
var strings: Dictionary = {}
const StringMotion := preload("res://string_motion.gd")
const HandMotion := preload("res://hand_motion.gd")
var wire_motion: Dictionary = {}
const StruckMotion := preload("res://struck_motion.gd")
var struck_motion: Array[StruckMotion] = []
var hand_motion: Dictionary = {}
const PillarPlayer = preload("res://pillar_player.gd")
var pillar_players: Dictionary = {}
var harp_owner: Dictionary = {}
const MalletGrip := preload("res://mallet_grip.gd")
var mallet_grips: Dictionary = {}
const INSPECTION_FOV := 43.0
var camera: Camera3D
var player: AudioStreamPlayer
var stem_players: Array = []
var time := -1.0
var playing := true
var auto_camera := true
var view := 0
var form_style := "carved"
const PerformanceHud := preload("res://performance_hud.gd")
var hud: PerformanceHud
var focus := ""                  # --focus=<aid>: frame that arm's mechanism, not the room
var focus_pick: Variant = null
var focus_span := 2.4            # metres of rail across the frame (a minimum)
var focus_dir := Vector3.ZERO    # --focus_dir=x,y,z: stand-off direction; zero = derive it
var focus_at := ""               # --focus_at=tip|root|head: frame THAT point, focus_span the true width
var clock_started := false
var silent := false
var audio_mode := "master"
var bass_string := ""
var follow_sid := ""
var follow_since := -1e9
# The ratchet's click has a sound (docs/plans/pawl-follow-ups.md, item 2): one
# sample, synthesised once, played from each pawl's roller at every click the
# rig makes (the bake's clicks, formlab.rig.Rig.click_times), CLICK_DB under the instruments.
# A stepped (or homing) landing and every hammer click plays the sample once on
# the arm's click player, as it always has. A mallet's freewheel clicks a tooth,
# 11.9 ms apart at its fastest — closer than a frame — so the clicks that fall
# in one rendered frame play as ONE voice on the arm's freewheel player, louder
# by their count (an incoherent sum: +10·log10 of the summed power); a click
# whose pawl rides the tips is the lighter ride tick, RIDE_DB under a drop.
const CLICK_DB := -12.0
const RIDE_DB := -9.0              # a ride click against a drop click
const CLICK_VOICES := 4            # each click player's polyphony
var click_stream: AudioStreamWAV
var ride_stream: AudioStreamWAV    # the roller ticking over a tip: no drop, no thump
var clicks: Dictionary = {}        # aid -> the arm's clicks, in time order
var click_times: Dictionary = {}    # aid -> packed times for random-access seeks
var click_players: Dictionary = {} # aid -> AudioStreamPlayer3D on the roller
var wheel_players: Dictionary = {} # aid -> a mallet's freewheel player on the roller (AudioStreamPolyphonic)
var click_next: Dictionary = {}    # aid -> index of the first click not yet played
var prev_time := -1.0
var _posed_time := -INF
var _camera_view := -2
var _camera_viewport := Vector2.ZERO
# --film: the piece as a film (FilmDirector): a camera and a lighting arc
# directed from the score's cues, no UI, a title and an end card.
var film := false
var director := FilmDirector.new()
var film_cards: Array = []   # [Control, t_in, t_out]

func _ready() -> void:
	if OS.get_cmdline_user_args().has("--drums"):
		get_tree().call_deferred("change_scene_to_file","res://drum_recital.tscn")
		return
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
	# The performance is baked (formlab/bake.py): the harness plays the rig's
	# motion back and owns none of it. A bake made from another score or
	# another model is refused, with the command that remakes it.
	if not motion.load(option("motion",MotionBake.path_for(score_path,asset)),score_path,manifest_path):
		push_error(str(motion.errors)); get_tree().quit(1); return
	film=OS.get_cmdline_user_args().has("--film")
	director.setup(motion,layout,score)
	model=load("res://assets/"+asset+".glb").instantiate()
	add_child(model)
	look.apply(model,layout["strings"])
	form_style=option("form","carved")
	_set_form(form_style)
	for aid in layout["arms"]:
		if layout["arms"][aid].has("pillar_player"):
			pillar_players[aid] = PillarPlayer.new()
			continue
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
		# (formlab.linkage.hammer_tool, formlab.rig.Rig.head_angle).
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
			if click_stream==null: click_stream=click_sample(motion.constant("RING_HZ"),motion.constant("RING_TAU"))
			clicks[aid]=motion.click_times(aid)
			var times := PackedFloat64Array()
			for click in clicks[aid]: times.append(click["t"])
			click_times[aid] = times
			var cp := AudioStreamPlayer3D.new()
			cp.name="click"; cp.stream=click_stream; cp.volume_db=CLICK_DB
			cp.attenuation_model=AudioStreamPlayer3D.ATTENUATION_DISABLED; cp.max_polyphony=CLICK_VOICES
			parts[aid]["roller"].add_child(cp); click_players[aid]=cp; click_next[aid]=0
			# a stepped arm's freewheel: one voice a frame, each with its own sample and gain
			if motion.stepped(aid):
				if ride_stream==null: ride_stream=ride_sample()
				var poly := AudioStreamPolyphonic.new(); poly.polyphony=CLICK_VOICES
				var wp := AudioStreamPlayer3D.new()
				wp.name="freewheel"; wp.stream=poly; wp.volume_db=CLICK_DB
				wp.attenuation_model=AudioStreamPlayer3D.ATTENUATION_DISABLED
				parts[aid]["roller"].add_child(wp); wheel_players[aid]=wp
		# Carriage-mounted shoulder sector gear + driver pinion, four-bar elbow crank + coupler rod (M4),
		# and M5 hinged mallet shaft + four-bar wrist crank and hammer lift cam (formlab.drives).
		drive_parts[aid]={}
		for dpart in ["shoulder_sector","shoulder_pinion","elbow_crank","elbow_rod","wrist_shaft","wrist_crank","wrist_rod","wrist_guide","wrist_plunger","mallet2_head","mallet2_shaft","splay_sector","hammer_cam","pendulum_arm","pendulum_sector","pendulum_pinion","digit_thumb","digit_d2","digit_d3","digit_d4"]:
			var dnode: Node3D=model.find_child(aid+"__"+dpart,true,false)
			if dnode!=null:
				drive_parts[aid][dpart]=dnode
				if dpart=="shoulder_pinion": spinion_home[aid]=dnode.basis
				elif dpart=="wrist_shaft": wshaft_home[aid]=dnode.basis
				elif dpart=="mallet2_head": m2head_home[aid]=dnode.basis
				elif dpart=="mallet2_shaft": m2shaft_home[aid]=dnode.basis
				elif dpart=="splay_sector": splay_home[aid]=dnode.basis
				elif dpart=="hammer_cam": hcam_home[aid]=dnode.basis
				elif dpart=="pendulum_arm": parm_home[aid]=dnode.basis
				elif dpart=="pendulum_sector": psec_home[aid]=dnode.basis
				elif dpart=="pendulum_pinion": ppin_home[aid]=dnode.basis
		if drive_parts[aid].has("mallet2_head"):
			var grip := MalletGrip.new()
			grip.bind(parts[aid],model.find_child(aid+"__inner_slide",true,false),motion.arms[aid]["splay"])
			mallet_grips[aid] = grip
		if layout["arms"][aid]["kind"] in ["pick","rake"] and drive_parts[aid].has("wrist_rod"):
			var hand := HandMotion.new()
			hand.bind(drive_parts[aid], layout["arms"][aid], motion.arms[aid].get("hand_pose", {}))
			hand_motion[aid] = hand
	# The chamber's flywheel, its axle pulley, companion pinion and the belt pulley turn about z
	# (formlab.layout.flywheel_plan); their imported bases are the unspun home.
	for label in ["Chamber flywheel","Chamber hub","Chamber drive pulley","Chamber belt pulley"]:
		var node: Node3D=model.find_child(label,true,false)
		if node!=null: wheel_home[node]=node.basis
	flywheel_pinion=model.find_child("Chamber flywheel pinion",true,false)
	if flywheel_pinion!=null: flywheel_pinion_home=flywheel_pinion.basis
	_assembly_nodes()
	# The joints table's body rows bound to the model: what evaluate() poses.
	# The lookups above stay as views of the same nodes (test_performance reads
	# them) and own the click players.
	rig=MotionRigScript.new()
	if not rig.bind(motion,model): push_error(str(rig.errors)); get_tree().quit(1); return
	var hits := {}
	var low_midi := INF
	for sid in layout["strings"]:
		var spec: Dictionary = layout["strings"][sid]
		if bass_string == "" or (spec["mid"] == "harp" and float(spec["midi"]) < low_midi):
			bass_string = sid
			if spec["mid"] == "harp": low_midi = float(spec["midi"])
		hits[sid]=[]
		if not layout["strings"][sid]["struck"]:
			strings[sid]=_make_string(sid)
	for e in score.events:
		var ts: Array=ScoreDoc.string_times(e)   # a rake roll's at its own onsets
		for k in range(e.get("strings",[]).size()):
			var sid: String=e["strings"][k]
			hits[sid].append({"t":ts[k],"event":e})
			if pillar_players.has(e["actuator"]): harp_owner[sid]=e["actuator"]
	for sid in strings:
		var wire := StringMotion.new()
		wire.bind(strings[sid], layout["strings"][sid], hits[sid], score, layout["arms"])
		wire_motion[sid] = wire
	for sid in layout["strings"]:
		var spec: Dictionary = layout["strings"][sid]
		if not spec["struck"]: continue
		var suffix := " bell" if layout["mechanisms"][spec["mid"]]["material"]=="glass" else " bar"
		var body := model.find_child(sid+suffix,true,false) as MeshInstance3D
		if body == null or body.get_blend_shape_count()==0: continue
		var voice := StruckMotion.new()
		voice.bind(body,spec,hits[sid])
		struck_motion.append(voice)
	for aid in pillar_players:
		pillar_players[aid].bind(model,aid,layout["arms"][aid],score.events,layout,wire_motion)
	for aid in hand_motion:
		hand_motion[aid].seat(parts[aid], aid, score.events, layout, wire_motion, motion)
	_environment()
	player=AudioStreamPlayer.new()
	add_child(player)
	var master_path := score.dir.path_join("chamber.wav")
	if FileAccess.file_exists(master_path):
		player.stream=AudioStreamWAV.load_from_file(master_path)
	else:
		audio_mode="stems"
	for mid in score.stem_ids():
		var p := AudioStreamPlayer.new(); p.stream=score.stems[mid]; add_child(p); stem_players.append(p)
	var ssaa := configure_capture(48.,45.5,8.)
	focus=option("focus","")
	focus_span=maxf(float(option("focus_span","2.4")),.1)
	focus_at=option("focus_at","")
	if option("focus_pick","")!="": focus_pick = float(option("focus_pick",""))
	var fd: PackedStringArray=option("focus_dir","").split(",",false)
	if fd.size()==3: focus_dir=Vector3(float(fd[0]),float(fd[1]),float(fd[2]))
	view=int(option("view","0"))
	auto_camera=option("camera","manual" if option("view","")!="" else "auto")=="auto"
	silent=OS.get_cmdline_user_args().has("--silent")
	if shot!="": playing=false; time=fixed_time
	if capture_dir!="":
		playing=false; time=capture_start
	_ui(ssaa if capture_target_size != Vector2i.ZERO else 1)
	print("CLOCKWORK: loaded ",score.events.size()," events, ",parts.size()+pillar_players.size()," rigs; ",audio_mode," audio")

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
const STRING_NODES := StringMotion.NODES

## A string is a static shaded tube along its own +Y (z = the pluck direction,
## world Z). The wire shader bends it each frame from the baked shape frames;
## a second, translucent copy is a sheath widened to the recent peak excursion —
## the blur a vibrating wire actually presents to the eye. Gauge follows pitch
## (a display gauge: true wire would be sub-pixel) and the strings are strung by
## register as a harp is (string_family), C strings red and F strings dark.
func _make_string(sid: String) -> Node3D:
	var s: Dictionary=layout["strings"][sid]
	var a := MotionBake.v(s["a"]); var b := MotionBake.v(s["b"])
	var length := a.distance_to(b)
	var midi := float(s["midi"])
	var radius := .0035*pow(2.0,(64.0-midi)/18.0)
	var family := string_family(midi)
	var holder := Node3D.new(); holder.name=sid+" string"
	holder.transform=Transform3D(MotionBake.link_basis(a,b),a)
	var colour := string_colour(s["mid"],midi,family)
	var mesh := _wire_mesh(length,radius,48,16)
	for sheath in [false,true]:
		var node := MeshInstance3D.new(); node.mesh=mesh
		var mat := ShaderMaterial.new(); mat.shader=WIRE
		mat.set_shader_parameter("radius",radius); mat.set_shader_parameter("length_m",length)
		mat.set_shader_parameter("albedo",colour); mat.set_shader_parameter("family",family)
		mat.set_shader_parameter("aniso",string_aniso(family))
		mat.set_shader_parameter("cross_axis",2.0 if str(s.get("mid",""))=="harp" else 0.35)
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
	var points: Array=[MotionBake.v(s["b"]),MotionBake.v(s["neck"]["bridge"]),MotionBake.v(s["neck"]["pin"])]
	# the winding (and a gut's twist) runs on continuously over the bridge: each
	# tube tells the shader how much wire came before it, else the ridges restart
	# their phase at every joint and a ring seam shows at the bridge pin
	var wound: float=MotionBake.v(s["a"]).distance_to(MotionBake.v(s["b"]))
	for i in range(points.size()-1):
		var p: Vector3=points[i]; var q: Vector3=points[i+1]; var length: float=p.distance_to(q)
		var node := MeshInstance3D.new(); node.mesh=_wire_mesh(length,radius,4,10)
		node.transform=Transform3D(MotionBake.link_basis(p,q),p)
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
		coil.position=MotionBake.v(w["centre"])
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
	return motion.joint_value("chamber/flywheel",t)

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
		node.visible=n.ends_with("_"+style) or n.ends_with("_stand") or n.ends_with("_soundboard") or n.ends_with("_actionplate") or n.ends_with("_tracery") or n.ends_with("_gantry") or n.ends_with("_railhead") or n.ends_with("_screw") or n.ends_with("_rack")

func _environment() -> void:
	look.light_rig(self)
	camera=Camera3D.new(); camera.fov=INSPECTION_FOV; add_child(camera); camera.current=true

func _ui(pixel_scale: int) -> void:
	if film: _film_cards()
	if film or OS.get_cmdline_user_args().has("--clean"): return
	var canvas := CanvasLayer.new()
	add_child(canvas)
	canvas.scale = Vector2.ONE * pixel_scale
	hud = PerformanceHud.new()
	canvas.add_child(hud)
	var layout_hud := func():
		hud.size = get_viewport().get_visible_rect().size / pixel_scale
	layout_hud.call()
	get_viewport().size_changed.connect(layout_hud)
	hud.bind(score)
	hud.seek_requested.connect(_seek)
	hud.command_requested.connect(_command)
	hud.camera_selected.connect(func(index: int):
		auto_camera = index < 0
		view = maxi(index, 0))

func _seek(t: float) -> void:
	time=clampf(t,-1,score.total_s); clock_started=false
	follow_sid = ""
	player.stop()
	for p in stem_players: p.stop()
	prev_time=time
	for aid in clicks:
		var times: PackedFloat64Array = click_times[aid]
		click_next[aid] = times.bsearch(time, false)

## Play every click that landed in (t0, t1]: the clock advanced from t0 to t1.
## A stepped click (and every hammer click) plays once on the click player; the
## frame's freewheel clicks play as one voice (click_frame, freewheel_voice).
func _play_clicks(t0: float, t1: float) -> void:
	for aid in clicks:
		var next: int = click_next[aid]
		var times: PackedFloat64Array = click_times[aid]
		if next >= times.size() or times[next] > t1: continue
		var f := click_frame(clicks[aid],next,t0,t1)
		click_next[aid]=f["next"]
		for k in int(f["stepped"]): click_players[aid].play()
		var v := freewheel_voice(int(f["drop"]),int(f["ride"]))
		if v.is_empty() or not wheel_players.has(aid): continue
		var wp: AudioStreamPlayer3D=wheel_players[aid]
		if not wp.playing: wp.play()
		var pb := wp.get_stream_playback() as AudioStreamPlaybackPolyphonic
		if pb!=null: pb.play_stream(ride_stream if v["ride"] else click_stream,0.0,float(v["db"]))

## The clicks of `list` (MotionBake.click_times) from index i that fall in the
## frame (t0, t1]: {next, stepped, drop, ride} — the index past the frame, the
## stepped clicks (one voice each), and the freewheel clicks by pawl state.
static func click_frame(list: Array, i: int, t0: float, t1: float) -> Dictionary:
	var out := {"next": i, "stepped": 0, "drop": 0, "ride": 0}
	while i<list.size() and float(list[i]["t"])<=t1:
		var c: Dictionary=list[i]
		if float(c["t"])>t0:
			if int(c.get("step",1))==1: out["stepped"]+=1
			elif int(c.get("pawl",0))==1: out["ride"]+=1
			else: out["drop"]+=1
		i+=1
	out["next"]=i
	return out

## One frame's freewheel clicks as a single voice: {} for none; else {ride, db}
## — the ride tick when every click rode the tips, the drop click when any
## dropped — and its gain over CLICK_DB, the clicks' summed power (a ride click
## RIDE_DB under a drop) against the sample it plays.
static func freewheel_voice(drop: int, ride: int) -> Dictionary:
	if drop+ride<=0: return {}
	var ride_power := pow(10.0,RIDE_DB/10.0)
	if drop==0: return {"ride": true, "db": RIDE_DB+10.0*log(float(ride))/log(10.0)}
	return {"ride": false, "db": 10.0*log(float(drop)+float(ride)*ride_power)/log(10.0)}

## The roller ticking over a tooth's tip while the pawl rides: the click's
## metallic tick alone — no drop into the gap, so no spring thump — 20 ms long
## so a freewheel's frame-a-voice clicks never pile past the polyphony.
static func ride_sample(rate: int = 44100) -> AudioStreamWAV:
	var n := int(.02*rate)
	var samples := PackedFloat32Array(); samples.resize(n)
	var rng := RandomNumberGenerator.new(); rng.seed=11
	var peak := 0.0
	for i in n:
		var t := float(i)/rate
		var tick := 0.0
		for p in [[3150.0,1.0],[4720.0,.6],[7060.0,.35]]:
			tick += p[1]*sin(TAU*p[0]*t)*exp(-t/.0009)
		tick += rng.randf_range(-1,1)*exp(-t/.0004)*.6
		samples[i]=tick
		peak=maxf(peak,absf(samples[i]))
	var data := PackedByteArray(); data.resize(n*2)
	for i in n: data.encode_s16(i*2,int(round(samples[i]/peak*.8*32767.0)))
	var wav := AudioStreamWAV.new()
	wav.format=AudioStreamWAV.FORMAT_16_BITS; wav.mix_rate=rate; wav.stereo=false; wav.data=data
	return wav

## A ratchet's click: the pawl's roller dropping onto the next tooth. A 3 ms
## metallic tick — three inharmonic partials of a small steel part, each rung
## for a couple of milliseconds over a grain of noise — and under it the pawl's
## spring and lever ringing out against the carriage at RING_HZ: a low thump
## that beats at the ring rate and dies in RING_TAU, the ring the carriage's
## overshoot makes in formlab.rig.ratchet (the bake's RING_HZ / RING_TAU).
## Mono 16-bit at `rate`.
static func click_sample(ring_hz: float, ring_tau: float, rate: int = 44100) -> AudioStreamWAV:
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
		var thump := sin(TAU*95.0*t)*exp(-t/ring_tau)*(1.0+.5*cos(TAU*ring_hz*t))*.35*(1.0-exp(-t/.002))
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

## Periodic-feature blur sheath hysteresis (Rule 18): turns on when |dtheta| > 0.5*P
## and stays on until |dtheta| < 0.45*P (10% hysteresis).
static func sheath_step(dtheta_deg: float, period_deg: float, was_on: bool) -> bool:
	var a := absf(dtheta_deg)
	var hi := 0.5*period_deg
	return a>=0.9*hi if was_on else a>hi

func evaluate(t: float) -> void:
	# Every moving part of the model (the arms' links, crossheads, pinions,
	# pawls and rollers, the leadscrews, the hinged heads, the stands, the
	# rails and gantries the blows shake, the flywheel and its pulleys) is
	# posed from the bake's joints table: formlab/kinematics.py holds each row and
	# its law, MotionRig.apply writes the bound nodes.
	rig.apply(t)
	for voice in struck_motion:
		voice.apply(t)
	for sid in wire_motion:
		wire_motion[sid].apply(t)
	for aid in pillar_players:
		pillar_players[aid].apply(t)
	for aid in drive_parts:
		var pose := motion.pose(aid,t)
		var p: Dictionary=drive_parts[aid]
		var cfg: Dictionary=layout["arms"][aid]
		var root: Vector3=pose["root"]; var elbow: Vector3=pose["elbow"]; var wrist: Vector3=pose["wrist"]
		var upper := MotionBake.link_basis(root,elbow)
		# Shoulder sector gear & driver pinion (formlab.drives.SHOULDER_DRIVE, M4):
		if p.has("shoulder_sector"):
			p["shoulder_sector"].transform=Transform3D(upper,root)
		if p.has("shoulder_pinion"):
			var sh_drv: Dictionary=cfg.get("drives",{}).get("shoulder",{})
			var pin_o := MotionBake.v(sh_drv.get("pinion_origin",[0.0,0.0,-0.084]))
			var q_sh := atan2(elbow.y-root.y,elbow.z-root.z)
			var ratio_sh := float(sh_drv.get("ratio",-2.0))
			p["shoulder_pinion"].position=root+pin_o
			p["shoulder_pinion"].basis=Basis(Vector3.RIGHT,ratio_sh*q_sh)*spinion_home[aid]
		# Four-bar elbow crank & coupler rod (formlab.drives.four_bar_crank, M4):
		if p.has("elbow_crank") and p.has("elbow_rod"):
			var el_drv: Dictionary=cfg.get("drives",{}).get("elbow",{})
			var rc := float(el_drv.get("r_crank",0.080)); var rf := float(el_drv.get("r_lug",0.080))
			var u_vec := elbow-root; var f_vec := wrist-elbow
			var l1_len := u_vec.length(); var v_hat := f_vec.normalized()
			var p2 := elbow+rf*v_hat; var d_vec := p2-root
			var d_yz := Vector2(d_vec.y,d_vec.z).length()
			var l_yz2 := l1_len*l1_len-d_vec.x*d_vec.x
			var cos_a := clampf((rc*rc+d_yz*d_yz-l_yz2)/maxf(2.0*rc*d_yz,1e-9),-1.0,1.0)
			var alpha := acos(cos_a); var phi := atan2(d_vec.y,d_vec.z)
			var sgn := -1.0 if (u_vec.y*v_hat.z-u_vec.z*v_hat.y)>=0.0 else 1.0
			var th_c := phi+sgn*alpha
			var p1 := Vector3(root.x,root.y+rc*sin(th_c),root.z+rc*cos(th_c))
			p["elbow_crank"].transform=Transform3D(MotionBake.link_basis(root,p1),root)
			p["elbow_rod"].transform=Transform3D(MotionBake.link_basis(p1,p2),p1)
		# Hinged mallet shaft & four-bar wrist crank (formlab.drives.four_bar_wrist, M5):
		if p.has("wrist_shaft") and p.has("wrist_crank") and p.has("wrist_rod"):
			var wr_drv: Dictionary=cfg.get("drives",{}).get("hinge",{})
			var rc_w := float(wr_drv.get("r_crank",0.180)); var rf_w := float(wr_drv.get("r_lug",0.140)); var lr_w := float(wr_drv.get("coupler_l",0.220))
			var sgn_w := motion.flip_sign(aid); var th_w := float(pose["head"])
			var stick := Basis(Vector3.RIGHT,sgn_w*th_w)
			var face: Vector3 = pose["tip"]
			if mallet_grips.has(aid):
				var grip: MalletGrip = mallet_grips[aid]
				grip.apply(t,face,th_w,sgn_w)
				if p.has("wrist_guide"):
					var cheek := Vector3(-.122,0,0)
					p["wrist_guide"].transform=Transform3D(MotionBake.link_basis(wrist,grip.hinge),wrist+cheek)
					p["wrist_plunger"].transform=Transform3D(MotionBake.link_basis(grip.hinge,wrist),grip.hinge+cheek)
				stick = grip.swing_a
				face = grip.head_a
				p["mallet2_head"].transform = Transform3D(m2head_home[aid],grip.head_b)
				p["mallet2_shaft"].transform = Transform3D(grip.swing_b*m2shaft_home[aid],grip.head_b)
				p["splay_sector"].transform = Transform3D(Basis(Vector3.UP,grip.dial)*splay_home[aid],grip.hinge)
			p["wrist_shaft"].transform = Transform3D(stick*wshaft_home[aid],face)
			var p2_w := face+stick*Vector3(0,0,sgn_w*rf_w)
			var d_w := p2_w-wrist; var d_wyz := Vector2(d_w.y,d_w.z).length()
			var l_wyz2 := lr_w*lr_w-d_w.x*d_w.x
			var cos_aw := clampf((rc_w*rc_w+d_wyz*d_wyz-l_wyz2)/maxf(2.0*rc_w*d_wyz,1e-9),-1.0,1.0)
			var th_cw := atan2(d_w.y,d_w.z)+sgn_w*acos(cos_aw)
			var p1_w := Vector3(wrist.x,wrist.y+rc_w*sin(th_cw),wrist.z+rc_w*cos(th_cw))
			p["wrist_crank"].transform=Transform3D(MotionBake.link_basis(wrist,p1_w),wrist)
			p["wrist_rod"].transform=Transform3D(MotionBake.link_basis(p1_w,p2_w),p1_w)
		elif p.has("wrist_crank") and p.has("wrist_rod"):
			var wf_drv: Dictionary=cfg.get("drives",{}).get("wrist_flex",{})
			var cl_w := float(wf_drv.get("carrier_l",0.50))
			var mo_w := MotionBake.v(wf_drv.get("mount_offset",[0.0,0.20,-0.10]))
			var hand: HandMotion = hand_motion[aid]
			var p2_w := hand.apply(t,pose["tip"])+mo_w
			var pin := wrist+hand.swivel_offset
			var line := p2_w-pin
			var along := line.normalized()
			# Swing the swivel's rest frame to the socket. Its outboard offset
			# keeps this direction in the forward hemisphere at full fold.
			var ref := hand.fold_direction
			var axis := hand.swivel_axis
			var bend := ref-(along+axis)*(along.dot(ref)/maxf(1.+along.dot(axis),1e-6))
			if axis==Vector3.ZERO:
				bend = Vector3(0,along.z,-along.y).normalized()
				if along.z+2.*along.y<0.: bend = -bend
			var height := sqrt(maxf(0.,cl_w*cl_w-.25*line.length_squared()))
			var knee := .5*(pin+p2_w)+height*bend
			var axle := bend.cross(along).normalized()
			p["wrist_crank"].transform=Transform3D(MotionBake.link_basis(pin,knee,axle),pin)
			p["wrist_rod"].transform=Transform3D(MotionBake.link_basis(knee,p2_w,axle),knee)
		# Hammer lift cam (formlab.drives.HAMMER_CAM, M5):
		if p.has("hammer_cam"):
			var hc_drv: Dictionary=cfg.get("drives",{}).get("hinge",{})
			var cam_o := MotionBake.v(hc_drv.get("cam_origin",[0.0,0.31,0.036]))
			var ratio_hc := float(hc_drv.get("ratio",2.0))
			p["hammer_cam"].position=pose["tip"]+cam_o
			p["hammer_cam"].basis=Basis(Vector3.RIGHT,-ratio_hc*float(pose["head"])*motion.flip_sign(aid))*hcam_home[aid]
		# Rake pendulum forearm, sector gear & driver pinion (formlab.drives.PENDULUM_DRIVE, M9):
		if p.has("pendulum_arm") and p.has("pendulum_sector") and p.has("pendulum_pinion"):
			var pd_drv: Dictionary=cfg.get("drives",{}).get("pendulum",{})
			var pin_o := MotionBake.v(pd_drv.get("pinion_origin",[0.0,0.084,-0.045]))
			var ratio_pd := float(pd_drv.get("ratio",-2.0))
			var th_pd := 0.22*root.x
			p["pendulum_arm"].position=wrist
			p["pendulum_arm"].basis=Basis(Vector3.BACK,th_pd)*parm_home[aid]
			p["pendulum_sector"].position=wrist
			p["pendulum_sector"].basis=Basis(Vector3.BACK,th_pd)*psec_home[aid]
			p["pendulum_pinion"].position=wrist+pin_o
			p["pendulum_pinion"].basis=Basis(Vector3.BACK,ratio_pd*th_pd)*ppin_home[aid]
	if flywheel_pinion!=null and layout.has("flywheel") and layout["flywheel"].has("mate"):
		var spin: float=flywheel_angle(t)
		var k: float=float(layout["flywheel"]["mate"]["ratio"])
		flywheel_pinion.basis=Basis(Vector3(0,0,1),spin*k)*flywheel_pinion_home
	look.breathe(score.envelope_at("chamber",t))
	if film: _film_frame(t)
	_camera_at(t)

## One film frame's lighting and cards (the camera is _camera_at's).
func _film_frame(t: float) -> void:
	var l := director.light_at(t)
	look.env.tonemap_exposure=l["exposure"]; look.env.fog_density=l["fog"]
	look.key_light.light_energy=1.3*l["key"]; look.fill_light.light_energy=1.2*l["fill"]; look.rim_light.light_energy=l["rim"]
	for card in film_cards:
		var fade := clampf((t-float(card[1]))/.9,0.0,1.0)*clampf((float(card[2])-t)/.9,0.0,1.0)
		(card[0] as Control).modulate.a=fade*fade*(3.0-2.0*fade)

## The title over the dark hall, and an end card over the ring-out.
func _film_cards() -> void:
	var ssaa := maxi(int(option("ssaa","2" if (OS.get_environment("SHOT")!="" or option("capture","")!="") else "1")),1)
	var layer := CanvasLayer.new(); add_child(layer)
	var make := func(lines: Array, t_in: float, t_out: float) -> void:
		var box := VBoxContainer.new(); box.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		box.alignment=BoxContainer.ALIGNMENT_CENTER; box.mouse_filter=Control.MOUSE_FILTER_IGNORE
		for line in lines:
			var label := Label.new(); label.text=line[0]; label.horizontal_alignment=HORIZONTAL_ALIGNMENT_CENTER
			label.add_theme_font_size_override("font_size",int(line[1])*ssaa); label.add_theme_color_override("font_color",line[2])
			box.add_child(label)
		box.modulate.a=0.0; layer.add_child(box); film_cards.append([box,t_in,t_out])
	var title: String=str(score.doc.get("name","The Chamber")).to_upper()
	var spaced := " ".join(Array(title.split("")))
	make.call([[spaced,58,Color("f1e3c6")],["a machine that plays its score",22,Color(.72,.76,.74)]],.6,4.6)
	make.call([["composed, synthesised and built in code",22,Color(.72,.76,.74)],["L  O  A  M",34,Color("f1e3c6")]],score.total_s-4.2,score.total_s+1.0)

func _smooth_rail_x(aid: String, t: float) -> float:
	var sum := 0.0; var wsum := 0.0
	for k in 17:
		var f := float(k)/16.0*2.0-1.0
		var w := .5+.5*cos(PI*f)
		sum += motion.joint_origin(aid+"/carriage",t+f*1.6).x*w; wsum += w
	return sum/maxf(wsum,1e-6)

func _camera_at(t: float) -> void:
	if focus=="repair" or pillar_players.has(focus):
		var centre := Vector3(-1.38,.914,-1.46)
		var axis := Vector3(-.35,1.,.52)
		if pillar_players.has(focus):
			var arm: PillarPlayer = pillar_players[focus]
			centre = (arm.shoulder+arm.park)*.5
			axis = Vector3(.34,.24,signf(arm.park.z))
		if focus_dir!=Vector3.ZERO: axis=focus_dir
		camera.fov=INSPECTION_FOV
		var distance := .5*focus_span/tan(.5*deg_to_rad(camera.fov))
		camera.look_at_from_position(centre+axis.normalized()*distance,centre,Vector3.UP)
		return
	if layout["strings"].has(focus):
		var spec: Dictionary = layout["strings"][focus]
		var centre := MotionBake.contact(layout,focus,focus_pick)
		if spec["mid"]=="harp" and not pillar_players.is_empty():
			# Keep the contact and its hand in frame in an inspection close-up.
			var arm_id: String = harp_owner.get(focus,"")
			if pillar_players.has(arm_id):
				var side := signf(pillar_players[arm_id].park.z)
				centre+=Vector3(0,.012,side*.050)
		if spec["mid"]=="rake" or (spec["mid"]=="harp" and pillar_players.is_empty()): centre.y+=.037
		if spec["mid"]=="bells": centre+=Vector3(0,-.18,.055)
		camera.fov = INSPECTION_FOV
		var standoff := .5*focus_span/tan(.5*deg_to_rad(camera.fov))
		var axis := focus_dir.normalized() if focus_dir!=Vector3.ZERO else Vector3(.4,.32,1.).normalized()
		camera.look_at_from_position(centre+axis*standoff,centre,Vector3.UP)
		return
	if film or (auto_camera and not layout["arms"].has(focus)):
		var c := director.camera_at(t)
		camera.fov=float(c["fov"])
		camera.look_at_from_position(c["pos"],c["target"],Vector3.UP)
		return
	camera.fov = INSPECTION_FOV
	var target := Vector3(0,1.55,.2)
	var pos := Vector3(7.8,5.8,12.8)
	var chosen := view
	# --focus=<aid> overrides every view: frame one arm's own mechanism so a clip
	# reads the carriage, the rack, the pawl and the tool rather than the room.
	# Anchored on a static Y/Z frame and fixed distance, panning at most with
	# smoothed rail X traversal so the camera never jerks with the tool's stroke.
	if focus!="" and layout.get("arms",{}).has(focus):
		var cfg: Dictionary=layout["arms"][focus]
		var t_ref: float=fixed_time if shot!="" else (capture_start+.5*capture_seconds if capture_dir!="" else 0.0)
		var pose := motion.pose(focus,t_ref)
		var root: Vector3=pose["root"]; var tip: Vector3=pose["tip"]
		var rx := _smooth_rail_x(focus,t)
		target=Vector3(rx,(root.y+tip.y)/2.0,(root.z+tip.z)/2.0)
		var size := get_viewport().get_visible_rect().size
		var aspect: float=size.x/maxf(size.y,1.0)
		var tan_half: float=maxf(tan(deg_to_rad(camera.fov)/2.0),.001)
		var half_w: float=maxf(focus_span,absf(root.x-tip.x)+.30)/2.0
		var half_h: float=(absf(root.y-tip.y)+.30)/2.0
		if focus_at!="":
			target=Vector3(rx,tip.y,tip.z) if focus_at=="tip" else Vector3(rx,root.y,root.z)
			if focus_at=="head":
				var h0 := motion.joint_origin(focus+"/head",t_ref) if motion.has_joint(focus+"/head") else tip+Vector3(0,motion.head_length(focus),0)
				target=Vector3(rx,h0.y,h0.z)
			half_w=focus_span/2.0; half_h=focus_span/2.0
		var distance: float=maxf(maxf(half_w/(tan_half*aspect),half_h/tan_half),.8 if focus_at=="" else .30)
		var dir := focus_dir
		if dir==Vector3.ZERO:
			var mid: String=str(cfg.get("mid",""))
			var away := Vector3(0,0,1)
			if layout.get("mechanisms",{}).has(mid):
				var c := MotionBake.v(layout["mechanisms"][mid]["center"])
				away=Vector3(root.x-c.x,0,root.z-c.z)
				if away.length()<.05: away=Vector3(0,0,1)
			dir=(away.normalized()+Vector3(0,.18,0)).normalized()
		camera.look_at_from_position(target+dir.normalized()*distance,target,Vector3.UP)
		return
	if chosen == 0:
		target = Vector3(.45, .95, .2)
	elif chosen in [1,2,3]:
		var mid: String=["harp","rake","bars"][chosen-1]
		target=MotionBake.v(layout["mechanisms"][mid]["center"])
		if chosen in [1,2]: target.y=1.95 if chosen==1 else 1.55
		pos=target+Vector3(2.6,2.0,5.8) if chosen!=1 else Vector3(2.8,3.25,7.8)
	elif chosen==4: pos=Vector3(.01,13,4)
	elif chosen==5: target=Vector3(.1,1.8,-2.55); pos=Vector3(.1,7,1.0)
	elif chosen==6: target=Vector3(-.15,3.3,.25); pos=target+Vector3(.65,.28,3.5)
	elif chosen==7: target=Vector3(0,1.95,0); pos=Vector3(0,1.95,6.6)
	elif chosen==8: target=Vector3(-.9,.35,.2); pos=target+Vector3(1.3,.8,2.2)
	elif chosen==9:
		var aid: String="harp_arm1" if layout["arms"].has("harp_arm1") else layout["arms"].keys()[0]
		if pillar_players.has(aid):
			var arm: PillarPlayer=pillar_players[aid]
			target=arm.shoulder.lerp(arm.palm.position,.51)
			pos=target+Vector3(.73,.38,1.92)
		else:
			var pose0 := motion.pose(aid,0.0)
			var mid0: Vector3=(pose0["elbow"]+pose0["wrist"])/2.0
			target=Vector3(_smooth_rail_x(aid,t),mid0.y,mid0.z)
			pos=target+Vector3(1.5,.45,-1.9)
	elif chosen==10 and not strings.is_empty():
		# String close-up: the most recently sounded unstruck string, seen from
		# 45° off its pluck axis so both the bend and the blur read. The camera
		# latches for a while so a run of plucks does not throw it about.
		if follow_sid == "" or t < follow_since or t-follow_since > 1.5:
			var best := -INF
			follow_sid = ""
			for sid in wire_motion:
				var latest: float = wire_motion[sid].last_contact(t)
				if latest > best or follow_sid == "":
					best = latest
					follow_sid = sid
			follow_since = t
		var s: Dictionary=layout["strings"][follow_sid]
		var a := MotionBake.v(s["a"]); var b := MotionBake.v(s["b"])
		target=a.lerp(b,.3); pos=target+Vector3(.85,.3,.85)
	elif chosen==11:
		# Bar frame close-up: the treble end's rails, cord posts and resonator mouths, from low in front.
		var c := MotionBake.v(layout["mechanisms"]["bars"]["center"]) if layout["mechanisms"].has("bars") else Vector3(4.5,1.35,1.2)
		target=c+Vector3(.8,-.17,0); pos=c+Vector3(-.6,-.3,1.7)
	elif chosen==12:
		# The harp's action from the string side: the plate on the neck's string-side
		# face, the discs and fork pins straddling the strings, bridge and tuning pins
		# and the dead lengths, seen from behind the string plane where the arms work.
		var c := MotionBake.v(layout["mechanisms"]["harp"]["center"]) if layout["mechanisms"].has("harp") else Vector3(0,3.3,0)
		target=Vector3(c.x-.1,3.35,c.z); pos=target+Vector3(1.05,.15,-1.45)
	elif chosen==13:
		# The flywheel drive: wheel, plummer blocks, pedestals, the belt to the cabinet's end.
		var f: Vector3=MotionBake.v(layout["flywheel"]["centre"]) if layout.has("flywheel") else Vector3(-2.4,.53,-1.5)
		target=f+Vector3(.2,-.05,-.1); pos=f+Vector3(-.75,.55,1.75)
	elif chosen==14:
		# The harp's string feet from the string side: the eyelets on the ferrule
		# mouths along the soundbox, looking down the feet line from the treble end.
		var e: Vector3=MotionBake.v(layout["eyelets"]["harp07"]["centre"]) if layout.has("eyelets") and layout["eyelets"].has("harp07") else Vector3(0,1.45,0)
		target=e+Vector3(-.15,.02,0); pos=e+Vector3(.85,.55,-.9)
	elif chosen==16 and bass_string != "":
		# A wound bass string at arm's length: the harp's lowest string a hand above
		# its eyelet, from the string side, for the winding, the highlight along the
		# wire and the darkening at the hardware (shaders/wire_string.gdshader).
		var a := MotionBake.v(layout["strings"][bass_string]["a"])
		var b := MotionBake.v(layout["strings"][bass_string]["b"])
		target=a+(b-a)*.12; pos=target+Vector3(.16,.05,-.28)
	elif chosen==17:
		target=Vector3(-.16,1.37,.50); pos=target+Vector3(1.08,.35,1.86)
	elif chosen==18:
		target=Vector3(-.24,.52,-1.53); pos=target+Vector3(.78,.26,1.85)
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
	var selected_view := -1 if auto_camera else view
	var viewport_size := get_viewport().get_visible_rect().size
	if time != _posed_time:
		evaluate(time)
		_posed_time = time
	elif selected_view != _camera_view or viewport_size != _camera_viewport:
		_camera_at(time)
	_camera_view = selected_view
	_camera_viewport = viewport_size
	if hud != null:
		hud.update_playback(time, playing, selected_view, form_style, audio_mode)
	if shot!="" or capture_dir!="": record_frame()

func _unhandled_key_input(event: InputEvent) -> void:
	if not event is InputEventKey or not event.pressed or event.echo: return
	_command(event.keycode)

func _command(key: Key) -> void:
	match key:
		KEY_SPACE:
			playing=not playing
			_seek(-1.0 if playing and time >= score.total_s else time)
		KEY_HOME: _seek(-1)
		KEY_LEFT: _seek(time-2)
		KEY_RIGHT: _seek(time+2)
		KEY_C: auto_camera=false; view=(view+1)%PerformanceHud.VIEWS.size()
		KEY_F: _set_form(["carved","ribbed","shell"][( ["carved","ribbed","shell"].find(form_style)+1)%3])
		KEY_A: auto_camera=true
		KEY_T:
			if hud != null: hud.track.visible = not hud.track.visible
		KEY_M:
			audio_mode="stems" if audio_mode=="master" else "master"
			if player.stream==null: audio_mode="stems"
			_seek(time)
		_:
			if key>=KEY_1 and key<=KEY_9:
				var index: int=key-KEY_1
				if index<stem_players.size():
					stem_players[index].volume_db=0 if stem_players[index].volume_db<-40 else -80
					if hud != null:
						hud.track.muted[score.stem_ids()[index]] = stem_players[index].volume_db < -40
						hud.track.queue_redraw()
					if audio_mode!="stems": audio_mode="stems"; _seek(time)
