<div align="center">
  <img src="logo.png" alt="Logo" width="128" height="128">
  <h1>Watermark Detector and Cleaner</h1>
  <p>
    <a href="https://opensource.org/license/mit"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
    <img src="https://img.shields.io/badge/Language-Python_3.x-yellow.svg" alt="Language">
    <img src="https://img.shields.io/badge/GUI-CustomTkinter-blueviolet.svg" alt="GUI">
    <img src="https://img.shields.io/badge/CV-OpenCV-green.svg" alt="OpenCV">
  </p>
</div>

Detect and Remove hidden watermark in the screenshot && Randomize fingerprint to avoid tracking. 100% offline.

![Screenshot](Screenshot.png)


## ✨ What's New 
- **Modern UI & Asynchronous Engine**: Fully redesigned with `CustomTkinter`. Features True Dark/Light modes, frameless dialogs, and a non-blocking asynchronous multi-threaded backend.
- **Advanced 4-Layer Detection**: 
  - `LSB (Spatial)`: Scans the least significant bits.
  - `FFT`, `DCT`, `DWT (Frequency)`: Analyzes geometric patterns in Fourier and Wavelet spectrums.
- **Adaptive Clearance Modes**: `Aggressive` (maximum removal), `Balanced` (recommended), `Conservative` (quality preservation).
- **Privacy Engine**: 
  - `Rand Name`: Hashes the output file with a random 9-character string.
  - `Rand Size`: Invokes a micro-crop (±2px) imperceptible to the human eye to destroy resolution-based tracking.
  - `Force JPEG`: Compresses lossless images to strip container-level steganography.

## 🛠️ Usage

### Quick Start (No Installation)

1. Clone the repo and install dependencies:
```bash
git clone https://github.com/AndrewWangDev/remove_watermark.git
cd remove_watermark
pip install -r requirements.txt
```
2. Launch the app:
```bash
python src/main.py
```
3. **Workflow**: Browse for an input image -> Select your detection/privacy parameters -> Hit **Detect Watermarks** (to scan) or **Clean & Save** (to output the neutralized image).

## 📊 Scoring & Verification 
The Detection Engine runs an empirical mathematical analysis across 4 frequency and spatial dimensions to compute anomaly scores and determine a global confidence probability:

```text
--- Starting DETECT ---
Method:     | LSB       | FFT       | DCT       | DWT       | 
Score:      | 0.32      | 28.50     | 142.10    | 12.40     | 
Result:     | Clean     | Clean     | Clean     | Clean     | 
Conclusion: The image is clean / unlikely to be watermarked (0% probability).
            No significant watermark signatures detected.
--- DETECT Finished ---
```
- **LSB (Spatial)**: Measures spatial transition probability and difference energy in lowest bit-planes. Natural images have smooth neighborhoods (< 0.45); pseudo-random or encrypted steganographic payloads converge towards Bernoulli white noise (~0.500).
- **FFT / DCT / DWT**: Identifies geometric spikes, mid-frequency AC clusters, and wavelet high-frequency anomalies via fully vectorized transforms.
- **Global Probability**: A deterministic, multi-feature weighted confidence model (Weighted Confidence Evaluation). If no watermarks are detected, the score deterministically resolves to 0%.

## 🧠 Core Algorithm Architecture

This application employs a dual-domain analysis to expose and destroy steganographic artifacts:

```text
    [ Original Suspicious Image ]
                  │
                  ▼
 ┌─────────────────────────────────┐
 │   Spatial Domain Analysis       │
 │   (Extracting LSB Bit-Planes)   │ ──► LSB Detection
 └─────────────────────────────────┘
                  │
       (FFT / DCT / DWT Transform)
                  │
                  ▼
 ┌─────────────────────────────────┐
 │  Frequency Domain Manipulation  │
 │  * Target High-Frequency Spikes │ ──► FFT/DCT/DWT Detection
 │  * Apply Low-Pass / Masking     │
 └─────────────────────────────────┘
                  │
       (Inverse Transformation)
                  │
                  ▼
      [ Sanitized Clean Image ]
```

## 🏗️ Tech Stack
- **Backend Algorithms**: OpenCV (`cv2`), Numpy, PyWavelets, Scipy
- **Frontend Engine**: CustomTkinter (Tkinter Wrapper)
- **Packaging**: PyInstaller + PIL (Dynamic Logo Generation)
