import React from "react";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { renderWithProviders } from "../../../test-utils/renderWithProviders";
import i18n from "../../../utils/i18n";
import {
  getPluginReadme,
  getStoreReadme,
  setPluginEnabled,
} from "../../../api/plugins";
import PluginsDetails from "./PluginsDetails";

jest.mock("notistack", () => {
  const snackbar = { enqueueSnackbar: jest.fn() };
  return { useSnackbar: () => snackbar };
});
jest.mock("../../../api/plugins", () => ({
  getPluginReadme: jest.fn(),
  getStoreReadme: jest.fn(),
  pluginError: (error) => error,
  setPluginEnabled: jest.fn(),
  uninstallPlugin: jest.fn(),
}));
let mockPlugins = [];
let mockStore = null;
jest.mock("../../../hooks/usePlugins", () => ({
  notifyPluginsChanged: jest.fn(),
  useAnnounceInstalled: () => jest.fn(),
  useInstalledPlugins: () => ({ plugins: mockPlugins, loading: false }),
  usePluginUpdates: () => ({ updates: {} }),
  useStore: () => ({ store: mockStore, loading: false }),
}));
// Not under test, and they pull in ESM Jest does not transform.
jest.mock("./PluginDialog", () => () => null);
jest.mock("./PluginSettings", () => () => null);
jest.mock(
  "./Readme",
  () =>
    ({ text, urls }) =>
      urls ? `${text} @ ${urls.images}` : text,
);

const { enqueueSnackbar } = jest.requireMock("notistack").useSnackbar();

// As in the Design, Sentiment Tools needs Text Toolkit, which needs NLP Core.
const installed = (id, name, needs = [], overrides = {}) => ({
  id,
  name,
  version: "1.0.0",
  components: [],
  component_types: [],
  dependencies: [],
  plugin_dependencies: needs,
  authors: [],
  project_urls: {},
  enabled: true,
  active: true,
  source: "local",
  location: "kit.zip",
  trust_level: "local",
  trust_tier: "local",
  ...overrides,
});
const off = { enabled: false, active: false };
const core = installed("nlp-core", "NLP Core");
const toolkit = installed("text-toolkit", "Text Toolkit", ["nlp-core"]);
const tools = installed("sentiment-tools", "Sentiment Tools", ["text-toolkit"]);

const open = (id) =>
  renderWithProviders(
    <Routes>
      <Route path="/app/plugins/:pluginId" element={<PluginsDetails />} />
    </Routes>,
    { route: `/app/plugins/${id}` },
  );

beforeAll(() => i18n.changeLanguage("es"));
beforeEach(() => {
  jest.clearAllMocks();
  mockStore = null;
  getPluginReadme.mockResolvedValue(null);
});

it("reads the README of the open plugin when it opens", async () => {
  mockPlugins = [core];
  getPluginReadme.mockResolvedValueOnce("# NLP Core usage");
  open("nlp-core");

  expect(await screen.findByText("# NLP Core usage")).toBeInTheDocument();
  expect(getPluginReadme).toHaveBeenCalledWith("nlp-core");
});

it("resolves its README's images at the installed commit", async () => {
  const base = "https://raw.githubusercontent.com/acme/core/c1/";
  mockPlugins = [installed("nlp-core", "NLP Core", [], { readme_base: base })];
  getPluginReadme.mockResolvedValueOnce("# NLP Core usage");
  open("nlp-core");

  expect(
    await screen.findByText(`# NLP Core usage @ ${base}`),
  ).toBeInTheDocument();
});

it("asks before turning off a plugin others need, naming them", async () => {
  mockPlugins = [tools, toolkit, core];
  setPluginEnabled.mockResolvedValue({ ...core, ...off });
  open("nlp-core");
  await userEvent.click(screen.getByRole("switch"));

  const dialog = screen.getByRole("dialog", { name: "¿Desactivar NLP Core?" });
  expect(
    within(dialog)
      .getAllByRole("listitem")
      .map((item) => item.textContent),
  ).toEqual(["Text Toolkit", "Sentiment Tools"]);
  expect(setPluginEnabled).not.toHaveBeenCalled();
  await userEvent.click(
    within(dialog).getByRole("button", { name: "Desactivar" }),
  );
  expect(setPluginEnabled).toHaveBeenCalledWith("nlp-core", false, {
    allowBlocked: false,
  });
});

