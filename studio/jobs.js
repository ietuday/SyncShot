export async function readJobs(method = 'GET') {
  const response = await fetch('/api/jobs', { method });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error);
  return data;
}
