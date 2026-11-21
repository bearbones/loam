extends "res://performance_capture.gd"
## The stereo master, pedal linkages and articulated player share one event clock.
const FINISH := preload("res://shaders/drum_finish.gdshader")
const Look := preload("res://clockwork_look.gd")
const BOW := preload("res://assets/textures/metal_data.png")
const GRAIN := preload("res://assets/textures/board_surface.png")

class Stroke:
	var t: float
	var velocity: float
	var center: Vector3
	var local_point: Vector3
	var normal: Vector3
	var grip: Vector3
	var direction: Vector3
	var spin := false
	var salute := false
	var overhand := false
	var voice: String

class Limb:
	var upper: Node3D
	var lower: Node3D
	var palm: Node3D
	var stick: Node3D
	var thigh: Node3D
	var shin: Node3D
	var pedal: Node3D
	var strap: Node3D
	var boot: Node3D
	var side: float
	var heel: Vector3
	var strokes: Array[Stroke]=[]
	var times:=PackedFloat64Array()

class Voice:
	var mesh: MeshInstance3D
	var head: ShaderMaterial
	var at: Vector3
	var normal: Vector3
	var spots:=PackedVector3Array()
	var normals:=PackedVector3Array()
	var metal: bool
	var radius: float
	var times:=PackedFloat64Array()
	var phase_cos:=PackedFloat64Array()
	var phase_sin:=PackedFloat64Array()
	var decay: float
	var frequency: float
	var tail: float
	var last_response:=INF

	func strike(t: float,level: float) -> void:
		# Transport both quadratures to this contact and apply the impulse once.
		var a:=0.
		var b:=0.
		if not times.is_empty():
			var dt:=t-times[-1]
			var gain:=exp(-dt*decay)
			var c:=cos(dt*frequency)*gain
			var s:=sin(dt*frequency)*gain
			a=phase_cos[-1]*c+phase_sin[-1]*s
			b=phase_sin[-1]*c-phase_cos[-1]*s
		times.append(t);phase_cos.append(a);phase_sin.append(b+level)

	func wave(i: int,t: float) -> float:
		var dt:=t-times[i]
		return exp(-dt*decay)*(phase_cos[i]*cos(dt*frequency)+phase_sin[i]*sin(dt*frequency))

	func response_at(t: float) -> float:
		var last:=times.bsearch(t,false)-1
		var first:=times.bsearch(t-tail)
		if first>last:return 0.
		var value:=wave(last,t)
		return value-wave(first-1,t) if first>0 else value

var player:=AudioStreamPlayer.new()
var cam:=Camera3D.new()
var model: Node3D
var torso: Node3D
var optics: Node3D
var beater: Node3D
var arms: Dictionary={}
var voices: Dictionary={}
var surfaces: Array[Voice]=[]
var kit: Dictionary
var score: Dictionary
var left: Limb
var right: Limb
var drum: Voice
var tempo: float
var lead: float
var duration: float
var stick_l: float
var upper_l: float
var lower_l: float
var shoulder_local: Vector3
var chest_home: Vector3
var beat_times:=PackedFloat64Array()
var kicks:=PackedFloat64Array()
var gap_times:=PackedFloat64Array()
var gap_values:=PackedFloat32Array()
var time:=0.
var playing:=true
var silent:=false
var view: String
var beater_hit: float
var thigh_l: float
var shin_l: float

