import React, { useEffect, useId, useRef, useState } from "react";

function TexInline({ children }) {
  return <span className="tex-inline">{`\\(${children}\\)`}</span>;
}

function TexBlock({ children }) {
  return <div className="tex-block">{`\\[${children}\\]`}</div>;
}

const NOTES_BY_SLUG = {
  "data-pipeline": {
    summary: "What this slide means",
    content: (
      <>
        <p>
          The builder turns heterogeneous raw sources into one sparse supervision matrix. Conceptually the training set is
          a table <TexInline>{"\\mathcal D = \\{(s_i, v_i, T_i, y_i, z_i)\\}"}</TexInline>, where solubility
          <TexInline>{"y_i = \\ln x_{2,i}"}</TexInline> is dense but auxiliary targets <TexInline>{"z_i"}</TexInline> are mostly missing.
        </p>
        <p>
          The key visual point is that missingness is structural, not an error: each auxiliary column has a mask
          <TexInline>{"m_{ij} \\in \\{0,1\\}"}</TexInline>. The scaffold split then enforces that the same solute core does not appear in both train and test.
        </p>
      </>
    ),
    report: (
      <p>
        In report terms, this figure justifies why the training loop is multi-task but mask-aware. The model sees one
        merged schema, while every auxiliary head only contributes where the corresponding supervision bit is present,
        so sparsity becomes a planned design constraint rather than a data-quality failure.
      </p>
    ),
  },
  "molecular-featurization": {
    summary: "How SMILES becomes tensors",
    content: (
      <>
        <p>
          The molecule is first parsed into a graph <TexInline>{"G = (V, E)"}</TexInline>. Each atom gets a feature vector
          <TexInline>{"x_a \\in \\mathbb R^{35}"}</TexInline>, and each bond gets a feature vector
          <TexInline>{"e_{ab} \\in \\mathbb R^{8}"}</TexInline>.
        </p>
        <p>
          The interactive panel makes that mapping explicit: click an atom or bond, and the card on the right shows the
          corresponding symbolic features together with one small slice of the learned numeric representation.
        </p>
      </>
    ),
    report: (
      <p>
        The practical reason to show this explicitly is that every downstream claim about TGNN-Solv starts here. If the
        graph abstraction drops chemically relevant local cues, neither the solver nor auxiliary supervision can recover
        that information later, because they only operate on the encoded representation they receive.
      </p>
    ),
  },
  pretraining: {
    summary: "How Stage 0 works in this repository",
    content: (
      <>
        <p>
          `src/tgnn_solv/pretrain.py` implements a standalone pre-curriculum Stage 0. It is explicitly separate from
          Phase 1 in `trainer.py`: Stage 0 uses large SMILES collections, updates `model.gnn` and `model.readout` in
          place, and then discards its temporary heads before normal TGNN training begins.
        </p>
        <p>
          The code trains four objectives together: masked 2-hop subgraph reconstruction, masked bond-type prediction,
          RDKit descriptor regression, and graph-level contrastive learning. The combined objective is
          <TexInline>{"L = L_{atom} + 0.5L_{bond} + L_{prop} + 0.5L_{ctr}"}</TexInline> with default temperature
          <TexInline>{"\\tau = 0.1"}</TexInline>.
        </p>
      </>
    ),
    report: (
      <p>
        The intended payoff is not a separate benchmark, but a chemically sharper initialization for the main
        curriculum. Stage 0 teaches local topology, graph-level invariances, and descriptor-aligned global semantics
        before the architecture has to solve the much harder supervised SLE problem on sparse thermodynamic labels.
      </p>
    ),
  },
  architecture: {
    summary: "Where learning stops and physics starts",
    content: (
      <>
        <p>
          The encoder and interaction stack learn molecular representations, but the final prediction is not produced by
          a free MLP. Instead, the model assembles a pair state
          <TexInline>{"g_{pair} = [g_{sol} \\parallel g_{slv} \\parallel g_{sol}\\odot g_{slv} \\parallel |g_{sol}-g_{slv}|]"}</TexInline>
          and turns it into thermodynamic parameters.
        </p>
        <p>
          The red zone is the point of the architecture: once <TexInline>{"T_m, \\Delta H_{fus}, \\tau_{12}, \\tau_{21}, \\alpha"}</TexInline>
          are predicted, the hardcoded SLE solver determines <TexInline>{"\\ln x_2"}</TexInline>. That is the physics bottleneck.
        </p>
      </>
    ),
    report: (
      <p>
        That separation is the core modeling claim of the project. The network is allowed to learn latent chemistry, but
        it is not allowed to invent an unconstrained mapping from embeddings to solubility; instead it must explain the
        prediction through physically interpretable intermediate quantities.
      </p>
    ),
  },
  "sle-solver": {
    summary: "Why the iteration converges quickly",
    content: (
      <>
        <p>
          The solver applies a fixed-point map
          <TexBlock>{"x_2^{(k+1)} = \\lambda e^{-\\Phi - \\ln\\gamma_2(x_2^{(k)})} + (1-\\lambda)x_2^{(k)}"}</TexBlock>
          until the iterate stabilizes.
        </p>
        <p>
          The left panel is zoomed into the only region that matters numerically. Because the local slope is small,
          <TexInline>{"|g'(x_2^*)| \\ll 1"}</TexInline>, the orange cobweb contracts to the green root in a few steps.
        </p>
      </>
    ),
    report: (
      <p>
        The important reading is not the exact synthetic numbers, but the geometry of the map near the solution. A
        stable contraction means forward solve time stays low, implicit gradients become attractive, and the solver can
        remain a hardcoded layer instead of turning into another fragile learned recurrent block.
      </p>
    ),
  },
  "implicit-diff": {
    summary: "Why implicit gradients are preferred",
    content: (
      <>
        <p>
          Unrolled differentiation stores every solver step and backpropagates through the whole chain, which costs
          <TexInline>{"\\mathcal O(N)"}</TexInline> memory and multiplies many local Jacobians.
        </p>
        <p>
          Implicit differentiation instead uses the converged fixed point directly:
          <TexBlock>{"\\frac{d x_2^*}{d\\theta} = -\\frac{\\partial F / \\partial \\theta}{\\partial F / \\partial x_2^*}"}</TexBlock>
          so backward becomes a one-step correction around the solution.
        </p>
      </>
    ),
    report: (
      <p>
        In other words, the method trades iteration-history bookkeeping for local analytical structure at the solution.
        That reduces memory pressure, removes long chains of fragile Jacobian products, and matches the fact that only
        the converged root matters for the final loss.
      </p>
    ),
  },
  "loss-landscape": {
    summary: "What changed after the loss fix",
    content: (
      <>
        <p>
          Training optimizes a weighted sum <TexInline>{"L = \\sum_j \\lambda_j L_j"}</TexInline>. If one component dominates
          the total scale, the optimizer effectively ignores the rest.
        </p>
        <p>
          The left plot shows that `vant_hoff_local` was swallowing the objective; the right plot shows the intended regime,
          where solubility again owns most of the gradient budget and the auxiliary terms stay secondary.
        </p>
      </>
    ),
    report: (
      <p>
        This slide is therefore an optimization diagnosis, not only a cosmetic rebalance. If `L_sol` is numerically tiny
        compared with the rest, the model can appear to train while effectively not learning the target task that matters
        most for the paper, namely solubility prediction itself.
      </p>
    ),
  },
  "linear-probe": {
    summary: "How to read the probe scores",
    content: (
      <>
        <p>
          Each bar is a linear-probe score for one descriptor. The metric is
          <TexInline>{"R^2 = 1 - \\frac{\\sum (y - \\hat y)^2}{\\sum (y - \\bar y)^2}"}</TexInline>, so larger values mean
          the encoder retained that descriptor more faithfully.
        </p>
        <p>
          This slide argues that the present error gap is mostly representational. If a descriptor is only weakly recoverable
          from the encoder state, the downstream physics path never gets a clean enough starting point.
        </p>
      </>
    ),
    report: (
      <p>
        That is why the probe matters strategically. It separates a solver bottleneck from an encoder bottleneck: if the
        latent state does not linearly expose descriptor information that is known to be useful, improving the physics head
        alone will have limited payoff because the missing signal has already been lost upstream.
      </p>
    ),
  },
  "error-decomposition": {
    summary: "What the waterfall is attributing",
    content: (
      <>
        <p>
          The bars are additive gaps relative to the best descriptor baseline. In shorthand,
          <TexInline>{"\\Delta \\mathrm{MAE} = \\mathrm{MAE}_{model} - \\mathrm{MAE}_{RF}"}</TexInline>.
        </p>
        <p>
          The important interpretation is not the exact number on each bar, but the split of responsibility: most of the
          current degradation appears before the solver, inside the molecular representation itself.
        </p>
      </>
    ),
    report: (
      <p>
        Put differently, the waterfall turns a vague underperformance statement into an engineering prioritization. If the
        largest gap is representational, the next experiments should focus on encoder enrichment, descriptor augmentation,
        and pretraining rather than replacing the thermodynamic solver.
      </p>
    ),
  },
  "temperature-extrapolation": {
    summary: "Why the physics path extrapolates differently",
    content: (
      <>
        <p>
          Outside the observed temperature range, a generic tabular regressor often defaults toward local averages. The
          TGNN path remains structured because the solver imposes an explicit temperature law through <TexInline>{"\\Phi(T)"}</TexInline>.
        </p>
        <p>
          A useful mental model is the van't Hoff slope:
          <TexInline>{"\\frac{d\\ln x_2}{dT} \\approx \\frac{\\Delta H_{sol}}{RT^2}"}</TexInline>. The exact implementation is more detailed,
          but the key point is that temperature dependence is encoded, not guessed.
        </p>
      </>
    ),
    report: (
      <p>
        The slide is schematic on purpose: it communicates expected behavior, not a final benchmark panel. The message is
        that physics earns its keep precisely where interpolation ends, because the solver imposes a structured trend that
        remains meaningful beyond the temperatures seen during fitting.
      </p>
    ),
  },
  curriculum: {
    summary: "Why the schedule is staged",
    content: (
      <>
        <p>
          Early in training, the model is not ready to run the whole physics stack stably. Phase 1 therefore keeps
          solubility off, roughly as <TexInline>{"w_{sol}(t)=0"}</TexInline>, while property heads warm up.
        </p>
        <p>
          Phase 2 activates the full solver path, and Phase 3 lowers the learning rate for refinement. The visual point is
          that solver activation, correction unfreezing, and oracle annealing are coordinated rather than simultaneous.
        </p>
      </>
    ),
    report: (
      <p>
        This is effectively a stabilization protocol for a heterogeneous model. The schedule controls when fragile pieces
        are allowed to move, so the encoder, auxiliary heads, solver-facing parameters, and correction branch do not all
        start drifting before their upstream signals are even sensible.
      </p>
    ),
  },
  "gc-priors": {
    summary: "What the prior is buying you",
    content: (
      <>
        <p>
          Instead of predicting crystal properties from scratch, the model learns a bounded residual:
          <TexBlock>{"T_m = T_m^{GC} + \\delta, \\qquad |\\delta| \\le 50\\,K"}</TexBlock>
        </p>
        <p>
          That changes optimization geometry. The head no longer searches the full physically plausible interval; it only has
          to correct the prior locally, which is why the search window on the right is dramatically narrower.
        </p>
      </>
    ),
    report: (
      <p>
        From a training perspective, this is a variance-reduction device. A decent group-contribution anchor removes a
        large low-frequency burden from the crystal head, so learned capacity is spent on bounded residual structure instead
        of rediscovering first-order thermochemistry from sparse labels.
      </p>
    ),
  },
  overfitting: {
    summary: "How to read the overfitting signal",
    content: (
      <>
        <p>
          The three panels track validation quality, parameter drift, and objective balance together. The useful scalar is
          the best epoch
          <TexInline>{"t^* = \\arg\\min_t \\mathrm{MAE}_{val}(t)"}</TexInline>, which appears very early.
        </p>
        <p>
          After that point, train loss keeps improving, but validation stalls while <TexInline>{"\\tau_{reg}"}</TexInline> rises.
          That combination suggests the model is using extra freedom to fit training noise rather than improving physical generalization.
        </p>
      </>
    ),
    report: (
      <p>
        The three traces are shown together because no single metric is sufficient on its own. Validation MAE indicates
        usefulness, `tau_reg` indicates whether NRTL parameters are drifting into aggressive regimes, and `sol_fraction`
        shows whether the optimizer is still spending enough attention on the main target.
      </p>
    ),
  },
  "comparison-table": {
    summary: "How to interpret the positioning slide",
    content: (
      <>
        <p>
          This slide is not an absolute benchmark table; it is a compact trade-off view. Each model is summarized by a small score
          vector <TexInline>{"r \\in [0,4]^5"}</TexInline> over accuracy, extrapolation, interpretability, consistency, and speed.
        </p>
        <p>
          The radar view emphasizes geometry of trade-offs, while the matrix view emphasizes readability on dense slides.
          Both are meant to answer the same question: what is gained when physics is inserted into the prediction path?
        </p>
      </>
    ),
    report: (
      <p>
        This makes the slide useful in discussion, because it compresses a multi-objective argument into one panel. The
        intended conclusion is not that TGNN dominates every baseline on every axis today, but that it occupies a
        different operating point where interpretability and extrapolation are built into the prediction path.
      </p>
    ),
  },
  "master-equation": {
    summary: "The equation behind the whole model",
    content: (
      <>
        <p>
          The central decomposition is
          <TexBlock>{"\\ln x_2 = -\\Phi - \\ln\\gamma_2"}</TexBlock>
          where <TexInline>{"-\\Phi"}</TexInline> is the crystal-side melting penalty and
          <TexInline>{"-\\ln\\gamma_2"}</TexInline> is the solvent-side interaction penalty.
        </p>
        <p>
          The axis view is useful because both effects act on the same scalar coordinate. Equivalently,
          <TexInline>{"x_2 = \\exp(-\\Phi - \\ln\\gamma_2)"}</TexInline>, so either a worse crystal term or a worse interaction term
          pushes solubility downward in one additive log-space picture.
        </p>
      </>
    ),
    report: (
      <p>
        As a report summary, this is the cleanest mental model for TGNN-Solv. The network is learning two physically
        interpretable penalties whose sum determines the final prediction, which is exactly why the model can support
        explanation, diagnostics, and controlled extrapolation better than a direct black-box regressor.
      </p>
    ),
  },
};

