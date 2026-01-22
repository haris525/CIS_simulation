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

# Current State Inputs
st.sidebar.subheader("Current State (Mock Data)")
total_open = st.sidebar.number_input("Total Open Complaints", value=200, min_value=0, step=10)
pct_over_50_days = st.sidebar.slider("% Currently > 50 days old", 0, 100, 43, help="43% means 57% are under 50 days")
pct_over_100_days = st.sidebar.slider("% Currently > 100 days old", 0, 100, 12, help="12% means 88% are under 100 days")

# Calculate current distribution
over_50 = int(total_open * pct_over_50_days / 100)
over_100 = int(total_open * pct_over_100_days / 100)
under_50 = total_open - over_50

# Weekly Flow Parameters
st.sidebar.subheader("Weekly Parameters")
weekly_opened = st.sidebar.slider("Complaints Opened / Week", 0, 50, 15)
weekly_closed = st.sidebar.slider("Complaints Closed / Week", 0, 50, 20)

closure_strategy = st.sidebar.selectbox(
    "Closure Strategy",
    ["Oldest First (Prioritize Aging)", "Newest First (FIFO)", "Mixed (50/50)"],
    help="Which complaints get closed first?"
)

# Simulation Settings
st.sidebar.subheader("Simulation Settings")
weeks_to_simulate = st.sidebar.slider("Weeks to Simulate", 4, 52, 26)


# --- Simulation Logic ---
def simulate_aging(total_open, over_50, over_100, weekly_opened, weekly_closed,
                   closure_strategy, weeks):
    """
    Simulate complaint aging over time.

    We track 4 age buckets:
    - 0-50 days (green for 50-day metric)
    - 51-100 days (red for 50-day, green for 100-day)
    - >100 days (red for both metrics)
    """

    # Initialize buckets
    bucket_0_50 = total_open - over_50
    bucket_51_100 = over_50 - over_100
    bucket_over_100 = over_100

    results = []

    for week in range(weeks + 1):
        total = bucket_0_50 + bucket_51_100 + bucket_over_100

        if total > 0:
            pct_under_50 = (bucket_0_50 / total) * 100
            pct_under_100 = ((bucket_0_50 + bucket_51_100) / total) * 100
        else:
            pct_under_50 = 100
            pct_under_100 = 100

        results.append({
            'week': week,
            'total_open': total,
            'bucket_0_50': bucket_0_50,
            'bucket_51_100': bucket_51_100,
            'bucket_over_100': bucket_over_100,
            'pct_under_50_days': pct_under_50,
            'pct_under_100_days': pct_under_100
        })

        if week < weeks:
            # Age existing complaints (roughly: each week, some move to older bucket)
            # Simplified: ~14% of 0-50 bucket ages past 50 days each week (50 days ≈ 7 weeks)
            aging_to_51_100 = int(bucket_0_50 * 0.14)
            # ~10% of 51-100 bucket ages past 100 days each week (50 days ≈ 5 weeks in this bucket)
            aging_to_over_100 = int(bucket_51_100 * 0.10)

            # Apply aging
            bucket_0_50 -= aging_to_51_100
            bucket_51_100 += aging_to_51_100 - aging_to_over_100
            bucket_over_100 += aging_to_over_100

            # Add new complaints (all start in 0-50 bucket)
            bucket_0_50 += weekly_opened

            # Close complaints based on strategy
            to_close = min(weekly_closed, bucket_0_50 + bucket_51_100 + bucket_over_100)

            if closure_strategy == "Oldest First (Prioritize Aging)":
                # Close from oldest buckets first
                close_from_over_100 = min(to_close, bucket_over_100)
                bucket_over_100 -= close_from_over_100
                to_close -= close_from_over_100

                close_from_51_100 = min(to_close, bucket_51_100)
                bucket_51_100 -= close_from_51_100
                to_close -= close_from_51_100

                bucket_0_50 -= to_close

            elif closure_strategy == "Newest First (FIFO)":
                # Close from newest bucket first
                close_from_0_50 = min(to_close, bucket_0_50)
                bucket_0_50 -= close_from_0_50
                to_close -= close_from_0_50

                close_from_51_100 = min(to_close, bucket_51_100)
                bucket_51_100 -= close_from_51_100
                to_close -= close_from_51_100

                bucket_over_100 -= to_close

            else:  # Mixed
                # Proportional closure
                total_current = bucket_0_50 + bucket_51_100 + bucket_over_100
                if total_current > 0:
                    close_0_50 = int(to_close * bucket_0_50 / total_current)
                    close_51_100 = int(to_close * bucket_51_100 / total_current)
                    close_over_100 = to_close - close_0_50 - close_51_100

                    bucket_0_50 -= min(close_0_50, bucket_0_50)
                    bucket_51_100 -= min(close_51_100, bucket_51_100)
                    bucket_over_100 -= min(close_over_100, bucket_over_100)

            # Ensure no negative values
            bucket_0_50 = max(0, bucket_0_50)
            bucket_51_100 = max(0, bucket_51_100)
            bucket_over_100 = max(0, bucket_over_100)

    return pd.DataFrame(results)


# Run simulation
df = simulate_aging(total_open, over_50, over_100, weekly_opened, weekly_closed,
                    closure_strategy, weeks_to_simulate)

