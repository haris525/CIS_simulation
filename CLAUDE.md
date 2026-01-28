# CLAUDE.md - AI Assistant Guide for CIS Metrics Simulator

## Project Overview

This is a **Streamlit-based web application** for simulating complaint aging metrics over time. It helps CIS (Complaint Intake System) operations teams model scenarios to understand what closure rates and strategies are needed to meet service level targets.

**Primary Purpose:** Predict how complaint intake and closure rates affect aging metrics, enabling data-driven decisions for complaint processing operations.

## Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.x | Runtime |
| Streamlit | >= 1.28.0 | Web framework |
| Pandas | >= 2.0.0 | Data manipulation |
| NumPy | >= 1.24.0 | Numerical computing |
| Plotly | >= 5.18.0 | Interactive visualizations |

## Project Structure

```
CIS_simulation/
├── app.py              # Main application (single-file app, ~350 lines)
├── requirements.txt    # Python dependencies
├── CLAUDE.md           # This file
└── .git/               # Git repository
```

This is a **minimal, single-file application** - all logic is contained in `app.py`.

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app.py
```

The app will be available at `http://localhost:8501` by default.

## Core Concepts

### Three-Bucket Aging Model

The simulation uses a three-bucket system based on configurable age thresholds:

| Bucket | Age Range | Description |
|--------|-----------|-------------|
| Bucket 1 | 0 to `target_1_days` | Fresh complaints (e.g., 0-50 days) |
| Bucket 2 | `target_1_days+1` to `target_2_days` | Aging complaints (e.g., 51-100 days) |
| Bucket 3 | > `target_2_days` | Overdue complaints (e.g., >100 days) |

### Aging Rate Calculation

Complaints progress between buckets based on dynamic rates:
```python
rate_1_to_2 = min(1.0, 7 / target_1_days)           # Weekly aging from Bucket 1 to 2
rate_2_to_3 = min(1.0, 7 / (target_2_days - target_1_days))  # Weekly aging from Bucket 2 to 3
```

### Closure Strategies

1. **Oldest First (Prioritize Aging):** Closes Bucket 3 → Bucket 2 → Bucket 1
   - Best for improving aging metrics

2. **Newest First (FIFO):** Closes Bucket 1 → Bucket 2 → Bucket 3
   - Fast throughput but worsens aging metrics

3. **Mixed (50/50):** Proportional closures from all buckets
   - Balanced approach

## Code Architecture

### Application Flow

```
User Input (Sidebar)
    ↓
Bucket Initialization (calculate from percentages)
    ↓
simulate_aging() function
    ├── Weekly aging (buckets progress forward)
    ├── Weekly intake (new complaints to Bucket 1)
    ├── Weekly closures (based on strategy)
    └── Results collection (DataFrame row per week)
    ↓
Pandas DataFrame with simulation history
    ↓
Dashboard Visualization & Metrics
```

### Key Components in app.py

| Lines | Component | Description |
|-------|-----------|-------------|
| 1-10 | Setup | Imports and page configuration |
| 12-72 | Sidebar | Configuration inputs (targets, current state, parameters) |
| 76-171 | `simulate_aging()` | Core simulation logic |
| 179-209 | Metrics | KPI cards with deltas |
| 211-276 | Charts | Four-panel Plotly dashboard |
| 278-311 | Goal Seeker | Calculate required closure rates |
| 313-349 | Data Export | Simulation data table and model assumptions |

### Main Function: `simulate_aging()`

```python
def simulate_aging(total_open, bucket_1_init, bucket_2_init, bucket_3_init,
                   weekly_opened, weekly_closed, closure_strategy, weeks,
                   target_1_days, target_2_days):
```

**Parameters:**
- `total_open`: Starting number of open complaints
- `bucket_*_init`: Initial distribution across buckets
- `weekly_opened/closed`: Flow rates
- `closure_strategy`: Which bucket to prioritize
- `weeks`: Simulation duration
- `target_*_days`: Age thresholds

**Returns:** Pandas DataFrame with weekly simulation results

## Code Conventions

### UI Patterns
- Emoji-prefixed headers for visual organization
- Sidebar for all configuration inputs
- `st.metric()` for KPI display with deltas
- `st.expander()` for optional/advanced sections
- Color coding: Blue (Target 1), Purple (Target 2), Green/Yellow/Red (buckets)

### Data Patterns
- All calculations use integer complaint counts
- Percentage calculations guard against division by zero: `if total > 0:`
- Negative value guards: `max(0, value)`
- Dynamic bucket calculations from slider percentages

### Validation Rules
- `target_2_days > target_1_days` (enforced with `st.stop()`)
- `pct_meeting_target_2 >= pct_meeting_target_1` (broader bucket must be larger)

## Common Development Tasks

### Adding a New Metric Target
1. Add input in sidebar (around line 17-31)
2. Update `simulate_aging()` function to track new metric
3. Add visualization in charts section (around line 211-276)
4. Update Goal Seeker if needed (around line 278-311)

### Modifying Closure Strategy
1. Locate strategy handling in `simulate_aging()` (lines 133-164)
2. Add new elif block for new strategy
3. Update selectbox options (line 64-68)
4. Document in Model Assumptions (line 336-339)

### Changing Aging Model
1. Modify rate calculations (lines 93-94)
2. Update aging logic (lines 119-125)
3. Update Model Assumptions documentation (lines 330-334)

### Adding Export Formats
1. Create new expander section after line 324
2. Use `st.download_button()` with appropriate MIME type
3. Convert DataFrame to desired format

## Testing

No automated tests exist. Manual testing approach:
1. Run `streamlit run app.py`
2. Test edge cases: 0 complaints, 100% in any bucket, high/low rates
3. Verify validation errors trigger correctly
4. Confirm charts render with various configurations

## Key Assumptions and Limitations

1. **Simplified aging model** - constant weekly rates
2. **No seasonality** - intake/closure rates don't vary
3. **All new complaints start in Bucket 1** - no backdated complaints
4. **Linear decay model** - may not reflect real-world patterns
5. **Single-threaded** - not designed for concurrent users

## Git Workflow

- Main development happens on feature branches
- Commit messages should describe what changed
- No CI/CD pipeline configured

## Common Issues

### "Age Target #2 must be greater than Age Target #1"
- Ensure second threshold is always larger than first

### Charts not rendering
- Check if all bucket counts are non-negative
- Verify Plotly is properly installed

### Goal Seeker returns "Not achieved"
- Target may be mathematically impossible
- Try extending timeline or reducing intake rate

## Quick Reference

```python
# Run simulation
df = simulate_aging(total_open, bucket_1, bucket_2, bucket_3,
                    opened, closed, strategy, weeks,
                    target_1_days, target_2_days)

# Access results
df['pct_meeting_target_1']  # % under first threshold
df['pct_meeting_target_2']  # % under second threshold
df['total_open']            # Total complaints
df['bucket_1/2/3']          # Counts per bucket
```

## Contact

Repository maintained via GitHub. Check git log for recent contributors.
