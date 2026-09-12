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
			var actual: float=upper.mesh.get_aabb().size.y*upper.global_basis.y.length()
			if absf(actual-float(scene.layout["arms"][aid]["l1"]))>.001: failures.append("imported link axis/scale wrong "+aid)
	print("  integrated GLB: %d tool contacts; %d rigs" % [contacts,scene.parts.size()])
	print("PERFORMANCE: PASS" if failures.is_empty() else str(failures))
	quit(0 if failures.is_empty() else 1)
