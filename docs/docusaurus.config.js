// @ts-check
const { themes: prismThemes } = require('prism-react-renderer');

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'DashAI Documentation',
  tagline: 'Open-source ML platform for developers',
  favicon: 'img/favicon.ico',

  url: 'https://DashAISoftware.github.io',
  baseUrl: '/DashAI/',

  organizationName: 'DashAISoftware',
  projectName: 'DashAI',

  onBrokenLinks: 'warn',
  onBrokenMarkdownLinks: 'warn',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: require.resolve('./sidebars.js'),
          editUrl: 'https://github.com/DashAISoftware/DashAI/tree/develop/docs/',
          routeBasePath: '/',
        },
        blog: false,
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      }),
    ],
  ],

  plugins: [
    [
      require.resolve('@easyops-cn/docusaurus-search-local'),
      {
        hashed: true,
        docsRouteBasePath: '/',
      },
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      navbar: {
        title: 'DashAI',
        items: [
          {
            type: 'docSidebar',
            sidebarId: 'gettingStartedSidebar',
            position: 'left',
            label: 'Getting Started',
          },
          {
            type: 'docSidebar',
            sidebarId: 'tutorialsSidebar',
            position: 'left',
            label: 'Tutorials',
          },
          {
            type: 'docSidebar',
            sidebarId: 'componentsSidebar',
            position: 'left',
            label: 'Components',
          },
          {
            type: 'docSidebar',
            sidebarId: 'pluginsSidebar',
            position: 'left',
            label: 'Plugin Development',
          },
          {
            href: 'https://github.com/DashAISoftware/DashAI',
            label: 'GitHub',
            position: 'right',
          },
        ],
      },
      footer: {
        style: 'dark',
        links: [
          {
            title: 'Docs',
            items: [
              { label: 'Getting Started', to: '/getting-started/installation' },
              { label: 'Components', to: '/components/tasks' },
            ],
          },
          {
            title: 'Community',
            items: [
              { label: 'GitHub', href: 'https://github.com/DashAISoftware/DashAI' },
            ],
          },
        ],
        copyright: `Copyright © ${new Date().getFullYear()} DashAI. Licensed under Apache 2.0.`,
      },
      prism: {
        theme: prismThemes.github,
        darkTheme: prismThemes.dracula,
        additionalLanguages: ['python', 'bash', 'json'],
      },
      colorMode: {
        defaultMode: 'light',
        disableSwitch: false,
      },
    }),
};

module.exports = config;