func _ready() -> void:
	kit=JSON.parse_string(FileAccess.get_file_as_string("res://assets/drum_kit.json"))
	score=JSON.parse_string(FileAccess.get_file_as_string("res://assets/overcrank.json"))
	tempo=60./float(score.bpm);lead=score.lead;duration=score.total_s
	upper_l=kit.upper;lower_l=kit.lower;stick_l=kit.stick
	chest_home=MotionBake.v(kit.chest);shoulder_local=MotionBake.v(kit.shoulder)
	model=preload("res://assets/drum_kit.glb").instantiate()
	add_child(model)
	torso=_part("Torso casting");optics=_part("Optic housing");beater=_part("Kick beater")
	thigh_l=kit.thigh;shin_l=kit.shin
	beater_hit=asin((float(kit.batter_z)-float(kit.beater_radius)-beater.position.z)/float(kit.beater_length))
	_bind_kit()
	left=_limb("left",1.);right=_limb("right",-1.)
	arms={"left":left,"right":right}
	_bind_score()
	var lights:=Look.new()
	lights.metal=BOW
	lights.light_rig(self)
	lights.env.ambient_light_energy=.51
	lights.key_light.light_energy=1.12
	lights.fill_light.position=Vector3(2.2,2.9,3.1);lights.fill_light.light_energy=1.12
	lights.rim_light.position=Vector3(-2.4,3.5,-2.);lights.rim_light.light_energy=1.72
	add_child(cam);cam.current=true
	add_child(player);player.stream=preload("res://assets/overcrank.ogg")
	configure_capture(lead,0.,duration)
	view=option("view","film")
	silent=OS.get_cmdline_user_args().has("--silent")
	time=fixed_time if shot!="" else capture_start if capture_dir!="" else 0.
	playing=shot=="" and capture_dir==""
	evaluate(time)
	if playing and not silent: player.play()
	print("OVERCRANK: %d scored attacks, %.2f seconds" % [score.events.size(),duration])

func _part(label: String) -> MeshInstance3D:
	return model.find_child(label,true,false) as MeshInstance3D

func _material(finish: int, color: String) -> ShaderMaterial:
	var m:=ShaderMaterial.new()
	m.shader=FINISH
	m.set_shader_parameter("finish",finish);m.set_shader_parameter("tint",Color(color))
	m.set_shader_parameter("hammered",preload("res://assets/textures/cymbal_hammer.png"))
	m.set_shader_parameter("toolmarks",BOW);m.set_shader_parameter("woodwork",GRAIN)
	return m

func _bind_kit() -> void:
	var palette={"Oxblood lacquer":_material(0,"a23225"),"Hammered bronze":_material(1,"d6ac69"),
		"Woven rug":_material(3,"795954"),"Hickory":_material(4,"dfa66c"),"Petrol enamel":_material(5,"28635c")}
	for mesh: MeshInstance3D in model.find_children("*","MeshInstance3D",true,false):
		for i in mesh.mesh.get_surface_count():
			var m:=mesh.mesh.surface_get_material(i)
			if m!=null and palette.has(m.resource_name):mesh.set_surface_override_material(i,palette[m.resource_name])
	for id in kit.voices:
		var s: Dictionary=kit.voices[id]
		var v:=Voice.new()
		v.at=MotionBake.v(s.center);v.normal=MotionBake.v(s.normal);v.metal=s.kind=="metal";v.radius=s.radius
		v.frequency=50. if v.metal else 133.
		v.decay=8. if v.metal else 32.
		v.tail=.69 if v.metal else .20
		if v.metal:
			for point in s.spots:
				v.spots.append(MotionBake.v(point.point));v.normals.append(MotionBake.v(point.normal))
		v.mesh=_part(id+(" plate" if v.metal else " head"))
		if not v.metal:
			v.head=_material(2,"e5dbc5");v.head.set_shader_parameter("radius",v.radius)
			v.mesh.set_surface_override_material(0,v.head)
		voices[id]=v
		surfaces.append(v)
	drum=voices.hat

func _limb(id: String,side: float) -> Limb:
	var l:=Limb.new()
	l.upper=_part(id+" upper");l.lower=_part(id+" lower");l.palm=_part(id+" palm");l.stick=_part(id+" stick")
	l.thigh=_part(id+" thigh");l.shin=_part(id+" shin");l.pedal=_part(id+" footboard");l.boot=_part(id+" boot")
	l.strap=_part(id+" pedal strap")
	l.side=side;l.heel=MotionBake.v(kit.pedals[id])
	return l

func _rest(arm: Limb,t: float) -> Stroke:
	var n:=Stroke.new()
	n.t=t;n.grip=Vector3(arm.side*.47,1.49,-.41)
	n.direction=Vector3(arm.side*.26,.62,.73).normalized()
	return n

