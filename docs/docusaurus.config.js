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
          },
          {
            type: 'docSidebar',
            sidebarId: 'learnSidebar',
            position: 'left',
            label: 'Learn',
          },
          {
            type: 'docSidebar',
            sidebarId: 'deepDiveSidebar',
            position: 'left',
            label: 'Deep Dive',
          },
          {
            type: 'docSidebar',
            sidebarId: 'buildSidebar',
            position: 'left',
            label: 'Build',
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
        links: [
          {
            title: 'Discover',
            items: [
              { label: 'Overview', to: '/discover/overview' },
              { label: 'Installation', to: '/discover/installation' },
            ],
          },
          {
            title: 'Learn',
            items: [
              { label: 'Tutorials', to: '/learn/tutorials/upload-dataset' },
              { label: 'Module Guides', to: '/learn/guides/datasets' },
            ],
          },
          {
            title: 'Build',
            items: [
              { label: 'REST API', to: '/build/rest-api' },
              { label: 'Plugin Development', to: '/build/plugin-development/overview' },
              { label: 'GitHub', href: 'https://github.com/DashAISoftware/DashAI' },
            ],
          },
        ],
        copyright: `Copyright © ${new Date().getFullYear()} DashAI. Licensed under Apache 2.0.`,
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
    }),
};

module.exports = config;
