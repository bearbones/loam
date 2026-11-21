shader_type spatial;
render_mode cull_disabled, diffuse_burley, specular_schlick_ggx;

uniform int finish = 0;
uniform vec4 tint : source_color = vec4(.60,.28,.15,1.);
uniform sampler2D toolmarks : repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D woodwork : repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D hammered : repeat_enable, filter_linear_mipmap_anisotropic;
uniform float radius = .25;
uniform float flex = 0.;
varying vec3 p;
void vertex() {
	p=VERTEX;
	if (finish==2) {
		float r=clamp(length(p.xz)/radius,0.,1.);
		VERTEX.y+=flex*(1.-r*r)*cos(4.2*r);
	}
}
void fragment(){
	vec3 c=tint.rgb;
	float rough=.4;
	float metal=0.;
	float coat=0.;
	float relief=0.;
	vec2 planar=vec2(p.x+p.z*.67,p.y+p.z*.32);
	vec3 map=texture(toolmarks,planar*2.8).rgb;
	if (finish==0) {
		// Translucent oxblood wrap over a hammered, silver-flecked ground.
		float fleck=texture(toolmarks,planar*12.).b;
		c*=.73+.48*map.r;
		c+=vec3(.28,.105,.055)*smoothstep(.59,.80,fleck)*(.50+.50*map.g);
		rough=.25+.13*map.g;metal=.32;coat=.66;
	} else if (finish==1) {
		float r=length(p.xz);
		vec2 polar=vec2(atan(p.z,p.x)/6.283185,r);
		float t=r*880.+.36*sin(polar.x*69.)+.15*sin(r*138.);
		float groove=cos(t*6.283185)*(1.-smoothstep(.14,.72,fwidth(t)));
		vec3 lathe=texture(toolmarks,p.xz*5.).rgb;
		float h=lathe.r;
		vec4 strike=texture(hammered,p.xz/.24);
		relief=.00075*strike.r+.000013*groove+.000032*(lathe.r-.5);
		c*=.79+.35*h+.055*groove;
		// A stamped pair of wings outside the bell, darkened in the die.
		vec2 badge=p.xz-vec2(.042,.108);
		float wing=abs(abs(badge.x)*.31+badge.y);
		float stamp=(1.-smoothstep(.0011,.0025,wing))*step(abs(badge.x),.035);
		stamp=max(stamp,(1.-smoothstep(.001,.0023,abs(length(badge)-.009))));
		c=mix(c,vec3(.045,.027,.016),stamp*.85);
		c*=.88+.11*strike.a+.08*strike.r+.018*sin(108.*r);
		rough=.25+.11*strike.a+.07*map.g+.010*groove;metal=.79;
	} else if (finish==2) {
		float grain=texture(toolmarks,p.xz*14.).b;
		float d=length((p.xz-vec2(.011,-.008))/radius);
		float wear=exp(-d*d*7.)*(.45+.54*map.r);
		float swirl=length(p.xz-vec2(.031,-.026));
		float arc=.5+.5*sin(swirl*1850.+map.r*4.);
		c*=1.-wear*(.18+.15*map.r)+.10*(grain-.5)-.025*arc*wear;
		relief=.00008*grain;
		rough=.74-.29*wear;
	} else if (finish==3) {
		float q=length(p.xz);
		float a=atan(p.z,p.x);
		float band=1.-smoothstep(.003,.008,min(abs(q-1.66),abs(q-1.55)));
		float braid=abs(abs(fract(a*7.64+.5)-.5)*.135-abs(q-1.605));
		float border=(1.-smoothstep(.002,.006,braid))*step(abs(q-1.605),.047);
		float inner=abs(q-(1.34+.044*cos(a*18.)));
		float gold=clamp(band+.7*border+.45*(1.-smoothstep(.002,.007,inner)),0.,1.);
		c=mix(vec3(.053,.064,.070),vec3(.228,.128,.068),gold*(.74+.18*map.r));
		float weave=sin(p.x*2600.)*sin(p.z*2440.);
		float aa=1.-smoothstep(.1,.6,max(fwidth(p.x),fwidth(p.z))*400.);
		c*=.80+.32*map.r+aa*.09*weave;rough=.91;
	} else if (finish==4) {
		float fiber=texture(woodwork,vec2(p.y*2.,(p.x+p.z)*11.)).a;
		c*=.81+.38*fiber;rough=.38;
	} else {
		c*=.80+.32*map.r;rough=.32+.15*map.g;metal=.37;coat=.32;relief=map.g*.00011;
	}
	vec3 dx=dFdx(VERTEX),dy=dFdy(VERTEX);
	vec3 a=cross(dy,NORMAL),b=cross(NORMAL,dx);
	float det=dot(dx,a);
	vec3 slope=(a*dFdx(relief)+b*dFdy(relief))*sign(det)/max(abs(det),1e-12);
	NORMAL=normalize(NORMAL-slope);
	ALBEDO=c;ROUGHNESS=rough;METALLIC=metal;CLEARCOAT=coat;CLEARCOAT_ROUGHNESS=.24;
}
