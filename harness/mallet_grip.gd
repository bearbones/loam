extends RefCounted
## Independent mallet rotation about each stick's proximal pin. The inner
## slide follows the second pin while the outer tube stays on the first.

var _times := PackedFloat64Array()
var _apices := PackedFloat64Array()
var _fingers := PackedInt32Array()
var _starts := PackedFloat64Array()
var _ends := PackedFloat64Array()
var _from := PackedFloat64Array()
var _to := PackedFloat64Array()
var _initial: float
var _pitch: float
var _head_seat: Node3D
var _housing_seat: Node3D
var slide: Node3D
var head_a: Vector3
var head_b: Vector3
var hinge: Vector3
var swing_a: Basis
var swing_b: Basis
var width: float
var dial: float

func bind(parts: Dictionary, inner: Node3D, plan: Dictionary) -> void:
	var parent: Node3D = parts["tool"].get_parent()
	if inner!=null:
		_head_seat = Node3D.new()
		_housing_seat = Node3D.new()
		parent.add_child(_head_seat)
		parent.add_child(_housing_seat)
		parts["tool"].reparent(_head_seat,false)
		parts["shank"].reparent(_housing_seat,false)
	slide = inner
	_initial = plan["dx_init"]
	_pitch = plan["dx_base"]
	for n in plan["notes"]:
		_times.append(n["t"])
		_apices.append(n["t_apex"])
		_fingers.append(n["finger"])
	for s in plan["segs"]:
		_starts.append(s[0])
		_ends.append(s[1])
		_from.append(s[2])
		_to.append(s[3])

static func _ease(u: float) -> float:
	return u*u*u*(10.0+u*(-15.0+6.0*u))

func apply(t: float, tip: Vector3, swing: float, side: float) -> void:
	var j := _starts.bsearch(t,false)-1
	width = _initial
	if j>=0:
		var u := clampf((t-_starts[j])/(_ends[j]-_starts[j]),0.,1.)
		width = lerpf(_from[j],_to[j],_ease(u))
	dial = (width-_pitch)/.032
	var lift := 0.
	if not _times.is_empty():
		var next := mini(_times.bsearch(t),_times.size()-1)
		var prev := maxi(0,next-1)
		var gap := _times[next]-_times[prev]
		var start := maxf(_times[prev]+minf(.035,.12*gap),_apices[next]-.20)
		var end := maxf(start+.001,_times[next]-minf(.038,.12*gap))
		var u := _ease(clampf((t-start)/(end-start),0.,1.))
		lift = lerpf(_fingers[prev],_fingers[next],u)
	var drive := Basis(Vector3.RIGHT,side*swing)
	var shaft_pin := Vector3(0,.055,side*.50)
	hinge = tip+drive*shaft_pin
	if slide==null:
		# Earlier two-stick models have a rigid guide cast into the sector.
		dial = (width-_pitch)/.40
		swing_a = drive
		swing_b = drive
		head_a = tip
		head_b = tip+Vector3.RIGHT*width
		return
	swing_a = Basis(Vector3.RIGHT,side*(swing+.215*lift))
	swing_b = Basis(Vector3.RIGHT,side*(swing+.215*(1.-lift)))
	head_a = hinge-swing_a*shaft_pin
	head_b = hinge+Vector3.RIGHT*width-swing_b*shaft_pin
	_head_seat.position = head_a-tip
	_housing_seat.position = hinge-tip
	slide.position = hinge+Vector3.RIGHT*width
