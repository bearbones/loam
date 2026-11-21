extends SceneTree
## Integration check: the GLB nodes and actual animated tool origins agree with the score.
func _init() -> void:
	call_deferred("check_scene")

## Where the rendered hammer head's felt face is: the mesh is built at flip zero
## with the face straight down from the hinge, so the posed basis carries it.
func felt_face(head: Node3D, head_l: float) -> Vector3:
	return head.global_position+head.global_basis*Vector3(0,-head_l,0)

# Scrubbing out of a contact window must clear both uploaded buffers. Returning
# to the same frame must reproduce its samples independently of the last seek.
func check_wire_seek(scene, failures: Array) -> void:
	for event in scene.score.events:
		if event["mech"] != "harp" or event.get("shape") == null: continue
		var wire: Node3D = scene.strings[event["strings"][0]]
		var mat: ShaderMaterial = wire.get_child(0).material_override
		var t := float(event["t"]) - .022
		scene.evaluate(t)
		var pull: PackedFloat32Array = mat.get_shader_parameter("disp")
		var rest := PackedFloat32Array()
		rest.resize(scene.STRING_NODES)
		if pull.size() != rest.size() or pull == rest:
			failures.append("harp pre-pull missing before first contact")
		t = float(event["t"]) + .075
		scene.evaluate(t)
		var expected: PackedFloat32Array = mat.get_shader_parameter("disp")
		var envelope: PackedFloat32Array = mat.get_shader_parameter("envelope")
		scene.evaluate(-1.0)
		var quiet: PackedFloat32Array = mat.get_shader_parameter("envelope")
		if quiet != rest or wire.get_child(1).visible:
			failures.append("a string kept ringing after a backwards seek into pre-roll")
		scene.evaluate(t)
		if not wire.get_child(1).visible or mat.get_shader_parameter("disp") != expected or mat.get_shader_parameter("envelope") != envelope:
			failures.append("returning to a string contact changed the motion or blur")
		return

# Sweep the visible link ends. At the parked pose the wrist and palm socket
# used to coincide, allowing the folded knee to invert between two frames.
func check_wrist_travel(scene, failures: Array) -> void:
	var last := {}
	var step := 0.
	var error := 0.
	var nearest := INF
	var links: Array[Node3D] = []
	var lengths := PackedFloat32Array()
	for aid in scene.hand_motion:
		if scene.layout["arms"][aid]["mid"]!="harp": continue
		for part in ["wrist_crank","wrist_rod"]:
			links.append(scene.drive_parts[aid][part])
			lengths.append(scene.layout["arms"][aid]["drives"]["wrist_flex"]["carrier_l"])
	for frame in range(-60,ceili(scene.score.total_s*60.)):
		scene.evaluate(frame/60.)
		for aid in scene.hand_motion:
			var rod: Node3D = scene.drive_parts[aid]["wrist_rod"]
			var crank: Node3D = scene.drive_parts[aid]["wrist_crank"]
			var cfg: Dictionary = scene.layout["arms"][aid]["drives"]["wrist_flex"]
			var l := float(cfg["carrier_l"])
			var socket: Vector3 = scene.parts[aid]["tool"].global_position+MotionBake.v(cfg["mount_offset"])
			error = maxf(error,rod.to_global(Vector3.UP*l).distance_to(socket))
			error = maxf(error,crank.to_global(Vector3.UP*l).distance_to(rod.global_position))
			var pin: Node3D = scene.parts[aid]["wristhead"].get_node(aid+"__carrier_seat")
			error = maxf(error,pin.global_position.distance_to(crank.global_position))
			if last.has(aid): step = maxf(step,rod.global_position.distance_to(last[aid]))
			last[aid] = rod.global_position
		for i in links.size():
			var p := links[i].global_position
			var q := p+links[i].global_basis.y*lengths[i]
			for j in range((i/2+1)*2,links.size()):
				var a := links[j].global_position
				var b := a+links[j].global_basis.y*lengths[j]
				var pair := Geometry3D.get_closest_points_between_segments(p,q,a,b)
				nearest = minf(nearest,pair[0].distance_to(pair[1]))
	if nearest<.040: failures.append("harp wrist links cross: %.2f mm between centre lines" % (nearest*1000.))
	# Limit the inter-frame chord as well as the pin error. A full inversion
	# can cover a link diameter while still satisfying both closure equations.
	if step>.27 or error>.0001:
		failures.append("wrist carriage sweep: peak frame travel %.4f m, pin error %.6f m" % [step,error])
	print("  wrist carriers: peak %.3f m/frame at 60 Hz, worst pin error %.4f mm" % [step,error*1000.])

func check_plucks(scene, failures: Array) -> void:
	if not scene.pillar_players.is_empty():
		check_pillar_players(scene,failures)
		return
	var count := 0
	var largest_wrist := 0.
	var least_draw := INF
	var least_curl := INF
	var least_free := INF
	for e in scene.score.events:
		if e["mech"]!="harp": continue
		var aid: String=e["actuator"]
		var sid: String=e["strings"][0]
		var d: String=["thumb","d2","d3","d4"][int(e["finger"])]
		var finger: Node3D=scene.drive_parts[aid]["digit_"+d]
		var pad: Node3D=finger.find_child(aid+"__pad_"+d,true,false)
		var joint: Node3D=pad.get_parent()
		var palm: Node3D=scene.parts[aid]["tool"]
		if finger.get_parent()!=palm or joint.get_parent().get_parent()!=finger:
			failures.append("disconnected phalanx "+aid+"/"+d); return
		var t:=float(e["t"])
		scene.evaluate(t-.064)
		var planted:=palm.global_position
		var caught:=pad.global_position
		var open:=joint.basis.get_rotation_quaternion()
		scene.evaluate(t)
		largest_wrist=maxf(largest_wrist,planted.distance_to(palm.global_position))
		least_draw=minf(least_draw,caught.distance_to(pad.global_position))
		least_curl=minf(least_curl,open.angle_to(joint.basis.get_rotation_quaternion()))
		scene.evaluate(t+.058)
		var line:=MotionBake.contact(scene.layout,sid,e["pick"])
		line+=scene.wire_motion[sid].excursion_at(float(e["pick"]))
		least_free=minf(least_free,pad.global_position.distance_to(line))
		count+=1
	print("  %d harp plucks: least draw %.2f mm, distal turn %.1f deg, separation after slip %.2f mm, peak wrist travel %.3f mm" % [count,1000*least_draw,rad_to_deg(least_curl),least_free*1000,largest_wrist*1000])
	if least_draw<.009 or least_curl<.20 or largest_wrist>.001 or least_free<.003:
		failures.append("harp failed to load and release with a planted hand")

