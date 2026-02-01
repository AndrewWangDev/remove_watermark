import cv2
import numpy as np
import os

class WatermarkProcessor:
    def __init__(self):
        pass

    def detect_watermark(self, image_path):
        try:
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return "Error: Could not load image.", False
            
            # FFT
            f = np.fft.fft2(img)
            fshift = np.fft.fftshift(f)
            magnitude_spectrum = 20 * np.log(np.abs(fshift))
            
            rows, cols = img.shape
            crow, ccol = rows // 2, cols // 2
            
            # Mask out the center (DC component and low frequencies)
            mask_size = 30
            magnitude_spectrum[crow-mask_size:crow+mask_size, ccol-mask_size:ccol+mask_size] = 0
            
            return "Frequency analysis complete. Spectrum generated.", True
            
        except Exception as e:
            return f"Error during detection: {str(e)}", False

    def clean_watermark(self, image_path):
        try:
            img = cv2.imread(image_path, 0) # Load as grayscale for FFT processing

            
            if img is None:
                return "Error: Could not load image."

            f = np.fft.fft2(img)
            fshift = np.fft.fftshift(f)
            rows, cols = img.shape
            crow, ccol = rows // 2, cols // 2

            # Create a mask allowing low frequencies (center)
            mask = np.zeros((rows, cols), np.uint8)
            r = min(rows, cols) // 4  # Keep inner 25% frequencies
            cv2.circle(mask, (ccol, crow), r, 1, thickness=-1)
            
            # Apply mask
            fshift_filtered = fshift * mask
            
            # Inverse FFT
            f_ishift = np.fft.ifftshift(fshift_filtered)
            img_back = np.fft.ifft2(f_ishift)
            img_back = np.abs(img_back)
            
            # Normalize to 0-255
            img_back = cv2.normalize(img_back, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
            
            # Save result
            dir_name, file_name = os.path.split(image_path)
            new_name = os.path.join(dir_name, "cleaned_" + file_name)
            cv2.imwrite(new_name, img_back)
            
            return f"Image cleaned and saved to: {new_name}"

        except Exception as e:
            return f"Error during cleaning: {str(e)}"
