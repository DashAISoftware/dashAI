import React from "react";

import { BrowserRouter, Route, Routes } from "react-router-dom";

import "./App.css";
import DatasetsPage from "./pages/datasets/Datasets";
import ModelsPage from "./pages/models/Models";
import ExperimentsPage from "./pages/experiments/Experiments";
import Home from "./pages/home/Home";
import ExplainersDashboard from "./components/explainers/ExplainersDashboard";
import ExplainersPage from "./pages/ExplainersPage";
import ExplainerData from "./components/explainers/ExplainerData";
import ResponsiveAppBar from "./components/ResponsiveAppBar";
import PluginsPage from "./pages/plugins/Plugins";
import PipelinesPage from "./pages/pipelines/Pipelines";
import NewPipeline from "./pages/pipelines/NewPipeline";
import PluginsDetails from "./pages/plugins/components/PluginsDetails";
import Generative from "./pages/generative/Generative";
import NewPipelineWrapper from "./pages/pipelines/newPipelineWrapper";
import JobQueueWidget from "./components/jobs/JobQueueWidget";

function App() {
  return (
    <BrowserRouter
      future={{ v7_relativeSplatPath: true, v7_startTransition: true }}
    >
      <ResponsiveAppBar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/app" element={<Home />} />
        <Route path="/app/data/" element={<DatasetsPage />} />
        <Route path="/app/experiments" element={<ExperimentsPage />} />
        <Route path="/app/models" element={<ModelsPage />} />
        <Route path="/app/explainers">
          <Route index element={<ExplainersPage />} />
          <Route path="runs/:id" element={<ExplainersDashboard />} />
          <Route
            path="explainer/:scope/:runId/:id"
            element={<ExplainerData />}
          />
        </Route>
        <Route path="/app/generative" element={<Generative />} />
        <Route path="/app/pipelines" element={<PipelinesPage />} />
        <Route path="/app/pipelines/new" element={<NewPipelineWrapper />} />
        <Route
          path="/app/pipelines/:pipelineId"
          element={<NewPipelineWrapper />}
        />
        <Route path="/app/plugins">
          <Route index element={<PluginsPage />} />
          <Route path=":category">
            <Route index element={<PluginsPage />} />
            <Route path="details/:id" element={<PluginsDetails />} />
          </Route>
        </Route>
      </Routes>
      <JobQueueWidget />
    </BrowserRouter>
  );
}
export default App;
