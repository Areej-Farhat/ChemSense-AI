"""ChemSense AI: a beginner-friendly electrochemical graph explainer."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scipy.signal import find_peaks, savgol_filter

APP_DIR = Path(__file__).parent
SAMPLE_DIR = APP_DIR / "sample_data"

SAMPLE_OPTIONS = {
    "Cyclic voltammetry (potential vs current)": SAMPLE_DIR / "cyclic_voltammetry_sample.csv",
    "Chronoamperometry (time vs current)": SAMPLE_DIR / "chronoamperometry_sample.csv",
}
TGA_SAMPLE_PATH = SAMPLE_DIR / "tga_sample.csv"

POTENTIAL_HINTS = ("potential", "voltage", "volt", "e_we", "ewe", "e / v", "e/v")
TIME_HINTS = ("time", "t / s", "t/s", "seconds")
CURRENT_HINTS = ("current", "amp", "i /", "i/", "i_a", "ua", "ma")
TEMPERATURE_HINTS = ("temperature", "temp")
WEIGHT_HINTS = ("weight", "mass")


def main() -> None:
    st.set_page_config(
        page_title="ChemSense AI",
        page_icon="⚗️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_styles()

    st.title("ChemSense AI")
    st.caption("Upload CV or TGA data, see the graph, and get a simple scientific explanation.")

    with st.sidebar:
        st.header("Get started")
        st.write(
            "You can try the app with a built-in example, or upload your own CSV file "
            "from Excel, Google Sheets, or lab software."
        )
        experiment_choice = st.radio(
            "Experiment type",
            ("Cyclic Voltammetry (CV)", "Thermogravimetric Analysis (TGA)"),
        )
        is_tga = experiment_choice.startswith("Thermogravimetric")
        source = st.radio(
            "Choose data source",
            ("Use the built-in sample dataset", "Upload my own CSV file"),
        )

        dataframe = None
        source_label = ""

        if source == "Use the built-in sample dataset":
            if is_tga:
                sample_path = TGA_SAMPLE_PATH
                sample_name = "TGA sample (weight vs temperature)"
            else:
                sample_name = st.selectbox("Sample experiment", list(SAMPLE_OPTIONS.keys()))
                sample_path = SAMPLE_OPTIONS[sample_name]
            if not sample_path.exists():
                st.error("The sample file is missing. Please keep the sample_data folder in this project.")
                st.stop()
            dataframe = load_tga_csv(sample_path) if is_tga else load_csv(sample_path)
            source_label = sample_name
            st.success("Sample data loaded. You can explore the graph on the right.")
        else:
            uploaded = st.file_uploader("Upload a CSV file", type=["csv"])
            if uploaded is None:
                st.info("No file yet. Upload a CSV, or switch back to the sample dataset.")
            else:
                try:
                    dataframe = load_tga_csv(uploaded) if is_tga else load_csv(uploaded)
                    source_label = uploaded.name
                except Exception:
                    st.error(
                        "ChemSense AI could not read that file. For CV, save a CSV with a header row. "
                        "For TGA, title rows and unit rows are OK — the app looks for Temperature and Weight columns."
                    )
                    st.stop()

        st.divider()
        st.subheader("How to use")
        st.markdown(
            """
