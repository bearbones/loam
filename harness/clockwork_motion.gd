class_name ClockworkMotion
extends RefCounted
## Stateless, seekable score-to-rig evaluation. All contacts include rake offsets.
var score: ScoreDoc
var geometry: Dictionary
var plans: Dictionary = {}
var acts: Dictionary = {}
var mech_of: Dictionary = {}
var sched: Dictionary = {}
var blows_by_arm: Dictionary = {}    # the recoil bus, per striking arm
var blows_by_mech: Dictionary = {}   # ...and per instrument, for its stand

func setup(sd: ScoreDoc, layout: Dictionary) -> void:
	score = sd
	geometry = layout
	for m in sd.mechs:
		for a in m["actuators"]:
			acts[a["id"]] = a
			mech_of[a["id"]] = m["id"]
			plans[a["id"]] = []
	for e in sd.events:
		if e.get("actuator") != null and plans.has(e["actuator"]):
			plans[e["actuator"]].append(e)
	for aid in plans:
		plans[aid].sort_custom(func(a, b): return float(a["t_move"]) < float(b["t_move"]))
	_schedules()

func v(a: Array) -> Vector3:
	return Vector3(a[0], a[1], a[2])

func contact(sid: String, pick = null) -> Vector3:
	var s: Dictionary = geometry["strings"][sid]
	var u := .5 if s["struck"] else float(s["pick"] if pick == null else pick)
	return v(s["a"]).lerp(v(s["b"]), u)

func clearance(aid: String) -> Vector3:
	return Vector3(0, .22, 0) if geometry["strings"][acts[aid]["home"]]["struck"] else Vector3(0, 0, -.22)

static func smooth(u: float) -> float:
	u = clampf(u, 0, 1)
	return u*u*(3-2*u)

## Two motion vocabularies (docs/motion-design.md), mirrored in formlab/rig.py.
## A mallet arm is a stepped machine: its carriage advances along the rack in
## ratchet clicks (one tooth a click, a little overshoot that rings out on the
## pawl), the mallet cocks and drops onto the bar, and the blow sets the whole
## assembly shuddering (recoil). A pick or rake arm is a servo: jerk-limited
## S-curve slews, no overshoot, nothing rings.
const PITCH := TAU*.12/16        # the rack's tooth pitch (formlab.clearance.PINION)
const CLICK_S := .09             # seconds a ratchet click takes when the score allows
const CLICK_MIN_S := .04         # ...and the least it may take when it does not
const CLICK_MOVE := .4           # fraction of a click spent moving; the rest rings and holds
const OVERSHOOT := .10           # of a tooth, past the detent (the pawl's play)
const RING_HZ := 14.0
const RING_TAU := .09
const SLEW_S := .4               # a servo slew takes this long when the score allows
const CLICK_TEETH_MAX := 4       # ...and a hurried click spans no more teeth than this
const SERVO_V_MAX := 3.0         # m/s: the fastest a servo carriage runs
const WORLD_SCALE := 3.0         # score position units -> rig metres (tools/build_clockwork.py)
const SCURVE_RAMP := .3          # fraction of a slew spent accelerating (and decelerating)
const COCK := .5                 # a mallet rises this much of its lift again before it drops
const COCK_AT := .4              # ...by this fraction of the strike interval
# The assembly after a blow: [amplitude, Hz, decay s]; x shakes the carriage along
# the rail, z the mallet across the bar, and the bounce lifts it (of the lift).
const RECOIL := {"x": [.004, 11.0, .14], "z": [.0025, 17.0, .10], "bounce": [.06, 8.0, .16]}
const RECOIL_GATE := .08         # the shudder is gone this long before the next strike begins
const PAD := .01                 # overshoot and recoil, when an early move is checked for clearance
# The blow shakes the ASSEMBLY, not only the arm (docs/motion-design.md, "The
# blow shakes the assembly"): [amplitude, Hz, decay s] each, driven from the
# recoil bus below. Every amplitude is a named constant because the operator
# tunes them by eye. Reasoning for the numbers is in the doc.
const STAND_THUMP := [.0015, 9.0, .12]   # the instrument's stand, vertically (m)
const RAIL_SAG := [.001, 12.0, .15]      # the rail's first bending mode, at mid-span (m)
const MAST_SWAY := [.0003, 6.0, .30]     # the gantry swaying about its plinths (rad)
const BLOW_DROP_REF := .33               # a full blow: 0.22 m of lift risen COCK again
const SHUDDER_GAIN := 1.0                # ...all three together: the one dial to tune by eye
const SHUDDER_TAIL := 1.0                # a ring is spent this long after its blow
const RAIL_OVER := .26                   # the guide bars run this far past the reach window (formlab.gantry)
# A HINGED HAMMER (kind == "hammer"): the arm positions and dips a little, and a
# head hinged on a pin at the shank's end does the rest of the blow. It lies
# back on a felt-faced check at rest, swings a touch further, falls, strikes,
# and the check catches the rebound. ARM_SHARE of the contact's clearance is the
# arm's dip; the flip supplies the remainder, which is what sets the rest angle.
# Mirrors formlab.rig.HAMMER.
const HEAD_L := .12                      # hinge to the felt face
const HEAD_R := .045                     # the felt head's radius
const HEAD_ARM_SHARE := .30              # of the clearance lift the ARM provides
const HEAD_COCK := .02                   # ...sunk this much further into the check's felt
const HEAD_CHECK := [.10, 12.5, .045]    # the rebound the check takes: [rad, Hz, decay s]

