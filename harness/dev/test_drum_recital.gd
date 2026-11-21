extends SceneTree
## Check the shipped instrument, score, moving contacts and complete four-limb reach.

func _init() -> void:
	call_deferred("check")

# The moving stick shafts and arm stocks must clear the real meshes through
# every transfer. Probe around their cross-sections as well as down the centre.
func sweep(scene) -> int:
	var fixed: Array[MeshInstance3D]=[scene.optics,scene.torso,scene._part("Kit stands and shells"),scene._part("Hat bottom")]
	for v in scene.surfaces:fixed.append(v.mesh)
	var limbs: Array=[scene.left,scene.right]
	var obstacles:=fixed.duplicate()
	for l in limbs:obstacles.append_array([l.stick,l.palm,l.upper,l.lower])
	var trees: Array[TriangleMesh]=[]
	for ob in obstacles:trees.append(ob.mesh.generate_triangle_mesh())
	var offsets: Array[Vector3]=[Vector3.ZERO,Vector3.RIGHT,Vector3.LEFT,Vector3.BACK,Vector3.FORWARD]
	# The upper stock is pinned inside the shoulder casting. Start its probes
	# beyond the spherical bearing. Each distal end has its own adjoining joint.
	var spans: Array[Vector2]=[Vector2(-.123,.355),Vector2(.055,scene.lower_l-.040),Vector2(.142,scene.upper_l-.058)]
	var radii:=PackedFloat32Array([.006,.034,.042])
	var faults:=0
	for frame in ceili(scene.duration*180):
		scene.evaluate(frame/180.)
		for arm in limbs:
			for j in obstacles.size():
				var ob: Node3D=obstacles[j]
				if ob==arm.palm or ob==arm.upper or ob==arm.lower or ob==arm.stick:continue
				var inverse:=ob.transform.affine_inverse()
				for k in spans.size():
					var part: Node3D=arm.stick if k==0 else arm.lower if k==1 else arm.upper
					var world_to_obstacle:=inverse*part.transform
					for direction in offsets:
						var offset:=direction*radii[k]
						var p:=world_to_obstacle*(Vector3.UP*spans[k].x+offset)
						var q:=world_to_obstacle*(Vector3.UP*spans[k].y+offset)
						if not trees[j].intersect_segment(p,q).is_empty():
							if faults==0: print("  intersection ",part.name," / ",ob.name," at ",frame/180.)
							faults+=1
	return faults

func check() -> void:
	var scene=load("res://drum_recital.tscn").instantiate()
	if scene.get_script()==null:push_error("drum recital did not compile");quit(1);return
	root.add_child(scene)
	scene.playing=false;scene.player.stop()
	var pad_error:=0.
	var kick_error:=0.
	var foot_error:=0.
	var arm_error:=0.
	var leg_error:=0.
	var tricks:=0
	var hits:=0
	var bottom: MeshInstance3D=scene._part("Hat bottom")
	var lip:=MotionBake.v(scene.kit.hat_lip)
	var double_crashes:=0
	var previous_crash:=-1.
	for limb in [scene.left,scene.right]:
		for n in limb.strokes:
			if n.voice=="":continue
			scene.evaluate(n.t)
			var voice=scene.voices[n.voice]
			var point: Vector3=voice.mesh.to_global(n.local_point)
			if not voice.metal:
				var response: float=voice.head.get_shader_parameter("flex")
				point.y+=scene._skin_height(n.local_point,voice.radius,-response/.006)
			var center: Vector3=limb.stick.to_global(Vector3.UP*scene.stick_l)
			pad_error=maxf(pad_error,center.distance_to(point+n.normal*float(scene.kit.bead)))
			if n.spin or n.overhand:tricks+=1
			hits+=1
	for e in scene.score.events:
		var t:=float(e.t)
		if e.limb=="kick":
			scene.evaluate(t)
			var ball: Vector3=scene.beater.to_global(Vector3.UP*.286)
			kick_error=maxf(kick_error,absf(ball.z+.037-.29))
			hits+=1
		elif e.limb=="pedal":
			scene.evaluate(t)
			foot_error=maxf(foot_error,scene.drum.mesh.to_global(lip).distance_to(bottom.to_global(lip)))
			hits+=1
		elif e.voice in ["crash_l","crash_r"]:
			if previous_crash==t:double_crashes+=1
			previous_crash=t
	for frame in range(ceili(scene.duration*240.)):
		scene.evaluate(frame/240.)
		for limb in [scene.left,scene.right]:
			var shoulder: Vector3=scene.torso.to_global(Vector3(limb.side*scene.shoulder_local.x,scene.shoulder_local.y,scene.shoulder_local.z))
			arm_error=maxf(arm_error,limb.upper.position.distance_to(shoulder))
			arm_error=maxf(arm_error,limb.upper.to_global(Vector3.UP*scene.upper_l).distance_to(limb.lower.position))
			arm_error=maxf(arm_error,limb.lower.to_global(Vector3.UP*scene.lower_l).distance_to(limb.palm.position))
			leg_error=maxf(leg_error,limb.thigh.to_global(Vector3.UP*.49).distance_to(limb.shin.position))
			leg_error=maxf(leg_error,limb.shin.to_global(Vector3.UP*.46).distance_to(limb.boot.position))
	scene.evaluate(8.114)
	var old: Transform3D=scene.right.stick.transform
	scene.evaluate(28.);scene.evaluate(8.114)
	var match_seek:=old.is_equal_approx(scene.right.stick.transform)
	var crossings:=sweep(scene)
	print("  rendered mesh intersections at 180 Hz: ",crossings)
	var valid: bool=crossings==0 and hits==scene.score.events.size() and tricks>=4 and double_crashes>=3 and pad_error<.0001 and kick_error<.0001 and foot_error<.0001 and arm_error<.0001 and leg_error<.0001 and match_seek
	print("DRUM KIT: %d sounded contacts, %d full turns, %d paired crashes; maximum error in mm: bead %.4f kick %.4f hi-hat %.4f arms %.4f legs %.4f; seek %s" % [hits,tricks,double_crashes,pad_error*1000,kick_error*1000,foot_error*1000,arm_error*1000,leg_error*1000,match_seek])
	print("DRUM KIT: PASS" if valid else "DRUM KIT: FAIL")
	quit(0 if valid else 1)
