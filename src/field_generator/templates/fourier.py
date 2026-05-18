import numpy as np

from ._spectral import gaussian_correlated_field

MD_TO_M2 = 9.869233e-16  # 1 mD = 9.869233e-16 m²


def generate(
    nx: int,
    ny: int,
    nz: int,
    perm_mean_md: float,
    perm_std_log: float,
    poro_mean: float,
    poro_std: float,
    correlation_length: float = 0.2,
    seed: int | None = None,
    **_,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Spatially-correlated log-normal permeability field via Fourier (spectral) synthesis.

    Permeability is log-normally distributed — the standard assumption in reservoir
    engineering. A single spatially-correlated Gaussian base field z ~ N(0,1) is
    generated via spectral synthesis, then transformed:

        k = exp(ln(perm_mean_m2) + perm_std_log * z)

    Porosity is generated from a weakly correlated independent draw and clipped to
    physically meaningful bounds.

    Args:
        perm_mean_md:      geometric mean permeability (mD).
                           Typical: 1–10 mD (tight), 10–100 mD (moderate), 100–1000 mD (good).
        perm_std_log:      std of ln(k), controls spatial variability.
                           0.5 = mild (k varies ~2× around mean),
                           1.0 = moderate (k varies ~7× P10–P90),
                           2.0 = strong (k varies ~55× P10–P90),
                           3.0 = extreme (carbonates with vugs).
        poro_mean:         mean porosity. Typical: 0.10–0.30.
        poro_std:          std of porosity. Typical: 0.02–0.06.
        correlation_length: spatial correlation as fraction of domain size.
                           0.1 = patchy, 0.2–0.3 = moderate, 0.5+ = large-scale trend.
        seed:              integer seed for reproducibility.

    Returns:
        perm: (nz, ny, nx) float64, m²
        poro: (nz, ny, nx) float64, dimensionless, clamped to [0.03, 0.45]
    """
    rng = np.random.default_rng(seed)
    seed_indep = int(rng.integers(0, 2**31))

    base = gaussian_correlated_field(nx, ny, correlation_length, seed=seed)

    ln_k_mean = np.log(perm_mean_md * MD_TO_M2)
    perm_2d = np.exp(ln_k_mean + perm_std_log * base)

    # Porosity: same spatial structure as perm (rho=0.3 correlation) + independent noise.
    # Weak positive correlation reflects the perm-poro relationship seen in core data.
    indep = gaussian_correlated_field(nx, ny, correlation_length, seed=seed_indep)
    rho = 0.3
    poro_driver = rho * base + np.sqrt(1.0 - rho**2) * indep
    poro_2d = np.clip(poro_mean + poro_std * poro_driver, 0.03, 0.45)

    perm = np.broadcast_to(perm_2d[np.newaxis], (nz, ny, nx)).copy()
    poro = np.broadcast_to(poro_2d[np.newaxis], (nz, ny, nx)).copy()
    return perm, poro
