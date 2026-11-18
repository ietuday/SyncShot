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

export async function receiveMedia(request, directory) {
  const audio = join(directory, 'audio');
  const images = join(directory, 'images');
  await Promise.all([mkdir(audio, { recursive: true }), mkdir(images, { recursive: true })]);
  const parser = Busboy({
    headers: request.headers,
    limits: { files: maxImages + 2, fields: 0, fileSize: maxUploadBytes },
  });
  let received = 0;
  let audioName;
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
  return { audio, images, audioName };
}
