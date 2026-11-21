extends RefCounted
## Digit poses in authored order. The prefix of closing times and suffix
## of opening times bound the active gestures even when two notes overlap.
const DIGITS := ["thumb", "d2", "d3", "d4"]
var _thumb_axis := Vector3(0.0, 0.85, 0.52).normalized()

var _nodes: Array[Node3D] = []
var _homes: Array[Basis] = []
var _knuckles := PackedVector3Array()
var _digit := PackedInt32Array()
var _place := PackedFloat64Array()
var _pull := PackedFloat64Array()
var _slip := PackedFloat64Array()
var _close := PackedFloat64Array()
var _first := PackedFloat64Array()
var _last := PackedFloat64Array()
var _curls := PackedFloat64Array()
var _rake: bool
var _side := 1.
var _middle: Array[Node3D] = []
var _distal: Array[Node3D] = []
var _pads: Array[Node3D] = []
var _ready := PackedVector3Array()
var _mounted := false

func bind(parts: Dictionary, cfg: Dictionary, pose: Dictionary) -> void:
	_rake = cfg.get("kind") == "rake"
	_side = -1. if int(cfg.get("index",0))==1 else 1.
	var knuckles: Dictionary = pose.get("knuckles", cfg.get("hand", {}).get("knuckles", {}))
	_curls.resize(DIGITS.size())
	for digit in DIGITS:
		var node: Node3D = parts.get("digit_" + digit)
		_nodes.append(node)
		_homes.append(node.basis if node != null else Basis.IDENTITY)
		_knuckles.append(MotionBake.v(knuckles.get(digit, [.014,.078,-.036])))
	var latest := -INF
	for note in pose.get("notes", []):
		var digit := DIGITS.find(note.get("digit", "d2"))
		if digit < 0: continue
		var place := float(note.get("t_place", 0.0))
		var pull := float(note.get("t_pull", place))
		var slip := float(note.get("t_slip", pull+.064))
		var close := float(note.get("t_close", slip+.10))
		_digit.append(digit)
		_place.append(place)
		_pull.append(pull)
		_slip.append(slip)
		_close.append(close)
		_first.append(minf(place-.16, pull))
		latest = maxf(latest, close+.42)
		_last.append(latest)
	for i in range(_first.size()-2, -1, -1):
		_first[i] = minf(_first[i], _first[i+1])

static func _ease(u: float) -> float:
	return u*u*u*(10.0+u*(-15.0+6.0*u))

func apply(t: float, tip: Vector3) -> Vector3:
	_curls.fill(0.0)
	for j in range(_last.bsearch(t), _first.bsearch(t, false)):
		var d := _digit[j]
		if t >= _place[j]-.16 and t < _place[j]:
			var u := clampf((t-(_place[j]-.16))/.16, 0.0, 1.0)
			_curls[d] = minf(_curls[d], -.14*sin(PI*u))
		elif t >= _pull[j] and t <= _slip[j]:
			var u := clampf((t-_pull[j])/maxf(_slip[j]-_pull[j], 1e-6), 0.0, 1.0)
			_curls[d] = maxf(_curls[d], .24*_ease(u))
			if _rake:
				for k in DIGITS.size():
					var finger := (k+1)%4 if d == 1 else k
					var delay := clampf((u-.16*k)/.52, 0.0, 1.0)
					_curls[finger] = maxf(_curls[finger], .46*sin(PI*delay))
		elif t > _slip[j] and t <= _close[j]:
			var u := clampf((t-_slip[j])/maxf(_close[j]-_slip[j], 1e-6), 0.0, 1.0)
			_curls[d] = maxf(_curls[d], .24+(.610865-.24)*_ease(u))
		elif t > _close[j] and t <= _close[j]+.14:
			_curls[d] = maxf(_curls[d], .610865)
		elif t > _close[j]+.14 and t < _close[j]+.42:
			var u := clampf((t-(_close[j]+.14))/.28, 0.0, 1.0)
			_curls[d] = maxf(_curls[d], .610865*(1.0-_ease(u)))
	var peak := maxf(maxf(_curls[0], _curls[1]), maxf(_curls[2], _curls[3]))
	for d in DIGITS.size():
		var node := _nodes[d]
		if node == null: continue
		var q := _curls[d]
		if q >= 0.0 and peak > q: q = lerpf(q, peak, .18)
		if _mounted:
			node.basis = Basis(Vector3.RIGHT, _side*(.12+q*.85))
			_middle[d].basis = Basis(Vector3.RIGHT, _side*(.18+q*1.32))
			_distal[d].basis = Basis(Vector3.RIGHT, _side*(.12+q*.96))
		else:
			var rotation := Basis(Vector3.RIGHT,q)
			if d==0: rotation = Basis(_thumb_axis,.32*q)*rotation
			node.basis = rotation*_homes[d]
	var palm := _seat_at(t, tip)
	if _seat!=null: _seat.position = palm-tip
	if _mounted:
		if not _rake:
			for j in range(_times.bsearch(t-.074),_times.bsearch(t+.155,false)):
				play_finger(_keys[j],t,palm)
	else:
		for d in DIGITS.size():
			if _nodes[d]!=null: _nodes[d].position = palm+_knuckles[d]
	return palm

