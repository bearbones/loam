class_name MotionRig
extends RefCounted
## Every moving part of the model, posed from the bake's joints table
## (MotionBake.frames_at; formlab/bake.py's docstring is the spec). The header's
## body rows bind GLB nodes to joints; apply(t) writes each bound node from its
## joint's frame by the row's mode:
##   frame  node.transform = Transform3D(B, P)                  (a link)
##   rest   node.position = P, and node.basis = B*home.basis    (a part on its pin;
##          unless the joint's frame is the world's identity: then the basis
##          is never written, as a crosshead's never is)
##   spin   node.basis = B*home.basis                           (a wheel on its axle)
##   world  a root joint moving a mesh built in world space: a revolute turns
##          it about the joint's axis line, Transform3D(B, P - B*P)*home; a
##          prismatic slides it, Transform3D(home.basis, home.origin + S)
## home is the node's transform at bind(): the imported, unposed part. No node
## is bound twice, and every node is written by exactly one row, so the order
## of the rows does not matter. A new joint with a body is data: bind() and
## apply() need no change.

enum {FRAME, REST, WORLD, SPIN}
const MODES := ["frame", "rest", "world", "spin"]

var errors: PackedStringArray = []
var bake: MotionBake
var _bound: Array = []          # [joint index, node, mode, home] in the table's body order
var _home: Dictionary = {}      # node -> its transform at bind()
var _by_joint: Dictionary = {}  # joint id -> [{node, home}]


## Resolves every body row against the model: an exact node name with
## find_child, a pattern (containing "*") with find_children over Node3D. A
## missing required node fails, naming it and its joint; an optional one
## that is absent is skipped (a mesh the build did not pack).
func bind(motion: MotionBake, model: Node) -> bool:
	bake = motion; _bound = []; _home = {}; _by_joint = {}; errors = []
	for b in motion.bodies():
		var jid := str(b["joint"])
		var i := motion.joint_index(jid)
		var mode := MODES.find(b["mode"])
		if i < 0 or mode < 0:
			errors.append("body %s: joint %s / mode %s is not in the table" % [str(b["node"]), jid, str(b["mode"])]); return false
		var pat := str(b["node"])
		var found: Array = []
		if pat.contains("*"):
			found = model.find_children(pat, "Node3D", true, false)
		else:
			var node := model.find_child(pat, true, false)
			if node != null: found = [node]
		if found.is_empty() and not bool(b.get("optional", false)):
			errors.append("Missing GLB node %s for joint %s" % [pat, jid]); return false
		for node in found:
			var n3 := node as Node3D
			if n3 == null:
				errors.append("GLB node %s for joint %s is not a Node3D" % [node.name, jid]); return false
			if _home.has(n3):
				errors.append("GLB node %s is bound twice (joint %s)" % [n3.name, jid]); return false
			_home[n3] = n3.transform
			_bound.append([i, n3, mode, n3.transform])
			if not _by_joint.has(jid): _by_joint[jid] = []
			_by_joint[jid].append({"node": n3, "home": n3.transform})
	return true


## Poses every bound node at t (pose mode).
func apply(t: float) -> void:
	bake.frames_at(t)
	for b in _bound:
		var i: int = b[0]; var node: Node3D = b[1]; var home: Transform3D = b[3]
		match b[2]:
			FRAME:
				node.transform = Transform3D(bake.frame_b(i), bake.frame_p(i))
			REST:
				node.position = bake.frame_p(i)
				if not bake.frame_ident(i): node.basis = bake.frame_b(i)*home.basis
			SPIN:
				node.basis = bake.frame_b(i)*home.basis
			WORLD:
				if bake.joint_type(i) == MotionBake.PRISMATIC:
					node.transform = Transform3D(home.basis, home.origin+bake.frame_slide(i))
				else:
					var basis := bake.frame_b(i); var p := bake.frame_p(i)
					node.transform = Transform3D(basis, p-basis*p)*home


## Every bound node, in body-row order.
func bound_nodes() -> Array:
	var out: Array = []
	for b in _bound: out.append(b[1])
	return out


## The nodes a joint moves: [{node, home}] (empty for a joint with no body).
func nodes(joint_id: String) -> Array: return _by_joint.get(joint_id, [])


## A bound node's transform at bind().
func home(node: Node3D) -> Transform3D: return _home[node]
