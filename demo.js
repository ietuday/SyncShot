const byId = id => document.getElementById(id);
const audio = new Audio();
const formats = {
  landscape: { width: 1280, height: 720 },
  portrait: { width: 720, height: 1280 },
  square: { width: 720, height: 720 },
};
const selectedFormat = () => formats[byId('format').value] ?? formats.landscape;
const exportResolutions = {
  480: { edge: 480, longEdge: 854, bitrate: 1200000 },
  720: { edge: 720, longEdge: 1280, bitrate: 2500000 },
  1080: { edge: 1080, longEdge: 1920, bitrate: 5000000 },
};

function exportDimensions(format, resolution) {
  const { edge, longEdge, bitrate } = resolution;
  if (format === 'portrait') return { width: edge, height: longEdge, bitrate };
  if (format === 'square') return { width: edge, height: edge, bitrate };
  return { width: longEdge, height: edge, bitrate };
}

function applyPreviewFormat() {
  const frame = byId('frame');
  const { width, height } = selectedFormat();
  frame.style.aspectRatio = width + ' / ' + height;
  frame.style.maxWidth = Math.round(520 * width / height) + 'px';
}

byId('format').addEventListener('change', applyPreviewFormat);
function cropPosition(framing) {
  return framing === 'cover'
    ? byId('crop-position').value.split(',').map(Number)
    : [0.5, 0.5];
}

function applyPreviewFraming() {
  const framing = byId('framing').value;
  const [x, y] = cropPosition(framing);
  for (const control of document.querySelectorAll(".photo-crop")) control.hidden = framing !== "cover";
  byId('crop-control').hidden = framing !== 'cover';
  const frame = byId('frame');
  frame.style.setProperty('--photo-fit', framing);
  frame.style.setProperty('--photo-position', (x * 100) + '% ' + (y * 100) + '%');
}

byId('framing').addEventListener('change', () => {
  stopPreview();
  applyPreviewFraming();
});
byId('crop-position').addEventListener('change', applyPreviewFraming);
applyPreviewFraming();

function photoBounds(sourceWidth, sourceHeight, frameWidth, frameHeight, framing, position) {
  const widthRatio = frameWidth / sourceWidth;
  const heightRatio = frameHeight / sourceHeight;
  const scale = framing === 'cover'
    ? Math.max(widthRatio, heightRatio)
    : Math.min(widthRatio, heightRatio);
  const width = sourceWidth * scale;
  const height = sourceHeight * scale;
  return { x: (frameWidth - width) * position[0], y: (frameHeight - height) * position[1], width, height };
}
applyPreviewFormat();
const sample = [
  { name: 'A road through the hills', color: '#325647' },
  { name: 'The river crossing', color: '#214e68' },
  { name: 'A quiet evening', color: '#634137' },
];
let duration = 24;
let photos = [];
let captions = [];
let captionRequest = 0;
const sampleSrt = `1
00:00:00,500 --> 00:00:04,000
The road climbs into the hills.

2
00:00:08,000 --> 00:00:12,000
A river runs through the valley.

3
00:00:16,500 --> 00:00:21,000
As evening falls, the road grows quiet.`;
let timer;

let previewRequest = 0;
function stopPreview() {
  previewRequest++;
  cancelAnimationFrame(timer);
  audio.pause();
  byId('player').hidden = true;
}

function parseSrt(source) {
  const normalized = source.replace(/^\uFEFF/, '').replace(/\r\n?/g, '\n').trim();
  if (!normalized) throw new Error('The SRT file is empty.');
  const timing = /^(\d{2,}:[0-5]\d:[0-5]\d,\d{3})\s+-->\s+(\d{2,}:[0-5]\d:[0-5]\d,\d{3})(?:\s+.*)?$/;
  function seconds(value) {
    const [hours, minutes, secs, millis] = value.split(/[:,]/).map(Number);
    return hours * 3600 + minutes * 60 + secs + millis / 1000;
  }
  let previousEnd = 0;
  return normalized.split(/\n[ \t]*\n+/).map((block, index) => {
    const lines = block.split('\n');
    const position = /^\d+$/.test(lines[0].trim()) ? 1 : 0;
    const times = lines[position]?.trim().match(timing);
    const text = lines.slice(position + 1).join('\n').trim();
    if (!times || !text) throw new Error('Invalid SRT caption at block ' + (index + 1) + '.');
    const start = seconds(times[1]);
    const end = seconds(times[2]);
    if (!Number.isFinite(end) || end <= start || start < previousEnd) {
      throw new Error('Invalid or overlapping SRT times at block ' + (index + 1) + '.');
    }
    previousEnd = end;
    return { start, end, text };
  });
}