func _bind_score() -> void:
	for arm: Limb in arms.values():
		arm.strokes.append(_rest(arm,-.95));arm.times.append(-.95)
	var open:=false
	for e in score.events:
		var t:=float(e.t)
		if e.limb=="kick":
			kicks.append(t);continue
		var v: Voice=voices[e.voice]
		v.strike(t,e.v)
		if e.voice=="hat":
			if e.style=="open" or e.style=="chick":
				if not open:
					gap_times.append(t-.080);gap_values.append(0.)
					gap_times.append(t-.020);gap_values.append(1.)
				open=true
			if e.style!="open" and open:
				gap_times.append(t-.016);gap_values.append(1.)
				gap_times.append(t);gap_values.append(0.)
				open=false
		if e.limb=="pedal":continue
		var arm: Limb=arms[e.limb]
		var n:=Stroke.new()
		n.t=t;n.velocity=e.v;n.spin=e.get("trick","")=="wheel";n.salute=e.get("trick","")=="salute";n.voice=e.voice
		n.overhand=e.get("trick","")=="overhand"
		var response:=v.response_at(t)
		if v.metal:
			var site:=clampi(roundi((float(e.offset)+1.)*.5*(v.spots.size()-1)),0,v.spots.size()-1)
			var rot:=_rock(0. if v==drum and e.style!="open" else response)
			n.local_point=v.spots[site];n.normal=rot*v.normals[site]
			n.center=v.at+rot*n.local_point
		else:
			var lane:=arm.side*.046 if e.voice=="snare" else 0.
			n.local_point=Vector3(lane+float(e.offset)*.020,0,-.024)
			n.normal=Vector3.UP
			n.center=v.at+n.local_point+Vector3.UP*_skin_height(n.local_point,v.radius,response)
		if e.style=="open":n.center.y+=.027
		n.direction=Vector3(clampf((n.center.x-arm.side*.36)*1.32,-.93,.93),-.54,.83).normalized()
		n.grip=n.center+n.normal*float(kit.bead)-n.direction*stick_l
		arm.strokes.append(n);arm.times.append(t)
		if e.voice=="snare" and n.velocity>.82:beat_times.append(t)
	for arm: Limb in arms.values():
		var park:=_rest(arm,arm.times[-1]+.85)
		park.grip=Vector3(arm.side*.62,1.88,-.57)
		park.direction=Vector3(arm.side*.37,.88,.27).normalized()
		arm.strokes.append(park);arm.times.append(park.t)

static func _smooth(x: float) -> float:
	x=clampf(x,0.,1.)
	return x*x*(3.-2.*x)

static func _link_pair(first: Node3D,second: Node3D,root: Vector3,end: Vector3,pole: Vector3,a: float,b: float) -> void:
	var diff:=end-root
	var d:=diff.length()
	var axis:=diff/d
	var along:=(a*a-b*b+d*d)/(2.*d)
	var bend:=(pole-axis*pole.dot(axis)).normalized()
	var middle:=root+axis*along+bend*sqrt(maxf(0.,a*a-along*along))
	var axle:=axis.cross(bend)
	first.transform=Transform3D(MotionBake.link_basis(root,middle,axle),root)
	second.transform=Transform3D(MotionBake.link_basis(middle,end,axle),middle)

