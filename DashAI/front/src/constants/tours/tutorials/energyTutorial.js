import React from "react";

export const energyTutorialSteps = [
  {
    target: "body",
    content: (
      <div>
        <h3>Tutorial: Energy Dataset</h3>
        <p>Este es un tutorial para este dataset en específico.</p>
        <p>
          Aquí aprenderás a explorar y analizar los datos de energía disponibles
          en DashAI.
        </p>
      </div>
    ),
    placement: "center",
    disableBeacon: true,
  },
  {
    target: 'a[href="/app/models"]',
    content: (
      <div>
        <h3>Ir a Modelos</h3>
        <p>
          Ahora ve al módulo de <strong>Modelos</strong> para entrenar un modelo
          con el dataset Energy.
        </p>
      </div>
    ),
    placement: "bottom",
    disableBeacon: true,
    spotlightClicks: true,
    isInteractive: true,
    hideFooter: true,
    disableOverlayClose: true,
  },
];

export const energyModelsSteps = [
  {
    target: '[data-tour-extra="regression-task"]',
    content: (
      <div>
        <h3>Tarea de Regresión</h3>
        <p>
          Selecciona la tarea de <strong>Regresión</strong> para entrenar un
          modelo que prediga valores continuos con el dataset Energy.
        </p>
      </div>
    ),
    placement: "bottom",
    disableBeacon: true,
    spotlightClicks: true,
    isInteractive: true,
    hideFooter: true,
    disableOverlayClose: true,
  },
  {
    target: '[data-tour="models-dataset-selection"] .MuiInputBase-root',
    content: (
      <div>
        <h3>Elegir Dataset</h3>
        <p>
          Selecciona el dataset <strong>Energy</strong> del selector y luego haz
          clic en <strong>Siguiente</strong>.
        </p>
      </div>
    ),
    placement: "top",
    disableBeacon: true,
    disableOverlayClose: true,
  },
  {
    target: '[data-tour="create-session-button"]',
    content: (
      <div>
        <h3>Crear Sesión</h3>
        <p>
          Haz clic en <strong>Create Session</strong> para entrenar el modelo
          con el dataset Energy.
        </p>
      </div>
    ),
    placement: "top",
    disableBeacon: true,
    spotlightClicks: true,
    isInteractive: true,
    hideFooter: true,
    disableOverlayClose: true,
  },
];

export const energySessionSteps = [
  {
    target: '[data-tour="first-model"]',
    content: (
      <div>
        <h3>Agregar Modelo</h3>
        <p>
          Haz clic en cualquier modelo del panel derecho para agregarlo a la
          sesión.
        </p>
      </div>
    ),
    placement: "left",
    disableBeacon: true,
    spotlightClicks: true,
    isInteractive: true,
    hideFooter: true,
    disableOverlayClose: true,
  },
  {
    target: '[data-tour="add-model-button"]',
    content: (
      <div>
        <h3>Confirmar Modelo</h3>
        <p>
          Haz clic en <strong>Add Model</strong> para agregar el modelo a la
          sesión.
        </p>
      </div>
    ),
    placement: "top",
    disableBeacon: true,
    spotlightClicks: true,
    isInteractive: true,
    hideFooter: true,
    disableOverlayClose: true,
  },
  {
    target: '[data-tour="train-button"]',
    content: (
      <div>
        <h3>Entrenar Modelo</h3>
        <p>
          Haz clic en <strong>Train</strong> para entrenar el modelo con el
          dataset Energy.
        </p>
      </div>
    ),
    placement: "top",
    disableBeacon: true,
    spotlightClicks: true,
    isInteractive: true,
    hideFooter: true,
    disableOverlayClose: true,
  },
  {
    target: '[data-tour="predictions-tab"]',
    content: (
      <div>
        <h3>Pestaña de Predicciones</h3>
        <p>
          Cuando termine el entrenamiento, haz clic en la pestaña{" "}
          <strong>Predictions</strong> para ver y crear predicciones.
        </p>
      </div>
    ),
    placement: "bottom",
    disableBeacon: true,
    spotlightClicks: true,
    isInteractive: true,
    hideFooter: true,
    disableOverlayClose: true,
  },
  {
    target: '[data-tour="new-manual-prediction"]',
    content: (
      <div>
        <h3>Predicción Manual</h3>
        <p>
          Haz clic en <strong>New Manual Prediction</strong> para agregar una
          predicción ingresando los datos manualmente.
        </p>
      </div>
    ),
    placement: "top",
    disableBeacon: true,
    spotlightClicks: true,
    isInteractive: true,
    disableOverlayClose: true,
  },
];

export const energyTutorialConfig = {
  continuous: true,
  showProgress: true,
  showSkipButton: true,
  showBackButton: false,
  disableOverlayClose: false,
  disableCloseOnEsc: true,
};
