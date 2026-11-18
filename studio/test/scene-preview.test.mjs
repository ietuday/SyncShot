import test from 'node:test';
import assert from 'node:assert/strict';
import { sceneAtTime, clampPreviewTime } from '../scene-preview.js';

const scenes = [
  { image: 'a.png', start: 0, end: 4 },
  { image: 'b.png', start: 4, end: 10 },
];
test('preview maps playhead to the active scene and progress', () => {
  assert.equal(sceneAtTime(scenes, 0).index, 0);
  assert.equal(sceneAtTime(scenes, 4).index, 1);
  assert.equal(sceneAtTime(scenes, 7).progress, 0.5);
  assert.equal(sceneAtTime(scenes, 10).index, 1);
});
test('invalid input does not select a scene', () => {
  assert.equal(sceneAtTime([], 0), null);
  assert.equal(sceneAtTime(scenes, NaN), null);
});
test('playhead clamps after timeline edits', () => {
  assert.equal(clampPreviewTime(50, scenes), 10);
  assert.equal(clampPreviewTime(-1, scenes), 0);
});
