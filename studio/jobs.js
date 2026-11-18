export async function readJobs(method = 'GET', body) {
  const response = await fetch('/api/jobs', { method, body });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error);
  return data;
}
