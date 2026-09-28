extends SceneTree
## Print every ratchet click the baked performance makes (MotionBake) ("CLICK aid t teeth", one a
## click, at the click's landing) and write the synthesised click sample as a
## WAV beside it, so a mix of the piece with its clicks can be made outside
## the harness (tools/click_mix.py). --asset=NAME picks the manifest;
## --out=PATH names the WAV.
func _init() -> void:
	var sd := ScoreDoc.new()
	if not sd.load(ScoreDoc.default_path()):
		print(sd.errors); quit(1); return
	var asset := "clockwork"
	var out := ""
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--asset="): asset=a.substr(8)
		if a.begins_with("--out="): out=a.substr(6)
	var rig := MotionBake.new()
	if not rig.load(MotionBake.path_for(sd.path,asset),sd.path,"res://assets/"+asset+".json"):
		print(rig.errors); quit(1); return
	for aid in rig.arms:
		for c in rig.click_times(aid):
			print("CLICK %s %.9f %.6f" % [aid,float(c["t"]),float(c["teeth"])])
	if out!="":
		var wav: AudioStreamWAV=load("res://performance.gd").click_sample(rig.constant("RING_HZ"),rig.constant("RING_TAU"))
		wav.save_to_wav(out)
		print("WAV ",out," ",wav.get_length()," s")
	quit(0)
