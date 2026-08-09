function clone(value) {
  return structuredClone(value);
}

export class SchemaState {
  #schema;
  #revision;

  constructor(schema = {}, revision = 0) {
    this.#schema = clone(schema);
    this.#revision = revision;
  }

  addColumn(table, column) {
    const definition = this.#schema[table];
    if (definition === undefined) {
      throw new Error(`unknown table: ${table}`);
    }
    definition.columns.push(column);
    this.#revision += 1;
  }

  addIndex(table, index) {
    const definition = this.#schema[table];
    if (definition === undefined) {
      throw new Error(`unknown table: ${table}`);
    }
    definition.indexes.push(index);
    this.#revision += 1;
  }

  snapshot() {
    return { schema: clone(this.#schema), revision: this.#revision };
  }

  restore(snapshot) {
    this.#schema = clone(snapshot.schema);
    this.#revision = snapshot.revision;
  }

  view() {
    return this.snapshot();
  }
}
