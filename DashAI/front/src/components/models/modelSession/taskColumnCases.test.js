import { selectionReady, shownRoles } from "./columnRoles";
import taskColumnCases from "./__fixtures__/taskColumnCases.json";

/*
 * The wizard decides from a task's metadata whether a selection is ready.
 * These cases come from the registered tasks, with the backend's verdict on
 * each (tests/back/tasks/task_column_cases.py writes them, and pytest checks
 * they are up to date), so the wizard is checked on the tasks the backend
 * actually declares instead of hand-written copies of them (#994).
 */
const cases = taskColumnCases.tasks.flatMap(({ task, metadata, cases }) =>
  cases.map((c) => [task, c.name, metadata, c]),
);

describe("the wizard agrees with the backend on every registered task", () => {
  test.each(cases)("%s: %s", (_task, _name, metadata, c) => {
    const ready = selectionReady(
      shownRoles(metadata),
      c.selection,
      metadata.io_roles.inputs,
      metadata.requires_input_columns,
    );

    expect(ready).toBe(c.valid);
  });
});
