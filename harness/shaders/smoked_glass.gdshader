shader_type spatial;
render_mode blend_mix, depth_prepass_alpha, cull_back, diffuse_burley, specular_schlick_ggx;

uniform sampler2D cords : filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D punches : filter_linear_mipmap_anisotropic, repeat_disable;
uniform vec3 centre;
uniform vec3 span = vec3(1.);
uniform float pitch = 74.;
uniform vec4 tint : source_color = vec4(.35,.65,.54,1.);
varying vec3 shell;
varying vec3 spindle;

void vertex() {
    shell=(VERTEX-centre)/span;
    spindle=normalize(mat3(MODELVIEW_MATRIX)*vec3(0.,1.,0.));
}

void fragment() {
    float az=atan(shell.z,shell.x)/TAU;
    float h=shell.y+.5;
    vec2 uv=vec2(az+pitch*.153,1.-h);
    vec4 relief=texture(cords,uv);
    float rim=1.-smoothstep(.016,.036,h);
    float belt=(1.-smoothstep(.003,.009,abs(h-.102)))+.7*(1.-smoothstep(.003,.009,abs(h-.133)));
    // One frosted impression on the audience side, above the wheel cuts.
    vec2 die=vec2(.5-(az-.25)*3.2,(.72-h)/.20);
    float inside=step(.16,die.x)*step(die.x,.84)*step(0.,die.y)*step(die.y,1.);
    die.x=(die.x-.16)/.68;
    vec2 cell=vec2(mod(pitch,8.),floor(pitch/8.));
    float etch=texture(punches,(cell+clamp(die,.001,.999))/vec2(8.,16.)).r*inside;
    vec3 n=normalize(NORMAL);
    vec3 t=cross(spindle,n);
    vec3 b=cross(n,t);
    n=normalize(n+(t*(relief.r-.5)+b*(relief.g-.5))*.66);
    float edge=pow(1.-clamp(dot(n,normalize(VIEW)),0.,1.),2.2);
    float seed=relief.a;
    float ground=clamp(etch+.62*rim+.36*belt+.27*seed,0.,1.);
    vec3 body=mix(tint.rgb*.60,tint.rgb*1.18,relief.b);
    ALBEDO=mix(body,vec3(.63,.75,.67),ground*.86);
    // Long reflections off the workshop windows bend across the lap marks.
    vec3 ray=normalize(mat3(INV_VIEW_MATRIX)*reflect(-normalize(VIEW),n));
    float strip=exp(-pow((ray.x+.57*ray.z-.28)*9.,2.))*smoothstep(-.25,.4,ray.y);
    float glint=strip*(.085+.29*edge)*(1.-ground*.68);
    EMISSION=vec3(.78,.90,.83)*glint;
    METALLIC=.035;
    SPECULAR=.78;
    ROUGHNESS=.082+.18*ground+.039*(1.-relief.b);
    ALPHA=clamp(.31+.45*edge+.29*ground+.08*(1.-relief.b),0.,.90);
    NORMAL=n;
}
