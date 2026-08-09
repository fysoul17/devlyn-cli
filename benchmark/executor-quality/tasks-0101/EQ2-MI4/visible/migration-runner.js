import { applyMigrationStep } from "./step-applier.js";

/** Coordinate the step applier and migration journal. */
export function runMigrationBatch(state, journal, migrations) {
  const applied = [];
  const skipped = [];

  try {
    for (const migration of migrations) {
      if (!journal.claim(migration.key)) {
        skipped.push(migration.key);
        continue;
      }
      applyMigrationStep(state, migration);
      journal.commit(migration.key, state.view().revision);
      applied.push(migration.key);
    }
    return { ok: true, applied, skipped, error: null };
  } catch (error) {
    return { ok: false, applied, skipped, error: error.message };
  }
}
