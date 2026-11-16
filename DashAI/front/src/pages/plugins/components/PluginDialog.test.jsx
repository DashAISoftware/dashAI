import React from "react";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../../test-utils/renderWithProviders";
import i18n from "../../../utils/i18n";
import {
  discardPreview,
  installPreview,
  previewRemote,
  setPluginEnabled,
  updatePlugin,
} from "../../../api/plugins";
import PluginDialog from "./PluginDialog";

jest.mock("notistack", () => {
  const snackbar = { enqueueSnackbar: jest.fn() };
  return { useSnackbar: () => snackbar };
});
jest.mock("../../../api/plugins", () => ({
  discardPreview: jest.fn(),
  installPreview: jest.fn(),
  pluginError: (error) => error,
  previewRemote: jest.fn(),
  previewUpload: jest.fn(),
  setPluginEnabled: jest.fn(),
  updatePlugin: jest.fn(),
}));
let mockInstalled = [];
jest.mock("../../../hooks/usePlugins", () => ({
  notifyPluginsChanged: jest.fn(),
  useInstalledPlugins: () => ({ plugins: mockInstalled }),
  useStore: () => ({ store: null }),
}));
jest.mock(
  "../../../components/credentials/CredentialsDialog",
  () => () => null,
);

const { enqueueSnackbar } = jest.requireMock("notistack").useSnackbar();

// Store plugin Sentiment Tools needs NLP Core (store) and Text Toolkit (disabled).
const plugin = {
  id: "sentiment-tools",
  name: "Sentiment Tools",
  source: "git",
  can_update: true,
  location: "https://github.com/acme-ml/sentiment-tools",
  ref: "v1.2.0",
  sha256: "a",
};
const preview = (overrides) => ({
  is_valid: true,
  errors: [],
  dependencies: [],
  plugin_dependencies: [],
  version: "1.2.0",
  version_change: null,
  trust_level: "github_attested",
  trust_tier: "attested",
  needs_ack: false,
  sha256: "a",
  removed: null,
  owner: "acme-ml",
  in_store: false,
  replaces_other: false,
  ...overrides,
});
const needs = [
  {
    id: "nlp-core",
    name: "NLP Core",
    state: "store",
    location: "https://github.com/nlp-lab/nlp-core",
    ref: "v2.0.0",
  },
  {
    id: "text-toolkit",
    name: "Text Toolkit",
    state: "disabled",
    location: null,
    ref: null,
  },
];

const open = () => {
  const onDone = jest.fn();
  const onClose = jest.fn();
  renderWithProviders(
    <PluginDialog
      open
      mode="install"
      plugin={plugin}
      onClose={onClose}
      onDone={onDone}
    />,
  );
  return { onDone, onClose };
};

beforeAll(() => i18n.changeLanguage("es"));
beforeEach(() => {
  jest.clearAllMocks();
  mockInstalled = [{ id: "text-toolkit", trust_tier: "attested" }];
  previewRemote.mockImplementation(async (location) =>
    location === plugin.location
      ? preview({
          id: "sentiment-tools",
          name: "Sentiment Tools",
          plugin_dependencies: needs,
          preview: "token-tools",
        })
      : preview({
          id: "nlp-core",
          name: "NLP Core",
          owner: "nlp-lab",
          trust_level: "github_asset",
          trust_tier: "unverified",
          needs_ack: true,
          preview: "token-core",
        }),
  );
});

