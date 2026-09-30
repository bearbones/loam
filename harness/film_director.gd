class_name FilmDirector
extends RefCounted
## The film of the piece (`--film`): a camera and a lighting arc directed from
## the score's own cues, as a pure function of score time — so any frame can be
## rendered alone, in any order, and a render split across processes cuts
## together seamlessly (tools/render_film.sh).
##
## The score carries a camera script written with the piece (songs/chamber.py:
## wide-dark, arm0-close, arm2-run, overhead, rake-close, bars-close, wide-lit,
## pullback, all-arms). Each cue here becomes a MOVING shot: a push, an orbit, a
## crane, or a track that follows the arm the music is in. Cuts land on the cue,
## which the score put on a downbeat. A shot that follows an arm aims at its
## tool SMOOTHED over FOLLOW_S either side (the performance is known in
## advance, so the camera may anticipate like an operator who has read the
## score): the camera leans with a phrase, it does not twitch with a click.

const FOLLOW_S := .7
const FOLLOW_TAPS := 9

var bake: MotionBake
var layout: Dictionary
var total_s: float = 86.0
var shots: Array = []      # [{t0, t1, name, fn: Callable(u, t) -> {pos, target, fov, focus}}]
var light_keys: Array = [] # [[t, exposure, key, fill, rim, fog]]


func setup(b: MotionBake, lay: Dictionary, score: ScoreDoc) -> void:
	bake = b; layout = lay; total_s = score.total_s
	var cue_t := {}
	for c in score.cues:
		if c["kind"] == "camera": cue_t[c["name"]] = float(c["t"])
	var bar := 60.0/float(score.doc.get("bpm", 84.0))*4.0
	var t := func(name: String, fallback: float) -> float: return float(cue_t.get(name, fallback))
	var cuts := [
		["wide-dark", t.call("wide-dark", 0.0), _wide_dark],
		["arm0-close", t.call("arm0-close", 2*bar), _arm0_close],
		["arm2-run", t.call("arm2-run", 4*bar), _arm2_run],
		["overhead", t.call("overhead", 8*bar), _overhead],
		["rake-close", t.call("rake-close", 12*bar), _rake_close],
		["bars-close", t.call("bars-close", 16*bar), _bars_low],
		# the ratchet is the machine's showpiece: two bars into the mallets' entry
		# the camera goes round behind the rail to watch a pawl ride the teeth
		["bars-ratchet", t.call("bars-close", 16*bar)+2*bar, _bars_ratchet],
		["wide-lit", t.call("wide-lit", 20*bar), _wide_lit],
		["pullback", t.call("pullback", 24*bar), _pullback],
		["all-arms", t.call("all-arms", 27.5*bar), _all_arms],
	]
	for i in cuts.size():
		var t1: float = cuts[i+1][1] if i+1 < cuts.size() else total_s
		shots.append({"name": cuts[i][0], "t0": cuts[i][1], "t1": t1, "fn": cuts[i][2]})
	# The lighting arc: the hall is dark while the harp unfolds alone, comes
	# up as the piece gathers, is fully lit when every mechanism plays
	# (wide-lit), and goes back to dark through the ring-out.
	# [t, exposure, key, fill, rim, fog density]
	var lit: float = t.call("wide-lit", 20*bar)
	light_keys = [
		[0.0, 0.0, .25, .3, 2.6, .045],
		[3.5, .55, .35, .45, 2.4, .040],
		[t.call("arm0-close", 2*bar), .8, .8, .8, 2.2, .028],
		[t.call("overhead", 8*bar), .85, 1.0, 1.0, 2.0, .022],
		[t.call("bars-close", 16*bar), .95, 1.2, 1.1, 2.0, .018],
		[lit, 1.08, 1.45, 1.25, 2.1, .014],
		[t.call("pullback", 24*bar), 1.0, 1.35, 1.2, 2.0, .016],
		[t.call("all-arms", 27.5*bar), .85, 1.0, 1.0, 2.2, .022],
		[total_s-3.0, .6, .6, .7, 2.4, .030],
		[total_s, 0.0, .2, .3, 2.4, .045],
	]


