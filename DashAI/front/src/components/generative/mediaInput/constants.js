import ImageIcon from "@mui/icons-material/Image";
import AudiotrackIcon from "@mui/icons-material/Audiotrack";
import VideocamIcon from "@mui/icons-material/Videocam";

export const MEDIA_KINDS = {
  Image: {
    accept: "image/*",
    icon: ImageIcon,
    tooltipKey: "label.attachImage",
  },
  Audio: {
    accept: "audio/*",
    icon: AudiotrackIcon,
    tooltipKey: "label.attachAudio",
  },
  Video: {
    accept: "video/*",
    icon: VideocamIcon,
    tooltipKey: "label.attachVideo",
  },
};

export const MEDIA_ORDER = Object.keys(MEDIA_KINDS);

// Normalize cardinality entries into {min, max}.
// Accepts: integer N (exactly N), "n" (0..∞), or {min, max} (max "n" = ∞).
export const parseCardinality = (value) => {
  if (value === "n") return { min: 0, max: Infinity };
  if (typeof value === "number") return { min: value, max: value };
  if (value && typeof value === "object") {
    const min = Number(value.min ?? 0);
    const rawMax = value.max ?? "n";
    const max = rawMax === "n" ? Infinity : Number(rawMax);
    return { min, max };
  }
  return { min: 0, max: 0 };
};

export const isActive = (value) => {
  const { min, max } = parseCardinality(value);
  return max > 0 || min > 0;
};

export const formatRange = ({ min, max }) => {
  if (min === max) return `exactly ${min}`;
  if (max === Infinity) return `min ${min}, max ∞`;
  return `min ${min}, max ${max}`;
};

export const kindTooltip = (label, enabled, current, { min, max }) => {
  if (!enabled) return `${label} (not supported)`;
  const maxLabel = max === Infinity ? "∞" : max;
  return `${label} — ${current}/${maxLabel} (${formatRange({ min, max })})`;
};