function captionAt(cues, elapsed) {
  let start = 0;
  let end = cues.length;
  while (start < end) {
    const mid = Math.floor((start + end) / 2);
    if (cues[mid].end <= elapsed) start = mid + 1;
    else end = mid;
  }
  return cues[start]?.start <= elapsed ? cues[start].text : '';
}

function paintCaption(context, text, width, height) {
  if (!text) return;
  const maxWidth = width * 0.85;
  context.save();
  const scale = Math.min(width, height) / 720;
  context.font = '600 ' + Math.round(32 * scale) + 'px system-ui';
  context.textAlign = 'center';
  context.textBaseline = 'middle';
  const lines = [];
  for (const paragraph of text.split('\n')) {
    let line = '';
    for (const word of paragraph.split(/\s+/)) {
      const candidate = line ? line + ' ' + word : word;
      if (line && context.measureText(candidate).width > maxWidth) {
        lines.push(line);
        line = word;
      } else {
        line = candidate;
      }
    }
    lines.push(line);
  }
  const spacing = 40 * scale;
  const firstY = height - 45 * scale - (lines.length - 1) * spacing;
  lines.forEach((line, index) => {
    const y = firstY + index * spacing;
    const boxWidth = Math.min(maxWidth, context.measureText(line).width) + 24 * scale;
    context.fillStyle = 'rgba(0, 0, 0, 0.78)';
    context.fillRect((width - boxWidth) / 2, y - spacing / 2, boxWidth, spacing);
    context.fillStyle = 'white';
    context.fillText(line, width / 2, y, maxWidth);
  });
  context.restore();
}

function useCaptions(content) {
  captions = parseSrt(content);
  byId('caption-status').textContent = captions.length + ' captions ready.';
}

byId('captions').addEventListener('change', async event => {
  const request = ++captionRequest;
  stopPreview();
  captions = [];
  const file = event.target.files[0];
  const status = byId('caption-status');
  status.textContent = file ? 'Reading captions…' : 'Subtitles off.';
  if (!file) return;
  try {
    if (file.size > 1024 * 1024) throw new Error('Use an SRT file up to 1 MB.');
    const content = await file.text();
    if (request === captionRequest) useCaptions(content);
  } catch (error) {
    if (request === captionRequest) status.textContent = error.message;
  }
});

byId('sample-captions').addEventListener('click', () => {
  stopPreview();
  ++captionRequest;
  byId('captions').value = '';
  useCaptions(sampleSrt);
});

function zoomAt(scene, elapsed, motion) {
  const fraction = Math.max(0, Math.min(1, (elapsed - scene.start) / (scene.end - scene.start)));
  if (motion === 'zoom-in') return 1 + fraction * 0.15;
  if (motion === 'zoom-out') return 1.15 - fraction * 0.15;
  return 1;
}

function frameAt(scenes, elapsed, transition) {
  const index = scenes.findIndex(scene => elapsed < scene.end);
  const current = scenes[index < 0 ? scenes.length - 1 : index];
  if (transition !== 'fade' || index < 1) return { current, alpha: 1 };
  const previous = scenes[index - 1];
  const seconds = Math.min(0.5, (current.end - current.start) / 2, (previous.end - previous.start) / 2);
  const alpha = Math.min(1, Math.max(0, (elapsed - current.start) / seconds));
  return { current, previous: alpha < 1 ? previous : undefined, alpha };
}

function defaultPhotoSeconds(index) {
  const step = duration * 100 / photos.length;
  return ((Math.round((index + 1) * step) - Math.round(index * step)) / 100).toFixed(2);
}

