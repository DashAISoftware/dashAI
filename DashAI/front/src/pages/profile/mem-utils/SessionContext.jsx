import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import PropTypes from "prop-types";

import { setUnauthorizedHandler } from "../../../api/api";
import * as authService from "./authService";

const SessionContext = createContext(null);

/**
 * Keeps the logged-in user and the list of accounts, and exposes the session
 * actions to the whole app through `useSession()`.
 */
export function SessionProvider({ children }) {
  const [user, setUser] = useState(null);
  const [users, setUsers] = useState([]);
  // True until the backend has said who is logged in; guards wait for it
  const [loading, setLoading] = useState(true);
  // True when a session that was open stopped being valid
  const [expired, setExpired] = useState(false);

  // Read by the 401 handler, which is registered once
  const userRef = useRef(null);
  useEffect(() => {
    userRef.current = user;
  }, [user]);

  useEffect(() => {
    // A 401 without a session (wrong password, first load) is not an expiry
    setUnauthorizedHandler(() => {
      if (userRef.current) {
        setUser(null);
        setExpired(true);
      }
    });
    return () => setUnauthorizedHandler(null);
  }, []);

  useEffect(() => {
    Promise.all([
      // An unreachable backend is treated as no session
      authService.getCurrentUser().catch(() => null),
      authService.getUsers(),
    ]).then(([currentUser, allUsers]) => {
      setUser(currentUser);
      setUsers(allUsers);
      setLoading(false);
    });
  }, []);

  const login = useCallback(async (identifier, password) => {
    const loggedUser = await authService.login(identifier, password);
    setUser(loggedUser);
    setExpired(false);
    return loggedUser;
  }, []);

  const logout = useCallback(async () => {
    await authService.logout();
    setUser(null);
  }, []);

  // The backend starts a session for the new account right away
  const register = useCallback(async (data) => {
    const newUser = await authService.register(data);
    setUser(newUser);
    setExpired(false);
    return newUser;
  }, []);

  // Own profile goes to the backend; other accounts are still mock data
  const updateUser = useCallback(
    async (userId, changes) => {
      if (userId === user?.id) {
        setUser(await authService.updateProfile(changes));
        return;
      }
      setUsers(await authService.updateUser(userId, changes));
    },
    [user],
  );

  const changePassword = useCallback(
    (currentPassword, newPassword) =>
      authService.changePassword(currentPassword, newPassword),
    [],
  );

  // Permissions come from the global role, as computed by the backend;
  // project roles are not checked yet
  const can = useCallback(
    (permission) => Boolean(user) && user.permissions.includes(permission),
    [user],
  );

  const value = useMemo(
    () => ({
      user,
      users,
      loading,
      expired,
      isAuthenticated: Boolean(user),
      login,
      logout,
      register,
      updateUser,
      changePassword,
      can,
    }),
    [
      user,
      users,
      loading,
      expired,
      login,
      logout,
      register,
      updateUser,
      changePassword,
      can,
    ],
  );

  return (
    <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
  );
}

SessionProvider.propTypes = {
  children: PropTypes.node.isRequired,
};

export function useSession() {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error("useSession must be used within a SessionProvider");
  }
  return context;
}
