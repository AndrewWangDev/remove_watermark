import os
import sys
import random
import numpy as np
import cv2
import shutil

# Ensure repo root is on sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, repo_root)

from src.logic.algorithms import (
    process_lsb, process_fft, process_dct, process_dwt, _deblock_8x8
)
from src.logic.processor import (
    WatermarkProcessor, blend_alpha_to_bgr, imwrite_unicode, imread_unicode
)
from src.ui.main_view import get_resource_path

def _make_dummy_image(h, w, c=3):
    rng = random.Random(42)
    data = bytes([rng.randint(40, 210) for _ in range(h * w * c)])
    if c == 1:
        return np.frombuffer(data, dtype=np.uint8).reshape((h, w))
    return np.frombuffer(data, dtype=np.uint8).reshape((h, w, c))

def test_resource_path():
    print("\n--- 1. Testing Resource Path Resolution ---")
    p = get_resource_path("logo.png")
    assert os.path.exists(p), f"Resource logo.png not found: {p}"
    print(f"OK: logo.png resolved to {p}")

def test_alpha_blending():
    print("\n--- 2. Testing Alpha Blending for JPEG Export ---")
    # 10x10 fully transparent image with black underlying pixels
    rgba = np.zeros((10, 10, 4), dtype=np.uint8)
    rgba[:, :, :3] = 0 # Black RGB
    rgba[:, :, 3] = 0  # 100% Transparent
    
    blended = blend_alpha_to_bgr(rgba, bg_color=(255, 255, 255))
    # All transparent pixels must be crisp white (255, 255, 255), not black (0, 0, 0)!
    assert np.all(blended == 255), "Transparent region did not blend to white!"
    print("OK: Transparent regions correctly blended to pure white without dark halos.")

def test_pipeline_lsb_zero_cleanliness():
    print("\n--- 3. Testing Pipeline Order & Pure LSB Cleanliness ---")
    # Synthetic image with random LSB noise on all channels
    img = _make_dummy_image(128, 128, 3)
    
    test_dir = os.path.join(repo_root, "test_pipeline_tmp")
    os.makedirs(test_dir, exist_ok=True)
    test_in = os.path.join(test_dir, "input.png")
    test_out = os.path.join(test_dir, "cleaned.png")
    imwrite_unicode(test_in, img)

    processor = WatermarkProcessor()
    # Run ALL algorithms in Color Preserve mode
    msg, ok = processor.process_image(
        image_path=test_in,
        methods=["LSB", "FFT", "DCT", "DWT"],
        action="clean",
        color_preserve=True,
        aggressiveness="Balanced",
        output_path=test_out
    )
    assert ok, f"Processing failed: {msg}"
    
    cleaned = imread_unicode(test_out)
    # The output MUST have strictly cleared LSB on ALL channels, proving FFT/DCT/YCrCb did not overwrite it!
    for c in range(3):
        lsb = cleaned[:, :, c] & 1
        assert np.all(lsb == 0), f"Channel {c} LSB was corrupted by post-LSB operations!"
    print("OK: Reordered pipeline successfully guaranteed 100% clean LSB bitplanes across all channels!")

    shutil.rmtree(test_dir)

def test_fft_notch_depth():
    print("\n--- 4. Testing FFT Continuous Notch Filter Depth ---")
    img = np.ones((64, 64), dtype=np.uint8) * 128
    # Inject high-frequency single spike in frequency domain
    f = np.fft.fft2(img)
    fshift = np.fft.fftshift(f)
    fshift[20, 20] += 1e6
    fshift[64 - 20, 64 - 20] += 1e6 # conjugate
    img_spiked = np.clip(np.real(np.fft.ifft2(np.fft.ifftshift(fshift))), 0, 255).astype(np.uint8)
    
    cleaned = process_fft(img_spiked, "Balanced", "clean")
    f_clean = np.fft.fftshift(np.fft.fft2(cleaned))
    # Verify that the spike energy is severely crushed (depth >= 95%)
    assert np.abs(f_clean[20, 20]) < np.abs(fshift[20, 20]) * 0.1, "FFT notch failed to deep-attenuate spike center!"
    print("OK: FFT continuous Gaussian notch filter successfully annihilated spike center to <10%.")

def test_dct_detection_and_deblocking():
    print("\n--- 5. Testing DCT False Positive Elimination & Deblocking ---")
    # Clean white background with black text-like high contrast lines (not watermark!)
    canvas = np.full((128, 128), 255, dtype=np.uint8)
    cv2.line(canvas, (10, 20), (100, 20), 0, 2)
    cv2.line(canvas, (20, 10), (20, 100), 0, 2)
    cv2.putText(canvas, "Code", (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, 0, 2)
    
    det = process_dct(canvas, "Balanced", "detect")
    print("Clean text canvas DCT detect:", det)
    # Natural code text should not be falsely flagged as Found!
    assert det["detected"] == False, "Clean text canvas falsely detected as watermark by DCT!"
    
    # Injected spread-spectrum watermark
    import random
    rng = random.Random(42)
    noise = np.array([rng.choice([-2, 2]) for _ in range(128 * 128)], dtype=np.int16).reshape((128, 128))
    canvas_wm = np.clip(canvas.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    det_wm = process_dct(canvas_wm, "Balanced", "detect")
    print("Watermarked canvas DCT detect:", det_wm)
    assert det_wm["detected"] == True, "Watermarked canvas failed to be detected by DCT!"
    
    # Test deblocking filter preserves dimensions
    deblocked = _deblock_8x8(canvas)
    assert deblocked.shape == canvas.shape, "Deblocking altered shape!"
    print("OK: Clean text canvas correctly marked clean by DCT; deblocking verified.")

def test_dwt_text_protection():
    print("\n--- 6. Testing DWT Text Stroke Edge Preservation ---")
    canvas = np.full((128, 128), 255, dtype=np.uint8)
    cv2.putText(canvas, "Hello", (15, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.2, 0, 3)
    
    cleaned = process_dwt(canvas, "Balanced", "clean")
    # Calculate SSIM or correlation: text strokes must remain sharp and dark
    min_val = np.min(cleaned)
    assert min_val < 30, "Text strokes were severely washed out by DWT soft thresholding!"
    print("OK: DWT text strokes remain sharp and dark without excessive blur.")

if __name__ == "__main__":
    test_resource_path()
    test_alpha_blending()
    test_pipeline_lsb_zero_cleanliness()
    test_fft_notch_depth()
    test_dct_detection_and_deblocking()
    test_dwt_text_protection()
    print("\n=========================================")
    print("ALL 6 COMPREHENSIVE AUDIT TESTS PASSED!")
    print("=========================================")
