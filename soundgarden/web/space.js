// Shared, dependency-free exploration math. A position is always a full recipe.
export const DEFAULT = [.64, .52, .51, .4, .15, .2, .12, .2, .18, .2];
export const DIMENSIONS = ['Material', 'Ring', 'Brightness', 'Damping', 'Beating', 'Mallet', 'Softness', 'Hollow', 'Bloom', 'Drive'];
export const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));
const normal = random => Math.sqrt(-2 * Math.log(Math.max(random(), 1e-9))) * Math.cos(2 * Math.PI * random());
const norm = a => Math.hypot(...a);
export const dimsPerAxis = spread => 1 + Math.round(clamp(spread, 0, 1) * (DIMENSIONS.length - 1));
function shuffled(n, random) {
  const order = Array.from({length: n}, (_, i) => i);
  for (let i = n - 1; i > 0; i--) { const j = Math.floor(random() * (i + 1)); [order[i], order[j]] = [order[j], order[i]]; }
  return order;
}
function axis(spread, k, weights, random, exclude) {
  const order = shuffled(weights.length, random).filter(i => i !== exclude).slice(0, k);
  const vector = Array(weights.length).fill(0);
  for (const i of order) vector[i] = (random() < .5 ? -1 : 1) * ((1 - spread) * Math.abs(normal(random)) + spread) * weights[i];
  const n = norm(vector);
  return n > 0 ? vector.map(x => x / n) : null;
}
// Mirrors soundgarden/field.py spread_plane. spread 0: one dimension per axis;
// spread 1: every dimension, near-even magnitudes. weights rescale dimensions.
export function spreadPlane(spread = 1, weights = null, random = Math.random) {
  spread = clamp(Number.isFinite(spread) ? spread : 1, 0, 1);
  const w = validWeights(weights) ? weights : Array(DIMENSIONS.length).fill(1);
  const k = dimsPerAxis(spread);
  for (let attempt = 0; attempt < 256; attempt++) {
    const u = axis(spread, k, w, random, null);
    if (!u) continue;
    const strongest = u.reduce((best, x, i) => Math.abs(x) > Math.abs(u[best]) ? i : best, 0);
    let v = axis(spread, k, w, random, k === 1 ? strongest : null);
    if (!v) continue;
    const dot = v.reduce((s, x, i) => s + x * u[i], 0);
    v = v.map((x, i) => x - dot * u[i]);
    const n = norm(v);
    if (n > 1e-3) return [u, v.map(x => x / n)];
  }
  throw new Error('Could not draw an orthogonal plane.');
}
export const randomPlane = (random = Math.random) => spreadPlane(1, null, random);
export function atPosition(center, axes, position, radius) {
  return center.map((value, i) => {
    const offset = 3 * radius * (position[0] * axes[0][i] + position[1] * axes[1][i]);
    const odds = Math.exp(offset);
    return value * odds / (1 - value + value * odds);
  });
}
export function validVector(v) {
  return Array.isArray(v) && v.length === 10 && v.every(x => typeof x === 'number' && Number.isFinite(x) && x >= 0 && x <= 1);
}
export function validWeights(w) {
  return Array.isArray(w) && w.length === 10 && w.every(x => typeof x === 'number' && Number.isFinite(x) && x > 0);
}
export function validAxes(a) {
  return Array.isArray(a) && a.length === 2 && a.every(v => Array.isArray(v) && v.length === 10 && v.every(x => typeof x === 'number' && Number.isFinite(x) && Math.abs(x) <= 1.001)) && a.every(v => Math.abs(Math.hypot(...v) - 1) < .01) && Math.abs(a[0].reduce((s, x, i) => s + x * a[1][i], 0)) < .01;
}
export function validNotes(notes) {
  return Array.isArray(notes) && notes.length === 16 && notes.every(n => n === null || (Number.isInteger(n) && n >= 60 && n <= 72));
}
