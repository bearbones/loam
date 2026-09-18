class_name ClockworkLook
extends RefCounted
## Shared material palette; applied after GLB import so rebuilding geometry preserves the look.
const SURFACE = preload("res://shaders/craft_surface.gdshader")
const GLASS = preload("res://shaders/smoked_glass.gdshader")
const SKY_SHADER = preload("res://shaders/studio_sky.gdshader")
var cache: Dictionary = {}
var grain: Texture2D
var metal: Texture2D
var fibre: Texture2D
var lamp_material: StandardMaterial3D
var counts: Dictionary = {}

func surface(kind: int, dark: String, light: String, rough: float, axis := 0, variant := 0) -> ShaderMaterial:
	var key := "%d/%s/%s/%s/%d/%d" % [kind,dark,light,rough,axis,variant]
	if cache.has(key): return cache[key]
	var m := ShaderMaterial.new(); m.shader=SURFACE
	m.set_shader_parameter("grain_map",grain)
	m.set_shader_parameter("metal_map",metal)
	m.set_shader_parameter("fibre_map",fibre)
	m.set_shader_parameter("finish_kind",kind)
	m.set_shader_parameter("dark_color",Color(dark))
	m.set_shader_parameter("light_color",Color(light))
	m.set_shader_parameter("base_roughness",rough)
	m.set_shader_parameter("grain_axis",axis)
	m.set_shader_parameter("seed_offset",variant*.173)
	m.set_shader_parameter("relief",.0002 if kind==0 else .000008)
	cache[key]=m
	return m

func apply(model: Node3D) -> void:
	grain=load("res://assets/textures/walnut_data.png")
	metal=load("res://assets/textures/metal_data.png")
	fibre=load("res://assets/textures/felt_data.png")
	var glass := ShaderMaterial.new(); glass.shader=GLASS; glass.set_shader_parameter("tint",Color("709f88"))
	lamp_material=StandardMaterial3D.new()
	lamp_material.albedo_color=Color("d0aa65"); lamp_material.roughness=.22
	lamp_material.emission_enabled=true; lamp_material.emission=Color("f4ae51")
	lamp_material.emission_energy_multiplier=.4
	for node in model.find_children("*","MeshInstance3D",true,false):
		var mesh_node: MeshInstance3D=node
		for index in mesh_node.mesh.get_surface_count():
			var original: Material=mesh_node.mesh.surface_get_material(index)
			if original==null: continue
			var title := original.resource_name.to_lower()
			var label := String(mesh_node.name).to_lower()
			var variant := int(String(mesh_node.name).hash()%7)
			var replacement: Material
			if title.contains("walnut") or title.contains("rosewood"):
				var axis := 0
				if label.contains("leg") or label.contains("bridge"): axis=1
				replacement=surface(0,"28150d","68472b",.38,axis,variant)
				if title.contains("rosewood"): replacement=surface(0,"2b100b","7b452a",.33,2,variant)
			elif title.contains("spruce"):
				replacement=surface(0,"957344","dcc396",.42,0,variant)
			elif title.contains("brass"):
				replacement=surface(1,"998354","c9b585",.34,0,variant)
			elif title.contains("steel") or title.contains("silver"):
				replacement=surface(2,"202f37","627681",.27,1,variant)
			elif title.contains("felt"):
				replacement=surface(3,"9b917b","e5dac4",.94,0,variant)
			elif title.contains("horn"):   # a plectrum blade: dark amber, streaked along its length
				replacement=surface(0,"3a1f08","b47a34",.40,1,variant)
			elif title.contains("glass"):
				replacement=lamp_material if label=="chamber__lamp" else glass
			elif title.contains("enamel"):
				replacement=surface(4,"121b1e","2c393b",.39)
			else:
				push_warning("No craft finish for imported material "+title); continue
			if label.begins_with("form_") and replacement is ShaderMaterial:
				replacement=replacement.duplicate()
				replacement.set_shader_parameter("use_sweep_uv",true)
			mesh_node.set_surface_override_material(index,replacement)
			counts[title]=int(counts.get(title,0))+1
	print("CRAFT MATERIALS: ",counts,"; ",cache.size()," shared variants")

