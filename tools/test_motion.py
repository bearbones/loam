"""Ruler for the two motion vocabularies (docs/motion-design.md).

    python3 tools/test_motion.py                       # both built assets
    python3 tools/test_motion.py LAYOUT.json SCORE.json

Holds formlab.rig.Rig to the rendered rig (harness/dev/dump_motion.gd prints
ClockworkMotion.tip_at at 240 Hz; skipped when godot is not on the PATH) and
checks what each vocabulary promises:
  - every scored contact is hit exactly and the path has no jumps at the
    score's boundaries (t_move, t, t_free);
  - a stepped arm's carriage travels in ratchet clicks: it holds still most
    of the way, overshoots each detent by no more than a tenth of a tooth and
    lands on the target; a mallet cocks above its rest before it drops, and
    falls without pause; the recoil is zero at every blow and by the next
    strike, rings within a blow's wake, and never pushes the mallet into the bar;
  - a servo arm slews on an S-curve: monotone (no overshoot), landing
    exactly, cruising at ~1/(1-ramp) of its mean speed, with a continuous
    acceleration (jerk-limited);
  - a blow shakes the assembly: the instrument's stand, the arm's rail and its
    gantry each answer every blow, are exactly zero at the blow itself, live
    in its wake and back to rest before the arm's next strike begins.
  - arms of one mechanism keep the planner's x clearance at every moment.
"""
import json, shutil, subprocess, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from formlab import rig as R
from formlab.rig import Rig

failures = []
def check(ok, msg):
    print(('  PASS ' if ok else '  FAIL ')+msg)
    if not ok: failures.append(msg)

def parity(rig, layout_path, score_path):
    godot = shutil.which('godot')
    if godot is None: print('  SKIP godot not on PATH: rendered-rig parity unmeasured'); return
    out = subprocess.run([godot, '--headless', '--path', str(ROOT/'harness'), '-s', 'dev/dump_motion.gd', '--',
                          f'--score={score_path}', f'--asset={layout_path.stem}'], capture_output=True, text=True, timeout=600).stdout
    worst = 0.0; n = 0; shud = 0.0; ns = 0; head = 0.0; felt = 0.0; nh = 0; consts = {}
    for line in out.splitlines():
        if line.startswith('CONST '):
            _, name, value = line.split(); consts[name] = float(value)
        elif line.startswith('TIP '):
            _, aid, t, x, y, z = line.split(); n += 1
            worst = max(worst, float(np.linalg.norm(rig.tip_at(aid, float(t))-np.array([float(x), float(y), float(z)]))))
        elif line.startswith('HEAD '):
            _, aid, t, a, fx, fy, fz = line.split(); t = float(t); nh += 1
            mine = rig.pose(aid, t)
            head = max(head, abs(mine['head']-float(a)))
            felt = max(felt, float(np.linalg.norm(mine['felt']-np.array([float(fx), float(fy), float(fz)]))))
        elif line.startswith('SHUD '):
            _, aid, t, stand, sag, sway = line.split(); t = float(t); ns += 1
            lo, hi = rig.rail_span(aid)
            mine = np.array([rig.stand_thump(rig.mech_of[aid], t), rig.rail_sag(aid, t, (lo+hi)/2), rig.mast_sway(aid, t)])
            shud = max(shud, float(np.abs(mine-np.array([float(stand), float(sag), float(sway)])).max()))
    # What a reposition costs is one module's business (loam/motion_timing.py);
    # the planner charges it, formlab.rig imports it and the harness mirrors
    # the numbers by hand. A drift here is two machines, not one.
    mine = R.motion_timing.constants()
    bad = [f'{k} {consts.get(k)} vs {v}' for k, v in mine.items() if abs(consts.get(k, np.nan)-v) > 1e-9]
    check(len(consts) == len(mine) and not bad,
          f'rendered rig mirrors every travel-timing constant: {len(consts)}/{len(mine)}'
          + (' — '+', '.join(bad) if bad else ''))
    check(n > 1000 and worst < 1e-5, f'rendered rig and numpy mirror agree: {n} samples, worst {worst:.2e} m')
    check(ns > 1000 and shud < 1e-9, f'rendered assembly shudder and numpy mirror agree: {ns} samples, worst {shud:.2e}')
    # the head's angle comes off a Vector3 length in GDScript, so it carries
    # float32 just as the tip does; the tolerance is the same as TIP's.
    if nh: check(head < 1e-6 and felt < 1e-5,
                 f'rendered hinged head and numpy mirror agree: {nh} samples, worst {head:.2e} rad / {felt:.2e} m')

