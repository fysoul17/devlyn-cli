export function applyMigrationStep(state, migration) {
  const { kind, table, name } = migration.change;
  if (kind === "column") {
    state.addColumn(table, name);
  } else if (kind === "index") {
    state.addIndex(table, name);
  } else {
    throw new Error(`unsupported change: ${kind}`);
  }

  if (migration.failAfterApply) {
    throw new Error(`migration step failed: ${migration.key}`);
  }
}
