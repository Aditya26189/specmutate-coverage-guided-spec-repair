# app.py — SpecMutate Streamlit Demo
# Phase 13: Verdict, signals, repair logs in a premium dark-mode browser UI

import streamlit as st
import json
from pathlib import Path

# ─── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SpecMutate — Spec Repair Dashboard",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    background: #0d1117 !important;
    color: #e6edf3 !important;
    font-family: 'Inter', sans-serif;
}

[data-testid="stSidebar"] {
    background: #161b22 !important;
    border-right: 1px solid #30363d;
}

.metric-card {
    background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
    border: 1px solid #374151;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 12px;
    transition: transform 0.2s, box-shadow 0.2s;
}
.metric-card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.4); }

.metric-value { font-size: 2.4rem; font-weight: 700; line-height: 1; margin-bottom: 4px; }
.metric-label { font-size: 0.8rem; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.08em; }

.verdict-badge {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.badge-underconstrained { background: #1e3a5f; color: #60a5fa; border: 1px solid #2563eb; }
.badge-overconstrained  { background: #3d1a1a; color: #f87171; border: 1px solid #dc2626; }
.badge-correct          { background: #14352b; color: #34d399; border: 1px solid #059669; }

.task-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 10px;
    cursor: pointer;
    transition: border-color 0.2s, background 0.2s;
}
.task-card:hover { border-color: #58a6ff; background: #1c2129; }
.task-card-selected { border-color: #58a6ff !important; background: #1c2129 !important; }

.signal-bar-wrap { margin: 6px 0; }
.signal-label { font-size: 0.78rem; color: #8b949e; margin-bottom: 2px; }

.spec-box {
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 14px 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    color: #c9d1d9;
    white-space: pre-wrap;
    overflow-x: auto;
    max-height: 300px;
    overflow-y: auto;
}

.headline-banner {
    background: linear-gradient(135deg, #1a237e 0%, #0d47a1 50%, #1565c0 100%);
    border-radius: 14px;
    padding: 28px 36px;
    margin-bottom: 24px;
    border: 1px solid #1e40af;
}
.headline-title {
    font-size: 1.9rem; font-weight: 700;
    background: linear-gradient(90deg, #93c5fd, #a5f3fc);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 4px;
}
.headline-sub { font-size: 0.9rem; color: #93c5fd; }

.section-header {
    font-size: 1rem; font-weight: 600; color: #58a6ff;
    border-bottom: 1px solid #30363d; padding-bottom: 8px; margin: 20px 0 14px 0;
    text-transform: uppercase; letter-spacing: 0.05em;
}

.repair-step {
    background: #161b22; border: 1px solid #30363d; border-radius: 8px;
    padding: 12px 16px; margin-bottom: 8px;
    border-left: 3px solid #58a6ff;
}
.converged-tag  { color: #34d399; font-weight: 600; }
.diverged-tag   { color: #f87171; font-weight: 600; }

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0d1117; }
::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)


# ─── Load results ─────────────────────────────────────────────────────────────
@st.cache_data
def load_results():
    p = Path("results/benchmark_results.json")
    if not p.exists():
        return None
    return json.loads(p.read_text())


results = load_results()

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔬 SpecMutate")
    st.markdown("**Coverage-Guided Spec Repair**")
    st.markdown("---")
    st.markdown("**Model:** `gemini-2.5-flash`")
    st.markdown("**Signals:** S1 · S2 · S3 · S4")
    st.markdown("**Operators:** FlipComparison · RemovePrecondition · RemovePostcondition")
    st.markdown("---")

    if results:
        filter_opt = st.selectbox(
            "Filter by label",
            ["All", "underconstrained", "overconstrained", "correct"]
        )
        show_only_wrong = st.checkbox("Show only misdiagnosed", value=False)
    else:
        filter_opt = "All"
        show_only_wrong = False

    st.markdown("---")
    st.markdown("<small style='color:#6e7681'>SpecMutate · Hackathon 2026</small>", unsafe_allow_html=True)

# ─── Main content ─────────────────────────────────────────────────────────────
if results is None:
    st.error("❌ No results found. Run `python run_benchmark.py` first.")
    st.stop()

tasks = results["results"]
acc   = results["diagnostic_accuracy"]
rep_r = results["repair_convergence_rate"]
rep_n = results["repair_converged"]
rep_t = results["repair_total"]
total = results["total_tasks"]
correct_count = results["correct_diagnoses"]

# Headline banner
st.markdown(f"""
<div class="headline-banner">
  <div class="headline-title">🔬 SpecMutate — Spec Repair Dashboard</div>
  <div class="headline-sub">Coverage-guided specification diagnosis &amp; CEGIS repair · gemini-2.5-flash · 15-task benchmark</div>
</div>
""", unsafe_allow_html=True)

# KPI row
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-value" style="color:#60a5fa">{correct_count}/{total}</div>
        <div class="metric-label">Diagnostic Accuracy</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-value" style="color:#34d399">{acc:.1%}</div>
        <div class="metric-label">Accuracy Rate</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-value" style="color:#a78bfa">{rep_n}/{rep_t}</div>
        <div class="metric-label">Repairs Converged</div>
    </div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-value" style="color:#fb923c">{rep_r:.1%}</div>
        <div class="metric-label">Repair Convergence Rate</div>
    </div>""", unsafe_allow_html=True)

# ─── Signal distribution chart ────────────────────────────────────────────────
st.markdown('<div class="section-header">Signal Heatmap — All 15 Tasks</div>', unsafe_allow_html=True)

import pandas as pd
rows = []
for t in tasks:
    rows.append({
        "Task": t["task_id"],
        "S1 Completeness": t["signals"]["s1"],
        "S2 Discrimination": t["signals"]["s2"],
        "S3 CrossHair": t["signals"]["s3"],
        "S4 Stability": t["signals"]["s4"],
        "Correct": "✅" if t["correct_diagnosis"] else "❌",
        "Predicted": t["predicted"],
        "Ground Truth": t["ground_truth"],
    })
df = pd.DataFrame(rows).set_index("Task")
# Pure-CSS colour function — no matplotlib needed
def _color_signal(val):
    """Map 0–1 signal value to a green/yellow/red background cell."""
    try:
        v = float(val)
    except (TypeError, ValueError):
        return ""
    # interpolate: 0 = red, 0.5 = yellow, 1 = green
    if v >= 0.7:
        bg = f"rgba(52,211,153,{0.15 + v*0.25})"   # green
        fg = "#34d399"
    elif v >= 0.4:
        bg = f"rgba(251,191,36,{0.15 + v*0.20})"   # yellow
        fg = "#fbbf24"
    else:
        bg = f"rgba(248,113,113,{0.15 + (1-v)*0.20})"  # red
        fg = "#f87171"
    return f"background-color: {bg}; color: {fg}; font-weight: 600"

# Use map if available (pandas 2.1+), otherwise fallback to applymap
style_obj = df.style
if hasattr(style_obj, "map"):
    style_obj = style_obj.map(_color_signal, subset=["S1 Completeness","S2 Discrimination","S3 CrossHair","S4 Stability"])
else:
    style_obj = style_obj.applymap(_color_signal, subset=["S1 Completeness","S2 Discrimination","S3 CrossHair","S4 Stability"])

st.dataframe(
    style_obj.set_properties(**{"font-family": "JetBrains Mono", "font-size": "12px"}),
    use_container_width=True,
    height=400,
)

# ─── Per-task detail ──────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Per-Task Detail</div>', unsafe_allow_html=True)

# Filter
filtered = tasks
if filter_opt != "All":
    filtered = [t for t in tasks if t["ground_truth"] == filter_opt]
if show_only_wrong:
    filtered = [t for t in filtered if not t["correct_diagnosis"]]

BADGE = {
    "underconstrained": '<span class="verdict-badge badge-underconstrained">underconstrained</span>',
    "overconstrained":  '<span class="verdict-badge badge-overconstrained">overconstrained</span>',
    "correct":          '<span class="verdict-badge badge-correct">correct</span>',
}

if not filtered:
    st.info("No tasks match the current filter.")
else:
    selected = st.selectbox(
        "Select task to inspect",
        [t["task_id"] for t in filtered],
        format_func=lambda tid: next(
            f"{t['task_id']} — {t['ground_truth']} {'✅' if t['correct_diagnosis'] else '❌'}"
            for t in filtered if t["task_id"] == tid
        )
    )
    task = next(t for t in filtered if t["task_id"] == selected)

    col_a, col_b = st.columns([1, 2])
    with col_a:
        gt_badge  = BADGE.get(task["ground_truth"], task["ground_truth"])
        pred_badge = BADGE.get(task["predicted"], task["predicted"])
        ok = "✅ Correct diagnosis" if task["correct_diagnosis"] else "❌ Misdiagnosed"
        st.markdown(f"""
        <div style='margin-bottom:16px'>
            <div style='font-size:0.8rem;color:#8b949e;margin-bottom:4px'>GROUND TRUTH</div>
            {gt_badge}
        </div>
        <div style='margin-bottom:16px'>
            <div style='font-size:0.8rem;color:#8b949e;margin-bottom:4px'>PREDICTED</div>
            {pred_badge}
        </div>
        <div style='font-size:0.95rem;font-weight:600;margin-top:8px'>{ok}</div>
        """, unsafe_allow_html=True)

        st.markdown("**Signal scores**")
        for sig, label in [("s1","S1 Completeness"),("s2","S2 Discrimination"),
                           ("s3","S3 CrossHair"),("s4","S4 Stability")]:
            v = task["signals"][sig]
            st.progress(v, text=f"{label}: {v:.2f}")

        diag = task.get("diagnosis", {})
        if "weighted_score" in diag:
            st.markdown(f"**Fusion score:** `{diag['weighted_score']:.3f}`")
        if "overconstrained_via" in diag:
            st.markdown(f"**Detected via:** `{diag['overconstrained_via']}`")

    with col_b:
        repair = task.get("repair")
        if repair:
            st.markdown(f"**Repair:** {'✅ CONVERGED' if repair['converged'] else '❌ DID NOT CONVERGE'} "
                        f"in **{repair['iterations']}** iteration(s)")
            st.markdown(f"_{repair.get('convergence_reason', '')}_")

            for i, step in enumerate(repair.get("history", []), 1):
                conv = step.get("converged", False)
                tag  = '<span class="converged-tag">✓ converged</span>' if conv else '<span class="diverged-tag">✗ not yet</span>'
                with st.expander(f"Iteration {i} — {tag}", expanded=(i == repair["iterations"])):
                    if step.get("counterexample"):
                        st.markdown("**Counterexample:**")
                        st.code(step["counterexample"], language="python")
                    if step.get("repaired_spec"):
                        st.markdown("**Repaired spec:**")
                        st.code(step["repaired_spec"], language="python")

            if repair.get("final_spec"):
                st.markdown("**Final repaired spec:**")
                st.code(repair["final_spec"], language="python")
        else:
            st.info("No repair attempted (task diagnosed as correct).")