function showPhotoOrder(focusIndex, direction) {
  const list = byId('photo-order');
  list.hidden = !photos.length;
  byId("custom-pacing").disabled = !photos.length;
  if (!photos.length && byId("pacing").value === "custom") byId("pacing").value = "auto";
  list.replaceChildren(...photos.map((photo, index) => {
    const row = document.createElement('li');
    const label = document.createElement('span');
    label.textContent = (index + 1) + '. ' + photo.name;
    const actions = document.createElement('div');
    for (const [delta, arrow, name] of [[-1, '↑', 'up'], [1, '↓', 'down']]) {
      const target = index + delta;
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = arrow;
      button.setAttribute('aria-label', 'Move ' + photo.name + ' ' + name);
      button.disabled = target < 0 || target >= photos.length;
      button.addEventListener('click', () => {
        stopPreview();
        [photos[index], photos[target]] = [photos[target], photos[index]];
        showPhotoOrder(target, delta);
        if (!byId('plan').disabled) showPlan();
      });
      actions.append(button);
    }
    const crop = document.createElement('label');
    crop.className = 'photo-crop';
    crop.hidden = byId('framing').value !== 'cover';
    crop.textContent = 'Crop for ' + photo.name;
    const position = byId('crop-position').cloneNode(true);
    position.removeAttribute('id');
    position.add(new Option('Use global crop', ''), 0);
    position.value = photo.position ?? '';
    position.addEventListener('change', () => {
      photo.position = position.value;
      stopPreview();
    });
    crop.append(position);

    const time = document.createElement('label');
    time.hidden = byId('pacing').value !== 'custom';
    time.className = 'photo-time';
    time.textContent = 'Seconds for ' + photo.name;
    const input = document.createElement('input');
    input.type = 'number';
    input.step = '0.01';
    input.min = '0.05';
    input.value = photo.seconds ?? defaultPhotoSeconds(index);
    input.addEventListener('input', () => {
      photo.seconds = input.value;
      stopPreview();
      if (!byId('plan').disabled) showPlan();
    });
    time.append(input);
    row.append(label, actions, crop, time);
    return row;
  }));
  if (focusIndex !== undefined) {
    const buttons = list.children[focusIndex].querySelectorAll('button');
    const preferred = direction < 0 ? buttons[0] : buttons[1];
    const fallback = direction < 0 ? buttons[1] : buttons[0];
    (preferred.disabled ? fallback : preferred).focus();
  }
}

function buildPlan() {
  const sources = photos.length ? photos : sample;
  const pacing = byId('pacing').value;
  if (pacing === 'custom') {
    let end = 0;
    const scenes = photos.map((photo, index) => {
      const seconds = Number(photo.seconds ?? defaultPhotoSeconds(index));
      if (!Number.isFinite(seconds) || seconds < 0.05) throw new Error('Enter at least 0.05 seconds for each photo.');
      const start = end;
      end += seconds;
      return { photo, start, end };
    });
    if (Math.abs(end - duration) > 0.011 || scenes.at(-1).start >= duration) {
      throw new Error('Photo times total ' + end.toFixed(2) + ' s. Match the narration duration of ' + duration.toFixed(2) + ' s.');
    }
    scenes.at(-1).end = duration;
    return scenes;
  }
  const count = Math.min(500, pacing === 'auto' ? sources.length : Math.ceil(duration / Number(pacing)));
  return Array.from({ length: count }, (_, index) => ({
    photo: sources[index % sources.length],
    start: index * duration / count,
    end: (index + 1) * duration / count,
  }));
}

function showPlan() {
  let scenes;
  try {
    scenes = buildPlan();
  } catch (error) {
    document.querySelector('table').hidden = true;
    byId('status').textContent = error.message;
    return null;
  }
  document.querySelector('tbody').replaceChildren(...scenes.map((scene, index) => {
    const row = document.createElement('tr');
    for (const value of [index + 1, scene.start.toFixed(2) + ' s', scene.end.toFixed(2) + ' s', scene.photo.name]) {
      row.insertCell().textContent = value;
    }
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'preview-scene';
    button.textContent = 'Play';
    button.setAttribute('aria-label', 'Preview scene ' + (index + 1));
    button.addEventListener('click', () => {
      if (!byId('preview').disabled) void preview(false, scenes, scene);
    });
    row.insertCell().append(button);
    return row;
  }));
  document.querySelector('table').hidden = false;
  byId('status').textContent = scenes.length + ' scenes across ' + duration.toFixed(1) + ' seconds.';
  return scenes;
}