func _hand(arm: Limb,t: float) -> void:
	var next:=clampi(arm.times.bsearch(t),1,arm.times.size()-1)
	var a:=arm.strokes[next-1];var b:=arm.strokes[next]
	var span:=b.t-a.t
	var u:=clampf((t-a.t)/span,0.,1.)
	var travel:=u
	var rise:=u
	if b.grip.y>a.grip.y+.24:
		travel=clampf((u-.26)/.74,0.,1.)
		rise=pow(u,.72)
	elif a.grip.y>b.grip.y+.24:
		travel=clampf(u/.74,0.,1.)
		rise=1.-pow(1.-u,.72)
	var w:=_smooth(travel)
	var arc:=sin(PI*rise)
	var grip:=a.grip.lerp(b.grip,w)
	var base:=a.direction.slerp(b.direction,w).normalized()
	var height:=minf(.168,.31*span)*(.49+.51*maxf(a.velocity,b.velocity))
	grip.y+=height*arc
	var direction:=base.slerp(Vector3.UP,minf(.88,span*1.64)*arc).normalized()
	var rotation:=MotionBake.link_basis(Vector3.ZERO,direction)
	if b.spin or b.salute or b.overhand:
		var lift:=arc*arc
		var flourish:=Vector3(arm.side*.66,1.94,-.52)
		if b.overhand:
			# The upper arm describes a broad circle. The stick clears the
			# cap as the elbow crosses inside and snaps back to the drum.
			flourish=Vector3(arm.side*(.53+.36*cos(PI*u)),2.05,-.48-.29*sin(PI*u))
		grip=grip.lerp(flourish,lift)
		rotation=MotionBake.link_basis(Vector3.ZERO,direction.slerp(Vector3(arm.side*.24,.94,.20).normalized(),lift))
		if b.spin or b.overhand:
			var angle:=arm.side*TAU*_smooth((u-.18)/.64)
			rotation=Basis(Vector3(arm.side*.12,.035,1.).normalized(),angle)*rotation
	# Bring the grip around the front of the goggles on cross-body rebounds.
	var crossing:=1.-smoothstep(.22,.60,absf(grip.x))
	grip.z+=.34*crossing*arc*minf(1.,span/.44)
	if (a.voice=="floor" and b.voice=="crash_r") or (a.voice=="crash_r" and b.voice=="floor"):
		grip.x+=.13*arc
	var root:=torso.to_global(Vector3(arm.side*shoulder_local.x,shoulder_local.y,shoulder_local.z))
	var bearing:=rotation.z*.041
	var delta:=grip-bearing-root
	var reach:=upper_l+lower_l-.003
	var forward:=sqrt(maxf(0.,reach*reach-delta.x*delta.x-delta.y*delta.y))
	grip.z=minf(grip.z,root.z+forward+bearing.z)
	var wrist:=grip-bearing
	arm.stick.transform=Transform3D(rotation,grip)
	arm.palm.transform=Transform3D(rotation,wrist)
	var elbow_pole:=Vector3(arm.side*.97,.27,.72)
	if b.spin or b.overhand:
		elbow_pole+=Vector3(arm.side*.13,.80,-.43)*arc*arc
	_link_pair(arm.upper,arm.lower,root,wrist,elbow_pole,upper_l,lower_l)

static func _age(times: PackedFloat64Array,t: float) -> float:
	var i:=times.bsearch(t,false)
	return t-times[i-1] if i>0 else INF

func _gap(t: float) -> float:
	var i:=gap_times.bsearch(t,false)
	if i==0 or i==gap_times.size():return 0.
	return lerpf(gap_values[i-1],gap_values[i],_smooth((t-gap_times[i-1])/(gap_times[i]-gap_times[i-1])))

func _feet(t: float,opening: float) -> void:
	var i:=kicks.bsearch(t)
	var since:=t-kicks[i-1] if i>0 else INF
	var until:=kicks[i]-t if i<kicks.size() else INF
	var contact:=maxf(1.-_smooth(since/.093),1.-_smooth(until/.065))
	beater.rotation.x=lerpf(-.49,beater_hit,contact)
	_foot(right,contact)
	_foot(left,1.-opening)

func _foot(arm: Limb,pressure: float) -> void:
	var rot:=Basis(Vector3.UP,.42 if arm==left else 0.)*Basis(Vector3.RIGHT,lerpf(-.24,-.028,pressure))
	arm.pedal.transform=Transform3D(rot,arm.heel)
	var heel:=arm.heel+rot*Vector3(0,.040,.011)
	arm.boot.transform=Transform3D(rot,heel)
	var toe:=arm.pedal.to_global(Vector3(0,.005,.244))
	var cam_pin:=beater.to_global(Vector3(.022,.039,-.040)) if arm==right else drum.at+Vector3(0,-.93-.016*pressure,0)
	var strap_basis:=MotionBake.link_basis(toe,cam_pin)
	strap_basis.y*=toe.distance_to(cam_pin)
	arm.strap.transform=Transform3D(strap_basis,toe)
	var hip:=torso.to_global(Vector3(arm.side*.137,-.142,.029))
	_link_pair(arm.thigh,arm.shin,hip,heel,Vector3(arm.side*.42,.1,1.),thigh_l,shin_l)

