extends Node3D
## Shared deterministic capture for the chamber and drum recital.
var shot := ""
var capture_dir := ""
var frame := 0
var warmup_frames := 0
var capture_start := 45.5
var capture_seconds := 8.0
var capture_fps := 30.0
var capture_speed := 1.0         # score seconds a video second: 0.25 is quarter speed
var capture_target_size := Vector2i.ZERO # final output size before SSAA upscaling
var capture_srv: TCPServer = null
var capture_tcp: StreamPeerTCP = null
var capture_pid := -1
var fixed_time := 48.0

func option(key: String, fallback: String) -> String:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--"+key+"="):
			return a.substr(key.length()+3)
	return fallback

func configure_capture(default_time: float, default_start: float, default_seconds: float) -> int:
	shot=OS.get_environment("SHOT")
	fixed_time=float(option("time",str(default_time)))
	capture_dir=option("capture","")
	capture_start=float(option("start",str(default_start)))
	capture_seconds=float(option("seconds",str(default_seconds)))
	capture_fps=float(option("fps","30"))
	# A slow-motion capture takes capture_fps frames a VIDEO second while score
	# time runs at capture_speed: at 60 fps and 0.25, a 90 ms click fills 22
	# frames. --seconds stays the score window, so the frame count grows.
	capture_speed=maxf(float(option("speed","1")),.001)
	if capture_dir!="":
		DirAccess.make_dir_recursive_absolute(capture_dir.get_base_dir() if capture_dir.ends_with(".mp4") else capture_dir)
	# --size=WxH renders at exactly that size whatever the window manager makes
	# of the window: the root viewport renders at the content scale size and is
	# only scaled to the window for display (captures read the viewport).
	var size: PackedStringArray=option("size","").split("x",false)
	var ssaa := maxi(int(option("ssaa","2" if (shot!="" or capture_dir!="") else "1")),1)
	if size.size()==2:
		capture_target_size=Vector2i(int(size[0]),int(size[1]))
		get_window().content_scale_mode=Window.CONTENT_SCALE_MODE_VIEWPORT
		get_window().content_scale_aspect=Window.CONTENT_SCALE_ASPECT_KEEP
		get_window().content_scale_size=capture_target_size*ssaa
	elif ssaa>1 and (shot!="" or capture_dir!=""):
		capture_target_size=Vector2i(1600,900)
		get_window().content_scale_mode=Window.CONTENT_SCALE_MODE_VIEWPORT
		get_window().content_scale_aspect=Window.CONTENT_SCALE_ASPECT_KEEP
		get_window().content_scale_size=capture_target_size*ssaa
	return ssaa

func record_frame() -> void:
	await RenderingServer.frame_post_draw
	warmup_frames+=1
	if warmup_frames<12: return
	# quit() lands at the end of the frame: a coroutine resumed after it must
	# not write a frame past the count (it would repeat the next chunk's first)
	var count := roundi(capture_seconds*capture_fps/capture_speed)
	if shot=="" and frame>=count: return
	var img := get_viewport().get_texture().get_image()
	if shot=="" and capture_dir.ends_with(".mp4"):
		if capture_tcp==null and not _open_ffmpeg_stream(img.get_size()):
			get_tree().quit(1); return
		if img.get_format()!=Image.FORMAT_RGB8:
			img.convert(Image.FORMAT_RGB8)
		if capture_tcp.put_data(img.get_data())!=OK:
			push_error("ffmpeg stream write failed on frame %d" % frame)
			_close_ffmpeg_stream(); get_tree().quit(1); return
		frame+=1
		if frame>=count:
			if not _close_ffmpeg_stream():
				get_tree().quit(1); return
			get_tree().quit()
		return
	var path := shot if shot!="" else capture_dir.path_join("%05d.png" % frame)
	if capture_target_size!=Vector2i.ZERO and img.get_size()!=capture_target_size:
		img.resize(capture_target_size.x,capture_target_size.y,Image.INTERPOLATE_LANCZOS)
	img.save_png(path)
	frame+=1
	if shot!="" or frame>=count: get_tree().quit()

func _open_ffmpeg_stream(in_size: Vector2i) -> bool:
	capture_srv=TCPServer.new()
	if capture_srv.listen(0,"127.0.0.1")!=OK:
		push_error("ffmpeg TCPServer listen failed"); return false
	var port := capture_srv.get_local_port()
	var out_size := capture_target_size if capture_target_size!=Vector2i.ZERO else in_size
	var args := PackedStringArray([
		"-hide_banner","-loglevel","error","-y",
		"-f","rawvideo","-pix_fmt","rgb24",
		"-s","%dx%d" % [in_size.x,in_size.y],
		"-r",str(capture_fps),
		"-i","tcp://127.0.0.1:%d" % port,
	])
	if out_size!=in_size:
		args.append_array(PackedStringArray(["-vf","scale=%d:%d:flags=lanczos" % [out_size.x,out_size.y]]))
	var out_path := ProjectSettings.globalize_path(capture_dir) if capture_dir.begins_with("res://") else capture_dir
	args.append_array(PackedStringArray([
		"-c:v","libx264",
		"-preset",option("preset","medium"),
		"-crf",option("crf","18"),
		"-pix_fmt","yuv420p",
		"-movflags","+faststart",
		out_path,
	]))
	capture_pid=OS.create_process("ffmpeg",args)
	if capture_pid<=0:
		push_error("failed to launch ffmpeg"); capture_srv.stop(); capture_srv=null; return false
	var t0 := Time.get_ticks_msec()
	while capture_tcp==null and Time.get_ticks_msec()-t0<10000:
		if capture_srv.is_connection_available():
			capture_tcp=capture_srv.take_connection()
		else:
			OS.delay_msec(2)
	if capture_tcp==null:
		push_error("ffmpeg did not connect to local stream"); capture_srv.stop(); capture_srv=null; return false
	capture_tcp.set_no_delay(true)
	return true

func _close_ffmpeg_stream() -> bool:
	if capture_tcp!=null:
		capture_tcp.disconnect_from_host(); capture_tcp=null
	if capture_srv!=null:
		capture_srv.stop(); capture_srv=null
	if capture_pid>0:
		while OS.is_process_running(capture_pid):
			OS.delay_msec(5)
		var code := OS.get_process_exit_code(capture_pid)
		capture_pid=-1
		if code!=0:
			push_error("ffmpeg exited with code %d" % code); return false
	return true
