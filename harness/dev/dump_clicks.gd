extends SceneTree
## Print every ratchet click the baked performance makes (MotionBake) ("CLICK aid t teeth
## pawl step", one a click: a stepped or homing landing, a hammer click, or a
## mallet freewheel's crossing of a tooth; pawl 1 when it rides the tips, step
## 1 when stepped) and write the synthesised click samples as WAVs beside it —
## the drop click and the lighter ride tick (performance.gd click_sample,
## ride_sample) — so a mix of the piece with its clicks can be made outside the
## harness (tools/click_mix.py). --asset=NAME picks the manifest; --out=PATH
## names the click WAV; --ride_out=PATH the ride tick's (default: PATH with
## "_ride" before its extension).
func _init() -> void:
	var sd := ScoreDoc.new()
	if not sd.load(ScoreDoc.default_path()):
		print(sd.errors); quit(1); return
	var asset := "clockwork"
	var out := ""
	var ride_out := ""
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--asset="): asset=a.substr(8)
		if a.begins_with("--out="): out=a.substr(6)
		if a.begins_with("--ride_out="): ride_out=a.substr(11)
	var rig := MotionBake.new()
	if not rig.load(MotionBake.path_for(sd.path,asset),sd.path,"res://assets/"+asset+".json"):
		print(rig.errors); quit(1); return
	for aid in rig.arms:
		for c in rig.click_times(aid):
			print("CLICK %s %.9f %.6f %d %d" % [aid,float(c["t"]),float(c["teeth"]),int(c["pawl"]),int(c["step"])])
	if out!="":
		var perf: GDScript=load("res://performance.gd")
		var wav: AudioStreamWAV=perf.click_sample(rig.constant("RING_HZ"),rig.constant("RING_TAU"))
		wav.save_to_wav(out)
		print("WAV ",out," ",wav.get_length()," s")
		if ride_out=="": ride_out=out.get_basename()+"_ride."+(out.get_extension() if out.get_extension()!="" else "wav")
		var tick: AudioStreamWAV=perf.ride_sample()
		tick.save_to_wav(ride_out)
		print("RIDEWAV ",ride_out," ",tick.get_length()," s")
	quit(0)
