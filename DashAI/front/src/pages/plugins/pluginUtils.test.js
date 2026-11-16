import {
  canReinstall,
  canUpdateTo,
  canToggle,
  dependentsOf,
  errorMessage,
  authorLine,
  originFilters,
  pluginLinks,
  resolveReadmeUrl,
  savedPageSize,
  unmetDependencies,
  versionNotice,
} from "./pluginUtils";

const plugin = (overrides = {}) => ({
  id: "geo-features",
  problem: null,
  ...overrides,
});

// t() as i18next resolves it here, the key and its params or the fallback.
const t = (key, options) => JSON.stringify({ key, ...options });

describe("what a problem allows", () => {
  it.each([
    ["damaged", false, true],
    ["dependency_version", false, false],
    ["incompatible", false, false],
    ["repair_failed", false, true],
    ["load_failed", true, false], // turning it on retries loading it
    ["restart_required", false, false], // nothing changes until reopening
    ["blocked", true, false], // turning it on asks "anyway?"
  ])("%s: toggle %s, reinstall %s", (code, toggle, reinstall) => {
    const broken = plugin({ problem: { code, detail: "" } });
    expect(canToggle(broken)).toBe(toggle);
    expect(canReinstall(broken)).toBe(reinstall);
  });

  it("offers only Update when there is a newer release (it fixes it too)", () => {
    const broken = plugin({ problem: { code: "damaged", detail: "" } });
    expect(canReinstall(broken, "v2.0.0")).toBe(false);
  });
});

it("lists a plugin's links once: its repo and issues, then the manifest's", () => {
  const project_urls = {
    Homepage: "https://github.com/acme/kit/",
    Issues: "https://github.com/Acme/kit/issues",
    Docs: "https://acme.dev/kit",
  };
  const remote = { can_update: true, project_urls };
  expect(
    pluginLinks({
      ...remote,
      source: "git",
      web_url: "https://github.com/acme/kit",
    }),
  ).toEqual([
    { key: "github", url: "https://github.com/acme/kit" },
    { key: "issues", url: "https://github.com/acme/kit/issues" },
    { label: "Docs", url: "https://acme.dev/kit" },
  ]);
  // A source the front doesn't know shows its site, by host.
  expect(
    pluginLinks({
      ...remote,
      source: "gitlab",
      web_url: "https://gitlab.com/acme/kit",
    })[0],
  ).toEqual({ label: "gitlab.com", url: "https://gitlab.com/acme/kit" });
  // A .zip shows only what its manifest names.
  expect(pluginLinks({ source: "local", project_urls })).toHaveLength(3);
});

it("names its owner at its source when it names no author", () => {
  expect(authorLine({ authors: [], owner: "acme" })).toBe("acme");
  expect(authorLine({ authors: [{ name: "Ana" }], owner: "acme" })).toBe("Ana");
  expect(authorLine({ authors: [], owner: null })).toBeNull();
});

// As in the Design, sentiment-tools needs text-toolkit, which needs nlp-core.
it("has an origin chip per source of its plugins, and the selected one", () => {
  const plugins = [{ source: "gitlab" }, { source: "git" }, {}];
  expect(originFilters(plugins, "all")).toEqual([
    "all",
    "git",
    "gitlab",
    "local",
  ]);
  expect(originFilters([{ source: "git" }], "local")).toEqual([
    "all",
    "git",
    "local",
  ]);
});

