import * as React from "react";
import AppBar from "@mui/material/AppBar";
import Box from "@mui/material/Box";
import Toolbar from "@mui/material/Toolbar";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import Menu from "@mui/material/Menu";
import MenuIcon from "@mui/icons-material/Menu";
import Container from "@mui/material/Container";
import Avatar from "@mui/material/Avatar";
import Button from "@mui/material/Button";
import MenuItem from "@mui/material/MenuItem";
import { Link as RouterLink, useLocation } from "react-router-dom";
import { useTheme } from "@mui/material/styles";
import HomeIcon from "@mui/icons-material/HomeOutlined";
import { useTranslation } from "react-i18next";
import LanguageSelector from "./LanguageSelector";
import { ColorModeContext } from "../contexts/ThemeContext";
import Brightness4Icon from "@mui/icons-material/Brightness4";
import Brightness7Icon from "@mui/icons-material/Brightness7";
import HardwareMonitorButton from "./hardware/HardwareMonitorButton";

function ResponsiveAppBar() {
  const theme = useTheme();
  const colorMode = React.useContext(ColorModeContext);
  const location = useLocation();
  const { t } = useTranslation(["common"]);

  const [anchorElNav, setAnchorElNav] = React.useState(null);

  const pages = [
    { name: t("common:datasets"), to: "/app/data", disabled: false },
    { name: t("common:models"), to: "/app/models", disabled: false },
    { name: t("common:pipelines"), to: "/app/pipelines", disabled: false },
    { name: t("common:generative"), to: "/app/generative", disabled: false },
    { name: t("common:plugins"), to: "/app/plugins/browse", disabled: false },
  ];

  const handleOpenNavMenu = (event) => {
    setAnchorElNav(event.currentTarget);
  };

  const handleCloseNavMenu = () => {
    setAnchorElNav(null);
  };

  return (
    <AppBar
      position="sticky"
      enableColorOnDark
      sx={{ background: theme.palette.background.box }}
    >
      <Container maxWidth="xl">
        <Toolbar>
          <Avatar
            alt="DashAI Logo"
            src="/images/logo.png"
            variant="square"
            sx={{ width: 120, p: 0, mr: 3, my: 1, mt: 2 }}
          />

          {/* Render on xs screens */}
          <Box sx={{ flexGrow: 1, display: { xs: "flex", sm: "none" } }}>
            <IconButton
              size="large"
              onClick={handleOpenNavMenu}
              color="inherit"
            >
              <MenuIcon />
            </IconButton>
            <Menu
              id="menu-appbar"
              anchorEl={anchorElNav}
              anchorOrigin={{
                vertical: "bottom",
                horizontal: "left",
              }}
              autoFocus
              keepMounted
              transformOrigin={{
                vertical: "top",
                horizontal: "left",
              }}
              open={Boolean(anchorElNav)}
              onClose={handleCloseNavMenu}
              sx={{
                display: { xs: "block", md: "none" },
                backgroundColor: theme.palette.background,
              }}
            >
              {pages.map((page) => (
                <MenuItem
                  key={page.name}
                  onClick={handleCloseNavMenu}
                  component={RouterLink}
                  to={page.to}
                  selected={page.to === location.pathname}
                >
                  <Typography color="text.primary" textAlign="center">
                    {page.name}
                  </Typography>
                </MenuItem>
              ))}
            </Menu>
          </Box>

          {/* Render on sm to xl screens */}
          <Box sx={{ flexGrow: 1, display: { xs: "none", sm: "flex" } }}>
            <IconButton
              aria-label="delete"
              component={RouterLink}
              to="/app"
              disableRipple
              sx={{ mr: 2 }}
            >
              <HomeIcon />
            </IconButton>
            {pages.map((page) => (
              <Button
                component={RouterLink}
                to={page.to}
                key={page.name}
                onClick={handleCloseNavMenu}
                sx={{
                  my: 2,
                  display: "block",
                  color:
                    page.to === location.pathname
                      ? theme.palette.primary.main
                      : theme.palette.text.primary,
                }}
                size="large"
                disabled={page.disabled}
                disableRipple
              >
                {page.name}
              </Button>
            ))}
          </Box>
          <LanguageSelector />
          <HardwareMonitorButton />

          {/* Theme Toggle Button */}
          <Box sx={{ flexGrow: 0 }}>
            <IconButton
              onClick={colorMode.toggleColorMode}
              aria-label="toggle theme"
              sx={{
                ml: 1,
                color:
                  theme.palette.mode === "dark"
                    ? "inherit"
                    : theme.palette.text.primary,
              }}
            >
              {theme.palette.mode === "dark" ? (
                <Brightness7Icon />
              ) : (
                <Brightness4Icon />
              )}
            </IconButton>
          </Box>
        </Toolbar>
      </Container>
    </AppBar>
  );
}
export default ResponsiveAppBar;
