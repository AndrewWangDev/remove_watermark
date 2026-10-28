import numpy as np
import cv2
import pywt

# Precompute standard 8x8 2D-DCT orthogonal basis matrix for vectorized processing
_DCT_N = 8
_DCT_A = np.zeros((_DCT_N, _DCT_N), dtype=np.float32)
for _k in range(_DCT_N):
    for _n in range(_DCT_N):
        _ck = np.sqrt(1.0 / _DCT_N) if _k == 0 else np.sqrt(2.0 / _DCT_N)
        _DCT_A[_k, _n] = _ck * np.cos(np.pi * (2 * _n + 1) * _k / (2.0 * _DCT_N))
_DCT_AT = _DCT_A.T

# Precompute 8x8 mid-frequency mask for blind spread-spectrum watermark detection
_DCT_MID_MASK = np.zeros((8, 8), dtype=bool)
for _u in range(8):
    for _v in range(8):
        if 3 <= (_u + _v) <= 8 and not (_u == 0 and _v == 0):
            _DCT_MID_MASK[_u, _v] = True

def _deblock_8x8(img):
    """
    Lightweight adaptive deblocking filter for 8x8 block boundaries.
    Smooths boundary step discontinuities without blurring internal block contents.
    """
    h, w = img.shape
    out = img.copy()
    
    # Horizontal block boundaries: row indices 8, 16, 24, ...
    for r in range(8, h, 8):
        # 3-tap lowpass across the boundary: [r-1], [r]
        p0 = img[r - 1, :].astype(np.float32)
        q0 = img[r, :].astype(np.float32)
        diff = np.abs(p0 - q0)
        # Only smooth small/subtle quantization steps (< 16), preserving true image edges
        smooth_mask = diff < 16.0
        if np.any(smooth_mask):
            out[r - 1, smooth_mask] = np.clip(0.65 * p0[smooth_mask] + 0.35 * q0[smooth_mask], 0, 255)
            out[r, smooth_mask] = np.clip(0.35 * p0[smooth_mask] + 0.65 * q0[smooth_mask], 0, 255)
            
    # Vertical block boundaries: col indices 8, 16, 24, ...
    for c in range(8, w, 8):
        p0 = out[:, c - 1].astype(np.float32)
        q0 = out[:, c].astype(np.float32)
        diff = np.abs(p0 - q0)
        smooth_mask = diff < 16.0
        if np.any(smooth_mask):
            out[smooth_mask, c - 1] = np.clip(0.65 * p0[smooth_mask] + 0.35 * q0[smooth_mask], 0, 255)
            out[smooth_mask, c] = np.clip(0.35 * p0[smooth_mask] + 0.65 * q0[smooth_mask], 0, 255)
            
    return out

