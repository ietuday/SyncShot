import test from 'node:test';
import assert from 'node:assert/strict';
import { trimManualTimeline } from '../manual-preview.js';

const base = {
  fps: 24, width: 1280, height: 720, crossfade_seconds: 0.5,
  scenes: [
    { image:'a.jpg', motion:'zoom_in', duration: 6.5 },
    { image:'b.jpg', motion:'pan_left', duration: 6.5 },
    { image:'c.jpg', motion:'static', duration: 8 },
  ],
};
const runtime = t => t.scenes.reduce((sum, s) => sum + s.duration, 0) -
  t.crossfade_seconds * (t.scenes.length - 1);

test('cuts within a scene and retains edited order and crossfade', () => {
  const preview = trimManualTimeline(base, 10);
  assert.deepEqual(preview.scenes.map(s => s.image), ['a.jpg','b.jpg']);
  assert.deepEqual(preview.scenes.map(s => s.duration), [6.5, 4]);
  assert.equal(runtime(preview), 10);
  assert.equal(base.scenes.length, 3);
});
test('handles a preview ending exactly on a scene boundary', () => {
  const preview = trimManualTimeline(base, 6);
  assert.deepEqual(preview.scenes.map(s => s.duration), [6]);
  assert.equal(runtime(preview), 6);
});
test('extends previous scene when preview ends inside an unrenderable fade', () => {
  const preview = trimManualTimeline(base, 6.25);
  assert.equal(preview.scenes.length, 1);
  assert.equal(runtime(preview), 6.25);
});
test('does not expand timelines shorter than the preview', () => {
  assert.equal(runtime(trimManualTimeline(base, 30)), 20);
});
test('rejects invalid preview requests', () => {
  assert.throws(() => trimManualTimeline(base, -2), /positive/);
  assert.throws(() => trimManualTimeline({...base, scenes:[]}), /valid timeline/);
});
