# TCC4DGS: Fast 4D Gaussian Splatting Reconstruction under Temporal Consistency Constraints

Official project page for **TCC4DGS**.

## 📌 Abstract

Fast 4D Gaussian Splatting (4DGS) reconstruction must balance compact Gaussian representations, short training times, and stable cross-frame motion modeling. In dynamic scenes, occlusion, motion blur, and transient appearance changes can corrupt frame-wise supervision, causing redundant densification, erroneous pruning, and temporal artifacts such as ghosting and flicker. We present **TCC4DGS**, a fast 4DGS reconstruction framework constrained by temporal consistency. The framework evaluates cross-frame motion consistency using optical-flow errors between adjacent frames. Gaussians that persistently cover high-temporal-error regions are selected as densification candidates, while a pruning score combines the flow reconstruction error with an edge-aware smoothness term. Specifically, we first compute the cross-frame discrepancy between rendered and prior optical flow and normalize it to identify high-temporal-error regions. We then jointly gate per-Gaussian temporal-error scores and image-space gradients so that cloning or splitting is performed only in persistently under-reconstructed regions. Candidate Gaussians are subsequently evaluated using the flow reconstruction error and edge-aware smoothness term to remove redundant primitives that consistently induce temporal inconsistency while preserving genuine motion boundaries. Throughout training, adjacent frames from the same viewpoint are rasterized once each to obtain rendered optical flow efficiently, thereby limiting the additional cost of temporal supervision. Experiments on Neural 3D Video and ENeRF-Outdoor show that our method maintains or improves reconstruction quality while reducing the size of the trained Gaussian point-cloud model and accelerating training. TCC4DGS thus provides a unified solution for efficient and temporally stable dynamic-scene reconstruction.

Our contributions include:

- A general framework that can be integrated with diverse 3DGS backbones and achieves a better balance among training time, model size, reconstruction quality, and temporal stability.
- A temporal-consistency-guided densification rule that selects Gaussians persistently covering high-temporal-error regions as candidates. Cloning or splitting is performed only when both the optical-flow error and image-space gradient indicate under-reconstruction.
- A pruning score that combines the flow reconstruction error with an edge-aware smoothness term, preferentially removing redundant Gaussians that consistently cause temporal inconsistency without excessively penalizing genuine motion boundaries.
- An improved Gaussian rasterization pipeline that processes adjacent frames from the same viewpoint once each, efficiently producing rendered images and optical flow in CUDA while concurrently accumulating per-Gaussian error statistics.

## 🏗️ Pipeline Overview

<div align="center">
  <img src="./img/pipeline.png"
       alt="TCC4DGS Pipeline Overview"
       style="width:100%; max-width:1400px;">
</div>
<div align="left">
  <p><i>Fig. 1. Overview of TCC4DGS. (1) Multiview videos are used to initialize a Gaussian scene representation with time-varying primitives. We first sample <i>j</i> viewpoints and then select the same frame <i>i</i> for each sampled viewpoint. (2) The optical-flow error is normalized into an error map. A high-error mask is generated using the flow-error threshold τ<sub>flow</sub>, and error statistics are accumulated across the <i>j</i> sampled views to obtain the Optical Flow Score. (3) High-temporal-error Gaussians and image gradients jointly determine densification candidates. The flow reconstruction error is combined with L<sub>ea</sub> to form the pruning score, where L<sub>ea</sub> denotes an edge-aware smoothness term controlled by the edge-weight and smoothing coefficients. (4) Adjacent frames from the same viewpoint are rasterized once each to obtain rendered optical flow efficiently. Image<sub>loss</sub> and Flow<sub>loss</sub> jointly update the time-varying Gaussian parameters.</i></p>
</div>

## 📊 Qualitative Results

<div align="center">
  <img src="./img/Fig2.png" alt="Qualitative results on the N3DV dataset" style="width:100%; max-width:1400px;"><br>
  <img src="./img/Fig3.png" alt="Qualitative results on the ENeRF-Outdoor dataset" style="width:100%; max-width:1400px;">
</div>

### Quantitative Results

**Table 1. N3DV dataset.**

