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

## 📈 Quantitative Results

**Table 1. N3DV dataset.**

<table style="width:100%; font-size:1.08em; text-align:center;">
<thead><tr><th>Method</th><th>PSNR ↑</th><th>SSIM ↑</th><th>LPIPS ↓</th><th>Size/MB ↓</th><th>Time/min ↓</th></tr></thead>
<tbody>
<tr><td>4D-GS</td><td>28.525</td><td><strong>0.953</strong></td><td>0.055</td><td>1198.12</td><td>150</td></tr>
<tr><td>Ex4DGS</td><td>31.600</td><td>0.949</td><td><strong>0.044</strong></td><td>40.54</td><td>30</td></tr>
<tr><td>3D-4DGS</td><td>29.590</td><td>0.926</td><td>0.124</td><td>425.07</td><td>25</td></tr>
<tr><td>4DGaussians</td><td>26.499</td><td>0.917</td><td>0.077</td><td>53.89</td><td>60</td></tr>
<tr><td>4DGaussians + FastGS</td><td>26.756</td><td>0.923</td><td>0.076</td><td>19.62</td><td>30</td></tr>
<tr><td>4DGaussians + Ours</td><td>27.869</td><td>0.927</td><td>0.074</td><td>16.47</td><td>32</td></tr>
<tr><td>STGS</td><td>31.754</td><td>0.947</td><td>0.046</td><td>23.74</td><td>25</td></tr>
<tr><td>STGS + FastGS</td><td>31.002</td><td>0.945</td><td>0.049</td><td>16.52</td><td><strong>13</strong></td></tr>
<tr><td><strong>STGS + Ours</strong></td><td><strong>31.841</strong></td><td>0.944</td><td>0.053</td><td><strong>10.83</strong></td><td>15</td></tr>
</tbody></table>

**Table 2. ENeRF-Outdoor dataset.**

<table style="width:100%; font-size:1.08em; text-align:center;">
<thead><tr><th>Method</th><th>PSNR ↑</th><th>SSIM ↑</th><th>LPIPS ↓</th><th>Size/MB ↓</th><th>Time/min ↓</th></tr></thead>
<tbody>
<tr><td>4D-GS</td><td>24.627</td><td>0.793</td><td>0.128</td><td>4699.41</td><td>240</td></tr>
<tr><td>Ex4DGS</td><td>25.644</td><td>0.817</td><td>0.121</td><td>71.64</td><td>25</td></tr>
<tr><td>3D-4DGS</td><td>22.822</td><td>0.593</td><td>0.425</td><td>390.41</td><td>17</td></tr>
<tr><td>4DGaussians</td><td>20.950</td><td>0.581</td><td>0.344</td><td>177.24</td><td>130</td></tr>
<tr><td>4DGaussians + FastGS</td><td>22.346</td><td>0.654</td><td>0.283</td><td>61.79</td><td>60</td></tr>
<tr><td>4DGaussians + Ours</td><td>22.830</td><td>0.689</td><td>0.261</td><td>53.07</td><td>70</td></tr>
<tr><td>STGS</td><td>23.737</td><td>0.837</td><td><strong>0.102</strong></td><td>94.07</td><td>17</td></tr>
<tr><td>STGS + FastGS</td><td>23.851</td><td>0.830</td><td>0.124</td><td>65.87</td><td><strong>13</strong></td></tr>
<tr><td><strong>STGS + Ours</strong></td><td><strong>25.865</strong></td><td><strong>0.849</strong></td><td><strong>0.102</strong></td><td><strong>53.77</strong></td><td>15</td></tr>
</tbody></table>

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