func check_pillar_players(scene, failures: Array) -> void:
	var count := 0
	var pin_error := 0.
	var pad_error := 0.
	var wrist_travel := 0.
	var least_draw := INF
	var least_curl := INF
	var least_free := INF
	var knuckle := INF
	var idle_gap := INF
	var strings: Array = []
	for sid in scene.strings:
		var spec: Dictionary = scene.layout["strings"][sid]
		if spec["mid"]!="harp": continue
		strings.append([MotionBake.v(spec["a"]),MotionBake.v(spec["b"]),scene.wire_motion[sid],.0035*pow(2.,(64.-float(spec["midi"]))/18.)])
	var target_strings := {}
	for row in strings: target_strings[row[2]]=[row]
	var minimum_gap := INF
	var closure := INF
	var pre_shape := 0.
	var approach_curl := INF
	var spread_angle := INF
	var joint_opening := 0.
	var seek_error := 0.
	var rebound_gap := INF
	var mesh_hits := 0
	var near_side := INF
	var arrays: Array = scene.pillar_players.values()
	var probes := {}
	var mutual := INF
	for arm in arrays:
		probes[arm] = finger_meshes(arm)
		for n in arm.notes:
			var d = arm.digits[n.digit]
			scene.evaluate(n.time-.064)
			var plant: Vector3=arm.palm.global_position
			var start: Vector3=d.pad.global_position
			var placed: Quaternion=d.distal.basis.get_rotation_quaternion()
			for sample in 9:
				scene.evaluate(n.time-.064+.008*sample)
				var wire: Vector3=n.base+n.wire.excursion_at(n.pick)
				var radius: float = n.gauge+arm.pad_radius
				pad_error=maxf(pad_error,absf(d.pad.global_position.distance_to(wire)-radius))
				wrist_travel=maxf(wrist_travel,plant.distance_to(arm.palm.global_position))
				for hinge in [d.root,d.middle,d.distal]:
					if hinge.global_basis.y.dot(Vector3.UP)<.99999:
						failures.append("finger pin tilted across speaking wire"); return
				var k: Vector3=d.root.global_position-wire
				knuckle=minf(knuckle,Vector2(k.x,k.z).length()-.013-n.gauge)
				for inactive in arm.digits:
					if inactive==d: continue
					var relative: Vector3=inactive.pad.global_position-wire
					idle_gap=minf(idle_gap,Vector2(relative.x,relative.z).length()-arm.pad_radius-n.gauge)
			least_draw=minf(least_draw,start.distance_to(d.pad.global_position))
			least_curl=minf(least_curl,placed.angle_to(d.distal.basis.get_rotation_quaternion()))
			scene.evaluate(n.time+.058)
			var delta: Vector3=d.pad.global_position-(n.base+n.wire.excursion_at(n.pick))
			least_free=minf(least_free,Vector2(delta.x,delta.z).length()-arm.pad_radius-n.gauge)
			n.wire.apply(n.time)
			arm.apply(n.time)
			var hold_distance: float = arm.palm.position.distance_to(d.pad.global_position)
			arm.apply(n.closed_at)
			closure=minf(closure,hold_distance-arm.palm.position.distance_to(d.pad.global_position))
			n.wire.apply(n.align_at)
			arm.apply(n.align_at)
			var open_angle: float = absf(d.last_flex.z)
			var thumb: Node3D = arm.digits[0].root
			var index: Node3D = arm.digits[1].root
			spread_angle = minf(spread_angle,thumb.global_basis.z.angle_to(index.global_basis.z))
			var late: float = lerpf(n.align_at,n.touch_at,.80)
			n.wire.apply(late)
			arm.apply(late)
			approach_curl=minf(approach_curl,absf(d.last_flex.z)-open_angle)
			pre_shape=maxf(pre_shape,absf(d.last_flex.z-d.placed.z))
			var seek_pose: Transform3D = d.pad.global_transform
			n.wire.apply(n.time+.4)
			arm.apply(n.time+.4)
			n.wire.apply(late)
			arm.apply(late)
			seek_error=maxf(seek_error,d.pad.global_position.distance_to(seek_pose.origin))
			# At the end of a slip the wire can rebound through its whole
			# excursion within a video frame. Check the whole line of rebound,
			# including its first instant, independently of oscillation phase.
			for sample in 65:
				var t: float = lerpf(n.time,n.clear_at,sample/64.)
				n.wire.apply(t)
				arm.apply(t)
				mesh_hits+=finger_wire_hits(probes[arm],target_strings[n.wire])
				var outside: Vector3 = n.push.cross(Vector3.UP)
				if outside.dot(arm.frame.z)>0.: outside=-outside
				rebound_gap=minf(rebound_gap,outside.dot(d.pad.global_position-n.base)-n.gauge-arm.pad_radius)
			# Measure actual hinge rotations, signed into flexion for each digit.
			# Independent joint clocks can open the middle link during a pluck.
			var earlier: Vector3 = d.placed*d.sign_x
			var extension := Vector3.ZERO
			for step in 65:
				var t: float = n.time-.064+step*.001
				n.wire.apply(t)
				arm.apply(t)
				var signed_flex: Vector3 = d.last_flex*d.sign_x
				extension+=(earlier-signed_flex).max(Vector3.ZERO)
				earlier=signed_flex
			joint_opening=maxf(joint_opening,maxf(extension.x,maxf(extension.y,extension.z)))
			for sample in 121:
				var t: float = lerpf(n.align_at,n.time,sample/120.)
				n.wire.apply(t)
				arm.apply(t)
				mesh_hits+=finger_wire_hits(probes[arm],target_strings[n.wire])
				var diff: Vector3 = d.pad.global_position-(n.base+n.wire.excursion_at(n.pick))
				near_side=minf(near_side,-diff.dot(arm.frame.z))
				minimum_gap=minf(minimum_gap,Vector2(diff.x,diff.z).length()-n.gauge-arm.pad_radius)
			count+=1
	for i in range(-60,ceili(scene.score.total_s*60.)):
		scene.evaluate(i/60.)
		for j in arrays.size():
			var arm = arrays[j]
			minimum_gap=minf(minimum_gap,rank_clearance(arm,strings))
			mesh_hits+=finger_wire_hits(probes[arm],strings)
			var root_point: Vector3=arm.upper.global_position
			var elbow: Vector3=arm.lower.global_position
			var wrist: Vector3=arm.palm.to_global(Vector3(0,0,-.063))
			pin_error=maxf(pin_error,root_point.distance_to(arm.shoulder))
			pin_error=maxf(pin_error,elbow.distance_to(arm.upper.to_global(Vector3.UP*arm.l1)))
			pin_error=maxf(pin_error,wrist.distance_to(arm.lower.to_global(Vector3.UP*arm.l2)))
			for other in arrays.slice(j+1):
				for seg in [[root_point,elbow],[elbow,wrist]]:
					for pair in [[other.shoulder,other.lower.global_position],[other.lower.global_position,other.palm.to_global(Vector3(0,0,-.063))]]:
						var points:=Geometry3D.get_closest_points_between_segments(seg[0],seg[1],pair[0],pair[1])
						mutual=minf(mutual,points[0].distance_to(points[1]))
	print("  %d pillar plucks, mm: pad error %.3f, planted wrist travel %.3f, draw %.2f, post-release gap %.2f, knuckle gap %.2f, folded pad gap %.2f, arm closure error %.3f, link separation %.1f, fingertip curl %.1f deg" % [count,pad_error*1000.,wrist_travel*1000.,least_draw*1000.,least_free*1000.,knuckle*1000.,idle_gap*1000.,pin_error*1000.,mutual*1000.,rad_to_deg(least_curl)])
	print("  full rank pad clearance %.4f mm, near side %.3f mm, rebound line clearance %.4f mm, mesh intersections %d" % [minimum_gap*1000.,near_side*1000.,rebound_gap*1000.,mesh_hits])
	print("  minimum fingertip closure toward palm %.2f mm, pre-contact distal angle error %.4f degrees, opening under load %.3f degrees, seek error %.4f mm" % [closure*1000.,rad_to_deg(pre_shape),rad_to_deg(joint_opening),seek_error*1000.])
	if spread_angle<.65 or approach_curl<.20 or pre_shape>.015 or joint_opening>deg_to_rad(1.) or closure<.035:
		failures.append("harp hand failed to splay, pre-shape or close into the palm")
	if minimum_gap<-.00010 or rebound_gap<-.0001 or near_side<.002 or mesh_hits>0:
		failures.append("harp hand entered the wire during the stroke or transfer")
	if count==0 or pad_error>.00015 or wrist_travel>.0001 or least_draw<.009 or least_free<.003 or knuckle<.05 or idle_gap<.012 or least_curl<.30:
		failures.append("harp pad failed seated loading, clearance or release")
	if pin_error>.0001 or mutual<.11 or seek_error>.00001:
		failures.append("pillar arm reach or seek stability failed")