| Method | PSNR ↑ | SSIM ↑ | LPIPS ↓ | Size/MB ↓ | Time/min ↓ |
| --- | ---: | ---: | ---: | ---: | ---: |
| 4D-GS | 28.525 | **0.953** | 0.055 | 1198.12 | 150 |
| Ex4DGS | 31.600 | 0.949 | **0.044** | 40.54 | 30 |
| 3D-4DGS | 29.590 | 0.926 | 0.124 | 425.07 | 25 |
| 4DGaussians | 26.499 | 0.917 | 0.077 | 53.89 | 60 |
| 4DGaussians + FastGS | 26.756 | 0.923 | 0.076 | 19.62 | 30 |
| 4DGaussians + Ours | 27.869 | 0.927 | 0.074 | 16.47 | 32 |
| STGS | 31.754 | 0.947 | 0.046 | 23.74 | 25 |
| STGS + FastGS | 31.002 | 0.945 | 0.049 | 16.52 | **13** |
| **STGS + Ours** | **31.841** | 0.944 | 0.053 | **10.83** | 15 |

**Table 2. ENeRF-Outdoor dataset.**

| Method | PSNR ↑ | SSIM ↑ | LPIPS ↓ | Size/MB ↓ | Time/min ↓ |
| --- | ---: | ---: | ---: | ---: | ---: |
| 4D-GS | 24.627 | 0.793 | 0.128 | 4699.41 | 240 |
| Ex4DGS | 25.644 | 0.817 | 0.121 | 71.64 | 25 |
| 3D-4DGS | 22.822 | 0.593 | 0.425 | 390.41 | 17 |
| 4DGaussians | 20.950 | 0.581 | 0.344 | 177.24 | 130 |
| 4DGaussians + FastGS | 22.346 | 0.654 | 0.283 | 61.79 | 60 |
| 4DGaussians + Ours | 22.830 | 0.689 | 0.261 | 53.07 | 70 |
| STGS | 23.737 | 0.837 | **0.102** | 94.07 | 17 |
| STGS + FastGS | 23.851 | 0.830 | 0.124 | 65.87 | **13** |
| **STGS + Ours** | **25.865** | **0.849** | **0.102** | **53.77** | 15 |

## 🎬 Demo Videos

### Indoor Scene Reconstruction Demos

<div align="center">
  <video src="./demo/cut_roasted_beef.mp4" controls muted loop playsinline width="100%"></video>
  <img src="./demo/cut_roasted_beef.gif" width="100%" alt="Cut Roasted Beef Scene GIF">
  <p><i>Cut Roasted Beef Scene — <a href="./demo/cut_roasted_beef.mp4">Download High-Quality MP4</a></i></p>
</div>

<div align="center">
  <video src="./demo/flame_steak.mp4" controls muted loop playsinline width="100%"></video>
  <img src="./demo/flame_steak.gif" width="100%" alt="Flame Steak Scene GIF">
  <p><i>Flame Steak Scene — <a href="./demo/flame_steak.mp4">Download High-Quality MP4</a></i></p>
</div>

<div align="center">
  <video src="./demo/sear_steak.mp4" controls muted loop playsinline width="100%"></video>
  <img src="./demo/sear_steak.gif" width="100%" alt="Sear Steak Scene GIF">
  <p><i>Sear Steak Scene — <a href="./demo/sear_steak.mp4">Download High-Quality MP4</a></i></p>
</div>

---

### Outdoor Scene Reconstruction Demos

<div align="center">
  <video src="./demo/actor1_4.mp4" controls muted loop playsinline width="100%"></video>
  <img src="./demo/actor1_4.gif" width="100%" alt="Actor 1 4 Scene GIF">
  <p><i>Actor 1_4 Scene — <a href="./demo/actor1_4.mp4">Download High-Quality MP4</a></i></p>
</div>

<div align="center">
  <video src="./demo/actor2_3.mp4" controls muted loop playsinline width="100%"></video>
  <img src="./demo/actor2_3.gif" width="100%" alt="Actor 2 3 Scene GIF">
  <p><i>Actor 2_3 Scene — <a href="./demo/actor2_3.mp4">Download High-Quality MP4</a></i></p>
</div>

<div align="center">
  <video src="./demo/actor5_6.mp4" controls muted loop playsinline width="100%"></video>
  <img src="./demo/actor5_6.gif" width="100%" alt="Actor 5 6 Scene GIF">
  <p><i>Actor 5_6 Scene — <a href="./demo/actor5_6.mp4">Download High-Quality MP4</a></i></p>
</div>

## 🚧 Code Release

The full code will be released **upon paper acceptance**.

Contact information will be provided with the public release.
