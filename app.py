import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="CIS Metrics Simulator", page_icon="📊", layout="wide")

st.title("📊 CIS Metrics Prediction Simulator")
st.markdown("Simulate how complaint intake and closure rates affect aging metrics over time.")

# --- Sidebar: Configuration ---
st.sidebar.header("⚙️ Configuration")

# Metric Targets
st.sidebar.subheader("Metric Targets")
target_1_days = st.sidebar.number_input("Age Target #1 (days)", value=50, min_value=1, step=5,
                                         help="First aging threshold in days")
target_2_days = st.sidebar.number_input("Age Target #2 (days)", value=100, min_value=2, step=5,
                                         help="Second aging threshold in days (must be > Target #1)")

if target_2_days <= target_1_days:
    st.sidebar.error("Age Target #2 must be greater than Age Target #1.")
    st.stop()

target_1_pct = st.sidebar.number_input("Target % for Age Target #1", value=90.0,
                                        min_value=0.0, max_value=100.0, step=1.0,
                                        help="Goal percentage of complaints under Target #1")
target_2_pct = st.sidebar.number_input("Target % for Age Target #2", value=98.0,
                                        min_value=0.0, max_value=100.0, step=1.0,
                                        help="Goal percentage of complaints under Target #2")

# Current State Inputs
st.sidebar.subheader("Current State")
total_open = st.sidebar.number_input("Total Open Complaints", value=200, min_value=0, step=10)

pct_meeting_target_1 = st.sidebar.slider(
    f"Current % Meeting Target #1 (< {target_1_days} days)",
    0, 100, 57,
    help=f"Percentage of open complaints currently under {target_1_days} days old"
)
pct_meeting_target_2 = st.sidebar.slider(
    f"Current % Meeting Target #2 (< {target_2_days} days)",
    0, 100, 88,
    help=f"Percentage of open complaints currently under {target_2_days} days old"
)

if pct_meeting_target_2 < pct_meeting_target_1:
    st.sidebar.error("% meeting Target #2 must be >= % meeting Target #1 (it's a broader bucket).")
    st.stop()

# Derive bucket counts from positive-framing sliders
bucket_1_count = int(total_open * pct_meeting_target_1 / 100)
bucket_2_count = int(total_open * pct_meeting_target_2 / 100) - bucket_1_count
bucket_2_count = max(0, bucket_2_count)
bucket_3_count = total_open - bucket_1_count - bucket_2_count
bucket_3_count = max(0, bucket_3_count)

# Weekly Flow Parameters
st.sidebar.subheader("Weekly Parameters")
weekly_opened = st.sidebar.slider("Complaints Opened / Week", 0, 1000, 15)
weekly_closed = st.sidebar.slider("Complaints Closed / Week", 0, 1000, 20)

closure_strategy = st.sidebar.selectbox(
    "Closure Strategy",
    ["Oldest First (Prioritize Aging)", "Newest First (FIFO)", "Mixed (50/50)"],
    help="Which complaints get closed first?"
)

# Simulation Settings
st.sidebar.subheader("Simulation Settings")
weeks_to_simulate = st.sidebar.slider("Weeks to Simulate", 4, 52, 26)


