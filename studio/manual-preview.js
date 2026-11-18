/**
 * Trim a validated Go cinematic timeline to a short prefix. The source timeline
 * stores each outgoing crossfade as additional encoded duration. Reconstruct
 * that overlap only between the scenes actually retained for the preview.
 */
export function trimManualTimeline(timeline, requestedSeconds = 10) {
  if (!timeline || !Array.isArray(timeline.scenes) || timeline.scenes.length === 0 ||
      !Number.isFinite(requestedSeconds) || requestedSeconds <= 0) {
    throw new Error('A valid timeline and positive preview duration are required.');
  }
  const fade = timeline.crossfade_seconds || 0;
  const visible = timeline.scenes.map((scene, index) => ({
    image: scene.image, motion: scene.motion,
    duration: scene.duration - (index < timeline.scenes.length - 1 ? fade : 0),
  }));
  if (visible.some(scene => !Number.isFinite(scene.duration) || scene.duration <= 0)) {
    throw new Error('Timeline contains an invalid scene duration.');
  }
  const total = visible.reduce((sum, scene) => sum + scene.duration, 0);
  const limit = Math.min(requestedSeconds, total);
  let remaining = limit;
  const selected = [];
  for (const scene of visible) {
    if (remaining <= 0.000001) break;
    const length = Math.min(remaining, scene.duration);
    selected.push({ ...scene, duration: length });
    remaining -= length;
  }
  // A final scene shorter than the crossfade cannot be encoded by Go. Extend
  // the previous scene across that fractional tail instead.
  if (selected.length > 1 && selected.at(-1).duration <= fade) {
    const trailing = selected.pop();
    selected.at(-1).duration += trailing.duration;
  }
  const scenes = selected.map((scene, index) => ({
    ...scene,
    duration: scene.duration + (index < selected.length - 1 ? fade : 0),
  }));
  return { ...timeline, scenes };
}