func stepped(aid: String) -> bool:
	return String(acts[aid]["kind"]) in ["mallet", "hammer"]

func hammer(aid: String) -> bool:
	return String(acts[aid]["kind"]) == "hammer"

## What the TOOL FRAME's origin clears the contact by. For a rigid tool that is
## the contact's own clearance; a hinged hammer's arm hovers only HEAD_ARM_SHARE
## of it, because the head lying back on its check holds the felt the rest up.
func hover(aid: String) -> Vector3:
	var lift := clearance(aid)
	return lift*HEAD_ARM_SHARE if hammer(aid) else lift

## The flip angle at which the felt face clears by the whole lift while the arm
## hovers at `hover`: HEAD_L*(1-cos) covers the remainder.
func rest_angle(aid: String) -> float:
	if not hammer(aid): return 0.0
	var rise := (clearance(aid)-hover(aid)).length()
	return acos(clampf(1.0-rise/HEAD_L, -1.0, 1.0))

## Which way the head swings back: toward its own rail, never across the
## instrument. Derived from the geometry so both implementations agree.
func flip_sign(aid: String) -> float:
	var cfg: Dictionary = geometry["arms"][aid]
	return 1.0 if float(cfg["root_z"]) >= contact(acts[aid]["home"]).z else -1.0

## Where a hinged head's felt face sits relative to the tool frame's origin.
## The hinge is HEAD_L above the origin and the face swings on it. Zero at
## theta = 0, which is why the blow is exact.
static func head_offset(theta: float, sign: float) -> Vector3:
	return Vector3(0.0, HEAD_L*(1-cos(theta)), HEAD_L*sin(theta)*sign)

## Minimum-jerk step: zero velocity and acceleration at both ends.
func quintic(u: float) -> float:
	u = clampf(u, 0, 1)
	return u*u*u*(10-15*u+6*u*u)

## Jerk-limited slew: smooth acceleration ramp, constant-velocity cruise, mirror
## ramp — the profile of a telescope drive. Ramps integrate smoothstep.
func scurve(u: float) -> float:
	u = clampf(u, 0, 1)
	var r := SCURVE_RAMP
	var s: float
	if u < r: s = r*_ramp(u/r)
	elif u <= 1-r: s = r*.5+(u-r)
	else: s = (1-r)-r*_ramp((1-u)/r)
	return s/(1-r)

static func _ramp(w: float) -> float:
	return w*w*w-w*w*w*w*.5

## A carriage travel of dx is this many teeth of the rack...
func teeth(dx: float) -> int:
	return maxi(1, int(floor(absf(dx)/PITCH+.5)))

## ...taken one a click, but never faster than CLICK_MIN_S when the window T
## is short (then a click spans several teeth).
func clicks(dx: float, T: float) -> int:
	return mini(teeth(dx), maxi(1, int(floor(T/CLICK_MIN_S))))

## What a reposition of dx WANTS, by vocabulary — the mirror of
## loam.motion_timing.travel_s, which is what the score planner charged this
## move. A stepped arm clicks a tooth at a time; a servo needs its S-curve's
## ramps however short the move, and its top speed however long.
func travel_want(kind: String, dx: float) -> float:
	if absf(dx) <= 0.0: return 0.0
	if kind == "mallet" or kind == "hammer": return teeth(dx)*CLICK_S
	return maxf(SLEW_S, absf(dx)/SERVO_V_MAX)

