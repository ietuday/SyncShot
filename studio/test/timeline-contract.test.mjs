import test from 'node:test';
import assert from 'node:assert/strict';
import { editedTimelinePayload, validateEditedTimeline } from '../timeline-contract.js';

const photos = new Map([['0001.jpg', 'one.jpg'], ['0002.png', 'two.png']]);
const payload = editedTimelinePayload([
  { image:'two.png', start:0, end:4, duration:4 },
  { image:'one.jpg', start:4, end:10, duration:6 },
], 'pan_left');

test('maps edited scene order to server-controlled uploaded filenames', () => {
  const plan = validateEditedTimeline(payload, photos, 10, { crossfade: 0.5 });
  assert.deepEqual(plan.scenes, [
    { image: '0002.png', duration: 4.5, motion: 'pan_left' },
    { image: '0001.jpg', duration: 6, motion: 'pan_left' },
  ]);
  assert.equal(plan.crossfade_seconds, 0.5);
  assert.equal(plan.scenes.reduce((n, s) => n + s.duration, 0) - 0.5, 10);
});
test('rejects unknown names, paths and unexpected properties', () => {
  assert.throws(() => validateEditedTimeline({version:1, scenes:[{ image:'../../etc/passwd', duration:10, motion:'static' }]}, photos, 10), /photo/);
  assert.throws(() => validateEditedTimeline({...payload, injected:1}, photos, 10), /Unexpected/);
});
test('rejects mismatched audio and duplicate filenames', () => {
  assert.throws(() => validateEditedTimeline(payload, photos, 15), /must match narration/);
  assert.throws(() => validateEditedTimeline(payload, new Map([['a','same.jpg'],['b','same.jpg']]), 10), /Duplicate/);
});
test('rejects invalid scene durations and motions', () => {
  assert.throws(() => validateEditedTimeline({version:1, scenes:[{image:'one.jpg',duration:-5,motion:'static'}]}, photos, 10), /duration/);
  assert.throws(() => validateEditedTimeline({version:1, scenes:[{image:'one.jpg',duration:10,motion:'bad'}]}, photos, 10), /motion/);
});
