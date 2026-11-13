import PropTypes from "prop-types";

import { useSession } from "./SessionContext";

/**
 * Renders its children only with a session open. Used for the parts of the
 * app that live outside the routes (the app bar, the job widget), so the
 * session views show nothing but their own card.
 */
export default function SessionOnly({ children }) {
  const { isAuthenticated } = useSession();
  return isAuthenticated ? children : null;
}

SessionOnly.propTypes = {
  children: PropTypes.node.isRequired,
};
