extends RefCounted
## One voiced shell or tongue. The first mode has fixed mounting nodes.
## Integrate the vibration over a short shutter so high pitches do not alias
## into large slow movements when the film is sampled at 30 frames/s.

var _node: MeshInstance3D
var _times := PackedFloat64Array()
var _strength := PackedFloat64Array()
var _decay: float
var _omega: float
var _tail: float
var _shutter_gain: float
var _moving := false

func bind(node: MeshInstance3D, spec: Dictionary, hits: Array) -> void:
	_node = node
	_decay = .56 if spec["mid"]=="bells" else (.075 if spec["mid"]=="blocks" else .28)
	_tail = 6.*_decay
	_omega = TAU*440.*pow(2.,(float(spec["midi"])-69.)/12.)
	var window := _omega/480.
	_shutter_gain = sin(window)/window
	hits.sort_custom(func(a,b): return a["t"]<b["t"])
	for hit in hits:
		_times.append(hit["t"])
		_strength.append(hit["event"]["amp"])

func apply(t: float) -> void:
	var begin := _times.bsearch(t-_tail)
	var end := _times.bsearch(t,false)
	if begin==end and not _moving: return
	var amplitude := 0.
	for i in range(begin,end):
		var age := t-_times[i]
		amplitude += _strength[i]*exp(-age/_decay)*sin(age*_omega)
	_node.set_blend_shape_value(0,clampf(amplitude*_shutter_gain,-1.,1.))
	_moving = begin<end
