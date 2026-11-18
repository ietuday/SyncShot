// Pure timeline lookup for the browser-only preview. The last frame belongs to the last scene.
export function sceneAtTime(scenes, seconds) {
  if (!Array.isArray(scenes) || scenes.length === 0 || !Number.isFinite(seconds)) return null;
  const total = scenes[scenes.length - 1].end;
  if (!Number.isFinite(total) || total <= 0) return null;
  const time = Math.max(0, Math.min(seconds, total));
  const index = time >= total ? scenes.length - 1 :
    scenes.findIndex(scene => time >= scene.start && time < scene.end);
  if (index < 0) return null;
  const scene = scenes[index];
  const duration = Math.max(0.001, scene.end - scene.start);
  return { scene, index, progress: Math.max(0, Math.min(1, (time - scene.start) / duration)) };
}

export function clampPreviewTime(time, scenes) {
  const total = scenes?.at(-1)?.end ?? 0;
  return Number.isFinite(time) && Number.isFinite(total) ? Math.max(0, Math.min(time, total)) : 0;
}
