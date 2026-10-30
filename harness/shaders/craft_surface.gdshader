shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx;

// Object coordinates keep the texture attached to animated rigid links.
uniform sampler2D grain_map : filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D wood_normal_map : filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D wood_depth_map : filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D metal_map : filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D metal_normal_map : filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D metal_depth_map : filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D fibre_map : filter_linear_mipmap_anisotropic, repeat_enable;

uniform vec4 dark_color : source_color = vec4(.12, .05, .025, 1.0);
uniform vec4 light_color : source_color = vec4(.30, .15, .07, 1.0);
uniform int finish_kind = 0; // 0 lacquered grooved wood, 1 brushed brass/bronze, 2 brushed steel, 3 felt, 4 enamel, 5 floor
uniform int grain_axis = 0;
uniform bool use_sweep_uv = false;
uniform float texture_scale = 1.0;
uniform float seed_offset = 0.0;
uniform float base_roughness = .38;
uniform float relief = .0002;
uniform float normal_strength = 1.0;
uniform float depth_scale = .012;
uniform float clearcoat = .85;
uniform float clearcoat_roughness = .08;
uniform float groove_depth = 1.0;
uniform float anisotropy = .75;

varying vec3 object_position;
varying vec3 object_normal;
varying vec3 v_tangent_vs;
varying vec3 v_binormal_vs;

void vertex() {
    object_position = VERTEX;
    object_normal = NORMAL;

    // Build an object-space tangent aligned with the grain/brush axis (+U),
    // or use the authored sweep tangent on curved profiled forms.
    vec3 axis_u = vec3(1.0, 0.0, 0.0);
    vec3 axis_v = normalize(vec3(0.0, 1.0, 1.0));
    if (grain_axis == 1) {
        axis_u = vec3(0.0, 1.0, 0.0);
        axis_v = normalize(vec3(1.0, 0.0, 1.0));
    } else if (grain_axis == 2) {
        axis_u = vec3(0.0, 0.0, 1.0);
        axis_v = normalize(vec3(1.0, 1.0, 0.0));
    }
    if (use_sweep_uv && dot(TANGENT, TANGENT) > 0.25) {
        axis_u = normalize(TANGENT);
    }
    vec3 n_obj = normalize(NORMAL);
    vec3 t_obj = axis_u - n_obj * dot(n_obj, axis_u);
    if (dot(t_obj, t_obj) < 1e-4) {
        t_obj = axis_v - n_obj * dot(n_obj, axis_v);
    }
    t_obj = normalize(t_obj);
    vec3 b_obj = cross(n_obj, t_obj);

    v_tangent_vs = (MODELVIEW_MATRIX * vec4(t_obj, 0.0)).xyz;
    v_binormal_vs = (MODELVIEW_MATRIX * vec4(b_obj, 0.0)).xyz;
}

// Parallax Occlusion Mapping (POM) with linear search + secant contact refinement.
vec2 pom_wood(vec2 uv, vec3 view_ts, float scale, vec2 ddx, vec2 ddy) {
    if (scale <= 0.00001) return uv;
    // Refract view ray through the clear lacquer coat (IOR ~ 1.49).
    vec2 step_uv = (view_ts.xy / (max(view_ts.z, 0.22) * 1.49)) * scale / 6.0;
    vec2 curr_uv = uv;
    float prev_layer = 0.0;
    float prev_depth = 1.0 - textureGrad(wood_depth_map, curr_uv, ddx, ddy).r;
    for (int i = 1; i <= 6; i++) {
        float layer = float(i) / 6.0;
        vec2 next_uv = uv - step_uv * float(i);
        float d = 1.0 - textureGrad(wood_depth_map, next_uv, ddx, ddy).r;
        if (layer >= d) {
            float d_curr = d - layer;
            float d_prev = prev_depth - prev_layer;
            float w = clamp(d_curr / max(abs(d_curr - d_prev), 1e-5), 0.0, 1.0);
            return mix(next_uv, curr_uv, w);
        }
        curr_uv = next_uv;
        prev_layer = layer;
        prev_depth = d;
    }
    return curr_uv;
}

vec2 pom_metal(vec2 uv, vec3 view_ts, float scale, vec2 ddx, vec2 ddy) {
    if (scale <= 0.00001) return uv;
    vec2 step_uv = (view_ts.xy / max(view_ts.z, 0.24)) * scale / 5.0;
    vec2 curr_uv = uv;
    float prev_layer = 0.0;
    float prev_depth = 1.0 - textureGrad(metal_depth_map, curr_uv, ddx, ddy).r;
    for (int i = 1; i <= 5; i++) {
        float layer = float(i) / 5.0;
        vec2 next_uv = uv - step_uv * float(i);
        float d = 1.0 - textureGrad(metal_depth_map, next_uv, ddx, ddy).r;
        if (layer >= d) {
            float d_curr = d - layer;
            float d_prev = prev_depth - prev_layer;
            float w = clamp(d_curr / max(abs(d_curr - d_prev), 1e-5), 0.0, 1.0);
            return mix(next_uv, curr_uv, w);
        }
        curr_uv = next_uv;
        prev_layer = layer;
        prev_depth = d;
    }
    return curr_uv;
}

