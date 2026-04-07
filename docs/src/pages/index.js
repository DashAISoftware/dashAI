import React from "react";
import Link from "@docusaurus/Link";
import useBaseUrl from "@docusaurus/useBaseUrl";
import useDocusaurusContext from "@docusaurus/useDocusaurusContext";
import Layout from "@theme/Layout";

const SECTIONS = [
  {
    id: "discover",
    colorVar: "--dashai-discover",
    bgVar: "--dashai-discover-bg",
    label: "Discover",
    title: "What is DashAI?",
    desc: "Overview, key features, installation, and use cases — for new users",
    to: "/discover/overview",
  },
  {
    id: "learn",
    colorVar: "--dashai-learn",
    bgVar: "--dashai-learn-bg",
    label: "Learn",
    title: "Tutorials & Guides",
    desc: "Step-by-step tutorials, module guides, and complete ML flows",
    to: "/learn/tutorials/upload-dataset",
  },
  {
    id: "deep-dive",
    colorVar: "--dashai-deep-dive",
    bgVar: "--dashai-deep-dive-bg",
    label: "Deep Dive",
    title: "Architecture & Internals",
    desc: "Platform architecture, component registry, metrics, and explainability",
    to: "/deep-dive/architecture",
  },
  {
    id: "build",
    colorVar: "--dashai-build",
    bgVar: "--dashai-build-bg",
    label: "Build",
    title: "API & Development",
    desc: "REST API reference, plugin development, dev setup, and contributing",
    to: "/build/dev-setup",
  },
];

export default function Home() {
  const { siteConfig } = useDocusaurusContext();
  const sponsorLogosSrc = useBaseUrl("/img/logos.png");
  return (
    <Layout title="Documentation" description={siteConfig.tagline}>
      <div className="dashai-home">
        {/* ── Hero gradient banner ── */}
        <div className="dashai-landing-hero">
          <h1 className="dashai-landing-hero__title">DashAI Documentation</h1>
          <p className="dashai-landing-hero__subtitle">
            Your complete guide to the open-source, no-code Machine Learning
            platform.
          </p>
        </div>

        {/* ── 4 macro-section cards ── */}
        <div className="dashai-landing-cards">
          {SECTIONS.map((sec) => (
            <Link
              key={sec.id}
              to={sec.to}
              className={`dashai-landing-card dashai-landing-card--${sec.id}`}
            >
              <div className="dashai-landing-card__header">
                <div
                  className="dashai-landing-card__bar"
                  style={{ background: `var(${sec.colorVar})` }}
                />
                <span
                  className="dashai-landing-card__label"
                  style={{ color: `var(${sec.colorVar})` }}
                >
                  {sec.label}
                </span>
              </div>
              <div className="dashai-landing-card__title">{sec.title}</div>
              <div className="dashai-landing-card__desc">{sec.desc}</div>
            </Link>
          ))}
        </div>

        {/* ── "New to DashAI?" CTA ── */}
        <div className="dashai-cta">
          <span className="dashai-cta__icon">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z" />
              <path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z" />
            </svg>
          </span>
          <div className="dashai-cta__body">
            <div className="dashai-cta__heading">New to DashAI?</div>
            <div className="dashai-cta__text">
              Follow the Getting Started guide to understand the platform step
              by step.
            </div>
          </div>
          <Link
            to="/discover/workbench"
            className="dashai-cta__btn"
          >
            Get Started
          </Link>
        </div>

        {/* ── Acknowledgments ── */}
        <div className="dashai-ack">
          <div className="dashai-ack__label">ACKNOWLEDGMENTS</div>
          <p className="dashai-ack__text">
            Sponsored by CENIA (FB210017) and IMFD (ICN17_002). Developed by
            students of DCC UChile and UTFSM.
          </p>
          <img
            className="dashai-ack__logos"
            src={sponsorLogosSrc}
            alt="Sponsor logos: DCC UChile, UTFSM, CENIA, IMFD"
          />
        </div>
      </div>
    </Layout>
  );
}
