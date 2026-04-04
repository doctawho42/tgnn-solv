import React, { startTransition, useEffect, useState } from "react";
import { PRESENTATION_FIGURES } from "./figures.jsx";
import { PresentationDataProvider, usePresentationData } from "./presentation-data.js";
import { SlideNotes } from "./slide-notes.jsx";

function readInitialIndex() {
  if (typeof window === "undefined") {
    return 0;
  }
  const hash = window.location.hash.replace(/^#/, "");
  const figureIndex = PRESENTATION_FIGURES.findIndex((figure) => figure.slug === hash);
  return figureIndex >= 0 ? figureIndex : 0;
}

export function PresentationApp() {
  return (
    <PresentationDataProvider>
      <PresentationDeck />
    </PresentationDataProvider>
  );
}

function PresentationDeck() {
  const [activeIndex, setActiveIndex] = useState(readInitialIndex);
  const activeFigure = PRESENTATION_FIGURES[activeIndex];
  const FigureComponent = activeFigure.component;
  const presentationData = usePresentationData();

  useEffect(() => {
    const onHashChange = () => {
      const nextIndex = readInitialIndex();
      setActiveIndex(nextIndex);
    };

    const onKeyDown = (event) => {
      if (event.key === "ArrowRight" || event.key === "PageDown") {
        event.preventDefault();
        startTransition(() => {
          setActiveIndex((previous) => Math.min(PRESENTATION_FIGURES.length - 1, previous + 1));
        });
      }
      if (event.key === "ArrowLeft" || event.key === "PageUp") {
        event.preventDefault();
        startTransition(() => {
          setActiveIndex((previous) => Math.max(0, previous - 1));
        });
      }
    };

    window.addEventListener("hashchange", onHashChange);
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("hashchange", onHashChange);
      window.removeEventListener("keydown", onKeyDown);
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const nextHash = `#${activeFigure.slug}`;
    if (window.location.hash !== nextHash) {
      window.history.replaceState(null, "", nextHash);
    }
  }, [activeFigure.slug]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return undefined;
    }

    let timeoutId;
    const root = document.getElementById("tgnn-presentation-root");
    const typeset = () => {
      if (!root) {
        return;
      }
      if (window.MathJax?.typesetPromise) {
        window.MathJax.typesetPromise([root]).catch(() => {});
      }
    };

    if (window.MathJax?.typesetPromise) {
      window.requestAnimationFrame(typeset);
    } else {
      timeoutId = window.setTimeout(typeset, 900);
    }

    return () => {
      if (timeoutId) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [activeIndex]);

  const goToIndex = (nextIndex) => {
    startTransition(() => {
      setActiveIndex(clampIndex(nextIndex));
    });
  };

  return (
    <div className="tgnn-presentation-page">
      <section className="presentation-hero">
        <div className="presentation-hero__eyebrow">Interactive research deck</div>
        <div className="presentation-hero__copy">
          <h1>TGNN-Solv Presentation</h1>
          <p>
            A slide-like React application embedded directly into the MkDocs site. The deck covers the data
            pipeline, baselines, architecture, solver mechanics, diagnostics, optimization behavior, and the
            current accuracy gap.
          </p>
        </div>
        <div className="presentation-hero__stats">
          <div>
            <strong>{PRESENTATION_FIGURES.length}</strong>
            <span>figures</span>
          </div>
          <div>
            <strong>React</strong>
            <span>embedded in MkDocs</span>
          </div>
          <div>
            <strong>{formatGeneratedAt(presentationData.meta.generatedAt)}</strong>
            <span>{presentationData.meta.source === "manifest" ? "auto-fed metrics" : "fallback metrics"}</span>
          </div>
          <div>
            <strong>Keyboard</strong>
            <span>&larr; / &rarr; to navigate</span>
          </div>
        </div>
      </section>

      <div className="presentation-strip">
        <div className="presentation-strip__title">Deck map</div>
        <nav className="presentation-strip__nav" aria-label="Presentation figures">
          {PRESENTATION_FIGURES.map((figure, index) => (
            <button
              type="button"
              key={figure.slug}
              className={`presentation-strip__item${index === activeIndex ? " is-active" : ""}`}
              onClick={() => goToIndex(index)}
            >
              <span className="presentation-strip__count">{String(index + 1).padStart(2, "0")}</span>
              <span className="presentation-strip__text">{figure.title}</span>
            </button>
          ))}
        </nav>
      </div>

      <main className="presentation-stage">
          <header className="presentation-stage__header">
            <div>
              <div className="presentation-stage__meta">
                Slide {activeIndex + 1} / {PRESENTATION_FIGURES.length}
              </div>
              <h2>{activeFigure.title}</h2>
              <p>{activeFigure.blurb}</p>
            </div>
            <div className="presentation-stage__actions">
              <button type="button" className="nav-button" onClick={() => goToIndex(activeIndex - 1)} disabled={activeIndex === 0}>
                Prev
              </button>
              <button
                type="button"
                className="nav-button nav-button--primary"
                onClick={() => goToIndex(activeIndex + 1)}
                disabled={activeIndex === PRESENTATION_FIGURES.length - 1}
              >
                Next
              </button>
            </div>
          </header>

          <div className="presentation-stage__tags">
            {activeFigure.tags.map((tag) => (
              <span key={tag} className="presentation-tag">
                {tag}
              </span>
            ))}
          </div>

          <FigureComponent />
          <SlideNotes slug={activeFigure.slug} />
      </main>
    </div>
  );
}

function clampIndex(index) {
  return Math.min(PRESENTATION_FIGURES.length - 1, Math.max(0, index));
}

function formatGeneratedAt(value) {
  if (!value) {
    return "Auto data";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Auto data";
  }
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
  }).format(date);
}
