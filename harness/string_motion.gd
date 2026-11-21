extends RefCounted
## One speaking wire. Bind the score and both materials once, then sample
## only contacts whose finite-difference clip can still reach the playhead.

const NODES := 24
const PULL_S := 0.064
const MAX_TAIL_S := 5.0

class Contact:
	var time: float
	var gain: float
	var release_m: float
	var omega: float
	var draw: Vector3
	var tent := PackedFloat32Array()
	var offset: int
	var stride: int
	var nodes: int
	var frames: int
	var rate: float
	var step: float

class WireFrame:
	var displacement := PackedFloat32Array()
	var envelope := PackedFloat32Array()

	func _init() -> void:
		displacement.resize(NODES)
		envelope.resize(NODES)

var _contacts: Array[Contact] = []
var _times := PackedFloat64Array()
var _samples: PackedFloat32Array
var _tail := 0.0
var _wire: ShaderMaterial
var _blur: ShaderMaterial
var _sheath: MeshInstance3D
var _front := WireFrame.new()
var _back := WireFrame.new()
var _ringing := false
var _direction: Vector3

func bind(holder: Node3D, spec: Dictionary, hits: Array, score: ScoreDoc, arms: Dictionary = {}) -> void:
	_direction = holder.basis * Vector3(2.0 if spec.get("mid") == "harp" else .35, 0, 1)
	_wire = holder.get_child(0).material_override
	_sheath = holder.get_child(1)
	_blur = _sheath.material_override
	_sheath.visible = false
	_samples = score.shapes
	hits.sort_custom(func(a, b): return a["t"] < b["t"])
	for hit in hits:
		var e: Dictionary = hit["event"]
		var c := Contact.new()
		c.time = hit["t"]
		c.gain = float(e["amp"]) * .035
		if spec.get("mid") == "harp" and e.get("kind", "pluck") == "pluck":
			var mount: Dictionary = arms.get(e["actuator"],{}).get("pillar_player",{})
			if not mount.is_empty():
				_direction = holder.basis*Vector3(-2,0,1)
				_wire.set_shader_parameter("cross_axis",-2.)
				_blur.set_shader_parameter("cross_axis",-2.)
			c.omega = TAU*440.*pow(2.,(float(spec["midi"])-69.)/12.)
			c.release_m = (.016 + .008 * float(e["amp"])) *float(mount.get("side",1.)) / sqrt(5.0)
			var value = e.get("pick")
			var pick := float(spec.get("pick",.5) if value==null else value)
			c.tent.resize(NODES)
			for i in NODES:
				var u := float(i) / (NODES - 1)
				c.tent[i] = u / maxf(pick, 1e-6) if u <= pick else (1.0-u) / maxf(1.0-pick, 1e-6)
			c.draw = _direction*c.release_m*_line_at(c.tent,pick)
		var clip: Dictionary = score.clips.get(e.get("shape"), {})
		if not clip.is_empty():
			c.offset = int(clip["offset"])
			c.stride = int(clip["nodes"])
			c.nodes = mini(NODES, c.stride)
			c.frames = int(clip["frames"])
			c.rate = float(clip["rate_hz"])
			c.step = 1.0 / c.rate
			_tail = maxf(_tail, minf(MAX_TAIL_S, (c.frames + 4) * c.step))
		_contacts.append(c)
		_times.append(c.time)

func draw_at_release(t: float) -> Vector3:
	var index := _times.bsearch(t)
	return _contacts[index].draw if index<_contacts.size() and is_equal_approx(_times[index],t) else Vector3.ZERO

func last_contact(t: float) -> float:
	var past := _times.bsearch(t, false)
	return _times[past-1] if past > 0 else -INF

func apply(t: float) -> void:
	var first := _times.bsearch(t - _tail)
	var end := _times.bsearch(t + PULL_S, false)
	if first == end and not _ringing:
		return
	_back.displacement.fill(0.0)
	_back.envelope.fill(0.0)
	for j in range(first, end):
		var c := _contacts[j]
		var age := t - c.time
		if age < 0:
			if c.tent.is_empty() or age < -PULL_S: continue
			var w := (age + PULL_S) / PULL_S
			var pull := c.release_m * (w*w*w*(4.0+w*(-4.5+1.5*w)))
			for i in NODES:
				_back.displacement[i] += pull * c.tent[i]
		elif age <= MAX_TAIL_S and c.frames > 0:
			_sample(c, age)
	var peak := 0.0
	for i in NODES:
		var excursion := maxf(_back.envelope[i], absf(_back.displacement[i]))
		peak = maxf(peak, excursion)
	if peak == 0.0 and not _ringing:
		return
	_ringing = peak > 0.0
	# Keep the last uploaded arrays immutable while computing the next frame.
	var old := _front
	_front = _back
	_back = old
	var excitation := clampf(peak / .02, 0.0, 1.0)
	_wire.set_shader_parameter("disp", _front.displacement)
	_wire.set_shader_parameter("envelope", _front.envelope)
	_wire.set_shader_parameter("excitation", excitation)
	_blur.set_shader_parameter("disp", _front.displacement)
	_blur.set_shader_parameter("envelope", _front.envelope)
	# Catmull-Rom can overshoot the node peaks. Hide only an entirely silent sheath.
	_sheath.visible = _ringing

func _sample(c: Contact, age: float) -> void:
	var frame := int(age * c.rate)
	if frame < c.frames:
		var base := c.offset + frame * c.stride
		if c.tent.is_empty():
			for i in c.nodes:
				_back.displacement[i] += _samples[base+i] * c.gain
		else:
			var attack := 1.0 - exp(-age / .045)
			var amplitude := c.release_m * exp(-age / .16)
			var release := amplitude*cos(c.omega*age)
			for i in c.nodes:
				_back.displacement[i] += release*c.tent[i] + _samples[base+i]*c.gain*attack*.25
				_back.envelope[i] = maxf(_back.envelope[i],absf(amplitude)*c.tent[i])
	for k in range(1, 5):
		var past := age - k * c.step
		if past < 0.0: break
		var f := int(past * c.rate)
		if f >= c.frames: continue
		var base := c.offset + f * c.stride
		for i in c.nodes:
			_back.envelope[i] = maxf(_back.envelope[i], absf(_samples[base+i] * c.gain))

# Sample the same 48 longitudinal mesh intervals and Catmull-Rom values as
# wire_string.gdshader, including the residual motion of earlier notes.
func excursion_at(u: float) -> Vector3:
	if not _ringing: return Vector3.ZERO
	return _direction*_line_at(_front.displacement,u)

static func _line_at(data: PackedFloat32Array, u: float) -> float:
	var ring := clampf(u,0.,1.)*48.
	var i := floori(ring)
	return lerpf(_spline(data,i/48.),_spline(data,mini(i+1,48)/48.),ring-i)

static func _spline(d: PackedFloat32Array,u: float) -> float:
	var k := u*(NODES-1)
	var i := floori(k)
	return cubic_interpolate(d[i],d[mini(i+1,NODES-1)],d[maxi(i-1,0)],d[mini(i+2,NODES-1)],k-i)
