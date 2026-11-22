extends SceneTree
## Validate the imported performances through the gallery's normal selector.

func _init() -> void:
	call_deferred("check")

func check() -> void:
	var packed: PackedScene=load("res://cabinet_recital.tscn")
	if packed==null:
		quit(1);return
	var stage=packed.instantiate()
	if stage.get_script()==null or not stage.has_method("_select"):
		push_error("Cabinet scene did not compile");quit(1);return
	root.add_child(stage)
	var failures:=PackedStringArray()
	if stage.catalog.size()!=25:failures.append("catalog size")
	var notes:=0
	for i in stage.catalog.size():
		stage._select(i)
		var row: Dictionary=stage.catalog[i]
		var player: AnimationPlayer=stage.animator
		if player==null or not player.has_animation("Recital"):
			failures.append(row.id+" missing animation");continue
		var anim: Animation=player.get_animation("Recital")
		if absf(anim.length-stage.duration)>.021 or absf(stage.audio.stream.get_length()-stage.duration)>.035:
			failures.append(row.id+" score, animation and audio clocks differ")
		if anim.get_track_count()<stage.layouts[row.id].moving_tracks:
			failures.append(row.id+" missing actuator tracks")
		var parts: Array[Node]=stage.model.find_children("*","MeshInstance3D",true,false)
		if row.id == "handpan":
			var fields: Array[MeshInstance3D] = []
			for part: MeshInstance3D in parts:
				if part.get_blend_shape_count() == 1:
					fields.append(part)
			if fields.size() != 8:
				failures.append("handpan missing formed tone fields")
			var heard := {}
			var flexed := {}
			for attack in row.events:
				heard[int(attack.lane)] = true
				stage.evaluate(float(attack.t) + .035)
				for field in fields:
					if absf(field.get_blend_shape_value(0)) > .1:
						flexed[field.name] = true
			if flexed.size() != heard.size():
				failures.append("handpan tone fields did not respond to their lanes")
			stage.evaluate(0.)
			for field in fields:
				if absf(field.get_blend_shape_value(0)) > .001:
					failures.append("handpan field did not return home")
		var home: Array[Transform3D]=[]
		stage.evaluate(0.)
		for part: Node3D in parts: home.append(part.transform)
		var active:=false
		for event in row.events:
			notes+=1
			stage.evaluate(event.t)
			for j in parts.size():
				if not home[j].is_equal_approx(parts[j].transform):
					active=true;break
		if not active:failures.append(row.id+" did not move")
		stage.evaluate(.65)
		var reference: Array[Transform3D]=[]
		for part: Node3D in parts: reference.append(part.transform)
		stage.evaluate(stage.duration*.90);stage.evaluate(.65)
		for j in parts.size():
			if not reference[j].is_equal_approx(parts[j].transform):
				failures.append(row.id+" has a history-dependent seek");break
		if stage.picker.selected!=i or stage.label_title.text!=row.title:
			failures.append(row.id+" selection has stale UI")
		stage._toggle()
		if stage.running:failures.append(row.id+" pause")
		stage._toggle()
		if not stage.running:failures.append(row.id+" resume")
	stage._select(stage.catalog.size())
	if stage.index!=0:failures.append("selection wrap")
	stage.free()
	for failure in failures:push_error(failure)
	print("CABINET: %d instruments, %d score events, %d failures" % [25,notes,failures.size()])
	quit(0 if failures.is_empty() else 1)