# --- Simulation Logic ---
def simulate_aging(total_open, bucket_1_init, bucket_2_init, bucket_3_init,
                   weekly_opened, weekly_closed, closure_strategy, weeks,
                   target_1_days, target_2_days):
    """
    Simulate complaint aging over time with dynamic age targets.

    Buckets:
    - Bucket 1: 0 to target_1_days
    - Bucket 2: target_1_days+1 to target_2_days
    - Bucket 3: > target_2_days
    """

    bucket_1 = bucket_1_init
    bucket_2 = bucket_2_init
    bucket_3 = bucket_3_init

    # Dynamic aging rates
    rate_1_to_2 = min(1.0, 7 / target_1_days)
    rate_2_to_3 = min(1.0, 7 / (target_2_days - target_1_days))

    results = []

    for week in range(weeks + 1):
        total = bucket_1 + bucket_2 + bucket_3

        if total > 0:
            pct_target_1 = (bucket_1 / total) * 100
            pct_target_2 = ((bucket_1 + bucket_2) / total) * 100
        else:
            pct_target_1 = 100
            pct_target_2 = 100

        results.append({
            'week': week,
            'total_open': total,
            'bucket_1': bucket_1,
            'bucket_2': bucket_2,
            'bucket_3': bucket_3,
            'pct_meeting_target_1': pct_target_1,
            'pct_meeting_target_2': pct_target_2
        })

        if week < weeks:
            # Age existing complaints
            aging_to_bucket_2 = int(bucket_1 * rate_1_to_2)
            aging_to_bucket_3 = int(bucket_2 * rate_2_to_3)

            bucket_1 -= aging_to_bucket_2
            bucket_2 += aging_to_bucket_2 - aging_to_bucket_3
            bucket_3 += aging_to_bucket_3

            # Add new complaints (all start in bucket 1)
            bucket_1 += weekly_opened

            # Close complaints based on strategy
            to_close = min(weekly_closed, bucket_1 + bucket_2 + bucket_3)

            if closure_strategy == "Oldest First (Prioritize Aging)":
                close_from_3 = min(to_close, bucket_3)
                bucket_3 -= close_from_3
                to_close -= close_from_3

                close_from_2 = min(to_close, bucket_2)
                bucket_2 -= close_from_2
                to_close -= close_from_2

                bucket_1 -= to_close

            elif closure_strategy == "Newest First (FIFO)":
                close_from_1 = min(to_close, bucket_1)
                bucket_1 -= close_from_1
                to_close -= close_from_1

                close_from_2 = min(to_close, bucket_2)
                bucket_2 -= close_from_2
                to_close -= close_from_2

                bucket_3 -= to_close

            else:  # Mixed
                total_current = bucket_1 + bucket_2 + bucket_3
                if total_current > 0:
                    close_1 = int(to_close * bucket_1 / total_current)
                    close_2 = int(to_close * bucket_2 / total_current)
                    close_3 = to_close - close_1 - close_2

                    bucket_1 -= min(close_1, bucket_1)
                    bucket_2 -= min(close_2, bucket_2)
                    bucket_3 -= min(close_3, bucket_3)

            # Ensure no negative values
            bucket_1 = max(0, bucket_1)
            bucket_2 = max(0, bucket_2)
            bucket_3 = max(0, bucket_3)

    return pd.DataFrame(results)


# Run simulation
df = simulate_aging(total_open, bucket_1_count, bucket_2_count, bucket_3_count,
                    weekly_opened, weekly_closed, closure_strategy, weeks_to_simulate,
                    target_1_days, target_2_days)

# --- Main Dashboard ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    current_pct_1 = df.iloc[0]['pct_meeting_target_1']
    final_pct_1 = df.iloc[-1]['pct_meeting_target_1']
    delta_1 = final_pct_1 - current_pct_1
    st.metric(f"% < {target_1_days} Days (Final)", f"{final_pct_1:.1f}%", f"{delta_1:+.1f}%")

with col2:
    current_pct_2 = df.iloc[0]['pct_meeting_target_2']
    final_pct_2 = df.iloc[-1]['pct_meeting_target_2']
    delta_2 = final_pct_2 - current_pct_2
    st.metric(f"% < {target_2_days} Days (Final)", f"{final_pct_2:.1f}%", f"{delta_2:+.1f}%")

with col3:
    final_total = df.iloc[-1]['total_open']
    delta_total = final_total - total_open
    st.metric("Total Open (Final)", int(final_total), f"{delta_total:+.0f}")

with col4:
    green_week = None
    for _, row in df.iterrows():
        if row['pct_meeting_target_1'] >= target_1_pct:
            green_week = int(row['week'])
            break

    if green_week is not None:
        st.metric(f"Weeks to Green ({target_1_days}d)", f"{green_week} weeks", "✅")
    else:
        st.metric(f"Weeks to Green ({target_1_days}d)", "Not achieved", "❌")

# --- Charts ---
st.subheader("📈 Metric Projections")

fig = make_subplots(rows=2, cols=2,
                    subplot_titles=(f"% < {target_1_days} Days Over Time",
                                    f"% < {target_2_days} Days Over Time",
                                    "Total Open Complaints",
                                    "Age Distribution Over Time"))

# Chart 1: % meeting target 1
fig.add_trace(
    go.Scatter(x=df['week'], y=df['pct_meeting_target_1'],
               mode='lines+markers', name=f'% < {target_1_days} days',
               line=dict(color='blue', width=2)),
    row=1, col=1
)
fig.add_hline(y=target_1_pct, line_dash="dash", line_color="green",
              annotation_text=f"{target_1_pct}% Target", row=1, col=1)

# Chart 2: % meeting target 2
fig.add_trace(
    go.Scatter(x=df['week'], y=df['pct_meeting_target_2'],
               mode='lines+markers', name=f'% < {target_2_days} days',
               line=dict(color='purple', width=2)),
    row=1, col=2
)
fig.add_hline(y=target_2_pct, line_dash="dash", line_color="green",
              annotation_text=f"{target_2_pct}% Target", row=1, col=2)