## The least time that reposition can take: the ratchet cannot click faster
## than CLICK_MIN_S nor span more than CLICK_TEETH_MAX teeth at once, and a
## servo has only its top speed. Below this there is no machine (the planner
## refuses the contact; loam.motion_timing.floor_s).
func travel_floor(kind: String, dx: float) -> float:
	if absf(dx) <= 0.0: return 0.0
	if kind == "mallet" or kind == "hammer":
		return ceil(float(teeth(dx))/float(CLICK_TEETH_MAX))*CLICK_MIN_S
	return absf(dx)/SERVO_V_MAX

## Ratchet advance over u in [0,1] in n clicks: each click moves in its first
## CLICK_MOVE with a minimum-jerk step to `over` (of a click) past the detent,
## then rings out on the pawl at RING_HZ and holds. The window is T seconds.
func ratchet(u: float, n: int, T: float, over: float) -> float:
	u = clampf(u, 0, 1)
	var k := mini(int(floor(u*n)), n-1)
	var w := u*n-k
	var p: float
	if w < CLICK_MOVE:
		p = quintic(w/CLICK_MOVE)*(1+over)
	else:
		var tr := (w-CLICK_MOVE)*T/n
		var fade := 1.0-smooth((w-.7)/.3)
		p = 1+over*exp(-tr/RING_TAU)*cos(TAU*RING_HZ*tr)*fade
	return (k+p)/n

## Repositioning from a to b over u in [0,1] (T seconds): clicks along the rail
## (x) with the arm following in one minimum-jerk move, or one S-curve slew.
## The overshoot is a tenth of a tooth however many teeth a click spans.
func travel(a: Vector3, b: Vector3, u: float, T: float, clicky: bool) -> Vector3:
	if not clicky: return a.lerp(b, scurve(u))
	var p := a.lerp(b, quintic(u))
	var n := clicks(b.x-a.x, T)
	var over := OVERSHOOT*minf(1.0, PITCH*n/maxf(absf(b.x-a.x), .000001))
	p.x = a.x+(b.x-a.x)*ratchet(u, n, T, over)
	return p

## The strike from origin onto first over u in [0,1]: a mallet cocks, then drops
## with the acceleration of a fall; a pick winds up away from the string and
## sweeps in on a minimum-jerk curve.
func strike(origin: Vector3, first: Vector3, lift: Vector3, u: float, clicky: bool) -> Vector3:
	if not clicky: return origin.lerp(first, quintic(u))+lift*.45*sin(PI*u)
	return origin.lerp(first+lift, quintic(u))+lift*(cocked(u, COCK)-1)

## The cocked drop's height profile: 1 at the start, lifted to 1+c at COCK_AT,
## then falling as 1-v^2 to exactly 0 at the blow. Used for a stepped arm's
## lift and, scaled by its rest angle, for a hinged hammer's flip — one
## profile, so the two stay in phase. Mirrors formlab.rig.cocked.
static func cocked(u: float, c: float) -> float:
	u = clampf(u, 0, 1)
	if u < COCK_AT: return 1+c*smooth(u/COCK_AT)
	var v := (u-COCK_AT)/(1-COCK_AT)
	return (1+c)*(1-v*v)

## The hinged head's flip angle at t: `rest_angle` lying back on its check,
## cocked a touch further over the strike, exactly 0 at the blow, then the
## rebound the check takes, and back to rest. Mirrors formlab.rig.head_angle.
func head_angle(aid: String, t: float) -> float:
	if not hammer(aid): return 0.0
	var rest := rest_angle(aid)
	for s in sched[aid]:
		if t < s["go"]: return rest
		if t < s["hit"]:
			# travelling with the head laid back; the flip is the strike itself
			if s["moving"] and t < s["approach"]: return rest
			var start: float = s["approach"] if s["moving"] else maxf(s["tm"], s["approach"])
			var u := clampf((t-start)/maxf(s["hit"]-start, .000001), 0.0, 1.0)
			return rest*cocked(u, HEAD_COCK)
		if t <= s["end"]: return 0.0
		if t < s["t_free"]:
			# the head bounces off the bar and the check takes it: |damped sine|
			# so the felt never passes through the string it just hit, fading
			# into the lay-back as the arm releases.
			var tau: float = t-s["end"]
			var w := quintic((t-s["end"])/maxf(s["t_free"]-s["end"], .000001))
			var bounce: float = float(HEAD_CHECK[0])*absf(exp(-tau/float(HEAD_CHECK[2]))*sin(TAU*float(HEAD_CHECK[1])*tau))
			return rest*w+bounce*(1-w)
	return rest