1. Choose CV or TGA.
2. Load sample data or upload a CSV.
3. Confirm the X and Y columns.
4. Read the graph and the explanation.
            """
        )
        st.caption("Tip: a CSV is a spreadsheet saved with commas between values.")

    if dataframe is None:
        show_welcome()
        return

    numeric_columns = list(dataframe.select_dtypes(include="number").columns)
    if len(numeric_columns) < 2:
        needed = "Temperature and Weight" if is_tga else "Potential and Current"
        st.error(
            f"This file needs at least two numeric columns, such as {needed}. "
            "Open it in Excel and check that the numbers were not saved as text."
        )
        st.stop()

    if is_tga:
        guessed_x, guessed_y = guess_tga_axes(numeric_columns)
        experiment_type = "tga"
        x_axis_label = "X axis (usually Temperature (°C))"
        y_axis_label = "Y axis (usually Weight (%))"
        x_key, y_key = "tga_x_axis", "tga_y_axis"
    else:
        guessed_x, guessed_y, experiment_type = guess_axes(dataframe, numeric_columns)
        x_axis_label = "X axis (usually Potential or Time)"
        y_axis_label = "Y axis (usually Current)"
        x_key, y_key = "cv_x_axis", "cv_y_axis"

    col_pick, col_meta = st.columns([2, 1])
    with col_pick:
        x_col = st.selectbox(x_axis_label, numeric_columns, index=guessed_x, key=x_key)
        y_options = [col for col in numeric_columns if col != x_col]
        y_default = numeric_columns[guessed_y]
        y_index = y_options.index(y_default) if y_default in y_options else 0
        y_col = st.selectbox(y_axis_label, y_options, index=y_index, key=y_key)
    with col_meta:
        st.metric("Rows in file", f"{len(dataframe):,}")
        st.caption(f"Source: {source_label}")

    plot_df = dataframe[[x_col, y_col]].dropna()
    if len(plot_df) < 5:
        st.error("There is not enough numeric data to draw a graph. Please check the file.")
        st.stop()

    x = plot_df[x_col].to_numpy(dtype=float)
    y = plot_df[y_col].to_numpy(dtype=float)
    if not is_tga and (x_col != numeric_columns[guessed_x] or y_col != numeric_columns[guessed_y]):
        experiment_type = classify_experiment(x_col, y_col)

    stats = analyze_curve(x, y, experiment_type)
    figure = make_figure(plot_df, x_col, y_col, experiment_type, stats)

    graph_tab, explain_tab, data_tab = st.tabs(["Graph", "Explanation", "Data table"])
    with graph_tab:
        st.plotly_chart(figure, use_container_width=True)
        st.caption("Hover on the line to see exact values. Use the toolbar to zoom or download the image.")
        if experiment_type == "cyclic_voltammetry":
            show_cv_graph_interpretation(x_col, y_col, stats)
        elif experiment_type == "tga":
            show_tga_graph_interpretation(x_col, y_col, stats)
    with explain_tab:
        show_explanation(x_col, y_col, experiment_type, stats)
    with data_tab:
        st.dataframe(dataframe, use_container_width=True, hide_index=True)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
            .block-container { padding-top: 1.4rem; max-width: 1200px; }
            h1 { letter-spacing: -0.03em; }
            .welcome-card {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 16px;
                padding: 1.2rem 1.3rem;
                height: 100%;
            }
            .welcome-card h3 { margin-top: 0; }
            .interpretation-box {
                background: #F8FAFC;
                border: 1px solid #CBD5E1;
                border-left: 5px solid #0F766E;
                border-radius: 12px;
                padding: 1.05rem 1.2rem 0.4rem 1.2rem;
                margin-top: 0.4rem;
            }
            .interpretation-box h3 { margin-top: 0.15rem; margin-bottom: 0.35rem; }
            .interpretation-label {
                display: inline-block;
                font-size: 0.78rem;
                font-weight: 700;
                letter-spacing: 0.04em;
                text-transform: uppercase;
                color: #0F766E;
                margin-bottom: 0.2rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def show_welcome() -> None:
    st.info("Choose a sample dataset or upload a CSV file in the left sidebar to begin.")
    left, right, extra = st.columns(3)
    with left:
        st.markdown(
            """
            <div class="welcome-card">
                <h3>1. Load data</h3>
                <p>Start with the built-in cyclic voltammetry example. It is designed so you can test the app without any lab file.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            """
            <div class="welcome-card">
                <h3>2. See the graph</h3>
                <p>ChemSense AI plots current against potential or time, which is how electrochemistry results are usually shown.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with extra:
        st.markdown(
            """
            <div class="welcome-card">
                <h3>3. Read the story</h3>
                <p>The explanation uses everyday scientific language: peaks, electron flow, and whether the reaction looks reversible.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def load_csv(file_or_path) -> pd.DataFrame:
    return pd.read_csv(file_or_path)


def _cell_is_numeric(value) -> bool:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return False
    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none", "null"}:
        return False
    text = text.replace(",", "")
    try:
        float(text)
        return True
    except ValueError:
        return False


def _row_numeric_count(row: pd.Series) -> int:
    return sum(_cell_is_numeric(value) for value in row.tolist())


def _clean_header_name(value, index: int) -> str:
    text = "" if value is None or (isinstance(value, float) and pd.isna(value)) else str(value).strip()
    return text if text else f"Column {index + 1}"


