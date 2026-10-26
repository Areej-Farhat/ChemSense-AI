"""Create the built-in CSV examples shipped with ChemSense AI."""

from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).parent / "sample_data"
OUT.mkdir(exist_ok=True)


def cyclic_voltammetry() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    forward = np.linspace(-0.20, 0.80, 401)
    reverse = np.linspace(0.80, -0.20, 401)
    potential = np.concatenate([forward, reverse])

    def faradaic(e, center, height, width):
        return height * np.exp(-((e - center) ** 2) / (2 * width**2))

    current_forward = (
        faradaic(forward, 0.412, 18.4, 0.038)
        + 1.15 * (forward + 0.20)
        + 0.35
    )
    current_reverse = (
        faradaic(reverse, 0.348, -16.9, 0.040)
        + 1.15 * (reverse + 0.20)
        - 1.05
    )
    current = np.concatenate([current_forward, current_reverse])
    current += rng.normal(0, 0.12, current.shape)
    return pd.DataFrame({"Potential_V": np.round(potential, 5), "Current_uA": np.round(current, 4)})


def chronoamperometry() -> pd.DataFrame:
    rng = np.random.default_rng(11)
    time = np.linspace(0.01, 10.0, 500)
    # Cottrell-like decay plus a small faradaic plateau
    current = 42.0 / np.sqrt(time) + 1.8
    current += rng.normal(0, 0.18, current.shape)
    return pd.DataFrame({"Time_s": np.round(time, 4), "Current_uA": np.round(current, 4)})


def main() -> None:
    cyclic_voltammetry().to_csv(OUT / "cyclic_voltammetry_sample.csv", index=False)
    chronoamperometry().to_csv(OUT / "chronoamperometry_sample.csv", index=False)


if __name__ == "__main__":
    main()
