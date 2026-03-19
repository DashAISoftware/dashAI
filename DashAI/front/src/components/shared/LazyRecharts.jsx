import { lazy } from "react";

// Lazy-loaded recharts chart container components for code splitting.
// These are the top-level chart wrappers; wrapping them in React.lazy defers
// the entire recharts bundle until a chart is first rendered.
export const LazyLineChart = lazy(() =>
  import("recharts").then((mod) => ({ default: mod.LineChart })),
);
export const LazyBarChart = lazy(() =>
  import("recharts").then((mod) => ({ default: mod.BarChart })),
);
export const LazyPieChart = lazy(() =>
  import("recharts").then((mod) => ({ default: mod.PieChart })),
);

// Re-exported recharts primitives — available once the lazy chunk loads.
// Import these alongside the lazy containers to avoid multiple recharts imports.
export {
  Line,
  Bar,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
