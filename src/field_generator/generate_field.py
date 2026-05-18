#!/usr/bin/env python3
"""
CLI for generating reservoir perm/poro field .h5 files.

Usage:
    python src/field_generator/generate_field.py <config.yaml> [--preview]

Example:
    python src/field_generator/generate_field.py field_configs/homogeneous_100md.yaml --preview
"""

import argparse
import sys
from pathlib import Path

import h5py
import numpy as np
import yaml

# Ensure project root is on path so field_generator is importable as a package
sys.path.insert(0, str(Path(__file__).parent.parent))

from field_generator.templates import fourier, gmm, homogeneous

MD_TO_M2 = 9.869233e-16

TEMPLATES = {
    'homogeneous': homogeneous.generate,
    'fourier': fourier.generate,
    'gmm': gmm.generate,
}


def make_well_mask(nx: int, ny: int, nz: int, well_cfg: dict) -> np.ndarray:
    """Build boolean well mask from config. Defaults to center cell of layer 0."""
    mask = np.zeros((nz, ny, nx), dtype=bool)
    i = well_cfg.get('i', nx // 2)  # 0-indexed x
    j = well_cfg.get('j', ny // 2)  # 0-indexed y
    k = well_cfg.get('k', 0)         # 0-indexed z
    mask[k, j, i] = True
    return mask


def save_h5(path: Path, perm: np.ndarray, poro: np.ndarray, well_mask: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, 'w') as f:
        f.create_dataset('perm', data=perm, dtype='float64')
        f.create_dataset('poro', data=poro, dtype='float64')
        f.create_dataset('well_mask', data=well_mask)

    geomean_md = np.exp(np.log(perm).mean()) / MD_TO_M2
    print(f'Saved: {path}')
    print(f'  shape (nz,ny,nx): {perm.shape}')
    print(f'  perm  min={perm.min()/MD_TO_M2:.3g} mD  '
          f'max={perm.max()/MD_TO_M2:.3g} mD  geomean={geomean_md:.3g} mD')
    print(f'  poro  min={poro.min():.3f}  mean={poro.mean():.3f}  max={poro.max():.3f}')
    well_count = well_mask.sum()
    print(f'  well  {well_count} cell(s) marked')


def save_preview(perm: np.ndarray, poro: np.ndarray, well_mask: np.ndarray, h5_path: Path) -> None:
    import matplotlib.colors as mcolors
    import matplotlib.pyplot as plt

    perm_md = perm[0] / MD_TO_M2  # first layer, convert to mD
    poro_2d = poro[0]
    well_2d = well_mask[0]
    wy, wx = np.where(well_2d)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    vmin, vmax = perm_md.min(), perm_md.max()
    if vmin == vmax:
        norm = mcolors.Normalize(vmin=vmin * 0.9, vmax=vmax * 1.1)
    else:
        norm = mcolors.LogNorm(vmin=vmin, vmax=vmax)

    im0 = axes[0].imshow(perm_md, origin='lower', cmap='viridis', norm=norm)
    axes[0].scatter(wx, wy, c='red', s=80, marker='x', linewidths=2, label='well')
    plt.colorbar(im0, ax=axes[0], label='Permeability (mD)')
    axes[0].set_title('Permeability (log scale)')
    axes[0].set_xlabel('x cell index')
    axes[0].set_ylabel('y cell index')
    axes[0].legend()

    im1 = axes[1].imshow(poro_2d, origin='lower', cmap='plasma',
                          vmin=max(0, poro_2d.min()), vmax=min(1, poro_2d.max()))
    axes[1].scatter(wx, wy, c='red', s=80, marker='x', linewidths=2, label='well')
    plt.colorbar(im1, ax=axes[1], label='Porosity')
    axes[1].set_title('Porosity')
    axes[1].set_xlabel('x cell index')
    axes[1].legend()

    fig.suptitle(h5_path.stem, fontsize=13)
    fig.tight_layout()

    preview_path = h5_path.with_suffix('.png')
    fig.savefig(preview_path, dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f'Preview: {preview_path}')


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Generate reservoir perm/poro field .h5 from a YAML config.'
    )
    parser.add_argument('config', help='Path to field config YAML')
    parser.add_argument('--preview', action='store_true',
                        help='Save a preview PNG alongside the .h5 file')
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        sys.exit(f'Config not found: {config_path}')

    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    template_name = cfg.get('template')
    if template_name not in TEMPLATES:
        sys.exit(f"Unknown template '{template_name}'. Available: {list(TEMPLATES)}")

    grid = cfg['grid']
    nx, ny, nz = grid['nx'], grid['ny'], grid['nz']
    params = cfg.get('params', {})
    well_cfg = cfg.get('well', {})
    output = Path(cfg['output'])

    perm, poro = TEMPLATES[template_name](nx=nx, ny=ny, nz=nz, **params)
    well_mask = make_well_mask(nx, ny, nz, well_cfg)

    save_h5(output, perm, poro, well_mask)

    if args.preview:
        save_preview(perm, poro, well_mask, output)


if __name__ == '__main__':
    main()
