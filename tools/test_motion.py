"""Ruler for the motion vocabularies (docs/motion-design.md).

    python3 tools/test_motion.py                       # both built assets
    python3 tools/test_motion.py LAYOUT.json SCORE.json

formlab.rig.Rig is the one implementation of the motion; the harness plays a
bake of it (formlab/bake.py, held to the rig by tools/test_bake.py). Checks
what each vocabulary promises:
  - every scored contact is hit exactly and the path has no jumps at the
    score's boundaries (t_move, t, t_free) nor at a mallet's own (t_apex,
    arrive, t_head_free);
  - one occupancy model: every move leaves at the score's t_move exactly;
  - the hinged hammer's carriage travels in ratchet clicks: it holds still
    most of the way, overshoots each detent by no more than a tenth of a tooth
    and lands on the target; the arm cocks above its rest before it drops, and
    falls without pause;
  - a mallet's carriage (formlab/stroke.py, PLAYERS M1) travels contact to
    contact by its declared travels (Rig.stroke(aid).travels): never before
    the score's go, arriving on the contact's x by the contact or by its hold;
    a stepped (or homing) travel steps a tooth at a time, sits at a detent most
    of the way and overshoots its target by 0.3-1.0 x OVERSHOOT x PITCH (a
    tenth of a tooth) on the drawn carriage (Rig.carriage_x, the detent ring;
    tools/test_stroke.py holds every landing); every travel clicks
    once a tooth, a freewheel's clicks at each mid-tooth crossing, a stepped
    one's at each landing and never faster than the ratchet's floor. The
    mallet's downstroke (it no longer cocks) is rulers 3, 4 and 8's;
  - a mallet's recoil (x and z rings, no bounce) is zero at every blow and by
    the next stroke's apex, rings within a blow's wake, and never carries the
    head below its contact's height;
  - a servo arm slews on an S-curve: monotone (no overshoot), landing
    exactly, cruising at ~1/(1-ramp) of its mean speed, with a continuous
    acceleration (jerk-limited);
  - a blow shakes the assembly: the instrument's stand, the arm's rail and its
    gantry each answer every blow, are exactly zero at the blow itself, live
    in its wake and back to rest before the arm's next strike begins (a
    mallet's next apex, the hammer's next approach).
  - arms of one mechanism keep the planner's x clearance at every moment.
"""
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from formlab import rig as R
from formlab.rig import Rig
motion_timing = R.motion_timing     # the module the rig and the planner both move by

failures = []
def check(ok, msg):
    print(('  PASS ' if ok else '  FAIL ')+msg)
    if not ok: failures.append(msg)

