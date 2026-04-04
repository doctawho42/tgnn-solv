import React, { createContext, useContext, useEffect, useState } from "react";

const FALLBACK_PRESENTATION_DATA = {
  meta: {
    source: "fallback",
    generatedAt: null,
  },
  pipeline: {
    total_rows: 120197,
    total_rows_label: "120.2k",
    solubility_rows: 101763,
    solubility_rows_label: "101.8k",
    unique_solutes: 19878,
    split_rows: { train: 104625, val: 7785, test: 7787 },
    split_rows_label: { train: "104.6k", val: "7.8k", test: "7.8k" },
    split_solubility_rows: { train: 90808, val: 5385, test: 5570 },
    split_solubility_rows_label: { train: "90.8k", val: "5.4k", test: "5.6k" },
    ratios: { train: 0.8, val: 0.1, test: 0.1 },
    missing_fraction_aux: 0.8496,
    missing_fraction_aux_label: "85.0%",
    scaffold_overlap: 0,
    scaffolds: {
      train: null,
      test: null,
    },
    preview_rows: [
      {
        sample: "Paracetamol",
        solute_smiles: "CC(=O)Nc1ccc(O)…",
        solvent_smiles: "CCO",
        T: "293",
        ln_x2: "-2.99",
        T_m: "442",
        dH_fus: "26.4",
        delta_hansen: "18.5/10.2/14.1",
        gamma_inf: "—",
        source: "BigSolDBv2.1",
      },
      {
        sample: "1-nitronaphthalene",
        solute_smiles: "O=[N+]([O-])c1…",
        solvent_smiles: "CCO",
        T: "298",
        ln_x2: "-3.59",
        T_m: "608",
        dH_fus: "—",
        delta_hansen: "—",
        gamma_inf: "—",
        source: "BigSolDBv2.1",
      },
      {
        sample: "Ethylene glycol monoeicosate",
        solute_smiles: "CCCCCCCCCCCCCCCC…",
        solvent_smiles: "CCO",
        T: "311",
        ln_x2: "-7.42",
        T_m: "—",
        dH_fus: "—",
        delta_hansen: "—",
        gamma_inf: "—",
        source: "BigSolDBv2.1",
      },
      {
        sample: "aux_only",
        solute_smiles: "O=[N+]([O-])c1…",
        solvent_smiles: "O",
        T: "298",
        ln_x2: "—",
        T_m: "638",
        dH_fus: "—",
        delta_hansen: "—",
        gamma_inf: "—",
        source: "aux_only",
      },
    ],
  },
  linear_probe: {
    descriptors: [
      { name: "FractionCSP3", value: 0.93 },
      { name: "NumHDonors", value: 0.69 },
      { name: "TPSA", value: 0.65 },
      { name: "NumHAcceptors", value: 0.62 },
      { name: "MolLogP", value: 0.61 },
      { name: "NumRotatableBonds", value: 0.6 },
      { name: "RingCount", value: 0.57 },
      { name: "MolWt", value: 0.45 },
      { name: "HeavyAtomCount", value: 0.44 },
      { name: "MolMR", value: 0.42 },
    ],
    median_r2: 0.5045652389526367,
    median_r2_label: "0.505",
    total_descriptors: 208,
    counts: {
      ge_0_8: 3,
      between_0_5_and_0_8: 104,
      lt_0_5: 101,
    },
  },
};

const PresentationDataContext = createContext(FALLBACK_PRESENTATION_DATA);

export function PresentationDataProvider({ children }) {
  const [data, setData] = useState(FALLBACK_PRESENTATION_DATA);

  useEffect(() => {
    let cancelled = false;

    async function loadData() {
      try {
        const response = await fetch("../assets/data/tgnn-presentation-data.json", {
          cache: "no-store",
        });
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const payload = await response.json();
        if (!cancelled) {
          setData(mergePresentationData(FALLBACK_PRESENTATION_DATA, payload));
        }
      } catch {
        if (!cancelled) {
          setData(FALLBACK_PRESENTATION_DATA);
        }
      }
    }

    loadData();
    return () => {
      cancelled = true;
    };
  }, []);

  return <PresentationDataContext.Provider value={data}>{children}</PresentationDataContext.Provider>;
}

export function usePresentationData() {
  return useContext(PresentationDataContext);
}

function mergePresentationData(base, payload) {
  return {
    ...base,
    ...payload,
    meta: {
      source: payload ? "manifest" : base.meta.source,
      generatedAt: payload?.generated_at ?? payload?.meta?.generatedAt ?? base.meta.generatedAt,
    },
    pipeline: {
      ...base.pipeline,
      ...payload?.pipeline,
      split_rows: {
        ...base.pipeline.split_rows,
        ...payload?.pipeline?.split_rows,
      },
      split_rows_label: {
        ...base.pipeline.split_rows_label,
        ...payload?.pipeline?.split_rows_label,
      },
      split_solubility_rows: {
        ...base.pipeline.split_solubility_rows,
        ...payload?.pipeline?.split_solubility_rows,
      },
      split_solubility_rows_label: {
        ...base.pipeline.split_solubility_rows_label,
        ...payload?.pipeline?.split_solubility_rows_label,
      },
      ratios: {
        ...base.pipeline.ratios,
        ...payload?.pipeline?.ratios,
      },
      scaffolds: {
        ...base.pipeline.scaffolds,
        ...payload?.pipeline?.scaffolds,
      },
      preview_rows: payload?.pipeline?.preview_rows ?? base.pipeline.preview_rows,
    },
    linear_probe: {
      ...base.linear_probe,
      ...payload?.linear_probe,
      counts: {
        ...base.linear_probe.counts,
        ...payload?.linear_probe?.counts,
      },
      descriptors: payload?.linear_probe?.descriptors ?? base.linear_probe.descriptors,
    },
  };
}
