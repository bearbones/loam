import assert from 'node:assert/strict';
import {DEFAULT, randomPlane, spreadPlane, dimsPerAxis, atPosition, validVector, validAxes, validNotes, validWeights} from './web/space.js';
for (let i=0; i<100; i++) {
  const axes = randomPlane();
  assert(validAxes(axes));
  const centered = atPosition(DEFAULT,axes,[0,0],2);
  centered.forEach((v,i) => assert(Math.abs(v-DEFAULT[i]) < 1e-15));
  for (const position of [[-1,-1],[1,1],[-1,1],[1,-1]]) {
    const vector = atPosition(DEFAULT,axes,position,2);
    assert(validVector(vector));
    const recentered = atPosition(vector,randomPlane(),[0,0],2);
    vector.forEach((v,i) => assert(Math.abs(v-recentered[i]) < 1e-15));
  }
}
// Field blend: k dimensions per axis, from one (two explored) to all ten, near-even at full blend.
const support = v => v.filter(x => Math.abs(x) > 1e-9).length;
for (let k = 1; k <= 10; k++) {
  const spread = (k - 1) / 9;
  assert.equal(dimsPerAxis(spread), k, `slider step ${k} must map back to ${k} dimensions`);
  for (let i = 0; i < 200; i++) {
    const [u, v] = spreadPlane(spread);
    assert(validAxes([u, v]));
    assert.equal(support(u), k, 'first axis touches exactly k dimensions');
    assert(support(v) >= k && support(v) <= Math.min(10, 2 * k), 'second axis stays within the union after orthogonalization');
    if (k === 1) assert(u.findIndex(x => x !== 0) !== v.findIndex(x => x !== 0), 'single dimensions differ');
    if (k === 10) assert(Math.min(...u.map(Math.abs)) * Math.sqrt(10) > .3, 'full blend is close to even');
  }
}
assert.equal(dimsPerAxis(.5), 6, 'midpoint rounds half up, matching Python');
const weighted = spreadPlane(1, [4,4,4,4,4,.25,.25,.25,.25,.25]);
assert(Math.min(...weighted[0].slice(0,5).map(Math.abs)) > Math.max(...weighted[0].slice(5).map(Math.abs)) * 5, 'weights scale dimensions before normalization');
assert(validWeights([1,1,1,1,1,1,1,1,1,1]) && !validWeights([0,1,1,1,1,1,1,1,1,1]) && !validWeights([1,1]));
assert(!validAxes([[1,0],[0,1]]));
assert(!validVector(Array(10).fill(NaN)));
assert(!validNotes(Array(16).fill(false)));
assert(!validNotes(Array(15).fill(60)));
assert(validNotes(Array(16).fill(null)));
console.log('PASS: 100 exploration planes, 2000 blended planes at every slider step, bounded corners, exact recentering, input validation');
