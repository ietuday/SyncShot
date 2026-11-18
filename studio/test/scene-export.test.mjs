import test from 'node:test';
import assert from 'node:assert/strict';
import { scenePlanCSV } from '../scene-export.js';

test('exports scene timestamps, photo names, and captions', () => {
  const csv = scenePlanCSV([{ start: 0, end: 8.5, image: 'photo.jpg', narration: ['Hello', 'world'] }], true);
  assert.match(csv, /^\uFEFF"Scene","Start \(s\)","End \(s\)","Photo","Narration"/);
  assert.match(csv, /"1","0.00","8.50","photo.jpg","Hello \| world"/);
});
test('quotes commas and neutralises spreadsheet formula input', () => {
  const csv = scenePlanCSV([{ start: 0, end: 1, image: '=2+2,"test"' }], false);
  assert.match(csv, /"'=2\+2,""test"""/);
});
test('omits captions when off', () => {
  assert.doesNotMatch(scenePlanCSV([{ start: 0, end: 1, image: 'a.png' }]), /Narration/);
});
