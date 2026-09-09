import {DEFAULT, DIMENSIONS, clamp, randomPlane, atPosition, validVector, validAxes, validNotes} from './space.js';

const $ = id => document.getElementById(id);
const VERSION = 'soundgarden-resonator/1';
const STORAGE = 'loam.soundgarden.session.v1';
const PHRASE = [60, null, 67, null, 64, null, 72, 67, null, 64, null, 62, 67, null, 64, null];
const copy = x => structuredClone(x);
let state = {version: VERSION, center: [...DEFAULT], axes: randomPlane(), position: [0, 0], radius: 1,
  round: 1, notes: [...PHRASE], bpm: 96, volume: .45, favorites: [], history: []};
let comparing = false, path = [], seeds = [], selectedSeed = 'Porcelain';
let context, master, compressor, limiter, buffers = {}, playing = false, nextTime = 0, nextStep = 0;
let timer, paintFrame, playEvents = [], voices = new Set(), revision = 0, renderTimer, pending = null, rendering = false;
let ready = false, storageWarning = false;
const noteName = midi => ['C','C♯','D','D♯','E','F','F♯','G','G♯','A','A♯','B'][midi % 12] + (Math.floor(midi / 12) - 1);
const status = text => { $('status').textContent = text; };
const current = () => atPosition(state.center, state.axes, state.position, state.radius);
const audible = () => comparing ? state.center : current();
function fieldSnapshot() {
  const {center, axes, position, radius, round} = state;
  return copy({center, axes, position, radius, round});
}
function validField(s) {
  return s && validVector(s.center) && validAxes(s.axes) && Array.isArray(s.position) && s.position.length === 2 && s.position.every(x => typeof x === 'number' && Number.isFinite(x) && Math.abs(x) <= 1) && typeof s.radius === 'number' && s.radius >= .15 && s.radius <= 2 && Number.isInteger(s.round) && s.round >= 1;
}
function validateSession(s) {
  if (!s || s.version !== VERSION || !validField(s) || !validNotes(s.notes) || !Number.isInteger(s.bpm) || s.bpm < 40 || s.bpm > 200 || typeof s.volume !== 'number' || !Number.isFinite(s.volume) || s.volume < 0 || s.volume > .9 || !Array.isArray(s.history) || s.history.length > 100 || !s.history.every(validField) || !Array.isArray(s.favorites) || s.favorites.length > 100 || !s.favorites.every(f => f && typeof f.name === 'string' && f.name.length <= 80 && validVector(f.vector) && validNotes(f.notes) && Number.isInteger(f.bpm) && f.bpm >= 40 && f.bpm <= 200)) throw new Error('This is not a compatible Soundgarden session.');
  return copy(s);
}
function save() {
  try { localStorage.setItem(STORAGE, JSON.stringify(state)); }
  catch { storageWarning = true; status('Browser storage is full or unavailable. Export your session to keep it.'); }
}
try {
  const previous = localStorage.getItem(STORAGE);
  if (previous) { state = validateSession(JSON.parse(previous)); selectedSeed = ''; }
} catch { storageWarning = true; status('Saved session could not be loaded. Starting with Porcelain.'); }