func light_rig(parent: Node3D) -> void:
	var world := WorldEnvironment.new()
	var env := Environment.new(); world.environment=env
	var sky := Sky.new(); var mat := ShaderMaterial.new(); mat.shader=SKY_SHADER
	sky.sky_material=mat; sky.radiance_size=Sky.RADIANCE_SIZE_256; sky.process_mode=Sky.PROCESS_MODE_QUALITY
	env.sky=sky; env.background_mode=Environment.BG_COLOR; env.background_color=Color("1b2529")
	env.ambient_light_source=Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_sky_contribution=.65
	env.ambient_light_color=Color("a1b6c4"); env.ambient_light_energy=.35
	env.reflected_light_source=Environment.REFLECTION_SOURCE_SKY
	env.tonemap_mode=Environment.TONE_MAPPER_FILMIC; env.tonemap_exposure=1.0; env.tonemap_white=5.0
	env.fog_enabled=true; env.fog_density=.016; env.fog_light_color=Color("1b2529"); env.fog_light_energy=1.0
	env.ssao_enabled=true; env.ssao_radius=.28; env.ssao_intensity=1.4; env.ssao_detail=.5
	parent.add_child(world)
	var key := DirectionalLight3D.new(); key.name="Warm large key"
	key.rotation_degrees=Vector3(-48,-32,0); key.light_color=Color("fff0d8"); key.light_energy=1.3
	key.light_angular_distance=1.5; key.shadow_enabled=true; key.shadow_bias=.035; key.shadow_normal_bias=.8
	key.shadow_blur=2.0; key.shadow_opacity=.88; key.directional_shadow_blend_splits=true
	key.directional_shadow_max_distance=32; parent.add_child(key)
	var fill := OmniLight3D.new(); fill.name="Cool soft fill"; fill.position=Vector3(-5,4,5)
	fill.omni_range=18; fill.light_color=Color("afcde8"); fill.light_energy=1.2; parent.add_child(fill)
	var rim := OmniLight3D.new(); rim.name="Amber rim"; rim.position=Vector3(2,5,-4)
	rim.omni_range=15; rim.light_color=Color("ffd7a0"); rim.light_energy=2.0; parent.add_child(rim)
	var floor := MeshInstance3D.new(); floor.name="Studio floor"
	floor.mesh=cyclorama();
	floor.position.y=-.565; floor.material_override=surface(5,"0b1216","151f24",.9)
	parent.add_child(floor)
	parent.get_viewport().msaa_3d=Viewport.MSAA_4X

func breathe(value: float) -> void:
	if lamp_material!=null: lamp_material.emission_energy_multiplier= .08+minf(value*2.0,.6)

func cyclorama() -> ArrayMesh:
	# A continuous floor-to-wall curve removes the distracting ground-plane horizon.
	var rows: Array=[Vector3(0,0,60),Vector3(0,0,-12)]
	var normals: Array=[Vector3.UP,Vector3.UP]
	for i in range(1,25):
		var angle := i*PI/48.0
		rows.append(Vector3(0,7*(1-cos(angle)),-12-7*sin(angle)))
		normals.append(Vector3(0,cos(angle),sin(angle)))
	rows.append(Vector3(0,60,-19)); normals.append(Vector3.BACK)
	var vertices := PackedVector3Array(); var ns := PackedVector3Array(); var indices := PackedInt32Array()
	for i in rows.size():
		vertices.append(rows[i]+Vector3(-60,0,0)); vertices.append(rows[i]+Vector3(60,0,0))
		ns.append(normals[i]); ns.append(normals[i])
		if i<rows.size()-1:
			var k := i*2
			indices.append_array(PackedInt32Array([k,k+3,k+1,k,k+2,k+3]))
	var arrays: Array=[]; arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX]=vertices; arrays[Mesh.ARRAY_NORMAL]=ns; arrays[Mesh.ARRAY_INDEX]=indices
	var mesh := ArrayMesh.new(); mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	return mesh
