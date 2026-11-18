import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { readJobs } from '../jobs.js';
import '../studio.css';

function Studio() {
  const [jobs, setJobs] = useState([]);
  const [connected, setConnected] = useState(false);
  const [submitting, setSubmitting] = useState(false);
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
      await readJobs('POST');
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
      <p>Add one narration to <code>inputs/audio</code> and your images to <code>inputs/images</code>.</p>
      <button onClick={start} disabled={!connected || submitting || busy}>Render video</button>
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
