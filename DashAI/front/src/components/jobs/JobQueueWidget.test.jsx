import React from "react";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../../test-utils/renderWithProviders";

// Mock API modules before importing component
jest.mock("../../api/job", () => ({
  deleteJob: jest.fn(),
  deleteAllJobs: jest.fn(),
  getJobs: jest.fn(() => Promise.resolve([])),
}));

jest.mock("../../hooks/useJobPolling", () => ({
  useJobManager: () => ({
    jobs: [],
    loading: false,
    error: null,
    refresh: jest.fn(),
  }),
}));

import JobQueueWidget from "./JobQueueWidget";

describe("JobQueueWidget", () => {
  it("renders without crashing", () => {
    renderWithProviders(<JobQueueWidget />);
  });

  it("renders the Job Queue header", () => {
    renderWithProviders(<JobQueueWidget />);
    expect(screen.getByText("Job Queue")).toBeInTheDocument();
  });
});
