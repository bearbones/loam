class_name ClockworkMotion
extends RefCounted
## Stateless, seekable score-to-rig evaluation. All contacts include rake offsets.
var score: ScoreDoc
var geometry: Dictionary
var plans: Dictionary = {}
var acts: Dictionary = {}

func setup(sd: ScoreDoc, layout: Dictionary) -> void:
	score = sd
	geometry = layout
	for m in sd.mechs:
		for a in m["actuators"]:
			acts[a["id"]] = a
			plans[a["id"]] = []
	for e in sd.events:
		if e.get("actuator") != null and plans.has(e["actuator"]):
			plans[e["actuator"]].append(e)
	for aid in plans:
		plans[aid].sort_custom(func(a, b): return float(a["t_move"]) < float(b["t_move"]))

func v(a: Array) -> Vector3:
	return Vector3(a[0], a[1], a[2])

func contact(sid: String, pick = null) -> Vector3:
	var s: Dictionary = geometry["strings"][sid]
	var u := .5 if s["struck"] else float(s["pick"] if pick == null else pick)
	return v(s["a"]).lerp(v(s["b"]), u)

func clearance(aid: String) -> Vector3:
	return Vector3(0, .22, 0) if geometry["strings"][acts[aid]["home"]]["struck"] else Vector3(0, 0, -.22)

func smooth(u: float) -> float:
	u = clampf(u, 0, 1)
	return u*u*(3-2*u)

func tip_at(aid: String, t: float) -> Vector3:
	var lift := clearance(aid)
	var rest := contact(acts[aid]["home"]) + lift
	for e in plans[aid]:
		var tm := float(e["t_move"])
		if t < tm:
			return rest
		var hit := float(e["t"])
		var ids: Array = e["strings"]
		var first := contact(ids[0], e.get("pick"))
		var last := contact(ids[-1], e.get("pick"))
		var spread := float(e.get("spread_s", 0))
		var end := hit + spread*(ids.size()-1)
		if t < hit:
			var approach := hit - float(acts[aid]["approach_s"])
			# A zero-travel rake still repositions during its approach interval.
			if approach > tm + .000001 and t < approach:
				return rest.lerp(first+lift, smooth((t-tm)/(approach-tm)))
			var start := maxf(tm, approach)
			var origin := first+lift if approach > tm+.000001 else rest
			var u := clampf((t-start)/maxf(hit-start,.000001),0,1)
			return origin.lerp(first,smooth(u)) + lift*.45*sin(PI*u)
		if t <= end:
			if ids.size()==1 or spread<=0:
				return first
			var index := minf((t-hit)/spread,ids.size()-1)
			var k := mini(int(index),ids.size()-2)
			# Linear sweep crosses each string at the exact audible sub-onset.
			return contact(ids[k],e.get("pick")).lerp(contact(ids[k+1],e.get("pick")),index-k)
		if t < float(e["t_free"]):
			return last + lift*smooth((t-end)/maxf(float(e["t_free"])-end,.000001))
		rest = last+lift
	return rest

func pose(aid: String, t: float) -> Dictionary:
	var cfg: Dictionary = geometry["arms"][aid]
	var tip := tip_at(aid,t)
	var root := Vector3(tip.x,float(cfg["root_y"]),float(cfg["root_z"]))
	var delta := tip+Vector3(0,.15,0)-root
	var distance := delta.length()
	var l1 := float(cfg["l1"])
	var l2 := float(cfg["l2"])
	var d := clampf(distance,absf(l1-l2)+.00001,l1+l2-.00001)
	var direction := delta.normalized()
	var along := (l1*l1-l2*l2+d*d)/(2*d)
	var bend := Vector3.UP - direction*direction.dot(Vector3.UP)
	if bend.length_squared()<.00001:
		bend=Vector3.FORWARD
	var elbow := root + direction*along + bend.normalized()*sqrt(maxf(0,l1*l1-along*along))
	return {"root":root,"elbow":elbow,"tip":tip,"reachable":distance<=l1+l2 and distance>=absf(l1-l2)}
