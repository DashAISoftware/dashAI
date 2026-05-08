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
    title: "¿Qué es DashAI?",
    desc: "Descripción general, características clave, instalación y casos de uso — para nuevos usuarios",
    to: "/discover/overview",
  },
  {
    id: "learn",
    colorVar: "--dashai-learn",
    bgVar: "--dashai-learn-bg",
    label: "Learn",
    title: "Tutoriales y Guías",
    desc: "Tutoriales paso a paso, guías de módulos y flujos completos de ML",
    to: "/learn/tutorials/upload-dataset",
  },
  {
    id: "deep-dive",
    colorVar: "--dashai-deep-dive",
    bgVar: "--dashai-deep-dive-bg",
    label: "Deep Dive",
    title: "Arquitectura e Internos",
    desc: "Arquitectura de la plataforma, registro de componentes, métricas y explicabilidad",
    to: "/deep-dive/architecture",
  },
  {
    id: "build",
    colorVar: "--dashai-build",
    bgVar: "--dashai-build-bg",
    label: "Build",
    title: "API y Desarrollo",
    desc: "Referencia de la API REST, desarrollo de plugins, configuración del entorno y contribuciones",
    to: "/build/dev-setup",
  },
];

export default function Home() {
  const { siteConfig } = useDocusaurusContext();
  const logos = [
    {
      name: "DCC Universidad de Chile",
      url: "https://dcc.uchile.cl/",
      src: useBaseUrl("/img/institutions/dcc-logo.png"),
      small: true,
    },
    {
      name: "Universidad Técnica Federico Santa María",
      url: "https://www.usm.cl/",
      src: useBaseUrl("/img/institutions/utfsm-logo.png"),
      small: true,
    },
    {
      name: "Centro Nacional de Inteligencia Artificial",
      url: "https://www.cenia.cl/",
      src: useBaseUrl("/img/institutions/cenia-logo.png"),
    },
    {
      name: "Instituto Milenio Fundamentos de los Datos",
      url: "https://www.imfd.cl/",
      src: useBaseUrl("/img/institutions/imfd-logo.png"),
    },
    {
      name: "Agencia Nacional de Investigación y Desarrollo (ANID)",
      url: "https://www.anid.cl/",
      src: useBaseUrl("/img/institutions/anid-logo.png"),
    },
  ];
  return (
    <Layout title="Documentación" description={siteConfig.tagline}>
      <div className="dashai-home">
        {/* ── Hero gradient banner ── */}
        <div className="dashai-landing-hero">
          <h1 className="dashai-landing-hero__title">
            Documentación de DashAI
          </h1>
          <p className="dashai-landing-hero__subtitle">
            Tu guía completa para la plataforma de Machine Learning de código
            abierto sin necesidad de programar.
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
            <div className="dashai-cta__heading">¿Nuevo en DashAI?</div>
            <div className="dashai-cta__text">
              Sigue la guía de inicio para entender la plataforma paso a paso.
            </div>
          </div>
          <Link to="/discover/workbench" className="dashai-cta__btn">
            Comenzar
          </Link>
        </div>

        {/* ── Acknowledgments ── */}
        <div className="dashai-ack">
          <div className="dashai-ack__label">AGRADECIMIENTOS</div>
          <p className="dashai-ack__text">
            Este trabajo es patrocinado por ANID a través de Fondef IDEA
            ID25I10330 y por subvenciones a los centros CENIA (FB210017) e IMFD
            (ICN17_002). Desarrollado por estudiantes de DCC UChile y UTFSM.
          </p>
          <div className="dashai-ack__logos">
            {logos.map((logo) => (
              <a
                key={logo.name}
                href={logo.url}
                target="_blank"
                rel="noopener noreferrer"
                className="dashai-ack__logo-card"
                aria-label={logo.name}
              >
                <img
                  className={`dashai-ack__logo${
                    logo.small ? " dashai-ack__logo--small" : ""
                  }`}
                  src={logo.src}
                  alt={logo.name}
                />
              </a>
            ))}
          </div>
        </div>
      </div>
    </Layout>
  );
}
