shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx;
// Object coordinates keep the texture attached to animated rigid links.
uniform sampler2D grain_map : filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D metal_map : filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D fibre_map : filter_linear_mipmap_anisotropic, repeat_enable;
uniform vec4 dark_color : source_color = vec4(.12,.05,.025,1);
uniform vec4 light_color : source_color = vec4(.3,.15,.07,1);
uniform int finish_kind = 0; // 0 walnut, 1 brass, 2 steel, 3 felt, 4 enamel, 5 floor
uniform int grain_axis = 0;
uniform bool use_sweep_uv = false;
uniform float texture_scale = 1.0;
uniform float seed_offset = 0.0;
uniform float base_roughness = .38;
uniform float relief = .0007;
varying vec3 object_position;
varying vec3 object_normal;
void vertex() { object_position=VERTEX; object_normal=NORMAL; }
void fragment() {
    vec3 p=object_position*texture_scale;
    vec3 n=normalize(object_normal);
    if (grain_axis==1) { p=p.yxz; n=n.yxz; }
    if (grain_axis==2) { p=p.zyx; n=n.zyx; }
    p+=vec3(seed_offset,seed_offset*.31,seed_offset*.73);
    float height=0.0;
    if (finish_kind==0) {
        vec2 uv=use_sweep_uv ? vec2(UV.x*.44,UV.y*1.8) : vec2(p.x*.44,(p.y+p.z)*1.8);
        vec3 grain=texture(grain_map,uv).rgb;
        float tone=clamp(grain.r*.9-grain.g*.28,.03,.96);
        float rings=.48+.15*sin(length(p.yz)*120.0+grain.r*3.0);
        tone=mix(tone,rings,(use_sweep_uv ? 0.0 : pow(abs(n.x),8.0)*.85));
        ALBEDO=mix(dark_color.rgb,light_color.rgb,tone);
        ROUGHNESS=clamp(base_roughness+(grain.b-.5)*.15+grain.g*.15,.24,.65);
        METALLIC=0.0;
        SPECULAR=.32;
        height=grain.r*.16-grain.g*.3;
    } else if (finish_kind==1 || finish_kind==2) {
        vec3 pat=texture(metal_map,vec2(p.x+p.z,p.y+p.z)*1.8).rgb;
        vec3 brush=texture(metal_map,vec2(p.x*.6,p.y+p.z)*7.0).rgb;
        float age=smoothstep(.47,.78,pat.r);
        ALBEDO=mix(light_color.rgb,dark_color.rgb,age*.12);
        ROUGHNESS=clamp(base_roughness+age*.08+(brush.g-.5)*.1,.19,.57);
        METALLIC=finish_kind==1 ? .88-age*.06 : .93;
        SPECULAR=.5;
        height=(brush.g-.5)*.25+(pat.b-.5)*.12;
    } else if (finish_kind==3) {
        vec3 fibre=texture(fibre_map,vec2(p.x+p.z,p.y)*22.0).rgb;
        ALBEDO=mix(dark_color.rgb,light_color.rgb,fibre.r*.6+.2);
        ROUGHNESS=.95;
        METALLIC=0.0;
        SPECULAR=.15;
        RIM=.22;
        RIM_TINT=.8;
        height=fibre.r*.35;
    } else {
        vec3 grit=texture(metal_map,vec2(p.x+p.y,p.z+p.y)*3.0).rgb;
        ALBEDO=mix(dark_color.rgb,light_color.rgb,grit.r*.4+.3);
        METALLIC=finish_kind==4 ? .25 : 0.0;
        ROUGHNESS=base_roughness+(grit.b-.5)*.08;
        SPECULAR=.3;
        height=grit.b*.12;
    }
    // Surface-gradient bump: world-sized relief, no mesh displacement or UV seams.
    vec3 dx=dFdx(VERTEX), dy=dFdy(VERTEX);
    vec3 rx=cross(dy,NORMAL), ry=cross(NORMAL,dx);
    float det=dot(dx,rx);
    vec3 gradient=sign(det)*(dFdx(height)*rx+dFdy(height)*ry);
    NORMAL=normalize(max(abs(det),.00000001)*NORMAL-relief*gradient);
}
