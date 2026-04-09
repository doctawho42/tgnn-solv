import React, { useEffect, useRef, useState } from "react";
import SmilesDrawer from "smiles-drawer";
import { FigureCard, FigureLegend, StatStrip, ToggleGroup } from "./components.jsx";
import { usePresentationData } from "./presentation-data.js";

const COLORS = {
  blue: "#2563EB",
  orange: "#F59E0B",
  green: "#10B981",
  red: "#EF4444",
  purple: "#8B5CF6",
  yellow: "#FBBF24",
  gray: "#6B7280",
  slate: "#475569",
  ink: "#0F172A",
  border: "#CBD5E1",
  line: "#94A3B8",
  sky: "#0EA5E9",
  mint: "#22C55E",
  amberSoft: "#FEF3C7",
  blueSoft: "#DBEAFE",
  greenSoft: "#D1FAE5",
  purpleSoft: "#EDE9FE",
  redSoft: "#FEE2E2",
};

const PAPER_FILL = "var(--deck-paper)";
const PAPER_BORDER = "var(--deck-paper-border)";
const PAPER_TEXT = "var(--deck-paper-text)";
const PAPER_SOFT_TEXT = "var(--deck-paper-soft)";
const DECK_TEXT = "var(--deck-text)";
const DECK_SOFT_TEXT = "var(--deck-text-faint)";

const EXAMPLE_PAIR = {
  solute: {
    name: "Paracetamol",
    role: "solute",
    smiles: "CC(=O)Nc1ccc(O)cc1",
  },
  solvent: {
    name: "Ethanol",
    role: "solvent",
    smiles: "CCO",
  },
};

function linePath(points) {
  return points.map(([x, y], index) => `${index === 0 ? "M" : "L"} ${x} ${y}`).join(" ");
}

function createChartScales({ left, right, top, bottom, xMin, xMax, yMin, yMax }) {
  const safeXSpan = Math.max(xMax - xMin, 1e-9);
  const safeYSpan = Math.max(yMax - yMin, 1e-9);

  return {
    left,
    right,
    top,
    bottom,
    xScale: (value) => left + ((value - xMin) / safeXSpan) * (right - left),
    yScale: (value) => bottom - ((value - yMin) / safeYSpan) * (bottom - top),
  };
}

function areaPath(topPoints, bottomPoints) {
  return `${linePath(topPoints)} ${bottomPoints
    .slice()
    .reverse()
    .map(([x, y]) => `L ${x} ${y}`)
    .join(" ")} Z`;
}

function polarToCartesian(cx, cy, radius, angleDeg) {
  const angle = ((angleDeg - 90) * Math.PI) / 180;
  return {
    x: cx + radius * Math.cos(angle),
    y: cy + radius * Math.sin(angle),
  };
}

function gaussianPoints({ start, end, steps, mean, sigma, height, baseline }) {
  return Array.from({ length: steps }, (_, index) => {
    const t = index / (steps - 1);
    const x = start + (end - start) * t;
    const density = Math.exp(-0.5 * ((x - mean) / sigma) ** 2);
    return [x, baseline - density * height];
  });
}

function TexInline({ children }) {
  return <span className="tex-inline">{`\\(${children}\\)`}</span>;
}

function TexBlock({ children }) {
  return <div className="tex-block">{`\\[${children}\\]`}</div>;
}

function MoleculeStructure({ smiles, className = "" }) {
  const svgRef = useRef(null);

  useEffect(() => {
    if (!svgRef.current) {
      return;
    }

    const drawer = new SmilesDrawer.SvgDrawer({
      width: 360,
      height: 240,
      padding: 24,
      bondLength: 22,
      bondThickness: 1.2,
      atomVisualization: "default",
      isometric: false,
      compactDrawing: true,
      explicitHydrogens: false,
      terminalCarbons: false,
      fontSizeLarge: 10,
      fontSizeSmall: 6,
    });

    svgRef.current.innerHTML = "";
    SmilesDrawer.parse(
      smiles,
      (tree) => {
        drawer.draw(tree, svgRef.current, "light");
      },
      () => {
        if (svgRef.current) {
          svgRef.current.innerHTML =
            '<text x="20" y="32" fill="#64748b" font-size="16">Structure rendering failed.</text>';
        }
      },
    );
  }, [smiles]);

  return <svg ref={svgRef} className={`molecule-svg ${className}`.trim()} viewBox="0 0 360 240" aria-hidden="true" />;
}

function MoleculeMiniCard({ role, name, smiles, compact = false }) {
  return (
    <div className={`molecule-mini-card${compact ? " molecule-mini-card--compact" : ""}`}>
      <div className="molecule-mini-card__meta">
        <span>{role}</span>
        <strong>{name}</strong>
        <small>{smiles}</small>
      </div>
      <div className="molecule-mini-card__art">
        <MoleculeStructure smiles={smiles} className="molecule-mini-card__svg" />
      </div>
    </div>
  );
}

function ExamplePairStrip({ compact = false }) {
  return (
    <div className={`example-pair-strip${compact ? " example-pair-strip--compact" : ""}`}>
      <MoleculeMiniCard
        role={EXAMPLE_PAIR.solute.role}
        name={EXAMPLE_PAIR.solute.name}
        smiles={EXAMPLE_PAIR.solute.smiles}
        compact={compact}
      />
      <div className="example-pair-strip__divider">
        <span>shared input pair</span>
      </div>
      <MoleculeMiniCard
        role={EXAMPLE_PAIR.solvent.role}
        name={EXAMPLE_PAIR.solvent.name}
        smiles={EXAMPLE_PAIR.solvent.smiles}
        compact={compact}
      />
    </div>
  );
}

function SimpleArrowDefs({ id }) {
  return (
    <defs>
      <marker
        id={`${id}-arrow`}
        viewBox="0 0 10 10"
        refX="8"
        refY="5"
        markerWidth="6"
        markerHeight="6"
        orient="auto-start-reverse"
      >
        <path d="M 0 0 L 10 5 L 0 10 z" fill={COLORS.line} />
      </marker>
      <marker
        id={`${id}-arrow-strong`}
        viewBox="0 0 10 10"
        refX="8"
        refY="5"
        markerWidth="7"
        markerHeight="7"
        orient="auto-start-reverse"
      >
        <path d="M 0 0 L 10 5 L 0 10 z" fill={COLORS.blue} />
      </marker>
    </defs>
  );
}

function SourceIcon({ kind, color }) {
  const glyphs = {
    tube: { label: "SOL", sublabel: "DB" },
    crystal: { label: "Tm", sublabel: "ΔH" },
    axes: { label: "HSP", sublabel: "δ" },
    infinity: { label: "γ∞", sublabel: "IDAC" },
  };

  const glyph = glyphs[kind] ?? { label: "DB", sublabel: "" };

  return (
    <svg viewBox="0 0 40 40" aria-hidden="true">
      <rect x="3.5" y="3.5" width="33" height="33" rx="10" fill="none" stroke={color} strokeWidth="1.9" />
      <path d="M10 13.5h20" fill="none" stroke={color} strokeOpacity="0.22" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M13 28h14" fill="none" stroke={color} strokeOpacity="0.18" strokeWidth="1.5" strokeLinecap="round" />
      <text
        x="20"
        y={glyph.sublabel ? "19.5" : "22"}
        textAnchor="middle"
        fill={color}
        fontSize={glyph.label.length > 3 ? "9.4" : "12"}
        fontWeight="800"
        fontFamily="IBM Plex Sans, Inter, sans-serif"
      >
        {glyph.label}
      </text>
      {glyph.sublabel ? (
        <text
          x="20"
          y="27.8"
          textAnchor="middle"
          fill={color}
          fontSize="6.2"
          fontWeight="700"
          letterSpacing="0.06em"
          fontFamily="IBM Plex Sans, Inter, sans-serif"
        >
          {glyph.sublabel}
        </text>
      ) : null}
    </svg>
  );
}

function formatPercent(value, digits = 0) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "—";
  }
  return `${(Number(value) * 100).toFixed(digits)}%`;
}

function ScaffoldPreview({ item, label, tone }) {
  if (item?.svg) {
    return (
      <div className="pipeline-scaffold-art" style={{ "--scaffold-tone": tone }}>
        <div dangerouslySetInnerHTML={{ __html: item.svg }} />
      </div>
    );
  }

  return (
    <div className="pipeline-scaffold-art pipeline-scaffold-art--fallback" style={{ "--scaffold-tone": tone }}>
      <SourceIcon kind="crystal" color={tone} />
      <span>{label}</span>
    </div>
  );
}

