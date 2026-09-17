shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx, cull_disabled;
// A vibrating wire. The mesh is a straight tube along +Y (UV.x = node fraction,
// UV.y = angle fraction). `disp` bends it by the baked finite-difference frame
// (24 nodes, metres, along local Z — the pluck direction); `envelope` widens
// a translucent sheath to the recent peak excursion, the blur the eye sees.
const int NODES = 24;
uniform float disp[24];
uniform float envelope[24];
uniform float radius = .004;
uniform bool sheath = false;
uniform vec4 albedo : source_color = vec4(.78,.8,.82,1);
uniform float metallic = .75;
uniform float roughness = .28;
// A harp is strung by register: wound wire in the bass, gut through the middle,
// nylon at the top. 0 = plain steel wire, 1 = wound wire (a helical winding that
// catches the light as the wire turns), 2 = gut (twisted strands, a translucent
// solid that lets light through from behind), 3 = nylon (clear, glossy).
uniform int family = 0;
uniform float wind_pitch = 900.0;  // turns per metre of the winding
uniform float strand_pitch = 45.0; // turns per metre of the gut's twist
uniform float length_m = 3.0;
uniform float excitation = 0.0;   // 0 silent .. 1 full pluck: the wire glows with its energy
uniform vec4 glow : source_color = vec4(1.0, .86, .62, 1.0);
// A plucked wire never stays in one plane: the pick's release and the wire's own
// stiffness turn the motion into a slowly precessing ellipse. `cross` is the
// minor axis as a fraction of the major one, so the bend and the blur read
// from a camera in front of the string plane too, not only edge-on.
uniform float cross_axis = .35;
varying float v_env;
varying float v_theta;

float node_value(float u, bool env) {
    float k = clamp(u, 0.0, 1.0) * float(NODES - 1);
    int i = int(floor(k)); int j = min(i + 1, NODES - 1); float f = k - float(i);
    int i0 = max(i - 1, 0); int j1 = min(j + 1, NODES - 1);
    float p0, p1, p2, p3;
    if (env) { p0 = envelope[i0]; p1 = envelope[i]; p2 = envelope[j]; p3 = envelope[j1]; }
    else     { p0 = disp[i0];     p1 = disp[i];     p2 = disp[j];     p3 = disp[j1]; }
    // Catmull-Rom between nodes: the FD frame is smooth, the tube should be too.
    return 0.5 * ((2.0 * p1) + (-p0 + p2) * f + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * f * f + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * f * f * f);
}

void vertex() {
    float u = UV.x;
    float d = node_value(u, false);
    float du = (node_value(u + .01, false) - node_value(u - .01, false)) / (.02 * length_m); // dz/dy
    float theta = UV.y * 6.2831853;
    v_theta = theta;
    if (sheath) {
        float e = node_value(u, true);
        v_env = e;
        // elliptical lens: wide along Z (the pluck), the minor axis across X
        VERTEX.x = cos(theta) * (radius * 1.15 + e * cross_axis);
        VERTEX.z = sin(theta) * (radius + e);
    } else {
        v_env = 0.0;
    }
    VERTEX.z += d;
    VERTEX.x += d * cross_axis;
    // tilt the ring normal with the local slope of the bent wire
    vec3 n = NORMAL;
    NORMAL = normalize(vec3(n.x - du * cross_axis * n.y, n.y - du * n.z, n.z));
}

void fragment() {
    if (sheath) {
        // denser near the turning points (a sinusoid dwells there), soft in the middle
        float edge = abs(sin(v_theta));
        float a = smoothstep(.0008, .004, v_env) * (.14 + .34 * edge * edge);
        ALBEDO = albedo.rgb;
        ALPHA = a;
        METALLIC = 0.0; ROUGHNESS = .6; SPECULAR = .2;
        EMISSION = glow.rgb * mix(vec3(1.0), albedo.rgb, .5) * excitation * .8;
    } else {
        float tone = 1.0;
        float rough = roughness;
        float metal = metallic;
        float spec = .7;
        vec3 back = vec3(0.0);
        float rim = 0.0;
        if (family == 1) {
            // helical winding: fine periodic ridges catch the light as the wire turns
            float turns = UV.x * length_m * wind_pitch + UV.y;
            float ridge = .5 + .5 * cos(turns * 6.2831853);
            tone = .82 + .18 * ridge;
            rough = roughness + .08 * (1.0 - ridge);
        } else if (family == 2) {
            // gut: a slow helical grain from the twisted strands, matte, and
            // translucent enough that a string against the light glows at its edges
            float grain = .5 + .5 * cos((UV.x * length_m * strand_pitch + 2.0 * UV.y) * 6.2831853);
            tone = .92 + .08 * grain;
            rough = .52 + .06 * grain;
            metal = 0.0; spec = .35;
            back = albedo.rgb * .45; rim = .35;
        } else if (family == 3) {
            // nylon: clear and glossy, most of the light passes through
            rough = .20; metal = 0.0; spec = .5;
            back = albedo.rgb * .65; rim = .55;
        }
        // A thin wire in a dark studio would vanish as pure metal: keep a little
        // diffuse body so it reads, and let a sounding string light itself.
        ALBEDO = albedo.rgb * tone;
        METALLIC = metal * (1.0 - .35 * excitation);
        ROUGHNESS = rough;
        SPECULAR = spec;
        BACKLIGHT = back;
        RIM = rim; RIM_TINT = .7;
        // tinted by the wire's own colour so a red C stays red when it sings
        EMISSION = glow.rgb * mix(vec3(1.0), albedo.rgb, .65) * (excitation * excitation) * 1.1 + albedo.rgb * .06;
    }
}
