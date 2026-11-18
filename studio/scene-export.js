/**
 * Export the same scene plan shown in Studio to UTF-8 CSV.
 * Spreadsheet programs recognise the BOM and preserve non-Latin narration.
 */
export function scenePlanCSV(scenes, hasNarration = false) {
  const columns = ['Scene', 'Start (s)', 'End (s)', 'Photo'];
  if (hasNarration) columns.push('Narration');
  const escapeCell = value => {
    const text = String(value ?? '');
    // Quote all cells and neutralise spreadsheet formula injection.
    const safe = /^[\s]*[=+@-]/.test(text) ? "'" + text : text;
    return '"' + safe.replaceAll('"', '""') + '"';
  };
  const rows = scenes.map((scene, index) => {
    const row = [index + 1, Number(scene.start).toFixed(2), Number(scene.end).toFixed(2), scene.image ?? ''];
    if (hasNarration) row.push((scene.narration ?? []).join(' | '));
    return row;
  });
  return '\uFEFF' + [columns, ...rows].map(row => row.map(escapeCell).join(',')).join('\r\n') + '\r\n';
}

export function downloadScenePlan(scenes, hasNarration) {
  const blob = new Blob([scenePlanCSV(scenes, hasNarration)], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'syncshot-scene-plan.csv';
  try {
    document.body.append(link);
    link.click();
  } finally {
    link.remove();
    URL.revokeObjectURL(url);
  }
}