it("turns on what it needs first, in order, after asking", async () => {
  mockPlugins = [
    { ...tools, ...off },
    { ...toolkit, ...off },
    { ...core, ...off },
  ];
  setPluginEnabled.mockImplementation(async (id) => ({ id, active: true }));
  open("sentiment-tools");
  await userEvent.click(screen.getByRole("switch"));

  const dialog = screen.getByRole("dialog", {
    name: "¿Activar Sentiment Tools?",
  });
  expect(dialog).toHaveTextContent(
    "Para activar Sentiment Tools también se activarán:",
  );
  await userEvent.click(
    within(dialog).getByRole("button", { name: "Activar" }),
  );
  await waitFor(() => expect(setPluginEnabled).toHaveBeenCalledTimes(3));
  expect(setPluginEnabled.mock.calls.map(([id]) => id)).toEqual([
    "nlp-core",
    "text-toolkit",
    "sentiment-tools",
  ]);
  expect(enqueueSnackbar).toHaveBeenCalledWith(
    "Sentiment Tools activado junto con NLP Core y Text Toolkit.",
    { variant: "info" },
  );
});

it("stops when one it needs does not turn on", async () => {
  mockPlugins = [{ ...tools, ...off }, { ...toolkit, ...off }, core];
  setPluginEnabled.mockRejectedValue({ code: "load_failed" });
  open("sentiment-tools");
  await userEvent.click(screen.getByRole("switch"));
  await userEvent.click(screen.getByRole("button", { name: "Activar" }));

  await waitFor(() =>
    expect(enqueueSnackbar).toHaveBeenCalledWith(
      "No se pudo activar Text Toolkit. Sentiment Tools quedó como estaba.",
      { variant: "error" },
    ),
  );
  expect(setPluginEnabled).toHaveBeenCalledTimes(1);
});

it("turns it on too when one it needs works only after reopening", async () => {
  mockPlugins = [{ ...tools, ...off }, { ...toolkit, ...off }, core];
  const restart = { code: "restart_required", detail: "" };
  setPluginEnabled.mockImplementation(async (id) =>
    id === "text-toolkit"
      ? { id, enabled: true, active: false, problem: restart }
      : { id, enabled: true, active: false, problem: null },
  );
  open("sentiment-tools");
  await userEvent.click(screen.getByRole("switch"));
  await userEvent.click(screen.getByRole("button", { name: "Activar" }));

  await waitFor(() => expect(setPluginEnabled).toHaveBeenCalledTimes(2));
  expect(enqueueSnackbar).toHaveBeenCalledWith(
    "Es necesario reiniciar dashAI",
    { variant: "warning" },
  );
});

it("can't be turned on while one it needs is not installed, and says why", async () => {
  const stopped = {
    ...tools,
    active: false,
    problem: { code: "dependency_unavailable", detail: "" },
  };
  mockPlugins = [stopped];
  open("sentiment-tools");

  expect(screen.getByRole("switch")).toBeDisabled();
  expect(screen.getByRole("alert")).toHaveTextContent(
    "Necesita otro pluginNecesita text-toolkit, que no está instalado.",
  );
  await userEvent.hover(screen.getByText("Desactivado"));
  expect(await screen.findByRole("tooltip")).toHaveTextContent(
    "Necesita text-toolkit, que no está instalado.",
  );
  // Neither installed nor in the store, so there is no page to link to.
  const panel = screen.getByRole("complementary");
  expect(panel).toHaveTextContent(
    "Plugins que necesita · 1text-toolkitNo está instalado ni en la tienda",
  );
  expect(
    within(panel).queryByRole("link", { name: "text-toolkit" }),
  ).not.toBeInTheDocument();
  // Published in the store, but missing for the installed one.
  mockStore = { plugins: [{ id: "text-toolkit", offered: "v1.0.0" }] };
  open("sentiment-tools");
  const listed = screen.getAllByRole("complementary").at(-1);
  expect(listed).toHaveTextContent(
    "Plugins que necesita · 1text-toolkitNo instalado",
  );
  expect(
    within(listed).getByRole("link", { name: "text-toolkit" }),
  ).toHaveAttribute("href", "/app/plugins/text-toolkit");
});

it("links the notice to the plugin it needs", () => {
  mockPlugins = [
    {
      ...tools,
      active: false,
      problem: { code: "dependency_unavailable", detail: "" },
    },
    { ...toolkit, ...off },
    core,
  ];
  open("sentiment-tools");
  expect(screen.getByRole("switch")).toBeEnabled();
  expect(
    within(screen.getByRole("alert")).getByRole("link", {
      name: "Text Toolkit",
    }),
  ).toHaveAttribute("href", "/app/plugins/text-toolkit");
  // The panel, what it needs and its state.
  const panel = screen.getByRole("complementary");
  expect(panel).toHaveTextContent(
    "Plugins que necesita · 1Text ToolkitDesactivado",
  );
});

