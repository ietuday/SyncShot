export async function readJobs(method = 'GET', body) {
  const response = await fetch('/api/jobs', { method, body });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error);
  return data;
}

export async function cancelJob(id) {
  const response = await fetch(`/api/jobs/${encodeURIComponent(id)}/cancel`, { method: 'POST' });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Unable to cancel job.');
  return data;
}