static func _ring(p: Array, tau: float) -> float:
	return float(p[0])*exp(-tau/float(p[2]))*sin(TAU*float(p[1])*tau)

## The assembly's shudder after a mallet blow: zero at the blow, rung out and
## gated to nothing by the time the next strike begins, so contacts stay exact.
func recoil(aid: String, t: float) -> Vector3:
	if not stepped(aid): return Vector3.ZERO
	# A hinged hammer recoils in its HEAD and its check, not in the whole arm
	# (head_angle): the arm holds the contact while the head bounces.
	if hammer(aid): return Vector3.ZERO
	var hit := -INF
	var gate_end := INF
	for s in sched[aid]:
		if s["hit"] <= t: hit = s["hit"]
		else:
			gate_end = s["approach"]; break
	if hit == -INF: return Vector3.ZERO
	var tau := t-hit
	var gate := 1.0-smooth((t-(gate_end-RECOIL_GATE))/RECOIL_GATE)
	var lift := hover(aid)
	return Vector3(_ring(RECOIL["x"], tau), lift.y*absf(_ring(RECOIL["bounce"], tau)), _ring(RECOIL["z"], tau))*gate

## Each event's timing as the path uses it. Repositioning starts as soon as
## the arm is free and the move wants (`g0`), never later than the score's
## t_move: a machine moves, then waits. The score planner only promised the
## mechanism's arm clearance from t_move on, so an earlier start is checked
## here against the siblings under the planner's own occupancy model — an arm
## owns the whole x interval it crosses while it may be moving (from its own
## g0, since it may start early too) and hovers over its last contact after —
## and pushed later until the interval it wants is clear. The planner charges
## the same travel from the same numbers now, so `g0 == tm` and this sweep has
## nothing left to push; formlab/rig.py counts the exceptions for the ruler.
func _windows(aid: String) -> Array:
	var lift := hover(aid)
	var rest := contact(acts[aid]["home"])+lift
	var free_prev := -INF
	var out: Array = []
	for e in plans[aid]:
		var tm := float(e["t_move"])
		var hit := float(e["t"])
		var ids: Array = e["strings"]
		var first := contact(ids[0], e.get("pick"))
		var last := contact(ids[-1], e.get("pick"))
		var spread := float(e.get("spread_s", 0))
		var approach := hit-float(acts[aid]["approach_s"])
		# `want` is what this move would take unhurried, by the same function
		# the planner charged it with (loam.motion_timing) but over the
		# distance the rendered arm really crosses. The planner already gave
		# it everything it could, so the start is the score's.
		var want := travel_want(acts[aid]["kind"], first.x-rest.x)
		var g0 := maxf(free_prev, tm)
		var lo := rest.x
		var hi := rest.x
		var plo := first.x
		var phi := first.x
		for sid in ids:
			var x := contact(sid, e.get("pick")).x
			lo = minf(lo, x); hi = maxf(hi, x); plo = minf(plo, x); phi = maxf(phi, x)
		out.append({"event": e, "rest": rest, "first": first, "last": last, "spread": spread, "tm": tm, "g0": g0, "go": g0,
			"approach": approach, "hit": hit, "end": hit+spread*(ids.size()-1), "t_free": float(e["t_free"]), "lo": lo, "hi": hi,
			"want": want, "mlo": minf(rest.x, first.x), "mhi": maxf(rest.x, first.x), "plo": plo, "phi": phi, "moving": false})
		rest = last+lift
		free_prev = float(e["t_free"])
	return out

## One arm's whole occupancy of the rail as [t0, t1, lo, hi] spans. Three phases
## a contact, because the interval an arm CROSSED is not where it stands: it
## owns everything between where it left and where it lands until it arrives,
## then only the strings it is playing, then the one it hovers over. Mirrors
## loam.score._Solver's model exactly — that is the point of the plan it checks.
func _segments(aid: String, win: Array) -> Array:
	var home := contact(acts[aid]["home"]).x
	var segs: Array = [[-INF, win[0]["go"] if win.size() > 0 else INF, home, home]]
	for i in win.size():
		var o: Dictionary = win[i]
		var until: float = win[i+1]["go"] if i+1 < win.size() else INF
		segs.append([o["go"], o["approach"], o["mlo"], o["mhi"]])
		segs.append([o["approach"], o["end"], o["plo"], o["phi"]])
		segs.append([o["end"], until, o["last"].x, o["last"].x])
	return segs