## The shot at t: {pos, target, fov, focus (metres to the subject), name}.
func camera_at(t: float) -> Dictionary:
	var s: Dictionary = shots[0]
	for shot in shots:
		if t >= float(shot["t0"]): s = shot
	var u := clampf((t-float(s["t0"]))/maxf(float(s["t1"])-float(s["t0"]), .001), 0.0, 1.0)
	var c: Dictionary = (s["fn"] as Callable).call(u, t)
	c["name"] = s["name"]
	if not c.has("focus"): c["focus"] = (c["pos"] as Vector3).distance_to(c["target"])
	return c


## The lighting at t, interpolated between the arc's keys.
func light_at(t: float) -> Dictionary:
	var a: Array = light_keys[0]; var b: Array = light_keys[-1]
	for i in light_keys.size()-1:
		if t >= float(light_keys[i][0]) and t <= float(light_keys[i+1][0]):
			a = light_keys[i]; b = light_keys[i+1]; break
	var w := 0.0 if float(b[0]) <= float(a[0]) else _ease(clampf((t-float(a[0]))/(float(b[0])-float(a[0])), 0.0, 1.0))
	if t <= float(light_keys[0][0]): w = 0.0; b = a
	return {"exposure": lerpf(a[1], b[1], w), "key": lerpf(a[2], b[2], w), "fill": lerpf(a[3], b[3], w),
		"rim": lerpf(a[4], b[4], w), "fog": lerpf(a[5], b[5], w)}


static func _ease(u: float) -> float:
	return .5-.5*cos(PI*clampf(u, 0.0, 1.0))


static func _dir(az_deg: float, el_deg: float) -> Vector3:
	var az := deg_to_rad(az_deg); var el := deg_to_rad(el_deg)
	return Vector3(sin(az)*cos(el), sin(el), cos(az)*cos(el))


## An arm's tool, smoothed: a triangular window FOLLOW_S either side of t.
func follow(aids: Array, t: float) -> Vector3:
	var sum := Vector3.ZERO; var wsum := 0.0
	for k in FOLLOW_TAPS:
		var f := float(k)/float(FOLLOW_TAPS-1)*2.0-1.0
		var w := 1.0-absf(f)*.8
		for aid in aids:
			sum += bake.tip_at(aid, t+f*FOLLOW_S)*w; wsum += w
	return sum/wsum


func _center(mid: String, fallback: Vector3) -> Vector3:
	return MotionBake.v(layout["mechanisms"][mid]["center"]) if layout.get("mechanisms", {}).has(mid) else fallback


func _has(aid: String) -> bool: return bake.arms.has(aid)


# --- the shots ---------------------------------------------------------------

## Out of the dark: a slow push toward the harp as the lights come up.
func _wide_dark(u: float, _t: float) -> Dictionary:
	var e := _ease(u)
	return {"pos": Vector3(2.2, 4.4, 16.5).lerp(Vector3(1.1, 3.3, 10.2), e),
		"target": Vector3(0, 1.7, 0).lerp(Vector3(0, 2.15, 0), e), "fov": 38.0}


## The first pick arm, close from behind and to its side: an arm reaches from
## its carriage behind the machine forward to the strings, so it reads whole
## in profile, the strings it plucks beyond it. The camera drifts in.
func _arm0_close(u: float, t: float) -> Dictionary:
	var aid: String = "harp_arm0" if _has("harp_arm0") else str(bake.arms.keys()[0])
	var target := _arm_mid(aid, t)
	var az := lerpf(-128.0, -108.0, _ease(u))
	return {"pos": target+_dir(az, 20.0)*lerpf(3.3, 2.7, _ease(u)), "target": target, "fov": 38.0}


## Halfway along an arm, carriage to tool, its tool smoothed (see follow).
func _arm_mid(aid: String, t: float) -> Vector3:
	return (bake.vec(aid+".root", t)).lerp(follow([aid], t), .55)


