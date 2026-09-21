import cvxpy as cp
import numpy as np
import pandas as pd


def optimize_battery(
    prices,
    reserve_prices=None,
    power_mw=10.0,
    energy_mwh=20.0,
    initial_soc=0.50,
    charge_efficiency=0.95,
    discharge_efficiency=0.95,
    degradation_cost=0.002,
    min_soc=0.10,
    max_soc=0.95,
):
    """
    Optimize battery energy arbitrage + ancillary reserve capacity.

    Battery:
        power_mw: maximum charge/discharge power
        energy_mwh: energy capacity
        initial_soc: initial state of charge as fraction [0,1]

    Objective:
        maximize energy market revenue
        + ancillary service revenue
        - convex degradation cost
    """

    prices = np.asarray(prices, dtype=float)
    n = len(prices)

    if reserve_prices is None:
        reserve_prices = np.zeros(n)

    reserve_prices = np.asarray(reserve_prices, dtype=float)

    charge = cp.Variable(n, nonneg=True)
    discharge = cp.Variable(n, nonneg=True)
    reserve = cp.Variable(n, nonneg=True)

    soc = cp.Variable(n + 1)

    constraints = [
        soc[0] == initial_soc * energy_mwh,

        # SOC limits
        soc >= min_soc * energy_mwh,
        soc <= max_soc * energy_mwh,

        # Power limits
        charge <= power_mw,
        discharge <= power_mw,

        # Reserve consumes part of the available discharge capability.
        discharge + reserve <= power_mw,

        # Battery energy balance
        soc[1:]
        == soc[:-1]
        + charge_efficiency * charge
        - discharge / discharge_efficiency,

        # Reserve must be deliverable from available energy.
        reserve <= soc[:-1] * discharge_efficiency,
    ]

    # Market revenue
    energy_revenue = cp.sum(
        cp.multiply(prices, discharge - charge)
    )

    reserve_revenue = cp.sum(
        cp.multiply(reserve_prices, reserve)
    )

    # Convex approximation of degradation cost.
    throughput = charge + discharge

    degradation = degradation_cost * cp.sum_squares(throughput)

    objective = cp.Maximize(
        energy_revenue
        + reserve_revenue
        - degradation
    )

    problem = cp.Problem(objective, constraints)

    problem.solve(solver=cp.CLARABEL)

    if problem.status not in ["optimal", "optimal_inaccurate"]:
        raise RuntimeError(
            f"Optimization failed. Status: {problem.status}"
        )

    result = pd.DataFrame(
        {
            "price": prices,
            "reserve_price": reserve_prices,
            "charge_mw": charge.value,
            "discharge_mw": discharge.value,
            "reserve_mw": reserve.value,
            "soc_mwh": soc.value[1:],
        }
    )

    result["net_power_mw"] = (
        result["discharge_mw"] - result["charge_mw"]
    )

    result["energy_revenue"] = (
        result["price"] * result["net_power_mw"]
    )

    result["reserve_revenue"] = (
        result["reserve_price"] * result["reserve_mw"]
    )

    result["degradation_cost"] = (
        degradation_cost
        * (
            result["charge_mw"] + result["discharge_mw"]
        ) ** 2
    )

    result["net_revenue"] = (
        result["energy_revenue"]
        + result["reserve_revenue"]
        - result["degradation_cost"]
    )

    return result, problem.value


def naive_dispatch(
    prices,
    power_mw=10.0,
    energy_mwh=20.0,
    initial_soc=0.50,
    charge_threshold=30.0,
    discharge_threshold=60.0,
    charge_efficiency=0.95,
    discharge_efficiency=0.95,
):
    """
    Simple threshold-based battery strategy.

    Charge when price is below charge_threshold.
    Discharge when price is above discharge_threshold.
    """

    prices = np.asarray(prices, dtype=float)

    soc = initial_soc * energy_mwh

    records = []

    for price in prices:

        charge = 0.0
        discharge = 0.0

        if price <= charge_threshold:

            available_space = energy_mwh - soc

            charge = min(
                power_mw,
                available_space / charge_efficiency
            )

            soc += charge * charge_efficiency

        elif price >= discharge_threshold:

            available_energy = soc * discharge_efficiency

            discharge = min(
                power_mw,
                available_energy
            )

            soc -= discharge / discharge_efficiency

        revenue = price * (discharge - charge)

        records.append(
            {
                "price": price,
                "charge_mw": charge,
                "discharge_mw": discharge,
                "soc_mwh": soc,
                "revenue": revenue,
            }
        )

    return pd.DataFrame(records)