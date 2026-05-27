import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Box, Divider, Typography } from "@mui/material";
import CloudDownloadIcon from "@mui/icons-material/CloudDownload";
import StorageIcon from "@mui/icons-material/Storage";
import { useTranslation } from "react-i18next";
import Footer from "../threeSectionLayout/Footer";
import SearchBar from "../threeSectionLayout/SearchBar";
import SideBar from "../threeSectionLayout/panelContainers/SideBar";
import CollapsibleList from "../threeSectionLayout/CollapsibleList";
import { useDatasets } from "../../hooks/datasets/useDatasets";

/**
 * Left sidebar for the Hub module — shows DashAI datasets and downloaded datafiles.
 *
 * @param {Array} downloads - List of Datafile records to show.
 * @param {function} onDeleteDownload - Called with download id when user deletes.
 * @param {function} onImportDownload - Called with download record when user clicks Add.
 */
export default function HubLeftBar({
  downloads = [],
  onDeleteDownload,
  onImportDownload,
}) {
  const { t } = useTranslation(["hub", "common", "datasets"]);
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const { datasets, editDataset, deleteDatasetById } = useDatasets({ t });

  const q = searchQuery.toLowerCase();
  const filteredDatasets = datasets.filter((d) =>
    d.name.toLowerCase().includes(q),
  );
  const filteredDownloads = downloads.filter((dl) =>
    dl.name.toLowerCase().includes(q),
  );

  return (
    <SideBar>
      <Box
        sx={{
          p: 4,
          height: "64px",
          display: "flex",
          alignItems: "center",
          flexShrink: 0,
        }}
      >
        <Typography variant="body1" color="textSecondary">
          {t("hub:title")}
        </Typography>
      </Box>

      <Box px={4} pb={4} sx={{ flexShrink: 0 }}>
        <SearchBar
          placeholder={t("hub:searchDownloads", "Search...")}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </Box>

      <Divider sx={{ width: "90%", bgcolor: "divider", mx: "auto" }} />

      <Box display="flex" flexDirection="column" flex={1} minHeight={0}>
        <CollapsibleList
          items={filteredDatasets}
          onItemClick={(id) => navigate(`/app/data/datasets/${id}`)}
          onItemDelete={deleteDatasetById}
          onItemEdit={editDataset}
          defaultOpen={true}
          title={t("datasets:label.availableDatasets")}
          Icon={StorageIcon}
          getItemDescription={(ds) =>
            `${ds.total_rows} ${t("common:rows")}, ${ds.total_columns} ${t("common:columns")}`
          }
        />

        <Divider sx={{ width: "90%", bgcolor: "divider", mx: "auto" }} />

        <CollapsibleList
          items={filteredDownloads}
          onItemClick={(id) => {
            const dl = filteredDownloads.find((d) => d.id === id);
            if (dl?.status === "ready") onImportDownload?.(dl);
          }}
          onItemDelete={onDeleteDownload}
          onItemEdit={() => {}}
          defaultOpen={true}
          title={t("hub:downloadedDatasets")}
          Icon={CloudDownloadIcon}
          getItemDescription={(dl) =>
            t("hub:fromSource", { source: dl.source_name })
          }
        />
      </Box>

      <Footer />
    </SideBar>
  );
}