const EXTRA_NOTES_BY_SLUG = {
  "data-pipeline": (
    <>
      <p>
        From an engineering perspective, this merged table is the reason the training code has to carry masks all the
        way into the loss. A row may supervise <TexInline>{"\\ln x_2"}</TexInline> only, crystal properties only, or a mixed subset,
        so the model is effectively trained on a partially observed multi-task matrix rather than on a clean dense label tensor.
      </p>
      <p>
        The split policy matters just as much as the merge policy. If related scaffolds leaked across train and test, the
        evaluation would partly measure memorization of chemotypes already seen during fitting, whereas the maintained scaffold
        split gives a harder but more defensible estimate of generalization to new solute cores.
      </p>
    </>
  ),
  "molecular-featurization": (
    <>
      <p>
        The key implementation detail is that the graph retains chemically typed local structure, not just connectivity. Atom
        tensors encode hybridization, charge, aromaticity, ring membership, and simple physicochemical scalars, while bond tensors
        preserve order, conjugation, ring status, and stereochemical flags.
      </p>
      <p>
        This is why the slide is interactive rather than decorative. The viewer can move directly from a visible atom or bond to the
        exact local representation that the encoder consumes, which turns the featurization step into something auditable instead of a
        hidden preprocessing black box.
      </p>
    </>
  ),
  pretraining: (
    <>
      <p>
        Stage 0 should be read as representation shaping, not as a replacement for the three-phase curriculum. It is designed to teach
        the encoder invariances and chemically meaningful summary signals before the supervised TGNN objectives begin competing for
        capacity on a much smaller and much sparser thermodynamic dataset.
      </p>
      <p>
        The four tasks are complementary in that they stress different scales of information. Masked subgraphs and bond prediction
        enforce local chemistry, descriptor regression enforces molecule-level semantics, and contrastive learning encourages stable
        graph summaries under mild perturbations of the same underlying molecule.
      </p>
    </>
  ),
  architecture: (
    <>
      <p>
        Weight sharing in the encoder is a deliberate constraint. Solute and solvent play different thermodynamic roles downstream,
        but the model still benefits from a common molecular representation language at the graph level, which keeps parameter count
        controlled and reduces the chance that each branch learns incompatible latent conventions.
      </p>
      <p>
        The more important architectural choice is where the model is not flexible. Once the learned modules emit solver-facing
        quantities, the prediction path becomes structured, which means later analysis can ask whether an error came from the encoder,
        from crystal-property estimation, from interaction parameters, or from the correction branch.
      </p>
    </>
  ),
  "sle-solver": (
    <>
      <p>
        In implementation terms, the fixed-point loop is the bridge between learned parameters and thermodynamic consistency. The
        network does not directly output solubility; instead it outputs quantities that define the map whose root corresponds to the
        physically admissible solution.
      </p>
      <p>
        That distinction matters for stability and interpretation. A direct regressor can always fit a number, but a structured solver
        can fail or contract depending on the local geometry, so this slide is really explaining why the maintained parameterization is
        numerically tame enough to keep the hardcoded layer practical.
      </p>
    </>
  ),
  "implicit-diff": (
    <>
      <p>
        The backward story is as important as the forward story here. If gradients were propagated only through a finite unroll, the
        result would depend on an arbitrary truncation horizon and would inherit all the instability of repeated Jacobian products over
        the iteration chain.
      </p>
      <p>
        Implicit differentiation instead treats the converged state as the object of interest. That matches the training objective more
        closely, because the loss depends on the settled solution <TexInline>{"x_2^*"}</TexInline>, not on the transient path the solver used to get
        there, and it explains why memory use can stay essentially constant in the number of solver steps.
      </p>
    </>
  ),
  "loss-landscape": (
    <>
      <p>
        The before/after comparison is therefore a diagnosis of effective objective weighting. Even if YAML weights look reasonable on
        paper, the optimizer only responds to the scale it actually sees after all reductions, masks, and batching effects have been
        applied inside the training loop.
      </p>
      <p>
        Once solubility regains the majority share of the total loss, the auxiliary terms return to their intended role: they regularize
        and stabilize representation learning without hijacking the experiment. That is why this slide belongs in a report about model
        behavior, not only in a debugging appendix.
      </p>
    </>
  ),
  "linear-probe": (
    <>
      <p>
        Linear probes are useful precisely because they are weak models. If a descriptor cannot be recovered linearly from the latent
        state, then the information is either missing or encoded in a far less accessible form than a downstream head would ideally need
        for robust prediction and transfer.
      </p>
      <p>
        The strategic implication is that descriptor augmentation and pretraining are not cosmetic add-ons. They are direct attempts to
        reduce the representational deficit exposed by the probe, which is why this slide connects naturally to both the pretraining
        slide and the descriptor-gap slides later in the deck.
      </p>
    </>
  ),
  "error-decomposition": (
    <>
      <p>
        The RF baseline is not presented as the final desired model family; it is used here as a high-signal reference point because it
        sees strong fixed descriptors directly. That makes it a practical way to separate chemistry-representation losses from later
        losses introduced by the physics bottleneck.
      </p>
      <p>
        In report terms, the waterfall is really a prioritization chart. If nearly all of the gap appears before the solver, then the
        next cycle of work should focus on richer graph representations, pretraining, or descriptor fusion before spending large effort
        on redesigning the thermodynamic layer.
      </p>
    </>
  ),
  "temperature-extrapolation": (
    <>
      <p>
        This panel should be read as an inductive-bias argument. A model without embedded temperature physics has no reason to preserve
        the qualitative shape of a solubility curve outside the observed window, whereas the TGNN path inherits a structured dependence
        through the solver-facing thermodynamic terms.
      </p>
      <p>
        The note about pending quantitative results is important. The purpose of the slide is to explain why the physics bottleneck is
        expected to help out-of-range behavior, not to overclaim measured superiority on a benchmark that the project has not yet fully
        finalized for this exact visualization.
      </p>
    </>
  ),
  curriculum: (
    <>
      <p>
        The schedule is effectively a control system for optimization difficulty. Different parts of the architecture have very
        different failure modes, so staggering their activation prevents early noise in one branch from destabilizing the rest of the
        model before any meaningful representation has formed.
      </p>
      <p>
        This also explains why the phases should not be collapsed into a single training regime by default. Simultaneous activation of
        solver, correction, auxiliary losses, and oracle-like supports would make it much harder to attribute improvements or failures to
        a specific mechanism during experiments.
      </p>
    </>
  ),
  "gc-priors": (
    <>
      <p>
        Bounded residual learning changes the optimization problem from global search to local correction. Instead of asking the crystal
        head to discover an entire physically plausible interval from sparse supervision, the model begins from a chemically motivated
        estimate and only learns how to shift it within a controlled band.
      </p>
      <p>
        The practical interpretation is that prior quality now matters in a measurable way. If the GC estimate is already close, the
        residual branch can focus on systematic bias; if it is poor, the bound still prevents the head from drifting into implausible
        values while the rest of the architecture continues training.
      </p>
    </>
  ),
  overfitting: (
    <>
      <p>
        A useful way to read this slide is as a three-signal consensus check. Validation MAE alone tells you when performance peaks,
        but not why; the auxiliary traces reveal whether the model is becoming too confident in aggressive NRTL settings or whether the
        loss budget is slowly shifting away from the main target.
      </p>
      <p>
        That is why early stopping in this project should be informed by diagnostics rather than by a single scalar alone. A small change
        in validation error might be easy to dismiss, but if it arrives together with rising regularization pressure and weakening
        solubility focus, the combined picture is much more convincing evidence of overfitting.
      </p>
    </>
  ),
  "comparison-table": (
    <>
      <p>
        The radar and matrix views are complementary communication tools rather than competing scientific claims. The radar emphasizes
        geometry and trade-off shape for presentations, while the matrix sacrifices some visual drama in exchange for cleaner reading when
        many model families must be compared at once.
      </p>
      <p>
        The underlying ratings are deliberately coarse. They should be interpreted as a positioning summary grounded in the repository’s
        current evidence and modeling intent, not as a substitute for the detailed benchmark tables and experiment logs elsewhere in the
        documentation and results folders.
      </p>
    </>
  ),
  "master-equation": (
    <>
      <p>
        The reason this decomposition is so useful is that it turns one prediction into two interpretable penalties. In log space,
        additive structure is especially convenient: a worse crystal term or a worse interaction term simply shifts the same scalar
        outcome leftward, making diagnosis and explanation far more direct.
      </p>
      <p>
        That also clarifies the project’s modeling philosophy. TGNN-Solv is not trying to learn an opaque map from molecules and
        temperature to solubility; it is trying to learn the physically meaningful ingredients whose sum determines solubility, which is
        why the architecture can support explanation and controlled extrapolation more naturally than a direct black-box predictor.
      </p>
    </>
  ),
};

