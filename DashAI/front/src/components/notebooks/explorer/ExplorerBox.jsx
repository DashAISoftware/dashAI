import React, { useState, useEffect } from "react";
import {
  Card,
  CardContent,
  Box,
  Typography,
  Chip,
  IconButton,
  CircularProgress,
  Button,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { Analytics, Info, Delete } from "@mui/icons-material";
import { TabResults } from "./tabs";
import { getExplorerStatus } from "../../../utils/explorerStatus";
import { getComponentById } from "../../../api/component";
import { getExplorerById } from "../../../api/explorer";
import ExplorerDetailsModal from "../explorer/ExplorerDetailsModal";
import { useExplorerResults } from "./useExplorerResults";
import { useTranslation } from "react-i18next";

export default function ExplorerBox({
  explorer,
  handleExplorerDeleteClick,
  onStatusChange,
}) {
  const { t } = useTranslation(["datasets", "common"]);
  const theme = useTheme();
  const [explorerComponent, setExplorerComponent] = useState({});
  const [openExplorerDetails, setOpenExplorerDetails] = useState(false);
  const { loading, data, dataType, setData } = useExplorerResults(explorer);

  const statusLabel = explorer.status;

  const handleExplorerDetailsClick = () => {
    setOpenExplorerDetails(true);
  };

  useEffect(() => {
    const fetchConverterComponent = async () => {
      try {
        const component = await getComponentById(explorer.exploration_type);
        setExplorerComponent(component);
      } catch (error) {
        console.error("Failed to fetch converter component:", error);
      }
    };

    fetchConverterComponent();
  }, [explorer.exploration_type, t]);

  useEffect(() => {
    let intervalId;

    const fetchExplorerStatus = async () => {
      try {
        const updatedExplorer = await getExplorerById(explorer.id);

        // 🔑 Notificar al padre si cambia el estado
        if (updatedExplorer.status !== explorer.status) {
          onStatusChange(updatedExplorer.id, updatedExplorer.status);
        }

        const status = updatedExplorer.status;
        if (status === 3 || status === 4) {
          // Finished or Error
          clearInterval(intervalId);
        }
      } catch (error) {
        console.error("Failed to fetch explorer status:", error);
        clearInterval(intervalId);
      }
    };

    const currentStatus = explorer.status;
    if (currentStatus !== 3 && currentStatus !== 4) {
      //  Not Finished and not Error
      intervalId = setInterval(fetchExplorerStatus, 1500);
    }

    return () => clearInterval(intervalId);
  }, [explorer.id, explorer.status, onStatusChange]);

  return (
    <Card
      key={explorer.id}
      sx={{
        bgcolor: theme.palette.background.box,
        borderRadius: 2,
        height: "100%",
      }}
      className="explorer-box"
    >
      <CardContent
        sx={{
          display: "flex",
          flexDirection: "column",
          height: "100%",
        }}
      >
        {/* Header */}
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            mb: 2,
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Analytics
              sx={{ color: theme.palette.primary.main, fontSize: 20 }}
            />
            <Typography variant="h6">
              {explorerComponent.display_name}
            </Typography>
          </Box>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Chip
              label={getExplorerStatus(statusLabel, t)}
              color={
                statusLabel === 3
                  ? "success"
                  : statusLabel === 4
                    ? "error"
                    : "default"
              }
              size="small"
            />
            <>
              {statusLabel === 3 && ( // Finished
                <Chip
                  label={
                    dataType === "plotly_json"
                      ? t("common:infoEdit")
                      : t("common:info")
                  }
                  onClick={() => handleExplorerDetailsClick(explorer)}
                  size="small"
                  color="primary"
                  icon={<Info />}
                  sx={{
                    "&:hover": { bgcolor: "primary.light" },
                  }}
                />
              )}
              {(statusLabel === 4 || statusLabel === 3) && ( // Error or Finished
                <IconButton
                  size="small"
                  onClick={() => handleExplorerDeleteClick(explorer)}
                  sx={{
                    width: 24,
                    height: 24,
                    bgcolor: "error.main",
                    "&:hover": { bgcolor: "error.dark" },
                  }}
                >
                  <Delete sx={{ fontSize: 16, color: "white" }} />
                </IconButton>
              )}
            </>
          </Box>
        </Box>

        {statusLabel === 3 ? ( // Finished
          <Box
            sx={{
              flexGrow: 1,
              bgcolor: theme.palette.background.default,
              borderRadius: 1,
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
            }}
          >
            <TabResults
              id={explorer.id}
              minimalist
              height={300}
              data={data}
              loading={loading}
              dataType={dataType}
            />
          </Box>
        ) : statusLabel === 4 ? ( // Error
          <Box
            sx={{
              flexGrow: 1,
              bgcolor: theme.palette.background.default,
              borderRadius: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              p: 2,
            }}
          >
            <Typography
              variant="body2"
              sx={{ color: "error.main", textAlign: "center" }}
            >
              {t("datasets:error.explorerFailed")}
            </Typography>
          </Box>
        ) : (
          <Box
            sx={{
              flexGrow: 1,
              bgcolor: theme.palette.ui.hover,
              borderRadius: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <CircularProgress size={24} sx={{ mr: 1 }} />
            <Typography>{t("common:processing")}</Typography>
          </Box>
        )}
        {openExplorerDetails && (
          <ExplorerDetailsModal
            open={openExplorerDetails}
            onClose={() => {
              setOpenExplorerDetails(false);
            }}
            explorer={explorer}
            explorerComponent={explorerComponent}
            data={data}
            dataType={dataType}
            loading={loading}
            setData={setData}
          />
        )}
      </CardContent>
    </Card>
  );
}
