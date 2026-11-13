import React from "react";
import PropTypes from "prop-types";
import { Navigate, Outlet } from "react-router-dom";

import { useSession } from "./SessionContext";

/**
 * Route guard: without a session, redirects to the login view, telling it
 * when the reason is a session that expired. Logging in always leads to the
 * main portal, not back to the requested path. Works both wrapping an
 * element and as a layout route (renders the nested routes).
 *
 * Only hides the UI; the backend must also check the session on every
 * endpoint.
 */
export default function RequireAuth({ children }) {
  const { isAuthenticated, loading, expired } = useSession();

  if (loading) return null;

  if (!isAuthenticated) {
    return (
      <Navigate
        to="/app/login"
        replace
        state={expired ? { reason: "expired" } : undefined}
      />
    );
  }

  return children ?? <Outlet />;
}

RequireAuth.propTypes = {
  children: PropTypes.node,
};