# The wrist carriage is planned against the lowest string in its reach window.
# Seat the playing hand within that window at the measured horn pad. Only the
# palm and shank inherit this translation. The two carrier links close on it.
var _seat: Node3D
var swivel_offset: Vector3
var fold_direction: Vector3
var swivel_axis: Vector3
var _pole := PackedVector3Array()
var _times := PackedFloat64Array()
var _keys: Array[Touch] = []

class Touch:
	var time: float
	var digit: int
	var base: Vector3
	var offset: Vector3
	var pick: float
	var wire: StringMotionType
	var draw: Vector3

const StringMotionType := preload("res://string_motion.gd")

func seat(parts: Dictionary, aid: String, events: Array, layout: Dictionary, wires: Dictionary, motion: MotionBake) -> void:
	var palm: Node3D = parts["tool"]
	var parent := palm.get_parent()
	var swivel: Node3D = parts["wristhead"].get_node_or_null(NodePath(aid+"__carrier_seat"))
	# Earlier models carry only the baked wrist frame and four digit pivots.
	if swivel==null: return
	for d in DIGITS.size():
		if _nodes[d]==null: return
		var marker := _nodes[d].find_child(aid+"__pad_"+DIGITS[d],true,false) as Node3D
		if marker==null: return
		_pads.append(marker)
	_mounted = _nodes[0].get_parent()==palm and _pads[0].get_parent()!=_nodes[0]
	_seat = Node3D.new()
	swivel_offset = swivel.position
	fold_direction = swivel.basis.y
	swivel_axis = swivel.basis.x
	parent.add_child(_seat)
	for part in ["tool", "shank"]:
		parts[part].reparent(_seat, false)
	for d in DIGITS.size():
		var marker := _pads[d]
		_pole.append(marker.position)
		if _mounted:
			_distal.append(marker.get_parent())
			_middle.append(_distal[d].get_parent())
			_knuckles[d] = _nodes[d].position
			# The planted finger has bend in reserve for the lateral draw.
			var tip_local := _distal[d].position+Basis(Vector3.RIGHT,_side*.25)*marker.position
			_ready.append(Basis(Vector3.RIGHT,_side*.18)*(_middle[d].position+Basis(Vector3.RIGHT,_side*.45)*tip_local))
	for e in events:
		if e["actuator"] != aid: continue
		var times := ScoreDoc.string_times(e)
		for k in times.size():
			var key := Touch.new()
			key.time = times[k]
			key.digit = posmod(int(e.get("finger",1)),DIGITS.size())
			if _rake and not _digit.is_empty():
				key.digit = _digit[mini(_slip.bsearch(key.time-1e-6),_digit.size()-1)]
			var sid: String = e["strings"][k]
			var pick = e.get("pick")
			key.pick = float(layout["strings"][sid]["pick"] if pick==null else pick)
			key.wire = wires[sid]
			key.draw = key.wire.draw_at_release(key.time)
			key.base = MotionBake.contact(layout,sid,key.pick)
			key.offset = key.base-motion.tip_at(aid,key.time)
			_times.append(key.time)
			_keys.append(key)

