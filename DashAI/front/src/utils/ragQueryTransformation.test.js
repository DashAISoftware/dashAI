import {
  canPersistQueryTransformationRef,
  isGeneratorDownloaded,
  prepareEnableRef,
  resolveLabel,
} from "./ragQueryTransformation";

const GENERATORS = [
  { name: "Downloaded", downloaded: true },
  { name: "Missing", downloaded: false },
];
const PROMPTS = [
  {
    name: "RewriteDefault",
    metadata: { technique: "expansion", variant: "default" },
  },
];
const TRANSFORMER = {
  name: "LLMQueryExpander",
  metadata: { technique: "expansion" },
};

const completeRef = (llm) => ({
  component: "LLMQueryExpander",
  params: {
    llm_model: { component: llm, params: {} },
    prompt: { component: "RewriteDefault", params: {} },
  },
});

describe("isGeneratorDownloaded", () => {
  it("is true only for a known, downloaded model", () => {
    expect(isGeneratorDownloaded(GENERATORS, "Downloaded")).toBe(true);
    expect(isGeneratorDownloaded(GENERATORS, "Missing")).toBe(false);
    expect(isGeneratorDownloaded(GENERATORS, "Unknown")).toBe(false);
    expect(() => isGeneratorDownloaded(undefined, "Downloaded")).toThrow(
      TypeError,
    );
  });
});

describe("canPersistQueryTransformationRef", () => {
  it("accepts a complete ref with a downloaded model", () => {
    expect(
      canPersistQueryTransformationRef(completeRef("Downloaded"), GENERATORS),
    ).toBe(true);
  });

  it("refuses a complete ref whose model is not downloaded", () => {
    expect(
      canPersistQueryTransformationRef(completeRef("Missing"), GENERATORS),
    ).toBe(false);
  });

  it("refuses a ref without a prompt", () => {
    const ref = completeRef("Downloaded");
    delete ref.params.prompt;
    expect(canPersistQueryTransformationRef(ref, GENERATORS)).toBe(false);
  });
});

describe("prepareEnableRef", () => {
  it("seeds the downloaded model and the default prompt", () => {
    const { ref, blockedBy } = prepareEnableRef({
      transformer: TRANSFORMER,
      generators: GENERATORS,
      defaultGeneratorName: "Missing",
      prompts: PROMPTS,
    });

    expect(blockedBy).toBeNull();
    expect(ref.params.llm_model.component).toBe("Downloaded");
    expect(ref.params.prompt.component).toBe("RewriteDefault");
    expect(ref.params).not.toHaveProperty("reranker");
  });

  it("is blocked when no model is downloaded", () => {
    const { ref, blockedBy } = prepareEnableRef({
      transformer: TRANSFORMER,
      generators: [{ name: "Missing", downloaded: false }],
      defaultGeneratorName: "Missing",
      prompts: PROMPTS,
    });

    expect(ref).toBeNull();
    expect(blockedBy).toBe("needsDownloadedModel");
  });

  it("is blocked when the technique has no default prompt", () => {
    const { ref, blockedBy } = prepareEnableRef({
      transformer: TRANSFORMER,
      generators: GENERATORS,
      defaultGeneratorName: null,
      prompts: [],
    });

    expect(ref).toBeNull();
    expect(blockedBy).toBe("promptRequired");
  });
});

describe("resolveLabel", () => {
  it("resolves strings and multilingual objects with a fallback", () => {
    expect(resolveLabel("plain", "x", "en")).toBe("plain");
    expect(resolveLabel({ en: "English", es: "Español" }, "x", "es")).toBe(
      "Español",
    );
    expect(resolveLabel({ es: "Español" }, "x", "en")).toBe("Español");
    expect(resolveLabel(undefined, "fallback", "en")).toBe("fallback");
    expect(resolveLabel({}, "fallback", "en")).toBe("fallback");
  });
});