byId('audio').addEventListener('change', () => {
  stopPreview();
  if (audio.src) URL.revokeObjectURL(audio.src);
  const file = byId('audio').files[0];
  byId('preview').disabled = byId('preview-ending').disabled = byId('inspect-timeline').disabled = Boolean(file);
  byId('plan').disabled = byId('download-plan').disabled = Boolean(file);
  byId('export').disabled = Boolean(file);
  if (file) audio.src = URL.createObjectURL(file);
  else {
    audio.removeAttribute('src');
    audio.load();
    duration = 24;
    showPhotoOrder();
    showPlan();
  }
});

audio.addEventListener('loadedmetadata', () => {
  if (!Number.isFinite(audio.duration) || audio.duration <= 0) {
    byId('status').textContent = 'Choose an audio file with a known duration.';
    return;
  }
  duration = audio.duration;
  showPhotoOrder();
  byId('preview').disabled = byId('preview-ending').disabled = byId('inspect-timeline').disabled = byId('plan').disabled = byId('download-plan').disabled = byId('export').disabled = false;
  showPlan();
});
audio.addEventListener('error', () => {
  if (byId('audio').files.length) byId('status').textContent = 'This browser could not read the selected audio.';
});

byId('photos').addEventListener('change', () => {
  stopPreview();
  for (const photo of photos) URL.revokeObjectURL(photo.url);
  photos = Array.from(byId('photos').files, file => ({ name: file.name, url: URL.createObjectURL(file) }));
  showPhotoOrder();
  if (!byId('plan').disabled) showPlan();
});
byId('pacing').addEventListener('change', () => {
  stopPreview();
  showPhotoOrder();
  if (!byId('plan').disabled) showPlan();
});
byId('plan').addEventListener('click', showPlan);
function sceneCSV(scenes) {
  const field = value => {
    const text = String(value);
    const safe = /^[\s\u0000-\u001f]*[=+@-]/u.test(text) || /^[\t\r\n]/u.test(text)
      ? "'" + text : text;
    return '"' + safe.replaceAll('"', '""') + '"';
  };
  const rows = [['Scene', 'Start (s)', 'End (s)', 'Duration (s)', 'Photo']];
  for (const [index, scene] of scenes.entries()) {
    rows.push([
      index + 1, scene.start.toFixed(3), scene.end.toFixed(3),
      (scene.end - scene.start).toFixed(3), scene.photo.name,
    ]);
  }
  return '\ufeff' + rows.map(row => row.map(field).join(',')).join('\r\n') + '\r\n';
}

