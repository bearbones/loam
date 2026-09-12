"""Visual harp arrangement; explicit display proportions, independent of acoustic score geometry."""
def string_endpoints(mechanism, string):
    mid=mechanism['id']; mp=mechanism['pos']; sp=string['pos']
    x=3*(mp[0]+sp[0]); z=3*(mp[2]+sp[2]); length=3*string['length']*(1.7 if mid=='harp' else 1.0)
    struck=mechanism['kind']=='struck'
    y=(1.35 if struck else 2.05+3*mp[1])+3*sp[1]
    if mid in ('harp','rake'):
        xs=[s['pos'][0] for s in mechanism['strings']]
        import math
        lengths=[s['length'] for s in mechanism['strings']]
        u=math.log(max(lengths)/string['length'])/math.log(max(lengths)/min(lengths))
        if mid=='harp': u=u**.70
        span=3*(max(xs)-min(xs))*(.34 if mid=='harp' else .70)
        x=3*mp[0]+span*(u-.5)
        # A diagonal soundboard gathers the strings into a traditional triangular frame.
        y=.66+(1.64 if mid=='harp' else 1.36)*u
        return [x,y,z],[x,y+length,z]
    if struck: return [x,y,z-length/2],[x,y,z+length/2]
    return [x,y-length/2,z],[x,y+length/2,z]
