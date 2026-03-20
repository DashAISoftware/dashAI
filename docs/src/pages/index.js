import React from 'react';
import Link from '@docusaurus/Link';
import useBaseUrl from '@docusaurus/useBaseUrl';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';

const CARDS = [
  {
    emoji: '🚀',
    title: 'Getting Started',
    desc: 'Installation, quick start, and architecture overview',
    to: '/getting-started/installation',
  },
  {
    emoji: '📖',
    title: 'Tutorials',
    desc: 'Step-by-step guides: upload data, train models, predict, explore',
    to: '/tutorials/upload-dataset',
  },
  {
    emoji: '📦',
    title: 'Component Reference',
    desc: '112 models, converters, metrics, explorers and more — auto-generated from source',
    to: '/components/models',
  },
  {
    emoji: '🔌',
    title: 'Plugin Development',
    desc: 'Build and publish your own DashAI components',
    to: '/plugin-development/overview',
  },
];

export default function Home() {
  const { siteConfig } = useDocusaurusContext();
  const logoSrc = useBaseUrl('/img/logo.png');
  return (
    <Layout title="Documentation" description={siteConfig.tagline}>
      <div className="dashai-home">

        <div className="dashai-hero">
          <img
            className="dashai-hero__logo"
            src={logoSrc}
            alt="DashAI"
          />
          <h1 className="dashai-hero__title">DashAI Documentation</h1>
          <p className="dashai-hero__subtitle">
            Your complete guide to the open-source, no-code Machine Learning platform.
          </p>
          <div className="dashai-hero__actions">
            <Link
              className="button button--primary button--lg"
              to="/getting-started/installation"
            >
              Get Started →
            </Link>
            <Link
              className="button button--outline button--lg"
              to="/components/models"
            >
              Components
            </Link>
          </div>
        </div>

        <div className="dashai-info">
          <strong>ℹ Info:</strong> DashAI v0.3.0 — open source under Apache 2.0.
          Component reference pages are auto-generated from source code on every build.
        </div>

        <div className="dashai-section-title">Explore the documentation</div>

        <div className="dashai-cards">
          {CARDS.map((card) => (
            <Link key={card.title} to={card.to} className="dashai-card">
              <div className="dashai-card__title">{card.emoji} {card.title}</div>
              <div className="dashai-card__desc">{card.desc}</div>
            </Link>
          ))}
        </div>

        <div className="dashai-ack">
          <p>
            Sponsored by CENIA (FB210017) and IMFD (ICN17_002).
            Developed by students of DCC UChile and UTFSM.
          </p>
        </div>

      </div>
    </Layout>
  );
}