def _unique_names(names: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    unique: list[str] = []
    for name in names:
        if name not in seen:
            seen[name] = 0
            unique.append(name)
        else:
            seen[name] += 1
            unique.append(f"{name}_{seen[name]}")
    return unique


def _looks_like_tga_header(row: pd.Series) -> bool:
    joined = " ".join(str(value).lower() for value in row.tolist() if pd.notna(value) and str(value).strip())
    has_temp = any(hint in joined for hint in TEMPERATURE_HINTS)
    has_weight = "weight" in joined or "mass" in joined
    return has_temp and has_weight


def _read_raw_table(file_or_path) -> pd.DataFrame:
    def _read(separator: str | None) -> pd.DataFrame:
        if hasattr(file_or_path, "seek"):
            file_or_path.seek(0)
        return pd.read_csv(
            file_or_path,
            header=None,
            dtype=str,
            engine="python",
            encoding="utf-8-sig",
            sep=separator,
            skip_blank_lines=False,
        )

    raw = _read(",")
    if raw.shape[1] == 1 and len(raw) > 0:
        first = str(raw.iloc[0, 0])
        if "\t" in first:
            raw = _read("\t")
        elif ";" in first:
            raw = _read(";")
    return raw


def load_tga_csv(file_or_path) -> pd.DataFrame:
    """Read TGA exports that may include titles, unit rows, and blank columns."""
    raw = _read_raw_table(file_or_path)
    raw = raw.dropna(axis=1, how="all")
    raw = raw.map(lambda value: value.strip() if isinstance(value, str) else value)

    header_idx = None
    for idx in range(len(raw)):
        if _looks_like_tga_header(raw.iloc[idx]):
            header_idx = idx
            break
    if header_idx is None:
        header_idx = 0
        for idx in range(len(raw)):
            if _row_numeric_count(raw.iloc[idx]) >= 2:
                header_idx = max(idx - 1, 0)
                break

    names = _unique_names(
        [_clean_header_name(value, col) for col, value in enumerate(raw.iloc[header_idx].tolist())]
    )

    data_start = header_idx + 1
    while data_start < len(raw) and _row_numeric_count(raw.iloc[data_start]) < 2:
        data_start += 1
    if data_start >= len(raw):
        raise ValueError("No numeric TGA data rows were found.")

    data = raw.iloc[data_start:].copy()
    data.columns = names[: data.shape[1]]
    data = data.dropna(how="all")
    for column in data.columns:
        data[column] = pd.to_numeric(
            data[column].astype(str).str.replace(",", "", regex=False),
            errors="coerce",
        )
    data = data.dropna(axis=1, how="all").dropna(how="all")
    return data


def is_weight_column(name: str) -> bool:
    lowered = normalize_name(name)
    if "deriv" in lowered or "dtg" in lowered:
        return False
    return any(hint in lowered for hint in WEIGHT_HINTS)


def guess_tga_axes(numeric_columns: list[str]) -> tuple[int, int]:
    x_idx, y_idx = 0, 1 if len(numeric_columns) > 1 else 0
    for i, col in enumerate(numeric_columns):
        if column_matches(col, TEMPERATURE_HINTS):
            x_idx = i
            break
    for i, col in enumerate(numeric_columns):
        if i != x_idx and is_weight_column(col):
            y_idx = i
            break
    return x_idx, y_idx


def normalize_name(name: str) -> str:
    return str(name).strip().lower().replace("_", " ")


def column_matches(name: str, hints: tuple[str, ...]) -> bool:
    lowered = normalize_name(name)
    return any(hint in lowered for hint in hints)


def guess_axes(dataframe: pd.DataFrame, numeric_columns: list[str]) -> tuple[int, int, str]:
    x_idx, y_idx = 0, 1 if len(numeric_columns) > 1 else 0
    for i, col in enumerate(numeric_columns):
        if column_matches(col, POTENTIAL_HINTS) or column_matches(col, TIME_HINTS):
            x_idx = i
            break
    for i, col in enumerate(numeric_columns):
        if i != x_idx and column_matches(col, CURRENT_HINTS):
            y_idx = i
            break
    experiment_type = classify_experiment(numeric_columns[x_idx], numeric_columns[y_idx])
    return x_idx, y_idx, experiment_type


def classify_experiment(x_name: str, y_name: str) -> str:
    x_is_potential = column_matches(x_name, POTENTIAL_HINTS)
    x_is_time = column_matches(x_name, TIME_HINTS)
    y_is_current = column_matches(y_name, CURRENT_HINTS)
    if x_is_potential and y_is_current:
        return "cyclic_voltammetry"
    if x_is_time and y_is_current:
        return "chronoamperometry"
    if x_is_time and x_is_potential:
        return "potential_vs_time"
    if x_is_potential:
        return "potential_scan"
    if x_is_time:
        return "time_series"
    return "general"


def analyze_curve(x: np.ndarray, y: np.ndarray, experiment_type: str) -> dict:
    y_span = float(np.ptp(y)) if np.ptp(y) > 0 else 1.0
    peak_height = max(y_span * 0.12, np.std(y) * 0.8)
    peak_distance = max(len(y) // 40, 8)

    ox_idx, _ = find_peaks(y, prominence=peak_height * 0.35, distance=peak_distance)
    red_idx, _ = find_peaks(-y, prominence=peak_height * 0.35, distance=peak_distance)

    ox_peak = pick_extreme_peak(x, y, ox_idx, mode="max") if len(ox_idx) else None
    red_peak = pick_extreme_peak(x, y, red_idx, mode="min") if len(red_idx) else None

    if ox_peak is None:
        ox_peak = {"x": float(x[int(np.argmax(y))]), "y": float(np.max(y))}
    if red_peak is None:
        red_peak = {"x": float(x[int(np.argmin(y))]), "y": float(np.min(y))}

    slope = float(np.polyfit(x, y, 1)[0]) if len(x) >= 2 else 0.0
    noise = estimate_noise(y)
    turning_points = count_turning_points(x)

    delta_ep_mv = None
    reversibility = "unknown"
    if experiment_type == "cyclic_voltammetry" and ox_peak and red_peak:
        delta_ep_mv = abs(ox_peak["x"] - red_peak["x"]) * 1000.0
        if delta_ep_mv < 80:
            reversibility = "looks reversible"
        elif delta_ep_mv < 150:
            reversibility = "looks quasi-reversible"
        else:
            reversibility = "looks less reversible / more sluggish"

    current_ratio = None
    if ox_peak and red_peak and abs(ox_peak["y"]) > 1e-12:
        current_ratio = abs(red_peak["y"] / ox_peak["y"])

    return {
        "x_min": float(np.min(x)),
        "x_max": float(np.max(x)),
        "y_min": float(np.min(y)),
        "y_max": float(np.max(y)),
        "ox_peak": ox_peak,
        "red_peak": red_peak,
        "delta_ep_mv": delta_ep_mv,
        "reversibility": reversibility,
        "current_ratio": current_ratio,
        "slope": slope,
        "noise": noise,
        "turning_points": turning_points,
        "n_points": int(len(x)),
    }


def pick_extreme_peak(x: np.ndarray, y: np.ndarray, indices: np.ndarray, mode: str) -> dict:
    values = y[indices]
    chosen = int(indices[int(np.argmax(values) if mode == "max" else np.argmin(values))])
    return {"x": float(x[chosen]), "y": float(y[chosen])}


def estimate_noise(y: np.ndarray) -> str:
    if len(y) < 15:
        return "too few points to judge"
    window = min(len(y) if len(y) % 2 == 1 else len(y) - 1, 21)
    if window < 5:
        return "low"
    smooth = savgol_filter(y, window_length=window, polyorder=2)
    residual = float(np.std(y - smooth))
    signal = float(np.ptp(y)) or 1.0
    ratio = residual / signal
    if ratio < 0.02:
        return "low"
    if ratio < 0.06:
        return "moderate"
    return "high"


def count_turning_points(x: np.ndarray) -> int:
    direction = np.sign(np.diff(x))
    direction = direction[direction != 0]
    if len(direction) < 2:
        return 0
    return int(np.sum(direction[1:] != direction[:-1]))


def axis_title(column_name: str) -> str:
    name = column_name.replace("_", " ")
    lowered = name.lower()
    if "potential" in lowered or "voltage" in lowered:
        return f"{name}" if any(unit in lowered for unit in ("v", "volt")) else f"{name} (V)"
    if "current" in lowered:
        return name
    if "temperature" in lowered or "temp" in lowered:
        return name
    if "weight" in lowered or "mass" in lowered:
        return name
    if "time" in lowered:
        return name if any(unit in lowered for unit in ("s", "min")) else f"{name} (s)"
    return name


def make_figure(plot_df: pd.DataFrame, x_col: str, y_col: str, experiment_type: str, stats: dict) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=plot_df[x_col],
            y=plot_df[y_col],
            mode="lines",
            name="Measured data",
            line=dict(color="#0F766E", width=2.4),
            hovertemplate=f"{x_col}: %{{x:.4g}}<br>{y_col}: %{{y:.4g}}<extra></extra>",
        )
    )

    if experiment_type != "tga":
        ox = stats["ox_peak"]
        red = stats["red_peak"]
        fig.add_trace(
            go.Scatter(
                x=[ox["x"]],
                y=[ox["y"]],
                mode="markers+text",
                name="Highest current",
                marker=dict(size=11, color="#C2410C"),
                text=["Oxidation peak" if experiment_type == "cyclic_voltammetry" else "Maximum"],
                textposition="top center",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[red["x"]],
                y=[red["y"]],
                mode="markers+text",
                name="Lowest current",
                marker=dict(size=11, color="#1D4ED8"),
                text=["Reduction peak" if experiment_type == "cyclic_voltammetry" else "Minimum"],
                textposition="bottom center",
            )
        )

    title = {
        "cyclic_voltammetry": "Cyclic voltammogram",
        "chronoamperometry": "Current versus time",
        "tga": "Weight versus temperature",
        "potential_scan": "Current during a potential scan",
        "time_series": "Signal versus time",
    }.get(experiment_type, "Laboratory data")

    fig.update_layout(
        title=title,
        xaxis_title=axis_title(x_col),
        yaxis_title=axis_title(y_col),
        template="plotly_white",
        height=520,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(l=40, r=20, t=60, b=40),
    )
    if experiment_type == "cyclic_voltammetry":
        fig.update_xaxes(zeroline=True, zerolinewidth=1, zerolinecolor="#CBD5E1")
        fig.update_yaxes(zeroline=True, zerolinewidth=1, zerolinecolor="#CBD5E1")
    return fig


