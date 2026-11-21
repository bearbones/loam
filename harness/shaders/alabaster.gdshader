shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx;

// Calcite bands cut through the carved profiles in three dimensions. Two
// scales of the existing low-frequency patina field break up the deposits.
uniform sampler2D mineral_map : filter_linear_mipmap, repeat_enable;
uniform vec4 ivory : source_color = vec4(.90,.88,.80,1.0);
uniform vec4 body : source_color = vec4(.58,.64,.62,1.0);
uniform vec4 vein : source_color = vec4(.60,.45,.29,1.0);
varying vec3 stone;

void vertex() {
	stone = VERTEX;
}

void fragment() {
	vec2 cut = vec2(stone.x+.38*stone.z, stone.y-.31*stone.z);
	float cloud = texture(mineral_map, cut*.16).r - .5;
	float fleck = texture(mineral_map, cut*.79 + .31).r - .5;
	float layer = dot(stone, vec3(.86,.51,.43)) * 3.3
			+ .23*sin(dot(stone, vec3(2.1,-1.2,1.5))) + cloud*2.6 + fleck*.26;
	float dist = abs(fract(layer)-.5);
	float aa = min(fwidth(layer), .5);
	float seam = 1.0 - smoothstep(.008, .030+aa, dist);
	float bloom = exp(-8.0*dist);
	vec3 color = mix(body.rgb, ivory.rgb, clamp(.73+cloud*1.9+fleck*.55-bloom*.24,0.,1.));
	ALBEDO = mix(color, vein.rgb, seam*.46*(1.0-smoothstep(.05,.45,aa)));
	ROUGHNESS = clamp(.32 + bloom*.06 + fleck*.18, .26, .44);
	SPECULAR = .44;
	BACKLIGHT = ivory.rgb*.10;
}
