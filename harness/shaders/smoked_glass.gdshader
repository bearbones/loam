shader_type spatial;
render_mode blend_mix, depth_prepass_alpha, cull_back, diffuse_burley, specular_schlick_ggx;
uniform vec4 tint : source_color = vec4(.22,.43,.36,1);
void fragment() {
    float facing=clamp(dot(normalize(NORMAL),normalize(VIEW)),0.0,1.0);
    float edge=pow(1.0-facing,3.0);
    ALBEDO=tint.rgb;
    METALLIC=.08;
    ROUGHNESS=.12;
    SPECULAR=.8;
    ALPHA=.3+edge*.58;
}