def show_cv_graph_interpretation(x_col: str, y_col: str, stats: dict) -> None:
    """Plain-language reading of a CV plot, placed directly under the graph."""
    loop_note = (
        "In this file the potential (x-axis) moves one way and then turns back, so the line forms a loop. "
        "That loop is the usual shape of a cyclic voltammogram: one forward scan and one reverse scan."
        if stats["turning_points"] >= 1
        else (
            "In this file the potential (x-axis) mostly moves in one direction, so the line may look more like "
            "a single sweep than a full loop. The ideas of oxidation and reduction peaks still apply if those "
            "features are present."
        )
    )
    st.markdown(
        f"""
<div class="interpretation-box">
<p class="interpretation-label">Interpretation — not an experimental conclusion</p>
<h3>How to read this cyclic voltammetry graph</h3>
</div>
        """,
        unsafe_allow_html=True,
    )
    st.info(
        "This section is a teaching-style interpretation of the plotted curve. "
        "It is not a laboratory report, not a claim about how well the reaction performed, "
        "and not a substitute for your own analysis or a published method."
    )
    st.write(
        "A cyclic voltammogram plots **current** against **electrode potential**. "
        "As the potential is changed, molecules near the electrode can lose or gain electrons, "
        "and that electron flow is recorded as current."
    )
    st.write(loop_note)
    st.write(
        "**Oxidation peak (often the upward current feature):** oxidation means a species loses electrons. "
        "On many student CV graphs this appears as a rise in current that then falls again, leaving an "
        "upward peak. The peak marks where that oxidation current is strongest in the scan, not a grade "
        "for the experiment."
    )
    st.write(
        "**Reduction peak (often the downward current feature):** reduction means a species gains electrons. "
        "This often appears as a downward peak on the reverse scan. Together, the two peaks are a common "
        "picture of a molecule being oxidized and then reduced again, or the reverse."
    )
    st.write(
        "From **this plotted file only**, the potential axis runs from "
        f"{stats['x_min']:.3g} to {stats['x_max']:.3g} ({x_col}), and the current axis runs from "
        f"{stats['y_min']:.3g} to {stats['y_max']:.3g} ({y_col}). "
        "Those ranges come directly from the CSV values shown in the graph. "
        "ChemSense AI does not add extra peak voltages, peak currents, or performance scores beyond that."
    )
    st.caption(
        "Do not treat this interpretation as proof of reversibility, electrode quality, concentration, "
        "or reaction rate. Those conclusions need a full experimental method, replicates, and your course criteria."
    )