# The playing finger and wire are included in every sweep, during approach,
# draw and recovery. Tangency has zero surface clearance.
func rank_clearance(arm, strings: Array) -> float:
	var gap := INF
	for d in arm.digits:
		var tip: Vector3 = d.pad.global_position
		for s in strings:
			var a: Vector3=s[0]
			var b: Vector3=s[1]
			if absf(tip.x-a.x)>.13: continue
			var u:=clampf((tip.y-a.y)/(b.y-a.y),0.,1.)
			var point: Vector3=a.lerp(b,u)+s[2].excursion_at(u)
			gap=minf(gap,tip.distance_to(point)-float(s[3])-float(arm.pad_radius))
	return gap

func finger_meshes(arm) -> Array:
	var probes := []
	for d in arm.digits:
		for part: MeshInstance3D in [d.root,d.middle,d.distal]:
			probes.append([part,part.mesh.generate_triangle_mesh(),part.get_aabb()])
	return probes

# Intersect the actual imported finger links with longitudinal edges of the
# shader's 16-sided tube. Split rays at the 48 rendered mesh rings. A 0.05 mm
# inset distinguishes a grazing surface contact from entry into the material.
func finger_wire_hits(probes: Array, strings: Array) -> int:
	var hits := 0
	for probe in probes:
		var part: Node3D = probe[0]
		var world_box: AABB = part.global_transform*probe[2]
		if absf(world_box.get_center().z)>world_box.size.z*.5+.045: continue
		var inv := part.global_transform.affine_inverse()
		for s in strings:
			var a: Vector3=s[0]
			var b: Vector3=s[1]
			if absf(world_box.get_center().x-a.x)>world_box.size.x*.5+.045: continue
			var u := maxf(0.,(world_box.position.y-.001-a.y)/(b.y-a.y))
			var end := minf(1.,(world_box.end.y+.001-a.y)/(b.y-a.y))
			while u<end:
				var stop := minf(end,(floori(u*48.+.000001)+1)/48.)
				var p: Vector3=a.lerp(b,u)+s[2].excursion_at(u)
				var q: Vector3=a.lerp(b,stop)+s[2].excursion_at(stop)
				for edge in 16:
					var angle := TAU*edge/16.
					var offset := Vector3(cos(angle),0,sin(angle))*(float(s[3])-.00005)
					if not probe[1].intersect_segment(inv*(p+offset),inv*(q+offset)).is_empty():
						hits+=1
						break
				u=stop
	return hits

func check_mallets(scene, failures: Array) -> void:
	var clearance:=INF
	var closure:=0.
	var overlap:=INF
	# The felt fits inside a 62 mm sphere. Each oriented mesh box encloses
	# the complete forging, including the bosses beyond the nominal pins.
	for frame in range(-120,ceili(scene.score.total_s*120.)+1):
		scene.evaluate(frame/120.)
		for aid in scene.mallet_grips:
			var p: Dictionary=scene.drive_parts[aid]
			var arm: Dictionary=scene.parts[aid]
			var h: Dictionary=scene.layout["arms"][aid]["drives"]["hinge"]
			var lug: Vector3=p.wrist_shaft.to_global(Vector3(h.x_rod,0,scene.motion.flip_sign(aid)*h.r_lug))
			closure=maxf(closure,p.wrist_rod.to_global(Vector3(h.x_rod,h.coupler_l,0)).distance_to(lug))
			var span: float=p.wrist_guide.global_position.distance_to(p.wrist_plunger.global_position)
			overlap=minf(overlap,.405+.414-span)
			for head in [arm.tool,p.mallet2_head]:
				var centre: Vector3=head.to_global(head.mesh.get_aabb().get_center())
				for node in [arm.lower,arm.lower2,arm.wrist,arm.wristhead,p.wrist_crank,p.wrist_rod,p.wrist_guide,p.wrist_plunger]:
					var bb: AABB=node.mesh.get_aabb()
					var c: Vector3=node.to_local(centre)
					clearance=minf(clearance,c.distance_to(c.clamp(bb.position,bb.end))-.062)
	print("  120 Hz mallet sweep: minimum felt clearance %.2f mm, worst coupler pin error %.3f mm, minimum guide overlap %.1f mm" % [clearance*1000,closure*1000,overlap*1000])
	if clearance<.002 or closure>.00015 or overlap<.02: failures.append("mallet clearance or drive closure failed")

func check_struck_surfaces(scene, failures: Array) -> void:
	var seen := {}
	for e in scene.score.events:
		var sid: String = e["strings"][0]
		if seen.has(sid) or not scene.layout["strings"][sid]["struck"]: continue
		seen[sid] = true
		var spec: Dictionary = scene.layout["strings"][sid]
		var body := scene.model.find_child(sid+(" bell" if spec["mid"]=="bells" else " bar"),true,false) as MeshInstance3D
		if body==null or body.get_blend_shape_count()!=1:
			failures.append("missing acoustic mode on "+sid)
			continue
		var freq := 440.*pow(2.,(float(spec["midi"])-69.)/12.)
		var t := float(e["t"])+.25/freq
		scene.evaluate(t)
		var struck := body.get_blend_shape_value(0)
		scene.evaluate(-2.)
		if absf(struck)<.00005 or body.get_blend_shape_value(0)!=0.:
			failures.append("voiced surface failed impulse or reset on "+sid)

