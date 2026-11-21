shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx;

// Board coordinates are sawn with the part in Blender and stay with it in motion.
uniform sampler2D workshop : filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D punches : filter_linear_mipmap_anisotropic, repeat_disable;
uniform vec4 heartwood : source_color = vec4(.23,.12,.06,1.);
uniform vec4 sapwood : source_color = vec4(.58,.37,.20,1.);
uniform float ring_pitch = .0047;
uniform float oil = .64;
uniform float vessel = .75;
uniform vec3 centre;
uniform vec3 span = vec3(1.);
uniform float pitch = -1.;
uniform bool case_lid = false;
varying vec3 local_point;
varying vec3 local_normal;
varying vec3 board;
varying float board_id;

void vertex() {
	local_point = VERTEX;
	local_normal = NORMAL;
	board = vec3(UV.x,1.-UV.y,UV2.x);
	board_id = 1.-UV2.y;
}

void fragment() {
	float seed = fract(board_id*47.21);
	vec3 p = board;
	float x = p.x;
	// Offset the pith from the sawn board. Face grain, edge grain and rings
	// on the end are sections through the same drifting growth layers.
	vec2 radial = p.yz + vec2(.085*(seed-.47), .020+.062*seed);
	radial += vec2(.010*sin(4.8*x+seed*21.), .006*sin(7.3*x+seed*29.));
	float kx = mod(x+.46+seed*.83,1.04)-.52;
	float ky = p.y - (.095*sin(seed*53.)+.009*sin(9.*x));
	float k = exp(-dot(vec2(kx/.071,ky/.021),vec2(kx/.071,ky/.021)));
	radial.y += .011*k;
	float radius = length(radial) + .0012*sin(57.*radial.x+1.7*x);
	float phase = radius/ring_pitch + .15*sin(radius*537.+seed*52.) + .28*sin(radius*196.+2.*x);
	float band = .5+.5*cos(6.28318*phase);
	float late = mix(.26,band*band*band,1.-smoothstep(.18,.85,fwidth(phase)));
	// Project the pore sample into all three cut faces. No stretched strip on
	// a turned cheek or the edge of a bar. The ring field above is volumetric.
	vec3 n = abs(cross(dFdx(p),dFdy(p)));
	n /= max(n.x+n.y+n.z,1e-15);
	vec2 offset = vec2(seed*11.43,seed*5.79);
	vec4 pat = texture(workshop,p.xy/.32+offset)*n.z
		+ texture(workshop,p.xz/.32+offset)*n.y
		+ texture(workshop,p.zy/.32+offset)*n.x;
	vec3 edge = min(COLOR.rgb,1.-COLOR.rgb);
	float arris = 1.-smoothstep(.015,.12,max(min(edge.x,edge.y),min(max(edge.x,edge.y),edge.z)));
	float polish = clamp(arris*(.23+.69*pat.b)+oil*.24,0.,1.);
	float shade = clamp(.48 + .37*(pat.b-.5)+.19*(pat.a-.5) + .20*(seed-.5)
		+.115*sin(radius*219.+.24*sin(8.*x))-late*.34 - k*.43 - pat.r*.31*vessel, .015,.97);
	vec3 col = mix(heartwood.rgb,sapwood.rgb,shade);
	col *= 1.+polish*.26 - pat.g*.27;
	col = mix(col,sapwood.rgb,pat.g*.27*pat.b);
	float relief = -late*.00019 - pat.r*.00038*vessel - pat.g*.00076 + pat.a*.00007;
	float wear = 0.;
	float ink = 0.;
	if (case_lid && local_point.y>.909) {
		// The front lip has been lifted and wiped thousands of times. The
		// surface near the mended end was scraped back and oiled again.
		vec2 wipe=(local_point.xz-vec2(-.64,-1.275))/vec2(.38,.070);
		wear=exp(-dot(wipe,wipe))*(.69+.27*pat.b);
		vec2 repair=(local_point.xz-vec2(-1.44,-1.455))/vec2(.39,.098);
		float renewed=exp(-dot(repair,repair))*(.64+.22*pat.b);
		col=mix(col,sapwood.rgb,.30*wear);
		col*=1.-.15*renewed;
		polish=clamp(polish+wear*.6+renewed*.32,0.,1.);
		relief*=1.-.63*wear;
	}
	if (pitch>=0. && local_normal.y>.65) {
		vec3 at=(local_point-centre)/span;
		vec2 die=vec2(.5+at.x*1.33,.5+(at.z-.32)*span.z/(span.x*.45));
		float mask=step(0.,die.x)*step(die.x,1.)*step(0.,die.y)*step(die.y,1.);
		vec2 cell=vec2(mod(pitch,8.),floor(pitch/8.));
		ink=texture(punches,(cell+clamp(die,.001,.999))/vec2(8.,16.)).r*mask;
		vec2 mark=(local_point.xz-centre.xz)/vec2(.072,.103);
		wear=exp(-dot(mark,mark)*1.55)*(.64+.31*pat.b);
		col=mix(col,sapwood.rgb,wear*.34);
		col=mix(col,heartwood.rgb*.27,ink*.91);
		relief=relief*(1.-.65*wear)-.00014*ink;
	}
	vec3 dx=dFdx(VERTEX),dy=dFdy(VERTEX);
	vec3 a=cross(dy,NORMAL),b=cross(NORMAL,dx);
	float det=dot(dx,a);
	vec3 gradient=(a*dFdx(relief)+b*dFdy(relief))*sign(det)/max(abs(det),1e-12);
	NORMAL=normalize(NORMAL-gradient);
	ALBEDO=col;
	ROUGHNESS=clamp(.65-.22*oil-.16*polish-.13*wear+.13*pat.r+.08*pat.g+.10*(.5-pat.b),.22,.85);
	SPECULAR=.37;
	CLEARCOAT=oil*(.27+.5*polish);
	CLEARCOAT_ROUGHNESS=.27;
}
