import Busboy from 'busboy';
import { createWriteStream } from 'node:fs';
import { mkdir } from 'node:fs/promises';
import { extname, join } from 'node:path';
import { Transform } from 'node:stream';
import { pipeline } from 'node:stream/promises';

const audioTypes = new Set(['.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg']);
const imageTypes = new Set(['.jpg', '.jpeg', '.png', '.webp', '.bmp']);
export const maxUploadBytes = 512 * 1024 * 1024;
const maxImages = 200;
const maxSubtitleBytes = 1024 * 1024;
const motions = new Set(['static', 'zoom_in', 'zoom_out', 'pan_left', 'pan_right']);
const transitions = new Map([['cut', 0], ['fade', 0.5]]);
const modes = new Set(['preview', 'full']);

export async function receiveMedia(request, directory) {
  const audio = join(directory, 'audio');
  const images = join(directory, 'images');
  await Promise.all([mkdir(audio, { recursive: true }), mkdir(images, { recursive: true })]);
  const parser = Busboy({
    headers: request.headers,
    limits: { files: maxImages + 3, fields: 4, fieldSize: 32, fileSize: maxUploadBytes },
  });
  let received = 0;
  let audioName;
  let subtitles;
  const settings = new Map();
  let imageCount = 0;
  let failure;
  const writes = [];
  const reject = message => { failure ??= new Error(message); };
  const sizeLimit = new Transform({
    transform(chunk, encoding, callback) {
      received += chunk.length;
      if (received > maxUploadBytes) callback(new Error('Upload exceeds 512 MB.'));
      else callback(null, chunk);
    },
  });

  parser.on('fieldsLimit', () => reject('Unexpected upload field.'));
  parser.on('field', (name, value, { valueTruncated }) => {
    const allowed = { motion: motions, transition: transitions, mode: modes };
    if (valueTruncated || !Object.hasOwn(allowed, name) || !allowed[name].has(value) || settings.has(name)) {
      reject('Invalid render settings.');
      return;
    }
    settings.set(name, value);
  });
  parser.on('filesLimit', () => reject('Too many uploaded files.'));
  parser.on('file', (field, stream, { filename }) => {
    const suffix = extname(filename ?? '').toLowerCase();
    let target;
    if (field === 'audio' && !audioName && audioTypes.has(suffix)) {
      audioName = filename;
      target = join(audio, 'narration' + suffix);
    } else if (field === 'images' && imageCount < maxImages && imageTypes.has(suffix)) {
      imageCount += 1;
      target = join(images, String(imageCount).padStart(4, '0') + suffix);
    } else if (field === 'subtitles' && !subtitles && suffix === '.srt') {
      subtitles = join(directory, 'captions.srt');
      target = subtitles;
      let subtitleBytes = 0;
      stream.on('data', chunk => {
        subtitleBytes += chunk.length;
        if (subtitleBytes > maxSubtitleBytes) {
          reject('Subtitle file exceeds 1 MB.');
        }
      });
    } else {
      reject('Upload one supported narration and up to 200 supported images.');
      stream.resume();
      return;
    }
    stream.once('limit', () => reject('Uploaded file is too large.'));
    writes.push(pipeline(stream, createWriteStream(target, { flags: 'wx' }))
      .catch(error => { failure ??= error; }));
  });
  // Keep the request outside pipeline so a parser error can return a JSON response.
  const forwardRequestError = error => sizeLimit.destroy(error);
  request.on('error', forwardRequestError);
  try {
    const parse = pipeline(sizeLimit, parser);
    request.pipe(sizeLimit);
    await parse;
  } catch (error) {
    failure ??= error;
    request.unpipe(sizeLimit);
    request.resume();
  } finally {
    request.off('error', forwardRequestError);
    await Promise.all(writes);
  }
  if (failure) throw failure;
  if (!audioName || !imageCount) throw new Error('Select one narration and at least one image.');
  return {
    audio, images, audioName, subtitles,
    mode: settings.get('mode') ?? 'full',
    motion: settings.get('motion') ?? 'zoom_in',
    crossfade: transitions.get(settings.get('transition') ?? 'fade'),
  };
}
