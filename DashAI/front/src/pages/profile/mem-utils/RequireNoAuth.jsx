import React from "react";
import PropTypes from "prop-types";
import { Navigate, Outlet } from "react-router-dom";

import { useSession } from "./SessionContext";

/**
 * Route guard for the session views (log in, register): with a session open
 * there is nothing to do there, so it goes to the main portal. Works both
 * wrapping an element and as a layout route.
 */
export default function RequireNoAuth({ children }) {
  const { isAuthenticated, loading } = useSession();

  if (loading) return null;
  if (isAuthenticated) return <Navigate to="/app" replace />;

  return children ?? <Outlet />;
}

RequireNoAuth.propTypes = {
  children: PropTypes.node,
};
