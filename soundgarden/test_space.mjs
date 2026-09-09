import assert from 'node:assert/strict';
import {DEFAULT, randomPlane, atPosition, validVector, validAxes, validNotes} from './web/space.js';
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
assert(!validAxes([[1,0],[0,1]]));
assert(!validVector(Array(10).fill(NaN)));
assert(!validNotes(Array(16).fill(false)));
assert(!validNotes(Array(15).fill(60)));
assert(validNotes(Array(16).fill(null)));
console.log('PASS: 100 exploration planes, bounded corners, exact recentering, input validation');