## The low arm's run: high behind the machine's right side, orbiting round
## behind it, the arm reaching up from its low carriage to the strings.
func _arm2_run(u: float, t: float) -> Dictionary:
	var aid: String = "harp_arm2" if _has("harp_arm2") else str(bake.arms.keys()[0])
	var target := _arm_mid(aid, t)
	var az := lerpf(118.0, 172.0, _ease(u)); var el := lerpf(30.0, 22.0, _ease(u))
	return {"pos": target+_dir(az, el)*lerpf(3.6, 3.0, u), "target": target, "fov": 40.0}


## The pulse: high over the harp, turning slowly, the three arms working below.
func _overhead(u: float, _t: float) -> Dictionary:
	var c := _center("harp", Vector3(0, 2.05, 0))+Vector3(0, .2, -.9)
	var az := lerpf(-40.0, 25.0, u)
	return {"pos": c+_dir(az, 68.0)*7.2, "target": c, "fov": 42.0}


## The rake: from behind, turning round it, its arm between the lens and the
## strings it sweeps.
func _rake_close(u: float, t: float) -> Dictionary:
	var c := _center("rake", Vector3(-4.2, 2.65, .9))
	var target := c.lerp(_arm_mid("rake_arm0", t), .6) if _has("rake_arm0") else c
	var az := lerpf(222.0, 158.0, _ease(u))
	return {"pos": target+_dir(az, 18.0)*3.4, "target": target, "fov": 42.0}


## The mallets come in: low along the bars from the front, tracking both arms.
func _bars_low(u: float, t: float) -> Dictionary:
	var c := _center("bars", Vector3(4.5, 1.35, 1.2))
	var arms: Array = []
	for aid in ["bars_arm0", "bars_arm1"]: if _has(aid): arms.append(aid)
	var aim := follow(arms, t) if not arms.is_empty() else c
	var target := Vector3(lerpf(c.x, aim.x, .7), c.y+.35, c.z-.15)
	var off := Vector3(-.9, .15, 3.3).lerp(Vector3(-.4, .3, 2.7), _ease(u))
	return {"pos": target+off, "target": target, "fov": 40.0}


## Behind the rail: a mallet arm's carriage, pinion and pawl riding the rack,
## with the mallet dropping below.
func _bars_ratchet(u: float, t: float) -> Dictionary:
	var aid: String = "bars_arm0" if _has("bars_arm0") else str(bake.arms.keys()[0])
	var tip := follow([aid], t)
	var p := bake.pose(aid, t)
	var root := Vector3(tip.x, (p["root"] as Vector3).y, (p["root"] as Vector3).z)
	var target := root.lerp(tip, .35)
	var az := lerpf(208.0, 238.0, _ease(u))
	return {"pos": target+_dir(az, 12.0)*2.25, "target": target, "fov": 42.0}


## Every mechanism at once, fully lit, orbiting slowly.
func _wide_lit(u: float, _t: float) -> Dictionary:
	var c := Vector3(.4, 1.7, -.2)
	var az := lerpf(-22.0, 14.0, u)
	return {"pos": c+_dir(az, 16.0)*lerpf(10.8, 10.0, u), "target": c, "fov": 42.0}


## The coda: from close on the harp, pulling back and up as the music thins.
func _pullback(u: float, _t: float) -> Dictionary:
	var e := _ease(u)
	return {"pos": Vector3(.9, 2.7, 4.6).lerp(Vector3(2.2, 5.0, 12.5), e),
		"target": Vector3(0, 2.2, 0).lerp(Vector3(.4, 1.8, 0), e), "fov": 40.0}


## The last look: high from behind the machine, all its arms in view, as the
## lights go down on the ring-out.
func _all_arms(u: float, _t: float) -> Dictionary:
	var c := Vector3(.4, 1.8, -.6)
	var az := lerpf(212.0, 196.0, u)
	return {"pos": c+_dir(az, 28.0)*lerpf(9.0, 10.5, u), "target": c, "fov": 44.0}
