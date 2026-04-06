import React from "react";
import Link from "@docusaurus/Link";
import useBaseUrl from "@docusaurus/useBaseUrl";
import useDocusaurusContext from "@docusaurus/useDocusaurusContext";
import Layout from "@theme/Layout";

const CARDS = [
  {
    emoji: "🚀",
    title: "Primeros Pasos",
    desc: "Instalación, inicio rápido y descripción general de la arquitectura",
    to: "/getting-started/installation",
  },
  {
    emoji: "📖",
    title: "Tutoriales",
    desc: "Guías paso a paso: cargar datos, entrenar modelos, predecir, explorar",
    to: "/tutorials/upload-dataset",
  },
  {
    emoji: "📦",
    title: "Referencia de Componentes",
    desc: "Más de 112 modelos, convertidores, métricas, exploradores y más — generados automáticamente desde el código fuente",
    to: "/components/models",
  },
  {
    emoji: "🔌",
    title: "Desarrollo de Plugins",
    desc: "Crea y publica tus propios componentes para DashAI",
    to: "/plugin-development/overview",
  },
];

export default function Home() {
  const { siteConfig } = useDocusaurusContext();
  const logoSrc = useBaseUrl("/img/logo.png");
  return (
    <Layout title="Documentación" description={siteConfig.tagline}>
      <div className="dashai-home">
        <div className="dashai-hero">
          <img className="dashai-hero__logo" src={logoSrc} alt="DashAI" />
          <h1 className="dashai-hero__title">Documentación de DashAI</h1>
          <p className="dashai-hero__subtitle">
            Tu guía completa para la plataforma de Machine Learning de código
            abierto sin necesidad de programar.
          </p>
          <div className="dashai-hero__actions">
            <Link
              className="button button--primary button--lg"
              to="/getting-started/installation"
            >
              Comenzar →
            </Link>
            <Link
              className="button button--outline button--lg"
              to="/components/models"
            >
              Componentes
            </Link>
          </div>
        </div>
        <div className="dashai-info">
          <strong>ℹ Info:</strong> DashAI v0.3.0 — código abierto bajo MIT. Las
          páginas de referencia de componentes se generan automáticamente desde
          el código fuente en cada compilación.
        </div>
        <div className="dashai-section-title">Explora la documentación</div>
        <div className="dashai-cards">
          {CARDS.map((card) => (
            <Link key={card.title} to={card.to} className="dashai-card">
              <div className="dashai-card__title">
                {card.emoji} {card.title}
              </div>
              <div className="dashai-card__desc">{card.desc}</div>
            </Link>
          ))}
        </div>
        <div className="dashai-ack">
          <p>
            Patrocinado por CENIA (FB210017) e IMFD (ICN17_002). Desarrollado
            por estudiantes de DCC UChile y UTFSM.
          </p>
        </div>
      </div>
    </Layout>
  );
}
