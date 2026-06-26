import React from "react";

import { BrowserRouter, Outlet, Route, Routes } from "react-router-dom";
import { TourRegistryProvider } from "./contexts/TourRegistryContext";
import ModuleThemeWrapper from "./components/ModuleThemeWrapper";

import "./App.css";
import DatasetsPage from "./pages/datasets/Datasets";
import ModelsPage from "./pages/models/Models";
import Home from "./pages/home/Home";
import ResponsiveAppBar from "./components/ResponsiveAppBar";
import PluginsPage from "./pages/plugins/Plugins";
import PluginsDetails from "./pages/plugins/components/PluginsDetails";
import Generative from "./pages/generative/Generative";
import NewPipelineWrapper from "./pages/pipelines/newPipelineWrapper";
import HubContent from "./pages/hub/HubContent";
import HubImportPage from "./pages/hub/HubImportPage";
import JobQueueWidget from "./components/jobs/JobQueueWidget";
import { DatasetsAndNotebooksProvider } from "./components/custom/contexts/DatasetsAndNotebooksContext";

function DataSectionLayout() {
  return (
    <DatasetsAndNotebooksProvider>
      <Outlet />
    </DatasetsAndNotebooksProvider>
  );
}

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
          <Route path="/app/data" element={<DataSectionLayout />}>
            <Route index element={<DatasetsPage />} />
            <Route path="datasets/new" element={<DatasetsPage />} />
            <Route
              path="datasets/new/:dataloaderName"
              element={<DatasetsPage />}
            />
            <Route path="datasets/:id" element={<DatasetsPage />} />
            <Route path="notebooks/new" element={<DatasetsPage />} />
            <Route path="notebooks/:id" element={<DatasetsPage />} />
            <Route path="hub" element={<HubContent />} />
            <Route
              path="hub/import/:datafileId/*"
              element={<HubImportPage />}
            />
            <Route path="hub/:sourceName" element={<HubContent />} />
          </Route>
          <Route path="/app/models" element={<ModelsPage />} />
          <Route path="/app/models/datasets/:id" element={<ModelsPage />} />
          <Route path="/app/models/sessions/:id" element={<ModelsPage />} />
          <Route
            path="/app/models/sessions/new/:taskName"
            element={<ModelsPage />}
          />
          <Route path="/app/generative" element={<Generative />} />
          <Route path="/app/generative/sessions/new" element={<Generative />} />
          <Route
            path="/app/generative/sessions/new/:modelName"
            element={<Generative />}
          />
          <Route path="/app/generative/sessions/:id" element={<Generative />} />
          <Route path="/app/pipelines" element={<NewPipelineWrapper />} />
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