func _schedules() -> void:
	var win: Dictionary = {}
	for aid in plans: win[aid] = _windows(aid)
	for aid in plans:
		var need := float(geometry["mechanisms"][mech_of[aid]].get("arm_clearance_m", 0.0)) if geometry.has("mechanisms") else 0.0
		for s in win[aid]:
			var go: float = s["g0"]
			if need > 0.0:
				for other in plans:
					if other == aid or mech_of[other] != mech_of[aid]: continue
					for seg in _segments(other, win[other]):
						if seg[0] >= s["approach"] or seg[1] <= go: continue
						if maxf(s["mlo"]-seg[3], seg[2]-s["mhi"])-PAD < need: go = maxf(go, minf(seg[1], s["approach"]))
			s["go"] = go
			s["moving"] = s["approach"] > go+.000001
		sched[aid] = win[aid]
	_bus()

## The recoil bus: one entry a blow, shared by every rigid-body shudder so the
## stand, the rail and the gantry answer the same hits the arm's own recoil does.
## A blow records where it landed along the rail and how hard — the score's
## amplitude times the cocked drop's height, 1.0 for a full-amplitude mallet —
## and the time its arm's NEXT strike begins, which gates its ring to nothing.
func _bus() -> void:
	blows_by_arm.clear(); blows_by_mech.clear()
	for aid in plans:
		if not stepped(aid): continue
		var energy_scale: float = clearance(aid).y*(1+COCK)/BLOW_DROP_REF
		var mid: String = mech_of[aid]
		var list: Array = []
		for i in sched[aid].size():
			var s: Dictionary = sched[aid][i]
			list.append({"t": float(s["hit"]), "aid": aid, "mid": mid, "x": float(s["first"].x),
				"energy": float(s["event"].get("amp", 1.0))*energy_scale,
				"gate_end": float(sched[aid][i+1]["approach"]) if i+1 < sched[aid].size() else INF})
		blows_by_arm[aid] = list
		if not blows_by_mech.has(mid): blows_by_mech[mid] = []
		blows_by_mech[mid].append_array(list)
	for mid in blows_by_mech:
		blows_by_mech[mid].sort_custom(func(a, b): return float(a["t"]) < float(b["t"]))

## A blow's ring is gated exactly as `recoil` is: full until RECOIL_GATE before
## its arm's next strike begins, nothing after — so no ring smears a contact.
static func _blow_gate(b: Dictionary, t: float) -> float:
	return 1.0-smooth((t-(float(b["gate_end"])-RECOIL_GATE))/RECOIL_GATE)

## One bus's rings summed at t: a damped sinusoid a blow, weighted by the blow's
## energy and by `shape` (a mode shape — the rail's; 1.0 for a rigid body), and
## negative-going first because a blow pushes down. Zero at each blow itself
## (`_ring` starts at zero), so a shudder never displaces its own contact.
func _shudder(list: Array, t: float, p: Array, shape: Callable) -> float:
	var total := 0.0
	for i in range(list.size()-1, -1, -1):
		var b: Dictionary = list[i]
		var tau: float = t-float(b["t"])
		if tau < 0.0: continue
		if tau > SHUDDER_TAIL: break
		total += -_ring(p, tau)*float(b["energy"])*float(shape.call(b))*_blow_gate(b, t)
	return total*SHUDDER_GAIN

## The rail's two guide bars run RAIL_OVER past the reach window into their heads.
func rail_span(aid: String) -> Array:
	var rx: Array = geometry["arms"][aid]["reach_x"]
	return [float(rx[0])-RAIL_OVER, float(rx[1])+RAIL_OVER]

## The instrument's stand answers every blow on it with a short vertical thump —
## a felt head on a 5 kg bar over a wooden trestle. Summed over its arms.
func stand_thump(mid: String, t: float) -> float:
	if not blows_by_mech.has(mid): return 0.0
	return _shudder(blows_by_mech[mid], t, STAND_THUMP, func(_b): return 1.0)

