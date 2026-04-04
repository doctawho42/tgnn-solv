import React from "react";
import { createRoot } from "react-dom/client";
import { PresentationApp } from "./app.jsx";

function mountPresentation() {
  const rootElement = document.getElementById("tgnn-presentation-root");
  if (!rootElement || rootElement.dataset.mounted === "true") {
    return;
  }

  rootElement.dataset.mounted = "true";
  document.body.classList.add("tgnn-presentation-route");
  const root = createRoot(rootElement);
  root.render(<PresentationApp />);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", mountPresentation, { once: true });
} else {
  mountPresentation();
}