def show_tga_graph_interpretation(x_col: str, y_col: str, stats: dict) -> None:
    """Cautious reading of a TGA plot, placed directly under the graph."""
    st.markdown(
        """
<div class="interpretation-box">
<p class="interpretation-label">Interpretation — not an experimental conclusion</p>
<h3>How to read this TGA graph</h3>
</div>
        """,
        unsafe_allow_html=True,
    )
    st.info(
        "This section is a teaching-style interpretation of the plotted curve. "
        "It is not a laboratory report and it does not identify a decomposition temperature, "
        "a chemical reaction, or how pure or stable the sample is."
    )
    st.write(
        "Thermogravimetric analysis (TGA) heats a sample and records how its mass changes. "
        "A common student graph is **weight remaining (%)** against **temperature (°C)**."
    )
    st.write(
        "**Mass loss:** if weight % falls as temperature rises, some of the sample left the pan "
        "as gas or vapour. That can happen for several reasons, such as drying, solvent loss, "
        "or thermal decomposition. The curve alone does not tell you which of those happened."
    )
    st.write(
        "**Thermal decomposition:** this is a chemistry term for a material breaking down when heated. "
        "A step down in a TGA curve is sometimes caused by decomposition, but the same shape can also "
        "come from moisture loss or overlapping processes. ChemSense AI will not assign a decomposition "
        "temperature from this graph."
    )
    st.write(
        "From **this plotted file only**, "
        f"{x_col} runs from {stats['x_min']:.3g} to {stats['x_max']:.3g}, and "
        f"{y_col} runs from {stats['y_min']:.3g} to {stats['y_max']:.3g}. "
        "Those ranges come directly from the numeric rows in the CSV. "
        "No extra peak temperatures or mass-loss events are added."
    )
    st.caption(
        "Do not treat this interpretation as proof of thermal stability, composition, or a named "
        "decomposition step. Those conclusions need your method, atmosphere, heating rate, and course criteria."
    )


