// @ts-check
const { themes: prismThemes } = require("prism-react-renderer");

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: "DashAI Documentation",
  tagline: "Open-source ML platform for developers",
  favicon: "img/favicon.ico",

  url: "https://DashAISoftware.github.io",
  baseUrl: "/DashAI/",

  organizationName: "DashAISoftware",
  projectName: "DashAI",

  onBrokenLinks: "throw",
  onBrokenMarkdownLinks: "warn",

  i18n: {
    defaultLocale: "en",
    locales: ["en", "es"],
    localeConfigs: {
      en: { label: "English" },
      es: { label: "Español" },
    },
  },

  presets: [
    [
      "classic",
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: require.resolve("./sidebars.js"),
          editUrl:
            "https://github.com/DashAISoftware/DashAI/tree/develop/docs/",
          routeBasePath: "/",
        },
        blog: false,
        theme: {
          customCss: require.resolve("./src/css/custom.css"),
        },
      }),
    ],
  ],

  plugins: [
    [
      require.resolve("@easyops-cn/docusaurus-search-local"),
      {
        hashed: true,
        docsRouteBasePath: "/",
      },
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      navbar: {
        logo: {
          alt: "DashAI",
          src: "img/logo.png",
        },
        items: [
          {
            type: 'docSidebar',
            sidebarId: 'discoverSidebar',
            position: 'left',
            label: 'Discover',
            className: 'navbar-item--discover',
          },
          {
            type: 'docSidebar',
            sidebarId: 'learnSidebar',
            position: 'left',
            label: 'Learn',
            className: 'navbar-item--learn',
          },
          {
            type: 'docSidebar',
            sidebarId: 'deepDiveSidebar',
            position: 'left',
            label: 'Deep Dive',
            className: 'navbar-item--deep-dive',
          },
          {
            type: 'docSidebar',
            sidebarId: 'buildSidebar',
            position: 'left',
            label: 'Build',
            className: 'navbar-item--build',
          },
          {
            type: 'docSidebar',
            sidebarId: 'componentsSidebar',
            position: 'left',
            label: 'Components',
          },
          {
            href: 'https://github.com/DashAISoftware/DashAI',
            label: 'GitHub',
            position: 'right',
          },
        ],
      },
      footer: {
        style: "dark",
        links: [],
        copyright: `© ${new Date().getFullYear()} DashAI — Open Source Platform · Apache 2.0`,
      },
      prism: {
        theme: prismThemes.github,
        darkTheme: prismThemes.dracula,
        additionalLanguages: ["python", "bash", "json"],
      },
      colorMode: {
        defaultMode: "light",
        disableSwitch: false,
      },
      docs: {
        sidebar: {
          hideable: true,
          autoCollapseCategories: false,
        },
      },
    }),
};

module.exports = config;
