extends "res://performance_capture.gd"
## One instrument is resident at a time. Portable glTF animation and the stereo
## take share the score clock, including on pause, seek and frame capture.
const BASE := "res://assets/cabinet/"
const Look = preload("res://clockwork_look.gd")
# Contact seats are in each maker's local coordinates, on real shell, rail
# or throat geometry. The mast sits behind the deepest point of the instrument.
const SEATS := {
	"oud":[Vector3(-.25,.35,-.292),Vector3(.25,.35,-.292)],
	"nyckelharpa":[Vector3(-.125,.30,-.125),Vector3(.125,.30,-.125)],
	"kora":[Vector3(-.17,.34,-.255),Vector3(.17,.34,-.255)],
	"dulcimer":[Vector3(-.122,.30,-.095),Vector3(.122,.30,-.095)],
	"shakuhachi":[Vector3(-.034,.227,-.038),Vector3(.034,.227,-.038)],
	"siku":[Vector3(-.20,.69,-.106),Vector3(.20,.69,-.106)],
	"uilleann":[Vector3(-.22,.41,-.131),Vector3(-.02,.41,-.138)],
	"serpent":[Vector3(.12,.45,.021),Vector3(.22,.43,.010)],
	"hardanger":[Vector3(-.134,.25,-.105),Vector3(.134,.25,-.105)],
	"gurdy":[Vector3(-.166,.31,-.157),Vector3(.166,.31,-.157)]}
const DETAIL := {
	"oud":Vector3(0,.44,.02),"nyckelharpa":Vector3(-.09,.52,.08),"koto":Vector3(.20,.28,.02),
	"kora":Vector3(0,.46,.20),"dulcimer":Vector3(0,.44,.04),"shakuhachi":Vector3(0,.47,.02),
	"siku":Vector3(-.03,.85,0),"sheng":Vector3(0,.36,.07),"uilleann":Vector3(.08,.48,.06),
	"serpent":Vector3(0,.67,.07),"balafon":Vector3(0,.45,0),"mbira":Vector3(0,.25,.03),
	"tabla":Vector3(.04,.43,.02),"kulintang":Vector3(-.20,.37,.03),"udu":Vector3(0,.42,.13),
	"hardanger":Vector3(0,.36,.08),"gurdy":Vector3(0,.34,.08),"armonica":Vector3(.05,.54,0),
	"bandoneon":Vector3(.25,.29,.03),"handpan":Vector3(.07,.32,.06),"magnetar":Vector3(0,.60,0),
	"periapsis":Vector3(0,.22,.10),"choir":Vector3(0,.48,-.01),"cryotape":Vector3(-.14,.44,.04),
	"pulsar":Vector3(0,.54,.02)}
var catalog: Array
var layouts: Dictionary
var index := 0
var model: Node3D
var animator: AnimationPlayer
var stand: Node3D
var camera := Camera3D.new()
var audio := AudioStreamPlayer.new()
var clock := 0.
var duration := 1.
var running := false
var silent := false
var auto_next := true
var view := "recital"
var azimuth := 0.
var isolated := false
var eye: Vector3
var centre: Vector3
var detail: Vector3
var distance := 2.
var label_title := Label.new()
var label_family := Label.new()
var controls := HBoxContainer.new()
var picker := OptionButton.new()
var pause_button := Button.new()
var caption := PanelContainer.new()
var fabric: StandardMaterial3D
var brass: StandardMaterial3D