func _offset(key: Touch) -> Vector3:
	return key.offset - _rest_pad(key)

func _seat_at(t: float, tip: Vector3) -> Vector3:
	if _keys.is_empty(): return tip
	var next := clampi(_times.bsearch(t),0,_keys.size()-1)
	var prev := maxi(0,next-1)
	var a := _keys[prev]
	var b := _keys[next]
	var gap := b.time-a.time
	var start := maxf(a.time+minf(.07,gap*.16), b.time-.64)
	var end := b.time-minf(.10,gap*.22)
	var u := _ease(clampf((t-start)/maxf(end-start,1e-6),0.,1.))
	var p := tip+_offset(a).lerp(_offset(b),u)
	var nearest := minf(absf(t-a.time),absf(t-b.time))
	p = tip.lerp(p,_ease(clampf((1.30-nearest)/.65,0.,1.)))
	var wa := _contact_weight(t-a.time) if a!=b else 0.
	var wb := _contact_weight(t-b.time)
	var total := wa+wb
	if total>0.:
		var placed := Vector3.ZERO
		if wa>0.: placed += wa*_placement(a)
		if wb>0.: placed += wb*_placement(b)
		p = p.lerp(placed/total,minf(total,1.))
	return p

func _placement(key: Touch) -> Vector3:
	if _mounted and not _rake: return key.base-_rest_pad(key)
	return key.base+key.wire.excursion_at(key.pick)-_rest_pad(key)

func _rest_pad(key: Touch) -> Vector3:
	var d := key.digit
	if not _mounted: return _knuckles[d]+_nodes[d].basis*_pole[d]
	if not _rake: return _knuckles[d]+_ready[d]-.50*key.draw
	return _knuckles[d]+_nodes[d].basis*(_middle[d].position+_middle[d].basis*(_distal[d].position+_distal[d].basis*_pole[d]))

# The wrist holds station during load. Solve the middle hinge by the cosine
# law, then aim the knuckle at the wire. After slip the horn follows through
# past the release point while the string oscillates on its own.
func play_finger(key: Touch,t: float,palm: Vector3) -> void:
	var age := t-key.time
	var blend := _ease(clampf((age+.155)/.091,0.,1.)) if age<=0. else 1.-_ease(clampf(age/.074,0.,1.))
	if blend<=0.: return
	var d := key.digit
	var load := clampf((age+.064)/.064,0.,1.)
	var curl := _side*lerpf(.22,.62,_ease(load))
	var tip_vector := _distal[d].position+Basis(Vector3.RIGHT,curl)*_pole[d]
	var knuckle_link := _middle[d].position
	var excursion := key.wire.excursion_at(key.pick) if age<=0. else key.draw*(1.+.8*_ease(clampf(age/.045,0.,1.)))
	var target := key.base+excursion-palm-_knuckles[d]
	var c := knuckle_link.y*tip_vector.y+knuckle_link.z*tip_vector.z
	var s := knuckle_link.z*tip_vector.y-knuckle_link.y*tip_vector.z
	var k := .5*(target.length_squared()-knuckle_link.length_squared()-tip_vector.length_squared())-knuckle_link.x*tip_vector.x
	var elbow := atan2(s,c)+_side*acos(clampf(k/maxf(Vector2(c,s).length(),1e-8),-1.,1.))
	var ray := knuckle_link+Basis(Vector3.RIGHT,elbow)*tip_vector
	var aim := Basis(Quaternion(ray.normalized(),target.normalized()))
	_nodes[d].basis = _nodes[d].basis.slerp(aim,blend)
	_middle[d].basis = _middle[d].basis.slerp(Basis(Vector3.RIGHT,elbow),blend)
	_distal[d].basis = _distal[d].basis.slerp(Basis(Vector3.RIGHT,curl),blend)

func _contact_weight(age: float) -> float:
	# Overlapping attack and recovery windows crossfade at fast tempi.
	if _rake: return _ease(clampf(1.-absf(age)/.028,0.,1.))
	return _ease(clampf((age+.16)/.096,0.,1.)) if age<=0. else _ease(clampf(1.-age/.075,0.,1.))