## The rail's vertical deflection at rail position x: a steel bar pinned in its
## two heads, rung in its first bending mode — a half sine over the span, zero
## at the heads — by a blow whose own position along the rail sets how much of
## that mode it excites. So a blow at mid-span sags the rail by RAIL_SAG and a
## blow under a head barely moves it, which is what a beam does.
func rail_sag(aid: String, t: float, x: float) -> float:
	if not blows_by_arm.has(aid): return 0.0
	var span := rail_span(aid)
	var L: float = maxf(span[1]-span[0], .001)
	var here := sin(PI*clampf((x-span[0])/L, 0, 1))
	return _shudder(blows_by_arm[aid], t, RAIL_SAG, func(b):
		return here*sin(PI*clampf((float(b["x"])-span[0])/L, 0, 1)))

## The gantry sways about its plinths after a blow: a tilt across the rail (the
## axis the knee braces do not stiffen), applied to the whole gantry about the
## line through both plinth feet, so no mast gains a lever arm along the rail.
func mast_sway(aid: String, t: float) -> float:
	if not blows_by_arm.has(aid): return 0.0
	return _shudder(blows_by_arm[aid], t, MAST_SWAY, func(_b): return 1.0)

func tip_at(aid: String, t: float) -> Vector3:
	return path_at(aid, t)+recoil(aid, t)

## The scored path alone: rest, travel, strike, sweep, release, rest.
func path_at(aid: String, t: float) -> Vector3:
	var lift := hover(aid)
	var clicky := stepped(aid)
	var rest := contact(acts[aid]["home"]) + lift
	for s in sched[aid]:
		if t < s["go"]:
			return rest
		var first: Vector3 = s["first"]
		var hit: float = s["hit"]
		var approach: float = s["approach"]
		var e: Dictionary = s["event"]
		var ids: Array = e["strings"]
		if t < hit:
			if s["moving"] and t < approach:
				return travel(rest, first+lift, (t-s["go"])/(approach-s["go"]), approach-s["go"], clicky)
			var start: float = approach if s["moving"] else maxf(s["tm"], approach)
			var origin := first+lift if s["moving"] else rest
			var u := clampf((t-start)/maxf(hit-start,.000001),0,1)
			return strike(origin, first, lift, u, clicky)
		if t <= s["end"]:
			if ids.size()==1 or s["spread"]<=0:
				return first
			var index := minf((t-hit)/s["spread"],ids.size()-1)
			var k := mini(int(index),ids.size()-2)
			# Linear sweep crosses each string at the exact audible sub-onset.
			return contact(ids[k],e.get("pick")).lerp(contact(ids[k+1],e.get("pick")),index-k)
		if t < s["t_free"]:
			return s["last"] + lift*quintic((t-s["end"])/maxf(s["t_free"]-s["end"],.000001))
		rest = s["last"]+lift
	return rest

## When a stepped arm's ratchet clicks: one entry a click, at the moment the
## click's move lands on its detent and the pawl drops (go + (k+CLICK_MOVE)·T/n
## for the k-th of n clicks in a travel of T seconds — the same division
## `ratchet` makes), with the teeth that click spanned. The harness plays the
## click sample here (performance.gd); a servo arm never clicks.
func click_times(aid: String) -> Array:
	var out: Array = []
	if not stepped(aid): return out
	for s in sched[aid]:
		if not s["moving"]: continue
		var go: float = s["go"]
		var T: float = s["approach"]-go
		var dx: float = s["first"].x-s["rest"].x
		var n := clicks(dx, T)
		var spanned := teeth(dx)
		for k in n:
			out.append({"t": go+(k+CLICK_MOVE)*T/n, "teeth": float(spanned)/n, "aid": aid})
	return out

## Wrist pin relative to the tool's contact point; older manifests keep 0.15 m above.
func wrist_offset(cfg: Dictionary) -> Vector3:
	return v(cfg["wrist_offset"]) if cfg.has("wrist_offset") else Vector3(0,.15,0)

## Elbow side. "up" bulges the elbow up/forward (a mallet over a bar); "back"
## keeps it on the far side from the strings so a pick arm never pushes its
## elbow through the string plane. Mirrored in formlab/rig.py.
func bend_hint(cfg: Dictionary) -> Vector3:
	return Vector3.FORWARD if String(cfg.get("bend","up"))=="back" else Vector3.UP

