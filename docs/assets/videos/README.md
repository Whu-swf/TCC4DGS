# Video File Convention

The project page loads comparison videos from `comparisons/` using the following naming convention:

- `comparisons/<method>_<scene>.mp4`

Method prefixes:

- `SpacetimeGaussians`
- `4DGaussians`
- `3D-4DGS`
- `Ex4DGS`
- `STGS`
- `STGS_Fastgs`

Scene names:

- `actor1_4`
- `actor2_3`
- `actor5_6`
- `cut_roasted_beef`
- `flame_steak`
- `sear_steak`

Recommended encoding: H.264, `yuv420p`, 30 FPS, with `faststart` enabled.

The repository-level `demo/` directory stores compressed GIF previews and high-quality scene-comparison MP4 files for the GitHub README.