def process_lsb(img_channel, mode, action="clean", cancel_check=None):
    """
    mode: 'Conservative', 'Balanced', 'Aggressive'
    action: 'detect' or 'clean'
    """
    bits_to_clear = 1
    if mode == "Aggressive":
        bits_to_clear = 2
        
    if action == "detect":
        lsb_plane = (img_channel & 1).astype(np.float32)
        h, w = lsb_plane.shape
        if h < 2 or w < 2:
            return {"detected": False, "score": 0.0}

        # Check spatial transition probability / difference energy globally
        # Natural images exhibit spatial correlation in LSB (diff_rate is typically 0.25 ~ 0.44)
        # Pseudo-random / encrypted payloads exhibit Bernoulli white noise (diff_rate -> 0.500)
        diff_h = np.mean(np.abs(lsb_plane[:, :-1] - lsb_plane[:, 1:]))
        diff_v = np.mean(np.abs(lsb_plane[:-1, :] - lsb_plane[1:, :]))
        diff_rate = float((diff_h + diff_v) / 2.0)
        mean_bit = float(np.mean(lsb_plane))
        
        # Vectorized 4D block analysis (64x64) without Python loops for massive performance
        max_local_diff = diff_rate
        if h >= 64 and w >= 64:
            n_r = h // 64
            n_c = w // 64
            # (n_r, 64, n_c, 64) -> (n_r, n_c, 64, 64)
            blocks = lsb_plane[:n_r * 64, :n_c * 64].reshape(n_r, 64, n_c, 64).transpose(0, 2, 1, 3)
            blk_means = np.mean(blocks, axis=(-2, -1))
            balanced_mask = np.abs(blk_means - 0.5) < 0.05
            
            dh = np.mean(np.abs(blocks[:, :, :, :-1] - blocks[:, :, :, 1:]), axis=(-2, -1))
            dv = np.mean(np.abs(blocks[:, :, :-1, :] - blocks[:, :, 1:, :]), axis=(-2, -1))
            diffs = (dh + dv) / 2.0
            
            valid_diffs = diffs[balanced_mask]
            if len(valid_diffs) > 0:
                max_local_diff = float(np.max(valid_diffs))
        
        # Global payload or strong local payload
        is_global_payload = (diff_rate > 0.485) and (abs(mean_bit - 0.5) < 0.02)
        is_local_payload = (max_local_diff > 0.492)
        
        detected = bool(is_global_payload or is_local_payload)
        score_val = max(diff_rate, max_local_diff)
        return {"detected": detected, "score": float(round(score_val, 4))}
        
    if action == "clean":
        mask = 255 - ((1 << bits_to_clear) - 1)
        cleaned = img_channel & mask
        return cleaned

def process_fft(img_channel, mode, action="clean", cancel_check=None):
    rows, cols = img_channel.shape
    if rows < 16 or cols < 16:
        if action == "detect":
            return {"detected": False, "score": 0.0}
        return img_channel.copy()

    f = np.fft.fft2(img_channel)
    fshift = np.fft.fftshift(f)
    magnitude_spectrum = 20 * np.log(np.abs(fshift) + 1e-8)
    
    mean_val = float(np.mean(magnitude_spectrum))
    std_val = float(np.std(magnitude_spectrum))
    
    threshold_factor = 5.0
    if mode == "Conservative":
        threshold_factor = 7.0
    elif mode == "Aggressive":
        threshold_factor = 3.5
        
    threshold = mean_val + threshold_factor * std_val
    
    crow, ccol = rows // 2, cols // 2
    
    # Adaptive DC center protection radius based on resolution
    center_mask_radius = max(8, int(min(rows, cols) * 0.04))
    temp_spectrum = magnitude_spectrum.copy()
    cv2.circle(temp_spectrum, (ccol, crow), center_mask_radius, 0, -1)
    
    # Mask vertical and horizontal axes to ignore natural image boundaries
    temp_spectrum[max(0, crow - 2):min(rows, crow + 3), :] = 0
    temp_spectrum[:, max(0, ccol - 2):min(cols, ccol + 3)] = 0
    
    spikes = temp_spectrum > threshold
    detected = bool(np.any(spikes))
    
    if action == "detect":
        max_val = float(np.max(temp_spectrum))
        snr_score = max_val - mean_val
        return {"detected": detected, "score": float(round(snr_score, 2))}
        
    if action == "clean":
        if cancel_check and cancel_check():
            return None

        notch_radius = 2
        if mode == "Aggressive":
            notch_radius = 5
        elif mode == "Conservative":
            notch_radius = 1
            
        # Efficient vectorized morphological dilation
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * notch_radius + 1, 2 * notch_radius + 1))
        dilated_spikes = cv2.dilate(spikes.astype(np.uint8), kernel)
        
        # Enforce conjugate symmetry F(-u, -v) = F*(u, v) around center to avoid spatial phase distortion
        shift_r = 1 if rows % 2 == 0 else 0
        shift_c = 1 if cols % 2 == 0 else 0
        rotated_spikes = np.rot90(dilated_spikes, 2)
        if shift_r != 0 or shift_c != 0:
            rotated_spikes = np.roll(rotated_spikes, (shift_r, shift_c), axis=(0, 1))

        dilated_symmetric = np.maximum(dilated_spikes, rotated_spikes)
        
        # Build continuous Gaussian notch filter via distanceTransform
        # This ensures the notch strictly reaches 0.0 at spike centers (100% attenuation)
        # while transitioning smoothly outward without Gibbs ringing or central blur wash-out
        if np.any(dilated_symmetric):
            dist = cv2.distanceTransform(1 - dilated_symmetric, cv2.DIST_L2, 3)
            sigma = max(1.5, float(notch_radius) * 0.8)
            mask = 1.0 - np.exp(-(dist ** 2) / (2.0 * (sigma ** 2)))
            mask = np.clip(mask, 0.0, 1.0).astype(np.float32)
        else:
            mask = np.ones((rows, cols), dtype=np.float32)
        
        fshift_filtered = fshift * mask
        f_ishift = np.fft.ifftshift(fshift_filtered)
        img_back = np.fft.ifft2(f_ishift)
        
        # Take real part to strictly preserve luminance and contrast
        img_back = np.real(img_back)
        return np.clip(img_back, 0, 255).astype(np.uint8)