function initAudio() {
  if (context) return;
  context = new AudioContext();
  master = context.createGain();
  master.gain.value = state.volume;
  compressor = context.createDynamicsCompressor();
  compressor.threshold.value = -14;
  compressor.knee.value = 12;
  compressor.ratio.value = 8;
  compressor.attack.value = .003;
  compressor.release.value = .12;
  limiter = context.createWaveShaper();
  limiter.curve = Float32Array.from({length: 4097}, (_, i) => .85 * Math.tanh((i / 2048 - 1) / .85));
  master.connect(compressor).connect(limiter).connect(context.destination);
}
async function unlockAudio() {
  initAudio();
  if (context.state !== 'running') await context.resume();
}
function sound(midi, when) {
  const buffer = buffers[midi];
  if (!buffer || !context || context.state !== 'running') return;
  const source = context.createBufferSource();
  source.buffer = buffer;
  const gain = context.createGain();
  gain.gain.value = .65;
  source.connect(gain).connect(master);
  const voice = {source, gain};
  voices.add(voice);
  source.onended = () => { voices.delete(voice); source.disconnect(); gain.disconnect(); };
  source.start(when);
}
function silence() {
  if (!context) return;
  const now = context.currentTime;
  for (const {source, gain} of voices) {
    gain.gain.cancelScheduledValues(now);
    gain.gain.setTargetAtTime(0, now, .008);
    source.stop(now + .05);
  }
}
function paintPlayhead(step) {
  document.querySelectorAll('.playhead').forEach(e => e.classList.remove('playhead'));
  document.querySelectorAll('#steps .active').forEach(e => e.classList.remove('active'));
  if (step !== null) {
    document.querySelectorAll(`.note[data-step="${step}"]`).forEach(e => e.classList.add('playhead'));
    $('steps').children[step + 1].classList.add('active');
  }
}
function drawTransport() {
  if (!playing) return;
  let latest = null;
  while (playEvents.length && playEvents[0].time <= context.currentTime) latest = playEvents.shift().step;
  if (latest !== null) paintPlayhead(latest);
  paintFrame = requestAnimationFrame(drawTransport);
}
function schedule() {
  if (!playing) return;
  const now = context.currentTime;
  // Resume after sleep without trying to play every missed note at once.
  if (nextTime < now - .15) nextTime = now + .025;
  while (nextTime < now + .12) {
    const note = state.notes[nextStep];
    if (note !== null) sound(note, nextTime);
    playEvents.push({time: nextTime, step: nextStep});
    nextTime += 60 / state.bpm / 4;
    nextStep = (nextStep + 1) % 16;
  }
}
function stop() {
  playing = false;
  clearInterval(timer); cancelAnimationFrame(paintFrame);
  playEvents = []; silence(); paintPlayhead(null);
  $('play').textContent = 'Play loop';
}
$('play').onclick = async () => {
  if (playing) { stop(); return; }
  try {
    await unlockAudio();
    playing = true; nextStep = 0; nextTime = context.currentTime + .05;
    $('play').textContent = 'Stop loop';
    schedule(); timer = setInterval(schedule, 25); drawTransport();
  } catch { status('Audio could not start. Check your browser’s audio permissions.'); }
};
document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); });

