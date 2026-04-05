# Applications

TGNN-Solv is a solubility model first. The most defensible application layer is
therefore not "general chemistry AI", and not a full pharmacology simulator,
but decision support for workflows where explicit solvent and temperature
choices matter.

The maintained `Applications` workspace in the Experiment Lab exposes three
surfaces built around that principle:

- synthesis-route solvent screening
- developability and oral dose-pressure proxies
- solvent-swap / precipitation screening

## 1. Synthesis Route Screening

The route-facing workflow accepts a sequence of intermediates with:

- compound SMILES
- reaction temperature
- isolation temperature
- candidate solvents

For each step, the app scores solvents by whether they look:

- loadable at the hot endpoint
- significantly less soluble at the cold endpoint
- likely to create a useful temperature-swing crystallization window

This is deliberately narrower than retrosynthesis. The model is not planning
bond disconnections. Instead it acts as a solvent-selection layer inside a
human- or tool-designed route.

## 2. Developability and Oral Dose Proxies

The developability workflow uses water plus a few explicit formulation-relevant
solvent surrogates to answer questions like:

- does aqueous solubility look dose-limiting?
- how much cosolvent leverage exists relative to water?
- is the problem plausibly "preformulation-hard" rather than "hopeless in
  water only"?

The app reports:

- predicted `ln(x2)` and `x2`
- water-relative uplift
- an approximate aqueous molarity proxy
- a rough `250 mL` max-supported-dose proxy for water

That is intentionally framed as a proxy, not a full BCS or PBPK result.

## 3. PK / PD Scope

Equilibrium solubility is relevant to PK, but it is only one piece of the
chain. TGNN-Solv can support:

- preformulation solvent ranking
- precipitation and solvent-swap screening
- early oral dose-pressure heuristics

It does **not** directly predict:

- permeability
- dissolution kinetics
- precipitation in vivo
- metabolism or clearance
- distribution or exposure
- pharmacodynamics

So the right interpretation is:

- useful upstream of PK/PD models
- not a replacement for PK/PD models

## 4. Solvent-Swap and Workup Design

The solvent-swap screen looks at moving a compound from a donor solvent into a
poorer target medium and estimates how strong the crash-out pressure appears to
be. This is useful for:

- antisolvent ideas
- workup solvent exchange
- choosing between direct cooling and solvent-shift isolation

## 5. GUI Integration

Everything above is available in `Experiment Lab -> Applications`.

The app uses the same checkpoint-selection and inference-family logic as the
main inference workspace:

- `TGNN-Solv`
- `DirectGNN`

That means application screens can be compared across model families without
inventing a separate inference stack.

<div class="tgnn-page-nav" markdown="1">

## Related Pages

- [Evaluation & Inference](evaluation.md)
- [Experiment Lab](experiment_lab.md)
- [Architecture](architecture.md)
- [Results](results.md)

</div>
