import React from "react";
import Link from "@docusaurus/Link";
import useBaseUrl from "@docusaurus/useBaseUrl";
import useDocusaurusContext from "@docusaurus/useDocusaurusContext";
import Layout from "@theme/Layout";

const SECTIONS = [
  {
    id: "discover",
    label: "Discover",
    title: "What is DashAI?",
    desc: "Overview, key features, installation, and use cases — for new users",
    to: "/discover/overview",
  },
  {
    id: "learn",
    label: "Learn",
    title: "Tutorials & Guides",
    desc: "Step-by-step tutorials, module guides, and complete ML flows",
    to: "/learn/tutorials/upload-dataset",
  },
  {
    id: "deep-dive",
    label: "Deep Dive",
    title: "Architecture & Internals",
    desc: "Platform architecture, component registry, metrics, and explainability",
    to: "/deep-dive/architecture",
  },
  {
    id: "build",
    label: "Build",
    title: "API & Development",
    desc: "REST API reference, plugin development, dev setup, and contributing",
    to: "/build/rest-api",
  },
];

export default function Home() {
  const { siteConfig } = useDocusaurusContext();
  const logoSrc = useBaseUrl("/img/logo.png");
  const sponsorLogosSrc = useBaseUrl("/img/logos.png");
  return (
    <Layout title="Documentation" description={siteConfig.tagline}>
      <div className="dashai-home">
        <div className="dashai-hero">
          <img className="dashai-hero__logo" src={logoSrc} alt="DashAI" />
          <h1 className="dashai-hero__title">DashAI Documentation</h1>
          <p className="dashai-hero__subtitle">
            Your complete guide to the open-source, no-code Machine Learning
            platform.
          </p>
          <div className="dashai-hero__actions">
            <Link
              className="button button--primary button--lg"
              to="/discover/installation"
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
          <strong>ℹ Info:</strong> DashAI v0.3.0 — open source under Apache
          2.0. Component reference pages are auto-generated from source code on
          every build.
        </div>

        <div className="dashai-section-title">Explore the documentation</div>

        <div className="dashai-section-cards">
          {SECTIONS.map((sec) => (
            <Link
              key={sec.id}
              to={sec.to}
              className={`dashai-section-card dashai-section-card--${sec.id}`}
            >
              <div className="dashai-section-card__label">{sec.label}</div>
              <div className="dashai-section-card__title">{sec.title}</div>
              <div className="dashai-section-card__desc">{sec.desc}</div>
            </Link>
          ))}
        </div>

        <div className="dashai-ack">
          <img
            className="dashai-ack__logos"
            src={sponsorLogosSrc}
            alt="Sponsor logos: DCC, Universidad de Chile, CENIA, and IMFD"
          />
          <p>
            Sponsored by CENIA (FB210017) and IMFD (ICN17_002). Developed by
            students of DCC UChile and UTFSM.
          </p>
        </div>
      </div>
    </Layout>
  );
}
