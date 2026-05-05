import React from "react";
import AppBar from "@mui/material/AppBar";
import Box from "@mui/material/Box";
import Toolbar from "@mui/material/Toolbar";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import Menu from "@mui/material/Menu";
import MenuIcon from "@mui/icons-material/Menu";
import MenuItem from "@mui/material/MenuItem";
import { Link as RouterLink, useLocation } from "react-router-dom";
import { useTheme } from "@mui/material/styles";
import HomeIcon from "@mui/icons-material/HomeOutlined";
import { useTranslation } from "react-i18next";
import LanguageSelector from "./LanguageSelector";
import { ColorModeContext } from "../contexts/ThemeContext";
import DarkModeOutlinedIcon from "@mui/icons-material/DarkModeOutlined";
import LightModeOutlinedIcon from "@mui/icons-material/LightModeOutlined";
import Tooltip from "@mui/material/Tooltip";
import HardwareMonitorButton from "./hardware/HardwareMonitorButton";
import NavbarTourButton from "./tour/NavbarTourButton";

function ResponsiveAppBar() {
  const theme = useTheme();
  const colorMode = React.useContext(ColorModeContext);
  const location = useLocation();
  const { t } = useTranslation(["common"]);

  const [anchorElNav, setAnchorElNav] = React.useState(null);

  const pages = [
    { name: t("common:datasets"), to: "/app/data" },
    { name: t("common:models"), to: "/app/models" },
    { name: t("common:generative"), to: "/app/generative" },
    { name: t("common:plugins"), to: "/app/plugins/browse" },
  ];

  const isActive = (path) =>
    location.pathname === path || location.pathname.startsWith(path + "/");

  const handleOpenNavMenu = (e) => setAnchorElNav(e.currentTarget);
  const handleCloseNavMenu = () => setAnchorElNav(null);

  const iconBtnSx = React.useMemo(
    () => ({
      width: 32,
      height: 32,
      borderRadius: "4px",
      border: `1px solid ${theme.palette.divider}`,
      color: theme.palette.text.secondary,
      "&:hover": {
        background: theme.palette.ui.hover,
        color: theme.palette.text.primary,
      },
    }),
    [theme],
  );

  return (
    <AppBar
      position="sticky"
      enableColorOnDark
      elevation={0}
      sx={{
        width: "100%",
        maxWidth: "100%",
        overflowX: "clip",
        background: theme.palette.background.box,
        backdropFilter: "blur(8px)",
        borderBottom: `1px solid ${theme.palette.divider}`,
        "& .MuiToolbar-root": { minHeight: 52 },
      }}
    >
      <Toolbar
        sx={{ px: { xs: 1, sm: 2, md: 3 }, minHeight: 52, gap: 0, minWidth: 0 }}
      >
        {/* Logo */}
        <Box
          component={RouterLink}
          to="/app"
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1,
            textDecoration: "none",
            mr: { xs: 1, sm: 2 },
            flexShrink: 0,
          }}
        >
          <Typography
            sx={{
              fontSize: 16,
              fontWeight: 600,
              letterSpacing: "0.02em",
              color: theme.palette.text.primary,
              lineHeight: 1,
            }}
          >
            <Box component="span" sx={{ color: theme.palette.primary.main }}>
              Dash
            </Box>
            AI
          </Typography>
          <Box
            sx={{
              display: { xs: "none", sm: "block" },
              ...theme.typography.statusBadge,
              color: theme.palette.primary.main,
              border: `1px solid ${theme.palette.accent.amberBorder}`,
              background: theme.palette.accent.amberDim,
              borderRadius: "2px",
              px: "7px",
              py: "2px",
              lineHeight: 1.4,
            }}
          >
            Workbench
          </Box>
        </Box>

        {/* Mobile hamburger */}
        <Box
          sx={{ flexGrow: 1, minWidth: 0, display: { xs: "flex", md: "none" } }}
        >
          <IconButton
            size="large"
            onClick={handleOpenNavMenu}
            color="inherit"
            aria-label="open navigation menu"
            sx={{
              width: 32,
              height: 32,
              borderRadius: "4px",
              border: `1px solid ${theme.palette.divider}`,
              color: theme.palette.text.secondary,
              "&:hover": {
                background: theme.palette.ui.hover,
                color: theme.palette.text.primary,
              },
            }}
          >
            <MenuIcon />
          </IconButton>
          <Menu
            id="menu-appbar"
            anchorEl={anchorElNav}
            anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
            keepMounted
            transformOrigin={{ vertical: "top", horizontal: "left" }}
            open={Boolean(anchorElNav)}
            onClose={handleCloseNavMenu}
            sx={{ display: { xs: "block", md: "none" } }}
          >
            {pages.map((page) => (
              <MenuItem
                key={page.name}
                onClick={handleCloseNavMenu}
                component={RouterLink}
                to={page.to}
                selected={isActive(page.to)}
              >
                <Typography sx={{ ...theme.typography.tabLabel }}>
                  {page.name}
                </Typography>
              </MenuItem>
            ))}
          </Menu>
        </Box>

        {/* Desktop nav tabs */}
        <Box
          sx={{
            flexGrow: 1,
            minWidth: 0,
            display: { xs: "none", md: "flex" },
            alignItems: "stretch",
            height: 52,
            overflow: "hidden",
          }}
        >
          <IconButton
            component={RouterLink}
            to="/app"
            disableRipple
            sx={{ ...iconBtnSx, mr: 1, alignSelf: "center" }}
            aria-label="home"
          >
            <HomeIcon sx={{ fontSize: 16 }} />
          </IconButton>

          {pages.map((page) => {
            const active = isActive(page.to);
            return (
              <Box
                key={page.name}
                component={RouterLink}
                to={page.to}
                sx={{
                  display: "flex",
                  alignItems: "center",
                  px: "18px",
                  height: "100%",
                  textDecoration: "none",
                  ...theme.typography.tabLabel,
                  color: active
                    ? theme.palette.primary.main
                    : theme.palette.text.secondary,
                  background: active
                    ? theme.palette.accent.amberGlow
                    : "transparent",
                  borderBottom: active
                    ? `2px solid ${theme.palette.primary.main}`
                    : "2px solid transparent",
                  borderRight: `1px solid ${theme.palette.divider}`,
                  transition: "color 0.15s, background 0.15s",
                  "&:first-of-type": {
                    borderLeft: `1px solid ${theme.palette.divider}`,
                  },
                  "&:hover": {
                    color: theme.palette.text.primary,
                    background: theme.palette.ui.hover,
                  },
                }}
              >
                {page.name}
              </Box>
            );
          })}
        </Box>

        {/* Right controls */}
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: { xs: 0.5, sm: 1 },
            flexShrink: 0,
          }}
        >
          <LanguageSelector />
          <HardwareMonitorButton />
          <NavbarTourButton />
          <Tooltip
            title={
              theme.palette.mode === "dark"
                ? t("common:switchToLightMode")
                : t("common:switchToDarkMode")
            }
          >
            <IconButton
              onClick={colorMode.toggleColorMode}
              aria-label="toggle theme"
              sx={iconBtnSx}
            >
              {theme.palette.mode === "dark" ? (
                <LightModeOutlinedIcon sx={{ fontSize: 18 }} />
              ) : (
                <DarkModeOutlinedIcon sx={{ fontSize: 18 }} />
              )}
            </IconButton>
          </Tooltip>
        </Box>
      </Toolbar>
    </AppBar>
  );
}

export default ResponsiveAppBar;