def run(layout_path, score_path):
    print(f'== {layout_path.name} / {score_path.name}')
    layout = json.loads(layout_path.read_text()); score = json.loads(score_path.read_text())
    rig = Rig(score, layout)
    worst_contact = 0.0; worst_step = 0.0
    for e in score['events']:
        aid = e['actuator']
        for k, sid in enumerate(e['strings']):
            t = float(e['t'])+k*float(e.get('spread_s', 0))
            worst_contact = max(worst_contact, np.linalg.norm(rig.tip_at(aid, t)-rig.contact(sid, e.get('pick'))))
        for key in ('t_move', 't', 't_free'):
            t = float(e[key]); worst_step = max(worst_step, np.linalg.norm(rig.tip_at(aid, t-1e-6)-rig.tip_at(aid, t+1e-6)))
    # ...and a mallet's own boundaries: its stroke's apex, the carriage's
    # arrival and the instant the head is free (the contact)
    for aid in rig.acts:
        if not rig.mallet(aid): continue
        for s in rig.schedule(aid):
            for key in ('t_apex', 'arrive', 't_head_free'):
                t = float(s[key]); worst_step = max(worst_step, np.linalg.norm(rig.tip_at(aid, t-1e-6)-rig.tip_at(aid, t+1e-6)))
    check(worst_contact < 1e-9, f'every contact exact (worst {worst_contact:.1e} m)')
    check(worst_step < 1e-3, f'no jump at a score boundary (worst {worst_step:.1e} m)')
    stepped_travels = servo_travels = 0; clicks_seen = set(); early = 0
    per_click = []; servo_rate = []; wanted = hurried = 0
    detent_min = 1.0; over_max = 0.0; over_min = 1.0; land_worst = 0.0
    cock_min = 1.0; drop_pause = 0; cocked = 0; monotone = jerk = cruise = True; ratios = []
    for aid in rig.acts:
        stepped = rig.stepped(aid)
        for s in rig.schedule(aid):
            # the score's t_move exactly: not early, and not silently late
            # (a rig that waits for t_free where the plan freed the carriage
            # at the contact is a second occupancy model)
            early += int(abs(s['go']-s['tm']) > 1e-9)
            # what the move wanted unhurried against the window it got
            if s['moving']:
                wanted += 1
                kind = rig.acts[aid]['kind']; dx = s['first'][0]-s['rest'][0]
                hurried += int(motion_timing.hurried(kind, dx, s['arrive']-s['go'])
                               if motion_timing.contact_to_contact(kind)
                               else s['want'] > s['approach']-s['go']+1e-9)
            # A mallet no longer crosses [go, approach] in one click a window
            # under a cocked head: its carriage is judged on its stroke's
            # declared travels below. Past this line `stepped` is the hammer.
            if rig.mallet(aid): continue
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
                half = len(y)//2; drop_pause += int(np.any(np.diff(y[half:]) > 1e-9)); cocked += 1
    # A mallet's carriage, by its stroke's declared travels (DESIGN §2-§4):
    # contact to contact (freewheel: one 3-4-5; stepped: a 3-4-5 step and a
    # detent dwell a tooth) and the homing x legs (stepped, tooth by tooth).
    # The drawn carriage is Rig.carriage_x: the scored x plus the detent ring.
    m_travels = dict(step=0, freewheel=0, home=0); m_dwell = 1.0; m_over = []; m_land = 0.0
    m_bad_cross = []; m_before_go = 0; m_late = 0; m_at_go = 0; m_scored = 0
    m_gap = np.inf; m_click_x = 0.0; m_teeth = set(); m_hurried = m_hurry_off = 0
    for aid in rig.acts:
        st = rig.stroke(aid)
        if st is None: continue
        row = {id(s['event']): s for s in rig.schedule(aid)}
        by_travel = {}
        for c in st.clicks(): by_travel.setdefault(c['travel'], []).append(c)
        for tv in st.travels:
            m_travels[tv['regime']] += 1; m_teeth.add(tv['teeth'])
            sg = 1.0 if tv['x1'] > tv['x0'] else -1.0; step = abs(tv['x1']-tv['x0'])/tv['teeth']
            ts = np.arange(tv['t0'], tv['t1'], 1e-3)
            cx = np.array([rig.carriage_x(aid, t) for t in ts]); u = sg*(cx-tv['x0'])/step
            # lands: on its target x, and that is the contact's x, held from the
            # arrival (the contact itself, or the hold's start) to the contact
            m_land = max(m_land, abs(rig.carriage_x(aid, tv['t1'])-tv['x1']))
            if tv['event'] >= 0:
                s = row[id(score['events'][tv['event']])]; m_scored += 1
                m_land = max(m_land, abs(tv['x1']-s['first'][0]),
                             max(abs(rig.carriage_x(aid, t)-s['first'][0]) for t in np.linspace(tv['t1'], s['hit'], 25)))
                m_late += int(tv['t1'] > s['hit']+1e-9)
                # the rig hurries exactly the travels the planner counted hurried
                m_hurried += int(bool(tv['hurried'])); m_hurry_off += int(bool(tv['hurried']) != bool(
                    motion_timing.hurried(rig.acts[aid]['kind'], s['first'][0]-s['rest'][0], s['arrive']-s['go'])))
                # the carriage never moves before the score's go
                m_before_go += int(tv['t0'] < s['go']-1e-9); m_at_go += int(abs(tv['t0']-s['go']) <= 1e-9)
                if tv['t0'] > s['go']: m_before_go += int(np.ptp([rig.carriage_x(aid, t) for t in np.linspace(s['go'], tv['t0'], 25)]) > 1e-12)
            # one click a tooth: the carriage crosses each half-way point once,
            # and the click is where the vocabulary puts it (a freewheel's at the
            # mid-tooth crossing, a step's at its landing) on the scored x
            crossings = int(np.sum(np.diff(np.floor(u+.5)) != 0)); cs = sorted(by_travel.get(tv['id'], []), key=lambda c: c['t'])
            if crossings != tv['teeth'] or len(cs) != tv['teeth']:
                m_bad_cross.append(f'{aid} travel {tv["id"]} ({tv["regime"]}) at {tv["t0"]:.2f}s: {crossings} crossings, {len(cs)} clicks for {tv["teeth"]} teeth')
            for k, c in enumerate(cs):
                want = tv['x0']+sg*step*(k+(.5 if tv['regime'] == 'freewheel' else 1.0))
                m_click_x = max(m_click_x, abs(rig.path_at(aid, c['t'])[0]-want))
            if tv['regime'] == 'freewheel': continue
            if len(cs) > 1: m_gap = min(m_gap, float(np.diff([c['t'] for c in cs]).min()))
            # near a detent (within the pawl's play) most of the way, not in transit
            m_dwell = min(m_dwell, float(np.mean(np.abs(u-np.round(u)) < R.OVERSHOOT*1.01)))
            # the designed rebound: past the last landing, on the drawn carriage
            tt = np.arange(tv['t0'], tv['t1']+.06, 1e-3)
            m_over.append(max(sg*(rig.carriage_x(aid, t)-tv['x1']) for t in tt))
    # One occupancy model, not two: the planner charges each reposition what
    # the vocabulary costs and checks the clearance from the instant the arm
    # really leaves, so the rig has nothing to start early and nothing to push.
    check(early == 0 and not rig.pushed,
          f'every move starts exactly where the score planned it: {early} off t_move, {len(rig.pushed)} pushed')
    # ...and what it does in that window is inside the machine's limits. A
    # hammer travel the score hurried clicks faster than CLICK_S and spans
    # more than one tooth a click; it may never beat the ratchet's own floor.
    # (A mallet clicks a tooth: its floor is judged on its stepped clicks below.)
    hammers = [a for a in rig.acts if rig.hammer(a)]
    mallets = [a for a in rig.acts if rig.mallet(a)]
    if hammers or per_click:
        slow = min((p for p, _ in per_click), default=0.0); wide = max((w for _, w in per_click), default=np.inf)
        unhurried = sum(1 for p, _ in per_click if p > R.CLICK_S-1e-9)
        check(per_click and slow >= R.CLICK_MIN_S-1e-9 and wide <= R.CLICK_TEETH_MAX+1e-9,
              f'hammer: no click comes faster than {R.CLICK_MIN_S*1000:.0f} ms or spans more than {R.CLICK_TEETH_MAX} teeth '
              f'(fastest {slow*1000:.0f} ms, widest {wide:.2f} teeth; {unhurried}/{len(per_click)} travels click at '
              f'{R.CLICK_S*1000:.0f} ms a tooth)')
    check(wanted > 0, f'{wanted-hurried}/{wanted} repositions get the whole time the vocabulary wants '
                     f'({hurried} are hurried by the score and cross in what it left)')
    fast = max(servo_rate) if servo_rate else 0.0
    check(fast <= R.SERVO_V_MAX+1e-9,
          f'no servo slew crosses faster than {R.SERVO_V_MAX:g} m/s (fastest {fast:.2f} m/s over {len(servo_rate)} slews)')
    if hammers or stepped_travels:
        check(stepped_travels > 0 and detent_min >= .5, f'hammer: the carriage sits at a detent >= 50% of a travel ({stepped_travels} travels, least {detent_min:.2f}, clicks {sorted(clicks_seen)})')
        check(0 < over_max <= R.OVERSHOOT*R.PITCH*1.01 and over_min > .3*R.OVERSHOOT*R.PITCH, f'hammer: ratchet overshoot within a tenth of a tooth ({over_min*1000:.1f}..{over_max*1000:.1f} mm)')
    check(land_worst < 1e-9, f'every {"hammer and " if hammers else ""}servo travel lands on its target (worst {land_worst:.1e} m)')
    if hammers or cocked:
        check(cocked > 0 and cock_min > .3*R.COCK and drop_pause == 0, f'hammer: the arm cocks (least {cock_min:.2f} of the lift) and drops without pause ({cocked} strokes)')
    if mallets:
        n_step = m_travels['step']+m_travels['home']
        for msg in m_bad_cross: check(False, msg)
        check(not m_bad_cross and m_click_x < 1e-6,
              f'mallets click once a tooth: {sum(m_travels.values())} travels ({m_travels["step"]} stepped, '
              f'{m_travels["freewheel"]} freewheel, {m_travels["home"]} homing legs; teeth {sorted(m_teeth)}) cross each '
              f'half-tooth once, each click where it falls (a freewheel\'s mid-tooth, a step\'s landing; worst {m_click_x:.1e} m)')
        check(n_step > 0 and m_gap >= R.CLICK_MIN_S-1e-9,
              f'mallets\' stepped and homing clicks come no faster than {R.CLICK_MIN_S*1000:.0f} ms (fastest {m_gap*1000:.0f} ms)')
        check(m_travels['step'] > 0 and m_dwell >= .5,
              f'mallets\' stepped carriages sit at a detent >= 50% of a travel ({n_step} stepped and homing travels, least {m_dwell:.2f})')
        lo = min(m_over, default=0.0); hi = max(m_over, default=0.0)
        check(m_over and 0 < hi <= R.OVERSHOOT*R.PITCH*1.01 and lo > .3*R.OVERSHOOT*R.PITCH,
              f'mallets\' stepped landings overshoot within a tenth of a tooth on the drawn carriage ({lo*1000:.1f}..{hi*1000:.1f} mm)')
        check(m_land < 1e-9 and m_late == 0,
              f'every mallet travel lands on its target, the contact\'s x, by the contact or its hold, and holds it to the contact '
              f'(worst {m_land:.1e} m, {m_late} late)')
        check(m_hurry_off == 0, f'the mallets\' stroke hurries exactly the travels the planner counts hurried ({m_hurried}, {m_hurry_off} disagree)')
        check(m_before_go == 0,
              f'no mallet carriage moves before the score\'s go ({m_at_go}/{m_scored} travels leave at go, the rest later)')
    check(servo_travels > 0 and monotone, f'{servo_travels} servo slews, all monotone (no overshoot)')
    check(jerk, 'servo slews are jerk-limited (continuous acceleration)')
    check(ratios and all(abs(r-1/(1-R.SCURVE_RAMP)) < .04 for r in ratios), f'unhurried slews cruise at 1/(1-ramp) of their mean speed ({len(ratios)} measured)')
    # recoil: exact zero at blows and by the next stroke's start (its apex: the
    # mallet's downstroke begins there), live in a blow's wake, never toward
    # the bar; and the head (tip_at, rings and all) never below its contact's
    # height, the mallet's own "h >= 0" now that the |sine| bounce is retired
    zero_worst = 0.0; live_min = 1.0; into_bar = 0.0; head_h = (np.inf, 0.0)
    for aid in rig.acts:
        # a hinged hammer recoils in its head and its check, not in the arm
        # (checked below); its arm's recoil is exactly zero by design
        if not rig.stepped(aid) or rig.hammer(aid): continue
        sched = rig.schedule(aid); st = rig.stroke(aid)
        for s in sched:
            zero_worst = max(zero_worst, np.linalg.norm(rig.recoil(aid, s['hit'])), np.linalg.norm(rig.recoil(aid, s['t_apex'])))
            live_min = min(live_min, max(np.linalg.norm(rig.recoil(aid, s['hit']+dt)) for dt in np.arange(.005, .04, .005)))
        for t in np.arange(-1, float(score['total_s']), 1/240):
            tip = rig.tip_at(aid, t)
            into_bar = min(into_bar, tip[1]-rig.path_at(aid, t)[1])
            h = float(tip[1]-st.yc.ev(t))
            if h < head_h[0]: head_h = (h, float(t))
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
    check(zero_worst < 1e-12, f'recoil exactly zero at every blow and every stroke\'s start, its apex (worst {zero_worst:.1e})')
    check(live_min > 1e-3, f'recoil rings in a blow\'s wake (least peak {live_min*1000:.1f} mm)')
    check(into_bar > -1e-12, 'recoil never pushes a mallet toward its bar')
    check(head_h[0] > -1e-12, f'no mallet head dips below its contact\'s height (least {head_h[0]*1000:.3f} mm, at {head_h[1]:.3f} s)')
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
                # the next strike begins: a mallet's next apex (its blows' gate_end),
                # the hammer's next approach
                if i+1 < len(sched): gated = max(gated, abs(f(sched[i+1]['t_apex' if rig.mallet(aid) else 'approach'])))
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
