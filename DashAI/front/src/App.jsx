import React from "react";

import { BrowserRouter, Route, Routes } from "react-router-dom";
import { TourRegistryProvider } from "./contexts/TourRegistryContext";

import "./App.css";
import DatasetsPage from "./pages/datasets/Datasets";
import ModelsPage from "./pages/models/Models";
import Home from "./pages/home/Home";
import ResponsiveAppBar from "./components/ResponsiveAppBar";
import PluginsPage from "./pages/plugins/Plugins";
import PipelinesPage from "./pages/pipelines/Pipelines";
import PluginsDetails from "./pages/plugins/components/PluginsDetails";
import Generative from "./pages/generative/Generative";
import NewPipelineWrapper from "./pages/pipelines/newPipelineWrapper";
import JobQueueWidget from "./components/jobs/JobQueueWidget";

function App() {
  return (
    <TourRegistryProvider>
      <BrowserRouter
        future={{ v7_relativeSplatPath: true, v7_startTransition: true }}
      >
        <ResponsiveAppBar />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/app" element={<Home />} />
          <Route path="/app/data/" element={<DatasetsPage />} />
          <Route path="/app/data/datasets/new" element={<DatasetsPage />} />
          <Route
            path="/app/data/datasets/new/:dataloaderName"
            element={<DatasetsPage />}
          />
          <Route path="/app/data/datasets/:id" element={<DatasetsPage />} />
          <Route path="/app/data/notebooks/new" element={<DatasetsPage />} />
          <Route path="/app/data/notebooks/:id" element={<DatasetsPage />} />
          <Route path="/app/models" element={<ModelsPage />} />
          <Route path="/app/models/datasets/:id" element={<ModelsPage />} />
          <Route path="/app/models/sessions/:id" element={<ModelsPage />} />
          <Route
            path="/app/models/sessions/new/:taskName"
            element={<ModelsPage />}
          />
          <Route path="/app/generative" element={<Generative />} />
          <Route path="/app/generative/sessions/new" element={<Generative />} />
          <Route path="/app/generative/sessions/new/:modelName" element={<Generative />} />
          <Route path="/app/generative/sessions/:id" element={<Generative />} />
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
    </TourRegistryProvider>
  );
}
export default App;
