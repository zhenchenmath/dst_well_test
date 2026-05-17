import numpy as np


def gaussian_correlated_field(
    nx: int,
    ny: int,
    correlation_length: float,
    seed=None,
) -> np.ndarray:
    """
    2D Gaussian random field with Gaussian spatial correlation via spectral synthesis.

    Algorithm:
      1. Draw white noise in spatial domain
      2. FFT → apply Gaussian spectral filter → IFFT
      3. Standardize to N(0, 1)

    Args:
        nx, ny: grid dimensions (output shape is (ny, nx))
        correlation_length: spatial correlation as a fraction of max(nx, ny).
            0.1 = fine-scale heterogeneity (~2 cell patches on 50-cell grid)
            0.2 = moderate (~10 cell patches)
            0.4 = large-scale trend (~20 cell patches)
        seed: integer seed for reproducibility

    Returns:
        (ny, nx) float64 array with approximate N(0, 1) marginals
    """
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal((ny, nx))
    noise_fft = np.fft.rfft2(noise)

    fy = np.fft.fftfreq(ny)
    fx = np.fft.rfftfreq(nx)
    FX, FY = np.meshgrid(fx, fy)
    freq_mag = np.sqrt(FX**2 + FY**2)

    # Convert correlation length from domain fraction to cell units, then to freq units
    cl_cells = correlation_length * max(nx, ny)
    freq_sigma = 1.0 / (2.0 * np.pi * cl_cells)
    H = np.exp(-0.5 * (freq_mag / freq_sigma) ** 2)
    H[0, 0] = 0.0  # enforce zero mean

    field = np.fft.irfft2(noise_fft * H, s=(ny, nx))
    std = field.std()
    if std > 0:
        field /= std
    return field
