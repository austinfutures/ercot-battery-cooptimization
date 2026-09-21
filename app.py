import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from optimizer import optimize_battery, naive_dispatch
from data_utils import generate_demo_data, load_lmp_csv


st.set_page_config(
    page_title="ERCOT Battery Co-Optimization Engine",
    page_icon="🔋",
    layout="wide",
)


st.title("ERCOT Battery Storage Co-Optimization Engine")

st.write(
    """
    Interactive optimization engine for a 10 MW / 20 MWh battery.
    
    The model co-optimizes energy arbitrage and ancillary-service
    reserve capacity while respecting battery power, energy, efficiency,
    and state-of-charge constraints.
    """
)


# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------

st.sidebar.header("Battery Parameters")

power_mw = st.sidebar.slider(
    "Power Capacity (MW)",
    min_value=1.0,
    max_value=100.0,
    value=10.0,
    step=1.0,
)

energy_mwh = st.sidebar.slider(
    "Energy Capacity (MWh)",
    min_value=1.0,
    max_value=200.0,
    value=20.0,
    step=1.0,
)

initial_soc = st.sidebar.slider(
    "Initial SoC",
    min_value=0.0,
    max_value=1.0,
    value=0.50,
    step=0.05,
)

charge_efficiency = st.sidebar.slider(
    "Charge Efficiency",
    min_value=0.80,
    max_value=1.00,
    value=0.95,
    step=0.01,
)

discharge_efficiency = st.sidebar.slider(
    "Discharge Efficiency",
    min_value=0.80,
    max_value=1.00,
    value=0.95,
    step=0.01,
)

degradation_cost = st.sidebar.slider(
    "Degradation Cost",
    min_value=0.0,
    max_value=0.05,
    value=0.002,
    step=0.001,
    format="%.3f",
)


st.sidebar.header("Naive Strategy")

charge_threshold = st.sidebar.slider(
    "Naive Charge Threshold ($/MWh)",
    min_value=-50.0,
    max_value=100.0,
    value=30.0,
    step=5.0,
)

discharge_threshold = st.sidebar.slider(
    "Naive Discharge Threshold ($/MWh)",
    min_value=0.0,
    max_value=200.0,
    value=60.0,
    step=5.0,
)


# ---------------------------------------------------------
# Data
# ---------------------------------------------------------

st.sidebar.header("Market Data")

data_source = st.sidebar.radio(
    "Data Source",
    [
        "Demo Data",
        "Upload CSV",
    ],
)


if data_source == "Upload CSV":

    uploaded_file = st.sidebar.file_uploader(
        "Upload ERCOT LMP CSV",
        type=["csv"],
    )

    if uploaded_file is None:

        st.info(
            "Upload a CSV with columns: timestamp, lmp. "
            "Optional column: reserve_price."
        )

        st.stop()

    try:
        market_data = load_lmp_csv(
            uploaded_file
        )

    except Exception as e:

        st.error(
            f"Could not load CSV: {e}"
        )

        st.stop()

else:

    hours = st.sidebar.slider(
        "Demo Hours",
        min_value=24,
        max_value=720,
        value=168,
        step=24,
    )

    market_data = generate_demo_data(
        hours=hours
    )


# ---------------------------------------------------------
# Optimization
# ---------------------------------------------------------

prices = market_data["lmp"].values

reserve_prices = (
    market_data["reserve_price"].values
)


try:

    optimized, objective_value = optimize_battery(
        prices=prices,
        reserve_prices=reserve_prices,
        power_mw=power_mw,
        energy_mwh=energy_mwh,
        initial_soc=initial_soc,
        charge_efficiency=charge_efficiency,
        discharge_efficiency=discharge_efficiency,
        degradation_cost=degradation_cost,
    )

except Exception as e:

    st.error(
        f"Optimization error: {e}"
    )

    st.stop()


naive = naive_dispatch(
    prices=prices,
    power_mw=power_mw,
    energy_mwh=energy_mwh,
    initial_soc=initial_soc,
    charge_threshold=charge_threshold,
    discharge_threshold=discharge_threshold,
    charge_efficiency=charge_efficiency,
    discharge_efficiency=discharge_efficiency,
)


optimized_revenue = optimized["net_revenue"].sum()

naive_revenue = naive["revenue"].sum()

improvement = (
    (optimized_revenue - naive_revenue)
    / abs(naive_revenue)
    * 100
    if naive_revenue != 0
    else 0
)


# ---------------------------------------------------------
# KPI section
# ---------------------------------------------------------

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Optimized Revenue",
    f"${optimized_revenue:,.0f}",
)

col2.metric(
    "Naive Revenue",
    f"${naive_revenue:,.0f}",
)

col3.metric(
    "Improvement",
    f"{improvement:.1f}%",
)

col4.metric(
    "Average LMP",
    f"${market_data['lmp'].mean():.1f}/MWh",
)


# ---------------------------------------------------------
# Charts
# ---------------------------------------------------------

st.subheader("Market Price and Battery Dispatch")

fig, ax1 = plt.subplots(figsize=(12, 5))

ax1.plot(
    market_data["timestamp"],
    market_data["lmp"],
    label="ERCOT LMP",
)

ax1.set_ylabel(
    "LMP ($/MWh)"
)

ax1.set_xlabel(
    "Time"
)

ax2 = ax1.twinx()

ax2.plot(
    market_data["timestamp"],
    optimized["net_power_mw"],
    label="Battery Dispatch",
    alpha=0.7,
)

ax2.set_ylabel(
    "Battery Power (MW)"
)

fig.tight_layout()

st.pyplot(fig)


st.subheader("Battery State of Charge")

fig, ax = plt.subplots(figsize=(12, 4))

ax.plot(
    market_data["timestamp"],
    optimized["soc_mwh"],
)

ax.axhline(
    energy_mwh * 0.10,
    linestyle="--",
    label="Minimum SoC",
)

ax.axhline(
    energy_mwh * 0.95,
    linestyle="--",
    label="Maximum SoC",
)

ax.set_ylabel("Energy (MWh)")
ax.set_xlabel("Time")

ax.legend()

fig.tight_layout()

st.pyplot(fig)


# ---------------------------------------------------------
# Revenue breakdown
# ---------------------------------------------------------

st.subheader("Revenue Breakdown")

energy_revenue = optimized[
    "energy_revenue"
].sum()

reserve_revenue = optimized[
    "reserve_revenue"
].sum()

degradation = optimized[
    "degradation_cost"
].sum()

revenue_table = pd.DataFrame(
    {
        "Component": [
            "Energy Arbitrage",
            "Ancillary Services",
            "Degradation Cost",
            "Net Revenue",
        ],
        "Value ($)": [
            energy_revenue,
            reserve_revenue,
            -degradation,
            optimized_revenue,
        ],
    }
)

st.dataframe(
    revenue_table,
    use_container_width=True,
    hide_index=True,
)


# ---------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------

st.subheader("Optimization Output")

display_df = optimized.copy()

display_df.insert(
    0,
    "timestamp",
    market_data["timestamp"].values,
)

st.dataframe(
    display_df.round(3),
    use_container_width=True,
)


# ---------------------------------------------------------
# Download
# ---------------------------------------------------------

csv = display_df.to_csv(
    index=False
).encode("utf-8")

st.download_button(
    "Download Optimization Results",
    data=csv,
    file_name="battery_optimization_results.csv",
    mime="text/csv",
)