def process_dct(img_channel, mode, action="clean", cancel_check=None):
    rows, cols = img_channel.shape
    if rows < 8 or cols < 8:
        if action == "detect":
            return {"detected": False, "score": 0.0}
        return img_channel.copy()
    
    pad_rows = (8 - rows % 8) % 8
    pad_cols = (8 - cols % 8) % 8
    
    if pad_rows > 0 or pad_cols > 0:
        img_padded = np.pad(img_channel, ((0, pad_rows), (0, pad_cols)), mode='reflect')
    else:
        img_padded = img_channel.copy()
        
    padded_rows, padded_cols = img_padded.shape
    num_blocks_r = padded_rows // 8
    num_blocks_c = padded_cols // 8
    
    # Fully vectorized block reshaping: (num_r, 8, num_c, 8) -> (num_r, num_c, 8, 8)
    blocks = img_padded.reshape(num_blocks_r, 8, num_blocks_c, 8).transpose(0, 2, 1, 3).astype(np.float32)
    
    # 2D-DCT on all blocks simultaneously via matrix product: A @ blocks @ A.T
    blocks_dct = _DCT_A @ blocks @ _DCT_AT
    
    if action == "detect":
        # Measure mid-frequency AC coefficient energy and its dispersion
        # Text/UI edges have high AC only at sparse stroke boundaries (p25 == 0, cv > 1.5).
        # A true spread-spectrum watermark injects perturbation uniformly across all blocks,
        # lifting smooth background baseline (p25_ac > 20.0 with mid_ratio > 0.40).
        ac_energy_per_block = np.sum(np.abs(blocks_dct), axis=(-1, -2)) - np.abs(blocks_dct[:, :, 0, 0])
        mid_energy_per_block = np.sum(np.abs(blocks_dct[:, :, _DCT_MID_MASK]), axis=-1)
        
        total_ac = float(np.sum(ac_energy_per_block))
        total_mid = float(np.sum(mid_energy_per_block))
        global_mid_ratio = float(total_mid / total_ac) if total_ac > 1.0 else 0.0
        
        p25_ac = float(np.percentile(ac_energy_per_block, 25))
        p90_ac = float(np.percentile(ac_energy_per_block, 90))
        mean_ac = float(np.mean(ac_energy_per_block))
        std_ac = float(np.std(ac_energy_per_block))
        cv = std_ac / (mean_ac + 1e-5)
        
        threshold_ac = 2200.0 if mode == "Conservative" else (1600.0 if mode == "Balanced" else 1200.0)
        
        is_watermark = False
        if p25_ac > 20.0 and global_mid_ratio > 0.40:
            is_watermark = True
        elif p90_ac > threshold_ac and global_mid_ratio > 0.45 and cv < 1.3:
            is_watermark = True
            
        score_val = float(round(p25_ac * 10.0 + p90_ac * global_mid_ratio * 0.05, 2))
        return {"detected": bool(is_watermark), "score": score_val}
        
    if action == "clean":
        if cancel_check and cancel_check():
            return None

        # Standard JPEG Luminance Quantization Matrix
        Q_base = np.array([
            [16, 11, 10, 16, 24, 40, 51, 61],
            [12, 12, 14, 19, 26, 58, 60, 55],
            [14, 13, 16, 24, 40, 57, 69, 56],
            [14, 17, 22, 29, 51, 87, 80, 62],
            [18, 22, 37, 56, 68, 109, 103, 77],
            [24, 35, 55, 64, 81, 104, 113, 92],
            [49, 64, 78, 87, 103, 121, 120, 101],
            [72, 92, 95, 98, 112, 100, 103, 99]
        ], dtype=np.float32)
        
        q_factor = 0.5
        if mode == "Aggressive":
            q_factor = 1.0
        elif mode == "Conservative":
            q_factor = 0.2
            
        quant_matrix = np.maximum(Q_base * q_factor, 1.0)
        
        # Vectorized quantization across all blocks
        blocks_q = np.round(blocks_dct / quant_matrix) * quant_matrix
        # Strictly preserve exact DC coefficients to retain original luminance
        blocks_q[:, :, 0, 0] = blocks_dct[:, :, 0, 0]
        
        # Vectorized 2D-IDCT: A.T @ blocks_q @ A
        blocks_cleaned = _DCT_AT @ blocks_q @ _DCT_A
        
        # Reconstruct full image
        cleaned_padded = blocks_cleaned.transpose(0, 2, 1, 3).reshape(padded_rows, padded_cols)
        
        # Apply boundary deblocking filter to eliminate 8x8 blocking artifacts on lossless screenshots
        cleaned_deblocked = _deblock_8x8(cleaned_padded)
        cleaned = cleaned_deblocked[:rows, :cols]
        return np.clip(cleaned, 0, 255).astype(np.uint8)

