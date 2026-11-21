extends RefCounted
## A player has a fixed shoulder, a two-link reach and four planar digit chains.
## All note targets and material clearances are bound in the imported rig's metres.

const Wire = preload("res://string_motion.gd")
const DIGITS := ["thumb", "d2", "d3", "d4"]
const OPEN := Vector3(-.72,.58,.44)
const CLOSED := Vector3(.66,1.32,1.40)
const PREP := .145
const SLIP := .095

class Digit:
	var root: Node3D
	var middle: Node3D
	var distal: Node3D
	var pad: Node3D
	var lengths: Vector3
	var times := PackedFloat64Array()
	var notes: Array[Note] = []
	var last_flex := Vector3(INF,INF,INF)
	func set_flex(q: Vector3) -> void:
		if q==last_flex: return
		last_flex=q
		root.basis = Basis(Vector3.UP,q.x)
		middle.basis = Basis(Vector3.UP,q.y)
		distal.basis = Basis(Vector3.UP,q.z)

class Note:
	var time: float
	var digit: int
	var wire: Wire
	var base: Vector3
	var pick: float
	var gauge: float
	var push: Vector3
	var plant: Vector3
	var release_flex: Vector3

var digits: Array[Digit] = []
var notes: Array[Note] = []
var times := PackedFloat64Array()
var shoulder: Vector3
var upper: Node3D
var lower: Node3D
var palm: Node3D
var frame: Basis
var park: Vector3
var pole: Vector3
var l1: float
var l2: float
var pad_radius: float
var last_origin := Vector3(INF,INF,INF)

static func _reach(q: Vector3, l: Vector3) -> Vector3:
	return Vector3(l.x*sin(q.x)+l.y*sin(q.x+q.y)+l.z*sin(q.x+q.y+q.z),0,
		l.x*cos(q.x)+l.y*cos(q.x+q.y)+l.z*cos(q.x+q.y+q.z))

static func _flex(point: Vector3, l: Vector3, tip_angle: float) -> Vector3:
	var vx := l.z*sin(tip_angle)
	var vz := l.y+l.z*cos(tip_angle)
	var r := sqrt(vx*vx+vz*vz)
	var mid := acos(clampf((point.x*point.x+point.z*point.z-l.x*l.x-r*r)/(2.*l.x*r),-1.,1.))
	var base := atan2(point.x,point.z)-atan2(r*sin(mid),l.x+r*cos(mid))
	return Vector3(base,mid-atan2(vx,vz),tip_angle)

func bind(model: Node3D, aid: String, cfg: Dictionary, events: Array, layout: Dictionary, wires: Dictionary) -> void:
	var mount: Dictionary = cfg["pillar_player"]
	shoulder = MotionBake.v(mount["shoulder"])
	park = MotionBake.v(mount["park"])
	pole = MotionBake.v(mount["pole"])
	l1 = mount["upper"]
	l2 = mount["forearm"]
	pad_radius = mount["pad_radius"]
	upper = model.find_child(aid+"__upper_stock",true,false)
	lower = model.find_child(aid+"__forearm_stock",true,false)
	palm = model.find_child(aid+"__palm",true,false)
	for name in DIGITS:
		var d := Digit.new()
		d.root = palm.find_child(aid+"__digit_"+name,true,false)
		d.middle = d.root.get_child(0)
		d.distal = d.middle.get_child(0)
		d.pad = d.distal.find_child(aid+"__pad_"+name,true,false)
		d.lengths = Vector3(d.middle.position.z,d.distal.position.z,d.pad.position.z)
		digits.append(d)
	frame = Basis(Vector3.UP,PI if float(mount["side"])>0. else 0.)
	for e in events:
		if e["actuator"] != aid: continue
		var onsets := ScoreDoc.string_times(e)
		for k in onsets.size():
			var sid: String = e["strings"][k]
			var spec: Dictionary = layout["strings"][sid]
			var n := Note.new()
			n.time = onsets[k]
			n.digit = posmod(int(e.get("finger",1)),DIGITS.size())
			n.wire = wires[sid]
			n.pick = float(spec["pick"] if e.get("pick")==null else e["pick"])
			n.base = MotionBake.contact(layout,sid,n.pick)
			n.gauge = .0035*pow(2.,(64.-float(spec["midi"]))/18.)
			var draw := n.wire.draw_at_release(n.time)
			n.push = draw.normalized()
			var d := digits[n.digit]
			var open_reach := _reach(OPEN,d.lengths)
			n.plant = n.base-n.push*(n.gauge+pad_radius)-frame*(d.root.position+open_reach)
			n.release_flex = _flex(open_reach+frame.transposed()*draw,d.lengths,.88)
			d.times.append(n.time)
			d.notes.append(n)
			times.append(n.time)
			notes.append(n)

static func _ease(t: float, a: float, b: float) -> float:
	var s := clampf((t-a)/(b-a),0.,1.)
	return s*s*s*(10.+s*(-15.+6.*s))

func _palm_at(t: float) -> Vector3:
	if notes.is_empty(): return park
	var i := times.bsearch(t)
	if i==0:
		return park.lerp(notes[0].plant,_ease(t,times[0]-.86,times[0]-PREP))
	var prev := notes[i-1]
	if i==notes.size():
		return prev.plant.lerp(park,_ease(t,prev.time+.18,prev.time+.90))
	var next := notes[i]
	var gap := next.time-prev.time
	if gap>2.15:
		if t<prev.time+1.0:
			return prev.plant.lerp(park,_ease(t,prev.time+.18,prev.time+.90))
		return park.lerp(next.plant,_ease(t,next.time-.86,next.time-PREP))
	return prev.plant.lerp(next.plant,_ease(t,prev.time+minf(.12,gap*.19),next.time-minf(PREP,gap*.48)))

func _set_reach(origin: Vector3) -> void:
	if origin==last_origin: return
	last_origin=origin
	palm.transform = Transform3D(frame,origin)
	var wrist := origin+frame*Vector3(0,0,-.063)
	var axis := wrist-shoulder
	var dist := axis.length()
	axis /= dist
	var bend := (pole-axis*pole.dot(axis)).normalized()
	var along := (dist*dist+l1*l1-l2*l2)/(2.*dist)
	var elbow := shoulder+axis*along+bend*sqrt(maxf(0.,l1*l1-along*along))
	var pin := axis.cross(bend)
	upper.transform = Transform3D(MotionBake.link_basis(shoulder,elbow,pin),shoulder)
	lower.transform = Transform3D(MotionBake.link_basis(elbow,wrist,pin),elbow)

func apply(t: float) -> void:
	var origin := _palm_at(t)
	_set_reach(origin)
	for d in digits:
		var i := d.times.bsearch(t-.0000001)
		var q := CLOSED
		if i>0:
			var prev := d.notes[i-1]
			q = prev.release_flex.lerp(CLOSED,_ease(t,prev.time,prev.time+SLIP))
		if i<d.notes.size():
			var n := d.notes[i]
			var age := t-n.time
			if age>=-Wire.PULL_S-.0000001:
				var target := n.base+n.wire.excursion_at(n.pick)-n.push*(n.gauge+pad_radius)
				var local := frame.transposed()*(target-origin)-d.root.position
				q = _flex(local,d.lengths,lerpf(OPEN.z,.88,_ease(age,-Wire.PULL_S,0.)))
			elif age>=-PREP:
				q = q.lerp(OPEN,_ease(age,-PREP,-Wire.PULL_S))
		d.set_flex(q)
