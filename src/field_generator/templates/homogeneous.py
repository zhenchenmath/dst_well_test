import numpy as np

MD_TO_M2 = 9.869233e-16  # 1 mD = 9.869233e-16 m²


def generate(
    nx: int,
    ny: int,
    nz: int,
    perm_md: float,
    poro: float,
    **_,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Uniform permeability and porosity throughout the domain.

    Args:
        perm_md: permeability in milliDarcy (e.g., 10, 100, 1000)
        poro:    porosity fraction (e.g., 0.10, 0.25)

    Returns:
        perm: (nz, ny, nx) float64, m²
        poro: (nz, ny, nx) float64, dimensionless
    """
    perm = np.full((nz, ny, nx), perm_md * MD_TO_M2, dtype=np.float64)
    poro_field = np.full((nz, ny, nx), float(poro), dtype=np.float64)
    return perm, poro_field
