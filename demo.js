const byId = id => document.getElementById(id);
const audio = new Audio();
const formats = {
  landscape: { width: 1280, height: 720 },
  portrait: { width: 720, height: 1280 },
  square: { width: 720, height: 720 },
};
const selectedFormat = () => formats[byId('format').value] ?? formats.landscape;

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

function stopPreview() {
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
  context.font = '600 32px system-ui';
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
  const spacing = 40;
  const firstY = height - 45 - (lines.length - 1) * spacing;
  lines.forEach((line, index) => {
    const y = firstY + index * spacing;
    const boxWidth = Math.min(maxWidth, context.measureText(line).width) + 24;
    context.fillStyle = 'rgba(0, 0, 0, 0.78)';
    context.fillRect((width - boxWidth) / 2, y - 20, boxWidth, spacing);
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
  byId('preview').disabled = Boolean(file);
  byId('plan').disabled = Boolean(file);
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
  byId('preview').disabled = byId('plan').disabled = byId('export').disabled = false;
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
byId('preview').addEventListener('click', async () => {
  stopPreview();
  const scenes = showPlan();
  if (!scenes) return;
  const frame = byId('frame');
  const motion = byId('motion').value;
  const transition = byId('transition').value;
  const cues = captions;
  const limit = Math.min(duration, 10);
  if (byId('audio').files.length) {
    audio.currentTime = 0;
    try {
      await audio.play();
    } catch {
      byId('status').textContent = 'Audio playback could not start.';
      return;
    }
  }
  byId('player').hidden = false;
  const started = performance.now();
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
  frame.replaceChildren(outgoing.layer, incoming.layer, caption);

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

  function draw(now) {
    const elapsed = Math.min(limit, (now - started) / 1000);
    const { current, previous, alpha } = frameAt(scenes, elapsed, transition);
    drawLayer(incoming, current, elapsed);
    incoming.layer.style.opacity = alpha;
    incoming.layer.setAttribute('aria-hidden', 'false');
    outgoing.layer.hidden = !previous;
    outgoing.layer.setAttribute('aria-hidden', 'true');
    if (previous) drawLayer(outgoing, previous, previous.end);
    const text = captionAt(cues, elapsed);
    if (caption.textContent !== text) caption.textContent = text;
    caption.hidden = !text;
    byId('time').textContent = elapsed.toFixed(1) + ' / ' + limit.toFixed(1) + ' seconds';
    if (elapsed < limit) timer = requestAnimationFrame(draw);
    else audio.pause();
  }
  timer = requestAnimationFrame(draw);
});
showPlan();

let exportedUrl;
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
  if (duration > 300 || (audioFile && audioFile.size > 50 * 1024 * 1024)) {
    status.textContent = 'Use up to 5 minutes of narration and a 50 MB audio file for browser export.';
    return;
  }
  const mimeType = ['video/webm;codecs=vp9,opus', 'video/webm;codecs=vp8,opus', 'video/webm']
    .find(type => globalThis.MediaRecorder?.isTypeSupported(type));
  const canvas = document.createElement('canvas');
  if (!mimeType || !canvas.captureStream || (audioFile && !globalThis.AudioContext)) {
    status.textContent = 'WebM export requires a supported browser such as Chrome or Edge.';
    return;
  }

  const controls = ['inputs', 'plan', 'preview', 'export'].map(byId);
  controls.forEach(control => { control.disabled = true; });
  status.textContent = 'Preparing browser export…';
  byId('export-result').hidden = true;
  let audioContext;
  let stream;
  let recorder;
  let animation;
  let onVisibility;
  try {
    let source;
    if (audioFile) {
      audioContext = new AudioContext();
      await audioContext.resume();
      source = audioContext.createBufferSource();
      source.buffer = await audioContext.decodeAudioData(await audioFile.arrayBuffer());
    }

    const images = new Map();
    for (const { photo } of scenes) {
      if (photo.url && !images.has(photo)) {
        const image = new Image();
        image.src = photo.url;
        await image.decode();
        images.set(photo, image);
      }
    }
    const { width, height } = selectedFormat();
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
    paintCaption(context, captionAt(cues, 0), canvas.width, canvas.height);
    stream = canvas.captureStream(24);
    if (source) {
      const destination = audioContext.createMediaStreamDestination();
      source.connect(destination);
      for (const track of destination.stream.getAudioTracks()) stream.addTrack(track);
    }

    recorder = new MediaRecorder(stream, { mimeType, videoBitsPerSecond: 2500000 });
    const chunks = [];
    const output = new Promise((resolve, reject) => {
      recorder.ondataavailable = event => {
        if (event.data.size) chunks.push(event.data);
      };
      recorder.onstop = () => resolve(new Blob(chunks, { type: 'video/webm' }));
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
      paintCaption(context, captionAt(cues, elapsed), canvas.width, canvas.height);
      if (elapsed >= duration) {
        recorder.stop();
        return;
      }
      status.textContent = 'Exporting ' + Math.floor(elapsed / duration * 100) + '% · Keep this tab visible.';
      animation = requestAnimationFrame(draw);
    }
    animation = requestAnimationFrame(draw);
    const video = await output;
    if (!video.size) throw new Error('The browser produced an empty recording.');
    if (exportedUrl) URL.revokeObjectURL(exportedUrl);
    exportedUrl = URL.createObjectURL(video);
    const resultPlayer = byId('export-video');
    resultPlayer.style.maxWidth = Math.round(520 * canvas.width / canvas.height) + 'px';
    resultPlayer.src = exportedUrl;
    byId('download').href = exportedUrl;
    byId('export-result').hidden = false;
    status.textContent = 'Export complete. Your WebM is ready to download.';
  } catch (error) {
    status.textContent = error.message || 'Browser export failed.';
  } finally {
    cancelAnimationFrame(animation);
    if (onVisibility) document.removeEventListener('visibilitychange', onVisibility);
    if (recorder && recorder.state !== 'inactive') recorder.stop();
    stream?.getTracks().forEach(track => track.stop());
    if (audioContext) void audioContext.close().catch(() => {});
    controls.forEach(control => { control.disabled = false; });
  }
});