# Chart 3: Total open
fig.add_trace(
    go.Scatter(x=df['week'], y=df['total_open'],
               mode='lines+markers', name='Total Open',
               line=dict(color='orange', width=2)),
    row=2, col=1
)

# Chart 4: Stacked area for distribution
fig.add_trace(
    go.Scatter(x=df['week'], y=df['bucket_1'],
               fill='tozeroy', name=f'0-{target_1_days} days',
               line=dict(color='green')),
    row=2, col=2
)
fig.add_trace(
    go.Scatter(x=df['week'], y=df['bucket_1'] + df['bucket_2'],
               fill='tonexty', name=f'{target_1_days+1}-{target_2_days} days',
               line=dict(color='yellow')),
    row=2, col=2
)
fig.add_trace(
    go.Scatter(x=df['week'], y=df['bucket_1'] + df['bucket_2'] + df['bucket_3'],
               fill='tonexty', name=f'> {target_2_days} days',
               line=dict(color='red')),
    row=2, col=2
)

fig.update_layout(height=600, showlegend=True)
fig.update_xaxes(title_text="Week", row=2, col=1)
fig.update_xaxes(title_text="Week", row=2, col=2)
fig.update_yaxes(title_text="%", row=1, col=1)
fig.update_yaxes(title_text="%", row=1, col=2)
fig.update_yaxes(title_text="Count", row=2, col=1)
fig.update_yaxes(title_text="Count", row=2, col=2)

st.plotly_chart(fig, use_container_width=True)

# --- Goal Seeker ---
st.subheader("🎯 Goal Seeker: What Does It Take to Hit Green?")

target_weeks = st.slider(
    f"Target: Hit {target_1_pct}% ({target_1_days}-day metric) in how many weeks?",
    4, 52, 12
)


def find_required_closures(target_weeks, target_pct=target_1_pct):
    for closures in range(weekly_opened, 200):
        test_df = simulate_aging(total_open, bucket_1_count, bucket_2_count, bucket_3_count,
                                 weekly_opened, closures,
                                 "Oldest First (Prioritize Aging)", target_weeks,
                                 target_1_days, target_2_days)
        if test_df.iloc[-1]['pct_meeting_target_1'] >= target_pct:
            return closures
    return None


required = find_required_closures(target_weeks)

if required:
    surplus = required - weekly_opened
    st.success(
        f"✅ To reach **{target_1_pct}% under {target_1_days} days** in **{target_weeks} weeks**, "
        f"you need to close **{required} complaints/week** (currently closing {weekly_closed}/week)."
    )
    st.info(f"That's a net reduction of **{surplus} complaints/week** beyond intake ({weekly_opened}/week opened).")
else:
    st.error(
        f"❌ Cannot achieve {target_1_pct}% in {target_weeks} weeks even with maximum closure rate. "
        f"Consider extending timeline or reducing intake."
    )

# --- Data Table ---
with st.expander("📋 View Simulation Data"):
    display_df = df.rename(columns={
        'week': 'Week',
        'total_open': 'Total Open',
        'bucket_1': f'0-{target_1_days} days',
        'bucket_2': f'{target_1_days+1}-{target_2_days} days',
        'bucket_3': f'> {target_2_days} days',
        'pct_meeting_target_1': f'% < {target_1_days} days',
        'pct_meeting_target_2': f'% < {target_2_days} days'
    })
    st.dataframe(display_df.round(1))

# --- Assumptions ---
with st.expander("ℹ️ Model Assumptions"):
    rate_1 = min(1.0, 7 / target_1_days) * 100
    rate_2 = min(1.0, 7 / (target_2_days - target_1_days)) * 100
    st.markdown(f"""
**Aging Model:**
- New complaints enter the 0-{target_1_days} day bucket
- ~{rate_1:.1f}% of 0-{target_1_days} day complaints age into {target_1_days+1}-{target_2_days} days each week
- ~{rate_2:.1f}% of {target_1_days+1}-{target_2_days} day complaints age into >{target_2_days} days each week

**Closure Strategies:**
- **Oldest First**: Prioritizes closing complaints >{target_2_days} days, then {target_1_days+1}-{target_2_days}, then newest
- **Newest First**: Closes most recent complaints first (can worsen aging metrics!)
- **Mixed**: Closes proportionally from all buckets

**Targets:**
- {target_1_pct}% of complaints should be under {target_1_days} days
- {target_2_pct}% of complaints should be under {target_2_days} days

**Limitations:**
- This is a simplified model; actual aging patterns may vary
- Does not account for seasonality or variable intake rates
- Assumes constant weekly rates
    """)
