import React from "react";

export function FigureCard({ kicker, title, subtitle, controls, children, footer }) {
  return (
    <section className="presentation-card">
      <header className="presentation-card__header">
        <div>
          <div className="presentation-card__kicker">{kicker}</div>
          <h2>{title}</h2>
          {subtitle ? <p className="presentation-card__subtitle">{subtitle}</p> : null}
        </div>
        {controls ? <div className="presentation-card__controls">{controls}</div> : null}
      </header>
      <div className="presentation-card__body">{children}</div>
      {footer ? <footer className="presentation-card__footer">{footer}</footer> : null}
    </section>
  );
}

export function FigureLegend({ items }) {
  return (
    <div className="figure-legend" role="list">
      {items.map((item) => (
        <div className="figure-legend__item" key={item.label} role="listitem">
          <span className="figure-legend__swatch" style={{ background: item.color }} />
          <span>{item.label}</span>
        </div>
      ))}
    </div>
  );
}

export function ToggleGroup({ label, options, value, onChange }) {
  return (
    <div className="toggle-group" role="group" aria-label={label}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          className={`toggle-group__button${value === option.value ? " is-active" : ""}`}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

export function StatStrip({ items }) {
  return (
    <div className="stat-strip">
      {items.map((item) => (
        <div className="stat-strip__item" key={item.label}>
          <div className="stat-strip__value">{item.value}</div>
          <div className="stat-strip__label">{item.label}</div>
        </div>
      ))}
    </div>
  );
}
