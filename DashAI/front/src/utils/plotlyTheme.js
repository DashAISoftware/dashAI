/**
 * Apply MUI theme colors to a Plotly layout object that comes from the backend.
 * Strips fixed width/height so the caller can define its own sizing.
 *
 * @param {object} baseLayout  Raw layout object received from the backend.
 * @param {object} theme       MUI theme object (from useTheme()).
 * @returns {object}           New layout with theme colors applied.
 */
function applyThemeToLayout(baseLayout, theme) {
  const bg = theme.palette.background.paper;
  const textColor = theme.palette.text.primary;
  const gridColor = theme.palette.divider;

  // Strip backend-provided fixed dimensions so the caller's sizing takes over
  const { width: _w, height: _h, ...rest } = baseLayout ?? {};

  const axisOverride = {
    gridcolor: gridColor,
    zerolinecolor: gridColor,
  };

  return {
    ...rest,
    paper_bgcolor: bg,
    plot_bgcolor: bg,
    font: {
      ...baseLayout?.font,
      color: textColor,
      family: theme.typography.fontFamily,
    },
    xaxis: {
      ...baseLayout?.xaxis,
      ...axisOverride,
      tickfont: { ...baseLayout?.xaxis?.tickfont, color: textColor },
    },
    yaxis: {
      ...baseLayout?.yaxis,
      ...axisOverride,
      tickfont: { ...baseLayout?.yaxis?.tickfont, color: textColor },
    },
    legend: {
      ...baseLayout?.legend,
      bgcolor: bg,
      bordercolor: gridColor,
    },
    title: {
      ...baseLayout?.title,
      font: { ...baseLayout?.title?.font, color: textColor },
    },
    ...(baseLayout?.updatemenus && {
      updatemenus: baseLayout.updatemenus.map((menu) => ({
        ...menu,
        bgcolor:
          theme.palette.ui?.borderLight ?? theme.palette.background.paper,
        bordercolor: gridColor,
        font: { color: "#000000" },
        activecolor: theme.palette.primary.main,
      })),
    }),
    ...(baseLayout?.polar && {
      polar: {
        ...baseLayout.polar,
        bgcolor: bg,
        radialaxis: {
          ...baseLayout.polar.radialaxis,
          gridcolor: gridColor,
          linecolor: gridColor,
          tickfont: {
            ...baseLayout.polar.radialaxis?.tickfont,
            color: textColor,
          },
        },
        angularaxis: {
          ...baseLayout.polar.angularaxis,
          color: textColor,
          gridcolor: gridColor,
          linecolor: gridColor,
        },
      },
    }),
  };
}

export { applyThemeToLayout };