func pose(aid: String, t: float) -> Dictionary:
	var cfg: Dictionary = geometry["arms"][aid]
	var tip := tip_at(aid,t)
	# The carriage rides the rail, so it follows the rail's sag at its own x: the
	# links and the pawl move with the bar. The tool's tip is the scored path and
	# its own recoil, untouched — every contact stays exact.
	var root := Vector3(tip.x,float(cfg["root_y"])+rail_sag(aid,t,tip.x),float(cfg["root_z"]))
	var wrist := tip+wrist_offset(cfg)
	var delta := wrist-root
	var distance := delta.length()
	var l1 := float(cfg["l1"])
	var l2 := float(cfg["l2"])
	var d := clampf(distance,absf(l1-l2)+.00001,l1+l2-.00001)
	var direction := delta.normalized()
	var along := (l1*l1-l2*l2+d*d)/(2*d)
	var hint := bend_hint(cfg)
	var bend := hint - direction*direction.dot(hint)
	if bend.length_squared()<.00001:
		bend=Vector3.FORWARD
	var elbow := root + direction*along + bend.normalized()*sqrt(maxf(0,l1*l1-along*along))
	# A hinged hammer's felt face is not the tool frame's origin: it hangs on the
	# hinge HEAD_L above it and swings. `tip` stays the tool frame (the shank,
	# the fork and the check ride it); `felt` is the contact.
	var theta := head_angle(aid,t)
	var felt := tip if theta==0.0 else tip+head_offset(theta,flip_sign(aid))
	return {"root":root,"elbow":elbow,"wrist":wrist,"tip":tip,"head":theta,"felt":felt,
		"reachable":distance<=l1+l2 and distance>=absf(l1-l2)}

## Link frame: y along the link, x the pin axis (world X projected), z = x × y.
## Meshes are built at true length in this frame (formlab.linkage), never scaled.
static func link_basis(a: Vector3, b: Vector3) -> Basis:
	var y := (b-a).normalized()
	var x := Vector3.RIGHT - y*y.dot(Vector3.RIGHT)
	if x.length_squared()<.000001: x=Vector3.FORWARD
	x=x.normalized()
	return Basis(x,y,x.cross(y))

## The roller detent pawl under a mallet arm's pinion (formlab.pawl, mirrored
## here for the poser): its angle for a carriage at rail position x is the
## largest at which the roller is still clear of the teeth — the spring lifts
## it until it touches. Constants mirror formlab.pawl.PAWL / TOOTH and
## formlab.clearance.PINION; tools/test_pawl.py holds the two together.
const PAWL_LEVER := .10
const PAWL_TILT := -.25                  # the pawl's frame leans this much at rest (formlab.pawl.PAWL['tilt'])
const PAWL_DROP := .023
const PAWL_FINGER := .03
const PAWL_NOSE_R := .018
const PINION_R_TIP := .13
const PINION_R_HUB := .1014
const PINION_R_PITCH := .12
# the involute tooth (formlab.gear): 16 teeth, 20° pressure angle, 3 mm backlash, 4 mm corners
const TOOTH_PRESSURE := 20.0*PI/180.0
const TOOTH_BACKLASH := .003
const TOOTH_BEVEL := .004
const TOOTH_ROOT := PINION_R_HUB-.003
const TOOTH_FLANK_SAMPLES := 6
static var _tooth: PackedFloat64Array = PackedFloat64Array()   # the tooth's polygon inset by its bevel, (u, v) pairs, counter-clockwise

static func _inv(a: float) -> float: return tan(a)-a

## formlab.gear.tooth_polygon inset by gear.BEVEL (formlab.gear.inset), built once.
static func _tooth_polygon() -> PackedFloat64Array:
	var r_base := PINION_R_PITCH*cos(TOOTH_PRESSURE)
	var pitch := TAU*PINION_R_PITCH/16.0
	var psi_pitch := (pitch/4.0-TOOTH_BACKLASH/2.0)/PINION_R_PITCH
	var right: Array = []
	for j in TOOTH_FLANK_SAMPLES:
		var rho: float = r_base+(PINION_R_TIP-r_base)*float(j)/float(TOOTH_FLANK_SAMPLES-1)
		var ps: float = psi_pitch+_inv(TOOTH_PRESSURE)-_inv(acos(clampf(r_base/rho, -1.0, 1.0)))
		right.append([rho*cos(ps), -rho*sin(ps)])
	var pb: float = -atan2(right[0][1], right[0][0])
	var poly: Array = [[TOOTH_ROOT*cos(pb), -TOOTH_ROOT*sin(pb)]]
	for q in right: poly.append(q)
	for j in range(right.size()-1, -1, -1): poly.append([right[j][0], -right[j][1]])
	poly.append([TOOTH_ROOT*cos(pb), TOOTH_ROOT*sin(pb)])
	# inset: each edge's line shifted inward by the bevel, consecutive lines intersected (Cramer)
	var n := poly.size(); var lines: Array = []
	for j in n:
		var a: Array = poly[j]; var c: Array = poly[(j+1)%n]
		var ex: float = c[0]-a[0]; var ey: float = c[1]-a[1]; var L := sqrt(ex*ex+ey*ey); ex /= L; ey /= L
		lines.append([a[0]-ey*TOOTH_BEVEL, a[1]+ex*TOOTH_BEVEL, ex, ey])
	var out := PackedFloat64Array()
	for j in n:
		var l1: Array = lines[(j-1+n)%n]; var l2: Array = lines[j]
		var det: float = l2[2]*l1[3]-l1[2]*l2[3]; var dx: float = l2[0]-l1[0]; var dy: float = l2[1]-l1[1]
		var s: float = (dy*l2[2]-dx*l2[3])/det
		out.append(l1[0]+s*l1[2]); out.append(l1[1]+s*l1[3])
	return out

