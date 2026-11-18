import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { readJobs } from '../jobs.js';
import '../studio.css';

function Studio() {
  const [jobs, setJobs] = useState([]);
  const [connected, setConnected] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [audio, setAudio] = useState(null);
  const [images, setImages] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    let mounted = true;
    async function refresh() {
      try {
        const jobs = await readJobs();
        if (!mounted) return;
        setJobs(jobs);
        setConnected(true);
      } catch {
        if (mounted) setConnected(false);
      } finally {
        if (mounted) timer = setTimeout(refresh, 1000);
      }
    }
    let timer;
    void refresh();
    return () => {
      mounted = false;
      clearTimeout(timer);
    };
  }, []);

  async function start() {
    setSubmitting(true);
    setError('');
    try {
      const body = new FormData();
      body.append('audio', audio);
      for (const image of images) body.append('images', image);
      await readJobs('POST', body);
      setJobs(await readJobs());
    } catch (error) {
      setError(error.message);
    } finally {
      setSubmitting(false);
    }
  }

  const latest = jobs[0];
  const busy = latest && ['checking inputs', 'rendering'].includes(latest.status);
  return <main>
    <nav><strong>SyncShot</strong><a href="/angular/">Render history</a></nav>
    <section>
      <h1>Video studio</h1>
      <p>Select a narration and the photos for your video. Uploads can total up to 512 MB.</p>
      <fieldset disabled={submitting || busy}>
        <label>Narration
          <input type="file" accept=".mp3,.wav,.m4a,.aac,.flac,.ogg"
            onChange={event => setAudio(event.target.files[0] ?? null)} />
        </label>
        <label>Photos
          <input type="file" accept=".jpg,.jpeg,.png,.webp,.bmp" multiple
            onChange={event => setImages(Array.from(event.target.files).sort((a, b) => a.name.localeCompare(b.name)))} />
        </label>
      </fieldset>
      <button onClick={start} disabled={!connected || submitting || busy || !audio || !images.length}>
        {submitting ? 'Uploading…' : 'Render video'}
      </button>
      {latest && (busy || latest.status === 'completed') && <p>
        <progress aria-label="Render progress" max="100" value={latest.progress ?? 0} /> {latest.progress ?? 0}%
      </p>}
      <div aria-live="polite">
        {!connected && <p>Waiting for the local job API.</p>}
        {latest && <p>Latest job: {latest.status}</p>}
        {latest?.media && <p>{latest.media.audio} · {Math.round(latest.media.durationSeconds)} s · {latest.media.images} images</p>}
        {(error || latest?.error) && <p className="error">{error || latest.error}</p>}
        {latest?.videoUrl && <a href={latest.videoUrl}>Download MP4</a>}
      </div>
    </section>
  </main>;
}

createRoot(document.getElementById('root')).render(<Studio />);
