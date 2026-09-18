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
					for s in scene.motion.sched[aid].slice(0,8): moments.append(float(s["hit"]))   # the arm surely moves between some of its contacts
					for t in moments:
						scene.evaluate(t); var pz: Dictionary=scene.motion.pose(aid,t)
						if pawl.global_position.distance_to(pz["root"]+scene.motion.v(cfg["pawl"]["pivot"]))>.00001: failures.append("pawl off its pivot "+aid)
						var swing: Basis=pawl.global_basis*scene.pawl_home[aid].inverse()
						var nose: Vector3=pawl.global_position+swing*scene.motion.v(cfg["pawl"]["nose"])
						var q: Vector3=nose-gear.global_position
						if absf(ClockworkMotion.tooth_distance(q.x,q.y,pz["root"].x+phase)-float(cfg["pawl"]["nose_r"]))>.00002 or absf(q.z)>.0001: failures.append("pawl roller not riding the teeth %s at %.2f s" % [aid,t])
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
			for suffix in ["_gantry","_railhead"]:
				var node: Node3D=scene.model.find_child("form_"+aid+suffix,true,false)
				if node==null or not node.visible: failures.append("rail "+suffix.substr(1)+" missing or hidden "+aid)
		# The blow shakes the ASSEMBLY, not only the arm (docs/motion-design.md):
		# a struck instrument's stand thumps, the striking arm's guide bars sag
		# and its gantry sways. Measured on the RENDERED nodes: before the first
		# blow every one of them sits at its imported home, within 40 ms of the
		# blow at least one has moved, and by the next strike's start they are
		# home again — the shudder never smears a contact.
		for aid in scene.parts:
			if not scene.motion.stepped(aid) or scene.motion.blows_by_arm[aid].is_empty(): continue
			var mid: String=scene.motion.mech_of[aid]
			# node -> its imported home transform; the stand is shared by the
			# instrument's arms, so it is judged from the instrument's first blow.
			var probe: Array=[]
			for b in scene.shudder_nodes[aid]["bars"]: probe.append([b["node"],b["home"]])
			for f in scene.shudder_nodes[aid]["frame"]: probe.append([f["node"],f["home"]])
			var t_arm: float=float(scene.motion.blows_by_arm[aid][0]["t"])
			var t_first: float=t_arm
			if scene.stand_nodes.has(mid):
				probe.append([scene.stand_nodes[mid]["node"],scene.stand_nodes[mid]["home"]])
				t_first=minf(t_first,float(scene.motion.blows_by_mech[mid][0]["t"]))
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
			if scene.motion.blows_by_arm[aid].size()>1:
				var gate: float=float(scene.motion.blows_by_arm[aid][0]["gate_end"])
				if is_finite(gate):
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
				for child in dead_node.get_children():
					if child.material_override is ShaderMaterial and absf(float(child.material_override.get_shader_parameter("aniso"))-aniso_want)>1e-6: failures.append("dead length anisotropy off its family "+sid)
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
					if first.global_position.distance_to(scene.motion.v(s["b"]))>.00001: failures.append("dead length does not start at b "+sid)
					var top: MeshInstance3D=dead.get_child(1)
					if top.global_position.y<=scene.motion.v(s["b"]).y+.1: failures.append("dead length does not climb to the neck "+sid)
					# ...and winds on its tuning pin (formlab.layout.pin_wrap): a coil about the
					# pin's axis at the wrap's centre, as wide as the pin plus two wires, running
					# from the string plane toward the neck no further than the room the plan gives.
					var coil: MeshInstance3D=dead.get_child(2); var w: Dictionary=s["neck"]["wrap"]
					var radius: float=.0035*pow(2.0,(64.0-midi)/18.0); var box: AABB=coil.mesh.get_aabb()
					if coil.global_position.distance_to(scene.motion.v(w["centre"]))>.00001: failures.append("coil not on its tuning pin "+sid)
					if absf(box.size.x-2.0*(float(w["r"])+2.0*radius))>.002 or absf(box.size.y-2.0*(float(w["r"])+2.0*radius))>.002: failures.append("coil not wound on the pin "+sid)
					if box.position.z<-radius-.0001 or box.end.z>float(w["room"])+.0001 or box.size.z<3.0*radius: failures.append("coil runs past its room on the pin, or does not advance "+sid)
		# A plectrum is horn in a brass ferrule: the pick arms' tool mesh carries a brass
		# surface (the object's own slot: ferrule and screws) and a horn one (the blade);
		# a mallet is one felt surface.
		for aid in scene.parts:
			var tool: MeshInstance3D=scene.parts[aid]["tool"]; var names: Array=[]
			for index in tool.mesh.get_surface_count(): names.append(tool.mesh.surface_get_material(index).resource_name.to_lower())
			var horn: int=0; var brass: int=0
			for n in names:
				if n.contains("horn"): horn+=1
				if n.contains("brass"): brass+=1
			if scene.layout["arms"][aid]["kind"]=="mallet":
				if names.size()!=1 or not names[0].contains("felt"): failures.append("mallet is not one felt surface "+aid)
			elif names.size()!=2 or horn!=1 or brass!=1: failures.append("plectrum is not horn in a brass ferrule "+aid+" "+str(names))
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
	if not ("aniso" in uniforms and "contact_m" in uniforms): failures.append("wire shader lost its anisotropic highlight or its hardware contacts")
	print("  integrated GLB: %d tool contacts; %d rigs" % [contacts,scene.parts.size()])
	print("PERFORMANCE: PASS" if failures.is_empty() else str(failures))
	quit(0 if failures.is_empty() else 1)
