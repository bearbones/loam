shader_type sky;
// Invisible studio softboxes provide readable broad reflections in small metal parts.
float panel(vec3 d,vec3 aim,float width,float height) {
    vec3 right=normalize(cross(aim,vec3(0.0,1.0,0.0)));
    vec3 up=cross(right,aim);
    float forward=max(dot(d,aim),.001);
    vec2 uv=vec2(dot(d,right),dot(d,up))/forward;
    return (1.0-smoothstep(width,width+.06,abs(uv.x))) *
           (1.0-smoothstep(height,height+.06,abs(uv.y))) * step(.01,dot(d,aim));
}
void sky() {
    vec3 d=normalize(EYEDIR);
    if (AT_CUBEMAP_PASS) {
        COLOR=mix(vec3(.035,.047,.053),vec3(.18,.22,.25),smoothstep(-.2,.7,d.y));
        COLOR+=vec3(2.8,2.55,2.15)*panel(d,normalize(vec3(-.6,.85,.5)),.4,.5);
        COLOR+=vec3(1.0,1.4,1.75)*panel(d,normalize(vec3(.8,.4,.3)),.12,.65);
        COLOR+=vec3(2.0,1.55,.92)*panel(d,normalize(vec3(.2,.65,-.85)),.65,.16);
    } else {
        COLOR=mix(vec3(.035,.048,.053),vec3(.009,.015,.022),smoothstep(-.2,.8,d.y));
    }
}