func _ready() -> void:
	catalog=JSON.parse_string(FileAccess.get_file_as_string(BASE+"catalog.json"))
	layouts=JSON.parse_string(FileAccess.get_file_as_string(BASE+"display.json"))
	var key:=option("instrument","")
	if key!="":
		index=catalog.find_custom(func(entry):return entry.id==key)
		if index<0:
			push_error("Unknown cabinet instrument: "+key);get_tree().quit(2);return
	auto_next=key==""
	isolated=OS.get_cmdline_user_args().has("--isolated")
	azimuth=deg_to_rad(float(option("azimuth","0")))
	if not isolated:
		var room: PackedScene=load("res://assets/cabinet_room.glb")
		add_child(room.instantiate())
	var light:=Look.new()
	light.light_rig(self)
	light.env.ambient_light_energy=.39
	light.key_light.light_energy=.78
	light.key_light.directional_shadow_max_distance=6.
	light.key_light.shadow_normal_bias=.32
	light.fill_light.position=Vector3(-2.2,2.1,2.0)
	light.fill_light.light_energy=1.0
	light.rim_light.position=Vector3(1.9,2.7,-1.4)
	light.rim_light.light_energy=1.35
	var bench_light:=SpotLight3D.new()
	bench_light.light_color=Color("ffe7c7");bench_light.light_energy=3.1
	bench_light.spot_range=4.5;bench_light.spot_angle=39.;bench_light.spot_angle_attenuation=.74
	add_child(bench_light)
	var lamp_position:=Vector3(-1.10,2.4,1.35)
	if isolated:
		lamp_position=lamp_position.rotated(Vector3.UP,azimuth)
	bench_light.look_at_from_position(lamp_position,Vector3(0,.41,0))
	if option("light","")=="raking":
		light.key_light.rotation_degrees=Vector3(-16,-74,0)
		light.key_light.light_color=Color("fff1db")
		light.key_light.light_energy=1.45
		light.env.ambient_light_energy=.31
		bench_light.light_energy=.65
	camera.near=.025;camera.fov=34.
	add_child(camera);camera.current=true
	add_child(audio)
	fabric=StandardMaterial3D.new();fabric.albedo_color=Color("533c31");fabric.roughness=.82
	brass=StandardMaterial3D.new();brass.albedo_color=Color("98734c");brass.metallic=.65;brass.roughness=.39
	configure_capture(1.1,0.,float(catalog[index].duration))
	silent=OS.get_cmdline_user_args().has("--silent")
	view=option("view","recital")
	_make_ui()
	_select(index)

func _make_ui() -> void:
	var layer:=CanvasLayer.new();add_child(layer)
	layer.add_child(caption)
	caption.mouse_filter=Control.MOUSE_FILTER_IGNORE
	caption.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	var u:=get_viewport().get_visible_rect().size.x/1600.
	var bg:=StyleBoxFlat.new();bg.bg_color=Color("101b20ef")
	bg.border_color=Color("ba9258");bg.border_width_left=maxi(2,roundi(3*u))
	bg.content_margin_left=22*u;bg.content_margin_right=29*u
	bg.content_margin_top=8*u;bg.content_margin_bottom=10*u
	caption.add_theme_stylebox_override("panel",bg)
	var labels:=VBoxContainer.new();labels.add_theme_constant_override("separation",0);caption.add_child(labels)
	var font:=SystemFont.new();font.font_names=PackedStringArray(["Georgia","Liberation Serif","serif"])
	label_title.add_theme_font_override("font",font);label_title.add_theme_font_size_override("font_size",maxi(17,roundi(42*u)))
	label_title.modulate=Color("fbebc9");labels.add_child(label_title)
	label_family.add_theme_font_size_override("font_size",maxi(12,roundi(20*u)))
	label_family.modulate=Color("d7d8c5");labels.add_child(label_family)
	caption.offset_left=27*u;caption.offset_top=-120*u;caption.grow_vertical=Control.GROW_DIRECTION_BEGIN
	if OS.get_cmdline_user_args().has("--clean"):caption.hide()
	layer.add_child(controls)
	controls.visible=shot=="" and capture_dir=="" and not OS.get_cmdline_user_args().has("--clean")
	controls.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT)
	controls.position=Vector2(16,14)*u
	for item in catalog:picker.add_item(item.title)
	picker.item_selected.connect(_select);controls.add_child(picker)
	pause_button.pressed.connect(_toggle);controls.add_child(pause_button)
	var close:=Button.new();close.text="Detail";controls.add_child(close)
	close.pressed.connect(func():view="wide" if view=="detail" else "detail";evaluate(clock))

func _rod(parent: Node3D,a: Vector3,b: Vector3,r: float,mat: Material) -> void:
	var node:=MeshInstance3D.new();var mesh:=CylinderMesh.new()
	mesh.top_radius=r;mesh.bottom_radius=r;mesh.height=a.distance_to(b);mesh.radial_segments=16;mesh.rings=1
	node.mesh=mesh;node.material_override=mat
	node.transform=Transform3D(MotionBake.link_basis(a,b),(a+b)*.5)
	parent.add_child(node)

func _cradle(seats: Array, back: float) -> void:
	stand=Node3D.new();add_child(stand)
	var a: Vector3=seats[0]+model.position
	var b: Vector3=seats[1]+model.position
	var mast:=Vector3((a.x+b.x)*.5,maxf(.09,minf(a.y,b.y)-.085),back)
	var foot:=Vector3(mast.x,.003,mast.z)
	var radius:=clampf(a.distance_to(b)*.38,.056,.132)
	_rod(stand,foot,foot+Vector3.UP*.020,radius,brass)
	_rod(stand,foot+Vector3.UP*.02,mast,.012,brass)
	for tip: Vector3 in [a,b]:
		var socket:=tip+Vector3(0,-.010,-.022)
		_rod(stand,mast,socket,.009,brass)
		_rod(stand,socket,tip,.014,fabric)

