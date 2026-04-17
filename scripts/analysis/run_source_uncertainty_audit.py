#!/usr/bin/env python3
"""Audit BigSolDB source identifiers and assign source-level uncertainty priors."""

from __future__ import annotations

import argparse
import html
import json
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Any

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd
from rdkit import RDLogger

try:
    import requests
except Exception:  # pragma: no cover - optional at runtime
    requests = None

from tgnn_solv.data.source_uncertainty import (
    classify_source_method,
    looks_like_doi,
)
from tgnn_solv.data.sources import _process_bigsoldb_raw  # noqa: SLF001
from tgnn_solv.data.utils import RAW_DIR


DEFAULT_OVERRIDES = Path("notebooks/data/metadata/bigsoldb_source_method_overrides.csv")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build a reproducible source-level uncertainty map for the maintained "
            "BigSolDB supervised corpus. The audit preserves raw Source identifiers, "
            "computes source footprint diagnostics, optionally fetches DOI metadata, "
            "and exports heuristic method/sigma priors ready for manual review."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--raw-data",
        default=str(RAW_DIR / "BigSolDBv2.1.csv"),
        help="Raw BigSolDB CSV with the original Source column.",
    )
    parser.add_argument(
        "--out-dir",
        default="results/source_uncertainty_audit",
        help="Directory for generated audit artifacts.",
    )
    parser.add_argument(
        "--overrides",
        default=str(DEFAULT_OVERRIDES),
        help="CSV with manual source -> method/sigma overrides.",
    )
    parser.add_argument(
        "--top-manual-k",
        type=int,
        default=250,
        help="How many largest sources to export for manual review.",
    )
    parser.add_argument(
        "--fetch-metadata-limit",
        type=int,
        default=120,
        help=(
            "Fetch DOI metadata for the top-K sources by maintained row count. "
            "Use 0 to disable network metadata enrichment."
        ),
    )
    parser.add_argument(
        "--metadata-csv",
        default="",
        help=(
            "Optional pre-fetched source metadata CSV to reuse instead of issuing "
            "network requests. If provided, it must contain at least the `source` "
            "column and any subset of title/journal/abstract/OA fields."
        ),
    )
    parser.add_argument(
        "--metadata-sleep-seconds",
        type=float,
        default=0.05,
        help="Small pause between metadata requests.",
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=20.0,
        help="Timeout in seconds for metadata HTTP calls.",
    )
    parser.add_argument(
        "--unpaywall-email",
        default="",
        help=(
            "Optional real email address for Unpaywall OA lookups. "
            "Leave empty to skip Unpaywall."
        ),
    )
    return parser


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_ready(v) for v in value]
    if isinstance(value, tuple):
        return [_json_ready(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        numeric = float(value)
        return numeric if np.isfinite(numeric) else None
    return value


def _ensure_override_file(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        columns=[
            "source",
            "method",
            "sigma_ln_x2",
            "confidence",
            "rationale",
            "reviewer",
            "notes",
        ]
    ).to_csv(path, index=False)


def _load_overrides(path: Path) -> pd.DataFrame:
    _ensure_override_file(path)
    overrides = pd.read_csv(path, low_memory=False)
    if overrides.empty:
        return overrides
    overrides["source"] = overrides["source"].astype(str).str.strip()
    overrides = overrides.loc[overrides["source"].astype(bool)].copy()
    return overrides


def _coverage_rows(counts: pd.Series) -> pd.DataFrame:
    coverage_points = (10, 20, 30, 50, 100, 200, 500, 1000)
    total = float(counts.sum())
    rows: list[dict[str, Any]] = []
    running = counts.cumsum()
    for top_k in coverage_points:
        if top_k > len(counts):
            continue
        covered = float(running.iloc[top_k - 1])
        rows.append(
            {
                "top_k_sources": int(top_k),
                "covered_rows": int(covered),
                "coverage_fraction": covered / total if total else float("nan"),
            }
        )
    return pd.DataFrame(rows)


def _decode_openalex_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    if not inverted_index:
        return None
    max_pos = max(pos for positions in inverted_index.values() for pos in positions)
    tokens: list[str | None] = [None] * (max_pos + 1)
    for token, positions in inverted_index.items():
        for pos in positions:
            tokens[pos] = token
    text = " ".join(token for token in tokens if token)
    return text or None


def _fetch_source_metadata(
    doi: str,
    *,
    timeout: float,
    unpaywall_email: str = "",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source": doi,
        "title": None,
        "journal": None,
        "abstract": None,
        "oa_pdf_url": None,
        "is_oa": None,
        "metadata_provider": "none",
        "metadata_status": "not_fetched",
    }
    if requests is None or not looks_like_doi(doi):
        return payload

    try:
        semantic_url = (
            "https://api.semanticscholar.org/graph/v1/paper/DOI:"
            f"{doi}?fields=title,abstract,venue,openAccessPdf,year,externalIds"
        )
        response = requests.get(
            semantic_url,
            headers={"User-Agent": "TGNN-Solv/1.0"},
            timeout=timeout,
        )
        if response.ok:
            message = response.json()
            open_access_pdf = message.get("openAccessPdf") or {}
            payload.update(
                {
                    "title": html.unescape(str(message.get("title") or "")) or None,
                    "journal": html.unescape(str(message.get("venue") or "")) or None,
                    "abstract": html.unescape(str(message.get("abstract") or "")).strip() or None,
                    "oa_pdf_url": open_access_pdf.get("url"),
                    "is_oa": bool(open_access_pdf.get("url")) if open_access_pdf else None,
                    "metadata_provider": "semanticscholar",
                    "metadata_status": "ok",
                }
            )
            if payload["title"] or payload["journal"] or payload["abstract"]:
                return payload
        payload["metadata_status"] = f"semanticscholar_http_{response.status_code}"
    except Exception as exc:  # pragma: no cover - network/runtime dependent
        payload["metadata_status"] = f"semanticscholar_error:{type(exc).__name__}"

    try:
        openalex_url = "https://api.openalex.org/works/https://doi.org/" + urllib.parse.quote(
            doi,
            safe="",
        )
        response = requests.get(
            openalex_url,
            headers={"User-Agent": "TGNN-Solv/1.0"},
            timeout=timeout,
        )
        if response.ok:
            message = response.json()
            payload.update(
                {
                    "title": payload["title"] or html.unescape(str(message.get("title") or "")) or None,
                    "journal": payload["journal"]
                    or html.unescape(
                        str((message.get("primary_location") or {}).get("source", {}).get("display_name") or "")
                    )
                    or None,
                    "abstract": payload["abstract"]
                    or _decode_openalex_abstract(message.get("abstract_inverted_index")),
                    "oa_pdf_url": payload["oa_pdf_url"]
                    or ((message.get("open_access") or {}).get("oa_url")),
                    "is_oa": payload["is_oa"]
                    if payload["is_oa"] is not None
                    else (message.get("open_access") or {}).get("is_oa"),
                    "metadata_provider": "openalex"
                    if payload["metadata_provider"] == "none"
                    else payload["metadata_provider"],
                    "metadata_status": "ok",
                }
            )
            if payload["title"] or payload["journal"] or payload["abstract"]:
                return payload
        payload["metadata_status"] = f"openalex_http_{response.status_code}"
    except Exception as exc:  # pragma: no cover - network/runtime dependent
        payload["metadata_status"] = f"openalex_error:{type(exc).__name__}"

    try:
        crossref_url = f"https://api.crossref.org/works/{doi}"
        response = requests.get(
            crossref_url,
            headers={"User-Agent": "TGNN-Solv/1.0"},
            timeout=timeout,
        )
        if response.ok:
            message = response.json().get("message", {})
            payload.update(
                {
                    "title": payload["title"]
                    or html.unescape(" ".join(message.get("title", [])[:1]).strip())
                    or None,
                    "journal": payload["journal"]
                    or html.unescape(" ".join(message.get("container-title", [])[:1]).strip())
                    or None,
                    "abstract": payload["abstract"]
                    or html.unescape(str(message.get("abstract") or "")).strip()
                    or None,
                    "metadata_provider": "crossref"
                    if payload["metadata_provider"] == "none"
                    else payload["metadata_provider"],
                    "metadata_status": "ok",
                }
            )
            return payload
        payload["metadata_status"] = f"crossref_http_{response.status_code}"
    except Exception as exc:  # pragma: no cover - network/runtime dependent
        payload["metadata_status"] = f"crossref_error:{type(exc).__name__}"

    if unpaywall_email.strip():
        try:
            unpaywall_url = (
                "https://api.unpaywall.org/v2/"
                + urllib.parse.quote(doi, safe="")
                + f"?email={urllib.parse.quote(unpaywall_email.strip(), safe='@._+-')}"
            )
            response = requests.get(
                unpaywall_url,
                headers={"User-Agent": "TGNN-Solv/1.0"},
                timeout=timeout,
            )
            if response.ok:
                message = response.json()
                best_oa = message.get("best_oa_location") or {}
                payload.update(
                    {
                        "oa_pdf_url": payload["oa_pdf_url"]
                        or best_oa.get("url_for_pdf")
                        or best_oa.get("url"),
                        "is_oa": payload["is_oa"]
                        if payload["is_oa"] is not None
                        else message.get("is_oa"),
                        "metadata_provider": payload["metadata_provider"]
                        if payload["metadata_provider"] != "none"
                        else "unpaywall",
                        "metadata_status": "ok"
                        if payload["metadata_status"] == "not_fetched"
                        else payload["metadata_status"],
                    }
                )
            elif payload["metadata_status"] == "not_fetched":
                payload["metadata_status"] = f"unpaywall_http_{response.status_code}"
        except Exception as exc:  # pragma: no cover - network/runtime dependent
            if payload["metadata_status"] == "not_fetched":
                payload["metadata_status"] = f"unpaywall_error:{type(exc).__name__}"
    return payload


def _pair_key_frame(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["pair_key"] = (
        work["solute_smiles"].astype(str) + "||" + work["solvent_smiles"].astype(str)
    )
    return work


def _pair_step_stats(group: pd.DataFrame) -> tuple[float, float]:
    step_medians: list[float] = []
    uniform_flags: list[int] = []
    for _, pair_df in group.groupby("pair_key", sort=False):
        temps = np.sort(pair_df["temperature"].astype(float).unique())
        if temps.size < 3:
            continue
        steps = np.diff(temps)
        if steps.size == 0:
            continue
        step_medians.append(float(np.median(steps)))
        mean_step = float(np.mean(steps))
        if mean_step <= 0:
            uniform_flags.append(0)
            continue
        cv = float(np.std(steps) / mean_step)
        uniform_flags.append(int(cv <= 0.15))
    if not step_medians:
        return float("nan"), float("nan")
    return float(np.median(step_medians)), float(np.mean(uniform_flags))


def _vant_hoff_rmse_stats(group: pd.DataFrame) -> tuple[int, float, float]:
    rmses: list[float] = []
    for _, pair_df in group.groupby("pair_key", sort=False):
        work = (
            pair_df[["temperature", "ln_x2"]]
            .dropna()
            .drop_duplicates(subset=["temperature"], keep="first")
            .sort_values("temperature")
        )
        if len(work) < 3:
            continue
        inv_t = 1.0 / work["temperature"].to_numpy(dtype=float)
        ln_x2 = work["ln_x2"].to_numpy(dtype=float)
        if len(np.unique(inv_t)) < 2:
            continue
        coeff = np.polyfit(inv_t, ln_x2, deg=1)
        pred = coeff[0] * inv_t + coeff[1]
        rmse = float(np.sqrt(np.mean((pred - ln_x2) ** 2)))
        if np.isfinite(rmse):
            rmses.append(rmse)
    if not rmses:
        return 0, float("nan"), float("nan")
    arr = np.asarray(rmses, dtype=float)
    return int(arr.size), float(arr.mean()), float(np.median(arr))


def _build_source_summary(supervised_df: pd.DataFrame) -> pd.DataFrame:
    work = _pair_key_frame(supervised_df)
    counts = work["source"].value_counts()
    total_rows = float(len(work))
    rows: list[dict[str, Any]] = []
    for source, group in work.groupby("source", sort=False):
        temps_per_pair = group.groupby("pair_key")["temperature"].nunique()
        median_pair_step, fraction_uniform_step_pairs = _pair_step_stats(group)
        n_vant_hoff_pairs, mean_vh_rmse, median_vh_rmse = _vant_hoff_rmse_stats(group)
        n_rows = int(len(group))
        rows.append(
            {
                "source": str(source),
                "n_rows": n_rows,
                "coverage_fraction": n_rows / total_rows if total_rows else float("nan"),
                "row_rank": int(counts.index.get_loc(source) + 1),
                "unique_solutes": int(group["solute_smiles"].astype(str).nunique()),
                "unique_solvents": int(group["solvent_smiles"].astype(str).nunique()),
                "unique_pairs": int(group["pair_key"].nunique()),
                "mean_temps_per_pair": float(temps_per_pair.mean()),
                "median_temps_per_pair": float(temps_per_pair.median()),
                "fraction_pairs_multi_temp": float((temps_per_pair >= 2).mean()),
                "fraction_pairs_ge5_temps": float((temps_per_pair >= 5).mean()),
                "fraction_rows_at_298_15": float(
                    np.isclose(
                        group["temperature"].to_numpy(dtype=float),
                        298.15,
                        atol=1e-3,
                    ).mean()
                ),
                "median_pair_temp_step": median_pair_step,
                "fraction_uniform_step_pairs": fraction_uniform_step_pairs,
                "n_vant_hoff_pairs": int(n_vant_hoff_pairs),
                "mean_vant_hoff_rmse": mean_vh_rmse,
                "median_vant_hoff_rmse": median_vh_rmse,
            }
        )
    return pd.DataFrame(rows).sort_values(["n_rows", "source"], ascending=[False, True]).reset_index(drop=True)


def _fetch_metadata_for_sources(
    source_summary: pd.DataFrame,
    *,
    limit: int,
    timeout: float,
    sleep_seconds: float,
    unpaywall_email: str,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if limit <= 0:
        return pd.DataFrame(
            columns=[
                "source",
                "title",
                "journal",
                "abstract",
                "oa_pdf_url",
                "is_oa",
                "metadata_provider",
                "metadata_status",
            ]
        )
    fetch_sources = source_summary.head(limit)["source"].astype(str).tolist()
    for source in fetch_sources:
        rows.append(
            _fetch_source_metadata(
                source,
                timeout=timeout,
                unpaywall_email=unpaywall_email,
            )
        )
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)
    return pd.DataFrame(rows)


def _load_or_fetch_metadata(
    *,
    metadata_csv: str,
    source_summary: pd.DataFrame,
    limit: int,
    timeout: float,
    sleep_seconds: float,
    unpaywall_email: str,
) -> pd.DataFrame:
    expected_cols = [
        "source",
        "title",
        "journal",
        "abstract",
        "oa_pdf_url",
        "is_oa",
        "metadata_provider",
        "metadata_status",
    ]
    if str(metadata_csv).strip():
        metadata_path = Path(str(metadata_csv).strip())
        metadata_df = pd.read_csv(metadata_path, low_memory=False)
        for col in expected_cols:
            if col not in metadata_df.columns:
                metadata_df[col] = np.nan
        return metadata_df[expected_cols].copy()
    return _fetch_metadata_for_sources(
        source_summary,
        limit=limit,
        timeout=timeout,
        sleep_seconds=sleep_seconds,
        unpaywall_email=unpaywall_email,
    )


def _build_classification_table(
    source_summary: pd.DataFrame,
    metadata_df: pd.DataFrame,
    overrides_df: pd.DataFrame,
) -> pd.DataFrame:
    merged = source_summary.merge(metadata_df, on="source", how="left")
    if overrides_df.empty:
        overrides = pd.DataFrame(
            columns=[
                "source",
                "override_method",
                "override_sigma_ln_x2",
                "override_confidence",
                "override_rationale",
            ]
        )
    else:
        overrides = overrides_df.rename(
            columns={
                "method": "override_method",
                "sigma_ln_x2": "override_sigma_ln_x2",
                "confidence": "override_confidence",
                "rationale": "override_rationale",
            }
        )
    merged = merged.merge(overrides, on="source", how="left")

    classifications: list[dict[str, Any]] = []
    for row in merged.to_dict(orient="records"):
        classified = classify_source_method(
            source=row.get("source"),
            title=row.get("title"),
            journal=row.get("journal"),
            abstract=row.get("abstract"),
            stats=row,
            override_method=row.get("override_method"),
            override_sigma_ln_x2=row.get("override_sigma_ln_x2"),
            override_confidence=row.get("override_confidence"),
            override_rationale=row.get("override_rationale"),
        )
        classifications.append(classified)

    classified_df = pd.concat(
        [merged.reset_index(drop=True), pd.DataFrame(classifications)],
        axis=1,
    )
    classified_df["has_metadata_title"] = classified_df["title"].notna()
    classified_df["has_metadata_abstract"] = classified_df["abstract"].notna()
    classified_df["override_used"] = classified_df["heuristic_level"].eq("manual_override")
    return classified_df


def _build_manual_review_table(classified_df: pd.DataFrame, top_k: int) -> pd.DataFrame:
    columns = [
        "source",
        "n_rows",
        "coverage_fraction",
        "row_rank",
        "title",
        "journal",
        "method_guess",
        "sigma_ln_x2_guess",
        "confidence",
        "heuristic_level",
        "rationale",
        "override_used",
        "unique_solutes",
        "unique_solvents",
        "unique_pairs",
        "median_temps_per_pair",
        "fraction_pairs_ge5_temps",
        "fraction_rows_at_298_15",
        "mean_vant_hoff_rmse",
        "median_vant_hoff_rmse",
    ]
    return classified_df.head(top_k)[columns].copy()


def _write_summary_markdown(
    *,
    out_path: Path,
    rows_supervised: int,
    unique_sources: int,
    coverage_df: pd.DataFrame,
    classified_df: pd.DataFrame,
    metadata_df: pd.DataFrame,
    overrides_path: Path,
) -> None:
    method_rows = (
        classified_df.groupby("method_guess", dropna=False)["n_rows"]
        .sum()
        .sort_values(ascending=False)
    )
    lines = [
        "# Source Uncertainty Audit",
        "",
        f"- Maintained supervised rows: `{rows_supervised:,}`",
        f"- Unique detailed sources: `{unique_sources:,}`",
        f"- Override file: `{overrides_path}`",
    ]
    if not coverage_df.empty:
        lines.append("- Source concentration:")
        for row in coverage_df.itertuples(index=False):
            lines.append(
                f"  - top `{row.top_k_sources}` sources cover "
                f"`{row.coverage_fraction * 100:.2f}%` of maintained rows"
            )
    lines.extend(
        [
            f"- Metadata fetched for `{len(metadata_df):,}` sources",
            f"- Sources with metadata titles: `{int(classified_df['has_metadata_title'].sum()):,}`",
            f"- Sources with metadata abstracts: `{int(classified_df['has_metadata_abstract'].sum()):,}`",
            "",
            "## Row-weighted method mix",
            "",
        ]
    )
    for method, n_rows in method_rows.items():
        lines.append(
            f"- `{method}`: `{int(n_rows):,}` rows "
            f"(`{100.0 * n_rows / max(rows_supervised, 1):.2f}%`)"
        )
    lines.extend(
        [
            "",
            "## Key interpretation",
            "",
            "- `Source` is highly fragmented in raw BigSolDB; manual review of only the top-50 sources is not enough.",
            "- The exported source-level sigma map is a source prior, not a literal pointwise experimental error bar.",
            "- Pattern diagnostics use per-pair van't Hoff smoothness, not raw within-pair standard deviation, to avoid mixing temperature trends with measurement noise.",
        ]
    )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = build_parser().parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_df = pd.read_csv(Path(args.raw_data), low_memory=False)
    RDLogger.DisableLog("rdApp.error")
    try:
        supervised_df = _process_bigsoldb_raw(
            raw_df,
            preserve_source_detail=True,
        ).reset_index(drop=True)
    finally:
        RDLogger.EnableLog("rdApp.error")
    source_summary = _build_source_summary(supervised_df)
    coverage_df = _coverage_rows(source_summary["n_rows"])
    source_summary.to_csv(out_dir / "source_summary.csv", index=False)
    coverage_df.to_csv(out_dir / "source_coverage.csv", index=False)

    metadata_df = _load_or_fetch_metadata(
        metadata_csv=str(args.metadata_csv),
        source_summary=source_summary,
        limit=args.fetch_metadata_limit,
        timeout=args.request_timeout,
        sleep_seconds=args.metadata_sleep_seconds,
        unpaywall_email=args.unpaywall_email,
    )
    metadata_out = out_dir / "source_metadata.csv"
    metadata_df.to_csv(metadata_out, index=False)

    overrides_path = Path(args.overrides)
    overrides_df = _load_overrides(overrides_path)
    classified_df = _build_classification_table(
        source_summary=source_summary,
        metadata_df=metadata_df,
        overrides_df=overrides_df,
    )
    manual_review_df = _build_manual_review_table(classified_df, top_k=args.top_manual_k)

    classified_df.to_csv(out_dir / "source_method_candidates.csv", index=False)
    manual_review_df.to_csv(out_dir / "top_sources_manual_review.csv", index=False)

    row_level_df = supervised_df.merge(
        classified_df[
            [
                "source",
                "method_guess",
                "sigma_ln_x2_guess",
                "confidence",
                "heuristic_level",
                "rationale",
            ]
        ],
        on="source",
        how="left",
    )
    row_level_df.to_csv(out_dir / "supervised_rows_with_source_uncertainty.csv", index=False)

    summary = {
        "raw_rows": int(len(raw_df)),
        "supervised_rows": int(len(supervised_df)),
        "unique_sources": int(source_summary["source"].nunique()),
        "top_k_coverage": {
            str(int(row.top_k_sources)): float(row.coverage_fraction)
            for row in coverage_df.itertuples(index=False)
        },
        "metadata_fetch_limit": int(args.fetch_metadata_limit),
        "metadata_rows": int(len(metadata_df)),
        "metadata_with_title": int(classified_df["has_metadata_title"].sum()),
        "metadata_with_abstract": int(classified_df["has_metadata_abstract"].sum()),
        "override_rows": int(len(overrides_df)),
        "row_weighted_method_mix": {
            str(method): int(n_rows)
            for method, n_rows in (
                classified_df.groupby("method_guess", dropna=False)["n_rows"]
                .sum()
                .sort_values(ascending=False)
                .items()
            )
        },
        "source_weighted_method_mix": {
            str(method): int(count)
            for method, count in (
                classified_df["method_guess"]
                .fillna("unknown")
                .value_counts()
                .items()
            )
        },
        "top_manual_review_rows": int(len(manual_review_df)),
        "artifacts": {
            "source_summary_csv": str(out_dir / "source_summary.csv"),
            "source_coverage_csv": str(out_dir / "source_coverage.csv"),
            "source_metadata_csv": str(metadata_out),
            "source_method_candidates_csv": str(out_dir / "source_method_candidates.csv"),
            "top_sources_manual_review_csv": str(out_dir / "top_sources_manual_review.csv"),
            "row_level_uncertainty_csv": str(out_dir / "supervised_rows_with_source_uncertainty.csv"),
            "summary_md": str(out_dir / "SUMMARY.md"),
            "summary_json": str(out_dir / "summary.json"),
        },
    }
    (out_dir / "summary.json").write_text(
        json.dumps(_json_ready(summary), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _write_summary_markdown(
        out_path=out_dir / "SUMMARY.md",
        rows_supervised=len(supervised_df),
        unique_sources=int(source_summary["source"].nunique()),
        coverage_df=coverage_df,
        classified_df=classified_df,
        metadata_df=metadata_df,
        overrides_path=overrides_path,
    )


if __name__ == "__main__":
    main()