describe("plugins that need others", () => {
  const installed = (id, needs = [], overrides = {}) => ({
    id,
    name: id,
    plugin_dependencies: needs,
    enabled: true,
    active: true,
    problem: null,
    ...overrides,
  });
  const off = { enabled: false, active: false };
  const core = installed("nlp-core");
  const toolkit = installed("text-toolkit", ["nlp-core"]);
  const tools = installed("sentiment-tools", ["text-toolkit"]);
  const ids = (plugins) => plugins.map(({ id }) => id);

  it("lists the active ones that stop working without it, nearest first", () => {
    expect(ids(dependentsOf([tools, toolkit, core], "nlp-core"))).toEqual([
      "text-toolkit",
      "sentiment-tools",
    ]);
    const stopped = { ...tools, active: false };
    expect(dependentsOf([stopped, toolkit, core], "text-toolkit")).toEqual([]);
  });

  it("can't be turned on while one it needs is missing or has a problem", () => {
    const stopped = { ...tools, ...off };
    const missing = [stopped, { ...toolkit, ...off }];
    expect(unmetDependencies(stopped, missing)).toEqual([
      { id: "nlp-core", name: "nlp-core", reason: "uninstalled" },
      { id: "text-toolkit", name: "text-toolkit", reason: "disabled" },
    ]);
    expect(canToggle(stopped, missing)).toBe(false);
    // Disabled, but turning it on would not fix it.
    const broken = { ...toolkit, ...off, problem: { code: "incompatible" } };
    expect(unmetDependencies(stopped, [stopped, broken, core])).toEqual([
      { id: "text-toolkit", name: "text-toolkit", reason: "problem" },
    ]);
    // On, it can always be turned off.
    expect(canToggle(tools, [tools])).toBe(true);
  });

  it("names what keeps the one it needs off, not that one", () => {
    const waiting = {
      ...toolkit,
      active: false,
      problem: { code: "dependency_unavailable" },
    };
    const plugins = [{ ...tools, active: false }, waiting, { ...core, ...off }];
    expect(unmetDependencies(plugins[0], plugins)).toEqual([
      { id: "nlp-core", name: "nlp-core", reason: "disabled" },
    ]);
  });

  it("stops at plugins that need each other", () => {
    const a = installed("a", ["b"], off);
    const b = installed("b", ["a"], off);
    expect(unmetDependencies(a, [a, b])).toEqual([
      { id: "b", name: "b", reason: "disabled" },
    ]);
  });

  it("says why installing it can't go on", () => {
    const blocked = JSON.parse(
      errorMessage(t, {
        code: "dependency_unavailable",
        params: { id: "text-toolkit", problem: "blocked" },
      }),
    );
    expect(blocked.key).toBe("plugins:errors.dependency_unavailable");
    expect(blocked.name).toBe("text-toolkit");
    expect(JSON.parse(blocked.problem).key).toBe(
      "plugins:problem.blocked.title",
    );
    // At install, no longer active.
    const gone = errorMessage(t, {
      code: "dependency_unavailable",
      params: { id: "text-toolkit" },
    });
    expect(JSON.parse(gone).key).toBe("plugins:errors.dependency_inactive");
    const unread = errorMessage(t, {
      code: "missing_plugin_dependency",
      params: { id: "text-toolkit", store_read: false },
    });
    expect(JSON.parse(unread).key).toBe(
      "plugins:errors.missing_plugin_dependency_unread",
    );
    const range = errorMessage(t, {
      code: "plugin_dependency_version",
      params: { id: "text-toolkit", required: ">=2", installed: null },
    });
    expect(JSON.parse(range).key).toBe(
      "plugins:errors.plugin_dependency_version_store",
    );
    // A list, for the text's list format.
    const cycle = errorMessage(t, {
      code: "dependency_cycle",
      params: { ids: ["a", "b"] },
    });
    expect(JSON.parse(cycle).ids).toEqual(["a", "b"]);
  });
});

describe("a store plugin's README (resolveReadmeUrl)", () => {
  const commit = "c".repeat(40);

  it("resolves relative paths against its repo, and only allows http(s)", () => {
    // As the back sends them (readme_base, readme_links).
    const images = `https://raw.githubusercontent.com/a/b/${commit}/`;
    const links = `https://github.com/a/b/blob/${commit}/`;
    expect(resolveReadmeUrl("docs/demo.png", images)).toBe(
      `${images}docs/demo.png`,
    );
    expect(resolveReadmeUrl("./docs/../LICENSE", links)).toBe(
      `${links}LICENSE`,
    );
    expect(resolveReadmeUrl("https://example.org/x", links)).toBe(
      "https://example.org/x",
    );
    expect(resolveReadmeUrl("mailto:me@x.org", links)).toBe("mailto:me@x.org");
    expect(resolveReadmeUrl("#usage", links)).toBe("#usage");
    expect(resolveReadmeUrl("javascript:alert(1)", links)).toBeNull();
    expect(resolveReadmeUrl("data:image/svg+xml,<svg/>", images)).toBeNull();
    // An installed plugin's README, relative paths lead nowhere.
    expect(resolveReadmeUrl("docs/demo.png", null)).toBeNull();
  });
});

it("falls back to the technical detail for an unknown error code", () => {
  const message = JSON.parse(
    errorMessage(t, { code: "new_code", detail: "boom" }),
  );
  expect(message.defaultValue).toBe("boom");
});

describe("the version a preview brings", () => {
  const installed = "v0.1.0";
  const release = (version_change, ref = "v0.1.1") => ({ version_change, ref });

  it("updates to a newer version, or to the same one from a newer tag", () => {
    expect(canUpdateTo(release("newer"), installed)).toBe(true);
    expect(canUpdateTo(release("same"), installed)).toBe(true);
    expect(canUpdateTo(release("same", "v0.1.0"), installed)).toBe(false);
    expect(canUpdateTo(release("older"), installed)).toBe(false);
    // Nothing comparable installed (unreadable manifest), any release fixes it.
    expect(canUpdateTo(release(null), installed)).toBe(true);
  });

  it("says so about an older version, and about the same one when updating", () => {
    expect(versionNotice(release("older"), true)).toBe("olderUpdate");
    expect(versionNotice(release("older"), false)).toBe("older");
    expect(versionNotice({ version_change: "older", ref: null }, false)).toBe(
      "older",
    );
    expect(versionNotice(release("same"), true)).toBe("sameRelease");
    expect(versionNotice(release("same"), false)).toBeNull();
    expect(versionNotice(release("newer"), true)).toBeNull();
    expect(versionNotice(release(null), false)).toBeNull();
  });
});

test("savedPageSize keeps a valid choice and falls back to 9", () => {
  localStorage.clear();
  expect(savedPageSize()).toBe(9);
  localStorage.setItem("plugins.pageSize", "24");
  expect(savedPageSize()).toBe(24);
  localStorage.setItem("plugins.pageSize", "7");
  expect(savedPageSize()).toBe(9);
});
