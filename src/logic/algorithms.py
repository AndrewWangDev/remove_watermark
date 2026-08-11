import numpy as np
import cv2
import pywt
from scipy.fftpack import dct, idct

def _dct2(block):
    return dct(dct(block.T, norm='ortho').T, norm='ortho')

def _idct2(block):
    return idct(idct(block.T, norm='ortho').T, norm='ortho')

def process_lsb(img_channel, mode, action="clean"):
    """
    mode: 'Conservative', 'Balanced', 'Aggressive'
    action: 'detect' or 'clean'
    """
    bits_to_clear = 1
    if mode == "Aggressive":
        bits_to_clear = 2
        
    if action == "detect":
        lsb_plane = img_channel & 1
        variance = np.var(lsb_plane)
        # Random noise variance is ~0.25. Encrypted payloads are perfectly 0.25.
        # Natural images are close, but usually not EXACTLY 0.25.
        # A cleaned image (LSB=0) has variance 0.
        score = abs(variance - 0.25)
        detected = score < 0.005 # Tight threshold around 0.25
        return {"detected": bool(detected), "score": float(variance)}
        
    if action == "clean":
        mask = 255 - ((1 << bits_to_clear) - 1)
        cleaned = img_channel & mask
        return cleaned

def process_fft(img_channel, mode, action="clean"):
    f = np.fft.fft2(img_channel)
    fshift = np.fft.fftshift(f)
    magnitude_spectrum = 20 * np.log(np.abs(fshift) + 1e-8)
    
    mean_val = np.mean(magnitude_spectrum)
    std_val = np.std(magnitude_spectrum)
    
    threshold_factor = 5.0
    if mode == "Conservative":
        threshold_factor = 7.0
    elif mode == "Aggressive":
        threshold_factor = 3.5
        
    threshold = mean_val + threshold_factor * std_val
    
    rows, cols = img_channel.shape
    crow, ccol = rows // 2, cols // 2
    
    center_mask_radius = 50
    temp_spectrum = magnitude_spectrum.copy()
    cv2.circle(temp_spectrum, (ccol, crow), center_mask_radius, 0, -1)
    
    # Mask vertical and horizontal axes to ignore natural image boundaries
    temp_spectrum[crow-2:crow+3, :] = 0
    temp_spectrum[:, ccol-2:ccol+3] = 0
    
    spikes = temp_spectrum > threshold
    detected = np.any(spikes)
    
    if action == "detect":
        score = float(np.max(temp_spectrum)) if detected else float(np.max(temp_spectrum))
        return {"detected": bool(detected), "score": score}
        
    if action == "clean":
        notch_radius = 2
        if mode == "Aggressive":
            notch_radius = 5
        elif mode == "Conservative":
            notch_radius = 1
            
        mask = np.ones((rows, cols), np.float32)
        
        y_coords, x_coords = np.where(spikes)
        for y, x in zip(y_coords, x_coords):
            cv2.circle(mask, (x, y), notch_radius, 0, -1)
            
        # Smooth the mask to prevent Gibbs ringing!
        mask = cv2.GaussianBlur(mask, (5, 5), 0)
        
        fshift_filtered = fshift * mask
        f_ishift = np.fft.ifftshift(fshift_filtered)
        img_back = np.fft.ifft2(f_ishift)
        img_back = np.abs(img_back)
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
        q_factor = 1.2
    elif mode == "Conservative":
        q_factor = 0.2
        
    quant_matrix = np.maximum(Q_base * q_factor, 1.0)
        
    if action == "detect":
        # Heuristic: analyze AC coefficient energy of the first block as a proxy
        dct_block = _dct2(img_padded[0:8, 0:8])
        ac_energy = np.sum(np.abs(dct_block)) - np.abs(dct_block[0, 0])
        # Cleaned/Natural images often have different AC profiles. High AC energy -> anomalies
        detected = ac_energy > 1500
        return {"detected": bool(detected), "score": float(ac_energy)}
        
    if action == "clean":
        cleaned_padded = np.zeros_like(img_padded, dtype=np.float32)
        for r in range(0, padded_rows, 8):
            for c in range(0, padded_cols, 8):
                block = img_padded[r:r+8, c:c+8]
                dct_block = _dct2(block)
                
                # Quantize using perceptual matrix instead of flat scalar to preserve quality
                dct_block_quantized = np.round(dct_block / quant_matrix) * quant_matrix
                dct_block_quantized[0, 0] = dct_block[0, 0] # Restore exact DC
                
                cleaned_padded[r:r+8, c:c+8] = _idct2(dct_block_quantized)
                
        cleaned = cleaned_padded[:rows, :cols]
        return np.clip(cleaned, 0, 255).astype(np.uint8)

def process_dwt(img_channel, mode, action="clean"):
    # db4 is much smoother than haar. Haar causes severe square grid artifacts!
    wavelet = 'db4' 
    coeffs2 = pywt.dwt2(img_channel, wavelet)
    LL, (LH, HL, HH) = coeffs2
    
    if action == "detect":
        var_hh = np.var(HH)
        return {"detected": bool(var_hh > 250), "score": float(var_hh)}
        
    if action == "clean":
        threshold = 5
        if mode == "Aggressive":
            threshold = 15
        elif mode == "Conservative":
            threshold = 2
            
        LH_t = pywt.threshold(LH, threshold, mode='soft')
        HL_t = pywt.threshold(HL, threshold, mode='soft')
        HH_t = pywt.threshold(HH, threshold, mode='soft')
        
        coeffs2_t = LL, (LH_t, HL_t, HH_t)
        reconstructed = pywt.idwt2(coeffs2_t, wavelet)
        
        rows, cols = img_channel.shape
        reconstructed = reconstructed[:rows, :cols]
        return np.clip(reconstructed, 0, 255).astype(np.uint8)