func _select(which: int) -> void:
	audio.stop();audio.stream_paused=false
	if model!=null:remove_child(model);model.free()
	if stand!=null:remove_child(stand);stand.free();stand=null
	index=posmod(which,catalog.size())
	var item: Dictionary=catalog[index];var key: String=item.id
	var scene: PackedScene=load(BASE+key+".glb")
	model=scene.instantiate();add_child(model)
	animator=model.find_child("AnimationPlayer",true,false)
	if animator==null or not animator.has_animation("Recital"):
		push_error("Missing Recital animation in "+key); get_tree().quit(1);return
	animator.callback_mode_process=AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	animator.play("Recital")
	var layout: Dictionary=layouts[key]
	var lo:=MotionBake.v(layout.lo);var hi:=MotionBake.v(layout.hi);var size:=hi-lo
	model.position.y=-lo.y
	if key in SEATS and not isolated:
		model.position.y+=.075
		_cradle(SEATS[key],lo.z-.045)
	centre=(hi+lo)*.5+model.position
	detail=DETAIL[key]+model.position
	eye=MotionBake.v(layout.eye).normalized()
	var right:=Vector3.UP.cross(eye).normalized();var up:=eye.cross(right)
	var aspect:=get_viewport().get_visible_rect().size.aspect()
	var tan_v:=tan(deg_to_rad(camera.fov*.5))
	distance=0.
	for x in [-.5,.5]:
		for y in [-.5,.5]:
			for z in [-.5,.5]:
				var p:=size*Vector3(x,y,z)
				var fit:=maxf(absf(p.dot(right))/(tan_v*aspect),absf(p.dot(up))/tan_v)
				distance=maxf(distance,p.dot(eye)+fit*1.19)
	distance=maxf(distance,.82)
	centre-=up*(distance*tan_v*.090)
	duration=float(item.duration)
	audio.stream=load(BASE+key+".ogg")
	picker.select(index);label_title.text=item.title;label_family.text=item.family
	label_title.tooltip_text=item.history;picker.tooltip_text=item.history
	caption.reset_size()
	clock=clampf(fixed_time if shot!="" else capture_start if capture_dir!="" else 0.,0.,duration)
	running=shot=="" and capture_dir==""
	if running and not silent:audio.play()
	pause_button.text="Pause" if running else "Play"
	evaluate(clock)

func evaluate(t: float) -> void:
	animator.seek(clampf(t,0.,duration),true)
	var f:=clampf(t/duration,0.,1.)
	var focus:=0.
	if view=="detail": focus=1.
	elif view=="recital":focus=smoothstep(.33,.84,f)
	var target:=centre.lerp(detail,focus*.86)
	var direction:=eye.rotated(Vector3.UP,.15*sin(f*PI*1.35-.4))
	if view=="wide":direction=eye
	direction=direction.rotated(Vector3.UP,azimuth)
	if view=="macro":
		camera.look_at_from_position(detail+direction*distance*.40,detail,Vector3.UP)
		return
	camera.look_at_from_position(target+direction*distance*lerpf(1.,.55 if view=="recital" else .71,focus),target,Vector3.UP)

func _process(dt: float) -> void:
	if animator==null:return
	if not running and shot=="" and capture_dir=="":return
	if capture_dir!="":
		clock=capture_start+frame*capture_speed/capture_fps
	elif running:
		if silent:clock+=dt
		elif audio.playing:clock=audio.get_playback_position()+AudioServer.get_time_since_last_mix()-AudioServer.get_output_latency()
		else:clock=duration
		if clock>=duration:
			if auto_next:_select(index+1);return
			clock=duration;running=false;pause_button.text="Replay"
	evaluate(clock)
	if shot!="" or capture_dir!="":record_frame()

func _toggle() -> void:
	if clock>=duration:
		_select(index);return
	running=not running
	audio.stream_paused=not running
	pause_button.text="Pause" if running else "Play"

func _unhandled_key_input(e: InputEvent) -> void:
	if not e is InputEventKey or not e.pressed or e.echo:return
	match e.keycode:
		KEY_RIGHT:_select(index+1)
		KEY_LEFT:_select(index-1)
		KEY_HOME:_select(index)
		KEY_SPACE:_toggle()
		KEY_D:
			view="wide" if view=="detail" else "detail"
			evaluate(clock)