def show_explanation(x_col: str, y_col: str, experiment_type: str, stats: dict) -> None:
    st.subheader("What this graph is saying")
    paragraphs = build_explanation(x_col, y_col, experiment_type, stats)
    for paragraph in paragraphs:
        st.write(paragraph)

    left, mid, right = st.columns(3)
    left.metric("X range", f"{stats['x_min']:.3g} to {stats['x_max']:.3g}")
    mid.metric("Highest Y", f"{stats['y_max']:.3g}")
    right.metric("Lowest Y", f"{stats['y_min']:.3g}")

    if experiment_type == "cyclic_voltammetry" and stats["delta_ep_mv"] is not None:
        st.metric("Peak separation (ΔEₚ)", f"{stats['delta_ep_mv']:.0f} mV")

    with st.expander("Tiny glossary"):
        st.markdown(
            """
- **Oxidation**: the molecule loses electrons. On many CV graphs this is the upward current peak.
- **Reduction**: the molecule gains electrons. This is often the downward current peak.
- **Peak potential**: the X value (voltage) where the current reaches a peak.
- **Reversible**: electrons move in and out of the molecule reasonably easily, so the two peaks sit close together.
- **Current**: how fast electrons are flowing in the circuit, not how “strong” the chemical is by itself.
            """
        )


