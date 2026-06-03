import React, { useState, useMemo } from "react";
import PropTypes from "prop-types";
import { Box, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";
import HoverModelInfo from "./model/HoverModelInfo";

function StatisticalTestItem({ test, isSelected, onSelect, numberOfRuns }) {
  const theme = useTheme();
  const { i18n } = useTranslation();
  const [anchorEl, setAnchorEl] = useState(null);
  const [hoveredTest, setHoveredTest] = useState(null);

  const minRuns = test.metadata?.min_runs || 2;
  const isAvailable = numberOfRuns >= minRuns;

  const getDescription = useMemo(() => {
    if (
      test.metadata?.description &&
      typeof test.metadata.description === "object"
    ) {
      const langCode = i18n.language?.split("-")[0] || "en";
      return (
        test.metadata.description[langCode] ||
        test.metadata.description["en"] ||
        "No description"
      );
    }
    return test.description || "No description";
  }, [test, i18n.language]);

  const handleMouseEnter = (event) => {
    if (isAvailable) {
      setAnchorEl(event.currentTarget);
      const testWithDescription = {
        ...test,
        description: getDescription,
        display_name: test.metadata?.name || test.name,
      };
      setHoveredTest(testWithDescription);
    }
  };

  const handleMouseLeave = () => {
    setAnchorEl(null);
    setHoveredTest(null);
  };

  return (
    <>
      <Box
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onClick={() => isAvailable && onSelect(test)}
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1.5,
          p: 1.5,
          bgcolor: isAvailable
            ? theme.palette.ui.box
            : theme.palette.ui.disabled,
          border: `1px solid ${theme.palette.ui.border}`,
          borderRadius: 1,
          cursor: isAvailable ? "pointer" : "not-allowed",
          transition: "all 0.2s",
          opacity: isAvailable ? 1 : 0.5,
          position: "relative",
          "&:hover": {
            bgcolor: isAvailable
              ? theme.palette.action.hover
              : theme.palette.ui.disabled,
            borderColor: isAvailable
              ? theme.palette.primary.main
              : theme.palette.ui.border,
            transform: isAvailable ? "translateX(4px)" : "none",
          },
        }}
      >
        {/* Content */}
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography
            variant="body2"
            sx={{
              color: isAvailable
                ? theme.palette.text.primary
                : theme.palette.text.disabled,
              fontWeight: 500,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {test.metadata?.name || test.name}
          </Typography>
        </Box>
      </Box>

      {isAvailable && (
        <HoverModelInfo
          anchorEl={anchorEl}
          hoveredModel={hoveredTest}
          handleMouseLeave={handleMouseLeave}
        />
      )}
    </>
  );
}

StatisticalTestItem.propTypes = {
  test: PropTypes.shape({
    name: PropTypes.string.isRequired,
    display_name: PropTypes.string,
    description: PropTypes.string,
    metadata: PropTypes.object,
  }).isRequired,
  isSelected: PropTypes.bool.isRequired,
  onSelect: PropTypes.func.isRequired,
  numberOfRuns: PropTypes.number.isRequired,
};

export default StatisticalTestItem;
