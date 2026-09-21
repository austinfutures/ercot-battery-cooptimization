# ERCOT Battery Storage Co-Optimization Engine

A Python-based optimization engine for battery energy storage participating in ERCOT-style energy and ancillary-service markets.

## Project Overview

The system models a utility-scale battery and determines an economically optimal dispatch schedule while respecting physical battery constraints.

Default battery:

- 10 MW power capacity
- 20 MWh energy capacity
- 95% charge efficiency
- 95% discharge efficiency
- 10% minimum SoC
- 95% maximum SoC

## Optimization

The model uses CVXPY to solve a convex optimization problem.

The objective maximizes:

Energy arbitrage revenue + Ancillary-service reserve revenue - Battery degradation cost

The model includes:

- Charge/discharge power limits
- State-of-charge limits
- Round-trip efficiency
- Reserve capacity constraints
- Energy availability for reserve
- Convex degradation penalty

## Benchmark

The optimization engine is compared against a simple threshold-based dispatch strategy.

The application calculates the actual revenue improvement from the supplied market data.

## Data

The application includes synthetic ERCOT-like demo data for development.

For a real backtest, upload a CSV containing:

```text
timestamp,lmp,reserve_price
2025-01-01 00:00:00,25.4,4.2
2025-01-01 01:00:00,21.8,3.9
...