function readInitialOpenState() {
  if (typeof window === "undefined") {
    return false;
  }
  const params = new URLSearchParams(window.location.search);
  return params.get("notes") === "1";
}

export function SlideNotes({ slug }) {
  const [isOpen, setIsOpen] = useState(readInitialOpenState);
  const contentRef = useRef(null);
  const panelId = useId();
  const note = NOTES_BY_SLUG[slug];
  const extra = EXTRA_NOTES_BY_SLUG[slug];

  useEffect(() => {
    setIsOpen(readInitialOpenState());
  }, [slug]);

  useEffect(() => {
    if (!isOpen || !contentRef.current || typeof window === "undefined") {
      return;
    }
    if (window.MathJax?.typesetPromise) {
      window.MathJax.typesetPromise([contentRef.current]).catch(() => {});
    }
  }, [isOpen, slug]);

  if (!note) {
    return null;
  }

  return (
    <section className={`slide-notes${isOpen ? " is-open" : ""}`}>
      <button
        type="button"
        className="slide-notes__toggle"
        aria-expanded={isOpen}
        aria-controls={panelId}
        onClick={() => setIsOpen((previous) => !previous)}
      >
        <span className="slide-notes__title">Slide Notes</span>
        <span className="slide-notes__summary">{note.summary}</span>
        <span className="slide-notes__chevron">{isOpen ? "Hide" : "Show"}</span>
      </button>
      {isOpen ? (
        <div id={panelId} ref={contentRef} className="slide-notes__content">
          <p className="slide-notes__lead">
            This note expands the slide into a short report section: what the figure is claiming, how it maps to the
            maintained TGNN-Solv implementation, and what conclusion the viewer should take away from it.
          </p>
          {note.content}
          {note.report}
          {extra}
        </div>
      ) : null}
    </section>
  );
}
