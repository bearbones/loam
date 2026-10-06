extends SceneTree
## Integration check: the GLB nodes and actual animated tool origins agree with the score.
func _init() -> void:
	call_deferred("check_scene")

## Where the rendered hammer head's felt face is: the mesh is built at flip zero
## with the face straight down from the hinge, so the posed basis carries it.
func felt_face(head: Node3D, head_l: float) -> Vector3:
	return head.global_position+head.global_basis*Vector3(0,-head_l,0)

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
			var ts: Array=ScoreDoc.string_times(e)   # a rake roll's at its own onsets
			for k in range(e["strings"].size()):
				var t: float=ts[k]
				scene.evaluate(t)
				var tool: Node3D=scene.parts[e["actuator"]]["tool"]
				var target: Vector3=MotionBake.contact(scene.layout,e["strings"][k],e.get("pick"))
				if tool.global_position.distance_to(target)>.00001: failures.append("rendered tool misses contact")
				# A hinged hammer strikes with its head, not its tool: the flange's origin is
				# still the contact point, but what must land there is the felt face on the
				# flipping head, whose mesh carries it at (0,-HEAD_L,0) in the head's own frame.
				if scene.motion.hammer(e["actuator"]):
					var head: Node3D=scene.parts[e["actuator"]].get("head")
					if head==null: failures.append("hammer arm has no rendered head "+str(e["actuator"]))
					elif felt_face(head,scene.motion.head_l).distance_to(target)>.00001: failures.append("rendered felt face misses contact")
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
					if head2.global_position.distance_to(scene.motion.tip_at(aid,float(t))+Vector3(0,scene.motion.head_l,0))>.00001: failures.append("hammer hinge off the shank's end "+aid)
					if felt_face(head2,scene.motion.head_l).distance_to(want)>.00001: failures.append("rendered felt face off its flip %s at %.2f s" % [aid,t])
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
					var want: float=wrapf(-TAU*pose["root"].x/float(sc["pitch"]),-PI,PI)
					if (screw.transform*c).distance_to(c)>.00001: failures.append("leadscrew turns off its axis "+aid)
					if absf(angle_difference(screw.basis.get_euler().x,want))>.0001 or screw.basis.x.distance_to(Vector3.RIGHT)>.0001: failures.append("leadscrew not turned x/pitch "+aid)
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
					if scene.motion.hammer(aid) and ride_max!=0.0: failures.append("the hammer's pawl rides "+aid)
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
			for suffix in ["_gantry","_railhead"]:
				var node: Node3D=scene.model.find_child("form_"+aid+suffix,true,false)
				if node==null or not node.visible: failures.append("rail "+suffix.substr(1)+" missing or hidden "+aid)
		# The click has a sound (docs/motion-design.md): every pawl carries a player
		# on its roller with the synthesised sample, CLICK_DB under the instruments;
		# a stepped arm clicks (where and how often is formlab.rig's, held by
		# tools/test_motion.py and tools/test_bake.py), no two STEPPED clicks (a
		# stepped or homing landing, every hammer click) come closer than
		# CLICK_MIN_S, and a servo arm never clicks. A mallet's freewheel clicks a
		# tooth, as close as the tooth rate puts them (11.9 ms at the fastest):
		# those play frame-batched on the arm's freewheel player, the ride tick
		# lighter than the drop. The samples are ticks that decay.
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
			var mallet: bool=str(cfg.get("kind",""))=="mallet"
			var wp: AudioStreamPlayer3D=scene.wheel_players.get(aid)
			if mallet:
				if wp==null or wp.get_parent()!=scene.parts[aid]["roller"] or not (wp.stream is AudioStreamPolyphonic): failures.append("no freewheel player on the roller "+aid)
				elif absf(wp.volume_db-cp.volume_db)>1e-6 or (wp.stream as AudioStreamPolyphonic).polyphony!=cp.max_polyphony: failures.append("freewheel player not mixed and voiced as the click player "+aid)
				why=tick_decays.call(scene.ride_stream,.005,.05)
				if why!="": failures.append("ride sample %s %s" % [why,aid])
			elif wp!=null: failures.append("a %s arm has a freewheel player %s" % [cfg.get("kind",""),aid])
			var prev := -INF; var prev_any := -INF
			for c in list:
				var t: float=float(c["t"])
				if not (int(c["pawl"]) in [0,1] and int(c["step"]) in [0,1]): failures.append("click pawl/step not 0/1 %s at %.3f s" % [aid,t])
				if not mallet and (int(c["step"])!=1 or int(c["pawl"])!=0): failures.append("a %s click is not a stepped drop %s at %.3f s" % [cfg.get("kind",""),aid,t])
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
						if not mallet: failures.append("a %s click batched %s" % [cfg.get("kind",""),aid])
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
		# header's gate_end: a mallet's next apex, the hammer's next approach)
		# they are home again — the shudder never smears a contact.
		for aid in scene.parts:
			if not scene.motion.stepped(aid) or scene.motion.blows(aid).is_empty(): continue
			# every blow's gate falls after it and no later than the next blow; a
			# mallet's blow carries its stroke's v_in and e, the hammer's neither
			var bl: Array=scene.motion.blows(aid)
			var mallet_arm: bool=str(scene.layout["arms"][aid].get("kind",""))=="mallet"
			for j in bl.size():
				var g = bl[j]["gate_end"]
				if (g==null)!=(j==bl.size()-1): failures.append("blow %d of %s: gate_end null off the last blow" % [j,aid])
				elif g!=null and not (float(g)>float(bl[j]["t"]) and float(g)<=float(bl[j+1]["t"])): failures.append("blow %d of %s: gate_end %.4f not in (its blow, the next]" % [j,aid,float(g)])
				if mallet_arm and not (bl[j].has("v_in") and bl[j].has("e") and float(bl[j]["v_in"])>0.0 and float(bl[j]["e"])>0.0 and float(bl[j]["e"])<1.0): failures.append("mallet blow %d of %s carries no v_in / e" % [j,aid])
				if not mallet_arm and (bl[j].has("v_in") or bl[j].has("e")): failures.append("a %s blow carries a mallet's v_in / e %s" % [scene.layout["arms"][aid].get("kind",""),aid])
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
			var ratio: float=float(f["cyls"]["drive pulley"][2])/float(f["cyls"]["belt pulley"][2])
			var bar: float=240.0/float(scene.score.doc.get("bpm",84.0))
			# The imported mesh's own axes are whatever Blender baked in, so judge the
			# motion by the rotation between the two poses, not by any one local axis.
			scene.evaluate(10.0); var w0: Basis=wheel.global_basis; var p0: Basis=pulley.global_basis
			scene.evaluate(10.0+bar/4.0); var wq: Quaternion=(wheel.global_basis*w0.inverse()).get_rotation_quaternion(); var pq: Quaternion=(pulley.global_basis*p0.inverse()).get_rotation_quaternion()
			if absf(wq.get_angle()-TAU/4.0)>.001 or absf(absf(wq.get_axis().z)-1.0)>.0001: failures.append("flywheel does not turn a quarter turn in a quarter bar about z")
			var want: float=fmod(TAU/4.0*ratio,TAU); if want>PI: want=TAU-want
			if absf(pq.get_angle()-want)>.01 or absf(absf(pq.get_axis().z)-1.0)>.0001 or signf(pq.get_axis().z*pq.get_angle())!=signf(wq.get_axis().z*wq.get_angle()) and want<PI-.01: failures.append("belt pulley does not turn with the flywheel by the pulleys' ratio")
			if wheel.global_position.distance_to(MotionBake.v(f["centre"]))>.001: failures.append("flywheel off its planned centre")
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
	print("  integrated GLB: %d tool contacts; %d rigs" % [contacts,scene.parts.size()])
	print("PERFORMANCE: PASS" if failures.is_empty() else str(failures))
	quit(0 if failures.is_empty() else 1)