function requestRender(immediate = false, audition = false) {
  const id = ++revision;
  clearTimeout(renderTimer);
  pending = null;
  const request = {id, vector: audible(), notes: [...new Set([60, ...state.notes.filter(n => n !== null)])], audition};
  const enqueue = () => { pending = request; pump(); };
  if (immediate) enqueue(); else renderTimer = setTimeout(enqueue, 140);
  status(ready ? 'Preparing sound… current loop continues' : 'Preparing your instrument…');
}
async function pump() {
  if (rendering || !pending) return;
  const request = pending; pending = null; rendering = true;
  try {
    const response = await fetch('/api/render', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(request), signal:AbortSignal.timeout(30000)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Render failed');
    if (request.id !== revision) return;
    initAudio();
    const decoded = {};
    await Promise.all(Object.entries(data.samples).map(async ([note, encoded]) => {
      const bytes = Uint8Array.from(atob(encoded), c => c.charCodeAt(0));
      decoded[note] = await context.decodeAudioData(bytes.buffer);
    }));
    if (request.id !== revision) return;
    buffers = decoded; ready = true; $('play').disabled = false;
    $('brightness').textContent = Math.round(data.metrics.centroid_hz).toLocaleString();
    $('decay').textContent = data.metrics.energy95_s.toFixed(2);
    $('peak').textContent = (20 * Math.log10(data.metrics.peak)).toFixed(1);
    status(storageWarning ? 'Export your session to preserve it outside this browser.' : comparing ? 'Listening to this field’s starting sound' : playing ? 'Playing your current sound' : 'Ready to play · drag to audition');
    if (request.audition && !playing && context.state === 'running') {
      silence(); sound(request.audition === true ? 60 : request.audition, context.currentTime + .06);
    }
  } catch (error) {
    if (request.id === revision) status(`Sound unavailable. Check the local server, then move the pad to retry. ${error.message}`);
  } finally { rendering = false; if (pending) pump(); }
}

function axisName(axis) {
  const ranked = axis.map((value, i) => ({value, i})).filter(item => Math.abs(item.value) >= .05).sort((a,b) => Math.abs(b.value) - Math.abs(a.value)).slice(0,2);
  return ranked.map(({value,i}) => `${DIMENSIONS[i].toLowerCase()} ${value >= 0 ? '+' : '−'}`).join(', ');
}
function updateField() {
  const [x,y] = state.position;
  const px = (x + 1) * 300, py = (1 - y) * 195;
  for (const id of ['cursor','cursor-halo']) { $(id).setAttribute('cx',px); $(id).setAttribute('cy',py); }
  const rect = $('pad').getBoundingClientRect();
  for (const [id, radius] of [['cursor',8],['cursor-halo',23],['origin',4]]) {
    $(id).setAttribute('rx', radius * 600 / rect.width);
    $(id).setAttribute('ry', radius * 390 / rect.height);
  }
  $('cross-x').setAttribute('x1',px); $('cross-x').setAttribute('x2',px);
  $('cross-y').setAttribute('y1',py); $('cross-y').setAttribute('y2',py);
  $('trail').setAttribute('points', path.map(([x,y]) => `${(x+1)*300},${(1-y)*195}`).join(' '));
  $('coordinates').textContent = `${x.toFixed(2)} / ${y.toFixed(2)}`;
  $('axis-x').textContent = `Right: ${axisName(state.axes[0])}`;
  $('axis-y').textContent = `Up: ${axisName(state.axes[1])}`;
  $('round').textContent = `Exploration ${state.round}`;
  $('radius').value = state.radius; $('radius-value').textContent = state.radius.toFixed(2) + '×';
  $('undo').disabled = state.history.length === 0;
  $('compare').setAttribute('aria-pressed', String(comparing));
  $('compare').textContent = comparing ? 'Return to current sound' : 'Hear starting sound';
  $('recipe').replaceChildren(...audible().map((v,i) => {
    const row = document.createElement('div'); row.className = 'parameter';
    const label = document.createElement('span'); label.textContent = DIMENSIONS[i];
    const value = document.createElement('span'); value.textContent = v.toFixed(3);
    row.append(label,value); return row;
  }));
}
function changePosition(position) {
  comparing = false; state.position = position; selectedSeed = '';
  document.querySelectorAll('.seed.selected').forEach(el => el.classList.remove('selected'));
  path.push(position); path = path.slice(-80);
  updateField(); save(); requestRender(false, true);
}
const pad = $('pad');
const positionFromEvent = e => {
  const rect = pad.getBoundingClientRect();
  return [clamp((e.clientX - rect.left) / rect.width * 2 - 1, -1, 1), clamp(1 - (e.clientY - rect.top) / rect.height * 2, -1, 1)];
};
pad.onpointerdown = e => {
  if (e.button !== 0) return;
  unlockAudio().catch(() => status('Press Play loop to enable audio.'));
  pad.focus(); pad.setPointerCapture(e.pointerId); changePosition(positionFromEvent(e));
};
pad.onpointermove = e => { if (pad.hasPointerCapture(e.pointerId)) changePosition(positionFromEvent(e)); };
pad.onpointerup = e => { if (pad.hasPointerCapture(e.pointerId)) pad.releasePointerCapture(e.pointerId); };
pad.onkeydown = e => {
  const directions = {ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,1],ArrowDown:[0,-1]};
  if (!directions[e.key]) return;
  e.preventDefault(); unlockAudio().catch(() => {});
  const delta = e.shiftKey ? .01 : .06;
  changePosition(state.position.map((v,i) => clamp(v + directions[e.key][i] * delta, -1, 1)));
};
function pushHistory() { state.history.push(fieldSnapshot()); state.history = state.history.slice(-100); }
$('keep').onclick = () => {
  pushHistory(); state.center = audible(); state.position = [0,0]; state.axes = randomPlane();
  state.round++; path = []; comparing = false; selectedSeed = '';
  updateField(); renderSeeds(); save(); requestRender(true);
};
$('undo').onclick = () => {
  if (!state.history.length) return;
  Object.assign(state, state.history.pop()); path = []; comparing = false; selectedSeed = '';
  updateField(); renderSeeds(); save(); requestRender(true, true);
};
$('compare').onclick = () => {
  unlockAudio().catch(() => {}); comparing = !comparing;
  updateField(); requestRender(true, true);
};
$('radius').oninput = e => { state.radius = +e.target.value; comparing = false; updateField(); save(); requestRender(); };
$('volume').value = state.volume;
$('volume').oninput = e => { state.volume = +e.target.value; if (master) master.gain.setTargetAtTime(state.volume, context.currentTime, .02); save(); };

