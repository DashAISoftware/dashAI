import React from "react";
import { render, screen } from "@testing-library/react";

jest.mock("notistack", () => ({
  useSnackbar: () => ({ enqueueSnackbar: () => {} }),
}));

jest.mock("../context/ExplorersAndConvertersContext", () => ({
  useExplorersAndConverters: () => ({
    explorersAndConverters: [],
    setExplorersAndConverters: () => {},
    setColumnTypes: () => {},
    setLastAddedItemId: () => {},
  }),
}));

const mockSaveConverter = jest.fn();
jest.mock("../../../api/converter", () => ({
  getConverterById: jest.fn(),
  saveConverter: (...args) => mockSaveConverter(...args),
}));
jest.mock("../../../api/job", () => ({ enqueueConverterJob: jest.fn() }));
jest.mock("../../../utils/jobPoller", () => ({ startJobPolling: jest.fn() }));
jest.mock("../notebookColumns", () => ({
  ...jest.requireActual("../notebookColumns"),
  fetchNotebookColumnTypes: jest.fn(),
}));

// The steps themselves load schemas from the API; what is under test is
// what this section hands them.
jest.mock("./ScopeStepConverter", () => ({
  __esModule: true,
  default: ({ nextStep }) => (
    <button type="button" onClick={nextStep}>
      next
    </button>
  ),
}));
jest.mock("./ParameterStepConverter", () => ({
  __esModule: true,
  default: ({ excludeFields = [] }) => (
    <div data-testid="parameter-step">{excludeFields.join(",")}</div>
  ),
}));

import FormConverterSection from "./FormConverterSection";

const tool = (properties) => ({
  name: "BagOfWordsConverter",
  metadata: { supervised: false },
  schema: { properties },
});

const renderSection = ({ step, dataKind, properties, setStep = jest.fn() }) =>
  render(
    <FormConverterSection
      step={step}
      setStep={setStep}
      handleClose={() => {}}
      tool={tool(properties)}
      notebook={{ id: 1, data_kind: dataKind }}
    />,
  );

const BOTH = { lowercase: {}, drop_source_columns: {} };

describe("FormConverterSection drop original columns", () => {
  beforeEach(() => {
    // Never settles: the test only checks that saving was requested.
    mockSaveConverter.mockReturnValue(new Promise(() => {}));
  });

  it('hides "Drop original columns" for a document notebook', () => {
    renderSection({ step: 1, dataKind: "document", properties: BOTH });

    expect(screen.getByTestId("parameter-step")).toHaveTextContent(
      "drop_source_columns",
    );
  });

  it("shows it for a dataset notebook", () => {
    renderSection({ step: 1, dataKind: "dataset", properties: BOTH });

    expect(screen.getByTestId("parameter-step")).toHaveTextContent(/^$/);
  });

  it("skips the parameter step when the hidden option is the only field", () => {
    const setStep = jest.fn();
    renderSection({
      step: 0,
      dataKind: "document",
      properties: { drop_source_columns: {} },
      setStep,
    });

    screen.getByText("next").click();

    expect(setStep).not.toHaveBeenCalled();
    expect(mockSaveConverter).toHaveBeenCalledTimes(1);
  });
});
