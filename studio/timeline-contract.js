/**
 * Phase 4 timeline contract. Never trust browser-provided filesystem paths.
 * Scene identifiers are original upload names, translated to uploaded paths
 * only after the Node upload handler has stored the files.
 */
const motions = new Set(['static', 'zoom_in', 'zoom_out', 'pan_left', 'pan_right']);
const finite = n => typeof n === 'number' && Number.isFinite(n);
export function validateEditedTimeline(input, imageNames, audioSeconds, options = {}) {
  if (!input || typeof input !== 'object' || Array.isArray(input) ||
      input.version !== 1 || !Array.isArray(input.scenes)) {
    throw new Error('Timeline must contain version 1 and a scenes array.');
  }
  if (Object.keys(input).some(key => !['version', 'scenes'].includes(key))) {
    throw new Error('Unexpected timeline property.');
  }
  if (input.scenes.length < 1 || input.scenes.length > 500) {
    throw new Error('Timeline requires 1–500 scenes.');
  }
  const fade = options.crossfade ?? 0;
  if (!finite(fade) || fade < 0 || fade > 1) throw new Error('Invalid crossfade.');
  if (!finite(audioSeconds) || audioSeconds <= 0) throw new Error('Invalid narration duration.');
  const byName = new Map();
  for (const [stored, original] of imageNames) {
    if (byName.has(original)) {
      throw new Error('Duplicate photo names are ambiguous in an edited timeline; rename them before uploading.');
    }
    byName.set(original, stored);
  }
  const scenes = input.scenes.map((scene, index) => {
    if (!scene || typeof scene !== 'object' || Array.isArray(scene) ||
        Object.keys(scene).some(key => !['image', 'duration', 'motion'].includes(key)) ||
        typeof scene.image !== 'string' || !byName.has(scene.image)) {
      throw new Error(`Scene ${index + 1}: photo does not match an uploaded image.`);
    }
    if (!finite(scene.duration) || scene.duration < 0.5 || scene.duration > 3600) {
      throw new Error(`Scene ${index + 1}: duration must be 0.5–3600 seconds.`);
    }
    if (!motions.has(scene.motion)) {
      throw new Error(`Scene ${index + 1}: invalid motion.`);
    }
    if (index < input.scenes.length - 1 && scene.duration <= 0.001) {
      throw new Error(`Scene ${index + 1}: too short for crossfade.`);
    }
    return {
      image: byName.get(scene.image),
      // Manual Go timelines specify encoded duration including outgoing overlap.
      duration: scene.duration + (index < input.scenes.length - 1 ? fade : 0),
      motion: scene.motion,
    };
  });
  const duration = input.scenes.reduce((sum, scene) => sum + scene.duration, 0);
  if (Math.abs(duration - audioSeconds) > 0.06) {
    throw new Error(`Edited video length ${duration.toFixed(2)}s must match narration ${audioSeconds.toFixed(2)}s (within 0.06s). Adjust scene durations before rendering.`);
  }
  return { fps: options.fps ?? 24, width: options.width ?? 1280,
    height: options.height ?? 720, crossfade_seconds: fade, scenes };
}

export function editedTimelinePayload(scenes, defaultMotion = 'zoom_in') {
  return {
    version: 1,
    scenes: scenes.map(scene => ({
      image: scene.image,
      duration: Number((scene.duration ?? scene.end - scene.start).toFixed(2)),
      motion: defaultMotion,
    })),
  };
}
