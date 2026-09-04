/**
 * The schema pipeline, end to end: the payload the backend actually serves goes
 * in, and a Yup schema that enforces the component's declared cross-field rules
 * comes out.
 *
 * This is the seam the whole design rests on, and it is easy to break silently:
 * `formattedModel` flattens the JSON Schema down to its properties, so anything
 * living at the root — the rule set included — is dropped unless it is carried
 * across deliberately. A regression here does not throw; it just means no rule
 * ever fires in the browser again.
 */

import { validateYupSchema, yupToFormErrors } from "formik";

import {
  SCHEMA_RULES,
  formattedModel,
  generateYupSchema,
  getSchemaRules,
} from "./schema";
import {
  holdoutWireSchema,
  holdoutWireSchemaWithoutRules,
} from "./holdoutSchema.fixture";

/** Validate the way formik does, and return its per-field error object. */
async function errorsFor(schema, values) {
  try {
    await validateYupSchema(values, schema);
    return {};
  } catch (error) {
    return yupToFormErrors(error);
  }
}

const complete = {
  train: 0.6,
  validation: 0.3,
  test: 0.1,
  stratify: false,
  shuffle: true,
  random_state: 42,
};

describe("formattedModel carries the rule set across the flattening", () => {
  it("keeps the rules without turning them into a field", async () => {
    const formatted = await formattedModel(holdoutWireSchema);

    expect(getSchemaRules(formatted)).toHaveLength(3);
    // The loops that render one input per entry must not see them.
    expect(Object.keys(formatted)).toEqual([
      "train",
      "test",
      "validation",
      "stratify",
      "shuffle",
      "random_state",
    ]);
    expect(JSON.stringify(formatted)).not.toContain("x-dashai-rules");
    expect(Object.keys(formatted)).not.toContain("x-dashai-rules");
  });

  it("survives being spread, which several consumers do", async () => {
    const formatted = await formattedModel(holdoutWireSchema);
    expect(getSchemaRules({ ...formatted })).toHaveLength(3);
  });

  it("reports an empty rule set for a schema that declares none", async () => {
    const formatted = await formattedModel(holdoutWireSchemaWithoutRules);
    expect(getSchemaRules(formatted)).toEqual([]);
    expect(formatted[SCHEMA_RULES]).toEqual([]);
  });

  it("still marks required fields the way the renderer expects", async () => {
    const formatted = await formattedModel(holdoutWireSchema);
    expect(formatted.train.required).toBe(true);
    expect(formatted.train.placeholder).toBe(0.6);
    expect(formatted.train.title).toBe("Train");
  });
});

describe("generateYupSchema enforces the declared rules", () => {
  it("seeds the initial values from the placeholders", async () => {
    const { initialValues } = generateYupSchema(
      await formattedModel(holdoutWireSchema),
    );
    expect(initialValues).toEqual({
      train: 0.6,
      test: 0.2,
      validation: 0.2,
      stratify: false,
      shuffle: true,
      random_state: 42,
    });
  });

  it("accepts the seeded defaults", async () => {
    const { schema, initialValues } = generateYupSchema(
      await formattedModel(holdoutWireSchema),
    );
    await expect(errorsFor(schema, initialValues)).resolves.toEqual({});
  });

  it("accepts 60/30/10, which the pipeline editor's exact check rejects", async () => {
    const { schema } = generateYupSchema(
      await formattedModel(holdoutWireSchema),
    );
    expect(0.6 + 0.3 + 0.1).not.toBe(1);
    await expect(errorsFor(schema, complete)).resolves.toEqual({});
  });

  it("reports the sum under all three partitions, with the total quoted", async () => {
    const { schema } = generateYupSchema(
      await formattedModel(holdoutWireSchema),
    );
    const errors = await errorsFor(schema, { ...complete, test: 0.3 });

    expect(Object.keys(errors).sort()).toEqual(["test", "train", "validation"]);
    expect(errors.train).toBe(
      "Train, validation and test must sum to 1 (they currently add up to 1.2).",
    );
    expect(errors.validation).toBe(errors.train);
  });

  it("reports an empty train partition on its own field", async () => {
    const { schema } = generateYupSchema(
      await formattedModel(holdoutWireSchema),
    );
    const errors = await errorsFor(schema, {
      ...complete,
      train: 0,
      validation: 0.5,
      test: 0.5,
    });
    expect(errors.train).toBe("The train proportion must be greater than 0.");
    expect(errors.validation).toBeUndefined();
  });

  it("stops requiring the seed once shuffling is off", async () => {
    const { schema } = generateYupSchema(
      await formattedModel(holdoutWireSchema),
    );

    const shuffling = await errorsFor(schema, {
      ...complete,
      random_state: null,
    });
    expect(shuffling.random_state).toBeDefined();

    const notShuffling = await errorsFor(schema, {
      ...complete,
      shuffle: false,
      random_state: null,
    });
    expect(notShuffling.random_state).toBeUndefined();
  });

  it("changes nothing for a schema that declares no rules", async () => {
    const { schema } = generateYupSchema(
      await formattedModel(holdoutWireSchemaWithoutRules),
    );
    // A sum of 1.2 is only a problem because a rule says so; without the rule
    // each proportion is valid on its own and the form submits.
    await expect(
      errorsFor(schema, { ...complete, test: 0.3 }),
    ).resolves.toEqual({});
  });

  it("still enforces the per-field bounds the JSON Schema declares", async () => {
    const { schema } = generateYupSchema(
      await formattedModel(holdoutWireSchema),
    );
    const errors = await errorsFor(schema, { ...complete, train: 1.4 });
    // The field's own constraint wins on its own field; the relation is
    // reported on the siblings.
    expect(errors.train).toMatch(/less than or equal to 1/);
    expect(errors.validation).toMatch(/must sum to 1/);
  });
});
