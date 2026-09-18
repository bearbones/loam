extends SceneTree
## Integration check: the GLB nodes and actual animated tool origins agree with the score.
func _init() -> void:
	call_deferred("check_scene")

func check_scene() -> void:
	var scene=load("res://performance.tscn").instantiate()
	root.add_child(scene)
	scene.playing=false
	var failures: Array=[]
	var contacts := 0
	for aid in scene.parts:
		for part in scene.parts[aid]:
			if scene.parts[aid][part]==null: failures.append("missing GLB pivot "+aid+"/"+part)
	if failures.is_empty():
		for e in scene.score.events:
			for k in range(e["strings"].size()):
				var t: float=float(e["t"])+k*float(e.get("spread_s",0))
				scene.evaluate(t)
				var tool: Node3D=scene.parts[e["actuator"]]["tool"]
				var target: Vector3=scene.motion.contact(e["strings"][k],e.get("pick"))
				if tool.global_position.distance_to(target)>.00001: failures.append("rendered tool misses contact")
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
			var pose: Dictionary=scene.motion.pose(aid,48.0); scene.evaluate(48.0)
			var elbow_node: Node3D=scene.parts[aid]["elbow"]
			if elbow_node.global_position.distance_to(pose["elbow"])>.00001: failures.append("elbow pin off its pose "+aid)
			var upper2: Node3D=scene.parts[aid]["upper2"]
			if upper2.global_position.distance_to(pose["root"]+scene.motion.v(cfg["o1"]))>.00001: failures.append("parallel bar off its pin "+aid)
			# The pinion sits on its recorded mount (formlab.clearance.MOUNTS) and lies in
			# the plane that mount implies: upright (thin along z) in front of or behind
			# the carriage, flat (thin along y) above or below it.
			var gear: MeshInstance3D=scene.parts[aid]["gear"]
			var mount: String=str(cfg.get("pinion","back"))
			var offsets := {"front": Vector3(0,0,.195), "back": Vector3(0,0,-.195), "up": Vector3(0,.17,-.10), "down": Vector3(0,-.17,-.10)}
			if not offsets.has(mount): failures.append("unknown pinion mount "+mount+" "+aid)
			elif gear.global_position.distance_to(pose["root"]+offsets[mount])>.00001: failures.append("pinion off its mount "+aid)
			else:
				var box: AABB=gear.global_transform*gear.mesh.get_aabb()
				var thin: float=box.size.y if (mount=="up" or mount=="down") else box.size.z
				var wide: float=box.size.x
				if thin>.08 or wide<.25: failures.append("pinion not lying in its mount's plane %s (%.3f thin, %.3f wide)" % [aid,thin,wide])
			# Rail gantries, heads and racks are forms that are not frame variants: visible.
			for suffix in ["_gantry","_railhead"]:
				var node: Node3D=scene.model.find_child("form_"+aid+suffix,true,false)
				if node==null or not node.visible: failures.append("rail "+suffix.substr(1)+" missing or hidden "+aid)
		# Strings are strung by register like a harp: wound wire below C4, gut in the
		# middle, nylon from C5; every harp C is red and every harp F dark.
		for sid in scene.strings:
			var s: Dictionary=scene.layout["strings"][sid]
			var midi: float=float(s["midi"])
			var mat: ShaderMaterial=scene.strings[sid].get_child(0).material_override
			var family: int=int(mat.get_shader_parameter("family"))
			var expected: int=1 if midi<60.0 else (3 if midi>=72.0 else 2)
			if family!=expected: failures.append("string family off its register "+sid)
			var colour: Color=mat.get_shader_parameter("albedo")
			if s["mid"]=="harp" and int(midi)%12==0 and not (colour.r>.6 and colour.g<.4): failures.append("harp C string not red "+sid)
			if s["mid"]=="harp" and int(midi)%12==5 and colour.r>.35: failures.append("harp F string not dark "+sid)
			# A harp or rake string runs on past its speaking length: two straight dead
			# lengths (b to the bridge pin, bridge pin to the tuning pin) beside the string.
			if s["mid"]=="harp" or s["mid"]=="rake":
				var dead: Node3D=scene.find_child(sid+" dead",true,false)
				if dead==null or dead.get_child_count()!=2: failures.append("string has no dead length "+sid)
				else:
					var first: MeshInstance3D=dead.get_child(0)
					if first.global_position.distance_to(scene.motion.v(s["b"]))>.00001: failures.append("dead length does not start at b "+sid)
					var top: MeshInstance3D=dead.get_child(1)
					if top.global_position.y<=scene.motion.v(s["b"]).y+.1: failures.append("dead length does not climb to the neck "+sid)
		# The chamber's flywheel turns about z once a bar, and the belt pulley with it,
		# faster by the pulleys' radii (formlab.layout.flywheel_plan).
		var wheel: Node3D=scene.model.find_child("Chamber flywheel",true,false)
		var pulley: Node3D=scene.model.find_child("Chamber belt pulley",true,false)
		if wheel==null or pulley==null or not scene.layout.has("flywheel"): failures.append("flywheel assembly missing from the model")
		else:
			var f: Dictionary=scene.layout["flywheel"]
			var ratio: float=float(f["cyls"]["drive pulley"][2])/float(f["cyls"]["belt pulley"][2])
			var bar: float=240.0/float(scene.score.doc.get("bpm",84.0))
			# The imported mesh's own axes are whatever Blender baked in, so judge the
			# motion by the rotation between the two poses, not by any one local axis.
			scene.evaluate(10.0); var w0: Basis=wheel.global_basis; var p0: Basis=pulley.global_basis
			scene.evaluate(10.0+bar/4.0); var wq: Quaternion=(wheel.global_basis*w0.inverse()).get_rotation_quaternion(); var pq: Quaternion=(pulley.global_basis*p0.inverse()).get_rotation_quaternion()
			if absf(wq.get_angle()-TAU/4.0)>.001 or absf(absf(wq.get_axis().z)-1.0)>.0001: failures.append("flywheel does not turn a quarter turn in a quarter bar about z")
			var want: float=fmod(TAU/4.0*ratio,TAU); if want>PI: want=TAU-want
			if absf(pq.get_angle()-want)>.01 or absf(absf(pq.get_axis().z)-1.0)>.0001 or signf(pq.get_axis().z*pq.get_angle())!=signf(wq.get_axis().z*wq.get_angle()) and want<PI-.01: failures.append("belt pulley does not turn with the flywheel by the pulleys' ratio")
			if wheel.global_position.distance_to(scene.motion.v(f["centre"]))>.001: failures.append("flywheel off its planned centre")
	# The wire shader holds a sub-pixel string at a minimum on-screen width by
	# rebuilding the ring from UV.y, so the mesh's ring convention is pinned here.
	var probe: ArrayMesh=scene._wire_mesh(1.0,.01,2,8); var pv: PackedVector3Array=probe.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
	if pv[0].distance_to(Vector3(.01,0,0))>1e-6 or pv[2].distance_to(Vector3(0,0,.01))>1e-6 or pv[9].distance_to(Vector3(.01,.5,0))>1e-6: failures.append("wire mesh ring convention (x=r cos, z=r sin, +y along the string) changed under the shader")
	var uniforms: Array=load("res://shaders/wire_string.gdshader").get_shader_uniform_list().map(func(u): return u["name"])
	if not ("min_px" in uniforms and "radius" in uniforms): failures.append("wire shader lost its minimum on-screen width")
	print("  integrated GLB: %d tool contacts; %d rigs" % [contacts,scene.parts.size()])
	print("PERFORMANCE: PASS" if failures.is_empty() else str(failures))
	quit(0 if failures.is_empty() else 1)