static func _skin_height(p: Vector3,radius: float,response: float) -> float:
	var r:=Vector2(p.x,p.z).length()/radius
	return -.006*response*(1.-r*r)*cos(4.2*r)

static func _rock(response: float) -> Basis:
	return Basis.from_euler(Vector3(response*.035,0,response*.060))

func _respond(v: Voice,t: float,opening: float) -> void:
	var response:=v.response_at(t)
	if v==drum:response*=opening
	if response==v.last_response:return
	v.last_response=response
	if v.metal:
		v.mesh.basis=_rock(response)
	else:
		v.head.set_shader_parameter("flex",-response*.006)

func evaluate(t: float) -> void:
	var beat:=(t-lead)/tempo
	var tail:=1.-_smooth((t-(duration-2.1))/1.45)
	var sway:=sin(PI*beat)*.032*tail
	var accent:=exp(-_age(beat_times,t)*9.)*tail
	torso.transform=Transform3D(Basis.from_euler(Vector3(.078+.055*cos(TAU*beat)*tail+.083*accent,sin(PI*beat*.5)*.080*tail,-sway*1.42)),
		chest_home+Vector3(sway,-.032*accent+.014*sin(TAU*beat)*tail,.025*tail))
	_hand(left,t);_hand(right,t)
	var lift_l:=smoothstep(1.42,1.90,left.palm.position.y)
	var lift_r:=smoothstep(1.42,1.90,right.palm.position.y)
	var glance:=(lift_l-lift_r)*.31*tail+.19*sin(beat*PI*.26)*tail
	var nod:=.13+.13*cos(TAU*beat+.3)*tail+.16*accent-.20*maxf(lift_l,lift_r)*tail
	optics.transform=torso.transform*Transform3D(Basis.from_euler(Vector3(nod,glance,.075*sin(beat*PI*.5)*tail)),Vector3(0,.589,.028))
	var opening:=_gap(t)
	_feet(t,opening)
	for v in surfaces:_respond(v,t,opening)
	drum.mesh.position=drum.at+Vector3.UP*.027*opening
	_camera(t,beat)

func _camera(t: float,beat: float) -> void:
	var bar:=beat/4.
	var pos:=Vector3(.50,1.70,3.61)
	var aim:=Vector3(0,1.03,-.04)
	var fov:=38.
	var angle:=view
	if view=="film":
		if bar>=3. and bar<4.:angle="heads"
		elif bar>=6. and bar<7.:angle="side"
		elif bar>=10. and bar<11.:angle="pedals"
		elif bar>=14. and bar<16.:angle="heads"
		elif bar>=17. and bar<18.5:angle="side"
		else:angle="wide"
	match angle:
		"wide":
			pos=Vector3(.40+.69*sin(t*.19),2.13+.17*cos(t*.21),3.87);aim.y=1.07;fov=39.
		"heads":
			pos=Vector3(.38,3.72,.88);aim=Vector3(0,1.10,-.13);fov=47.
		"side":
			pos=Vector3(-2.47,1.98,1.54);aim=Vector3(-.06,1.27,-.30);fov=38.
		"pedals":
			pos=Vector3(-1.04,.43,-.68);aim=Vector3(-.09,.22,.12);fov=41.
	cam.fov=fov;cam.look_at_from_position(pos,aim,Vector3.UP)

func _process(delta: float) -> void:
	if model==null:return
	if capture_dir!="":time=capture_start+frame*capture_speed/capture_fps
	elif playing:
		if silent: time=minf(time+delta,duration)
		elif player.playing:time=clampf(player.get_playback_position()+AudioServer.get_time_since_last_mix()-AudioServer.get_output_latency(),0.,duration)
		else:time=duration
		if time>=duration:playing=false
	evaluate(time)
	if shot!="" or capture_dir!="":record_frame()

func _restart() -> void:
	time=0.
	playing=true
	if not silent:
		player.stream_paused=false
		player.play(0.)

func _unhandled_key_input(e: InputEvent) -> void:
	if not e is InputEventKey or not e.pressed or e.echo:return
	if e.keycode==KEY_HOME or (e.keycode==KEY_SPACE and time>=duration):
		_restart()
	elif e.keycode==KEY_SPACE:
		playing=not playing
		player.stream_paused=not playing