def build_explanation(x_col: str, y_col: str, experiment_type: str, stats: dict) -> list[str]:
    ox = stats["ox_peak"]
    red = stats["red_peak"]
    noise = stats["noise"]

    if experiment_type == "cyclic_voltammetry":
        delta = stats["delta_ep_mv"]
        ratio = stats["current_ratio"]
        loops = "The potential was scanned forward and then back, which is why the trace looks like a loop."
        if stats["turning_points"] == 0:
            loops = (
                "The potential mostly moves in one direction. This may be a linear sweep rather than a full "
                "cycle, but the same peak-reading ideas still apply."
            )
        peak_text = (
            f"The oxidation (upward) peak is near {ox['x']:.3g} on the {x_col} axis, "
            f"with a current of {ox['y']:.3g}. The reduction (downward) peak is near "
            f"{red['x']:.3g}, with a current of {red['y']:.3g}."
        )
        if delta is None:
            rev_text = "ChemSense AI could not confidently measure the gap between the two peaks."
        elif stats["reversibility"] == "looks reversible":
            rev_text = (
                f"The peaks are only about {delta:.0f} mV apart. For a simple one-electron reaction, "
                "a gap near 59 mV is the textbook reversible case, so this curve looks close to reversible: "
                "the molecule can be oxidized and then reduced again without too much extra driving force."
            )
        elif stats["reversibility"] == "looks quasi-reversible":
            rev_text = (
                f"The peaks are about {delta:.0f} mV apart. That is wider than the ideal 59 mV for a fast "
                "one-electron couple, so electron transfer is probably happening, but a little more slowly "
                "(often called quasi-reversible)."
            )
        else:
            rev_text = (
                f"The peaks are about {delta:.0f} mV apart, which is quite wide. The reaction may be slow, "
                "the resistance in the cell may be high, or the scan may include extra processes. "
                "Treat this as a clue, not a final verdict."
            )

        ratio_text = ""
        if ratio is not None:
            if 0.7 <= ratio <= 1.3:
                ratio_text = (
                    f"The downward peak is similar in size to the upward peak (ratio ≈ {ratio:.2f}). "
                    "That often means the oxidized form stays near the electrode and can be reduced again."
                )
            else:
                ratio_text = (
                    f"The two peak currents are not the same size (ratio ≈ {ratio:.2f}). "
                    "A follow-up chemical reaction, a sloping background, or an incomplete reverse scan "
                    "can cause that."
                )

        noise_text = (
            f"The trace looks {noise}-noise. "
            + (
                "A quieter curve makes peak positions easier to trust."
                if noise == "low"
                else "If the line is shaky, averaging more scans or checking cables and grounding can help."
            )
        )
        return [
            "This looks like a cyclic voltammogram: current is plotted while the electrode potential is swept.",
            loops,
            peak_text,
            rev_text,
            ratio_text,
            noise_text,
            "In class terms: you are watching a molecule give and take electrons as you change the voltage.",
        ]

    if experiment_type == "chronoamperometry":
        return [
            "This looks like a chronoamperometry experiment: the potential is stepped, then current is watched over time.",
            (
                f"The current starts near the extremes of the curve ({stats['y_max']:.3g} at the high end, "
                f"{stats['y_min']:.3g} at the low end) and then changes as time goes from "
                f"{stats['x_min']:.3g} to {stats['x_max']:.3g}."
            ),
            (
                "A common student pattern is a large current right after the step, then a decay toward a smaller "
                "steady value. That decay often happens because nearby reactant is used up and fresh reactant "
                "must diffuse to the electrode."
            ),
            (
                "If the current stays almost flat, the reaction may be limited by something other than diffusion, "
                "or the time window may be short."
            ),
            f"The line looks {noise}-noise. Sudden spikes can be bubbles, a loose contact, or electrical interference.",
        ]

    trend = "rising" if stats["slope"] > 0 else "falling" if stats["slope"] < 0 else "fairly flat"
    return [
        f"ChemSense AI plotted {y_col} against {x_col}.",
        (
            f"Across the file, {x_col} runs from {stats['x_min']:.3g} to {stats['x_max']:.3g}, "
            f"and {y_col} runs from {stats['y_min']:.3g} to {stats['y_max']:.3g}."
        ),
        f"Overall the signal is {trend} as {x_col} increases.",
        (
            f"The highest point is at {x_col} = {ox['x']:.3g} ({y_col} = {ox['y']:.3g}). "
            f"The lowest point is at {x_col} = {red['x']:.3g} ({y_col} = {red['y']:.3g})."
        ),
        f"The trace looks {noise}-noise, based on how much the line wiggles around a smooth trend.",
        "If this is electrochemical data, rename columns to Potential, Current, or Time so ChemSense AI can give a more specific explanation.",
    ]


if __name__ == "__main__":
    main()