def run(layout_path, score_path):
    print(f'== {layout_path.name} / {score_path.name}')
    layout = json.loads(layout_path.read_text()); score = json.loads(score_path.read_text())
    rig = Rig(score, layout)
    parity(rig, layout_path, score_path)
    worst_contact = 0.0; worst_step = 0.0
    for e in score['events']:
        aid = e['actuator']
        for k, sid in enumerate(e['strings']):
            t = float(e['t'])+k*float(e.get('spread_s', 0))
            worst_contact = max(worst_contact, np.linalg.norm(rig.tip_at(aid, t)-rig.contact(sid, e.get('pick'))))
        for key in ('t_move', 't', 't_free'):
            t = float(e[key]); worst_step = max(worst_step, np.linalg.norm(rig.tip_at(aid, t-1e-6)-rig.tip_at(aid, t+1e-6)))
    check(worst_contact < 1e-9, f'every contact exact (worst {worst_contact:.1e} m)')
    check(worst_step < 1e-3, f'no jump at a score boundary (worst {worst_step:.1e} m)')
    stepped_travels = servo_travels = 0; clicks_seen = set(); early = 0
    per_click = []; servo_rate = []; wanted = hurried = 0
    detent_min = 1.0; over_max = 0.0; over_min = 1.0; land_worst = 0.0
    cock_min = 1.0; drop_pause = 0; monotone = jerk = cruise = True; ratios = []
    for aid in rig.acts:
        stepped = rig.stepped(aid)
        for s in rig.schedule(aid):
            early += int(s['go'] < s['tm']-1e-9)
            # what the move wanted unhurried against the window it got
            if s['moving']:
                wanted += 1; hurried += int(s['want'] > s['approach']-s['go']+1e-9)
            if s['moving'] and abs(s['first'][0]-s['rest'][0]) > .02:
                T = s['approach']-s['go']; ts = s['go']+np.arange(0, int(T*1000)+1)/1000.0
                x = np.array([rig.path_at(aid, t)[0] for t in ts]); dx = np.diff(x)
                sign = np.sign(s['first'][0]-s['rest'][0]); span = abs(s['first'][0]-s['rest'][0])
                land_worst = max(land_worst, abs(rig.path_at(aid, s['approach'])[0]-s['first'][0]))
                if stepped:
                    stepped_travels += 1; n = R.clicks(s['first'][0]-s['rest'][0], T); clicks_seen.add(n)
                    per_click.append((T/n, R.teeth(s['first'][0]-s['rest'][0])/n))
                    # near a detent (within the pawl's play) most of the way, not in transit
                    step = span/n; near = np.abs((sign*(x-s['rest'][0])/step)-np.round(sign*(x-s['rest'][0])/step)) < R.OVERSHOOT*1.01
                    detent_min = min(detent_min, np.mean(near))
                    over = (sign*(x-s['first'][0])).max(); over_max = max(over_max, over); over_min = min(over_min, over)
                    # one click per detent: the path crosses each half-way point once
                    steps = sign*(x-s['rest'][0])/step; crossings = int(np.sum(np.diff(np.floor(steps+.5)) != 0))
                    if crossings != n: check(False, f'{aid} travel at {s["go"]:.2f}s: {crossings} clicks for {n} planned')
                else:
                    servo_travels += 1; servo_rate.append(span/T)
                    monotone &= bool(np.all(sign*dx >= -1e-12))
                    v = dx/1e-3; a = np.diff(v)/1e-3
                    if T > .8*R.SLEW_S: ratios.append(np.abs(v).max()/(span/T))
                    # a continuous acceleration: no sample-to-sample jump beyond the ramp's own jerk
                    jerk &= bool(np.abs(np.diff(a)).max() < 10*span/(R.SCURVE_RAMP**2*(1-R.SCURVE_RAMP)*T**3)*1e-3+1e-9)
            if stepped and s['moving']:
                ts = s['approach']+np.arange(0, int((s['hit']-s['approach'])*1000)+1)/1000.0
                y = np.array([rig.path_at(aid, t)[1] for t in ts])
                # ...measured against what the ARM lifts (Rig.hover): a hinged
                # hammer's arm hovers a third of the clearance and the head's
                # lay-back holds the felt face the rest of the way up.
                cock_min = min(cock_min, (y.max()-(s['first'][1]+rig.hover(aid)[1]))/rig.hover(aid)[1])
                half = len(y)//2; drop_pause += int(np.any(np.diff(y[half:]) > 1e-9))
    # One occupancy model, not two: the planner charges each reposition what
    # the vocabulary costs and checks the clearance from the instant the arm
    # really leaves, so the rig has nothing to start early and nothing to push.
    check(early == 0 and not rig.pushed,
          f'every move starts exactly where the score planned it: {early} early, {len(rig.pushed)} pushed')
    # ...and what it does in that window is inside the machine's limits. A
    # travel the score hurried clicks faster than CLICK_S and spans more than
    # one tooth a click; it may never beat the ratchet's own floor.
    slow = min(p for p, _ in per_click); wide = max(w for _, w in per_click)
    unhurried = sum(1 for p, _ in per_click if p > R.CLICK_S-1e-9)
    check(slow >= R.CLICK_MIN_S-1e-9 and wide <= R.CLICK_TEETH_MAX+1e-9,
          f'no click comes faster than {R.CLICK_MIN_S*1000:.0f} ms or spans more than {R.CLICK_TEETH_MAX} teeth '
          f'(fastest {slow*1000:.0f} ms, widest {wide:.2f} teeth; {unhurried}/{len(per_click)} travels click at '
          f'{R.CLICK_S*1000:.0f} ms a tooth)')
    check(wanted > 0, f'{wanted-hurried}/{wanted} repositions get the whole time the vocabulary wants '
                     f'({hurried} are hurried by the score and cross in what it left)')
    fast = max(servo_rate) if servo_rate else 0.0
    check(fast <= R.SERVO_V_MAX+1e-9,
          f'no servo slew crosses faster than {R.SERVO_V_MAX:g} m/s (fastest {fast:.2f} m/s over {len(servo_rate)} slews)')
    check(stepped_travels > 0 and detent_min >= .5, f'stepped carriages sit at a detent >= 50% of a travel ({stepped_travels} travels, least {detent_min:.2f}, clicks {sorted(clicks_seen)})')
    check(0 < over_max <= R.OVERSHOOT*R.PITCH*1.01 and over_min > .3*R.OVERSHOOT*R.PITCH, f'ratchet overshoot within a tenth of a tooth ({over_min*1000:.1f}..{over_max*1000:.1f} mm)')
    check(land_worst < 1e-9, f'every travel lands on its target (worst {land_worst:.1e} m)')
    check(cock_min > .3*R.COCK and drop_pause == 0, f'mallets cock (least {cock_min:.2f} of the lift) and drop without pause')
    check(servo_travels > 0 and monotone, f'{servo_travels} servo slews, all monotone (no overshoot)')
    check(jerk, 'servo slews are jerk-limited (continuous acceleration)')
    check(ratios and all(abs(r-1/(1-R.SCURVE_RAMP)) < .04 for r in ratios), f'unhurried slews cruise at 1/(1-ramp) of their mean speed ({len(ratios)} measured)')
    # recoil: exact zero at blows and by the next strike's start, live in a blow's wake, never toward the bar
    zero_worst = 0.0; live_min = 1.0; into_bar = 0.0
    for aid in rig.acts:
        # a hinged hammer recoils in its head and its check, not in the arm
        # (checked below); its arm's recoil is exactly zero by design
        if not rig.stepped(aid) or rig.hammer(aid): continue
        sched = rig.schedule(aid)
        for s in sched:
            zero_worst = max(zero_worst, np.linalg.norm(rig.recoil(aid, s['hit'])), np.linalg.norm(rig.recoil(aid, s['approach'])))
            live_min = min(live_min, max(np.linalg.norm(rig.recoil(aid, s['hit']+dt)) for dt in np.arange(.005, .04, .005)))
        for t in np.arange(0, float(score['total_s']), 1/240):
            into_bar = min(into_bar, rig.tip_at(aid, t)[1]-rig.path_at(aid, t)[1])
    # A hinged hammer instead: the head lies back at rest, flips to EXACTLY zero
    # at the blow (which is what puts the felt on the scored contact), never
    # passes through the bar, and the check takes a live rebound that is spent
    # before the arm is free.
    hammers = [a for a in rig.acts if rig.hammer(a)]
    for aid in hammers:
        rest = rig.rest_angle(aid)
        flip_zero = 0.0; flip_rest = 0.0; through = 0.0; bounce_min = 1.0; settled = 0.0; contact = 0.0
        for s in rig.schedule(aid):
            flip_zero = max(flip_zero, abs(rig.head_angle(aid, s['hit'])))
            flip_rest = max(flip_rest, abs(rig.head_angle(aid, s['go'])-rest))
            contact = max(contact, float(np.linalg.norm(rig.pose(aid, s['hit'])['felt']-s['first'])))
            # inside the release, where the check's bounce is what moves the
            # head: past t_free it is lying on its check again and the angle is
            # the rest angle, which would flatter this check into meaning nothing
            window = np.arange(.004, min(.05, max(s['t_free']-s['end'], .005)), .004)
            if len(window): bounce_min = min(bounce_min, max(rig.head_angle(aid, s['end']+dt)-rest*R.quintic(dt/max(s['t_free']-s['end'], 1e-6)) for dt in window))
            settled = max(settled, abs(rig.head_angle(aid, s['t_free'])-rest))
            for t in np.arange(s['approach'], s['end']+1e-9, .001):
                through = min(through, rig.head_angle(aid, t))
        check(flip_zero < 1e-12 and contact < 1e-9,
              f'{aid}: the head flips to exactly 0 at every blow, felt on the scored contact (worst {contact:.1e} m)')
        check(flip_rest < 1e-12 and settled < 1e-9, f'{aid}: the head lies on its check at rest and is back there when the arm is free')
        check(through > -1e-12, f'{aid}: the head never swings through the bar it just struck')
        check(bounce_min > .01, f'{aid}: the check takes a live rebound over the lay-back (least peak {bounce_min*1000:.1f} mrad)')
        arm_lift = float(rig.hover(aid)[1]); full = float(rig.clearance(aid)[1])
        check(abs(arm_lift/full-R.HAMMER['arm_share']) < 1e-12 and arm_lift < full,
              f'{aid}: the arm dips {arm_lift*1000:.0f} mm of the {full*1000:.0f} mm clearance ({R.HAMMER["arm_share"]:.0%}); the flip covers the rest')
    check(zero_worst < 1e-12, f'recoil exactly zero at every blow and every strike start (worst {zero_worst:.1e})')
    check(live_min > 1e-3, f'recoil rings in a blow\'s wake (least peak {live_min*1000:.1f} mm)')
    check(into_bar > -1e-12, 'recoil never pushes a mallet toward its bar')
    # the assembly's shudder: the stand, the rail and the gantry, off the recoil
    # bus. Each must be exactly zero at its own blow (so nothing displaces the
    # contact it answers), live 10-40 ms later, and back to rest before the
    # arm's next strike begins. The stand sums an instrument's arms, so it is
    # measured with one blow's own contribution.
    own_zero = 0.0; own_live = {}; gated = 0.0; peaks = {}
    for aid in rig.acts:
        if not rig.stepped(aid): continue
        lo, hi = rig.rail_span(aid); mid_x = (lo+hi)/2
        buses = {'stand': lambda t: rig._shudder([b], t, R.STAND_THUMP, lambda _b: 1.0),
                 'rail': lambda t: rig.rail_sag(aid, t, mid_x),
                 'mast': lambda t: rig.mast_sway(aid, t)}
        sched = rig.schedule(aid)
        for i, s in enumerate(sched):
            b = rig.blows_by_arm[aid][i]
            for name, f in buses.items():
                own_zero = max(own_zero, abs(f(s['hit'])))
                live = max(abs(f(s['hit']+dt)) for dt in np.arange(.010, .041, .005))
                own_live[name] = min(own_live.get(name, 1e9), live); peaks[name] = max(peaks.get(name, 0.0), live)
                if i+1 < len(sched): gated = max(gated, abs(f(sched[i+1]['approach'])))
    check(own_zero < 1e-12, f'every shudder is exactly zero at its blow (worst {own_zero:.1e})')
    check(all(v > 0 for v in own_live.values()),
          'every blow shakes the stand, the rail and the gantry 10-40 ms later (least '
          + ', '.join(f'{k} {own_live[k]*1000:.3f}' for k in ('stand', 'rail', 'mast'))+' mm/mrad)')
    check(gated < 1e-12, f'every shudder is gated to rest before the next strike begins (worst {gated:.1e})')
    named = [a[0]*R.SHUDDER_GAIN for a in (R.STAND_THUMP, R.RAIL_SAG, R.MAST_SWAY)]
    check(all(peaks[k] <= named[i]+1e-12 for i, k in enumerate(('stand', 'rail', 'mast'))),
          f'no shudder exceeds its named amplitude x gain {R.SHUDDER_GAIN:g} (peaks '
          + ', '.join(f'{k} {peaks[k]*1000:.3f}/{named[i]*1000:.2f}' for i, k in enumerate(('stand', 'rail', 'mast')))+')')
    # ...and the carriage rides the sagging rail while its tool stays exact
    sag_seen = 0.0; reach_ok = True
    for aid in rig.acts:
        if not rig.stepped(aid): continue
        for s in rig.schedule(aid):
            for dt in np.arange(.010, .041, .005):
                t = s['hit']+dt; p = rig.pose(aid, t)
                sag_seen = max(sag_seen, abs(p['root'][1]-layout['arms'][aid]['root_y']))
                reach_ok &= bool(p['reachable'])
    check(sag_seen > 1e-5 and reach_ok, f'the carriage follows the rail\'s sag ({sag_seen*1000:.2f} mm) and stays in reach')
    # the planner's x clearance between arms of one mechanism, at every moment
    worst_gap = np.inf; times = rig.sample_times()
    arms = list(rig.acts)
    for i, a in enumerate(arms):
        for b in arms[i+1:]:
            ma = layout['arms'][a]['mid']
            if ma != layout['arms'][b]['mid']: continue
            need = float(layout['mechanisms'][ma].get('arm_clearance_m', 0))
            if need <= 0: continue
            xa = np.array([rig.tip_at(a, t)[0] for t in times]); xb = np.array([rig.tip_at(b, t)[0] for t in times])
            worst_gap = min(worst_gap, (np.abs(xa-xb)-need).min())
    check(worst_gap > -1e-6, f'arms of one mechanism keep their planned x clearance ({worst_gap*1000:.0f} mm to spare)')

if __name__ == '__main__':
    # resolved: the paths are handed to godot, which does not share this cwd
    if len(sys.argv) > 2: pairs = [(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())]
    else: pairs = [(ROOT/'harness/assets/clockwork.json', ROOT/'render/chamber/score.json'),
                   (ROOT/'harness/assets/clockwork_expanded.json', ROOT/'render/clockwork/score.json')]
    for lp, sp in pairs: run(lp, sp)
    print('MOTION: '+('FAIL' if failures else 'PASS'))
    sys.exit(1 if failures else 0)
