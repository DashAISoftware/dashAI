import React from "react";

import { BrowserRouter, Route, Routes } from "react-router-dom";

import "./App.css";
import DatasetsPage from "./pages/datasets/Datasets";
import ModelsPage from "./pages/models/Models";
import Home from "./pages/home/Home";
import ResponsiveAppBar from "./components/ResponsiveAppBar";
import PluginsPage from "./pages/plugins/Plugins";
import PluginsDetails from "./pages/plugins/components/PluginsDetails";
import Generative from "./pages/generative/Generative";
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
        <Route path="/app/models" element={<ModelsPage />} />
        <Route path="/app/generative" element={<Generative />} />
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
