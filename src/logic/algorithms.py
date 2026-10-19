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

def process_lsb(img_channel, mode, action="clean"):
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

        # Calculate spatial transition probability / difference energy
        # Natural images exhibit spatial correlation in LSB, diff_rate is typically 0.25 ~ 0.44
        # Pseudo-random / encrypted watermark payloads exhibit Bernoulli white noise (diff_rate -> 0.500)
        diff_h = np.mean(np.abs(lsb_plane[:, :-1] - lsb_plane[:, 1:]))
        diff_v = np.mean(np.abs(lsb_plane[:-1, :] - lsb_plane[1:, :]))
        diff_rate = float((diff_h + diff_v) / 2.0)
        mean_bit = float(np.mean(lsb_plane))
        
        # An image with payload has both diff_rate close to 0.5 and balanced 0/1 ratio
        is_random_payload = (diff_rate > 0.485) and (abs(mean_bit - 0.5) < 0.02)
        
        # Cleaned images (LSB cleared) have diff_rate == 0
        detected = bool(is_random_payload)
        return {"detected": detected, "score": float(round(diff_rate, 4))}
        
    if action == "clean":
        mask = 255 - ((1 << bits_to_clear) - 1)
        cleaned = img_channel & mask
        return cleaned

def process_fft(img_channel, mode, action="clean"):
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
        notch_radius = 2
        if mode == "Aggressive":
            notch_radius = 5
        elif mode == "Conservative":
            notch_radius = 1
            
        # Efficient vectorized morphological dilation instead of point-by-point cv2.circle
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * notch_radius + 1, 2 * notch_radius + 1))
        dilated_spikes = cv2.dilate(spikes.astype(np.uint8), kernel)
        
        # Enforce conjugate symmetry F(-u, -v) = F*(u, v) around center to avoid spatial phase distortion
        dilated_symmetric = np.maximum(dilated_spikes, np.rot90(dilated_spikes, 2))
        mask = 1.0 - dilated_symmetric.astype(np.float32)
        
        # Smooth mask with Gaussian blur to prevent Gibbs ringing artifacts
        mask = cv2.GaussianBlur(mask, (5, 5), 0)
        
        fshift_filtered = fshift * mask
        f_ishift = np.fft.ifftshift(fshift_filtered)
        img_back = np.fft.ifft2(f_ishift)
        
        # Take real part to strictly preserve luminance and contrast (not np.abs which reverses phases)
        img_back = np.real(img_back)
        return np.clip(img_back, 0, 255).astype(np.uint8)

def process_dct(img_channel, mode, action="clean"):
    rows, cols = img_channel.shape
    
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
        # Global analysis: calculate AC energy across all blocks
        ac_energy_per_block = np.sum(np.abs(blocks_dct), axis=(-1, -2)) - np.abs(blocks_dct[:, :, 0, 0])
        # Watermark embedding typically creates consistent artificial high-frequency/mid-frequency AC energy
        mean_ac = float(np.mean(ac_energy_per_block))
        p90_ac = float(np.percentile(ac_energy_per_block, 90))
        
        # Baseline heuristic: natural images have varied AC depending on texture, but structured watermarks
        # create uniform elevated AC energy. Score reflects the 90th percentile AC energy
        threshold = 2200.0 if mode == "Conservative" else (1600.0 if mode == "Balanced" else 1200.0)
        detected = bool(p90_ac > threshold)
        return {"detected": detected, "score": float(round(p90_ac, 2))}
        
    if action == "clean":
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
        cleaned = cleaned_padded[:rows, :cols]
        return np.clip(cleaned, 0, 255).astype(np.uint8)

def process_dwt(img_channel, mode, action="clean"):
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
        # Natural images have high edge energy in LH/HL, artificial noise/watermarks inflate HH relative to LL
        hh_energy = float(np.var(HH))
        # Relative ratio against LL baseline
        ll_energy = float(np.var(LL)) + 1e-6
        ratio = (hh_energy / ll_energy) * 1000.0
        
        threshold = 300.0 if mode == "Conservative" else 150.0
        detected = bool(hh_energy > threshold and ratio > 1.0)
        return {"detected": detected, "score": float(round(hh_energy, 2))}
        
    if action == "clean":
        # Adaptive threshold based on estimated noise sigma
        base_thresh = max(1.0, sigma * 1.5)
        if mode == "Aggressive":
            threshold = base_thresh * 2.5
        elif mode == "Conservative":
            threshold = base_thresh * 0.8
        else:
            threshold = base_thresh * 1.5
            
        LH_t = pywt.threshold(LH, threshold, mode='soft')
        HL_t = pywt.threshold(HL, threshold, mode='soft')
        HH_t = pywt.threshold(HH, threshold, mode='soft')
        
        coeffs2_t = LL, (LH_t, HL_t, HH_t)
        reconstructed = pywt.idwt2(coeffs2_t, wavelet)
        
        reconstructed = reconstructed[:rows, :cols]
        return np.clip(reconstructed, 0, 255).astype(np.uint8)