def process_dwt(img_channel, mode, action="clean", cancel_check=None):
    rows, cols = img_channel.shape
    if rows < 16 or cols < 16:
        if action == "detect":
            return {"detected": False, "score": 0.0}
        return img_channel.copy()

    wavelet = 'db4'
    coeffs2 = pywt.dwt2(img_channel, wavelet)
    LL, (LH, HL, HH) = coeffs2
    
    # Robust noise standard deviation estimate using Donoho's VisuShrink (median of absolute HH / 0.6745)
    sigma = float(np.median(np.abs(HH)) / 0.6745)
    
    if action == "detect":
        hh_energy = float(np.var(HH))
        ll_energy = float(np.var(LL)) + 1e-6
        ratio = (hh_energy / ll_energy) * 1000.0
        
        threshold = 300.0 if mode == "Conservative" else 150.0
        detected = bool(hh_energy > threshold and ratio > 1.0)
        return {"detected": detected, "score": float(round(hh_energy, 2))}
        
    if action == "clean":
        if cancel_check and cancel_check():
            return None

        # Adaptive threshold based on estimated noise sigma
        base_thresh = max(1.0, sigma * 1.5)
        if mode == "Aggressive":
            threshold = base_thresh * 2.2
        elif mode == "Conservative":
            threshold = base_thresh * 0.7
        else:
            threshold = base_thresh * 1.3
            
        # Protect text strokes: apply soft thresholding strictly to diagonal details (HH)
        # where high-frequency invisible watermarks hide.
        # For horizontal (LH) and vertical (HL) subbands containing critical text stroke edges,
        # apply mild dead-zone filtering to preserve crisp font contours.
        HH_t = pywt.threshold(HH, threshold, mode='soft')
        LH_t = pywt.threshold(LH, threshold * 0.4, mode='greater')
        HL_t = pywt.threshold(HL, threshold * 0.4, mode='greater')
        
        coeffs2_t = LL, (LH_t, HL_t, HH_t)
        reconstructed = pywt.idwt2(coeffs2_t, wavelet)
        
        reconstructed = reconstructed[:rows, :cols]
        return np.clip(reconstructed, 0, 255).astype(np.uint8)
