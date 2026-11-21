shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx;

// A continuous floor, cove and circular wall. UV.x counts architectural bays
// around the room. The floor inlay and the panel mouldings are metre-scaled.
uniform sampler2D stone_map : filter_linear_mipmap, repeat_enable;
uniform vec4 slate : source_color = vec4(.065, .095, .115, 1.0);
uniform vec4 petrol : source_color = vec4(.10, .21, .23, 1.0);
uniform vec4 bronze : source_color = vec4(.54, .38, .20, 1.0);
varying vec3 room;

void vertex() {
	room = VERTEX;
}

float line_mask(float distance_m, float width_m) {
	float aa = max(fwidth(distance_m), .001);
	return 1.0 - smoothstep(max(width_m-aa*.5, 0.0), width_m+aa*.5, abs(distance_m));
}

void fragment() {
	float radius = length(room.xz);
	float wall = smoothstep(17.25, 17.95, radius);
	float x = (fract(UV.x)-.5) * 5.14;
	float y = room.y;
	// Rounded arch above a vertical dado, with a recessed inner panel and
	// a second narrow bead catching the light around its spring line.
	float arch = length(vec2(x, max(y-2.5, 0.0))) - 2.10;
	float recess = (1.0-smoothstep(-.16, .04, arch)) * smoothstep(.35, .65, y);
	float flute = .5+.5*cos(x*34.0);
	float fluting = flute * (1.0-smoothstep(.25, 1.8, fwidth(x)*34.0));
	float lamp = exp(-.52*x*x) * exp(-.38*max(y-.7, 0.0));
	float arch_trim = (.55*line_mask(arch, .032) + .28*line_mask(arch-.13, .016))
			* smoothstep(.32, .60, y);
	// Two fine concentric brass courses mark the edge of the instrument dais.
	float rings = line_mask(radius-7.55, .012) + .65*line_mask(radius-7.72, .009);
	float band = smoothstep(7.54,7.57,radius)*(1.0-smoothstep(7.70,7.73,radius));
	float joints = line_mask(sin(UV.x*3.141593)*2.0, .008) * band;
	float pool = exp(-.013*dot(room.xz-vec2(-4.,-5.), room.xz-vec2(-4.,-5.)));
	float mineral = texture(stone_map, room.xz*.13).r-.5;
	vec3 floor_color = mix(slate.rgb*.62, petrol.rgb, .08+.24*pool) * (1.0+mineral*.85);
	vec3 panel = mix(slate.rgb, petrol.rgb, .35+.45*lamp);
	panel *= 1.0-recess*(.24+.18*fluting);
	// Shallow pilasters share each bay boundary. A hooded bronze sconce
	// throws light up the flutes and a shorter pool onto the dado below.
	float column_x = 2.57-abs(x);
	float column = 1.0-smoothstep(.16,.28,column_x);
	float reveal = 1.0-smoothstep(.025,.09,abs(column_x-.22));
	panel *= (1.0+.28*column-.38*reveal);
	float baseboard = 1.0-smoothstep(.18,.26,y);
	panel = mix(panel, slate.rgb*.65, baseboard);
	float lamp_h = y-2.25;
	float housing = (1.0-smoothstep(.095,.14,column_x))*(1.0-smoothstep(.31,.35,abs(lamp_h)));
	float lens = (1.0-smoothstep(.047,.069,column_x))*(1.0-smoothstep(.20,.25,abs(lamp_h)));
	float wash = exp(-abs(lamp_h)*1.45-column_x*column_x/(.035+.13*abs(lamp_h)));
	float trim = mix(clamp(.58*rings+.3*joints,0.0,1.0), max(arch_trim, housing*.82), wall);
	ALBEDO = mix(mix(floor_color, panel, wall), bronze.rgb, trim);
	METALLIC = mix(.025,.62,trim);
	ROUGHNESS = mix(.86,.36,trim);
	SPECULAR = mix(.12,.46,wall);
	// Low, indirect amber light washes up each bay from the skirting.
	EMISSION = wall * (petrol.rgb*(.22+.5*recess) + bronze.rgb*(lamp*.13+wash*.66) + vec3(1.0,.66,.32)*lens*1.45);
}