it("shows a level the front has no texts for by its tier", async () => {
  mockPlugins = [
    installed("gl-kit", "GL Kit", [], {
      source: "gitlab",
      location: "https://gitlab.com/acme/gl-kit",
      can_update: true,
      web_url: "https://gitlab.com/acme/gl-kit",
      ref: "v1.0.0",
      commit: "abcdef1234567890",
      trust_level: "gitlab_source",
      trust_tier: "source",
    }),
  ];
  open("gl-kit");
  const panel = screen.getByRole("complementary");
  expect(panel).toHaveTextContent("Parcialmente verificado");
  expect(panel).toHaveTextContent("comprobado por su origen.");

  await userEvent.click(screen.getByRole("button", { name: "Ver detalles" }));
  expect(panel).toHaveTextContent("Commitabcdef1234");
});

it("lists in the panel the active plugins that need it, without a state", () => {
  mockPlugins = [tools, toolkit, core];
  open("text-toolkit");
  const panel = screen.getByRole("complementary");
  expect(panel).toHaveTextContent("Plugins que necesita · 1NLP CoreActivo");
  expect(panel).toHaveTextContent(
    /Plugins que lo necesitan · 1Sentiment Tools$/,
  );
});

it("shows when it was updated only if it ever was", () => {
  const at = "2026-10-03T16:05:00Z";
  mockPlugins = [
    installed("nlp-core", "NLP Core", [], { installed_at: at, updated_at: at }),
  ];
  open("nlp-core");
  const panel = screen.getByRole("complementary");
  expect(panel).toHaveTextContent("Instalado");
  expect(panel).not.toHaveTextContent("Actualizado");
});

it("names the newest release in the notice and shortens what it offers", async () => {
  const sha =
    "5cba6a8752955bb71fffc35e29763c61548f0322f348d3fe84d4e3b287ea534c";
  const release = {
    dependencies: [],
    plugin_dependencies: [],
    trust_level: "github_attested",
    trust_tier: "attested",
  };
  mockPlugins = [];
  mockStore = {
    plugins: [
      {
        id: "kit",
        name: "Kit",
        source: "git",
        location: "https://github.com/acme/kit",
        web_url: "https://github.com/acme/kit",
        offered: "v1.0.0",
        license: "MIT",
        authors: [{ name: "Ana" }],
        components: [],
        component_types: [],
        project_urls: {},
        releases: [
          {
            ...release,
            tag: "v1.1.0",
            version: "1.1.0",
            min_app_version: "0.11.0",
          },
          { ...release, tag: "v1.0.0", version: "1.0.0", sha256: sha },
        ],
      },
    ],
  };
  getStoreReadme.mockResolvedValue(null);
  const writeText = jest.fn().mockResolvedValue();
  Object.assign(navigator, { clipboard: { writeText } });
  open("kit");

  expect(screen.getByRole("alert")).toHaveTextContent(
    "La v1.1.0 requiere dashAI 0.11.0 o posterior.",
  );
  const panel = screen.getByRole("complementary");
  expect(panel).toHaveTextContent("PublicaciónVersiónv1.0.0");
  expect(panel).not.toHaveTextContent("Autor"); // its name alone, already on the card
  await userEvent.click(screen.getByRole("button", { name: "Ver detalles" }));
  expect(panel).not.toHaveTextContent("Tag"); // the version already says it
  expect(panel).toHaveTextContent("SHA-2565cba6a8752955bb7…");
  await userEvent.click(within(panel).getByRole("button", { name: "Copiar" }));
  expect(writeText).toHaveBeenCalledWith(sha);
});

it("lists the plugins that need it before uninstalling it", async () => {
  mockPlugins = [tools, toolkit, core];
  open("text-toolkit");
  await userEvent.click(screen.getByRole("button", { name: "Desinstalar" }));
  const dialog = screen.getByRole("dialog", {
    name: "Confirmar desinstalación",
  });
  expect(dialog).toHaveTextContent(
    "Estos plugins lo necesitan y dejarán de funcionar hasta que lo vuelvas a instalar:",
  );
  const warning = within(dialog).getByRole("alert");
  expect(warning).toHaveTextContent(
    "Estos plugins lo necesitan y dejarán de funcionar hasta que lo vuelvas a instalar:Sentiment Tools",
  );
  expect(within(warning).getByRole("listitem")).toHaveTextContent(
    "Sentiment Tools",
  );
});
