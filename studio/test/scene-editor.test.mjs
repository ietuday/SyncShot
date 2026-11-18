import test from 'node:test';
import assert from 'node:assert/strict';
import { recalculateScenes, reorderScenes, setSceneDuration } from '../scene-editor.js';

const scenes = [
  { image: 'first.png', start: 0, end: 5 },
  { image: 'second.png', start: 5, end: 10 },
  { image: 'third.png', start: 10, end: 15 },
];
test('reordering preserves durations and recomputes timestamps', () => {
  const result = reorderScenes(scenes, 0, 2);
  assert.deepEqual(result.map(s => s.image), ['second.png', 'third.png', 'first.png']);
  assert.deepEqual(result.map(s => [s.start, s.end]), [[0,5],[5,10],[10,15]]);
  assert.equal(scenes[0].image, 'first.png');
});
test('editing duration updates subsequent timestamps', () => {
  const result = setSceneDuration(scenes, 1, 8.5);
  assert.deepEqual(result.map(s => [s.start, s.end]), [[0,5],[5,13.5],[13.5,18.5]]);
});
test('invalid edits leave scenes unchanged', () => {
  assert.equal(reorderScenes(scenes, -1, 1), scenes);
  assert.equal(setSceneDuration(scenes, 0, -1), scenes);
});
