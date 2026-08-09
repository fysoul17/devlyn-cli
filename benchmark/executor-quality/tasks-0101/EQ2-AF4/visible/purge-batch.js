/** Coordinate cache purges with their generation counters. */
export function runPurgeBatch(store, counter, batchId, commands) {
  if (counter.hasCompleted(batchId)) {
    return { ok: true, skipped: true, purged: [], error: null };
  }

  const purged = [];
  try {
    for (const command of commands) {
      const generation = command.prepare(counter);
      purged.push(...command.execute(store, generation));
    }
    counter.complete(batchId);
    return { ok: true, skipped: false, purged, error: null };
  } catch (error) {
    return { ok: false, skipped: false, purged, error: error.message };
  }
}