function Figure1DataPipeline() {
  const { pipeline } = usePresentationData();
  const sources = [
    {
      id: "bigsoldb",
      title: "BigSolDBv2.1",
      value: `~${pipeline.solubility_rows_label ?? "101.8k"} matched rows`,
      subtitle: "solute · solvent · T · ln x₂",
      icon: "tube",
      color: COLORS.blue,
      columns: ["solute_smiles", "solvent_smiles", "T", "ln_x2"],
    },
    {
      id: "crystal",
      title: "Bradley + NIST",
      value: "crystal priors + overrides",
      subtitle: "T_m · ΔH_fus",
      icon: "crystal",
      color: COLORS.purple,
      columns: ["T_m", "dH_fus"],
    },
    {
      id: "hansen",
      title: "Hansen DB",
      value: "sparse solvent affinity labels",
      subtitle: "δ_d · δ_p · δ_h",
      icon: "axes",
      color: COLORS.green,
      columns: ["delta_hansen"],
    },
    {
      id: "idac",
      title: "IDAC",
      value: "optional infinite dilution labels",
      subtitle: "γ₂∞",
      icon: "infinity",
      color: COLORS.orange,
      columns: ["gamma_inf"],
    },
  ];
  const [activeSourceId, setActiveSourceId] = useState(sources[0].id);
  const activeSource = sources.find((source) => source.id === activeSourceId) ?? sources[0];
  const rows = (pipeline.preview_rows ?? []).map((row, index) => {
    const syntheticGamma = ["0.54", "1.12", "0.08", "0.91"][index] ?? "0.37";
    return {
      ...row,
      gamma_inf: row.gamma_inf === "—" ? syntheticGamma : row.gamma_inf,
    };
  });
  const columns = ["solute_smiles", "solvent_smiles", "T", "ln_x2", "T_m", "dH_fus", "delta_hansen", "gamma_inf"];
  const columnLabels = {
    solute_smiles: "solute_smiles",
    solvent_smiles: "solvent_smiles",
    T: "T",
    ln_x2: "ln x₂",
    T_m: "T_m",
    dH_fus: "ΔH_fus",
    delta_hansen: "δ_d/p/h",
    gamma_inf: "γ∞",
  };
  const splitRatios = pipeline.ratios ?? { train: 0.8, val: 0.1, test: 0.1 };

  return (
    <FigureCard
      kicker="Figure 1"
      title="Data Pipeline"
      subtitle="Current processed data are merged into one sparse supervision table, then scaffold-split without structural leakage."
      footer={
        <StatStrip
          items={[
            { label: "Unified rows", value: pipeline.total_rows_label ?? "120.2k" },
            { label: "Aux cells missing", value: pipeline.missing_fraction_aux_label ?? "85.0%" },
            {
              label: "Train/Test scaffold overlap",
              value: pipeline.scaffold_overlap === 0 ? "0" : String(pipeline.scaffold_overlap ?? "—"),
            },
          ]}
        />
      }
    >
      <div className="pipeline-layout pipeline-layout--reworked">
        <div className="pipeline-sources">
          {sources.map((source) => (
            <button
              type="button"
              key={source.id}
              className={`pipeline-source${source.id === activeSourceId ? " is-active" : ""}`}
              style={{ "--figure-accent": source.color }}
              onClick={() => setActiveSourceId(source.id)}
            >
              <span className="pipeline-source__icon">
                <SourceIcon kind={source.icon} color={source.color} />
              </span>
              <span className="pipeline-source__body">
                <strong>{source.title}</strong>
                <span>{source.value}</span>
                <small>{source.subtitle}</small>
              </span>
            </button>
          ))}
        </div>

        <div className="pipeline-builder pipeline-builder--expanded">
          <div className="pipeline-builder__header">
            <div>
              <span className="pipeline-builder__eyebrow">Merge & Enrich</span>
              <h3>DataBuilder</h3>
            </div>
            <div className="pipeline-builder__note">canonical-SMILES left joins</div>
          </div>

          <div className="pipeline-builder__flow">
            <span>sources</span>
            <span className="pipeline-builder__flow-arrow">→</span>
            <span className="pipeline-builder__flow-focus">solute_smiles · solvent_smiles · T</span>
            <span className="pipeline-builder__flow-arrow">→</span>
            <span>sparse supervised table</span>
          </div>

          <div className="pipeline-table pipeline-table--focus">
            <div className="pipeline-builder__table-wrap">
              <table className="pipeline-mini-table pipeline-mini-table--expanded">
                <thead>
                  <tr>
                    {columns.map((column) => (
                      <th
                        key={column}
                        className={activeSource.columns.includes(column) ? "is-highlighted" : ""}
                        style={{ "--cell-accent": activeSource.color }}
                      >
                        {columnLabels[column]}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, rowIndex) => (
                    <tr key={`${row.sample ?? row.solute_smiles}-${rowIndex}`}>
                      {columns.map((column) => {
                        const value = row[column];
                        const isMissing = value === "—";
                        const isHighlighted = activeSource.columns.includes(column);
                        return (
                          <td
                            key={`${rowIndex}-${column}`}
                            title={String(value)}
                            className={`${isMissing ? "is-missing" : ""} ${isHighlighted ? "is-highlighted" : ""}`.trim()}
                            style={{ "--cell-accent": activeSource.color }}
                          >
                            {value}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

          <div className="pipeline-builder__facts">
            <div className="pipeline-aside-card">
                <strong>Left-join sparsity</strong>
                <span>{formatPercent(pipeline.missing_fraction_aux, 1)} of auxiliary supervision slots stay empty by design.</span>
            </div>
              <div className="pipeline-aside-card">
                <strong>Current highlight</strong>
                <span>{activeSource.title}</span>
                <small>Highlighted columns are populated directly by the selected source.</small>
              </div>
              <div className="pipeline-aside-card">
                <strong>Processed split</strong>
                <span>{pipeline.split_rows_label?.train ?? "104.6k"} / {pipeline.split_rows_label?.val ?? "7.8k"} / {pipeline.split_rows_label?.test ?? "7.8k"} rows</span>
                <small>train / val / test after scaffold-aware partitioning.</small>
              </div>
              <div className="pipeline-aside-card">
                <strong>γ∞ display values</strong>
                <span>Current processed scaffold split has no matched IDAC rows, so the γ∞ column is shown schematically.</span>
              </div>
          </div>
        </div>
        </div>

        <div className="pipeline-split pipeline-split--scaffold">
          <div className="pipeline-split__header">
            <span className="pipeline-builder__eyebrow">Split</span>
            <h3>Scaffold holdout</h3>
            <p>Right panel now uses real RDKit Murcko scaffolds from the current train/test split.</p>
          </div>
          <div className="split-bar split-bar--detailed" aria-label="Train validation test split">
            <div className="split-bar__segment split-bar__segment--train" style={{ flex: splitRatios.train ?? 0.8 }}>
              <span>Train</span>
              <strong>{formatPercent(splitRatios.train ?? 0.8)}</strong>
            </div>
            <div className="split-bar__segment split-bar__segment--val split-bar__segment--compact" style={{ flex: splitRatios.val ?? 0.1 }}>
              <strong>{formatPercent(splitRatios.val ?? 0.1)}</strong>
            </div>
            <div className="split-bar__segment split-bar__segment--test split-bar__segment--compact" style={{ flex: splitRatios.test ?? 0.1 }}>
              <strong>{formatPercent(splitRatios.test ?? 0.1)}</strong>
            </div>
          </div>
          <div className="split-bar__stats">
            <div>
              <span>Train rows</span>
              <strong>{pipeline.split_rows_label?.train ?? "104.6k"}</strong>
            </div>
            <div>
              <span>Val rows</span>
              <strong>{pipeline.split_rows_label?.val ?? "7.8k"}</strong>
            </div>
            <div>
              <span>Test rows</span>
              <strong>{pipeline.split_rows_label?.test ?? "7.8k"}</strong>
            </div>
          </div>

          <div className="pipeline-scaffold-real">
            <div className="pipeline-scaffold-real__title">Real Murcko scaffolds</div>
            <div className="pipeline-scaffold-real__grid">
              <div className="pipeline-scaffold-card pipeline-scaffold-card--real">
                <ScaffoldPreview item={pipeline.scaffolds?.train} label="Train scaffold" tone={COLORS.blue} />
                <strong>Train-only core</strong>
                <small>{pipeline.scaffolds?.train?.example_name ?? "example from train split"}</small>
              </div>

              <div className="pipeline-scaffold-stop pipeline-scaffold-stop--real">
                <svg viewBox="0 0 72 64" aria-hidden="true">
                  <circle cx="36" cy="32" r="18" fill="none" stroke={COLORS.red} strokeWidth="2.8" />
                  <path d="M26 22 46 42" fill="none" stroke={COLORS.red} strokeWidth="3.2" strokeLinecap="round" />
                  <path d="M46 22 26 42" fill="none" stroke={COLORS.red} strokeWidth="3.2" strokeLinecap="round" />
                </svg>
                <span>no overlap</span>
              </div>

              <div className="pipeline-scaffold-card pipeline-scaffold-card--real">
                <ScaffoldPreview item={pipeline.scaffolds?.test} label="Test scaffold" tone={COLORS.gray} />
                <strong>Held-out core</strong>
                <small>{pipeline.scaffolds?.test?.example_name ?? "example from test split"}</small>
              </div>
            </div>
          </div>
          <p className="figure-subnote">Generated at docs build time from `train.csv` and `test.csv`; scaffold overlap is currently {pipeline.scaffold_overlap === 0 ? "zero" : pipeline.scaffold_overlap ?? "unknown"}.</p>
        </div>
      </div>
    </FigureCard>
  );
}

const ATOM_LOOKUP = {
  H: { chi: 2.2, vdw: 1.2, polar: 0.67 },
  C: { chi: 2.55, vdw: 1.7, polar: 1.76 },
  N: { chi: 3.04, vdw: 1.55, polar: 1.1 },
  O: { chi: 3.44, vdw: 1.52, polar: 0.8 },
  F: { chi: 3.98, vdw: 1.47, polar: 0.56 },
  P: { chi: 2.19, vdw: 1.8, polar: 3.63 },
  S: { chi: 2.58, vdw: 1.8, polar: 2.9 },
  Cl: { chi: 3.16, vdw: 1.75, polar: 2.18 },
  Br: { chi: 2.96, vdw: 1.85, polar: 3.05 },
  I: { chi: 2.66, vdw: 1.98, polar: 5.35 },
};

function normalizeCharge(charge) {
  if (charge === null || charge === undefined) {
    return 0;
  }
  if (typeof charge === "number") {
    return charge;
  }
  const value = Array.isArray(charge) ? charge.join("") : String(charge);
  return value.split("").reduce((sum, token) => {
    if (token === "+") {
      return sum + 1;
    }
    if (token === "-") {
      return sum - 1;
    }
    return sum;
  }, 0);
}

function bondOrder(edge) {
  if (edge.aromatic) {
    return 1.5;
  }
  if (edge.weight) {
    return edge.weight;
  }
  if (edge.bondType === "=") {
    return 2;
  }
  if (edge.bondType === "#") {
    return 3;
  }
  return 1;
}

function serializeSmilesGraph(graph) {
  const rawNodes = graph.vertices
    .filter((vertex) => vertex.value.element !== "H" && vertex.value.isDrawn !== false)
    .map((vertex) => ({
      id: vertex.id,
      label: vertex.value.element,
      x: vertex.position.x,
      y: vertex.position.y,
      aromatic: Boolean(vertex.value.isPartOfAromaticRing),
      inRing: Boolean(vertex.value.rings?.length),
      rings: vertex.value.rings ?? [],
      neighbours: vertex.neighbours ?? [],
      degree: vertex.neighbours?.length ?? 0,
      formalCharge: normalizeCharge(vertex.value.bracket?.charge),
      explicitHydrogens: vertex.value.bracket?.hcount ?? null,
    }));

  const nodeIds = new Set(rawNodes.map((node) => node.id));
  const minX = Math.min(...rawNodes.map((node) => node.x));
  const maxX = Math.max(...rawNodes.map((node) => node.x));
  const minY = Math.min(...rawNodes.map((node) => node.y));
  const maxY = Math.max(...rawNodes.map((node) => node.y));
  const width = 460;
  const height = 300;
  const padding = 30;
  const scale = Math.min(
    (width - padding * 2) / Math.max(1, maxX - minX),
    (height - padding * 2) / Math.max(1, maxY - minY),
  );

  const nodes = rawNodes.map((node) => ({
    ...node,
    cx: padding + (node.x - minX) * scale,
    cy: padding + (maxY - node.y) * scale,
    isHetero: node.label !== "C" && node.label !== "H",
  }));
  const nodeMap = new Map(nodes.map((node) => [node.id, node]));

  const edges = graph.edges
    .filter((edge) => nodeIds.has(edge.sourceId) && nodeIds.has(edge.targetId))
    .map((edge) => {
      const source = nodeMap.get(edge.sourceId);
      const target = nodeMap.get(edge.targetId);
      const sharedRing = source.rings.some((ringId) => target.rings.includes(ringId));
      return {
        id: edge.id,
        sourceId: edge.sourceId,
        targetId: edge.targetId,
        bondType: edge.bondType || "-",
        weight: edge.weight || 1,
        aromatic: Boolean(edge.isPartOfAromaticRing),
        conjugated: Boolean(edge.isPartOfAromaticRing || edge.bondType === "="),
        inRing: Boolean(edge.isPartOfAromaticRing || sharedRing),
        stereo: edge.wedge || "none",
      };
    });

  return {
    width,
    height,
    nodes,
    edges,
    stats: {
      atomCount: nodes.length,
      bondCount: edges.length,
      heteroCount: nodes.filter((node) => node.isHetero).length,
      ringCount: new Set(nodes.flatMap((node) => node.rings)).size,
    },
  };
}

function inferHybridization(node, graphData) {
  const incidentEdges = graphData.edges.filter(
    (edge) => edge.sourceId === node.id || edge.targetId === node.id,
  );
  if (node.aromatic || incidentEdges.some((edge) => edge.aromatic || edge.weight >= 2)) {
    return "sp²";
  }
  if (incidentEdges.some((edge) => edge.weight >= 3)) {
    return "sp";
  }
  return "sp³";
}

function inferHydrogenCount(node, graphData) {
  if (typeof node.explicitHydrogens === "number") {
    return node.explicitHydrogens;
  }
  const incidentEdges = graphData.edges.filter(
    (edge) => edge.sourceId === node.id || edge.targetId === node.id,
  );
  const valenceDefaults = {
    C: node.aromatic ? 3 : 4,
    N: 3,
    O: 2,
    S: 2,
    P: 3,
    F: 1,
    Cl: 1,
    Br: 1,
    I: 1,
  };
  const targetValence = valenceDefaults[node.label] ?? Math.max(1, node.degree);
  const occupied = incidentEdges.reduce((sum, edge) => sum + bondOrder(edge), 0);
  return Math.max(0, Math.round(targetValence - occupied - Math.max(0, node.formalCharge)));
}

function atomVector(node, graphData) {
  const props = ATOM_LOOKUP[node.label] ?? ATOM_LOOKUP.C;
  const hydrogenCount = inferHydrogenCount(node, graphData);
  return [
    node.isHetero ? 0.88 : 0.24,
    node.aromatic ? 0.82 : -0.18,
    (node.degree / 4) * 0.9 - 0.2,
    node.inRing ? 0.76 : -0.28,
    Math.max(-1, Math.min(1, node.formalCharge / 2)),
    (hydrogenCount / 4) * 0.9 - 0.2,
    (props.chi - 2.5) / 1.7,
    (props.polar - 1.7) / 3.9,
  ];
}

function bondLabel(edge) {
  if (edge.aromatic) {
    return "aromatic";
  }
  if (edge.weight >= 3) {
    return "triple";
  }
  if (edge.weight >= 2) {
    return "double";
  }
  return "single";
}

function bondVector(edge, graphData) {
  const source = graphData.nodes.find((node) => node.id === edge.sourceId);
  const target = graphData.nodes.find((node) => node.id === edge.targetId);
  const dx = (target?.cx ?? 0) - (source?.cx ?? 0);
  const dy = (target?.cy ?? 0) - (source?.cy ?? 0);
  const distance = Math.sqrt(dx * dx + dy * dy) / 100;
  return [
    (bondOrder(edge) / 3) * 0.9,
    edge.aromatic ? 0.84 : -0.16,
    edge.conjugated ? 0.72 : -0.22,
    edge.inRing ? 0.68 : -0.25,
    edge.stereo !== "none" ? 0.78 : -0.3,
    source?.isHetero ? 0.45 : -0.1,
    target?.isHetero ? 0.45 : -0.1,
    Math.max(-1, Math.min(1, distance - 1.1)),
  ];
}

function useSmilesExplorer(smiles) {
  const [state, setState] = useState({
    status: "loading",
    svgMarkup: "",
    graph: null,
    formula: "",
    error: "",
  });

  useEffect(() => {
    let cancelled = false;
    setState((previous) => ({ ...previous, status: "loading", error: "" }));

    SmilesDrawer.parse(
      smiles,
      (tree) => {
        try {
          const drawer = new SmilesDrawer.SvgDrawer({
            width: 420,
            height: 280,
            padding: 18,
            bondLength: 24,
            bondThickness: 1.4,
            compactDrawing: true,
            explicitHydrogens: false,
            terminalCarbons: false,
            fontSizeLarge: 11,
            fontSizeSmall: 7,
          });
          const svgElement = document.createElementNS("http://www.w3.org/2000/svg", "svg");
          drawer.draw(tree, svgElement, "light");
          const graph = serializeSmilesGraph(drawer.preprocessor.graph);
          const formula =
            typeof drawer.getMolecularFormula === "function" ? drawer.getMolecularFormula() : "";

          if (!cancelled) {
            setState({
              status: "ready",
              svgMarkup: svgElement.outerHTML,
              graph,
              formula,
              error: "",
            });
          }
        } catch (error) {
          if (!cancelled) {
            setState({
              status: "error",
              svgMarkup: "",
              graph: null,
              formula: "",
              error: error?.message ?? "Structure rendering failed.",
            });
          }
        }
      },
      (error) => {
        if (!cancelled) {
          setState({
            status: "error",
            svgMarkup: "",
            graph: null,
            formula: "",
            error: error?.message ?? "Invalid SMILES string.",
          });
        }
      },
    );

    return () => {
      cancelled = true;
    };
  }, [smiles]);

  return state;
}

function FeatureVectorGrid({ values, accent }) {
  return (
    <div className="feature-vector-grid">
      {values.map((value, index) => (
        <div
          key={`vec-${index}`}
          className="feature-vector-cell"
          style={{
            "--vector-accent": accent,
            "--vector-alpha": Math.min(1, Math.abs(value)),
          }}
        >
          <span>z{index}</span>
          <strong>{value >= 0 ? "+" : ""}{value.toFixed(2)}</strong>
        </div>
      ))}
    </div>
  );
}

function AtomInspector({ node, graphData }) {
  const props = ATOM_LOOKUP[node.label] ?? ATOM_LOOKUP.C;
  const vector = atomVector(node, graphData);
  const hydrogenCount = inferHydrogenCount(node, graphData);

  return (
    <div className="feature-inspector">
      <div className="feature-inspector__eyebrow">Selected atom</div>
      <div className="feature-inspector__title">
        <strong>{node.label}</strong>
        <span>atom #{node.id}</span>
      </div>
      <div className="feature-detail-list">
        <div><span>Hybridization</span><strong>{inferHybridization(node, graphData)}</strong></div>
        <div><span>Formal charge</span><strong>{node.formalCharge}</strong></div>
        <div><span>H count</span><strong>{hydrogenCount}</strong></div>
        <div><span>Aromatic / ring</span><strong>{node.aromatic ? "yes" : "no"} / {node.inRing ? "yes" : "no"}</strong></div>
        <div><span>χ (Pauling)</span><strong>{props.chi.toFixed(2)}</strong></div>
        <div><span>r_vdW (Å)</span><strong>{props.vdw.toFixed(2)}</strong></div>
        <div><span>α (polariz.)</span><strong>{props.polar.toFixed(2)}</strong></div>
        <div><span>Neighbours</span><strong>{node.degree}</strong></div>
      </div>
      <div className="feature-vector-card">
        <div className="feature-vector-card__title">Input tensor slice (8 dims shown)</div>
        <FeatureVectorGrid values={vector} accent={COLORS.blue} />
      </div>
    </div>
  );
}

function BondInspector({ edge, graphData }) {
  const vector = bondVector(edge, graphData);
  const source = graphData.nodes.find((node) => node.id === edge.sourceId);
  const target = graphData.nodes.find((node) => node.id === edge.targetId);

  return (
    <div className="feature-inspector">
      <div className="feature-inspector__eyebrow">Selected bond</div>
      <div className="feature-inspector__title">
        <strong>{source?.label ?? "?"}#{edge.sourceId} - {target?.label ?? "?"}#{edge.targetId}</strong>
        <span>bond #{edge.id}</span>
      </div>
      <div className="feature-detail-list">
        <div><span>Type</span><strong>{bondLabel(edge)}</strong></div>
        <div><span>Conjugated</span><strong>{edge.conjugated ? "yes" : "no"}</strong></div>
        <div><span>In ring</span><strong>{edge.inRing ? "yes" : "no"}</strong></div>
        <div><span>Stereo</span><strong>{edge.stereo}</strong></div>
        <div><span>Bond order</span><strong>{bondOrder(edge).toFixed(1)}</strong></div>
        <div><span>Endpoints</span><strong>{source?.label ?? "?"} / {target?.label ?? "?"}</strong></div>
      </div>
      <div className="feature-vector-card">
        <div className="feature-vector-card__title">Bond tensor slice (8 dims shown)</div>
        <FeatureVectorGrid values={vector} accent={COLORS.orange} />
      </div>
    </div>
  );
}

function graphNodeById(graphData, nodeId) {
  return graphData?.nodes.find((node) => node.id === nodeId) ?? null;
}

function graphIncidentEdges(graphData, nodeId) {
  return (graphData?.edges ?? []).filter(
    (edge) => edge.sourceId === nodeId || edge.targetId === nodeId,
  );
}

function graphOtherNodeId(edge, nodeId) {
  return edge.sourceId === nodeId ? edge.targetId : edge.sourceId;
}

function collectNHopNeighborhood(graphData, startId, hops = 2) {
  if (!graphData || startId === null || startId === undefined) {
    return new Set();
  }

  const visited = new Set([startId]);
  let frontier = new Set([startId]);

  for (let hop = 0; hop < hops; hop += 1) {
    const nextFrontier = new Set();
    frontier.forEach((nodeId) => {
      graphIncidentEdges(graphData, nodeId).forEach((edge) => {
        const otherId = graphOtherNodeId(edge, nodeId);
        if (!visited.has(otherId)) {
          visited.add(otherId);
          nextFrontier.add(otherId);
        }
      });
    });
    frontier = nextFrontier;
    if (!frontier.size) {
      break;
    }
  }

  return visited;
}

function averageVectors(vectors, size = 8) {
  if (!vectors.length) {
    return Array.from({ length: size }, () => 0);
  }

  const sums = Array.from({ length: size }, () => 0);
  vectors.forEach((vector) => {
    for (let index = 0; index < size; index += 1) {
      sums[index] += Number(vector[index] ?? 0);
    }
  });
  return sums.map((value) => value / vectors.length);
}

function summarizeGraphView(graphData, { maskedAtoms = [], maskedBonds = [] } = {}) {
  const maskedAtomSet = new Set(maskedAtoms);
  const maskedBondSet = new Set(maskedBonds);

  const atomSummary = averageVectors(
    (graphData?.nodes ?? []).map((node) =>
      maskedAtomSet.has(node.id) ? Array.from({ length: 8 }, () => 0) : atomVector(node, graphData),
    ),
  );
  const bondSummary = averageVectors(
    (graphData?.edges ?? []).map((edge) =>
      maskedBondSet.has(edge.id) ? Array.from({ length: 8 }, () => 0) : bondVector(edge, graphData),
    ),
  );

  return atomSummary.map((value, index) => value * 0.65 + bondSummary[index] * 0.35);
}

function findPretrainingSeedNode(graphData) {
  for (const node of graphData?.nodes ?? []) {
    if (node.label !== "C" || node.aromatic) {
      continue;
    }
    const incident = graphIncidentEdges(graphData, node.id);
    const hasDoubleO = incident.some((edge) => {
      const other = graphNodeById(graphData, graphOtherNodeId(edge, node.id));
      return bondOrder(edge) >= 2 && other?.label === "O";
    });
    const hasSingleO = incident.some((edge) => {
      const other = graphNodeById(graphData, graphOtherNodeId(edge, node.id));
      return bondOrder(edge) === 1 && other?.label === "O";
    });
    if (hasDoubleO && hasSingleO) {
      return node.id;
    }
  }
  return graphData?.nodes?.[0]?.id ?? null;
}

function findPretrainingBondTarget(graphData) {
  const carbonylBond = (graphData?.edges ?? []).find((edge) => {
    if (bondOrder(edge) < 2) {
      return false;
    }
    const source = graphNodeById(graphData, edge.sourceId);
    const target = graphNodeById(graphData, edge.targetId);
    return source?.label === "O" || target?.label === "O";
  });
  return carbonylBond?.id ?? graphData?.edges?.[0]?.id ?? null;
}

function buildPretrainingOverlay(graphData) {
  if (!graphData?.nodes?.length) {
    return null;
  }

  const seedId = findPretrainingSeedNode(graphData);
  const maskedAtomsSet = collectNHopNeighborhood(graphData, seedId, 2);
  const maskedAtoms = Array.from(maskedAtomsSet);
  const maskedBonds = graphData.edges
    .filter((edge) => maskedAtomsSet.has(edge.sourceId) && maskedAtomsSet.has(edge.targetId))
    .map((edge) => edge.id);

  const targetBondId = findPretrainingBondTarget(graphData);
  const targetBond = graphData.edges.find((edge) => edge.id === targetBondId) ?? graphData.edges[0];
  const anchorNode = graphNodeById(graphData, seedId) ?? graphData.nodes[0];

  const aromaticNodes = graphData.nodes.filter((node) => node.aromatic).map((node) => node.id);
  const heteroNodes = graphData.nodes.filter((node) => node.isHetero).map((node) => node.id);
  const aromaticEdges = graphData.edges.filter((edge) => edge.aromatic).map((edge) => edge.id);
  const lastAromaticNode = aromaticNodes.length ? aromaticNodes[aromaticNodes.length - 1] : null;
  const lastHeteroNode = heteroNodes.length ? heteroNodes[heteroNodes.length - 1] : null;

  const contrastiveAAtoms = Array.from(
    new Set([seedId, heteroNodes[0], aromaticNodes[1], aromaticNodes[3]].filter((value) => value !== null && value !== undefined)),
  ).slice(0, 3);
  const contrastiveABonds = Array.from(
    new Set([targetBond?.id, aromaticEdges[0]].filter((value) => value !== null && value !== undefined)),
  );
  const contrastiveBAtoms = Array.from(
    new Set([lastHeteroNode, aromaticNodes[0], lastAromaticNode].filter((value) => value !== null && value !== undefined)),
  ).slice(0, 3);
  const contrastiveBBonds = Array.from(
    new Set([targetBond?.id, aromaticEdges[1], aromaticEdges[2]].filter((value) => value !== null && value !== undefined)),
  ).slice(0, 2);

  return {
    seedId,
    maskedAtoms,
    maskedBonds,
    targetBondId: targetBond?.id ?? null,
    targetBondLabel: targetBond ? bondLabel(targetBond) : "single",
    targetBondAtoms: targetBond
      ? [
          graphNodeById(graphData, targetBond.sourceId),
          graphNodeById(graphData, targetBond.targetId),
        ].filter(Boolean)
      : [],
    atomSlice: atomVector(anchorNode, graphData),
    bondSlice: targetBond ? bondVector(targetBond, graphData) : Array.from({ length: 8 }, () => 0),
    graphSlice: summarizeGraphView(graphData),
    contrastiveAAtoms,
    contrastiveABonds,
    contrastiveASlice: summarizeGraphView(graphData, {
      maskedAtoms: contrastiveAAtoms,
      maskedBonds: contrastiveABonds,
    }),
    contrastiveBAtoms,
    contrastiveBBonds,
    contrastiveBSlice: summarizeGraphView(graphData, {
      maskedAtoms: contrastiveBAtoms,
      maskedBonds: contrastiveBBonds,
    }),
    anchorNode,
  };
}

function offsetBondSegment(source, target, offset) {
  const dx = target.cx - source.cx;
  const dy = target.cy - source.cy;
  const length = Math.max(1, Math.hypot(dx, dy));
  const ox = (-dy / length) * offset;
  const oy = (dx / length) * offset;
  return {
    x1: source.cx + ox,
    y1: source.cy + oy,
    x2: target.cx + ox,
    y2: target.cy + oy,
  };
}

function BondGlyph({ edge, source, target, stroke, opacity = 1, isHighlighted = false }) {
  const width = isHighlighted ? 4.8 : 3.2;
  if (edge.aromatic) {
    return (
      <>
        <line
          x1={source.cx}
          y1={source.cy}
          x2={target.cx}
          y2={target.cy}
          stroke={stroke}
          strokeWidth={width}
          strokeLinecap="round"
          opacity={opacity}
        />
        <line
          x1={source.cx}
          y1={source.cy}
          x2={target.cx}
          y2={target.cy}
          stroke={COLORS.ink}
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeDasharray="4 5"
          opacity={opacity * 0.55}
        />
      </>
    );
  }

  if (edge.weight >= 3) {
    return [-4, 0, 4].map((offset) => {
      const segment = offsetBondSegment(source, target, offset);
      return (
        <line
          key={`bond-${edge.id}-${offset}`}
          x1={segment.x1}
          y1={segment.y1}
          x2={segment.x2}
          y2={segment.y2}
          stroke={stroke}
          strokeWidth={offset === 0 ? width : width - 1}
          strokeLinecap="round"
          opacity={opacity}
        />
      );
    });
  }

  if (edge.weight >= 2) {
    return [-2.6, 2.6].map((offset) => {
      const segment = offsetBondSegment(source, target, offset);
      return (
        <line
          key={`bond-${edge.id}-${offset}`}
          x1={segment.x1}
          y1={segment.y1}
          x2={segment.x2}
          y2={segment.y2}
          stroke={stroke}
          strokeWidth={width - 0.7}
          strokeLinecap="round"
          opacity={opacity}
        />
      );
    });
  }

  return (
    <line
      x1={source.cx}
      y1={source.cy}
      x2={target.cx}
      y2={target.cy}
      stroke={stroke}
      strokeWidth={width}
      strokeLinecap="round"
      opacity={opacity}
    />
  );
}

function PretrainGraphView({
  graphData,
  accent,
  accentSoft,
  highlightedAtoms = [],
  maskedAtoms = [],
  highlightedBonds = [],
  maskedBonds = [],
  dimmedAtoms = [],
  dimmedBonds = [],
  showIndices = false,
  ariaLabel,
}) {
  if (!graphData) {
    return null;
  }

  const highlightedAtomSet = new Set(highlightedAtoms);
  const maskedAtomSet = new Set(maskedAtoms);
  const highlightedBondSet = new Set(highlightedBonds);
  const maskedBondSet = new Set(maskedBonds);
  const dimmedAtomSet = new Set(dimmedAtoms);
  const dimmedBondSet = new Set(dimmedBonds);

  return (
    <svg
      className="pretrain-graph-svg"
      viewBox={`0 0 ${graphData.width} ${graphData.height}`}
      role="img"
      aria-label={ariaLabel}
    >
      {graphData.edges.map((edge) => {
        const source = graphNodeById(graphData, edge.sourceId);
        const target = graphNodeById(graphData, edge.targetId);
        const isHighlighted = highlightedBondSet.has(edge.id);
        const isMasked = maskedBondSet.has(edge.id);
        const opacity = dimmedBondSet.has(edge.id) ? 0.18 : 1;
        const stroke = isHighlighted ? accent : isMasked ? COLORS.ink : edge.aromatic ? COLORS.sky : COLORS.line;

        return (
          <g key={`pretrain-edge-${edge.id}`}>
            <BondGlyph
              edge={edge}
              source={source}
              target={target}
              stroke={stroke}
              opacity={opacity}
              isHighlighted={isHighlighted}
            />
          </g>
        );
      })}

      {graphData.nodes.map((node) => {
        const isHighlighted = highlightedAtomSet.has(node.id);
        const isMasked = maskedAtomSet.has(node.id);
        const opacity = dimmedAtomSet.has(node.id) ? 0.22 : 1;
        const stroke = isHighlighted ? accent : node.isHetero ? COLORS.purple : node.aromatic ? COLORS.blue : COLORS.gray;
        const fill = isMasked ? COLORS.ink : isHighlighted ? accentSoft : "#FFFFFF";

        return (
          <g key={`pretrain-node-${node.id}`} opacity={opacity}>
            {isHighlighted ? (
              <circle cx={node.cx} cy={node.cy} r="19" fill="none" stroke={accent} strokeOpacity="0.22" strokeWidth="8" />
            ) : null}
            <circle
              cx={node.cx}
              cy={node.cy}
              r={isHighlighted ? 15.5 : 13.8}
              fill={fill}
              stroke={stroke}
              strokeWidth={isHighlighted ? 3.8 : 2.7}
            />
            <text
              x={node.cx}
              y={node.cy + 4.6}
              textAnchor="middle"
              fontSize="13"
              fontWeight="800"
              fill={isMasked ? "#FFFFFF" : node.isHetero ? COLORS.purple : COLORS.ink}
            >
              {node.label}
            </text>
            {showIndices ? (
              <text
                x={node.cx}
                y={node.cy - 18}
                textAnchor="middle"
                fontSize="10"
                fontWeight="800"
                fill={COLORS.slate}
              >
                {node.id}
              </text>
            ) : null}
          </g>
        );
      })}
    </svg>
  );
}

function Figure2Featurization() {
  const defaultSmiles = "CC(=O)Nc1ccc(O)cc1";
  const [draftSmiles, setDraftSmiles] = useState(defaultSmiles);
  const [committedSmiles, setCommittedSmiles] = useState(defaultSmiles);
  const [selectedEntity, setSelectedEntity] = useState({ type: "atom", id: null });
  const explorer = useSmilesExplorer(committedSmiles);

  useEffect(() => {
    if (explorer.status !== "ready" || !explorer.graph?.nodes.length) {
      return;
    }
    const firstHetero = explorer.graph.nodes.find((node) => node.isHetero) ?? explorer.graph.nodes[0];
    setSelectedEntity({ type: "atom", id: firstHetero.id });
  }, [committedSmiles, explorer.status, explorer.graph?.nodes?.length]);

  const selectedAtom =
    selectedEntity.type === "atom"
      ? explorer.graph?.nodes.find((node) => node.id === selectedEntity.id)
      : null;
  const selectedBond =
    selectedEntity.type === "bond"
      ? explorer.graph?.edges.find((edge) => edge.id === selectedEntity.id)
      : null;

  return (
    <FigureCard
      kicker="Figure 2"
      title="Molecular Featurization"
      subtitle="The slide now uses one parsed SMILES source for both the 2D depiction and the graph, with clickable atoms and bonds on the right."
    >
      <div className="featurization-rebuilt featurization-rebuilt--interactive">
        <div className="featurization-flow">
          <span>canonical SMILES</span>
          <span>→ 2D depiction</span>
          <span>→ graph topology</span>
          <span>→ click atom/bond to inspect tensor slice</span>
        </div>

        <form
          className="smiles-input-bar"
          onSubmit={(event) => {
            event.preventDefault();
            setCommittedSmiles(draftSmiles.trim() || defaultSmiles);
          }}
        >
          <label className="smiles-input-bar__field">
            <span>SMILES input</span>
            <input
              type="text"
              value={draftSmiles}
              onChange={(event) => setDraftSmiles(event.target.value)}
              spellCheck="false"
            />
          </label>
          <button type="submit" className="pill-button pill-button--primary">Render</button>
          <button
            type="button"
            className="pill-button"
            onClick={() => {
              setDraftSmiles(defaultSmiles);
              setCommittedSmiles(defaultSmiles);
            }}
          >
            Reset
          </button>
        </form>

        <div className="featurization-panels featurization-panels--interactive">
          <section className="featurization-panel featurization-panel--input">
            <div className="featurization-label">SMILES string</div>
            <div className="smiles-card smiles-card--interactive">{committedSmiles}</div>
            <div className="molecule-stats-grid">
              <div><strong>{explorer.graph?.stats.atomCount ?? "—"}</strong><span>atoms</span></div>
              <div><strong>{explorer.graph?.stats.bondCount ?? "—"}</strong><span>bonds</span></div>
              <div><strong>{explorer.graph?.stats.ringCount ?? "—"}</strong><span>rings</span></div>
              <div><strong>{explorer.formula || "—"}</strong><span>formula</span></div>
            </div>
            <p className="figure-subnote">Default input is paracetamol. The same parsed graph drives both depiction and graph tensors.</p>
          </section>

          <section className="featurization-panel featurization-panel--structure">
            <div className="featurization-label">2D depiction</div>
            {explorer.status === "error" ? (
              <div className="molecule-error">{explorer.error}</div>
            ) : (
              <div className="molecule-render" dangerouslySetInnerHTML={{ __html: explorer.svgMarkup }} />
            )}
            <p className="figure-subnote">Rendered automatically from the current input instead of a hand-drawn placeholder.</p>
          </section>

          <section className="featurization-panel featurization-panel--graph">
            <div className="featurization-label">Interactive molecular graph</div>
            {explorer.status === "error" ? (
              <div className="molecule-error">{explorer.error}</div>
            ) : (
              <div className="graph-explorer">
                <svg
                  className="graph-svg graph-svg--interactive"
                  viewBox={`0 0 ${explorer.graph?.width ?? 460} ${explorer.graph?.height ?? 300}`}
                  role="img"
                  aria-label={`Molecular graph for ${committedSmiles}`}
                >
                  {explorer.graph?.edges.map((edge) => {
                    const source = explorer.graph.nodes.find((node) => node.id === edge.sourceId);
                    const target = explorer.graph.nodes.find((node) => node.id === edge.targetId);
                    const isSelected = selectedEntity.type === "bond" && selectedEntity.id === edge.id;
                    return (
                      <g key={`edge-${edge.id}`}>
                        <line
                          x1={source.cx}
                          y1={source.cy}
                          x2={target.cx}
                          y2={target.cy}
                          stroke={isSelected ? COLORS.orange : edge.aromatic ? COLORS.blue : COLORS.line}
                          strokeWidth={isSelected ? 7 : edge.aromatic ? 4.6 : edge.weight >= 2 ? 4.2 : 3.5}
                          strokeLinecap="round"
                        />
                        <line
                          x1={source.cx}
                          y1={source.cy}
                          x2={target.cx}
                          y2={target.cy}
                          stroke="transparent"
                          strokeWidth="18"
                          strokeLinecap="round"
                          className="graph-hitline"
                          onClick={() => setSelectedEntity({ type: "bond", id: edge.id })}
                        />
                      </g>
                    );
                  })}

                  {explorer.graph?.nodes.map((node) => {
                    const isSelected = selectedEntity.type === "atom" && selectedEntity.id === node.id;
                    return (
                      <g
                        key={`node-${node.id}`}
                        className="graph-node"
                        onClick={() => setSelectedEntity({ type: "atom", id: node.id })}
                      >
                        <circle
                          cx={node.cx}
                          cy={node.cy}
                          r={isSelected ? 18 : 15}
                          fill={isSelected ? COLORS.blueSoft : "#FFFFFF"}
                          stroke={isSelected ? COLORS.blue : node.isHetero ? COLORS.purple : COLORS.gray}
                          strokeWidth={isSelected ? 4.2 : 3}
                        />
                        <text
                          x={node.cx}
                          y={node.cy + 5}
                          textAnchor="middle"
                          fontSize="15"
                          fontWeight="800"
                          fill={node.isHetero ? COLORS.purple : COLORS.ink}
                        >
                          {node.label}
                        </text>
                      </g>
                    );
                  })}
                </svg>

                <div className="graph-explorer__detail">
                  {selectedBond ? (
                    <BondInspector edge={selectedBond} graphData={explorer.graph} />
                  ) : selectedAtom ? (
                    <AtomInspector node={selectedAtom} graphData={explorer.graph} />
                  ) : (
                    <div className="feature-inspector feature-inspector--empty">Click any atom or bond to inspect its features.</div>
                  )}
                </div>
              </div>
            )}
            <p className="figure-subnote">Click a node or edge on the graph to switch the inspector between atom and bond tensors.</p>
          </section>
        </div>
      </div>
    </FigureCard>
  );
}

function FigurePretraining() {
  const exampleSmiles = "CC(=O)Oc1ccccc1C(=O)O";
  const explorer = useSmilesExplorer(exampleSmiles);
  const graphData = explorer.graph;
  const overlay = buildPretrainingOverlay(graphData);
  const descriptorRows = [
    { name: "MolLogP", value: "1.31", note: "lipophilicity" },
    { name: "TPSA", value: "63.6", note: "polar surface area" },
    { name: "MolWt", value: "180.2", note: "molecular weight" },
    { name: "FractionCSP3", value: "0.11", note: "aliphatic fraction" },
    { name: "NumHAcceptors", value: "3", note: "H-bond acceptors" },
    { name: "LabuteASA", value: "74.8", note: "approx. surface area" },
  ];

  const targetBondAtomIds = overlay?.targetBondAtoms?.map((node) => node.id) ?? [];
  const dimmedMaskAtoms = graphData?.nodes
    ?.filter((node) => !(overlay?.maskedAtoms ?? []).includes(node.id))
    .map((node) => node.id) ?? [];
  const dimmedMaskBonds = graphData?.edges
    ?.filter((edge) => !(overlay?.maskedBonds ?? []).includes(edge.id))
    .map((edge) => edge.id) ?? [];

  return (
    <FigureCard
      kicker="Stage 0"
      title="Pretraining"
      subtitle="The repository now treats Stage 0 as a maintained warm-start pipeline spanning `pretrain.py`, `pretrain_pipeline.py`, and the training CLI."
      footer={
        <StatStrip
          items={[
            { label: "Source", value: "ZINC250k" },
            { label: "Targets", value: "12 RDKit props" },
            { label: "Batch / LR", value: "128 / 3e-4" },
            { label: "Encoder", value: "MPNN or GPS" },
          ]}
        />
      }
    >
      <div className="pretrain-layout pretrain-layout--real">
        <div className="pretrain-topbar">
          <div className="pretrain-meta-card">
            <div className="pipeline-builder__eyebrow">SMILES source</div>
            <strong>`download_zinc250k()`</strong>
            <span>ZINC250k when available, otherwise canonicalized BigSolDB SMILES fallback.</span>
          </div>
          <div className="pretrain-flow-card">
            <div className="pretrain-flow-card__row">
              <span>SMILES</span>
              <span>→</span>
              <span>`PretrainDataset`</span>
              <span>→</span>
              <span>shared encoder + readout</span>
            </div>
            <div className="pretrain-flow-card__note">
              Updates `model.gnn` and `model.readout` in place, then discards the temporary Stage 0 heads.
            </div>
          </div>
          <div className="pretrain-meta-card">
            <div className="pipeline-builder__eyebrow">Repo behavior</div>
            <strong>Optional, checkpointable</strong>
            <span>`scripts/training/train.py --pretrain`, `--pretrain-checkpoint`, and `scripts/training/train_with_pretrain.py` all drive the same Stage 0 pipeline and can reuse saved encoder/readout warm starts.</span>
          </div>
        </div>

        <div className="pretrain-overview">
          <section className="pretrain-overview__structure">
            <div className="pretrain-task-card__eyebrow">Real molecule used across all four tasks</div>
            <strong>Aspirin · {exampleSmiles}</strong>
            {explorer.status === "ready" ? (
              <div className="pretrain-structure-frame" dangerouslySetInnerHTML={{ __html: explorer.svgMarkup }} />
            ) : (
              <div className="molecule-error">{explorer.error || "Rendering structure…"}</div>
            )}
            <p className="figure-subnote">The same parsed SMILES drives both the 2D depiction and the graph below; the slide no longer uses hand-drawn toy nodes.</p>
          </section>

          <section className="pretrain-overview__graph">
            <div className="pretrain-task-card__eyebrow">Structure → graph → shared MPNN / GPS encoder</div>
            <div className="pretrain-graph-frame pretrain-graph-frame--large">
              {graphData ? (
                <PretrainGraphView
                  graphData={graphData}
                  accent={COLORS.blue}
                  accentSoft={COLORS.blueSoft}
                  highlightedAtoms={overlay ? [overlay.seedId] : []}
                  highlightedBonds={overlay?.targetBondId ? [overlay.targetBondId] : []}
                  ariaLabel="Real molecular graph used for Stage 0 pretraining tasks"
                />
              ) : (
                <div className="molecule-error">{explorer.error || "Rendering graph…"}</div>
              )}
            </div>
            <div className="pretrain-mini-pipeline">
              <span>SMILES</span>
              <span>→</span>
              <span>`smiles_to_graph()`</span>
              <span>→</span>
              <span>GNN encoder</span>
              <span>→</span>
              <span>`h_atoms`, `g_mol`, `z`</span>
            </div>
            <p className="figure-subnote">`test_pretrain_pipeline.py` explicitly checks that Stage 0 passes the graph `batch` vector through the encoder, which is why GPS remains pretraining-safe rather than a special-case branch.</p>
          </section>

          <section className="pretrain-overview__vectors">
            <div className="pretrain-signal-card">
              <div className="pretrain-task-card__eyebrow">Masked atom target slice</div>
              <strong>{overlay ? `${overlay.anchorNode.label}${overlay.anchorNode.id}` : "atom slice"}</strong>
              <FeatureVectorGrid values={overlay?.atomSlice ?? Array.from({ length: 8 }, () => 0)} accent={COLORS.blue} />
            </div>
            <div className="pretrain-signal-card">
              <div className="pretrain-task-card__eyebrow">Graph summary slice</div>
              <strong>`g_mol` before task heads</strong>
              <FeatureVectorGrid values={overlay?.graphSlice ?? Array.from({ length: 8 }, () => 0)} accent={COLORS.green} />
            </div>
          </section>
        </div>

        <div className="pretrain-task-grid pretrain-task-grid--real">
          <section className="pretrain-task-card pretrain-task-card--blue">
            <div className="pretrain-task-card__title">1. Masked 2-hop subgraph</div>
            <div className="pretrain-task-card__split">
              <div className="pretrain-graph-frame">
                {graphData ? (
                  <PretrainGraphView
                    graphData={graphData}
                    accent={COLORS.blue}
                    accentSoft={COLORS.blueSoft}
                    highlightedAtoms={overlay ? [overlay.seedId] : []}
                    maskedAtoms={overlay?.maskedAtoms ?? []}
                    maskedBonds={overlay?.maskedBonds ?? []}
                    dimmedAtoms={dimmedMaskAtoms}
                    dimmedBonds={dimmedMaskBonds}
                    showIndices
                    ariaLabel="Two-hop masked neighborhood on a real molecular graph"
                  />
                ) : null}
              </div>
              <div className="pretrain-task-card__meta">
                <div className="pretrain-task-card__eyebrow">`PretrainDataset._mask_subgraph()`</div>
                <p className="figure-subnote">A real carbonyl-centered neighborhood is zeroed before the encoder. The dark connected component is the 2-hop mask, not a disconnected random atom sample.</p>
                <TexBlock>{"L_{atom} = \\|\\hat x_{mask} - x_{mask}\\|_2^2"}</TexBlock>
                <div className="pretrain-legend">
                  <span><i style={{ background: COLORS.ink }} /> masked atoms</span>
                  <span><i style={{ background: COLORS.blue }} /> seed / context anchor</span>
                </div>
              </div>
            </div>
          </section>

          <section className="pretrain-task-card pretrain-task-card--purple">
            <div className="pretrain-task-card__title">2. Bond type prediction</div>
            <div className="pretrain-task-card__split">
              <div className="pretrain-graph-frame">
                {graphData ? (
                  <PretrainGraphView
                    graphData={graphData}
                    accent={COLORS.purple}
                    accentSoft={COLORS.purpleSoft}
                    highlightedAtoms={targetBondAtomIds}
                    highlightedBonds={overlay?.targetBondId ? [overlay.targetBondId] : []}
                    ariaLabel="Real molecular bond highlighted for bond-type prediction"
                  />
                ) : null}
              </div>
              <div className="pretrain-task-card__meta">
                <div className="pretrain-task-card__eyebrow">`BondPredictionHead`</div>
                <p className="figure-subnote">The highlighted carbonyl bond is read from the parsed structure, endpoint states are concatenated as <TexInline>{"[h_u \\parallel h_v]"}</TexInline>, and the head predicts one of the four bond classes stored in `edge_attr[:, :4]`.</p>
                <div className="pretrain-bond-classes">
                  {["single", "double", "triple", "aromatic"].map((label) => (
                    <span key={label} className={`pretrain-bond-class${overlay?.targetBondLabel === label ? " is-active" : ""}`}>
                      {label}
                    </span>
                  ))}
                </div>
                <TexBlock>{"L_{bond} = \\mathrm{CE}(\\hat y_{bond}, y_{bond})"}</TexBlock>
              </div>
            </div>
          </section>

          <section className="pretrain-task-card pretrain-task-card--green">
            <div className="pretrain-task-card__title">3. RDKit property regression</div>
            <div className="pretrain-task-card__split">
              <div className="pretrain-property-structure">
                {explorer.status === "ready" ? (
                  <div dangerouslySetInnerHTML={{ __html: explorer.svgMarkup }} />
                ) : (
                  <div className="molecule-error">{explorer.error || "Rendering structure…"}</div>
                )}
              </div>
              <div className="pretrain-task-card__meta">
                <div className="pretrain-task-card__eyebrow">Real descriptor targets from RDKit</div>
                <div className="pretrain-descriptor-grid">
                  {descriptorRows.map((row) => (
                    <div key={row.name} className="pretrain-descriptor-card">
                      <div className="pretrain-descriptor-card__name">{row.name}</div>
                      <strong>{row.value}</strong>
                      <small>{row.note}</small>
                    </div>
                  ))}
                </div>
                <p className="figure-subnote">
                  These are actual RDKit targets computed on the aspirin graph. The maintained property head regresses a
                  12-dimensional descriptor vector from the pooled representation <TexInline>{"g_{mol}"}</TexInline>, so
                  Stage 0 teaches the encoder to preserve global molecular semantics that matter for solubility before
                  the sparse thermodynamic labels appear.
                </p>
                <TexBlock>{"L_{prop} = \\|\\hat p - p\\|_2^2"}</TexBlock>
              </div>
            </div>
          </section>

          <section className="pretrain-task-card pretrain-task-card--orange">
            <div className="pretrain-task-card__title">4. Graph contrastive learning</div>
            <div className="pretrain-contrastive-row">
              <div className="pretrain-contrastive-view">
                <div className="pretrain-task-card__eyebrow">aug view 1</div>
                <div className="pretrain-graph-frame pretrain-graph-frame--compact">
                  {graphData ? (
                    <PretrainGraphView
                      graphData={graphData}
                      accent={COLORS.orange}
                      accentSoft={COLORS.amberSoft}
                      maskedAtoms={overlay?.contrastiveAAtoms ?? []}
                      maskedBonds={overlay?.contrastiveABonds ?? []}
                      highlightedAtoms={overlay?.contrastiveAAtoms?.slice(0, 1) ?? []}
                      ariaLabel="First augmented graph view for contrastive pretraining"
                    />
                  ) : null}
                </div>
                <FeatureVectorGrid values={overlay?.contrastiveASlice ?? Array.from({ length: 8 }, () => 0)} accent={COLORS.orange} />
              </div>
              <div className="pretrain-contrastive-view">
                <div className="pretrain-task-card__eyebrow">aug view 2</div>
                <div className="pretrain-graph-frame pretrain-graph-frame--compact">
                  {graphData ? (
                    <PretrainGraphView
                      graphData={graphData}
                      accent={COLORS.orange}
                      accentSoft={COLORS.amberSoft}
                      maskedAtoms={overlay?.contrastiveBAtoms ?? []}
                      maskedBonds={overlay?.contrastiveBBonds ?? []}
                      highlightedAtoms={overlay?.contrastiveBAtoms?.slice(0, 1) ?? []}
                      ariaLabel="Second augmented graph view for contrastive pretraining"
                    />
                  ) : null}
                </div>
                <FeatureVectorGrid values={overlay?.contrastiveBSlice ?? Array.from({ length: 8 }, () => 0)} accent={COLORS.orange} />
              </div>
            </div>
            <p className="figure-subnote">Both views come from the same real molecule after node and edge zeroing. The graph is pooled to `g_aug`, projected to 128-d, normalized, and matched across the batch.</p>
            <TexBlock>{"L_{ctr} = \\tfrac{1}{2}\\left[\\mathrm{CE}(z_1 z_2^\\top / \\tau, y) + \\mathrm{CE}(z_2 z_1^\\top / \\tau, y)\\right]"}</TexBlock>
          </section>
        </div>

        <div className="pretrain-loss-card">
          <div className="pretrain-loss-card__main">
            <TexBlock>{"L = 1.0\\,L_{atom} + 0.5\\,L_{bond} + 1.0\\,L_{prop} + 0.5\\,L_{ctr}"}</TexBlock>
            <p className="figure-subnote">Default optimizer path in the repo: AdamW, cosine LR schedule, gradient clipping at 1.0, Stage 0 heads removed after pretraining completes, and an optional reusable checkpoint payload with `gnn_state_dict`, `readout_state_dict`, history, and metadata.</p>
          </div>
          <div className="pretrain-loss-card__chips">
            <span>`n_epochs=30`</span>
            <span>`batch_size=128`</span>
            <span>`mask_ratio=0.15`</span>
            <span>`bond_mask_ratio=0.15`</span>
            <span>`aug_node_mask_ratio=0.15`</span>
            <span>`aug_edge_mask_ratio=0.15`</span>
          </div>
        </div>
      </div>
    </FigureCard>
  );
}

function Figure3Architecture() {
  return (
    <FigureCard
      kicker="Figure 3"
      title="TGNN-Solv Architecture"
      subtitle="A vertical, physics-bottlenecked forward path from graphs to `ln x₂_final`."
      footer={
        <FigureLegend
          items={[
            { label: "Encoding", color: "rgba(37, 99, 235, 0.70)" },
            { label: "Auxiliary heads", color: "rgba(139, 92, 246, 0.70)" },
            { label: "Interaction", color: "rgba(16, 185, 129, 0.70)" },
            { label: "Physics", color: "rgba(245, 158, 11, 0.70)" },
            { label: "Solver", color: "rgba(239, 68, 68, 0.70)" },
          ]}
        />
      }
    >
      <div className="architecture-rebuilt architecture-rebuilt--compact">
        <section className="architecture-zone architecture-zone--blue">
          <div className="architecture-zone__title">1. Molecular encoding</div>
          <div className="architecture-compact-grid architecture-compact-grid--two">
            <div className="architecture-card architecture-card--label">Solute graph</div>
            <div className="architecture-card architecture-card--label">Solvent graph</div>
            <div className="architecture-card architecture-card--shared architecture-card--span-2">
              <div className="architecture-card__row">
                <div>
                  <strong>Shared GNN encoder</strong>
                  <span>`encoder_type = mpnn | gps` with tied weights</span>
                </div>
                <div className="architecture-badge">weight sharing</div>
              </div>
              <div className="architecture-encoding-grid">
                <div className="architecture-card architecture-card--ghost">h_sol atoms</div>
                <div className="architecture-card architecture-card--ghost">GPS adds Laplacian / RWSE PE + global attention</div>
                <div className="architecture-card architecture-card--ghost">h_slv atoms</div>
              </div>
            </div>
          </div>
        </section>

        <div className="architecture-flow-down architecture-flow-down--between">↓</div>

        <section className="architecture-zone architecture-zone--purple">
          <div className="architecture-zone__title">2. Pre-interaction heads</div>
          <div className="architecture-compact-grid architecture-compact-grid--two">
            <div className="architecture-card">
              <div className="architecture-card__row">
                <strong>FusionHead</strong>
                <span className="architecture-chip architecture-chip--ghost">temperature-invariant</span>
              </div>
              <span>Predicts <TexInline>{"T_m,\\ \\Delta H_{fus}"}</TexInline></span>
              <TexBlock>{"T_m = T_m^{GC} + 50\\tanh(h)"}</TexBlock>
              <small>Bounded residual around a calibrated Joback prior.</small>
            </div>
            <div className="architecture-card">
              <div className="architecture-card__row">
                <strong>HansenHead</strong>
                <span className="architecture-chip architecture-chip--ghost">temperature-invariant</span>
              </div>
              <span><TexInline>{"\\delta_d,\\ \\delta_p,\\ \\delta_h"}</TexInline> from solute features</span>
              <small>Auxiliary branch regularizes the solute representation before interaction.</small>
            </div>
          </div>
        </section>

        <div className="architecture-flow-down architecture-flow-down--between">↓</div>

        <section className="architecture-zone architecture-zone--green">
          <div className="architecture-zone__title">3. Interaction & readout</div>
          <div className="architecture-compact-grid architecture-compact-grid--two">
            <div className="architecture-card architecture-card--ghost">h_sol atoms</div>
            <div className="architecture-card architecture-card--ghost">h_slv atoms</div>
            <div className="architecture-card architecture-card--span-2">
              <strong>Cross-attention ×3</strong>
              <span>Bidirectional solute ↔ solvent context exchange.</span>
            </div>
            <div className="architecture-card architecture-card--span-2">
              <strong>Attention + Set2Set readout</strong>
              <span><TexInline>{"g_{sol}"}</TexInline> and <TexInline>{"g_{slv}"}</TexInline> pooled from interacting atom states</span>
            </div>
            <div className="architecture-card architecture-card--ghost">g_sol (3d)</div>
            <div className="architecture-card architecture-card--ghost">g_slv (3d)</div>
            <div className="architecture-card architecture-card--span-2">
              <strong>Pair representation</strong>
              <TexBlock>{"g_{pair} = [g_{sol} \\parallel g_{slv} \\parallel g_{sol}\\odot g_{slv} \\parallel |g_{sol}-g_{slv}|]"}</TexBlock>
            </div>
            <div className="architecture-card architecture-card--optional architecture-card--span-2">
              <strong>Optional TGNN descriptor augmentation</strong>
              <span>RDKit descriptors → normalize → MLP → pair-level fusion → project back to <TexInline>{"g_{pair}"}</TexInline></span>
            </div>
          </div>
        </section>

        <div className="architecture-flow-down architecture-flow-down--between">↓</div>

        <section className="architecture-zone architecture-zone--orange">
          <div className="architecture-zone__title">4. Physics heads</div>
          <div className="architecture-compact-grid architecture-compact-grid--three">
            <div className="architecture-card architecture-card--ghost">pair embedding + temperature</div>
            <div className="architecture-card architecture-card--ghost">thermometer injection</div>
            <div className="architecture-card">
              <strong>NRTLHead</strong>
              <span><TexInline>{"\\tau_{12}(T),\\ \\tau_{21}(T),\\ \\alpha"}</TexInline></span>
            </div>
          </div>
        </section>

        <div className="architecture-flow-down architecture-flow-down--between">↓</div>

        <section className="architecture-zone architecture-zone--red">
          <div className="architecture-zone__title">5. SLE solver & correction</div>
          <div className="architecture-compact-grid architecture-compact-grid--two">
            <div className="architecture-card architecture-card--solver">
              <div className="architecture-card__row">
                <strong>Hardcoded SLE solver</strong>
                <div className="architecture-badge architecture-badge--solver">0 learnable params</div>
              </div>
              <TexBlock>{"\\Phi(T)=\\frac{\\Delta H}{R}\\left(\\frac{1}{T}-\\frac{1}{T_m}\\right)-\\Delta C_p\\,\\psi(T)"}</TexBlock>
              <div className="solver-loop">
                <span><TexInline>{"x_2^{(0)} = \\exp(-\\Phi)"}</TexInline></span>
                <span><TexInline>{"\\ln \\gamma_2 = \\mathrm{NRTL}(x_1,x_2,\\tau,\\alpha)"}</TexInline></span>
                <span><TexInline>{"x_2^{(k+1)} = \\lambda e^{-\\Phi-\\ln\\gamma_2} + (1-\\lambda)x_2^{(k)}"}</TexInline></span>
              </div>
              <TexBlock>{"\\frac{d x_2^*}{d\\theta} = -\\frac{\\partial(\\Phi + \\ln\\gamma_2)/\\partial\\theta}{1 + x_2^*\\eta}"}</TexBlock>
            </div>
            <div className="architecture-card">
              <strong>Bounded correction</strong>
              <TexBlock>{"\\delta\\theta: \\{T_m,\\ \\Delta H,\\ \\tau\\}"}</TexBlock>
              <TexBlock>{"\\ln x_{2,final} = \\ln x_{2,physics} + (1-gate)\\,\\mathrm{clip}(\\Delta)"}</TexBlock>
              <span>Residual correction stays in parameter space instead of bypassing the solver.</span>
            </div>
            <div className="architecture-card architecture-card--final architecture-card--span-2">
              <strong><TexInline>{"\\ln x_{2,final}"}</TexInline></strong>
              <span>Physics-guided prediction with bounded correction.</span>
            </div>
          </div>
        </section>
      </div>
    </FigureCard>
  );
}

function Figure3ABaseline() {
  return (
    <FigureCard
      kicker="Figure 3A"
      title="Matched Baseline"
      subtitle="TGNN-Solv and DirectGNN share the same upstream chemistry stack; the maintained comparison isolates the physics bottleneck itself."
      footer={
        <StatStrip
          items={[
            { label: "Shared encoder", value: "same MPNN / GPS" },
            { label: "Shared interaction", value: "same cross-attn" },
            { label: "Different head", value: "physics vs direct" },
          ]}
        />
      }
    >
      <div className="baseline-slide">
        <ExamplePairStrip compact />

        <section className="baseline-shared">
          <div className="baseline-shared__header">
            <div>
              <span className="pipeline-builder__eyebrow">Controlled comparison</span>
              <h3>Everything upstream is matched</h3>
            </div>
            <small>Fair ablation of the physics path, not a completely different backbone.</small>
          </div>
          <div className="baseline-shared__flow">
            <div className="baseline-chip baseline-chip--shared">Shared GNN encoder</div>
            <div className="baseline-arrow">→</div>
            <div className="baseline-chip baseline-chip--shared">Cross-attention / interaction</div>
            <div className="baseline-arrow">→</div>
            <div className="baseline-chip baseline-chip--shared">PhysicsAwareReadout</div>
            <div className="baseline-arrow">→</div>
            <div className="baseline-chip baseline-chip--shared">pair representation</div>
          </div>
        </section>

        <div className="baseline-branches">
          <section className="baseline-lane baseline-lane--physics">
            <div className="baseline-lane__header">
              <strong>TGNN-Solv</strong>
              <span className="baseline-lane__badge baseline-lane__badge--physics">physics bottleneck</span>
            </div>
            <div className="baseline-lane__stack">
              <div className="baseline-chip">FusionHead → <TexInline>{"T_m,\\ \\Delta H_{fus},\\ \\Delta C_p"}</TexInline></div>
              <div className="baseline-chip">NRTLHead → <TexInline>{"\\tau_{12}(T),\\ \\tau_{21}(T),\\ \\alpha"}</TexInline></div>
              <div className="baseline-chip">Hardcoded SLE solver + bounded correction</div>
            </div>
            <TexBlock>{"\\ln x_{2,final} = \\mathrm{SLE}(\\theta_{pred}) + (1-gate)\\,\\mathrm{clip}(\\Delta)"}</TexBlock>
            <div className="baseline-lane__notes">
              <div>Pros: extrapolation, interpretable intermediates, thermodynamic structure.</div>
              <div>Constraint: representation errors are filtered through the solver-facing parameterization.</div>
            </div>
          </section>

          <section className="baseline-lane baseline-lane--direct">
            <div className="baseline-lane__header">
              <strong>DirectGNN</strong>
              <span className="baseline-lane__badge baseline-lane__badge--direct">no explicit physics</span>
            </div>
            <div className="baseline-lane__stack">
              <div className="baseline-chip">thermometer temperature encoding</div>
              <div className="baseline-chip">direct MLP → <TexInline>{"\\ln x_2"}</TexInline></div>
              <div className="baseline-chip">optional Morgan / descriptor augmentation</div>
            </div>
            <TexBlock>{"\\ln x_2 = \\mathrm{MLP}\\big([g_{pair} \\parallel \\mathrm{temp}(T)]\\big)"}</TexBlock>
            <div className="baseline-lane__notes">
              <div>Pros: simpler head, fewer structured constraints, easy descriptor fusion.</div>
              <div>Removes <code>FusionHead</code>, <code>NRTLHead</code>, <code>SLESolver</code>, and <code>AdaptivePhysicsCorrection</code>.</div>
            </div>
          </section>
        </div>

        <div className="baseline-summary-grid">
          <div className="baseline-summary-card">
            <strong>Same chemistry frontend</strong>
            <span>The experiment holds graph encoding, interaction, and readout fixed, even when the shared encoder family is switched from MPNN to GPS.</span>
          </div>
          <div className="baseline-summary-card">
            <strong>One modeling question</strong>
            <span>Does routing prediction through explicit thermodynamics help beyond the same backbone trained directly?</span>
          </div>
          <div className="baseline-summary-card">
            <strong>Descriptor path stays fair</strong>
            <span>Descriptor augmentation can now be matched on both families; fair comparisons keep the upstream extras aligned and only change the final prediction head.</span>
          </div>
        </div>
      </div>
    </FigureCard>
  );
}

function Figure3BDiagnostics() {
  return (
    <FigureCard
      kicker="Figure 3B"
      title="Solver-Facing Diagnostics"
      subtitle="`model.forward(...)` exposes both raw head outputs and the values that actually enter the solver, which makes oracle/GC diagnostics auditable."
      footer={
        <FigureLegend
          items={[
            { label: "raw predictions", color: "rgba(37, 99, 235, 0.70)" },
            { label: "solver-facing substitution", color: "rgba(245, 158, 11, 0.70)" },
            { label: "diagnostic exports", color: "rgba(16, 185, 129, 0.70)" },
          ]}
        />
      }
    >
      <div className="solver-diag-slide">
        <div className="solver-diag-header">
          <ExamplePairStrip compact />
          <div className="solver-diag-formula-card">
            <span className="pipeline-builder__eyebrow">solver substitution</span>
            <TexBlock>{"\\theta_{solver} = (1-m)\\odot\\theta_{pred} + m\\odot\\theta_{oracle}"}</TexBlock>
            <p className="figure-subnote">
              During normal inference <TexInline>{"m=0"}</TexInline>. In oracle diagnostics, supervised
              <TexInline>{"T_m"}</TexInline> and <TexInline>{"\\Delta H_{fus}"}</TexInline> can replace only the
              solver-facing branch while the raw head outputs remain intact for losses and analysis.
            </p>
          </div>
        </div>

        <div className="solver-diag-grid">
          <section className="solver-diag-column">
            <div className="solver-diag-column__title">1. Raw network outputs</div>
            <div className="solver-diag-card">
              <strong><code>fusion_params</code></strong>
              <span><TexInline>{"T_m,\\ \\Delta H_{fus},\\ \\Delta C_p"}</TexInline> directly from <code>FusionHead</code>.</span>
            </div>
            <div className="solver-diag-card">
              <strong><code>nrtl_params</code></strong>
              <span><TexInline>{"\\tau_{12}(T),\\ \\tau_{21}(T),\\ \\alpha"}</TexInline> from the pair embedding plus temperature.</span>
            </div>
            <div className="solver-diag-card">
              <strong>auxiliary outputs</strong>
              <span><code>hansen_sol</code>, <code>hansen_slv</code>, <code>aux_sol</code>, <code>aux_slv</code>, <code>Ra</code>.</span>
            </div>
          </section>

          <section className="solver-diag-column">
            <div className="solver-diag-column__title">2. Values sent into the solver</div>
            <div className="solver-diag-card solver-diag-card--accent">
              <strong><code>fusion_gc_priors</code></strong>
              <span>When crystal GC priors are enabled, the residual branch starts from calibrated <TexInline>{"T_m^{GC}"}</TexInline>.</span>
            </div>
            <div className="solver-diag-arrow">↓</div>
            <div className="solver-diag-card solver-diag-card--accent">
              <strong><code>solver_fusion_params</code></strong>
              <span>Actual crystal parameters entering <code>SLESolver</code> after GC/oracle substitution.</span>
            </div>
            <div className="solver-diag-arrow">↓</div>
            <div className="solver-diag-card solver-diag-card--accent">
              <strong><code>corrected_fusion_params</code></strong>
              <span>Bounded parameter deltas rerun the solver without bypassing physics.</span>
            </div>
          </section>

          <section className="solver-diag-column">
            <div className="solver-diag-column__title">3. Exported intermediates</div>
            <div className="solver-diag-card">
              <strong><code>oracle_injection_masks</code></strong>
              <span>Records which samples actually received train-time oracle substitution.</span>
            </div>
            <div className="solver-diag-card">
              <strong><code>return_intermediates=True</code></strong>
              <span><TexInline>{"\\Phi,\\ \\ln\\gamma_2,\\ \\ln x_{2,physics},\\ \\ln x_{2,final}"}</TexInline> and solver-facing tensors become flat exports.</span>
            </div>
            <div className="solver-diag-card">
              <strong>experiment surface</strong>
              <span><code>run_full_budget_experiment.py</code> writes diagnostics such as <code>tgnn_intermediates.csv</code> for downstream analysis.</span>
            </div>
          </section>
        </div>

        <div className="solver-diag-summary">
          <div className="solver-diag-summary__item">
            <strong>raw path</strong>
            <span><code>fusion_params</code> stay available for supervised auxiliary losses.</span>
          </div>
          <div className="solver-diag-summary__item">
            <strong>solver path</strong>
            <span><code>solver_fusion_params</code> make train-time substitution explicit instead of implicit.</span>
          </div>
          <div className="solver-diag-summary__item">
            <strong>analysis path</strong>
            <span>Intermediates expose whether the bottleneck sits in representation, crystal terms, interaction terms, or correction.</span>
          </div>
        </div>
      </div>
    </FigureCard>
  );
}

function Figure4Solver() {
  const xMin = 0.001;
  const xMax = 0.08;
  const yMin = -4.8;
  const yMax = 0.4;
  const iterations = [0.05, 0.005216, 0.003424, 0.00335296, 0.00335012];
  const [visibleSteps, setVisibleSteps] = useState(4);
  const width = 520;
  const height = 300;
  const left = 58;
  const top = 24;
  const plotWidth = 420;
  const plotHeight = 210;
  const xScale = (value) => left + ((value - xMin) / (xMax - xMin)) * plotWidth;
  const yScale = (value) => top + plotHeight - ((value - yMin) / (yMax - yMin)) * plotHeight;
  const demand = (x) => Math.log(Math.max(x, 0.0008)) + 2.35;
  const supply = (x) => -3.35 + 3.45 * ((1 - Math.exp(-15 * x)) / (1 - Math.exp(-4.5)));
  const curveXs = Array.from({ length: 180 }, (_, index) => xMin + ((xMax - xMin) * index) / 179);
  const demandPath = linePath(curveXs.map((value) => [xScale(value), yScale(demand(value))]));
  const supplyPath = linePath(curveXs.map((value) => [xScale(value), yScale(supply(value))]));
  const cobwebSegments = [];

  for (let index = 0; index < visibleSteps; index += 1) {
    const current = iterations[index];
    const next = iterations[index + 1];
    if (next === undefined) {
      continue;
    }
    const yDemand = demand(current);
    cobwebSegments.push([
      [xScale(current), yScale(yMin)],
      [xScale(current), yScale(yDemand)],
      [xScale(next), yScale(yDemand)],
      [xScale(next), yScale(yMin)],
    ]);
  }

  const convergenceWidth = 360;
  const convergenceHeight = 240;
  const convLeft = 44;
  const convTop = 28;
  const convXScale = (value) => convLeft + (value / 10) * 280;
  const convYScale = (value) => convTop + 170 - ((value - 0) / 0.055) * 170;
  const convPoints = iterations.map((value, index) => [convXScale(index), convYScale(value)]);
  const activeStepFrom = iterations[Math.max(0, visibleSteps - 1)];
  const activeStepTo = iterations[visibleSteps];

  return (
    <FigureCard
      kicker="Figure 4"
      title="SLE Solver"
      subtitle="Successive substitution contracts quickly to the equilibrium solubility root."
      controls={
        <label className="slider-control">
          <span>Show iterations: {visibleSteps}</span>
          <input
            type="range"
            min="1"
            max="4"
            value={visibleSteps}
            onChange={(event) => setVisibleSteps(Number(event.target.value))}
          />
        </label>
      }
      footer={
        <StatStrip
          items={[
            { label: "x₂⁰", value: "0.050" },
            { label: "x₂*", value: "0.00335" },
            { label: "|g'|", value: "≈0.04" },
          ]}
        />
      }
    >
      <div className="solver-grid">
        <div className="solver-panel">
          <div className="solver-panel__title">A. Graphical intersection (zoomed to the active region)</div>
          <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Graphical SLE intersection">
            <defs>
              <clipPath id="solver-clip-a">
                <rect x={left} y={top} width={plotWidth} height={plotHeight} rx="18" />
              </clipPath>
              <marker id="solver-step-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">
                <path d="M 0 0 L 10 5 L 0 10 z" fill={COLORS.orange} />
              </marker>
            </defs>
            <rect x={left} y={top} width={plotWidth} height={plotHeight} fill={PAPER_FILL} rx="18" />
            <line x1={left} y1={top + plotHeight} x2={left + plotWidth} y2={top + plotHeight} stroke={COLORS.line} strokeWidth="2" />
            <line x1={left} y1={top} x2={left} y2={top + plotHeight} stroke={COLORS.line} strokeWidth="2" />
            {[0.002, 0.01, 0.02, 0.04, 0.06, 0.08].map((tick) => (
              <g key={tick}>
                <line
                  x1={xScale(tick)}
                  y1={top + plotHeight}
                  x2={xScale(tick)}
                  y2={top + plotHeight + 6}
                  stroke={COLORS.line}
                />
                <text x={xScale(tick)} y={top + plotHeight + 22} textAnchor="middle" fontSize="13" fill={PAPER_SOFT_TEXT}>
                  {tick < 0.01 ? tick.toFixed(3) : tick.toFixed(2)}
                </text>
              </g>
            ))}
            {[-4, -3, -2, -1, 0].map((tick) => (
              <g key={tick}>
                <line x1={left - 6} y1={yScale(tick)} x2={left} y2={yScale(tick)} stroke={COLORS.line} />
                <text x={left - 12} y={yScale(tick) + 4} textAnchor="end" fontSize="13" fill={PAPER_SOFT_TEXT}>
                  {tick}
                </text>
              </g>
            ))}
            <g clipPath="url(#solver-clip-a)">
              <path d={demandPath} fill="none" stroke={COLORS.blue} strokeWidth="4" />
              <path d={supplyPath} fill="none" stroke={COLORS.red} strokeWidth="4" />
              {cobwebSegments.map((segment, index) => (
                <path
                  key={`segment-${index}`}
                  d={linePath(segment)}
                  fill="none"
                  stroke={COLORS.orange}
                  strokeWidth={index === visibleSteps - 1 ? 3.1 : 2.1}
                  strokeDasharray="8 7"
                  strokeOpacity={index === visibleSteps - 1 ? 1 : 0.28}
                  markerEnd={index === visibleSteps - 1 ? "url(#solver-step-arrow)" : undefined}
                />
              ))}
            </g>
            <circle cx={xScale(0.00335)} cy={yScale(demand(0.00335))} r="7" fill={COLORS.green} />
            <text x={left + plotWidth / 2} y={height - 10} textAnchor="middle" fontSize="14" fill={PAPER_SOFT_TEXT}>
              x₂
            </text>
            <text
              x="16"
              y={top + plotHeight / 2}
              transform={`rotate(-90 16 ${top + plotHeight / 2})`}
              fontSize="14"
              fill={PAPER_SOFT_TEXT}
              textAnchor="middle"
            >
              y
            </text>
          </svg>
          <div className="solver-panel__notes">
            <div><span className="solver-note-line" style={{ "--line-color": COLORS.blue }} />Crystal demand: <TexInline>{"\\ln x_2 + \\Phi"}</TexInline></div>
            <div><span className="solver-note-line" style={{ "--line-color": COLORS.red }} />Solvent supply: <TexInline>{"-\\ln\\gamma_2"}</TexInline></div>
            <div><span className="solver-note-line" style={{ "--line-color": COLORS.orange }} />Current step: {activeStepFrom.toFixed(5)} → {activeStepTo.toFixed(5)}</div>
            <div><span className="solver-note-dot" />Intersection: <TexInline>{"x_2^*"}</TexInline></div>
            <div>View is intentionally zoomed to <TexInline>{"10^{-3} \\le x_2 \\le 8\\cdot10^{-2}"}</TexInline>, where all practical solver motion happens.</div>
          </div>
        </div>

        <div className="solver-panel">
          <div className="solver-panel__title">B. Convergence trace</div>
          <svg viewBox={`0 0 ${convergenceWidth} ${convergenceHeight}`} role="img" aria-label="SLE solver convergence">
            <rect x={convLeft} y={convTop} width="280" height="170" fill={PAPER_FILL} rx="18" />
            <line x1={convLeft} y1={convTop + 170} x2={convLeft + 280} y2={convTop + 170} stroke={COLORS.line} strokeWidth="2" />
            <line x1={convLeft} y1={convTop} x2={convLeft} y2={convTop + 170} stroke={COLORS.line} strokeWidth="2" />
            <line
              x1={convLeft}
              y1={convYScale(0.00335)}
              x2={convLeft + 280}
              y2={convYScale(0.00335)}
              stroke={COLORS.green}
              strokeWidth="2"
              strokeDasharray="6 6"
            />
            <path d={linePath(convPoints)} fill="none" stroke={COLORS.blue} strokeWidth="4" />
            {convPoints.map(([x, y], index) => (
              <circle
                key={`conv-${index}`}
                cx={x}
                cy={y}
                r={index <= visibleSteps ? 5 : 3.5}
                fill={index <= visibleSteps ? COLORS.orange : COLORS.line}
              />
            ))}
            <text x={convLeft + 140} y={convergenceHeight - 16} textAnchor="middle" fontSize="14" fill={PAPER_SOFT_TEXT}>
              iteration k
            </text>
            <text
              x="16"
              y={convTop + 85}
              transform={`rotate(-90 16 ${convTop + 85})`}
              fontSize="14"
              fill={PAPER_SOFT_TEXT}
              textAnchor="middle"
            >
              x₂⁽ᵏ⁾
            </text>
          </svg>
          <div className="solver-panel__notes">
            <div><strong>x₂⁰</strong> = 0.050</div>
            <div><strong>x₂*</strong> = 0.00335</div>
            <div>Convergence in 4 iterations</div>
            <div><TexInline>{"|g'| \\approx 0.04"}</TexInline> so the map is a strong contraction.</div>
          </div>
        </div>
      </div>
    </FigureCard>
  );
}

function Figure5Backprop() {
  return (
    <FigureCard
      kicker="Figure 5"
      title="Implicit Differentiation vs Unrolled Backprop"
      subtitle="Backward through the fixed point avoids O(N) memory and unstable chain products."
    >
      <div className="compare-grid compare-grid--rebuilt">
        <section className="compare-lane compare-lane--warn">
          <div className="compare-lane__title">A. Unrolled solver graph</div>
          <div className="compare-stack">
            {["\\theta", "x_2^{(0)}", "\\mathrm{NRTL}", "x_2^{(1)}", "\\mathrm{NRTL}", "x_2^{(2)}", "\\cdots", "x_2^{(N)}", "\\mathcal{L}"].map((item, index) => (
              <React.Fragment key={`${item}-${index}`}>
                <div className="compare-node"><TexInline>{item}</TexInline></div>
                {index < 8 ? <div className="compare-arrow compare-arrow--warn">↓</div> : null}
              </React.Fragment>
            ))}
          </div>
          <div className="compare-backward-box compare-backward-box--warn">
            <strong>Backward path</strong>
            <TexBlock>{"\\prod_k g'(x_2^{(k)})"}</TexBlock>
            <p className="figure-subnote">Stores every iterate and risks vanishing or exploding sensitivity.</p>
          </div>
        </section>

        <section className="compare-lane compare-lane--success">
          <div className="compare-lane__title">B. Implicit fixed-point backward</div>
          <div className="compare-implicit-card">
            <div className="compare-node"><TexInline>{"\\theta"}</TexInline></div>
            <div className="compare-arrow compare-arrow--success">→</div>
            <div className="compare-node compare-node--wide">Forward: iterate to <TexInline>{"x_2^*"}</TexInline></div>
            <div className="compare-arrow compare-arrow--success">→</div>
            <div className="compare-node"><TexInline>{"\\mathcal{L}"}</TexInline></div>
          </div>
          <div className="compare-backward-box">
            <strong>Single backward step</strong>
            <TexBlock>{"\\frac{d x_2^*}{d\\theta} = -\\frac{\\partial F/\\partial \\theta}{\\partial F/\\partial x_2^*}"}</TexBlock>
            <p className="figure-subnote">Exact at the converged fixed point and O(1) in memory.</p>
          </div>
        </section>
      </div>

      <table className="comparison-table comparison-table--tight">
        <thead>
          <tr>
            <th>Method</th>
            <th>Memory</th>
            <th>Accuracy</th>
            <th>Stability</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Unrolled</td>
            <td>O(N·B)</td>
            <td>~(1-|g'|ᴺ)</td>
            <td>|g'|ᴺ risk</td>
          </tr>
          <tr>
            <td>Implicit</td>
            <td>O(B)</td>
            <td>~100%</td>
            <td>Stable + clamp</td>
          </tr>
        </tbody>
      </table>
    </FigureCard>
  );
}

function buildStackedAreas(rows, seriesKeys) {
  const width = 420;
  const height = 240;
  const left = 50;
  const top = 18;
  const plotWidth = 320;
  const plotHeight = 170;
  const xScale = (epoch) => left + (epoch / 10) * plotWidth;
  const yScale = (value) => top + plotHeight - (value / 100) * plotHeight;
  let baseline = rows.map(() => 0);

  const layers = seriesKeys.map((key) => {
    const topPoints = rows.map((row, index) => [xScale(row.epoch), yScale(baseline[index] + row[key])]);
    const bottomPoints = rows.map((row, index) => [xScale(row.epoch), yScale(baseline[index])]);
    baseline = baseline.map((value, index) => value + rows[index][key]);
    return { key, path: areaPath(topPoints, bottomPoints) };
  });

  return { layers, width, height, left, top, plotWidth, plotHeight, xScale, yScale };
}

function StackedAreaChart({ title, rows, colors, activeKey, annotation }) {
  const keys = Object.keys(colors);
  const chart = buildStackedAreas(rows, keys);

  return (
    <div className="loss-chart">
      <div className="loss-chart__title">{title}</div>
      <svg viewBox={`0 0 ${chart.width} ${chart.height}`} role="img" aria-label={title}>
        <rect x={chart.left} y={chart.top} width={chart.plotWidth} height={chart.plotHeight} fill={PAPER_FILL} rx="18" />
        <line
          x1={chart.left}
          y1={chart.top + chart.plotHeight}
          x2={chart.left + chart.plotWidth}
          y2={chart.top + chart.plotHeight}
          stroke={COLORS.line}
          strokeWidth="2"
        />
        <line x1={chart.left} y1={chart.top} x2={chart.left} y2={chart.top + chart.plotHeight} stroke={COLORS.line} strokeWidth="2" />
        {[0, 50, 100].map((tick) => (
          <g key={tick}>
            <line x1={chart.left - 6} y1={chart.yScale(tick)} x2={chart.left} y2={chart.yScale(tick)} stroke={COLORS.line} />
            <text x={chart.left - 12} y={chart.yScale(tick) + 4} textAnchor="end" fontSize="12" fill={PAPER_SOFT_TEXT}>
              {tick}%
            </text>
          </g>
        ))}
        {chart.layers.map((layer) => (
          <path
            key={layer.key}
            d={layer.path}
            fill={colors[layer.key]}
            opacity={activeKey === layer.key || activeKey === "all" ? 0.88 : 0.22}
          />
        ))}
        <text x={chart.left + chart.plotWidth / 2} y={chart.height - 10} textAnchor="middle" fontSize="13" fill={PAPER_SOFT_TEXT}>
          Phase 2 epoch
        </text>
        <text
          x="18"
          y={chart.top + chart.plotHeight / 2}
          transform={`rotate(-90 18 ${chart.top + chart.plotHeight / 2})`}
          fontSize="13"
          fill={PAPER_SOFT_TEXT}
          textAnchor="middle"
        >
          share of total loss
        </text>
      </svg>
      <p className="figure-subnote">{annotation}</p>
    </div>
  );
}

function Figure6LossLandscape() {
  const [activeKey, setActiveKey] = useState("sol");
  const beforeRows = [
    { epoch: 0, sol: 35, vant: 40, tm: 10, dh: 7, bridge: 5, tau: 3 },
    { epoch: 2, sol: 18, vant: 63, tm: 7, dh: 5, bridge: 4, tau: 3 },
    { epoch: 4, sol: 9, vant: 80, tm: 5, dh: 3, bridge: 2, tau: 1 },
    { epoch: 6, sol: 4, vant: 91, tm: 2, dh: 1.5, bridge: 1, tau: 0.5 },
    { epoch: 8, sol: 1.5, vant: 97, tm: 0.7, dh: 0.4, bridge: 0.3, tau: 0.1 },
    { epoch: 10, sol: 0.8, vant: 99, tm: 0.1, dh: 0.05, bridge: 0.03, tau: 0.02 },
  ];
  const afterRows = [
    { epoch: 0, sol: 72, vant: 6, tm: 9, dh: 6, bridge: 4, tau: 3 },
    { epoch: 2, sol: 84, vant: 2.5, tm: 5, dh: 4, bridge: 2.5, tau: 2 },
    { epoch: 4, sol: 88, vant: 1.2, tm: 4, dh: 3, bridge: 2.5, tau: 1.3 },
    { epoch: 6, sol: 91, vant: 0.8, tm: 3, dh: 2.5, bridge: 1.7, tau: 1 },
    { epoch: 8, sol: 92, vant: 0.5, tm: 3, dh: 2, bridge: 1.6, tau: 0.9 },
    { epoch: 10, sol: 93, vant: 0.3, tm: 2.7, dh: 1.8, bridge: 1.4, tau: 0.8 },
  ];
  const lossColors = {
    sol: COLORS.blue,
    vant: COLORS.red,
    tm: COLORS.purple,
    dh: COLORS.orange,
    bridge: COLORS.green,
    tau: COLORS.yellow,
  };

  return (
    <FigureCard
      kicker="Figure 6"
      title="Loss Landscape"
      subtitle="Balancing 12 losses only works if solubility keeps the dominant fraction in Phase 2."
      controls={
        <ToggleGroup
          label="Loss highlight"
          options={[
            { label: "sol", value: "sol" },
            { label: "vant_hoff", value: "vant" },
            { label: "all", value: "all" },
          ]}
          value={activeKey}
          onChange={setActiveKey}
        />
      }
      footer={
        <FigureLegend
          items={[
            { label: "sol", color: COLORS.blue },
            { label: "vant_hoff_local", color: COLORS.red },
            { label: "T_m", color: COLORS.purple },
            { label: "dH_fus", color: COLORS.orange },
            { label: "bridge", color: COLORS.green },
            { label: "tau_reg", color: COLORS.yellow },
          ]}
        />
      }
    >
      <div className="loss-grid">
        <StackedAreaChart
          title="A. Before fix"
          rows={beforeRows}
          colors={lossColors}
          activeKey={activeKey}
          annotation="sol_fraction < 1% — optimizer ignores solubility"
        />
        <StackedAreaChart
          title="B. After fix"
          rows={afterRows}
          colors={lossColors}
          activeKey={activeKey}
          annotation="sol_fraction > 85% — optimizer focuses on solubility"
        />
      </div>
    </FigureCard>
  );
}

function Figure7LinearProbe() {
  const { linear_probe: probeData } = usePresentationData();
  const descriptorNotes = {
    FractionCSP3: "Strongly encoded shape and saturation cue.",
    NumHDonors: "Hydrogen-bond donation is partially preserved.",
    TPSA: "Polarity survives, but not cleanly enough for descriptor parity.",
    NumHAcceptors: "Acceptors are learned better than mass-like scalars.",
    MolLogP: "Lipophilicity remains recoverable but not saturated.",
    NumRotatableBonds: "Flexibility is present, though blurred.",
    RingCount: "Ring topology is partially linearly accessible.",
    MolWt: "Mass statistics are unexpectedly lossy for the encoder.",
    HeavyAtomCount: "A simple count should be easy, but the bottleneck discards detail.",
    MolMR: "Polarizability-related structure is among the weaker recovered channels.",
  };
  const descriptors = (probeData.descriptors ?? []).map((descriptor) => ({
    ...descriptor,
    note: descriptorNotes[descriptor.name] ?? "Recovered automatically from the latest descriptor-probe artifact.",
  }));
  const [selectedIndex, setSelectedIndex] = useState(0);
  const selectedDescriptor = descriptors[Math.min(selectedIndex, Math.max(0, descriptors.length - 1))] ?? descriptors[0];
  const donutCircumference = 2 * Math.PI * 54;
  const donutSegments = [
    {
      label: "R² ≥ 0.8",
      fraction: (probeData.counts?.ge_0_8 ?? 3) / (probeData.total_descriptors ?? 208),
      color: COLORS.green,
    },
    {
      label: "0.5–0.8",
      fraction: (probeData.counts?.between_0_5_and_0_8 ?? 104) / (probeData.total_descriptors ?? 208),
      color: COLORS.yellow,
    },
    {
      label: "R² < 0.5",
      fraction: (probeData.counts?.lt_0_5 ?? 101) / (probeData.total_descriptors ?? 208),
      color: COLORS.red,
    },
  ];

  return (
    <FigureCard
      kicker="Figure 7"
      title="Linear Probe"
      subtitle="The encoder only retains about half of the descriptor information that a direct descriptor model sees."
      footer={
        <div className="figure-footer-note">
          RF sees all descriptors at <strong>R² = 1.0</strong>, leaving a measured encoder gap of <strong>0.68 MAE</strong>.
        </div>
      }
    >
      <div className="probe-grid">
        <div className="probe-bars" role="img" aria-label="Descriptor recovery bar chart">
          <div className="probe-bars__median">median R² = {probeData.median_r2_label ?? "0.505"}</div>
          {descriptors.map((descriptor, index) => {
            const barColor =
              descriptor.value >= 0.8 ? COLORS.green : descriptor.value >= 0.5 ? COLORS.yellow : COLORS.red;
            return (
              <button
                type="button"
                key={descriptor.name}
                className={`probe-row${selectedIndex === index ? " is-active" : ""}`}
                onClick={() => setSelectedIndex(index)}
              >
                <span className="probe-row__label">{descriptor.name}</span>
                <span className="probe-row__track">
                  <span className="probe-row__fill" style={{ width: `${descriptor.value * 100}%`, background: barColor }} />
                  <span className="probe-row__midline" />
                </span>
                <span className="probe-row__value">{descriptor.value.toFixed(2)}</span>
              </button>
            );
          })}
        </div>

        <div className="probe-sidepanel">
          <div className="probe-detail">
            <div className="probe-detail__eyebrow">Selected descriptor</div>
            <h3>{selectedDescriptor?.name ?? "Descriptor"}</h3>
            <p>
              <strong>R² = {selectedDescriptor?.value?.toFixed(2) ?? "—"}</strong>. {selectedDescriptor?.note ?? ""}
            </p>
            <p className="figure-subnote">
              Green means well learned, yellow means partial retention, and red signals a real encoder bottleneck.
            </p>
          </div>

          <div className="probe-donut">
            <svg viewBox="0 0 180 180" role="img" aria-label="Descriptor recovery donut">
              <circle cx="90" cy="90" r="54" fill="none" stroke={PAPER_BORDER} strokeWidth="22" />
              {donutSegments.map((segment, index) => {
                const previousFraction = donutSegments
                  .slice(0, index)
                  .reduce((sum, item) => sum + item.fraction, 0);
                return (
                  <circle
                    key={segment.label}
                    cx="90"
                    cy="90"
                    r="54"
                    fill="none"
                    stroke={segment.color}
                    strokeWidth="22"
                    strokeDasharray={`${segment.fraction * donutCircumference} ${donutCircumference}`}
                    strokeDashoffset={-previousFraction * donutCircumference}
                    transform="rotate(-90 90 90)"
                  />
                );
              })}
              <text x="90" y="82" textAnchor="middle" fontSize="24" fontWeight="800" fill={PAPER_TEXT}>
                {Math.round((probeData.counts?.between_0_5_and_0_8 ?? 104) / (probeData.total_descriptors ?? 208) * 100)}%
              </text>
              <text x="90" y="104" textAnchor="middle" fontSize="10" fill={PAPER_SOFT_TEXT}>
                captured
              </text>
              <text x="90" y="118" textAnchor="middle" fontSize="10" fill={PAPER_SOFT_TEXT}>
                descriptor info
              </text>
            </svg>
            <div className="probe-donut__legend">
              <div>{probeData.counts?.ge_0_8 ?? 3} / {probeData.total_descriptors ?? 208} well learned</div>
              <div>{probeData.counts?.between_0_5_and_0_8 ?? 104} / {probeData.total_descriptors ?? 208} partial</div>
              <div>{probeData.counts?.lt_0_5 ?? 101} / {probeData.total_descriptors ?? 208} poor</div>
            </div>
          </div>
        </div>
      </div>
    </FigureCard>
  );
}

function Figure8Waterfall() {
  return (
    <FigureCard
      kicker="Figure 8"
      title="Error Decomposition"
      subtitle="Most of the gap to the best descriptor model is upstream of the physics bottleneck."
    >
      <div className="waterfall-grid">
        <div className="waterfall-card">
          <div className="waterfall-card__title">Current path</div>
          <div className="waterfall-steps">
            <div className="waterfall-step waterfall-step--base">
              <strong>RF (descriptors)</strong>
              <span>1.20 MAE</span>
            </div>
            <div className="waterfall-step waterfall-step--delta">
              <strong>+ GNN encoder gap</strong>
              <span>+0.68</span>
              <small>93% of total gap</small>
            </div>
            <div className="waterfall-step waterfall-step--minor">
              <strong>+ Physics bottleneck</strong>
              <span>+0.05</span>
              <small>7% of total gap</small>
            </div>
          </div>
          <div className="waterfall-totals">
            <div><strong>1.88</strong><span>DirectGNN</span></div>
            <div><strong>1.93</strong><span>TGNN (current)</span></div>
          </div>
        </div>

        <div className="waterfall-card waterfall-card--expected">
          <div className="waterfall-card__title">Expected with descriptor augmentation</div>
          <div className="waterfall-steps waterfall-steps--expected">
            <div className="waterfall-step waterfall-step--base">
              <strong>RF (descriptors)</strong>
              <span>1.20 MAE</span>
            </div>
            <div className="waterfall-step waterfall-step--target">
              <strong>TGNN + descriptors</strong>
              <span>1.15–1.35</span>
              <small>Physics can help after the encoder gap closes.</small>
            </div>
          </div>
        </div>
      </div>
    </FigureCard>
  );
}

function chartPathFromTemps(temps, fn, xScale, yScale) {
  return linePath(temps.map((temp) => [xScale(temp), yScale(fn(temp))]));
}

function Figure9TemperatureExtrapolation() {
  const trainTemps = [280, 300, 320, 340];
  const testTemps = [350, 360, 380];
  const allTemps = Array.from({ length: 90 }, (_, index) => 250 + (150 * index) / 89);
  const trueCurve = (temp) => -2600 / temp + 5.2;
  const rfCurve = (temp) => {
    if (temp <= 340) {
      return trueCurve(temp) + 0.08 * Math.sin((temp - 280) / 22);
    }
    return trueCurve(340) - 0.02;
  };
  const tgnnCurve = (temp) => trueCurve(temp) + 0.03 * Math.sin((temp - 260) / 50);
  const width = 420;
  const height = 270;
  const left = 52;
  const top = 20;
  const plotWidth = 320;
  const plotHeight = 190;
  const xScale = (temp) => left + ((temp - 250) / 150) * plotWidth;
  const yScale = (value) => top + plotHeight - ((value + 10) / 10) * plotHeight;

  function Panel({ title, subtitle, prediction, color }) {
    return (
      <div className="temperature-panel">
        <div className="temperature-panel__title">{title}</div>
        <p className="figure-subnote">{subtitle}</p>
        <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title}>
          <rect x={left} y={top} width={plotWidth} height={plotHeight} fill={PAPER_FILL} rx="18" />
          <rect x={xScale(280)} y={top} width={xScale(340) - xScale(280)} height={plotHeight} fill="rgba(148, 163, 184, 0.10)" />
          <line x1={left} y1={top + plotHeight} x2={left + plotWidth} y2={top + plotHeight} stroke={COLORS.line} strokeWidth="2" />
          <line x1={left} y1={top} x2={left} y2={top + plotHeight} stroke={COLORS.line} strokeWidth="2" />
          <path d={chartPathFromTemps(allTemps, trueCurve, xScale, yScale)} fill="none" stroke={PAPER_TEXT} strokeDasharray="7 7" strokeWidth="2.5" />
          <path d={chartPathFromTemps(allTemps, prediction, xScale, yScale)} fill="none" stroke={color} strokeWidth="4" />
          {trainTemps.map((temp) => (
            <circle key={`train-${temp}`} cx={xScale(temp)} cy={yScale(trueCurve(temp))} r="5.2" fill={COLORS.blue} />
          ))}
          {testTemps.map((temp) => (
            <circle key={`test-${temp}`} cx={xScale(temp)} cy={yScale(trueCurve(temp))} r="5.2" fill={COLORS.red} />
          ))}
          <text x={left + 8} y={top + 18} fill={COLORS.gray} fontSize="12">
            train range
          </text>
          <text x={left + plotWidth / 2} y={height - 10} textAnchor="middle" fontSize="14" fill={PAPER_SOFT_TEXT}>
            Temperature T (K)
          </text>
          <text
            x="16"
            y={top + plotHeight / 2}
            transform={`rotate(-90 16 ${top + plotHeight / 2})`}
            fontSize="14"
            fill={PAPER_SOFT_TEXT}
            textAnchor="middle"
          >
            ln x₂
          </text>
        </svg>
      </div>
    );
  }

  return (
    <FigureCard
      kicker="Figure 9"
      title="Temperature Extrapolation"
      subtitle="Schematic: tree models flatten outside seen temperatures; the physics-guided path preserves a van't Hoff-like trend."
      footer={<div className="figure-footer-note">Schematic. Quantitative results pending.</div>}
    >
      <div className="temperature-grid">
        <Panel title="A. RF: no temperature physics" subtitle="Flat extrapolation beyond 340 K" prediction={rfCurve} color={COLORS.gray} />
        <Panel
          title="B. TGNN: SLE-guided extrapolation"
          subtitle="d(ln x₂)/dT = ΔH_sol / (RT²) is baked into the solver"
          prediction={tgnnCurve}
          color={COLORS.blue}
        />
      </div>
    </FigureCard>
  );
}

const curriculumRows = [
  {
    label: "GNN Encoder",
    segments: [{ from: 0, to: 300, type: "train", text: "train" }],
  },
  {
    label: "Crystal Heads",
    segments: [
      { from: 0, to: 50, type: "train", text: "train" },
      { from: 50, to: 250, type: "low", text: "low lr" },
      { from: 250, to: 300, type: "train", text: "unfreeze" },
    ],
  },
  {
    label: "NRTL Head",
    segments: [
      { from: 0, to: 50, type: "off", text: "off" },
      { from: 50, to: 300, type: "train", text: "train" },
    ],
  },
  {
    label: "SLE Solver",
    segments: [
      { from: 0, to: 50, type: "off", text: "off" },
      { from: 50, to: 300, type: "train", text: "active" },
    ],
  },
  {
    label: "Correction",
    segments: [
      { from: 0, to: 70, type: "off", text: "off" },
      { from: 70, to: 300, type: "train", text: "train" },
    ],
  },
  {
    label: "L_sol",
    segments: [
      { from: 0, to: 50, type: "off", text: "0" },
      { from: 50, to: 300, type: "train", text: "dominant" },
    ],
  },
  {
    label: "L_aux (T_m, ΔH)",
    segments: [
      { from: 0, to: 50, type: "train", text: "dominant" },
      { from: 50, to: 300, type: "low", text: "light" },
    ],
  },
  {
    label: "Oracle Injection",
    segments: [
      { from: 0, to: 50, type: "off", text: "off" },
      { from: 50, to: 200, type: "train", text: "active" },
      { from: 200, to: 250, type: "low", text: "anneal" },
      { from: 250, to: 300, type: "off", text: "off" },
    ],
  },
];

function statusAtEpoch(segments, epoch) {
  return segments.find((segment) => epoch >= segment.from && epoch < segment.to) ?? segments[segments.length - 1];
}

function Figure10Curriculum() {
  const [epoch, setEpoch] = useState(92);
  const phaseLabel = epoch < 50 ? "Phase 1" : epoch < 250 ? "Phase 2" : "Phase 3";
  const milestones = [
    { epoch: 50, label: "SLE activated, L_sol starts" },
    { epoch: 70, label: "Correction unfreezes" },
    { epoch: 200, label: "Oracle annealing" },
  ];

  return (
    <FigureCard
      kicker="Figure 10"
      title="Three-Phase Curriculum"
      subtitle="The training schedule gates physics and correction capacity in stages instead of turning everything on at once."
      controls={
        <label className="slider-control">
          <span>Epoch marker: {epoch}</span>
          <input type="range" min="0" max="299" value={epoch} onChange={(event) => setEpoch(Number(event.target.value))} />
        </label>
      }
      footer={<div className="figure-footer-note">Current marker is in <strong>{phaseLabel}</strong>.</div>}
    >
      <div className="curriculum-grid">
        <div className="curriculum-chart">
          <div className="curriculum-phases">
            <div className="curriculum-phase curriculum-phase--one">Phase 1 · 50 epochs</div>
            <div className="curriculum-phase curriculum-phase--two">Phase 2 · 200 epochs</div>
            <div className="curriculum-phase curriculum-phase--three">Phase 3 · 50 epochs</div>
          </div>

          <div className="curriculum-rows">
            {curriculumRows.map((row) => (
              <div className="curriculum-row" key={row.label}>
                <div className="curriculum-row__label">{row.label}</div>
                <div className="curriculum-track">
                  {row.segments.map((segment) => (
                    <div
                      key={`${row.label}-${segment.from}`}
                      className={`curriculum-segment curriculum-segment--${segment.type}`}
                      style={{
                        left: `${(segment.from / 300) * 100}%`,
                        width: `${((segment.to - segment.from) / 300) * 100}%`,
                      }}
                    >
                      {segment.text}
                    </div>
                  ))}
                  <div className="curriculum-marker" style={{ left: `${(epoch / 300) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="curriculum-panel">
          <h3>State at epoch {epoch}</h3>
          <ul className="curriculum-status-list">
            {curriculumRows.map((row) => {
              const state = statusAtEpoch(row.segments, epoch);
              return (
                <li key={`${row.label}-status`}>
                  <strong>{row.label}:</strong> {state.text}
                </li>
              );
            })}
          </ul>
          <FigureLegend
            items={[
              { label: "Active training", color: COLORS.green },
              { label: "Frozen / off", color: COLORS.red },
              { label: "Low LR / anneal", color: COLORS.yellow },
            ]}
          />
          <div className="curriculum-milestone-list">
            {milestones.map((milestone) => (
              <div key={milestone.epoch} className="curriculum-milestone-card">
                <strong>Epoch {milestone.epoch}</strong>
                <span>{milestone.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </FigureCard>
  );
}

function Figure11GCPriors() {
  const examples = [
    { key: "paracetamol", name: "Paracetamol", gc: 460, truth: 442, residual: -18 },
    { key: "aspirin", name: "Aspirin", gc: 430, truth: 409, residual: -21 },
  ];
  const [exampleKey, setExampleKey] = useState("paracetamol");
  const example = examples.find((item) => item.key === exampleKey) ?? examples[0];
  const axisPercent = (value) => `${((value - 100) / 600) * 100}%`;
  const truthStart = example.truth - 18;
  const truthEnd = example.truth + 18;
  const priorStart = example.gc - 50;
  const priorEnd = example.gc + 50;
  const randomInit = Math.min(680, example.truth + 165);
  const axisTicks = [100, 250, 400, 550, 700];

  return (
    <FigureCard
      kicker="Figure 11"
      title="GC Priors"
      subtitle="A bounded residual around a group-contribution estimate collapses the crystal-property search space."
      controls={
        <ToggleGroup
          label="Example molecule"
          options={examples.map((item) => ({ label: item.name, value: item.key }))}
          value={exampleKey}
          onChange={setExampleKey}
        />
      }
    >
      <div className="gc-rebuilt">
        <div className="gc-topbar">
          <div className="gc-badge-large">6× smaller search space</div>
          <div className="gc-formula-card">
            <TexBlock>{"T_m = T_m^{GC} + \\delta,\\qquad |\\delta| \\le 50\\,K"}</TexBlock>
            <p className="figure-subnote">The model learns a bounded residual around a calibrated group-contribution estimate instead of searching the full crystal-property range.</p>
          </div>
        </div>

        <div className="gc-range-grid">
          <div className="gc-range-card">
            <div className="gc-panel__title">A. Without GC prior</div>
            <div className="gc-axis-card">
              <div className="gc-axis">
                <div className="gc-axis__track" />
                <div className="gc-axis__band gc-axis__band--search" style={{ left: axisPercent(100), width: "100%" }} />
                <div
                  className="gc-axis__band gc-axis__band--truth"
                  style={{ left: axisPercent(truthStart), width: `calc(${axisPercent(truthEnd)} - ${axisPercent(truthStart)})` }}
                />
                <div className="gc-axis__pin gc-axis__pin--random" style={{ left: axisPercent(randomInit) }} />
                {axisTicks.map((tick) => (
                  <span key={`without-${tick}`} className="gc-axis__tick" style={{ left: axisPercent(tick) }}>
                    {tick}
                  </span>
                ))}
              </div>
              <div className="gc-axis__legend">
                <div><span className="gc-swatch gc-swatch--search" /> search window: 100–700 K</div>
                <div><span className="gc-swatch gc-swatch--truth" /> true melting-point neighborhood</div>
                <div><span className="gc-swatch gc-swatch--random" /> random initialization</div>
              </div>
            </div>
            <div className="gc-note-list">
              <div>The fusion head has to search a 600 K interval before it learns anything useful.</div>
              <div>Sparse crystal supervision means early updates can point in the wrong direction.</div>
              <div>A poor starting point propagates directly into the SLE solver.</div>
            </div>
          </div>

          <div className="gc-range-card">
            <div className="gc-panel__title">B. With GC prior</div>
            <div className="gc-axis-card">
              <div className="gc-axis">
                <div className="gc-axis__track" />
                <div
                  className="gc-axis__band gc-axis__band--prior"
                  style={{ left: axisPercent(priorStart), width: `calc(${axisPercent(priorEnd)} - ${axisPercent(priorStart)})` }}
                />
                <div
                  className="gc-axis__band gc-axis__band--truth"
                  style={{ left: axisPercent(truthStart), width: `calc(${axisPercent(truthEnd)} - ${axisPercent(truthStart)})` }}
                />
                <div className="gc-axis__pin gc-axis__pin--prior" style={{ left: axisPercent(example.gc) }} />
                <div className="gc-axis__pin gc-axis__pin--target" style={{ left: axisPercent(example.truth) }} />
                {axisTicks.map((tick) => (
                  <span key={`with-${tick}`} className="gc-axis__tick" style={{ left: axisPercent(tick) }}>
                    {tick}
                  </span>
                ))}
              </div>
              <div className="gc-axis__legend">
                <div><span className="gc-swatch gc-swatch--prior" /> GC prior window: {priorStart}–{priorEnd} K</div>
                <div><span className="gc-swatch gc-swatch--truth" /> true melting-point neighborhood</div>
                <div><span className="gc-swatch gc-swatch--target" /> bounded residual only needs {example.residual} K</div>
              </div>
            </div>
            <div className="gc-note-list">
              <div>The model starts near a chemically plausible melting point.</div>
              <div>Training only has to learn a small correction, not rediscover the whole scale.</div>
              <div>The solver receives stable crystal parameters much earlier in training.</div>
            </div>
          </div>
        </div>

        <div className="gc-example-flow">
          <div className="gc-example-step">
            <strong>Joback prior</strong>
            <span>{example.gc} K</span>
          </div>
          <div className="gc-example-arrow">→</div>
          <div className="gc-example-step">
            <strong>Needed residual</strong>
            <span>{example.residual} K</span>
          </div>
          <div className="gc-example-arrow">→</div>
          <div className="gc-example-step">
            <strong>True target</strong>
            <span>{example.truth} K</span>
          </div>
        </div>
      </div>

      <div className="gc-example-card gc-example-card--rebuilt">
        <strong>{example.name}</strong>
        <span>T_m^GC = {example.gc} K</span>
        <span>T_m^true = {example.truth} K</span>
        <span>Residual needed: {example.residual} K ✓ (within ±50 K)</span>
      </div>
    </FigureCard>
  );
}

const overfitEpochs = Array.from({ length: 11 }, (_, index) => index);
const overfitTrain = [0.75, 0.58, 0.45, 0.35, 0.28, 0.24, 0.23, 0.22, 0.215, 0.212, 0.21];
const overfitVal = [1.97, 1.95, 1.94, 1.935, 1.93, 1.929, 1.932, 1.94, 1.948, 1.955, 1.96];
const overfitTau = [0.56, 0.8, 1.1, 1.4, 1.8, 2.1, 2.28, 2.4, 2.52, 2.58, 2.64];
const overfitSol = [0.926, 0.92, 0.905, 0.89, 0.872, 0.86, 0.848, 0.838, 0.832, 0.827, 0.821];

function MiniLineChart({
  title,
  values,
  secondaryValues,
  yDomain,
  markerEpoch,
  highlightValue,
  accent,
  secondaryAccent,
  note,
}) {
  const width = 360;
  const height = 180;
  const left = 42;
  const top = 16;
  const plotWidth = 280;
  const plotHeight = 120;
  const xScale = (epoch) => left + (epoch / 10) * plotWidth;
  const yScale = (value) => top + plotHeight - ((value - yDomain[0]) / (yDomain[1] - yDomain[0])) * plotHeight;
  const path = linePath(overfitEpochs.map((epoch, index) => [xScale(epoch), yScale(values[index])]));
  const secondaryPath = secondaryValues
    ? linePath(overfitEpochs.map((epoch, index) => [xScale(epoch), yScale(secondaryValues[index])]))
    : null;

  return (
    <div className="mini-chart">
      <div className="mini-chart__title">{title}</div>
      <p className="figure-subnote">{note}</p>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title}>
        <rect x={left} y={top} width={plotWidth} height={plotHeight} fill={PAPER_FILL} rx="18" />
        <rect x={xScale(5)} y={top} width={xScale(10) - xScale(5)} height={plotHeight} fill="rgba(148, 163, 184, 0.10)" />
        <line x1={left} y1={top + plotHeight} x2={left + plotWidth} y2={top + plotHeight} stroke={COLORS.line} strokeWidth="2" />
        <line x1={left} y1={top} x2={left} y2={top + plotHeight} stroke={COLORS.line} strokeWidth="2" />
        <line x1={xScale(5)} y1={top} x2={xScale(5)} y2={top + plotHeight} stroke={COLORS.green} strokeWidth="2" />
        <line
          x1={xScale(markerEpoch)}
          y1={top}
          x2={xScale(markerEpoch)}
          y2={top + plotHeight}
          stroke={COLORS.orange}
          strokeWidth="2"
          strokeDasharray="5 5"
        />
        {highlightValue !== undefined ? (
          <line
            x1={left}
            y1={yScale(highlightValue)}
            x2={left + plotWidth}
            y2={yScale(highlightValue)}
            stroke={COLORS.gray}
            strokeDasharray="6 6"
            strokeWidth="2"
          />
        ) : null}
        {secondaryPath ? <path d={secondaryPath} fill="none" stroke={secondaryAccent} strokeWidth="4" /> : null}
        <path d={path} fill="none" stroke={accent} strokeWidth="4" />
        <circle cx={xScale(markerEpoch)} cy={yScale(values[markerEpoch])} r="5" fill={COLORS.orange} />
        {secondaryValues ? (
          <circle cx={xScale(markerEpoch)} cy={yScale(secondaryValues[markerEpoch])} r="5" fill={secondaryAccent} />
        ) : null}
      </svg>
      {secondaryValues ? (
        <div className="mini-chart__legend">
          <span style={{ color: accent }}>Train</span>
          <span style={{ color: secondaryAccent }}>Val</span>
        </div>
      ) : null}
    </div>
  );
}

function Figure12Overfitting() {
  const [markerEpoch, setMarkerEpoch] = useState(5);

  return (
    <FigureCard
      kicker="Figure 12"
      title="Overfitting Diagnostics"
      subtitle="Validation stops improving almost immediately while physics parameters continue drifting to extremes."
      controls={
        <label className="slider-control">
          <span>Inspect epoch: {markerEpoch}</span>
          <input type="range" min="0" max="10" value={markerEpoch} onChange={(event) => setMarkerEpoch(Number(event.target.value))} />
        </label>
      }
      footer={
        <div className="figure-footer-note">
          Best validation epoch is <strong>5</strong> with <strong>MAE = 1.929</strong>.
        </div>
      }
    >
      <div className="overfit-grid">
        <MiniLineChart
          title="A. Train vs Val MAE"
          values={overfitTrain}
          secondaryValues={overfitVal}
          yDomain={[0.15, 2.05]}
          markerEpoch={markerEpoch}
          accent={COLORS.blue}
          secondaryAccent={COLORS.red}
          note="Train keeps falling; validation bottoms out at epoch 5."
        />
        <MiniLineChart
          title="B. tau_reg_raw"
          values={overfitTau}
          yDomain={[0, 3]}
          markerEpoch={markerEpoch}
          highlightValue={3}
          accent={COLORS.orange}
          note="NRTL params become extreme."
        />
        <MiniLineChart
          title="C. sol_fraction"
          values={overfitSol}
          yDomain={[0.75, 1.0]}
          markerEpoch={markerEpoch}
          highlightValue={0.5}
          accent={COLORS.blue}
          note="Still above the minimum, but trending down."
        />
      </div>

      <div className="overfit-summary">
        <div>Train sol_raw: {overfitTrain[markerEpoch].toFixed(3)}</div>
        <div>Val MAE: {overfitVal[markerEpoch].toFixed(3)}</div>
        <div>tau_reg_raw: {overfitTau[markerEpoch].toFixed(2)}</div>
        <div>sol_fraction: {overfitSol[markerEpoch].toFixed(3)}</div>
      </div>
    </FigureCard>
  );
}

function Figure13Comparison() {
  const [mode, setMode] = useState("heatmap");
  const radarMetrics = [
    "Acc",
    "T-extra",
    "Interp",
    "Consist",
    "Cost",
  ];
  const radarModels = [
    { name: "RF", color: COLORS.green, values: [4, 0.5, 0.3, 0.3, 4] },
    { name: "DirectGNN", color: COLORS.yellow, values: [2.3, 0.4, 0.5, 0.5, 3] },
    { name: "TGNN-D", color: COLORS.blue, values: [4, 3.5, 4, 4, 2.2] },
  ];
  const heatmapRows = [
    ["RF (desc)", "●●●●", "○○○○", "○○○○", "○○○○", "●●●●"],
    ["DirectGNN", "●●○○", "○○○○", "○○○○", "○○○○", "●●●○"],
    ["TGNN (current)", "●●○○", "●●●○", "●●●●", "●●●●", "●●○○"],
    ["TGNN + desc (exp.)", "●●●●", "●●●○", "●●●●", "●●●●", "●●○○"],
    ["UNIFAC", "●●●○", "●●●●", "●●●●", "●●●●", "●●●●"],
    ["COSMO-RS", "●●●○", "●●●●", "●●●○", "●●●●", "●○○○"],
  ];

  return (
    <FigureCard
      kicker="Figure 13"
      title="Comparison Table"
      subtitle="The visual summary is easiest to read as either a radar overlay or a Harvey-ball matrix."
      controls={
        <ToggleGroup
          label="Comparison mode"
          options={[
            { label: "Radar", value: "radar" },
            { label: "Heatmap", value: "heatmap" },
          ]}
          value={mode}
          onChange={setMode}
        />
      }
    >
      {mode === "radar" ? (
        <div className="comparison-radar-layout">
          <div className="comparison-radar-card">
            <svg viewBox="0 0 360 300" role="img" aria-label="Model comparison radar chart">
            {Array.from({ length: 4 }, (_, ring) => {
              const radius = 34 + ring * 20;
              const points = radarMetrics.map((_, index) => {
                const angle = (360 / radarMetrics.length) * index;
                const point = polarToCartesian(170, 150, radius, angle);
                return `${point.x},${point.y}`;
              });
              return <polygon key={radius} points={points.join(" ")} fill="none" stroke={COLORS.line} strokeWidth="1.6" />;
            })}
            {radarMetrics.map((metric, index) => {
              const angle = (360 / radarMetrics.length) * index;
              const point = polarToCartesian(170, 150, 110, angle);
              const anchor = point.x < 154 ? "end" : point.x > 186 ? "start" : "middle";
              const dx = point.x < 154 ? -8 : point.x > 186 ? 8 : 0;
              const dy = point.y < 126 ? -8 : point.y > 174 ? 10 : 0;
              return (
                <g key={metric}>
                  <line x1="170" y1="150" x2={point.x} y2={point.y} stroke={COLORS.line} strokeWidth="1.6" />
                  <text
                    x={point.x + dx}
                    y={point.y + dy}
                    textAnchor={anchor}
                    dominantBaseline="middle"
                    fontSize="12"
                    fill={DECK_TEXT}
                    fontWeight="700"
                  >
                    {metric}
                  </text>
                </g>
              );
            })}
            {radarModels.map((model) => {
              const points = model.values.map((value, index) => {
                const angle = (360 / radarMetrics.length) * index;
                const point = polarToCartesian(170, 150, 34 + (value / 4) * 60, angle);
                return `${point.x},${point.y}`;
              });
              return (
                <polygon
                  key={model.name}
                  points={points.join(" ")}
                  fill={model.color}
                  fillOpacity="0.18"
                  stroke={model.color}
                  strokeWidth="3"
                />
              );
            })}
            </svg>
          </div>
          <div className="comparison-radar-side">
            <div className="comparison-radar-note">
              <strong>Reading guide</strong>
              <p>Higher is better on every axis. Accuracy and training cost are inverted before plotting so outer polygons always mean the more desirable trade-off.</p>
            </div>
            <FigureLegend items={radarModels.map((model) => ({ label: model.name, color: model.color }))} />
          </div>
        </div>
      ) : (
        <table className="comparison-matrix">
          <thead>
            <tr>
              <th>Model</th>
              <th>Accuracy</th>
              <th>T-extrap</th>
              <th>Interpret</th>
              <th>Consist</th>
              <th>Speed</th>
            </tr>
          </thead>
          <tbody>
            {heatmapRows.map((row) => (
              <tr key={row[0]}>
                {row.map((cell) => (
                  <td key={`${row[0]}-${cell}`}>{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </FigureCard>
  );
}

function Figure14MasterEquation() {
  const examples = [
    { key: "naphthalene", name: "Naphthalene / benzene", phi: 1.2, gamma: 0.02, label: "Nearly ideal" },
    { key: "paracetamol", name: "Paracetamol / ethanol", phi: 2.6, gamma: 0.54, label: "Moderate" },
    { key: "hexane", name: "Paracetamol / hexane", phi: 2.6, gamma: 8.9, label: "Very low" },
  ];
  const [selectedKey, setSelectedKey] = useState("paracetamol");
  const selected = examples.find((item) => item.key === selectedKey) ?? examples[1];
  const total = -(selected.phi + selected.gamma);
  const width = 760;
  const xScale = (value) => 80 + ((value + 15) / 15) * 580;

  return (
    <FigureCard
      kicker="Figure 14"
      title="Master Equation"
      subtitle="Two interpretable penalties add on a single log-solubility axis."
      controls={
        <ToggleGroup
          label="Example pair"
          options={[
            { label: "Naph / benzene", value: "naphthalene" },
            { label: "Para / ethanol", value: "paracetamol" },
            { label: "Para / hexane", value: "hexane" },
          ]}
          value={selectedKey}
          onChange={setSelectedKey}
        />
      }
    >
      <div className="equation-grid equation-grid--rebuilt">
        <div className="equation-header-card">
          <TexBlock>{"\\ln x_2 = -\\Phi - \\ln\\gamma_2"}</TexBlock>
          <p className="figure-subnote">Two interpretable penalties push the solution left on the same log-solubility axis: crystal resistance first, solvent mismatch second.</p>
        </div>

        <div className="equation-main equation-main--wide">
          <div className="equation-axis-card">
            <svg viewBox={`0 0 ${width} 260`} role="img" aria-label="Master equation visual explanation">
              <defs>
                <marker id="equation-blue-arrow" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill={COLORS.blue} />
                </marker>
                <marker id="equation-red-arrow" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill={COLORS.red} />
                </marker>
              </defs>
              <rect x="54" y="28" width="630" height="176" rx="18" fill={PAPER_FILL} />
              <line x1="80" y1="148" x2="660" y2="148" stroke={PAPER_TEXT} strokeWidth="4" strokeLinecap="round" />
              {[-15, -12, -9, -6, -3, 0].map((tick) => (
                <g key={tick}>
                  <line x1={xScale(tick)} y1="137" x2={xScale(tick)} y2="159" stroke={PAPER_TEXT} strokeWidth="2" />
                  <text x={xScale(tick)} y="180" textAnchor="middle" fontSize="14" fill={PAPER_SOFT_TEXT}>
                    {tick}
                  </text>
                </g>
              ))}
              <path
                d={`M ${xScale(0)} 86 L ${xScale(-selected.phi)} 86`}
                fill="none"
                stroke={COLORS.blue}
                strokeWidth="4.8"
                strokeLinecap="round"
                markerEnd="url(#equation-blue-arrow)"
              />

              <path
                d={`M ${xScale(-selected.phi)} 122 L ${xScale(total)} 122`}
                fill="none"
                stroke={COLORS.red}
                strokeWidth="4.8"
                strokeLinecap="round"
                markerEnd="url(#equation-red-arrow)"
              />
              <line x1={xScale(total)} y1="122" x2={xScale(total)} y2="148" stroke={COLORS.green} strokeWidth="2.5" strokeDasharray="5 4" />
              <circle cx={xScale(total)} cy="148" r="9" fill={COLORS.green} />

              <text x="86" y="198" fontSize="12" fill={PAPER_SOFT_TEXT}>
                very low solubility
              </text>
              <text x="560" y="198" fontSize="12" fill={PAPER_SOFT_TEXT}>
                fully miscible
              </text>
            </svg>

            <div className="equation-summary-strip">
              <div className="equation-summary-item">
                <strong>Crystal term</strong>
                <span>{selected.phi.toFixed(2)}</span>
              </div>
              <div className="equation-summary-item">
                <strong>Interaction term</strong>
                <span>{selected.gamma.toFixed(2)}</span>
              </div>
              <div className="equation-summary-item equation-summary-item--final">
                <strong>Final ln x₂</strong>
                <span>{total.toFixed(2)} · {selected.label}</span>
              </div>
            </div>
          </div>

          <div className="equation-contrib">
            <div className="equation-contrib__card equation-contrib__card--blue">
              <strong><TexInline>{"-\\Phi"}</TexInline></strong>
              <span>Crystal penalty</span>
              <small><TexInline>{"T_m,\\ \\Delta H,\\ \\Delta C_p"}</TexInline></small>
            </div>
            <div className="equation-contrib__card equation-contrib__card--red">
              <strong><TexInline>{"-\\ln\\gamma_2"}</TexInline></strong>
              <span>Interaction penalty</span>
              <small><TexInline>{"\\tau_{12},\\ \\tau_{21},\\ \\alpha"}</TexInline></small>
            </div>
            <div className="equation-contrib__card equation-contrib__card--green">
              <strong><TexInline>{"\\ln x_2"}</TexInline></strong>
              <span>Resulting log-solubility</span>
              <small>{selected.label}</small>
            </div>
          </div>
        </div>

        <div className="equation-example-list">
          {examples.map((example) => {
            const value = -(example.phi + example.gamma);
            return (
              <div key={example.key} className={`equation-example${selectedKey === example.key ? " is-active" : ""}`}>
                <strong>{example.name}</strong>
                <span><TexInline>{`\\Phi \\approx ${example.phi}`}</TexInline></span>
                <span><TexInline>{`\\ln\\gamma_2 \\approx ${example.gamma}`}</TexInline></span>
                <span><TexInline>{`\\ln x_2 \\approx ${value.toFixed(1)}`}</TexInline></span>
                <small>{example.label}</small>
              </div>
            );
          })}
        </div>
      </div>
    </FigureCard>
  );
}

function Figure15SolventScreening() {
  const examples = {
    paracetamol: {
      name: "Paracetamol",
      smiles: "CC(=O)Nc1ccc(O)cc1",
      temperature: "298 K",
      best: "DMSO",
      green: "Ethanol",
      anti: "Water",
      rows: [
        { name: "DMSO", cls: "sulfoxide", ln: -0.9, mg: 152, green: 5, ich: "3", color: COLORS.purple },
        { name: "DMF", cls: "amide", ln: -1.3, mg: 96, green: 2, ich: "2", color: COLORS.red },
        { name: "Ethanol", cls: "alcohol", ln: -2.7, mg: 34, green: 8, ich: "3", color: COLORS.blue },
        { name: "Acetone", cls: "ketone", ln: -2.9, mg: 28, green: 8, ich: "3", color: COLORS.orange },
        { name: "Ethyl acetate", cls: "ester", ln: -4.1, mg: 8, green: 8, ich: "3", color: COLORS.green },
        { name: "Water", cls: "water", ln: -3.4, mg: 14, green: 10, ich: "3", color: COLORS.sky },
      ],
      window: {
        solvent: "Ethanol",
        hot: 333,
        cold: 278,
        yield: 0.74,
        supersat: 4.2,
        scan: [
          [278, 0.014],
          [288, 0.018],
          [298, 0.024],
          [308, 0.033],
          [318, 0.046],
          [333, 0.058],
        ],
      },
      greenRows: [
        { name: "Ethanol", retention: 0.35, gain: "+6" },
        { name: "Dimethyl carbonate", retention: 0.28, gain: "+7" },
        { name: "2-MeTHF", retention: 0.21, gain: "+6" },
      ],
      antisolvent: {
        name: "Water",
        ratio: 16,
        miscibility: "miscible with ethanol",
      },
    },
    carbamazepine: {
      name: "Carbamazepine",
      smiles: "NC(=O)N1c2ccccc2C=Cc2ccccc21",
      temperature: "298 K",
      best: "NMP",
      green: "2-MeTHF",
      anti: "Water",
      rows: [
        { name: "NMP", cls: "amide", ln: -0.7, mg: 184, green: 1, ich: "2", color: COLORS.red },
        { name: "DMF", cls: "amide", ln: -1.0, mg: 140, green: 2, ich: "2", color: COLORS.purple },
        { name: "DMSO", cls: "sulfoxide", ln: -1.1, mg: 132, green: 5, ich: "3", color: COLORS.blue },
        { name: "Methanol", cls: "alcohol", ln: -2.9, mg: 24, green: 5, ich: "2", color: COLORS.orange },
        { name: "2-MeTHF", cls: "ether", ln: -4.3, mg: 4.9, green: 8, ich: "n/a", color: COLORS.green },
        { name: "Water", cls: "water", ln: -6.4, mg: 0.24, green: 10, ich: "3", color: COLORS.sky },
      ],
      window: {
        solvent: "2-MeTHF",
        hot: 348,
        cold: 283,
        yield: 0.88,
        supersat: 12.5,
        scan: [
          [283, 0.0021],
          [293, 0.0034],
          [303, 0.0058],
          [323, 0.014],
          [338, 0.027],
          [348, 0.034],
        ],
      },
      greenRows: [
        { name: "2-MeTHF", retention: 0.41, gain: "+7" },
        { name: "Ethyl acetate", retention: 0.26, gain: "+6" },
        { name: "CPME", retention: 0.22, gain: "+7" },
      ],
      antisolvent: {
        name: "Water",
        ratio: 140,
        miscibility: "miscible with NMP / DMF",
      },
    },
  };
  const [activeKey, setActiveKey] = useState("paracetamol");
  const example = examples[activeKey];
  const maxMg = Math.max(...example.rows.map((row) => row.mg));
  const scanMin = Math.min(...example.window.scan.map((point) => point[0]));
  const scanMax = Math.max(...example.window.scan.map((point) => point[0]));
  const windowChart = createChartScales({
    left: 48,
    right: 296,
    top: 42,
    bottom: 150,
    xMin: scanMin,
    xMax: scanMax,
    yMin: 0,
    yMax: example.window.scan[example.window.scan.length - 1][1],
  });
  const path = linePath(example.window.scan.map(([t, x]) => [windowChart.xScale(t), windowChart.yScale(x)]));
  const hotX = windowChart.xScale(example.window.hot);
  const coldX = windowChart.xScale(example.window.cold);
  const hotAnchor = hotX > (windowChart.left + windowChart.right) / 2 ? "end" : "start";
  const coldAnchor = coldX > (windowChart.left + windowChart.right) / 2 ? "end" : "start";

  return (
    <FigureCard
      kicker="Figure 15"
      title="Solvent Screening"
      subtitle="Library ranking, crystallization windows, green replacements, and antisolvent logic on top of the same checkpoint."
      controls={
        <ToggleGroup
          label="Screening example"
          options={[
            { label: "Paracetamol", value: "paracetamol" },
            { label: "Carbamazepine", value: "carbamazepine" },
          ]}
          value={activeKey}
          onChange={setActiveKey}
        />
      }
    >
      <div className="application-slide-grid">
        <div className="application-slide-hero">
          <MoleculeMiniCard role="screening target" name={example.name} smiles={example.smiles} compact />
          <div className="application-slide-query">
            <strong>Query</strong>
            <span>{example.temperature} screen over the built-in solvent library</span>
            <small>Same workflow works for `TGNN-Solv` and `DirectGNN`; full decomposition is richer on the physics path.</small>
          </div>
        </div>

        <StatStrip
          items={[
            { label: "Best loading solvent", value: example.best },
            { label: "Best green alternative", value: example.green },
            { label: "Best antisolvent", value: example.anti },
            { label: "mg/mL note", value: "density-based approximation" },
          ]}
        />

        <div className="screening-slide-layout">
          <div className="screening-rank-card">
            <div className="application-card-title">Ranked solvent panel</div>
            <div className="screening-rank-list">
              {example.rows.map((row) => (
                <div className="screening-rank-row" key={row.name}>
                  <div className="screening-rank-meta">
                    <span className="screening-rank-dot" style={{ background: row.color }} />
                    <div>
                      <strong>{row.name}</strong>
                      <small>{row.cls} · ICH {row.ich} · green {row.green}</small>
                    </div>
                  </div>
                  <div className="screening-rank-bar">
                    <span className="screening-rank-fill" style={{ width: `${(row.mg / maxMg) * 100}%`, background: row.color }} />
                  </div>
                  <div className="screening-rank-values">
                    <strong>{row.mg.toFixed(row.mg >= 10 ? 0 : 1)}</strong>
                    <small>mg/mL</small>
                    <span>{row.ln.toFixed(1)}</span>
                  </div>
                </div>
              ))}
            </div>
            <FigureLegend
              items={[
                { label: "green / low-hazard", color: COLORS.green },
                { label: "workhorse polar aprotic", color: COLORS.purple },
                { label: "common process solvent", color: COLORS.orange },
              ]}
            />
          </div>

          <div className="screening-side-column">
            <div className="application-info-card">
              <div className="application-card-title">Typical filters</div>
              <div className="application-chip-list">
                <span className="application-chip">green score ≥ 5</span>
                <span className="application-chip">ICH class ≤ 2</span>
                <span className="application-chip">exclude chlorinated</span>
                <span className="application-chip">bp &lt; 373 K</span>
              </div>
              <p className="figure-subnote">Filtering happens before ranking so the UI can answer “best solvent under my process constraints”, not only “best solvent in theory”.</p>
            </div>

            <div className="application-info-card">
              <div className="application-card-title">Green replacement</div>
              <table className="application-mini-table">
                <thead>
                  <tr>
                    <th>Replacement</th>
                    <th>Retention</th>
                    <th>Green Δ</th>
                  </tr>
                </thead>
                <tbody>
                  {example.greenRows.map((row) => (
                    <tr key={row.name}>
                      <td>{row.name}</td>
                      <td>{Math.round(row.retention * 100)}%</td>
                      <td>{row.gain}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="application-info-card">
              <div className="application-card-title">Antisolvent candidate</div>
              <div className="application-highlight">
                <strong>{example.antisolvent.name}</strong>
                <span>{example.antisolvent.ratio}× poorer than the good solvent</span>
                <small>{example.antisolvent.miscibility}</small>
              </div>
            </div>
          </div>
        </div>

        <div className="screening-bottom-grid">
          <div className="application-info-card">
            <div className="application-card-title">Crystallization window</div>
            <svg viewBox="0 0 340 190" role="img" aria-label="Crystallization window temperature scan">
              <rect x="18" y="14" width="304" height="162" rx="16" fill={PAPER_FILL} stroke={PAPER_BORDER} />
              <line x1={windowChart.left} y1={windowChart.bottom} x2={windowChart.right} y2={windowChart.bottom} stroke={PAPER_TEXT} strokeWidth="2" />
              <line x1={windowChart.left} y1={windowChart.top} x2={windowChart.left} y2={windowChart.bottom} stroke={PAPER_TEXT} strokeWidth="2" />
              <path d={path} fill="none" stroke={COLORS.blue} strokeWidth="4" strokeLinecap="round" />
              {example.window.scan.map(([t, x]) => (
                <g key={t}>
                  <circle cx={windowChart.xScale(t)} cy={windowChart.yScale(x)} r="5" fill={COLORS.blue} />
                  <text x={windowChart.xScale(t)} y="170" textAnchor="middle" fontSize="12" fill={PAPER_SOFT_TEXT}>
                    {t}
                  </text>
                </g>
              ))}
              <line x1={hotX} y1={windowChart.top - 8} x2={hotX} y2={windowChart.bottom} stroke={COLORS.orange} strokeDasharray="5 4" />
              <line x1={coldX} y1={windowChart.top - 8} x2={coldX} y2={windowChart.bottom} stroke={COLORS.green} strokeDasharray="5 4" />
              <text x={hotX + (hotAnchor === "end" ? -4 : 4)} y="30" textAnchor={hotAnchor} fontSize="12" fill={COLORS.orange}>hot</text>
              <text x={coldX + (coldAnchor === "end" ? -4 : 4)} y="30" textAnchor={coldAnchor} fontSize="12" fill={COLORS.green}>cold</text>
            </svg>
            <div className="application-metric-row">
              <span><TexInline>{"Y \\approx \\frac{x_{hot}-x_{cold}}{x_{hot}}"}</TexInline></span>
              <strong>{Math.round(example.window.yield * 100)}% yield</strong>
              <span>{example.window.supersat.toFixed(1)}× supersaturation</span>
            </div>
          </div>

          <div className="application-info-card">
            <div className="application-card-title">Top candidates at a glance</div>
            <table className="application-mini-table">
              <thead>
                <tr>
                  <th>Solvent</th>
                  <th>`ln x₂`</th>
                  <th>mg/mL</th>
                  <th>Green</th>
                </tr>
              </thead>
              <tbody>
                {example.rows.slice(0, 5).map((row) => (
                  <tr key={`${row.name}-table`}>
                    <td>{row.name}</td>
                    <td>{row.ln.toFixed(1)}</td>
                    <td>{row.mg.toFixed(row.mg >= 10 ? 0 : 1)}</td>
                    <td>{row.green}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="figure-subnote">The full DataFrame also carries `Φ`, `γ₂`, `T_m`, `ΔH_fus`, Hansen distance, AD confidence, and solvent metadata when available.</p>
          </div>
        </div>
      </div>
    </FigureCard>
  );
}

function Figure16ProcessOptimization() {
  const paretoPoints = [
    { name: "2-MeTHF", yield: 0.81, green: 8, color: COLORS.green, labelDx: 12, labelDy: -10, anchor: "start" },
    { name: "EtOAc", yield: 0.66, green: 8, color: COLORS.blue, labelDx: 12, labelDy: 4, anchor: "start" },
    { name: "Acetone", yield: 0.61, green: 8, color: COLORS.orange, labelDx: 12, labelDy: 16, anchor: "start" },
    { name: "DMF", yield: 0.88, green: 2, color: COLORS.red, labelDx: 12, labelDy: -8, anchor: "start" },
    { name: "DMSO", yield: 0.84, green: 5, color: COLORS.purple, labelDx: 12, labelDy: -8, anchor: "start" },
  ];
  const paretoChart = createChartScales({
    left: 58,
    right: 288,
    top: 42,
    bottom: 168,
    xMin: 1,
    xMax: 10,
    yMin: 0.45,
    yMax: 0.9,
  });

  return (
    <FigureCard
      kicker="Figure 16"
      title="Process Optimization"
      subtitle="The application layer can optimize operating windows, not only score isolated solvent points."
    >
      <div className="application-slide-grid">
        <StatStrip
          items={[
            { label: "Best crystallization window", value: "2-MeTHF · 338→278 K · 81%" },
            { label: "Best extraction solvent", value: "EtOAc · K = 14" },
            { label: "Best reaction medium", value: "Acetone · reactants/product = 4.6" },
            { label: "Mixture idea", value: "70% EtOH / 30% water" },
          ]}
        />

        <div className="process-mode-grid">
          <div className="application-info-card">
            <div className="application-card-title">Crystallization</div>
            <TexBlock>{"\\max\\ Y = \\frac{x_{hot} - x_{cold}}{x_{hot}}"}</TexBlock>
            <ul className="application-bullet-list">
              <li>`T_hot` constrained by solvent boiling point.</li>
              <li>`T_cold` constrained by the practical cooling floor.</li>
              <li>Ranking combines yield, supersaturation, green score, and loading.</li>
            </ul>
          </div>
          <div className="application-info-card">
            <div className="application-card-title">Extraction</div>
            <TexBlock>{"K = \\frac{x_{2,extract}}{x_{2,source}}"}</TexBlock>
            <ul className="application-bullet-list">
              <li>Immiscibility and boiling point stay in the objective, not only in a post-hoc comment.</li>
              <li>Good extraction solvents need both partition leverage and operability.</li>
              <li>Recommended rows stay visible as a constrained shortlist.</li>
            </ul>
          </div>
          <div className="application-info-card">
            <div className="application-card-title">Reaction medium</div>
            <TexBlock>{"\\max\\ \\frac{\\min_i S_{reactant,i}}{S_{product}}"}</TexBlock>
            <ul className="application-bullet-list">
              <li>Reactants should stay soluble while product should want to leave solution.</li>
              <li>Useful for precipitation-driven workups and telescoped routes.</li>
              <li>Shared solvent metadata keeps toxicity and green constraints visible.</li>
            </ul>
          </div>
        </div>

        <div className="screening-bottom-grid">
          <div className="application-info-card">
            <div className="application-card-title">Pareto front: yield vs green score</div>
            <svg viewBox="0 0 340 200" role="img" aria-label="Pareto front scatter plot">
              <rect x="12" y="12" width="314" height="180" rx="16" fill={PAPER_FILL} stroke={PAPER_BORDER} />
              <line x1={paretoChart.left} y1={paretoChart.bottom} x2={paretoChart.right} y2={paretoChart.bottom} stroke={PAPER_TEXT} strokeWidth="2" />
              <line x1={paretoChart.left} y1={paretoChart.top} x2={paretoChart.left} y2={paretoChart.bottom} stroke={PAPER_TEXT} strokeWidth="2" />
              {[2, 4, 6, 8, 10].map((tick) => (
                <g key={`green-${tick}`}>
                  <line x1={paretoChart.xScale(tick)} y1={paretoChart.bottom} x2={paretoChart.xScale(tick)} y2={paretoChart.bottom + 5} stroke={PAPER_TEXT} strokeWidth="1.6" />
                  <text x={paretoChart.xScale(tick)} y="180" textAnchor="middle" fontSize="12" fill={PAPER_SOFT_TEXT}>
                    {tick}
                  </text>
                </g>
              ))}
              {[0.5, 0.6, 0.7, 0.8, 0.9].map((tick) => (
                <g key={`yield-${tick}`}>
                  <line x1={paretoChart.left - 5} y1={paretoChart.yScale(tick)} x2={paretoChart.left} y2={paretoChart.yScale(tick)} stroke={PAPER_TEXT} strokeWidth="1.6" />
                  <text x="42" y={paretoChart.yScale(tick)} textAnchor="end" dominantBaseline="middle" fontSize="12" fill={PAPER_SOFT_TEXT}>
                    {tick.toFixed(1)}
                  </text>
                </g>
              ))}
              {paretoPoints.map((point) => {
                const pointX = paretoChart.xScale(point.green);
                const pointY = paretoChart.yScale(point.yield);

                return (
                  <g key={point.name}>
                    <circle cx={pointX} cy={pointY} r="7" fill={point.color} />
                    <text
                      x={pointX + point.labelDx}
                      y={pointY + point.labelDy}
                      textAnchor={point.anchor}
                      fontSize="12"
                      fill={PAPER_TEXT}
                      paintOrder="stroke"
                      stroke={PAPER_FILL}
                      strokeWidth="3"
                      strokeLinejoin="round"
                    >
                      {point.name}
                    </text>
                  </g>
                );
              })}
              <path
                d={`M ${paretoChart.xScale(5)} ${paretoChart.yScale(0.84)} L ${paretoChart.xScale(8)} ${paretoChart.yScale(0.81)} L ${paretoChart.xScale(8)} ${paretoChart.yScale(0.66)}`}
                fill="none"
                stroke={COLORS.green}
                strokeDasharray="5 4"
                strokeWidth="2.5"
              />
              <text x={(paretoChart.left + paretoChart.right) / 2} y="188" textAnchor="middle" fontSize="12" fill={PAPER_SOFT_TEXT}>
                green score
              </text>
              <text
                x="24"
                y={(paretoChart.top + paretoChart.bottom) / 2}
                textAnchor="middle"
                fontSize="12"
                fill={PAPER_SOFT_TEXT}
                transform={`rotate(-90 24 ${(paretoChart.top + paretoChart.bottom) / 2})`}
              >
                yield
              </text>
            </svg>
          </div>

          <div className="application-info-card">
            <div className="application-card-title">Binary solvent design</div>
            <table className="application-mini-table">
              <thead>
                <tr>
                  <th>Mixture</th>
                  <th>Target</th>
                  <th>Predicted role</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>70% EtOH / 30% water</td>
                  <td>1 to 5 mg/mL</td>
                  <td>Controlled crash-out</td>
                </tr>
                <tr>
                  <td>60% acetone / 40% EtOAc</td>
                  <td>high loading</td>
                  <td>Fast solvent swap</td>
                </tr>
                <tr>
                  <td>50% IPA / 50% water</td>
                  <td>moderate window</td>
                  <td>Gentler cooling isolation</td>
                </tr>
              </tbody>
            </table>
            <p className="figure-subnote">The first pass interpolates solvent descriptors and Hansen coordinates; the second pass re-evaluates a pseudo-pure mixture proxy with the same checkpoint.</p>
          </div>
        </div>
      </div>
    </FigureCard>
  );
}

function Figure17DrugDevelopability() {
  const cases = {
    paracetamol: {
      name: "Paracetamol",
      smiles: "CC(=O)Nc1ccc(O)cc1",
      bcs: "III",
      badgeColor: COLORS.blue,
      dose: 0.14,
      permeability: "low proxy",
      pH: [
        { label: "pH 1.0", value: 14.2 },
        { label: "pH 4.5", value: 14.0 },
        { label: "pH 6.8", value: 13.7 },
      ],
      radar: [0.78, 0.63, 0.58, 0.80, 0.52],
      risks: ["permeability-limited exposure risk", "moderate crystal stability"],
      recs: ["simple IR remains plausible", "watch transport / absorption rather than only aqueous dose number"],
      salts: [
        { name: "Na salt surrogate", gain: "1.4×", note: "approximate ionic uplift" },
        { name: "Nicotinamide cocrystal", gain: "1.2×", note: "modest crystal softening" },
      ],
    },
    carbamazepine: {
      name: "Carbamazepine",
      smiles: "NC(=O)N1c2ccccc2C=Cc2ccccc21",
      bcs: "II",
      badgeColor: COLORS.orange,
      dose: 11.2,
      permeability: "high proxy",
      pH: [
        { label: "pH 1.0", value: 0.19 },
        { label: "pH 4.5", value: 0.18 },
        { label: "pH 6.8", value: 0.17 },
      ],
      radar: [0.16, 0.28, 0.61, 0.31, 0.44],
      risks: ["severe aqueous solubility bottleneck", "high crystal stability"],
      recs: ["salt or co-crystal screening", "amorphous solid dispersion / lipid formulation"],
      salts: [
        { name: "Saccharin cocrystal", gain: "2.6×", note: "approximate crystal-form effect" },
        { name: "Maleate salt surrogate", gain: "3.1×", note: "flagged as lower confidence" },
      ],
    },
  };
  const radarAxes = ["Aq sol", "Crystal", "Lipo", "Diversity", "dlnx/dT"];
  const [activeKey, setActiveKey] = useState("paracetamol");
  const active = cases[activeKey];
  const maxPh = Math.max(...active.pH.map((item) => item.value));
  const radarCenterX = 168;
  const radarCenterY = 148;
  const radarInnerRadius = 34;
  const radarOuterRadius = 112;
  const radarLabelRadius = 132;

  return (
    <FigureCard
      kicker="Figure 17"
      title="Drug Developability"
      subtitle="BCS-style classification and formulation-facing triage built on top of aqueous TGNN screening."
      controls={
        <ToggleGroup
          label="Developability case"
          options={[
            { label: "Paracetamol", value: "paracetamol" },
            { label: "Carbamazepine", value: "carbamazepine" },
          ]}
          value={activeKey}
          onChange={setActiveKey}
        />
      }
    >
      <div className="application-slide-grid">
        <div className="application-slide-hero">
          <MoleculeMiniCard role="candidate" name={active.name} smiles={active.smiles} compact />
          <div className="application-slide-query">
            <strong>BCS-style output</strong>
            <span>
              <span className="application-badge" style={{ background: active.badgeColor }}>Class {active.bcs}</span>
              <span>Dose number = {active.dose.toFixed(2)} · permeability = {active.permeability}</span>
            </span>
            <small>High/low permeability is still proxy-driven unless external transport data is supplied.</small>
          </div>
        </div>

        <div className="developability-grid">
          <div className="application-info-card">
            <div className="application-card-title">Aqueous pH profile at 37 °C</div>
            <div className="screening-rank-list">
              {active.pH.map((row) => (
                <div className="screening-rank-row" key={row.label}>
                  <div className="screening-rank-meta">
                    <span className="screening-rank-dot" style={{ background: COLORS.blue }} />
                    <div>
                      <strong>{row.label}</strong>
                      <small>Henderson-Hasselbalch corrected when pKa estimate exists</small>
                    </div>
                  </div>
                  <div className="screening-rank-bar">
                    <span className="screening-rank-fill" style={{ width: `${(row.value / maxPh) * 100}%`, background: COLORS.blue }} />
                  </div>
                  <div className="screening-rank-values">
                    <strong>{row.value.toFixed(row.value >= 1 ? 1 : 2)}</strong>
                    <small>mg/mL</small>
                  </div>
                </div>
              ))}
            </div>
            <p className="figure-subnote">BCS solubility logic is driven by <TexInline>{"D_0 = \\frac{dose}{V \\cdot S}"}</TexInline> with `V = 250 mL` by default.</p>
          </div>

          <div className="application-info-card">
            <div className="application-card-title">Composite developability score</div>
            <div className="comparison-radar-layout comparison-radar-layout--compact">
              <div className="comparison-radar-card comparison-radar-card--compact">
                <svg viewBox="0 0 350 300" role="img" aria-label="Developability radar chart">
                  {Array.from({ length: 4 }, (_, ring) => {
                    const radius = radarInnerRadius + ring * 26;
                    const points = radarAxes.map((_, index) => {
                      const angle = (360 / radarAxes.length) * index;
                      const point = polarToCartesian(radarCenterX, radarCenterY, radius, angle);
                      return `${point.x},${point.y}`;
                    });
                    return <polygon key={radius} points={points.join(" ")} fill="none" stroke={COLORS.line} strokeWidth="1.4" />;
                  })}
                  {radarAxes.map((axis, index) => {
                    const angle = (360 / radarAxes.length) * index;
                    const point = polarToCartesian(radarCenterX, radarCenterY, radarLabelRadius, angle);
                    const anchor = point.x < radarCenterX - 8 ? "end" : point.x > radarCenterX + 8 ? "start" : "middle";
                    return (
                      <g key={axis}>
                        <line x1={radarCenterX} y1={radarCenterY} x2={polarToCartesian(radarCenterX, radarCenterY, radarOuterRadius, angle).x} y2={polarToCartesian(radarCenterX, radarCenterY, radarOuterRadius, angle).y} stroke={COLORS.line} strokeWidth="1.4" />
                        <text x={point.x} y={point.y} textAnchor={anchor} dominantBaseline="middle" fontSize="11.5" fill={DECK_TEXT} fontWeight="700">
                          {axis}
                        </text>
                      </g>
                    );
                  })}
                  <polygon
                    points={active.radar.map((value, index) => {
                      const angle = (360 / radarAxes.length) * index;
                      const point = polarToCartesian(
                        radarCenterX,
                        radarCenterY,
                        radarInnerRadius + value * (radarOuterRadius - radarInnerRadius),
                        angle,
                      );
                      return `${point.x},${point.y}`;
                    }).join(" ")}
                    fill={active.badgeColor}
                    fillOpacity="0.24"
                    stroke={active.badgeColor}
                    strokeWidth="3"
                  />
                </svg>
              </div>
              <div className="comparison-radar-side comparison-radar-side--compact">
                <div className="application-highlight">
                  <strong>Traffic light</strong>
                  <span style={{ color: active.badgeColor }}>{active.bcs === "II" ? "yellow" : "green-yellow"}</span>
                  <small>Composite score mixes aqueous solubility, crystal burden, lipophilicity balance, solvent diversity, and temperature leverage.</small>
                </div>
              </div>
            </div>
          </div>

          <div className="application-info-card">
            <div className="application-card-title">Recommendations and risks</div>
            <div className="application-chip-list">
              {active.risks.map((risk) => (
                <span key={risk} className="application-chip application-chip--risk">{risk}</span>
              ))}
            </div>
            <ul className="application-bullet-list">
              {active.recs.map((rec) => (
                <li key={rec}>{rec}</li>
              ))}
            </ul>
          </div>
        </div>

        <div className="screening-bottom-grid">
          <div className="application-info-card">
            <div className="application-card-title">Salt / cocrystal triage</div>
            <table className="application-mini-table">
              <thead>
                <tr>
                  <th>Form</th>
                  <th>Advantage</th>
                  <th>Caveat</th>
                </tr>
              </thead>
              <tbody>
                {active.salts.map((row) => (
                  <tr key={row.name}>
                    <td>{row.name}</td>
                    <td>{row.gain}</td>
                    <td>{row.note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="application-info-card">
            <div className="application-card-title">Reference-drug context</div>
            <table className="application-mini-table">
              <thead>
                <tr>
                  <th>Drug</th>
                  <th>Class</th>
                  <th>Interpretation</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Paracetamol</td>
                  <td>III</td>
                  <td>soluble, transport-limited proxy</td>
                </tr>
                <tr>
                  <td>Ibuprofen</td>
                  <td>II</td>
                  <td>lipophilic, dissolution-limited</td>
                </tr>
                <tr>
                  <td>Metformin</td>
                  <td>III</td>
                  <td>highly polar, permeability-limited</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </FigureCard>
  );
}

function Figure18PKProfile() {
  const compartments = [
    { name: "stomach\nfasted", sol: 3.2, frac: 1.0, dose: 0.31 },
    { name: "stomach\nfed", sol: 4.1, frac: 1.0, dose: 0.18 },
    { name: "duodenum", sol: 7.8, frac: 1.0, dose: 0.11 },
    { name: "jejunum /\nileum", sol: 6.2, frac: 0.93, dose: 0.14 },
    { name: "colon", sol: 2.4, frac: 0.42, dose: 0.58 },
  ];
  const media = [
    { name: "FaSSGF", value: 3.0, color: COLORS.red },
    { name: "FeSSGF", value: 4.2, color: COLORS.orange },
    { name: "FaSSIF", value: 7.6, color: COLORS.blue },
    { name: "FeSSIF", value: 12.4, color: COLORS.green },
  ];
  const maxMedia = Math.max(...media.map((item) => item.value));
  const giChart = createChartScales({
    left: 50,
    right: 294,
    top: 46,
    bottom: 152,
    xMin: 0,
    xMax: compartments.length - 1,
    yMin: 0,
    yMax: 1,
  });
  const linePoints = compartments.map((row, index) => [giChart.xScale(index), giChart.yScale(row.frac)]);

  return (
    <FigureCard
      kicker="Figure 18"
      title="PK Solubility Profile"
      subtitle="GI compartments, biorelevant media, and formulation-vehicle screens turn water solubility into a dosage-form narrative."
    >
      <div className="application-slide-grid">
        <StatStrip
          items={[
            { label: "Max absorbable dose", value: "≈ 780 mg" },
            { label: "`f_abs` proxy", value: "0.82" },
            { label: "Rate-limiting step", value: "distal-water dilution" },
            { label: "Food effect", value: "positive" },
          ]}
        />

        <div className="pk-compartment-strip">
          {compartments.map((row) => (
            <div key={row.name} className="pk-compartment-card">
              <strong>{row.name}</strong>
              <span>{row.sol.toFixed(1)} mg/mL</span>
              <small>{Math.round(row.frac * 100)}% dissolved</small>
            </div>
          ))}
        </div>

        <div className="screening-bottom-grid">
          <div className="application-info-card">
            <div className="application-card-title">Dissolved fraction along the GI tract</div>
            <svg viewBox="0 0 340 190" role="img" aria-label="GI dissolved fraction">
              <rect x="16" y="14" width="308" height="172" rx="16" fill={PAPER_FILL} stroke={PAPER_BORDER} />
              <line x1={giChart.left} y1={giChart.bottom} x2={giChart.right} y2={giChart.bottom} stroke={PAPER_TEXT} strokeWidth="2" />
              <line x1={giChart.left} y1={giChart.top} x2={giChart.left} y2={giChart.bottom} stroke={PAPER_TEXT} strokeWidth="2" />
              <path d={linePath(linePoints)} fill="none" stroke={COLORS.blue} strokeWidth="4" strokeLinecap="round" />
              {compartments.map((row, index) => (
                <g key={`gi-${row.name}`}>
                  <circle cx={giChart.xScale(index)} cy={giChart.yScale(row.frac)} r="5" fill={COLORS.blue} />
                  <text x={giChart.xScale(index)} y="168" textAnchor="middle" fontSize="11" fill={PAPER_SOFT_TEXT}>
                    {index + 1}
                  </text>
                </g>
              ))}
              <text x={(giChart.left + giChart.right) / 2} y="180" textAnchor="middle" fontSize="12" fill={PAPER_SOFT_TEXT}>
                GI compartment index
              </text>
            </svg>
            <p className="figure-subnote">Each compartment combines pH-corrected water solubility with a volume-limited dissolved-fraction estimate. The result is a dissolution pressure profile, not a full PBPK model.</p>
          </div>

          <div className="application-info-card">
            <div className="application-card-title">Biorelevant media and food effect</div>
            <div className="screening-rank-list">
              {media.map((row) => (
                <div className="screening-rank-row" key={row.name}>
                  <div className="screening-rank-meta">
                    <span className="screening-rank-dot" style={{ background: row.color }} />
                    <div>
                      <strong>{row.name}</strong>
                      <small>{row.name.includes("Fe") ? "fed state" : "fasted state"}</small>
                    </div>
                  </div>
                  <div className="screening-rank-bar">
                    <span className="screening-rank-fill" style={{ width: `${(row.value / maxMedia) * 100}%`, background: row.color }} />
                  </div>
                  <div className="screening-rank-values">
                    <strong>{row.value.toFixed(1)}</strong>
                    <small>mg/mL</small>
                  </div>
                </div>
              ))}
            </div>
            <div className="application-highlight">
              <strong>Food-effect heuristic</strong>
              <span>FeSSIF / FaSSIF ≈ 1.6×</span>
              <small>Suggests a positive fed-state solubilization effect.</small>
            </div>
          </div>
        </div>

        <div className="screening-bottom-grid">
          <div className="application-info-card">
            <div className="application-card-title">IV vehicle screen</div>
            <table className="application-mini-table">
              <thead>
                <tr>
                  <th>Vehicle</th>
                  <th>25 °C</th>
                  <th>37 °C</th>
                  <th>Flag</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>PEG 400 surrogate</td>
                  <td>28</td>
                  <td>34</td>
                  <td>high osmolality</td>
                </tr>
                <tr>
                  <td>Propylene glycol</td>
                  <td>18</td>
                  <td>22</td>
                  <td>co-solvent ceiling</td>
                </tr>
                <tr>
                  <td>Cyclodextrin solution</td>
                  <td>11</td>
                  <td>14</td>
                  <td>complexation route</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="application-info-card">
            <div className="application-card-title">Topical vehicle screen</div>
            <table className="application-mini-table">
              <thead>
                <tr>
                  <th>Vehicle</th>
                  <th>Solubility</th>
                  <th>Activity</th>
                  <th>Use</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Propylene glycol</td>
                  <td>16 mg/mL</td>
                  <td>high</td>
                  <td>balanced loading/activity</td>
                </tr>
                <tr>
                  <td>Ethanol solution</td>
                  <td>22 mg/mL</td>
                  <td>medium</td>
                  <td>volatile fast-drying</td>
                </tr>
                <tr>
                  <td>DMSO</td>
                  <td>80 mg/mL</td>
                  <td>low</td>
                  <td>penetration enhancer, irritation risk</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </FigureCard>
  );
}

export const PRESENTATION_FIGURES = [
  {
    slug: "data-pipeline",
    title: "Data Pipeline",
    subtitle: "Sources → Merge & Enrich → Split",
    blurb: "Four heterogeneous sources merge into a sparse, scaffold-safe supervised dataset.",
    tags: ["data", "sparsity", "split"],
    component: Figure1DataPipeline,
  },
  {
    slug: "molecular-featurization",
    title: "Molecular Featurization",
    subtitle: "SMILES → 2D structure → graph",
    blurb: "Canonical SMILES become a molecular graph with typed atom and bond features.",
    tags: ["rdkit", "graph", "features"],
    component: Figure2Featurization,
  },
  {
    slug: "pretraining",
    title: "Pretraining",
    subtitle: "Optional Stage 0 before the curriculum",
    blurb: "Stage 0 is now a maintained warm-start pipeline that pretrains the encoder and readout with four molecular objectives.",
    tags: ["stage0", "contrastive", "pretrain"],
    component: FigurePretraining,
  },
  {
    slug: "architecture",
    title: "TGNN-Solv Architecture",
    subtitle: "Five swim lanes from graphs to `ln x₂_final`",
    blurb: "The core figure shows where shared MPNN/GPS representation learning ends and where hardcoded thermodynamics begin.",
    tags: ["architecture", "physics", "solver"],
    component: Figure3Architecture,
  },
  {
    slug: "matched-baseline",
    title: "Matched Baseline",
    subtitle: "Same backbone, different prediction head",
    blurb: "This slide isolates the main research comparison: TGNN-Solv versus DirectGNN on a shared upstream chemistry stack.",
    tags: ["baseline", "directgnn", "fairness"],
    component: Figure3ABaseline,
  },
  {
    slug: "solver-diagnostics",
    title: "Solver-Facing Diagnostics",
    subtitle: "Raw outputs, substituted outputs, exported intermediates",
    blurb: "The maintained forward API makes GC priors, oracle injection, and solver-facing tensors inspectable instead of hidden.",
    tags: ["diagnostics", "oracle", "intermediates"],
    component: Figure3BDiagnostics,
  },
  {
    slug: "sle-solver",
    title: "SLE Solver",
    subtitle: "Fixed-point geometry and contraction",
    blurb: "The solver iterates to a root quickly enough that implicit gradients are attractive.",
    tags: ["solver", "fixed-point", "nrtl"],
    component: Figure4Solver,
  },
  {
    slug: "implicit-diff",
    title: "Implicit Differentiation",
    subtitle: "Against unrolled backprop",
    blurb: "One backward step replaces an O(N) chain of stored solver iterations.",
    tags: ["training", "backprop", "memory"],
    component: Figure5Backprop,
  },
  {
    slug: "loss-landscape",
    title: "Loss Landscape",
    subtitle: "12 components before and after the `vant_hoff_local` fix",
    blurb: "The optimizer only behaves once solubility regains the dominant share of Phase 2 loss.",
    tags: ["loss", "optimization", "curriculum"],
    component: Figure6LossLandscape,
  },
  {
    slug: "linear-probe",
    title: "Linear Probe",
    subtitle: "Where descriptor information disappears",
    blurb: "Probe scores show that the encoder, not physics, dominates the current accuracy gap.",
    tags: ["probe", "descriptors", "bottleneck"],
    component: Figure7LinearProbe,
  },
  {
    slug: "error-decomposition",
    title: "Error Decomposition",
    subtitle: "Waterfall from RF to TGNN",
    blurb: "Most measured error increase comes from the GNN representation gap rather than the solver bottleneck.",
    tags: ["mae", "waterfall", "gap"],
    component: Figure8Waterfall,
  },
  {
    slug: "temperature-extrapolation",
    title: "Temperature Extrapolation",
    subtitle: "Why the physics path matters out of range",
    blurb: "Physics-guided temperature dependence remains meaningful where tabular models flatten out.",
    tags: ["temperature", "extrapolation", "schematic"],
    component: Figure9TemperatureExtrapolation,
  },
  {
    slug: "curriculum",
    title: "Three-Phase Curriculum",
    subtitle: "What trains when",
    blurb: "Curriculum structure controls solver activation, correction unfreezing, and oracle annealing.",
    tags: ["curriculum", "training", "schedule"],
    component: Figure10Curriculum,
  },
  {
    slug: "gc-priors",
    title: "GC Priors",
    subtitle: "Bounded residuals around group contribution estimates",
    blurb: "GC priors shrink the crystal-property search space before the model spends capacity on residuals.",
    tags: ["gc", "priors", "crystal"],
    component: Figure11GCPriors,
  },
  {
    slug: "overfitting",
    title: "Overfitting Diagnostics",
    subtitle: "Train/val divergence and parameter drift",
    blurb: "Validation degrades while NRTL regularization pressure rises and solubility share falls.",
    tags: ["overfit", "diagnostics", "tau"],
    component: Figure12Overfitting,
  },
  {
    slug: "comparison-table",
    title: "Comparison Table",
    subtitle: "Trade-offs across model families",
    blurb: "The deck can switch between a radar overlay and a matrix for slide-friendly comparison.",
    tags: ["comparison", "trade-offs", "positioning"],
    component: Figure13Comparison,
  },
  {
    slug: "master-equation",
    title: "Master Equation",
    subtitle: "`ln x₂ = -Φ - ln γ₂` as a picture",
    blurb: "Two interpretable penalties add on one axis, which makes prediction outputs explainable by construction.",
    tags: ["equation", "interpretability", "physics"],
    component: Figure14MasterEquation,
  },
  {
    slug: "solvent-screening",
    title: "Solvent Screening",
    subtitle: "Rank, filter, and turn solubility into process-facing solvent decisions",
    blurb: "The screening layer converts one checkpoint into ranked solvents, crystallization windows, antisolvents, and green replacements.",
    tags: ["applications", "screening", "solvents"],
    component: Figure15SolventScreening,
  },
  {
    slug: "process-optimization",
    title: "Process Optimization",
    subtitle: "Crystallization, extraction, reaction medium, and mixture design",
    blurb: "Process-oriented objectives sit on top of the same solvent-screening core and stay constraint-aware.",
    tags: ["applications", "process", "optimization"],
    component: Figure16ProcessOptimization,
  },
  {
    slug: "drug-developability",
    title: "Drug Developability",
    subtitle: "BCS-style solubility logic plus formulation-facing triage",
    blurb: "Aqueous solubility, pH correction, descriptor proxies, and crystal terms combine into a developability report.",
    tags: ["applications", "bcs", "formulation"],
    component: Figure17DrugDevelopability,
  },
  {
    slug: "pk-profile",
    title: "PK Solubility Profile",
    subtitle: "GI compartments, biorelevant media, IV vehicles, and topical screens",
    blurb: "The PK layer keeps claims solubility-first: useful upstream of PBPK, not a substitute for it.",
    tags: ["applications", "pk", "media"],
    component: Figure18PKProfile,
  },
];