function setSeed(vector, plane = null) {
  pushHistory(); state.center = [...vector]; state.position = [0,0];
  state.axes = validAxes(plane?.axes) ? copy(plane.axes) : randomPlane();
  state.radius = typeof plane?.radius === 'number' && Number.isFinite(plane.radius) ? clamp(plane.radius,.15,2) : 1;
  state.round++; comparing = false; path = [];
  unlockAudio().catch(() => {}); updateField(); renderSeeds(); save(); requestRender(true, true);
}
function renderSeeds() {
  $('seeds').replaceChildren(...seeds.map(seed => {
    const button = document.createElement('button');
    button.className = 'seed' + (selectedSeed === seed.name ? ' selected' : '');
    const name = document.createElement('strong'); name.textContent = seed.name;
    const detail = document.createElement('small');
    detail.textContent = seed.metrics ? `${Math.round(seed.metrics.centroid_hz)} Hz · ${seed.metrics.energy95_s.toFixed(2)} s` : 'Starter sound';
    button.append(name, detail);
    button.onclick = () => { selectedSeed = seed.name; setSeed(seed.vector, seed.plane); };
    return button;
  }));
}
async function refreshLibrary() {
  try {
    const response = await fetch('/api/library');
    if (!response.ok) throw new Error();
    const data = await response.json();
    if (data.version !== VERSION) throw new Error();
    seeds = data.seeds.filter(s => validVector(s.vector)); renderSeeds();
    if (data.warning) status(data.warning);
  } catch { status('Starting points unavailable. Check the local server and press Refresh.'); }
}
$('refresh').onclick = refreshLibrary;
function renderFavorites() {
  const container = $('favorites'); container.replaceChildren();
  if (!state.favorites.length) {
    const empty = document.createElement('p'); empty.className = 'hint';
    empty.textContent = 'Keep the discoveries you want to hear again. Each saves its phrase, too.'; container.append(empty);
  }
  state.favorites.forEach((favorite,i) => {
    const row = document.createElement('div'); row.className = 'favorite-row';
    const button = document.createElement('button'); button.className = 'recall'; button.textContent = favorite.name;
    button.onclick = () => { state.notes = [...favorite.notes]; state.bpm = favorite.bpm; $('bpm').value = state.bpm; updateNotes(); selectedSeed = ''; setSeed(favorite.vector); };
    const remove = document.createElement('button'); remove.className = 'remove'; remove.textContent = '×';
    remove.setAttribute('aria-label', `Remove ${favorite.name}`);
    remove.onclick = () => { state.favorites.splice(i,1); renderFavorites(); save(); };
    row.append(button,remove); container.append(row);
  });
  $('favorite').disabled = state.favorites.length >= 100;
}
$('favorite').onclick = () => {
  if (state.favorites.length >= 100) return;
  const name = `Sound ${String(state.favorites.length + 1).padStart(2,'0')}`;
  state.favorites.push({name, vector: audible(), notes:[...state.notes], bpm:state.bpm});
  renderFavorites(); save(); status(`${name} saved with this phrase.`);
};