# --- Main Dashboard ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    current_pct_50 = df.iloc[0]['pct_under_50_days']
    final_pct_50 = df.iloc[-1]['pct_under_50_days']
    delta_50 = final_pct_50 - current_pct_50
    st.metric("% < 50 Days (Final)", f"{final_pct_50:.1f}%", f"{delta_50:+.1f}%")

with col2:
    current_pct_100 = df.iloc[0]['pct_under_100_days']
    final_pct_100 = df.iloc[-1]['pct_under_100_days']
    delta_100 = final_pct_100 - current_pct_100
    st.metric("% < 100 Days (Final)", f"{final_pct_100:.1f}%", f"{delta_100:+.1f}%")

with col3:
    final_total = df.iloc[-1]['total_open']
    delta_total = final_total - total_open
    st.metric("Total Open (Final)", int(final_total), f"{delta_total:+.0f}")

with col4:
    # Calculate weeks to green for 50-day metric
    green_week_50 = None
    for _, row in df.iterrows():
        if row['pct_under_50_days'] >= 90:
            green_week_50 = int(row['week'])
            break

    if green_week_50 is not None:
        st.metric("Weeks to Green (50d)", f"{green_week_50} weeks", "✅")
    else:
        st.metric("Weeks to Green (50d)", "Not achieved", "❌")

# --- Charts ---
st.subheader("📈 Metric Projections")

fig = make_subplots(rows=2, cols=2,
                    subplot_titles=("% < 50 Days Over Time", "% < 100 Days Over Time",
                                    "Total Open Complaints", "Age Distribution Over Time"))

# Chart 1: % under 50 days
fig.add_trace(
    go.Scatter(x=df['week'], y=df['pct_under_50_days'],
               mode='lines+markers', name='% < 50 days',
               line=dict(color='blue', width=2)),
    row=1, col=1
)
fig.add_hline(y=90, line_dash="dash", line_color="green",
              annotation_text="90% Target", row=1, col=1)

# Chart 2: % under 100 days
fig.add_trace(
    go.Scatter(x=df['week'], y=df['pct_under_100_days'],
               mode='lines+markers', name='% < 100 days',
               line=dict(color='purple', width=2)),
    row=1, col=2
)
fig.add_hline(y=98, line_dash="dash", line_color="green",
              annotation_text="98% Target", row=1, col=2)

# Chart 3: Total open
fig.add_trace(
    go.Scatter(x=df['week'], y=df['total_open'],
               mode='lines+markers', name='Total Open',
               line=dict(color='orange', width=2)),
    row=2, col=1
)

# Chart 4: Stacked area for distribution
fig.add_trace(
    go.Scatter(x=df['week'], y=df['bucket_0_50'],
               fill='tozeroy', name='0-50 days',
               line=dict(color='green')),
    row=2, col=2
)
fig.add_trace(
    go.Scatter(x=df['week'], y=df['bucket_0_50'] + df['bucket_51_100'],
               fill='tonexty', name='51-100 days',
               line=dict(color='yellow')),
    row=2, col=2
)
fig.add_trace(
    go.Scatter(x=df['week'], y=df['bucket_0_50'] + df['bucket_51_100'] + df['bucket_over_100'],
               fill='tonexty', name='> 100 days',
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

target_weeks = st.slider("Target: Hit 90% (50-day metric) in how many weeks?", 4, 26, 12)


# Binary search for required closure rate
def find_required_closures(target_weeks, target_pct=90):
    for closures in range(weekly_opened, 100):
        test_df = simulate_aging(total_open, over_50, over_100, weekly_opened, closures,
                                 "Oldest First (Prioritize Aging)", target_weeks)
        if test_df.iloc[-1]['pct_under_50_days'] >= target_pct:
            return closures
    return None


required = find_required_closures(target_weeks)

if required:
    surplus = required - weekly_opened
    st.success(
        f"✅ To reach **90% under 50 days** in **{target_weeks} weeks**, you need to close **{required} complaints/week** (currently closing {weekly_closed}/week).")
    st.info(f"That's a net reduction of **{surplus} complaints/week** beyond intake ({weekly_opened}/week opened).")
else:
    st.error(
        f"❌ Cannot achieve 90% in {target_weeks} weeks even with maximum closure rate. Consider extending timeline or reducing intake.")

# --- Data Table ---
with st.expander("📋 View Simulation Data"):
    st.dataframe(df.round(1))

# --- Assumptions ---
with st.expander("ℹ️ Model Assumptions"):
    st.markdown("""
    **Aging Model:**
    - New complaints enter the 0-50 day bucket
    - ~14% of 0-50 day complaints age into 51-100 days each week
    - ~10% of 51-100 day complaints age into >100 days each week

    **Closure Strategies:**
    - **Oldest First**: Prioritizes closing complaints >100 days, then 51-100, then newest
    - **Newest First**: Closes most recent complaints first (can worsen aging metrics!)
    - **Mixed**: Closes proportionally from all buckets

    **Limitations:**
    - This is a simplified model; actual aging patterns may vary
    - Does not account for seasonality or variable intake rates
    - Assumes constant weekly rates
    """)