byId('download-plan').addEventListener('click', () => {
  const scenes = showPlan();
  if (!scenes) return;
  const csv = new Blob([sceneCSV(scenes)], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(csv);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'syncshot-scene-plan.csv';
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  byId('status').textContent = 'Scene plan CSV downloaded (' + scenes.length + ' scenes).';
});
function readTitleCards() {
  return {
    opening: byId('opening-title').value.trim(),
    ending: byId('ending-title').value.trim(),
  };
}

function titleAt(cards, elapsed, total) {
  const length = Math.min(2, total / (cards.opening && cards.ending ? 2 : 1));
  if (elapsed < length && cards.opening) return cards.opening;
  if (elapsed >= total - length) return cards.ending;
  return '';
}

function paintTitle(context, title, width, height) {
  if (!title) return;
  context.save();
  context.fillStyle = 'rgba(0, 0, 0, 0.56)';
  context.fillRect(0, 0, width, height);
  context.fillStyle = 'white';
  context.textAlign = 'center';
  context.textBaseline = 'middle';
  const size = Math.round(Math.min(width, height) * 0.075);
  context.font = '700 ' + size + 'px system-ui';
  const maxWidth = width * 0.84;
  const lines = [];
  let line = '';
  for (const word of title.split(/\s+/)) {
    const next = line ? line + ' ' + word : word;
    if (line && context.measureText(next).width > maxWidth) {
      lines.push(line);
      line = word;
    } else line = next;
  }
  lines.push(line);
  const lineHeight = size * 1.2;
  lines.forEach((text, index) => {
    context.fillText(text, width / 2, height / 2 + (index - (lines.length - 1) / 2) * lineHeight, maxWidth);
  });
  context.restore();
}

async function preview(ending = false, plannedScenes, selectedScene, inspect = false) {
  stopPreview();
  const request = previewRequest;
  const scenes = plannedScenes ?? showPlan();
  if (!scenes) return;
  const frame = byId('frame');
  const motion = byId('motion').value;
  const transition = byId('transition').value;
  const cues = captions;
  const cards = readTitleCards();
  const segmentLength = selectedScene ? selectedScene.end - selectedScene.start : duration;
  const limit = Math.min(segmentLength, ending ? 3 : 10);
  const offset = selectedScene?.start ?? (ending ? duration - limit : 0);
  const end = offset + limit;
  const hasAudio = Boolean(byId('audio').files.length);
  const player = byId('player');
  player.hidden = false;
  if (selectedScene || inspect) player.focus();
  const slider = byId('preview-position');
  slider.max = duration;
  const play = byId('preview-play');
  const updatePlayLabel = playing => {
    play.textContent = playing ? 'Pause' : 'Play from here';
  };
  let isPlaying = false;
  let playbackRequest = 0;
  function createLayer() {
    const layer = document.createElement('div');
    layer.className = 'preview-layer';
    return { layer };
  }
  const incoming = createLayer();
  const outgoing = createLayer();
  const caption = document.createElement('div');
  caption.className = 'preview-caption';
  caption.hidden = true;
  const card = document.createElement('div');
  card.className = 'preview-title';
  card.hidden = true;
  frame.replaceChildren(outgoing.layer, incoming.layer, card, caption);

  function drawLayer(slot, scene, elapsed) {
    if (slot.scene !== scene) {
      slot.scene = scene;
      slot.layer.style.backgroundColor = scene.photo.color ?? '#19362d';
      slot.subject = document.createElement(scene.photo.url ? 'img' : 'span');
      if (scene.photo.url) {
        slot.subject.src = scene.photo.url;
        slot.subject.alt = scene.photo.name;
        if (scene.photo.position && byId('framing').value === 'cover') {
          const [x, y] = scene.photo.position.split(',').map(Number);
          slot.subject.style.objectPosition = (x * 100) + '% ' + (y * 100) + '%';
        }
      } else {
        slot.subject.textContent = scene.photo.name;
      }
      slot.layer.replaceChildren(slot.subject);
    }
    slot.subject.style.transform = 'scale(' + zoomAt(scene, elapsed, motion) + ')';
  }

  function renderPreview(elapsed, holdScene = false) {
    const frameTime = holdScene && elapsed === selectedScene?.end
      ? Math.max(offset, elapsed - 0.000001)
      : elapsed;
    const title = titleAt(cards, frameTime, duration);
    if (card.textContent !== title) card.textContent = title;
    card.hidden = !title;
    const { current, previous, alpha } = frameAt(scenes, frameTime, transition);
    drawLayer(incoming, current, frameTime);
    incoming.layer.style.opacity = alpha;
    incoming.layer.setAttribute('aria-hidden', 'false');
    outgoing.layer.hidden = !previous;
    outgoing.layer.setAttribute('aria-hidden', 'true');
    if (previous) drawLayer(outgoing, previous, previous.end);
    const text = captionAt(cues, frameTime);
    if (caption.textContent !== text) caption.textContent = text;
    caption.hidden = !text;
    slider.value = elapsed;
    byId('time').textContent = elapsed.toFixed(1) + ' / ' + duration.toFixed(1) + ' seconds';
  }

  function pause() {
    playbackRequest++;
    isPlaying = false;
    cancelAnimationFrame(timer);
    audio.pause();
    updatePlayLabel(false);
  }

  slider.oninput = () => {
    pause();
    renderPreview(Number(slider.value));
  };

  async function startPlayback(start, finish, holdScene) {
    const attempt = ++playbackRequest;
    isPlaying = true;
    updatePlayLabel(true);
    if (hasAudio) {
      audio.currentTime = start;
      try {
        await audio.play();
      } catch {
        if (attempt === playbackRequest && request === previewRequest) {
          pause();
          byId('status').textContent = 'Audio playback could not start.';
        }
        return;
      }
    }
    if (attempt !== playbackRequest || request !== previewRequest) return;
    const started = performance.now();
    function draw(now) {
      const position = hasAudio ? audio.currentTime : start + (now - started) / 1000;
      const elapsed = Math.min(finish, Math.max(start, position));
      renderPreview(elapsed, holdScene);
      if (elapsed < finish) timer = requestAnimationFrame(draw);
      else pause();
    }
    timer = requestAnimationFrame(draw);
  }

  play.onclick = () => {
    if (isPlaying) {
      pause();
    } else {
      const position = Number(slider.value);
      const start = position >= duration ? 0 : position;
      if (start !== position) renderPreview(start);
      void startPlayback(start, duration, false);
    }
  };
  updatePlayLabel(false);
  renderPreview(offset);
  if (!inspect) await startPlayback(offset, end, true);
}
byId('preview').addEventListener('click', () => preview());
byId('preview-ending').addEventListener('click', () => preview(true));
byId('inspect-timeline').addEventListener('click', () => preview(false, undefined, undefined, true));
showPlan();

const selectExportType = byId('export-type');
const resolutionControl = byId('resolution');
const frameRateControl = byId('frame-rate');
const currentFrameRate = () => frameRateControl.value === '30' ? 30 : 24;
const currentResolution = () => exportResolutions[resolutionControl.value] ?? exportResolutions[720];

function supportedType(type, resolution) {
  const profile = resolution.edge === 1080 ? '420028' : '42001f';
  const types = {
    webm: ['video/webm;codecs=vp9,opus', 'video/webm;codecs=vp8,opus', 'video/webm'],
    mp4: ['video/mp4;codecs=avc1.' + profile + ',mp4a.40.2', 'video/mp4;codecs=avc1,mp4a.40.2'],
  };
  return types[type]?.find(mime => globalThis.MediaRecorder?.isTypeSupported(mime));
}

function updateExportLabel() {
  const type = selectExportType.value;
  byId('export').textContent = type ? 'Export ' + (type === 'webm' ? 'WebM' : 'MP4') : 'Export video';
}

function updateExportOptions() {
  const resolution = currentResolution();
  const { width, height } = exportDimensions(byId('format').value, resolution);
  byId('export-dimensions').textContent = width + ' × ' + height + ' pixels · ' + currentFrameRate() + ' FPS';
  for (const option of selectExportType.options) option.disabled = !supportedType(option.value, resolution);
  if (!supportedType(selectExportType.value, resolution)) {
    selectExportType.value = supportedType('webm', resolution) ? 'webm' : supportedType('mp4', resolution) ? 'mp4' : '';
  }
  const support = byId('export-support');
  support.hidden = Boolean(supportedType('mp4', resolution));
  support.textContent = 'MP4 with H.264 and AAC is unavailable at this resolution in this browser.';
  updateExportLabel();
}
selectExportType.addEventListener('change', updateExportLabel);
resolutionControl.addEventListener('change', updateExportOptions);
frameRateControl.addEventListener('change', updateExportOptions);
byId('format').addEventListener('change', updateExportOptions);
updateExportOptions();

const settingsKey = 'syncshot-studio-settings-v1';
const settingFields = [
  'motion', 'transition', 'format', 'framing', 'crop-position',
  'pacing', 'export-type', 'resolution', 'frame-rate',
];
const settingsStatus = byId('settings-status');

function applySavedSettings(settings) {
  let skipped = 0;
  for (const id of settingFields) {
    const select = byId(id);
    const option = Array.from(select.options).find(item => item.value === settings[id]);
    if (!option || (option.disabled && id !== 'export-type')) {
      skipped++;
      continue;
    }
    select.value = option.value;
  }
  const requestedExportType = byId('export-type').value;
  stopPreview();
  applyPreviewFormat();
  applyPreviewFraming();
  showPhotoOrder();
  updateExportOptions();
  if (requestedExportType !== byId('export-type').value) skipped++;
  if (!byId('plan').disabled) showPlan();
  return skipped;
}

byId('save-settings').addEventListener('click', () => {
  try {
    const settings = Object.fromEntries(settingFields.map(id => [id, byId(id).value]));
    localStorage.setItem(settingsKey, JSON.stringify(settings));
    settingsStatus.textContent = 'Settings saved in this browser.';
  } catch {
    settingsStatus.textContent = 'This browser could not save your settings.';
  }
});

byId('load-settings').addEventListener('click', () => {
  try {
    const raw = localStorage.getItem(settingsKey);
    if (!raw) {
      settingsStatus.textContent = 'No saved settings in this browser yet.';
      return;
    }
    const settings = JSON.parse(raw);
    if (!settings || typeof settings !== 'object' || Array.isArray(settings)) throw new Error('Invalid settings');
    const skipped = applySavedSettings(settings);
    settingsStatus.textContent = skipped
      ? 'Settings loaded. Unavailable options were skipped.'
      : 'Settings loaded.';
  } catch {
    settingsStatus.textContent = 'Saved settings could not be loaded.';
  }
});

let exportedUrl;
let activeExport;
const cancelExport = byId('cancel-export');
cancelExport.addEventListener('click', () => {
  activeExport?.abort(new DOMException('Export canceled.', 'AbortError'));
});
byId('export').addEventListener('click', async () => {
  stopPreview();
  const scenes = showPlan();
  if (!scenes) return;
  const status = byId('status');
  const audioFile = byId('audio').files[0];
  const framing = byId('framing').value;
  const globalPosition = cropPosition(framing);
  const motion = byId('motion').value;
  const transition = byId('transition').value;
  const cues = captions;
  const cards = readTitleCards();
  if (duration > 300 || (audioFile && audioFile.size > 50 * 1024 * 1024)) {
    status.textContent = 'Use up to 5 minutes of narration and a 50 MB audio file for browser export.';
    return;
  }
  const fileType = selectExportType.value;
  const resolution = currentResolution();
  const frameRate = currentFrameRate();
  const outputSize = exportDimensions(byId('format').value, resolution);
  const mimeType = supportedType(fileType, resolution);
  const label = fileType === 'mp4' ? 'MP4' : 'WebM';
  const canvas = document.createElement('canvas');
  if (!mimeType || !canvas.captureStream || (audioFile && !globalThis.AudioContext)) {
    status.textContent = 'This export type is unavailable in your browser.';
    return;
  }

  const controls = ['inputs', 'plan', 'download-plan', 'preview', 'preview-ending', 'inspect-timeline', 'export'].map(byId);
  controls.push(...document.querySelectorAll('.preview-scene'));
  controls.forEach(control => { control.disabled = true; });
  status.textContent = 'Preparing browser export…';
  const controller = new AbortController();
  activeExport = controller;
  cancelExport.hidden = false;
  const interrupted = new Promise((_, reject) => {
    controller.signal.addEventListener('abort', () => reject(controller.signal.reason), { once: true });
  });
  const wait = task => Promise.race([task, interrupted]);
  let audioContext;
  let stream;
  let recorder;
  let animation;
  let onVisibility;
  try {
    let source;
    if (audioFile) {
      audioContext = new AudioContext();
      await wait(audioContext.resume());
      source = audioContext.createBufferSource();
      source.buffer = await wait(audioContext.decodeAudioData(await wait(audioFile.arrayBuffer())));
    }

    const images = new Map();
    for (const { photo } of scenes) {
      if (photo.url && !images.has(photo)) {
        const image = new Image();
        image.src = photo.url;
        await wait(image.decode());
        images.set(photo, image);
      }
    }
    const { width, height, bitrate } = outputSize;
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext('2d');
    const overlay = document.createElement('canvas');
    overlay.width = canvas.width;
    overlay.height = canvas.height;
    const overlayContext = overlay.getContext('2d');
    const paint = (context, scene, elapsed) => {
      context.fillStyle = scene.photo.color ?? '#19362d';
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.save();
      const zoom = zoomAt(scene, elapsed, motion);
      context.translate(canvas.width / 2, canvas.height / 2);
      context.scale(zoom, zoom);
      context.translate(-canvas.width / 2, -canvas.height / 2);
      const image = images.get(scene.photo);
      if (image) {
        const position = framing === 'cover' && scene.photo.position
          ? scene.photo.position.split(',').map(Number)
          : globalPosition;
        const bounds = photoBounds(image.naturalWidth, image.naturalHeight, canvas.width, canvas.height, framing, position);
        context.drawImage(image, bounds.x, bounds.y, bounds.width, bounds.height);
      } else {
        context.fillStyle = 'white';
        context.font = '44px system-ui';
        context.textAlign = 'center';
        context.textBaseline = 'middle';
        context.fillText(scene.photo.name, canvas.width / 2, canvas.height / 2, canvas.width * 0.85);
      }
      context.restore();
    };
    paint(context, scenes[0], 0);
    paintTitle(context, titleAt(cards, 0, duration), canvas.width, canvas.height);
    paintCaption(context, captionAt(cues, 0), canvas.width, canvas.height);
    stream = canvas.captureStream(frameRate);
    if (source) {
      const destination = audioContext.createMediaStreamDestination();
      source.connect(destination);
      for (const track of destination.stream.getAudioTracks()) stream.addTrack(track);
    }

    recorder = new MediaRecorder(stream, { mimeType, videoBitsPerSecond: bitrate });
    const chunks = [];
    const output = new Promise((resolve, reject) => {
      recorder.ondataavailable = event => {
        if (event.data.size) chunks.push(event.data);
      };
      recorder.onstop = () => resolve(new Blob(chunks, { type: 'video/' + fileType }));
      recorder.onerror = event => reject(event.error);
      onVisibility = () => {
        if (document.hidden) reject(new Error('Keep this tab visible during the export.'));
      };
      document.addEventListener('visibilitychange', onVisibility);
    });
    recorder.start(1000);
    const wallStart = performance.now();
    const audioStart = audioContext?.currentTime;
    source?.start();
    function draw(now) {
      const elapsed = source ? audioContext.currentTime - audioStart : (now - wallStart) / 1000;
      const { current, previous, alpha } = frameAt(scenes, elapsed, transition);
      if (previous) {
        paint(context, previous, previous.end);
        paint(overlayContext, current, elapsed);
        context.globalAlpha = alpha;
        context.drawImage(overlay, 0, 0);
        context.globalAlpha = 1;
      } else {
        paint(context, current, elapsed);
      }
      paintTitle(context, titleAt(cards, elapsed, duration), canvas.width, canvas.height);
      paintCaption(context, captionAt(cues, elapsed), canvas.width, canvas.height);
      if (elapsed >= duration) {
        recorder.stop();
        return;
      }
      status.textContent = 'Exporting ' + Math.floor(elapsed / duration * 100) + '% · Keep this tab visible.';
      animation = requestAnimationFrame(draw);
    }
    animation = requestAnimationFrame(draw);
    const video = await wait(output);
    if (!video.size) throw new Error('The browser produced an empty recording.');
    if (exportedUrl) URL.revokeObjectURL(exportedUrl);
    exportedUrl = URL.createObjectURL(video);
    const resultPlayer = byId('export-video');
    resultPlayer.style.maxWidth = Math.round(520 * canvas.width / canvas.height) + 'px';
    resultPlayer.src = exportedUrl;
    const download = byId('download');
    download.href = exportedUrl;
    download.download = 'syncshot.' + fileType;
    download.textContent = 'Download ' + label;
    byId('export-result').hidden = false;
    status.textContent = 'Export complete. Your ' + label + ' is ready to download.';
  } catch (error) {
    status.textContent = error.name === 'AbortError' && exportedUrl
      ? 'Export canceled. Your previous download is still available.'
      : error.message || 'Browser export failed.';
  } finally {
    activeExport = undefined;
    cancelExport.hidden = true;
    cancelAnimationFrame(animation);
    if (onVisibility) document.removeEventListener('visibilitychange', onVisibility);
    if (recorder && recorder.state !== 'inactive') recorder.stop();
    stream?.getTracks().forEach(track => track.stop());
    if (audioContext) void audioContext.close().catch(() => {});
    controls.forEach(control => { control.disabled = false; });
  }
});
