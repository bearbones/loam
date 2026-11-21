extends RefCounted
## A player has a fixed shoulder, a two-link reach and four planar digit chains.
## All note targets and material clearances are bound in the imported rig's metres.

const Wire = preload("res://string_motion.gd")
const DIGITS := ["thumb", "d2", "d3", "d4"]
# Within each horizontal phalanx plane the thumb opposes fingers 2–4.
# The four open shapes fan out behind the wire rank during transfer.
const LOAD_CURL := .32
const SPREAD := [Vector3(.76,-.38,-.25), Vector3(-.63,.37,.25),
	Vector3(-.39,.38,.26), Vector3(-.20,.41,.29)]

class Digit:
	var root: Node3D
	var middle: Node3D
	var distal: Node3D
	var pad: Node3D
	var lengths: Vector3
	var sign_x: float
	var spread: Vector3
	var placed: Vector3
	var resting: Vector3
	var closed: Vector3
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
	var seat_normal: Vector3
	var edge_normal: Vector3
	var plant: Vector3
	var approach: Vector3
	var retreat: Vector3
	var release_flex: Vector3
	var inv_pad_travel: float
	var align_at: float
	var touch_at: float
	var withdraw_at: float
	var clear_at: float
	var closed_at: float

	func pad_normal(t: float) -> Vector3:
		# The wire rolls from the fleshy flank onto the rounded end. At release
		# the entire line of rebound is tangent to the pad.
		return seat_normal.slerp(edge_normal, smoothstep(time-.015,time,t))

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
	for index in DIGITS.size():
		var name: String = DIGITS[index]
		var d := Digit.new()
		d.sign_x = -1. if index==0 else 1.
		d.spread = SPREAD[index]
		d.placed = Vector3(1.25,-.78,-.55) if index==0 else Vector3(-.96,.80,.55)
		d.resting = d.sign_x*Vector3(.22,1.13,1.02)
		d.closed = d.sign_x*Vector3(1.15,1.92,1.48)
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
			# Pick the perpendicular on this player's side of the string plane.
			n.edge_normal = n.push.cross(Vector3.UP)
			if n.edge_normal.dot(frame.z)>0.:
				n.edge_normal = -n.edge_normal
			n.seat_normal = n.edge_normal*cos(.65)-n.push*sin(.65)
			var radius := n.gauge+pad_radius
			var placed_reach := _reach(d.placed,d.lengths)
			n.plant = n.base+n.seat_normal*radius-frame*(d.root.position+placed_reach)
			var travel := draw+(n.edge_normal-n.seat_normal)*radius
			n.inv_pad_travel = 1./travel.dot(n.push)
			n.release_flex = _solve_digit(d,placed_reach+frame.transposed()*travel,absf(d.placed.z)+LOAD_CURL)
			times.append(n.time)
			notes.append(n)
	for i in notes.size():
		var n := notes[i]
		var before := n.time-notes[i-1].time if i>0 else 2.5
		var after := notes[i+1].time-n.time if i+1<notes.size() else 2.5
		# Short runs use a shallow lift between wires. The finger completes its
		# closure as the arm carries the hand to the next playing height.
		var lift := Vector3(-.012*digits[n.digit].sign_x,.032,-.115)
		n.approach = n.plant+frame*lift*lerpf(.68,1.,smoothstep(.17,.70,before))
		n.retreat = n.plant+frame*lift*lerpf(.68,1.,smoothstep(.17,.70,after))
		n.touch_at = n.time-Wire.PULL_S-minf(.036,before*.10)
		n.withdraw_at = n.time+minf(.047,after*.12)
		# Reserve part of even the shortest transfer for each side of the rank.
		var depart := n.time-before+minf(.047,before*.12)
		n.align_at = n.touch_at-minf(.23,(n.touch_at-depart)*.36)
		var land := n.time+after-Wire.PULL_S-minf(.036,after*.10)
		n.clear_at = n.withdraw_at+minf(.16,(land-n.withdraw_at)*.30)
		n.closed_at = minf(n.time+.085,n.clear_at)