it("reviews those it needs from the store and installs all in order", async () => {
  installPreview.mockImplementation(async (token) => ({
    name: token === "token-tools" ? "Sentiment Tools" : "NLP Core",
  }));
  setPluginEnabled.mockResolvedValue({ active: true });
  const { onDone } = open();

  await screen.findByRole("checkbox"); // reviewed
  const dialog = screen.getByRole("dialog", {
    name: "Instalar Sentiment Tools",
  });
  expect(previewRemote).toHaveBeenCalledWith(
    "https://github.com/nlp-lab/nlp-core",
    "v2.0.0",
  );
  // What it will download says so and its level, an installed one its state.
  expect(dialog).toHaveTextContent(
    "Plugins que necesitaNLP CoreSe instalará · Sin verificarText ToolkitDesactivado",
  );
  expect(dialog).toHaveTextContent(
    "Se instalará también NLP Core desde la tienda.",
  );
  expect(dialog).toHaveTextContent("Se activará Text Toolkit.");
  // One box, naming every author, because NLP Core's level asks for it.
  const install = within(dialog).getByRole("button", { name: "Instalar" });
  expect(install).toBeDisabled();
  await userEvent.click(
    within(dialog).getByRole("checkbox", {
      name: "Entiendo el riesgo y confío en acme-ml y nlp-lab",
    }),
  );
  await userEvent.click(install);

  await waitFor(() => expect(onDone).toHaveBeenCalled());
  expect(installPreview.mock.calls).toEqual([["token-core"], ["token-tools"]]);
  expect(setPluginEnabled).toHaveBeenCalledWith("text-toolkit", true);
  expect(installPreview.mock.invocationCallOrder[0]).toBeLessThan(
    setPluginEnabled.mock.invocationCallOrder[0],
  );
  expect(onDone).toHaveBeenCalledWith({ name: "Sentiment Tools" }, "install", [
    "NLP Core",
  ]);
});

it("says a repository typed in is in the store", async () => {
  previewRemote.mockResolvedValue(
    preview({
      name: "Sentiment Tools",
      in_store: true,
      preview: "token-tools",
    }),
  );
  renderWithProviders(
    <PluginDialog open mode="install" onClose={jest.fn()} onDone={jest.fn()} />,
  );

  await userEvent.type(
    screen.getByPlaceholderText("https://github.com/owner/repo"),
    `${plugin.location}{Enter}`,
  );
  expect(
    await screen.findByText(
      "Este plugin está en la tienda: sus actualizaciones y avisos vendrán de ella.",
    ),
  ).toBeInTheDocument();
});

it("doesn't flash the store note while it closes", async () => {
  previewRemote.mockResolvedValue(
    preview({
      name: "Sentiment Tools",
      in_store: true,
      preview: "token-tools",
    }),
  );
  // As the catalog does, closing drops the plugin while the dialog fades out
  function Catalog() {
    const [installing, setInstalling] = React.useState(plugin);
    return (
      <PluginDialog
        open={!!installing}
        mode="install"
        plugin={installing}
        onClose={() => setInstalling(null)}
        onDone={jest.fn()}
      />
    );
  }
  renderWithProviders(<Catalog />);

  const dialog = await screen.findByRole("dialog", {
    name: "Instalar Sentiment Tools",
  });
  await within(dialog).findByText("Verificado"); // reviewed
  await userEvent.click(
    within(dialog).getByRole("button", { name: "Cancelar" }),
  );
  expect(dialog).toBeInTheDocument(); // still fading out
  expect(dialog).not.toHaveTextContent("está en la tienda");
});

it("says when it installs an older release of one it needs", async () => {
  const older = [{ ...needs[0], latest: "v3.0.0" }];
  previewRemote.mockResolvedValueOnce(
    preview({ plugin_dependencies: older, preview: "token-tools" }),
  );
  open();

  const dialog = await screen.findByRole("dialog", {
    name: "Instalar Sentiment Tools",
  });
  expect(
    await within(dialog).findByText(
      "Se instalará también NLP Core 2.0.0 desde la tienda. Su última versión requiere actualizar dashAI.",
    ),
  ).toBeInTheDocument();
  expect(dialog).not.toHaveTextContent("Se instalará también NLP Core desde");
});