void fragment() {
    vec3 p = object_position * texture_scale;
    vec3 n = normalize(object_normal);
    if (grain_axis == 1) { p = p.yxz; n = n.yxz; }
    if (grain_axis == 2) { p = p.zyx; n = n.zyx; }
    p += vec3(seed_offset, seed_offset * .31, seed_offset * .73);

    // Orthonormal view-space tangent basis aligned with the grain/brush direction.
    vec3 N = normalize(NORMAL);
    vec3 T = v_tangent_vs - N * dot(N, v_tangent_vs);
    if (dot(T, T) < 1e-5) {
        T = normalize(cross(N, vec3(0.0, 1.0, 0.01)));
    } else {
        T = normalize(T);
    }
    vec3 B = normalize(cross(N, T));
    if (dot(B, v_binormal_vs) < 0.0) B = -B;
    TANGENT = T;
    BINORMAL = B;

    vec3 V = normalize(VIEW);
    float ndotv_geom = max(dot(V, N), 0.0);
    float grazing_fade = smoothstep(0.38, 0.75, ndotv_geom);
    vec3 view_ts = vec3(dot(V, T), dot(V, B), max(ndotv_geom, 0.35));

    vec3 mapped_normal = N;

    if (finish_kind == 0) {
        // --- Lacquered Grooved Wood ---
        float cross_v = p.y * abs(n.z) + p.z * abs(n.y) + (p.y * .78 - p.z * .62) * abs(n.x);
        vec2 base_uv = use_sweep_uv ? vec2(UV.x * .44, UV.y * 1.45) : vec2(p.x * .44, cross_v * 1.65);
        vec2 ddx = dFdx(base_uv);
        vec2 ddy = dFdy(base_uv);
        float uv_fw = max(length(ddx), length(ddy));
        float mip_fade = 1.0 - smoothstep(0.010, 0.065, uv_fw);

        float end_grain = use_sweep_uv ? 0.0 : smoothstep(0.55, 0.90, abs(n.x)) * .90;
        float eff_depth = depth_scale * 0.35 * groove_depth * (1.0 - end_grain * 0.88) * mip_fade * grazing_fade;
        vec2 uv = pom_wood(base_uv, view_ts, eff_depth, ddx, ddy);

        vec3 grain = textureGrad(grain_map, uv, ddx, ddy).rgb;
        vec3 w_depth = textureGrad(wood_depth_map, uv, ddx, ddy).rgb;
        vec3 w_norm = textureGrad(wood_normal_map, uv, ddx, ddy).rgb * 2.0 - 1.0;

        // Carved groove profile (w_depth.g) and subsurface chatoyancy along the wood fibres
        float side_mask = 1.0 - end_grain;
        float flute = (w_depth.g - .5) * 2.0 * groove_depth * side_mask * mip_fade;
        float chatoyant = .5 + .5 * sin(w_depth.g * 6.2831853 * mip_fade + dot(V, T) * 1.8) * mip_fade;
        float tone = clamp(grain.r * .88 - grain.g * .26 + flute * .09 + (chatoyant - .5) * .06 * side_mask, .03, .97);
        float ring_arg = length(p.yz) * 115.0 + grain.r * 2.8;
        float ring_fade = 1.0 - smoothstep(0.10, 0.35, fwidth(ring_arg));
        float rings = .46 + .16 * sin(ring_arg) * ring_fade;
        tone = mix(tone, rings, end_grain);

        vec3 wood_col = mix(dark_color.rgb, light_color.rgb, tone);

        // Beer-Lambert warm amber lacquer absorption inside deeper carved grooves & pores
        float sub_depth = mix(1.0 - w_depth.r, (0.5 - (rings - .46)) * .35, end_grain);
        float lacquer_path = clamp(sub_depth, 0.0, 1.0) * groove_depth / max(view_ts.z, .45);
        vec3 absorption = exp(-vec3(.14, .30, .56) * lacquer_path * .45 * clearcoat);
        float cavity_ao = mix(1.0, w_depth.b, .42 * groove_depth * side_mask * mip_fade);

        // Dual-layer clearcoat Fresnel response: glassy top coat over grooved wood substrate
        vec2 wn_xy = w_norm.xy * normal_strength * 0.72 * mip_fade * mix(.50, .85, groove_depth) * (1.0 - end_grain * .82);
        vec3 N_sub = normalize(T * wn_xy.x + B * wn_xy.y + N * max(w_norm.z, .45));
        vec3 N_coat = normalize(mix(N, N_sub, .10));

        float ndotv_coat = max(dot(N_coat, V), 0.0);
        float f_coat = (.04 + .96 * pow(1.0 - ndotv_coat, 5.0)) * clearcoat;

        ALBEDO = wood_col * absorption * mix(1.0, cavity_ao, .38);
        // Blend substrate roughness with the glossy clearcoat lobe at grazing/specular angles
        float sub_rough = clamp(base_roughness + (grain.b - .5) * .11 + grain.g * .12 - flute * .02, .24, .62);
        ROUGHNESS = mix(sub_rough, max(clearcoat_roughness, 0.11), clamp(f_coat * 1.35 + clearcoat * .22, 0.0, .75));
        METALLIC = 0.0;
        SPECULAR = mix(.36, .62, clearcoat);
        CLEARCOAT = clearcoat;
        CLEARCOAT_ROUGHNESS = max(clearcoat_roughness, 0.11);
        ANISOTROPY = .22 * side_mask;
        ANISOTROPY_FLOW = vec2(1.0, 0.0);
        AO = cavity_ao;
        AO_LIGHT_AFFECT = .55;

        mapped_normal = normalize(mix(N_sub, N_coat, clamp(f_coat * .72 + clearcoat * .22, 0.0, .80)));
    } else if (finish_kind == 1 || finish_kind == 2) {
        // --- Anisotropic Brushed Metallics (Brass, Bronze, Steel) ---
        float cross_m = p.y * abs(n.z) + p.z * abs(n.y) + (p.y + p.z) * .5 * abs(n.x);
        vec2 pat_uv = vec2(p.x + p.z, p.y + p.z) * 0.85;
        vec2 base_uv = vec2(p.x * .55, cross_m) * 6.5;
        vec2 ddx = dFdx(base_uv);
        vec2 ddy = dFdy(base_uv);
        float uv_fw = max(length(ddx), length(ddy));
        float mip_fade = 1.0 - smoothstep(0.012, 0.065, uv_fw);

        vec3 pat = texture(metal_map, pat_uv).rgb;
        vec3 brush = textureGrad(metal_map, base_uv, ddx, ddy).rgb;
        vec3 m_depth = textureGrad(metal_depth_map, base_uv, ddx, ddy).rgb;
        vec3 m_norm = textureGrad(metal_normal_map, base_uv, ddx, ddy).rgb * 2.0 - 1.0;

        // Gentle patina variation without blotchy contrast
        float age = smoothstep(.35, .85, pat.r) * 0.45;
        float groove_ao = mix(1.0, m_depth.b, .18 * mip_fade);

        // Anisotropic brush micro-ridge sheen across the bitangent
        float b_dot_v = dot(B, V);
        float aniso_band = sqrt(max(1.0 - b_dot_v * b_dot_v, 0.0));
        float brush_ridge = ((m_depth.r - .5) * .04 * mip_fade) + (aniso_band - .75) * .04 * anisotropy;

        ALBEDO = mix(light_color.rgb, dark_color.rgb, age * .10) * clamp(1.0 + brush_ridge, .95, 1.05);
        ROUGHNESS = clamp(base_roughness + age * .04 + (brush.g - .5) * .04 * mip_fade, .20, .54);
        METALLIC = finish_kind == 1 ? (.89 - age * .04) : .92;
        SPECULAR = .56;

        ANISOTROPY = anisotropy * 0.65;
        ANISOTROPY_FLOW = vec2(1.0, 0.0);
        AO = groove_ao;
        AO_LIGHT_AFFECT = .35;

        vec2 mn_xy = m_norm.xy * normal_strength * 0.22 * mip_fade;
        mapped_normal = normalize(T * mn_xy.x + B * mn_xy.y + N);
    } else if (finish_kind == 3) {
        // --- Pressed Wool Felt ---
        vec3 fibre = texture(fibre_map, vec2(p.x + p.z, p.y) * 22.0).rgb;
        ALBEDO = mix(dark_color.rgb, light_color.rgb, fibre.r * .6 + .2);
        ROUGHNESS = .95;
        METALLIC = 0.0;
        SPECULAR = .15;
        RIM = .22;
        RIM_TINT = .8;
    } else {
        // --- Stage Enamel & Studio Cyclorama ---
        vec3 grit = texture(metal_map, vec2(p.x + p.y, p.z + p.y) * 3.0).rgb;
        ALBEDO = mix(dark_color.rgb, light_color.rgb, grit.r * .4 + .3);
        METALLIC = finish_kind == 4 ? .25 : 0.0;
        ROUGHNESS = base_roughness + (grit.b - .5) * .06;
        SPECULAR = .3;
    }

    // Kaplanyan-Olano (2016) Specular Anti-Aliasing: filter roughness by sub-pixel normal variance
    // so curved moldings and normal-mapped grain reflect smoothly instead of beading into dots.
    vec3 dndu = dFdx(mapped_normal);
    vec3 dndv = dFdy(mapped_normal);
    float norm_var = clamp(dot(dndu, dndu) + dot(dndv, dndv), 0.0, 0.25);
    float kernel_r2 = min(2.2 * norm_var, 0.18);
    ROUGHNESS = clamp(sqrt(ROUGHNESS * ROUGHNESS + kernel_r2), 0.10, 1.0);
    if (finish_kind == 0) {
        CLEARCOAT_ROUGHNESS = clamp(sqrt(CLEARCOAT_ROUGHNESS * CLEARCOAT_ROUGHNESS + kernel_r2), 0.10, 1.0);
    }
    NORMAL = mapped_normal;
}