func check_scene() -> void:
	var scene=load("res://performance.tscn").instantiate()
	if scene.get_script()==null: push_error("performance.gd failed to compile"); quit(1); return
	root.add_child(scene)
	scene.playing=false
	var failures: Array=[]
	var contacts := 0
	for aid in scene.parts:
		for part in scene.parts[aid]:
			if scene.parts[aid][part]==null: failures.append("missing GLB pivot "+aid+"/"+part)
	if failures.is_empty():
		for e in scene.score.events:
			var ts: Array=ScoreDoc.string_times(e)   # a rake roll's at its own onsets
			for k in range(e["strings"].size()):
				var t: float=ts[k]
				scene.evaluate(t)
				var aid: String = e["actuator"]
				var sid: String = e["strings"][k]
				if scene.pillar_players.has(aid):
					contacts+=1   # every pad checked throughout its draw below
					continue
				var tool: Node3D = scene.parts[aid]["tool"]
				var target := MotionBake.contact(scene.layout,sid,e.get("pick"))
				var point := tool.global_position
				if scene.hand_motion.has(aid):
					var digit: String = ["thumb","d2","d3","d4"][int(e.get("finger",1))]
					if e["mech"]=="rake":
						var up: bool = e.get("dir","up" if e["midis"][-1]>=e["midis"][0] else "down")!="down"
						digit = "d2" if up else "thumb"
					var pad: Node3D = scene.drive_parts[aid]["digit_"+digit].find_child(aid+"__pad_"+digit,true,false)
					point = pad.global_position
					target += scene.wire_motion[sid].excursion_at(float(e["pick"]))
					var carrier: Node3D = scene.drive_parts[aid]["wrist_rod"]
					var drive: Dictionary = scene.layout["arms"][aid]["drives"]["wrist_flex"]
					var socket := tool.global_position+MotionBake.v(drive["mount_offset"])
					if carrier.to_global(Vector3.UP*float(drive["carrier_l"])).distance_to(socket)>.0001:
						failures.append("%s wrist carrier misses its palm socket at %.3f" % [aid,t])
					if e["mech"]=="harp":
						scene.evaluate(t-.032)
						var draw := MotionBake.contact(scene.layout,sid,e["pick"])
						draw += scene.wire_motion[sid].excursion_at(float(e["pick"]))
						if pad.global_position.distance_to(draw)>.0001:
							failures.append("%s fingertip lost the string during the pull at %.3f" % [aid,t])
				elif scene.mallet_grips.has(aid):
					var other: Node3D = scene.drive_parts[aid]["mallet2_head"]
					var second := int(e.get("finger",0))==1
					point = other.global_position if second else tool.global_position
					var idle := tool if second else other
					if idle.global_position.y<target.y+.055:
						failures.append("%s idle mallet landed at %.3f" % [aid,t])
				elif scene.motion.hammer(aid):
					var head: Node3D=scene.parts[aid].get("head")
					if head==null: failures.append("hammer arm has no rendered head "+aid)
					else: point = felt_face(head,scene.motion.head_length(aid))
				if point.distance_to(target)>.0001:
					failures.append("%s playing surface misses %s by %.2f mm at %.3f" % [aid,sid,point.distance_to(target)*1000.,t])
				contacts+=1
		for aid in scene.parts:
			var upper: MeshInstance3D=scene.parts[aid]["upper"]
			var cfg: Dictionary=scene.layout["arms"][aid]
			# Links are built at true length in their own frame and never scaled:
			# the imported mesh's y extent must match what formlab recorded, and the
			# posed basis must stay orthonormal.
			var expected: float=float(cfg.get("link_extent_y",cfg["l1"]))
			if absf(upper.mesh.get_aabb().size.y-expected)>.001: failures.append("imported link mesh extent wrong "+aid)
			if absf(upper.global_basis.y.length()-1.0)>.0001 or absf(upper.global_basis.x.dot(upper.global_basis.y))>.0001: failures.append("posed link basis not orthonormal "+aid)
			# Away from the blow the rendered head must track the flip the rig computes,
			# all the way back onto its check at rest.
			if scene.motion.hammer(aid):
				var head2: Node3D=scene.parts[aid].get("head")
				var hit0: float=float(scene.motion.blows(aid)[0]["t"])
				for t in [12.0,48.0,hit0-.03,hit0+.02]:
					scene.evaluate(float(t))
					var want: Vector3=scene.motion.pose(aid,float(t))["felt"]
					if head2==null: break
					if head2.global_position.distance_to(scene.motion.tip_at(aid,float(t))+Vector3(0,scene.motion.head_length(aid),0))>.00001: failures.append("hammer hinge off the shank's end "+aid)
					if felt_face(head2,scene.motion.head_length(aid)).distance_to(want)>.00001: failures.append("rendered felt face off its flip %s at %.2f s" % [aid,t])
			var pose: Dictionary=scene.motion.pose(aid,48.0); scene.evaluate(48.0)
			var elbow_node: Node3D=scene.parts[aid]["elbow"]
			if elbow_node.global_position.distance_to(pose["elbow"])>.00001: failures.append("elbow pin off its pose "+aid)
			var upper2: Node3D=scene.parts[aid]["upper2"]
			if upper2.global_position.distance_to(pose["root"]+MotionBake.v(cfg["o1"]))>.00001: failures.append("parallel bar off its pin "+aid)
			# The pinion sits on its recorded mount (formlab.clearance.MOUNTS) and lies in
			# the plane that mount implies: upright (thin along z) in front of or behind
			# the carriage, flat (thin along y) above or below it.
			# A servo arm has no pinion: its leadscrew shaft (form_<aid>_screw) turns
			# -2π·x/pitch about its own axis line, which stays put (formlab.gantry.
			# screw_geometry, performance.gd); a stepped arm still has its gear.
			var servo: bool=str(cfg.get("drive","rack"))=="screw"
			var gear_node: Node3D=scene.model.find_child(aid+"__gear",true,false)
			if servo:
				var screw: Node3D=scene.model.find_child("form_"+aid+"_screw",true,false)
				if gear_node!=null: failures.append("servo arm carries a pinion "+aid)
				if screw==null or not cfg.has("screw"): failures.append("servo arm has no leadscrew "+aid)
				else:
					var sc: Dictionary=cfg["screw"]; var c := Vector3(0,float(sc["y"]),float(sc["z"]))
					var lead: float=float(sc.get("lead",sc["pitch"]))
					var want: float=wrapf(-TAU*pose["root"].x/lead,-PI,PI)
					if (screw.transform*c).distance_to(c)>.00001: failures.append("leadscrew turns off its axis "+aid)
					if absf(angle_difference(screw.basis.get_euler().x,want))>.0001 or screw.basis.x.distance_to(Vector3.RIGHT)>.0001: failures.append("leadscrew not turned x/lead "+aid)
			var gear: MeshInstance3D=gear_node as MeshInstance3D
			var mount: String=str(cfg.get("pinion","back"))
			var offsets := {"front": Vector3(0,0,.195), "back": Vector3(0,0,-.195), "up": Vector3(0,.17,-.10), "down": Vector3(0,-.17,-.10)}
			if servo: pass
			elif not offsets.has(mount): failures.append("unknown pinion mount "+mount+" "+aid)
			elif gear==null: failures.append("stepped arm has no pinion "+aid)
			elif gear.global_position.distance_to(pose["root"]+offsets[mount])>.00001: failures.append("pinion off its mount "+aid)
			else:
				var box: AABB=gear.global_transform*gear.mesh.get_aabb()
				var thin: float=box.size.y if (mount=="up" or mount=="down") else box.size.z
				var wide: float=box.size.x
				# the disc (70 mm) plus the hub boss cast on its outer face (30 mm, formlab.clearance.PINION)
				if thin>.11 or wide<.25: failures.append("pinion not lying in its mount's plane %s (%.3f thin, %.3f wide)" % [aid,thin,wide])
			# A mallet arm's roller detent pawl (formlab.pawl) hangs on its pivot off the
			# carriage and its roller rides the pinion's teeth: at every sampled moment
			# the roller's centre is exactly its radius from the toothed disc as spun.
			if cfg.has("pawl"):
				var pawl: MeshInstance3D=scene.parts[aid].get("pawl")
				if pawl==null: failures.append("pawl missing "+aid)
				else:
					# The pinion is spun with the pawl's phase (formlab.pawl.dip_offset) so the
					# roller seats in a dip at the arm's home; the roller is its own part on
					# the pawl's axle and rolls on the tips by ROLLER_SPIN a metre of rail.
					var phase: float=float(cfg["pawl"].get("phase",0.0))
					var roller: MeshInstance3D=scene.parts[aid].get("roller")
					if roller==null: failures.append("pawl roller missing "+aid)
					var turned: Array=[]
					var moments: Array=[12.0,48.0,48.02,48.05,48.1,100.0]
					for b in scene.motion.blows(aid).slice(0,8): moments.append(float(b["t"]))   # the arm surely moves between some of its contacts
					# ...and where the pawl rides the tips hardest: a freewheel above
					# PAWL_RIDE teeth a second (the bake's .ride channel, M1)
					var ride_t := -1.0; var ride_max := 0.0
					for k in range(0,int(scene.score.total_s*100.0)):
						var r: float=scene.motion.ride(aid,k/100.0)
						if r>ride_max: ride_max=r; ride_t=k/100.0
					if ride_t>=0.0: moments.append_array([ride_t,ride_t+.004])
					var freewheels := 0
					for c in scene.motion.click_times(aid):
						if int(c["step"])==0 and int(c["pawl"])==1: freewheels+=1
					if freewheels>0 and ride_max<.5: failures.append("a pawl that rides %d clicks never rides in the bake %s (ride at most %.3f)" % [freewheels,aid,ride_max])
					for t in moments:
						scene.evaluate(t); var pz: Dictionary=scene.motion.pose(aid,t)
						if pawl.global_position.distance_to(pz["root"]+MotionBake.v(cfg["pawl"]["pivot"]))>.00001: failures.append("pawl off its pivot "+aid)
						var swing: Basis=pawl.global_basis*scene.pawl_home[aid].inverse()
						var nose: Vector3=pawl.global_position+swing*MotionBake.v(cfg["pawl"]["nose"])
						# the pawl swings in the disc's plane by the bake's angle at the
						# carriage's x plus the phase, leaned toward the tip-land angle by
						# the arm's ride (MotionBake.pawl, formlab.bake.Bake.pawl); that the
						# angle clears the teeth is formlab.pawl's to hold (tools/test_pawl.py,
						# tools/test_bake.py)
						var q: Vector3=nose-gear.global_position
						var got_swing: float=-atan2(swing.x.y,swing.x.x)
						var want_swing: float=scene.motion.pawl_angle(pz["root"].x+phase,scene.motion.ride(aid,t))
						if absf(wrapf(got_swing-want_swing,-PI,PI))>.00002 or absf(q.z)>.0001: failures.append("pawl off the baked angle %s at %.2f s" % [aid,t])
						# (MotionBake.pawl reads x in double precision, the pose's Vector3 in float32)
						if absf(want_swing-scene.motion.pawl(aid,t))>.00002: failures.append("the manifest's pawl phase is not the bake's %s" % aid)
						if roller!=null:
							if roller.global_position.distance_to(nose)>.00001: failures.append("roller off the pawl's axle %s at %.2f s" % [aid,t])
							turned.append([pz["root"].x,swing.inverse()*roller.global_basis*scene.roller_home[aid].inverse()])
					if roller!=null:
						# between the two moments farthest apart along the rail the roller has
						# turned about the pawl's axle by ROLLER_SPIN times the rail travelled
						# (the swing taken out)
						var far: int=0
						for i in turned.size(): if absf(turned[i][0]-turned[0][0])>absf(turned[far][0]-turned[0][0]): far=i
						var dx: float=turned[far][0]-turned[0][0]
						var rel: Basis=turned[far][1]*turned[0][1].inverse()
						var want: float=wrapf(float(cfg["pawl"].get("roller_spin",0.0))*dx,-PI,PI)
						var got: float=atan2(rel.x.y,rel.x.x)
						if absf(dx)<.001: failures.append("roller turn unmeasured (carriage did not move) "+aid)
						elif absf(wrapf(got-want,-PI,PI))>.0005 or absf(rel.z.z-1.0)>.0001: failures.append("roller does not roll on the tips %s (%.4f vs %.4f rad over %.3f m)" % [aid,got,want,dx])
					var pbox: AABB=pawl.mesh.get_aabb()
					# the lever's mesh runs from the eye past the yoke, and its tongues rise to the axle
					if pbox.position.x>-float(cfg["pawl"]["lever"])-.009 or pbox.end.x<.02 or pbox.end.y<float(cfg["pawl"]["finger"])+.003: failures.append("pawl mesh does not reach from its pivot to the roller's axle "+aid)
			elif scene.layout["arms"][aid]["kind"]=="mallet" and str(cfg.get("pinion","back")) in ["front","back"]: failures.append("mallet arm without a pawl "+aid)
			# Rail gantries, heads and racks are forms that are not frame variants: visible.
			var suffixes := ["_gantry","_railhead"] if servo else ["_gantry","_railhead","_rack"]
			for suffix in suffixes:
				var node: Node3D=scene.model.find_child("form_"+aid+suffix,true,false)
				if node==null or not node.visible: failures.append("rail "+suffix.substr(1)+" missing or hidden "+aid)
			if String(cfg.get("kind","")) in ["pick","rake"]:
				for d_key in ["thumb","d2","d3","d4"]:
					var dpart: String="digit_"+d_key
					if not scene.drive_parts[aid].has(dpart) or scene.drive_parts[aid][dpart]==null:
						failures.append("missing articulated digit "+dpart+" on "+aid)
				var hp_notes: Array=scene.motion.arms.get(aid,{}).get("hand_pose",{}).get("notes",[])
				if hp_notes.is_empty():
					failures.append("empty hand_pose notes on "+aid)
				else:
					var n0: Dictionary=hp_notes[0]
					var dk0: String="digit_"+String(n0.get("digit","d2"))
					scene.evaluate(-5.0)
					var b_rest: Basis=scene.drive_parts[aid][dk0].global_basis
					scene.evaluate(float(n0.get("t_close",0.1))+0.04)
					var b_curl: Basis=scene.drive_parts[aid][dk0].global_basis
					var rel_d: Basis=b_curl*b_rest.inverse()
					var ang_d: float=acos(clampf((rel_d.x.x+rel_d.y.y+rel_d.z.z-1.0)*0.5,-1.0,1.0))
					if ang_d<0.25:
						failures.append("digit %s on %s did not curl at t_close (%.3f rad)" % [dk0,aid,ang_d])
		# The click has a sound (docs/motion-design.md): every pawl carries a player
		# on its roller with the synthesised sample, CLICK_DB under the instruments;
		# a stepped arm clicks (where and how often is formlab.rig's, held by
		# tools/test_motion.py and tools/test_bake.py), no two STEPPED clicks (a
		# stepped or homing landing) come closer than CLICK_MIN_S, and a servo arm
		# never clicks. A stepped arm's freewheel clicks a tooth, as close as the
		# tooth rate puts them (11.9 ms at the fastest): those play frame-batched
		# on the arm's freewheel player, the ride tick lighter than the drop.
		var tick_decays = func(wav: AudioStreamWAV, shortest: float, longest: float) -> String:
			if wav==null or wav.get_length()<shortest or wav.get_length()>longest or wav.format!=AudioStreamWAV.FORMAT_16_BITS: return "missing or the wrong shape"
			var early := 0.0; var late := 0.0; var n: int=wav.data.size()/2; var tail: int=int(.01*wav.mix_rate)
			for i in mini(int(.005*wav.mix_rate),n): early=maxf(early,absf(wav.data.decode_s16(i*2))/32767.0)
			for i in range(n-tail,n): late=maxf(late,absf(wav.data.decode_s16(i*2))/32767.0)
			return "" if early>=.5 and late<=.05 else "not a tick that decays (%.2f, %.2f)" % [early,late]
		var clicked := 0
		var batched := {}   # fps -> [frames with a freewheel voice, the most clicks one voice carried, the most voices on a click player, ...on a freewheel player]
		for aid in scene.parts:
			var cfg: Dictionary=scene.layout["arms"][aid]
			var list: Array=scene.motion.click_times(aid)
			if not scene.motion.stepped(aid) and not list.is_empty(): failures.append("a servo arm clicks "+aid)
			if not cfg.has("pawl"): continue
			var cp: AudioStreamPlayer3D=scene.click_players.get(aid)
			if cp==null or cp.get_parent()!=scene.parts[aid]["roller"]: failures.append("no click player on the roller "+aid); continue
			if cp.volume_db>scene.CLICK_DB+1e-6 or cp.volume_db<scene.CLICK_DB-6.0: failures.append("click not mixed under the instruments "+aid)
			var why: String=tick_decays.call(cp.stream,.05,.3)
			if why!="": failures.append("click sample %s %s" % [why,aid])
			var stepped_arm: bool=scene.motion.stepped(aid)
			var wp: AudioStreamPlayer3D=scene.wheel_players.get(aid)
			if stepped_arm:
				if wp==null or wp.get_parent()!=scene.parts[aid]["roller"] or not (wp.stream is AudioStreamPolyphonic): failures.append("no freewheel player on the roller "+aid)
				elif absf(wp.volume_db-cp.volume_db)>1e-6 or (wp.stream as AudioStreamPolyphonic).polyphony!=cp.max_polyphony: failures.append("freewheel player not mixed and voiced as the click player "+aid)
				why=tick_decays.call(scene.ride_stream,.005,.05)
				if why!="": failures.append("ride sample %s %s" % [why,aid])
			elif wp!=null: failures.append("a %s arm has a freewheel player %s" % [cfg.get("kind",""),aid])
			var prev := -INF; var prev_any := -INF
			for c in list:
				var t: float=float(c["t"])
				if not (int(c["pawl"]) in [0,1] and int(c["step"]) in [0,1]): failures.append("click pawl/step not 0/1 %s at %.3f s" % [aid,t])
				if not stepped_arm and (int(c["step"])!=1 or int(c["pawl"])!=0): failures.append("a %s click is not a stepped drop %s at %.3f s" % [cfg.get("kind",""),aid,t])
				if t<prev_any: failures.append("clicks out of time order %s at %.3f s" % [aid,t])
				prev_any=t
				if int(c["step"])!=1: continue
				if t-prev<scene.motion.constant("CLICK_MIN_S")-1e-9: failures.append("stepped clicks faster than the floor %s at %.3f s" % [aid,t])
				prev=t
			clicked+=list.size()
			# Played frame by frame (performance.gd _play_clicks), every click sounds
			# exactly once, a frame's freewheel clicks as one voice, and neither of
			# the roller's players ever holds more voices than its polyphony —
			# at a capture's 30 fps, the usual 60 and a fast monitor's 144.
			for fps in [30.0,60.0,144.0]:
				var on_click: Array=[]; var on_wheel: Array=[]   # [start, length]
				var played := 0; var i := 0; var t0 := -1.0
				var most: Array=batched.get(fps,[0,0,0,0])
				for fr in range(1,int((scene.score.total_s+1.0)*fps)+2):
					var t1: float=-1.0+fr/fps
					var f: Dictionary=scene.click_frame(list,i,t0,t1)
					i=int(f["next"])
					played+=int(f["stepped"])+int(f["drop"])+int(f["ride"])
					for k in int(f["stepped"]): on_click.append([t1,cp.stream.get_length()])
					var v: Dictionary=scene.freewheel_voice(int(f["drop"]),int(f["ride"]))
					if not v.is_empty():
						if not stepped_arm: failures.append("a %s click batched %s" % [cfg.get("kind",""),aid])
						on_wheel.append([t1,(scene.ride_stream if v["ride"] else cp.stream).get_length()])
						most[0]+=1; most[1]=maxi(most[1],int(f["drop"])+int(f["ride"]))
					t0=t1
				batched[fps]=most
				if played!=list.size(): failures.append("frame playback at %d fps sounds %d of %d clicks %s" % [fps,played,list.size(),aid])
				for pair in [["click",on_click],["freewheel",on_wheel]]:
					var most_voices := 0; var alive: Array=[]
					for vc in pair[1]:
						alive=alive.filter(func(end): return end>vc[0]+1e-9)
						alive.append(vc[0]+vc[1]); most_voices=maxi(most_voices,alive.size())
					var slot: int=2 if pair[0]=="click" else 3
					most[slot]=maxi(most[slot],most_voices)
					if most_voices>scene.CLICK_VOICES: failures.append("%s player holds %d voices at %d fps, polyphony %d %s" % [pair[0],most_voices,fps,scene.CLICK_VOICES,aid])
		if clicked==0: failures.append("no mallet arm clicks in the piece")
		# a ride click is lighter than a drop; a frame's voice is louder by its count
		var one_drop: Dictionary=scene.freewheel_voice(1,0); var one_ride: Dictionary=scene.freewheel_voice(0,1)
		if not (one_ride["ride"] and not one_drop["ride"] and float(one_ride["db"])<float(one_drop["db"])-3.0): failures.append("a ride click is not lighter than a drop")
		if not (float(scene.freewheel_voice(0,2)["db"])>float(one_ride["db"])+2.9 and float(scene.freewheel_voice(2,0)["db"])>float(one_drop["db"])+2.9): failures.append("a frame's freewheel voice is not louder by its clicks' count")
		print("  freewheel clicks frame-batched: %s (fps: [freewheel voices, most clicks in one, peak voices on a click player, on a freewheel player])" % str(batched))
		# The blow shakes the ASSEMBLY, not only the arm (docs/motion-design.md):
		# a struck instrument's stand thumps, the striking arm's guide bars sag
		# and its gantry sways. Measured on the RENDERED nodes: before the first
		# blow every one of them sits at its imported home, within 40 ms of the
		# blow at least one has moved, and by the next strike's start (the
		# header's gate_end: the next stroke's apex)
		# they are home again — the shudder never smears a contact.
		for aid in scene.parts:
			if not scene.motion.stepped(aid) or scene.motion.blows(aid).is_empty(): continue
			# every blow's gate falls after it and no later than the next blow; a
			# stepped arm's blow carries its stroke's v_in and e
			var bl: Array=scene.motion.blows(aid)
			var stepped_b: bool=scene.motion.stepped(aid)
			for j in bl.size():
				var g = bl[j]["gate_end"]
				if (g==null)!=(j==bl.size()-1): failures.append("blow %d of %s: gate_end null off the last blow" % [j,aid])
				elif g!=null and not (float(g)>float(bl[j]["t"]) and float(g)<=float(bl[j+1]["t"])): failures.append("blow %d of %s: gate_end %.4f not in (its blow, the next]" % [j,aid,float(g)])
				if stepped_b and not (bl[j].has("v_in") and bl[j].has("e") and float(bl[j]["v_in"])>0.0 and float(bl[j]["e"])>0.0 and float(bl[j]["e"])<1.0): failures.append("stepped blow %d of %s carries no v_in / e" % [j,aid])
				if not stepped_b and (bl[j].has("v_in") or bl[j].has("e")): failures.append("a %s blow carries a mallet's v_in / e %s" % [scene.layout["arms"][aid].get("kind",""),aid])
			var mid: String=scene.motion.mech_of(aid)
			# node -> its imported home transform; the stand is shared by the
			# instrument's arms, so it is judged from the instrument's first blow.
			var probe: Array=[]
			for b in scene.shudder_nodes[aid]["bars"]: probe.append([b["node"],b["home"]])
			for f in scene.shudder_nodes[aid]["frame"]: probe.append([f["node"],f["home"]])
			var t_arm: float=float(scene.motion.blows(aid)[0]["t"])
			var t_first: float=t_arm
			if scene.stand_nodes.has(mid):
				probe.append([scene.stand_nodes[mid]["node"],scene.stand_nodes[mid]["home"]])
				for other in scene.motion.arms:
					if scene.motion.mech_of(other)==mid and not scene.motion.blows(other).is_empty(): t_first=minf(t_first,float(scene.motion.blows(other)[0]["t"]))
			if probe.is_empty(): failures.append("no assembly node answers "+aid); continue
			var away = func(pair: Array) -> float:
				var now: Transform3D=(pair[0] as Node3D).transform
				var spin: Quaternion=(now.basis*(pair[1] as Transform3D).basis.inverse()).get_rotation_quaternion()
				return maxf(now.origin.distance_to((pair[1] as Transform3D).origin),absf(spin.get_angle()))
			scene.evaluate(maxf(t_first-.5,-1.0))
			for pair in probe:
				if away.call(pair)>1e-9: failures.append("the assembly is not at rest before the first blow on "+aid)
			scene.evaluate(t_arm)
			for pair in probe:
				# only this arm's own nodes are promised zero at ITS blow (the
				# stand answers every arm of the instrument)
				if pair[0]!=scene.stand_nodes.get(mid,{}).get("node") and away.call(pair)>1e-9: failures.append("the assembly is not at rest at the blow it answers "+aid)
			var moved := 0.0
			for dt in [.01,.02,.03,.04]:
				scene.evaluate(t_arm+dt)
				for pair in probe: moved=maxf(moved,away.call(pair))
			if moved<1e-7: failures.append("the assembly does not answer a blow "+aid)
			if scene.motion.blows(aid).size()>1 and scene.motion.blows(aid)[0]["gate_end"]!=null:
				var gate: float=float(scene.motion.blows(aid)[0]["gate_end"])
				scene.evaluate(gate)
				for pair in probe:
					if pair[0]!=scene.stand_nodes.get(mid,{}).get("node") and away.call(pair)>1e-9: failures.append("the assembly still rings into the next strike "+aid)
		# Strings are strung by register like a harp: wound wire below C4, gut in the
		# middle, nylon from C5; every harp C is red and every harp F dark.
		for sid in scene.strings:
			var s: Dictionary=scene.layout["strings"][sid]
			var midi: float=float(s["midi"])
			var mat: ShaderMaterial=scene.strings[sid].get_child(0).material_override
			var family: int=int(mat.get_shader_parameter("family"))
			var expected: int=1 if midi<60.0 else (3 if midi>=72.0 else 2)
			if family!=expected: failures.append("string family off its register "+sid)
			# each family's highlight runs along the string by its own amount (string_aniso),
			# on the speaking length and on every dead length alike
			var aniso_want: float=scene.string_aniso(family)
			if absf(float(mat.get_shader_parameter("aniso"))-aniso_want)>1e-6: failures.append("string highlight anisotropy off its family "+sid)
			var dead_node: Node3D=scene.find_child(sid+" dead",false,false)
			if dead_node!=null:
				# ...and the winding's phase runs on over the bridge: each dead tube is told
				# the wire wound before it (the speaking length, then the bridge run)
				var wound: float=MotionBake.v(s["a"]).distance_to(MotionBake.v(s["b"]))
				# (an unset uniform reads back null: the speaking length leaves offset_m at its default 0)
				var speaking_offset=mat.get_shader_parameter("offset_m")
				if speaking_offset!=null and absf(speaking_offset)>1e-9: failures.append("speaking length does not start its winding at zero "+sid)
				for child in dead_node.get_children():
					if child.material_override is ShaderMaterial:
						var dm: ShaderMaterial=child.material_override
						if absf(float(dm.get_shader_parameter("aniso"))-aniso_want)>1e-6: failures.append("dead length anisotropy off its family "+sid)
						var dead_offset=dm.get_shader_parameter("offset_m")
						if dead_offset==null or absf(dead_offset-wound)>1e-5: failures.append("dead length restarts the winding's phase at its joint "+sid)
						var dead_len=dm.get_shader_parameter("length_m")
						if dead_len==null: failures.append("dead length carries no length_m "+sid)
						else: wound+=dead_len
			if not (aniso_want>0.0 if family in [1,2] else aniso_want<=0.0): failures.append("string_aniso stretches a smooth wire's highlight along it "+sid)
			var colour: Color=mat.get_shader_parameter("albedo")
			if s["mid"]=="harp" and int(midi)%12==0 and not (colour.r>.6 and colour.g<.4): failures.append("harp C string not red "+sid)
			if s["mid"]=="harp" and int(midi)%12==5 and colour.r>.35: failures.append("harp F string not dark "+sid)
			# A harp or rake string runs on past its speaking length: two straight dead
			# lengths (b to the bridge pin, bridge pin to the tuning pin) beside the string.
			if s["mid"]=="harp" or s["mid"]=="rake":
				var dead: Node3D=scene.find_child(sid+" dead",true,false)
				if dead==null or dead.get_child_count()!=3: failures.append("string has no dead length and coil "+sid)
				else:
					var first: MeshInstance3D=dead.get_child(0)
					if first.global_position.distance_to(MotionBake.v(s["b"]))>.00001: failures.append("dead length does not start at b "+sid)
					var top: MeshInstance3D=dead.get_child(1)
					if top.global_position.y<=MotionBake.v(s["b"]).y+.1: failures.append("dead length does not climb to the neck "+sid)
					# ...and winds on its tuning pin (formlab.layout.pin_wrap): a coil about the
					# pin's axis at the wrap's centre, as wide as the pin plus two wires, running
					# from the string plane toward the neck no further than the room the plan gives.
					var coil: MeshInstance3D=dead.get_child(2); var w: Dictionary=s["neck"]["wrap"]
					var radius: float=.0035*pow(2.0,(64.0-midi)/18.0); var box: AABB=coil.mesh.get_aabb()
					if coil.global_position.distance_to(MotionBake.v(w["centre"]))>.00001: failures.append("coil not on its tuning pin "+sid)
					if absf(box.size.x-2.0*(float(w["r"])+2.0*radius))>.002 or absf(box.size.y-2.0*(float(w["r"])+2.0*radius))>.002: failures.append("coil not wound on the pin "+sid)
					if box.position.z<-radius-.0001 or box.end.z>float(w["room"])+.0001 or box.size.z<3.0*radius: failures.append("coil runs past its room on the pin, or does not advance "+sid)
		# A plectrum is horn in a brass ferrule: the pick arms' tool mesh carries a brass
		# surface (the object's own slot: ferrule and screws) and a horn one (the blade);
		# a mallet is one felt surface; a hammer's flange is metal with one felt pad on
		# its check, and the head that hangs off it is felt on a bronze eye.
		for aid in scene.parts:
			var tool: MeshInstance3D=scene.parts[aid]["tool"]; var names: Array=[]
			for index in tool.mesh.get_surface_count(): names.append(tool.mesh.surface_get_material(index).resource_name.to_lower())
			var horn: int=0; var brass: int=0
			for n in names:
				if n.contains("horn"): horn+=1
				if n.contains("brass"): brass+=1
			var kind: String=str(scene.layout["arms"][aid]["kind"])
			if kind=="mallet":
				if names.size()!=1 or not names[0].contains("felt"): failures.append("mallet is not one felt surface "+aid)
			elif kind=="hammer":
				if not (names.has("blued steel") and names.has("phosphor bronze") and names.has("satin brass") and names.has("wool felt")): failures.append("hammer flange is not steel, bronze, brass and a felt pad "+aid+" "+str(names))
				var head: MeshInstance3D=scene.parts[aid].get("head"); var hn: Array=[]
				if head==null: failures.append("hammer head mesh missing "+aid)
				else:
					for index in head.mesh.get_surface_count(): hn.append(head.mesh.surface_get_material(index).resource_name.to_lower())
					if not (hn.has("wool felt") and hn.has("phosphor bronze") and hn.has("blued steel")): failures.append("hammer head is not felt on a bronze eye "+aid+" "+str(hn))
			elif names.size()!=2 or horn!=1 or brass!=1: failures.append("plectrum is not horn in a brass ferrule "+aid+" "+str(names))
		# The chamber's flywheel turns about z once a bar, and the belt pulley with it,
		# faster by the pulleys' radii (formlab.layout.flywheel_plan).
		var wheel: Node3D=scene.model.find_child("Chamber flywheel",true,false)
		var pulley: Node3D=scene.model.find_child("Chamber belt pulley",true,false)
		if wheel==null or pulley==null or not scene.layout.has("flywheel"): failures.append("flywheel assembly missing from the model")
		else:
			var f: Dictionary=scene.layout["flywheel"]
			var ratio: float=float(f["wraps"][0][1])/float(f["wraps"][1][1]) if f.has("wraps") else float(f["cyls"]["drive pulley"][2])/float(f["cyls"]["belt pulley"][2])
			var bar: float=240.0/float(scene.score.doc.get("bpm",84.0))
			# The imported mesh's own axes are whatever Blender baked in, so judge the
			# motion by the rotation between the two poses, not by any one local axis.
			scene.evaluate(10.0); var w0: Basis=wheel.global_basis; var p0: Basis=pulley.global_basis
			scene.evaluate(10.0+bar/4.0); var wq: Quaternion=(wheel.global_basis*w0.inverse()).get_rotation_quaternion(); var pq: Quaternion=(pulley.global_basis*p0.inverse()).get_rotation_quaternion()
			if absf(wq.get_angle()-TAU/4.0)>.001 or absf(absf(wq.get_axis().z)-1.0)>.0001: failures.append("flywheel does not turn a quarter turn in a quarter bar about z")
			var want: float=fmod(TAU/4.0*ratio,TAU); if want>PI: want=TAU-want
			if absf(pq.get_angle()-want)>.01 or absf(absf(pq.get_axis().z)-1.0)>.0001 or signf(pq.get_axis().z*pq.get_angle())!=signf(wq.get_axis().z*wq.get_angle()) and want<PI-.01: failures.append("belt pulley does not turn with the flywheel by the pulleys' ratio")
			if wheel.global_position.distance_to(MotionBake.v(f["centre"]))>.001: failures.append("flywheel off its planned centre")
	check_plucks(scene, failures)
	check_mallets(scene, failures)
	check_wire_seek(scene, failures)
	check_struck_surfaces(scene, failures)
	check_wrist_travel(scene, failures)
	# The wire shader holds a sub-pixel string at a minimum on-screen width by
	# rebuilding the ring from UV.y, so the mesh's ring convention is pinned here.
	var probe: ArrayMesh=scene._wire_mesh(1.0,.01,2,8); var pv: PackedVector3Array=probe.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
	if pv[0].distance_to(Vector3(.01,0,0))>1e-6 or pv[2].distance_to(Vector3(0,0,.01))>1e-6 or pv[9].distance_to(Vector3(.01,.5,0))>1e-6: failures.append("wire mesh ring convention (x=r cos, z=r sin, +y along the string) changed under the shader")
	var uniforms: Array=load("res://shaders/wire_string.gdshader").get_shader_uniform_list().map(func(u): return u["name"])
	if not ("min_px" in uniforms and "radius" in uniforms): failures.append("wire shader lost its minimum on-screen width")
	if not ("aniso" in uniforms and "contact_m" in uniforms): failures.append("wire shader lost its anisotropic highlight or its hardware contacts")
	# The sheath's ALPHA makes the whole material transparent, so without a depth
	# prepass the double-sided wire's inside wall bleeds through as a band.
	var render_line: String=""
	for line in load("res://shaders/wire_string.gdshader").code.split("\n"):
		if line.begins_with("render_mode"): render_line=line
	if not ("depth_prepass_alpha" in render_line): failures.append("wire shader draws no depth prepass: the tube's far wall shows through as a ring band")
	if not ("cull_disabled" in render_line): failures.append("wire shader culls back faces: the blur sheath loses its far wall")
	print("  integrated GLB: %d tool contacts; %d rigs" % [contacts,scene.parts.size()+scene.pillar_players.size()])
	print("PERFORMANCE: PASS" if failures.is_empty() else str(failures))
	quit(0 if failures.is_empty() else 1)
