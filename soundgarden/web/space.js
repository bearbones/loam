// Shared, dependency-free exploration math. A position is always a full recipe.
export const DEFAULT = [.64, .52, .51, .4, .15, .2, .12, .2, .18, .2];
export const DIMENSIONS = ['Material', 'Ring', 'Brightness', 'Damping', 'Beating', 'Mallet', 'Softness', 'Hollow', 'Bloom', 'Drive'];
export const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));
export function randomPlane(random = Math.random) {
  const normal = () => Math.sqrt(-2 * Math.log(Math.max(random(), 1e-9))) * Math.cos(2 * Math.PI * random());
  const normalize = a => { const n = Math.hypot(...a); return a.map(v => v / n); };
  const u = normalize(Array.from({length: 10}, normal));
  let v = Array.from({length: 10}, normal);
  const dot = v.reduce((s, x, i) => s + x * u[i], 0);
  v = normalize(v.map((x, i) => x - dot * u[i]));
  return [u, v];
}
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
export function validAxes(a) {
  return Array.isArray(a) && a.length === 2 && a.every(v => Array.isArray(v) && v.length === 10 && v.every(x => typeof x === 'number' && Number.isFinite(x) && Math.abs(x) <= 1.001)) && a.every(v => Math.abs(Math.hypot(...v) - 1) < .01) && Math.abs(a[0].reduce((s, x, i) => s + x * a[1][i], 0)) < .01;
}
export function validNotes(notes) {
  return Array.isArray(notes) && notes.length === 16 && notes.every(n => n === null || (Number.isInteger(n) && n >= 60 && n <= 72));
}