static func _solve_digit(d: Digit, point: Vector3, tip_flex: float) -> Vector3:
	point.x *= d.sign_x
	return d.sign_x*_flex(point,d.lengths,tip_flex)

static func _ease(t: float, a: float, b: float) -> float:
	var s := clampf((t-a)/(b-a),0.,1.)
	return s*s*s*(10.+s*(-15.+6.*s))

func _travel(prev: Note, next: Note, t: float) -> Vector3:
	if prev==null:
		return park.lerp(next.approach,_ease(t,next.align_at-.55,next.align_at))
	if next==null:
		return prev.retreat.lerp(park,_ease(t,prev.clear_at,prev.clear_at+.55))
	if next.time-prev.time>2.15:
		if t<prev.clear_at+.55:
			return prev.retreat.lerp(park,_ease(t,prev.clear_at,prev.clear_at+.55))
		return park.lerp(next.approach,_ease(t,next.align_at-.55,next.align_at))
	return prev.retreat.lerp(next.approach,_ease(t,prev.clear_at,next.align_at))

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
	if notes.is_empty():
		_set_reach(park)
		for d in digits: d.set_flex(d.spread)
		return
	var i := times.bsearch(t)
	var prev := notes[i-1] if i>0 else null
	var next := notes[i] if i<notes.size() else null
	if next!=null and t>=next.touch_at:
		_set_reach(next.plant)
		var d := digits[next.digit]
		var centre := next.base+next.wire.excursion_at(next.pick)
		var tip := centre+(next.gauge+pad_radius)*next.pad_normal(t)
		var local := frame.transposed()*(tip-next.plant)-d.root.position
		# Couple the joint bend to distance travelled on the pad. A separate
		# time curve for the tip can force the middle joint to open under load.
		var from_seat := tip-next.base-next.seat_normal*(next.gauge+pad_radius)
		var load_fraction := clampf(from_seat.dot(next.push)*next.inv_pad_travel,0.,1.)
		var bend := absf(d.placed.z)+LOAD_CURL*load_fraction
		for finger in digits:
			finger.set_flex(_solve_digit(d,local,bend) if finger==d else finger.resting)
	elif next!=null and t>=next.align_at:
		var descent := _ease(t,next.align_at,next.touch_at)
		_set_reach(next.approach.lerp(next.plant,descent))
		# Form the hook in the air. The last part of the descent presents an
		# already-rounded horn pad to the vibrating string from the near side.
		var shape := smoothstep(0.,.78,descent)
		for finger in digits:
			var playing := finger==digits[next.digit]
			var q := finger.spread.lerp(finger.placed if playing else finger.resting,shape)
			if playing:
				var point := _reach(q,finger.lengths)+frame.transposed()*next.wire.excursion_at(next.pick)*shape
				q = _solve_digit(finger,point,absf(q.z))
			finger.set_flex(q)
	elif prev!=null and t<=prev.clear_at:
		_set_reach(prev.plant.lerp(prev.retreat,_ease(t,prev.withdraw_at,prev.clear_at)))
		for finger in digits:
			var q := finger.resting
			if finger==digits[prev.digit]:
				var close := smoothstep(prev.time,prev.closed_at,t)
				q = prev.release_flex.lerp(finger.closed,close)
				# The last link rounds the rim before the large knuckle folds.
				# Advancing the long proximal link first sweeps the tip back
				# into the plane of the ringing wire.
				q.x = lerpf(prev.release_flex.x,finger.closed.x,close*close)
			finger.set_flex(q)
	else:
		_set_reach(_travel(prev,next,t))
		var opened := 1.
		if prev!=null:
			var end := prev.clear_at+.19
			if next!=null: end=minf(end,next.align_at)
			opened = _ease(t,prev.clear_at,end)
		for finger in digits:
			var folded := finger.closed if prev!=null and finger==digits[prev.digit] else finger.resting
			finger.set_flex(folded.lerp(finger.spread,opened))