## Signed distance from (u, v) to the inset tooth polygon: negative inside (formlab.gear.convex_distance).
static func _tooth_polygon_distance(u: float, v: float) -> float:
	if _tooth.is_empty(): _tooth = _tooth_polygon()
	var n := _tooth.size()/2; var inside := true; var dmin := INF
	for j in n:
		var ax := _tooth[2*j]; var ay := _tooth[2*j+1]; var bx := _tooth[(2*j+2)%(2*n)]; var by := _tooth[(2*j+3)%(2*n)]
		var ex := bx-ax; var ey := by-ay; var l2 := ex*ex+ey*ey
		var t := clampf(((u-ax)*ex+(v-ay)*ey)/l2, 0.0, 1.0)
		var px := u-(ax+t*ex); var py := v-(ay+t*ey); dmin = minf(dmin, sqrt(px*px+py*py))
		if ex*(v-ay)-ey*(u-ax) < 0.0: inside = false
	return -dmin if inside else dmin

## Signed distance in the disc's plane from (qx, qy) — relative to the disc's
## centre, carriage-local — to the toothed disc spun for a carriage at x: the
## hub and the three nearest teeth, each the inset polygon grown back by its bevel.
static func tooth_distance(qx: float, qy: float, x: float) -> float:
	var th := x/PINION_R_PITCH; var c := cos(th); var s := sin(th)
	var hx := qx*c+qy*s; var hy := -qx*s+qy*c
	var d := sqrt(hx*hx+hy*hy)-PINION_R_HUB
	var step := TAU/16.0; var i := roundf(atan2(hy, hx)/step)
	for k in [-1.0, 0.0, 1.0]:
		var phi: float = (i+k)*step; var cp := cos(phi); var sp := sin(phi)
		var u := hx*cp+hy*sp; var v := -hx*sp+hy*cp
		d = minf(d, _tooth_polygon_distance(u, v)-TOOTH_BEVEL)
	return d

## The roller's centre in the pawl's frame (origin at the pivot) at `alpha`,
## as [x, y] (an Array of 64-bit floats: a Vector2 would round to 32 bits and
## put the angle 1e-7 rad off the numpy mirror).
static func pawl_nose(alpha: float) -> Array:
	var c := cos(alpha); var s := sin(alpha); var nx := -PAWL_LEVER; var ny := PAWL_FINGER
	return [nx*c+ny*s, -nx*s+ny*c]

## The pawl's whole turn about +Z (its rest lean included) for a carriage at
## x: the largest at which the roller is still clear of the teeth. Mirrors
## formlab.pawl.angle / _pivot_from_centre.
static func pawl_angle(x: float) -> float:
	var px := PAWL_LEVER*cos(PAWL_TILT)-PAWL_FINGER*sin(PAWL_TILT)
	var py := -(PINION_R_TIP+PAWL_DROP)-PAWL_LEVER*sin(PAWL_TILT)-PAWL_FINGER*cos(PAWL_TILT)
	var lo := -.15+PAWL_TILT; var hi := .45+PAWL_TILT
	for _i in 48:
		var mid := (lo+hi)/2.0; var n := pawl_nose(mid)
		if tooth_distance(px+n[0], py+n[1], x) >= PAWL_NOSE_R: lo = mid
		else: hi = mid
	return lo