it("updates an installed one without turning on those it needs", async () => {
  previewRemote.mockResolvedValue(
    preview({
      id: "sentiment-tools",
      name: "Sentiment Tools",
      plugin_dependencies: [needs[1]], // Text Toolkit, disabled
      installed_version: "1.0.0",
      installed_location: plugin.location,
      version_change: "newer",
      preview: "token-tools",
      breaks: ["Plot Kit"],
    }),
  );
  updatePlugin.mockResolvedValue({ name: "Sentiment Tools" });
  const onDone = jest.fn();
  renderWithProviders(
    <PluginDialog
      open
      mode="update"
      plugin={{ ...plugin, ref: "v1.0.0" }}
      updateRef="v1.2.0"
      onClose={jest.fn()}
      onDone={onDone}
    />,
  );

  const dialog = await screen.findByRole("dialog", {
    name: "Actualizar Sentiment Tools",
  });
  expect(
    await within(dialog).findByText(
      "Text Toolkit sigue desactivado; se activará cuando actives Sentiment Tools.",
    ),
  ).toBeInTheDocument();
  expect(dialog).not.toHaveTextContent("Se activará Text Toolkit.");
  expect(dialog).toHaveTextContent(
    "Al instalar esta versión, Plot Kit dejará de funcionar porque necesita otra versión de Sentiment Tools.",
  );
  await userEvent.click(
    within(dialog).getByRole("button", { name: "Actualizar" }),
  );

  await waitFor(() => expect(onDone).toHaveBeenCalled());
  expect(updatePlugin).toHaveBeenCalledWith("sentiment-tools", "token-tools");
  expect(setPluginEnabled).not.toHaveBeenCalled();
});

it("turns none on either over an installed one it can't read", async () => {
  // Damaged manifest and .source, so only the list knows it is installed.
  mockInstalled.push({ id: "sentiment-tools", trust_tier: "unknown" });
  previewRemote.mockResolvedValue(
    preview({
      id: "sentiment-tools",
      name: "Sentiment Tools",
      plugin_dependencies: [needs[1]], // Text Toolkit, disabled
      preview: "token-tools",
    }),
  );
  installPreview.mockResolvedValue({ name: "Sentiment Tools" });
  const { onDone } = open();

  expect(
    await screen.findByText(
      "Text Toolkit sigue desactivado; se activará cuando actives Sentiment Tools.",
    ),
  ).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Instalar" }));
  await waitFor(() => expect(onDone).toHaveBeenCalled());
  expect(setPluginEnabled).not.toHaveBeenCalled();
});

it("says what stayed installed when it fails after them", async () => {
  installPreview.mockImplementation(async (token) => {
    if (token === "token-tools") throw { code: "load_failed", params: {} };
    return { name: "NLP Core" };
  });
  setPluginEnabled.mockResolvedValue({ active: true });
  open();
  await userEvent.click(await screen.findByRole("checkbox"));
  await userEvent.click(screen.getByRole("button", { name: "Instalar" }));

  await waitFor(() =>
    expect(enqueueSnackbar).toHaveBeenCalledWith(
      "NLP Core quedó instalado, pero Sentiment Tools no se pudo instalar.",
      { variant: "error" },
    ),
  );
});

it("discards every preview when closed", async () => {
  const { onClose } = open();
  await screen.findByRole("checkbox"); // reviewed
  await userEvent.click(screen.getByRole("button", { name: "Cancelar" }));
  expect(onClose).toHaveBeenCalled();
  expect(discardPreview.mock.calls).toEqual([["token-tools"], ["token-core"]]);
});

it("can't install when one it needs can't be had", async () => {
  previewRemote.mockResolvedValue(
    preview({
      is_valid: false,
      errors: [
        {
          code: "missing_plugin_dependency",
          detail: "",
          params: { id: "text-toolkit" },
        },
        {
          code: "dependency_cycle",
          detail: "",
          params: { ids: ["sentiment-tools", "text-toolkit"] },
        },
      ],
      preview: null,
    }),
  );
  open();
  expect(
    await screen.findByText(
      "Necesita el plugin «text-toolkit», que no está instalado ni publicado en la tienda. Instálalo primero desde un .zip o GitHub.",
    ),
  ).toBeInTheDocument();
  expect(
    screen.getByText(
      "Los plugins sentiment-tools y text-toolkit se necesitan entre sí, así que ninguno se puede instalar.",
    ),
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Instalar" })).toBeDisabled();
});
