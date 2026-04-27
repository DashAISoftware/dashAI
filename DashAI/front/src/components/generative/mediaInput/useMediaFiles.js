import { useState, useRef, useMemo } from "react";
import { MEDIA_ORDER, parseCardinality, isActive } from "./constants";

export function useMediaFiles(inputsCardinality) {
  const [text, setText] = useState("");
  const [filesByKind, setFilesByKind] = useState({});
  const [previewsByKind, setPreviewsByKind] = useState({});
  const fileInputRefs = useRef({});

  const textCard = parseCardinality(inputsCardinality.str);
  const wantsText = textCard.max > 0;
  const textRequired = textCard.min > 0;
  const activeKinds = useMemo(
    () => MEDIA_ORDER.filter((kind) => isActive(inputsCardinality[kind])),
    [inputsCardinality],
  );
  const hasAnyMedia = activeKinds.length > 0;

  const handleFileChange = (kind) => (e) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const { max } = parseCardinality(inputsCardinality[kind]);
    const current = filesByKind[kind] || [];
    const remaining = max - current.length;
    if (remaining <= 0) return;

    const incoming = Array.from(e.target.files).slice(0, remaining);
    const newPreviews = incoming.map((f) => URL.createObjectURL(f));

    setFilesByKind({ ...filesByKind, [kind]: [...current, ...incoming] });
    setPreviewsByKind({
      ...previewsByKind,
      [kind]: [...(previewsByKind[kind] || []), ...newPreviews],
    });
  };

  const removeFile = (kind, index) => {
    URL.revokeObjectURL(previewsByKind[kind][index]);
    const newFiles = [...(filesByKind[kind] || [])];
    const newPreviews = [...(previewsByKind[kind] || [])];
    newFiles.splice(index, 1);
    newPreviews.splice(index, 1);
    setFilesByKind({ ...filesByKind, [kind]: newFiles });
    setPreviewsByKind({ ...previewsByKind, [kind]: newPreviews });
    if (fileInputRefs.current[kind]) {
      fileInputRefs.current[kind].value = "";
    }
  };

  const requirementsMet = useMemo(() => {
    if (textRequired && !text.trim()) return false;
    for (const kind of activeKinds) {
      const { min, max } = parseCardinality(inputsCardinality[kind]);
      const count = (filesByKind[kind] || []).length;
      if (count < min || count > max) return false;
    }
    return true;
  }, [textRequired, text, activeKinds, filesByKind, inputsCardinality]);

  const reset = () => {
    setText("");
    Object.values(previewsByKind).forEach((arr) =>
      arr.forEach((url) => URL.revokeObjectURL(url)),
    );
    setFilesByKind({});
    setPreviewsByKind({});
    Object.values(fileInputRefs.current).forEach((ref) => {
      if (ref) ref.value = "";
    });
  };

  const collectPayload = () => {
    const allFiles = activeKinds.flatMap((kind) => filesByKind[kind] || []);
    return wantsText ? [...allFiles, text] : allFiles;
  };

  return {
    text,
    setText,
    filesByKind,
    previewsByKind,
    fileInputRefs,
    wantsText,
    textRequired,
    activeKinds,
    hasAnyMedia,
    handleFileChange,
    removeFile,
    requirementsMet,
    reset,
    collectPayload,
  };
}
