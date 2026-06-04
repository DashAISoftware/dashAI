export function setCustomDragImage(e) {
  const el = e.currentTarget;
  const rect = el.getBoundingClientRect();
  const clone = el.cloneNode(true);
  // Position the clone exactly over the original so the browser renders it
  // fully inside the viewport — off-screen positions can produce blank ghosts.
  Object.assign(clone.style, {
    position: "fixed",
    top: `${rect.top}px`,
    left: `${rect.left}px`,
    width: `${rect.width}px`,
    height: `${rect.height}px`,
    margin: "0",
    opacity: "1",
    transform: "none",
    pointerEvents: "none",
    zIndex: "10000",
  });
  document.body.appendChild(clone);
  e.dataTransfer.setDragImage(
    clone,
    e.clientX - rect.left,
    e.clientY - rect.top,
  );
  setTimeout(() => document.body.removeChild(clone), 0);
}
