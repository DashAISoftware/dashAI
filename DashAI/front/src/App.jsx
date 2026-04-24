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
import { GenerativeProvider } from "./components/generative/GenerativeContext";
import NewPipelineWrapper from "./pages/pipelines/newPipelineWrapper";
import JobQueueWidget from "./components/jobs/JobQueueWidget";
import RAGHomePage from "./pages/generative/RAG/RAGHomePage";
import RAGSessionsPage from "./pages/generative/RAG/RAGSessionsPage";
import RAGDocumentsPage from "./pages/generative/RAG/RAGDocumentsPage";
import RAGPromptsPage from "./pages/generative/RAG/RAGPromptsPage";
import SimplifiedRAGPage from "./pages/generative/simplified-RAG/SimplifiedRAGPage";

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
          <Route path="/app/models" element={<ModelsPage />} />
          <Route path="/app/generative" element={<Generative />} />
          <Route
            path="/app/generative/rag"
            element={
              <GenerativeProvider>
                <RAGHomePage />
              </GenerativeProvider>
            }
          />
          <Route
            path="/app/generative/rag/sessions"
            element={
              <GenerativeProvider>
                <RAGSessionsPage />
              </GenerativeProvider>
            }
          />
          <Route
            path="/app/generative/rag/documents"
            element={
              <GenerativeProvider>
                <RAGDocumentsPage />
              </GenerativeProvider>
            }
          />
          <Route
            path="/app/generative/rag/prompts"
            element={
              <GenerativeProvider>
                <RAGPromptsPage />
              </GenerativeProvider>
            }
          />
          <Route
            path="/app/generative/simplified-rag"
            element={
              <GenerativeProvider>
                <SimplifiedRAGPage />
              </GenerativeProvider>
            }
          />
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
