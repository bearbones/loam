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
uniform float metallic = .9;
uniform float roughness = .28;
uniform float wound = 0.0;        // 1 = bronze-wound bass string
uniform float wind_pitch = 900.0; // turns per metre of the winding
uniform float length_m = 3.0;
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
        // flat lens in the vibration plane: thin across X, wide along Z
        VERTEX.x = cos(theta) * radius * 1.15;
        VERTEX.z = sin(theta) * (radius + e);
    } else {
        v_env = 0.0;
    }
    VERTEX.z += d;
    // tilt the ring normal with the local slope of the bent wire
    vec3 n = NORMAL;
    NORMAL = normalize(vec3(n.x, n.y - du * n.z, n.z));
}

void fragment() {
    if (sheath) {
        // denser near the turning points (a sinusoid dwells there), soft in the middle
        float edge = abs(sin(v_theta));
        float a = smoothstep(.0008, .004, v_env) * (.10 + .30 * edge * edge);
        ALBEDO = albedo.rgb;
        ALPHA = a;
        METALLIC = 0.0; ROUGHNESS = .6; SPECULAR = .2;
    } else {
        float tone = 1.0;
        float rough = roughness;
        if (wound > 0.5) {
            // helical winding: fine periodic ridges catch the light as the wire turns
            float turns = UV.x * length_m * wind_pitch + UV.y;
            float ridge = .5 + .5 * cos(turns * 6.2831853);
            tone = .82 + .18 * ridge;
            rough = roughness + .08 * (1.0 - ridge);
        }
        ALBEDO = albedo.rgb * tone;
        METALLIC = metallic;
        ROUGHNESS = rough;
        SPECULAR = .6;
    }
}