function updateNotes() {
  document.querySelectorAll('.note').forEach(button => {
    const on = state.notes[+button.dataset.step] === +button.dataset.midi;
    button.classList.toggle('on', on); button.setAttribute('aria-pressed', String(on));
  });
  $('note-count').textContent = `${state.notes.filter(n => n !== null).length} notes / 16 steps`;
}
function buildPiano() {
  for (let midi = 72; midi >= 60; midi--) {
    const label = document.createElement('span'); label.className = 'key-label'; label.textContent = noteName(midi); $('piano').append(label);
    for (let step = 0; step < 16; step++) {
      const button = document.createElement('button');
      button.className = `note${[1,3,6,8,10].includes(midi % 12) ? ' black' : ''}${step % 4 === 0 ? ' bar' : ''}`;
      button.dataset.midi = midi; button.dataset.step = step;
      button.setAttribute('aria-label', `${noteName(midi)}, step ${step + 1}`);
      button.tabIndex = midi === 60 && step === 0 ? 0 : -1;
      button.onclick = () => {
        state.notes[step] = state.notes[step] === midi ? null : midi;
        updateNotes(); save(); unlockAudio().catch(() => {});
        requestRender(false, state.notes[step] === null ? false : midi);
      };
      button.onkeydown = e => {
        const moves = {ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,1],ArrowDown:[0,-1]};
        if (!moves[e.key]) return;
        e.preventDefault(); const [s,m] = moves[e.key];
        const target = document.querySelector(`.note[data-step="${clamp(step+s,0,15)}"][data-midi="${clamp(midi+m,60,72)}"]`);
        document.querySelectorAll('.note[tabindex="0"]').forEach(e => e.tabIndex = -1);
        target.tabIndex = 0; target.focus();
      };
      $('piano').append(button);
    }
  }
  $('steps').append(document.createElement('span'));
  for (let i=0; i<16; i++) { const step = document.createElement('span'); step.textContent = i % 4 === 0 ? String(i / 4 + 1) : '·'; $('steps').append(step); }
  updateNotes();
}
$('bpm').value = state.bpm;
$('bpm').oninput = e => {
  const value = Number(e.target.value);
  if (Number.isInteger(value) && value >= 40 && value <= 200) { state.bpm = value; save(); }
};
$('bpm').onchange = e => { state.bpm = clamp(Math.round(Number(e.target.value) || 96),40,200); e.target.value = state.bpm; save(); };
$('clear').onclick = () => { state.notes.fill(null); updateNotes(); save(); silence(); requestRender(true); };
$('reset-notes').onclick = () => { state.notes = [...PHRASE]; updateNotes(); save(); requestRender(true); };
$('export').onclick = () => {
  const url = URL.createObjectURL(new Blob([JSON.stringify(state,null,2)], {type:'application/json'}));
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'loam-soundgarden.json'; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url),1000);
};
$('import').onclick = () => $('import-file').click();
$('import-file').onchange = async e => {
  try {
    const file = e.target.files[0]; if (!file) return;
    if (file.size > 1000000) throw new Error('Session files must be smaller than 1 MB.');
    const imported = validateSession(JSON.parse(await file.text()));
    stop(); state = imported; comparing = false; path = []; selectedSeed = '';
    $('bpm').value = state.bpm; $('volume').value = state.volume;
    if (master) master.gain.setTargetAtTime(state.volume,context.currentTime,.02);
    updateField(); updateNotes(); renderSeeds(); renderFavorites(); save(); requestRender(true);
  } catch (error) { status(`Import failed: ${error.message}`); }
  finally { e.target.value = ''; }
};

buildPiano(); updateField(); renderFavorites(); refreshLibrary(); requestRender(true);
new ResizeObserver(updateField).observe($('pad'));
