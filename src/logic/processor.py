import cv2
import numpy as np
import os
from .algorithms import process_lsb, process_fft, process_dct, process_dwt

class WatermarkProcessor:
    def __init__(self):
        pass

    def process_image(self, image_path: str, methods: list, action: str, color_preserve: bool, aggressiveness: str, output_path: str, cancel_check=None, rand_name=False, rand_size=False, force_jpeg=False):
        """
        Main entry point for processing an image.
        Returns: (message: str, success: bool) for clean, (results: dict, detected: bool) for detect
        """
        try:
            if not os.path.exists(image_path):
                return "Error: File does not exist.", False

            if color_preserve:
                img = cv2.imread(image_path, cv2.IMREAD_COLOR)
                if img is None:
                    return "Error: Could not load image.", False
                
                # Convert BGR to YCrCb and process Y channel
                ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
                y_channel, cr_channel, cb_channel = cv2.split(ycrcb)
                channel_to_process = y_channel
            else:
                img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
                if img is None:
                    return "Error: Could not load image.", False
                channel_to_process = img
                
            results = {}
            current_channel = channel_to_process.copy()
            
            if "LSB" in methods:
                if cancel_check and cancel_check(): return "Task cancelled by user.", False
                if action == "detect":
                    results["LSB"] = process_lsb(current_channel, aggressiveness, "detect")
                else:
                    current_channel = process_lsb(current_channel, aggressiveness, "clean")
                    
            if "FFT" in methods:
                if cancel_check and cancel_check(): return "Task cancelled by user.", False
                if action == "detect":
                    results["FFT"] = process_fft(current_channel, aggressiveness, "detect")
                else:
                    current_channel = process_fft(current_channel, aggressiveness, "clean")
                    
            if "DCT" in methods:
                if cancel_check and cancel_check(): return "Task cancelled by user.", False
                if action == "detect":
                    results["DCT"] = process_dct(current_channel, aggressiveness, "detect")
                else:
                    # Pass cancel_check down if we want to cancel inner loops, 
                    # but checking here is usually enough for responsiveness
                    current_channel = process_dct(current_channel, aggressiveness, "clean")
                    if current_channel is None: return "Task cancelled by user.", False
                    
            if "DWT" in methods:
                if cancel_check and cancel_check(): return "Task cancelled by user.", False
                if action == "detect":
                    results["DWT"] = process_dwt(current_channel, aggressiveness, "detect")
                else:
                    current_channel = process_dwt(current_channel, aggressiveness, "clean")

            if cancel_check and cancel_check(): return "Task cancelled by user.", False

            if action == "detect":
                if not results:
                    return None, False
                # Always return True for 'success' if the detection process completed without crashing.
                # The actual results dict contains the per-algorithm 'detected' flags.
                return results, True

            # Action is clean
            if not methods:
                return "Error: No clean method selected", False

            if color_preserve:
                merged = cv2.merge([current_channel, cr_channel, cb_channel])
                result_img = cv2.cvtColor(merged, cv2.COLOR_YCrCb2BGR)
            else:
                result_img = current_channel

            if rand_size:
                import random
                h, w = result_img.shape[:2]
                crop_t = random.randint(0, 2)
                crop_b = random.randint(0, 2)
                crop_l = random.randint(0, 2)
                crop_r = random.randint(0, 2)
                if h - crop_t - crop_b > 10 and w - crop_l - crop_r > 10:
                    result_img = result_img[crop_t:h-crop_b, crop_l:w-crop_r]

            out_path_used = output_path
            
            if not out_path_used or out_path_used.startswith("Default"):
                dir_name, file_name = os.path.split(image_path)
                out_path_used = os.path.join(dir_name, "cleaned_" + file_name)
            elif os.path.isdir(out_path_used):
                file_name = os.path.basename(image_path)
                out_path_used = os.path.join(out_path_used, "cleaned_" + file_name)
                
            if force_jpeg:
                base, _ = os.path.splitext(out_path_used)
                out_path_used = base + ".jpg"
            
            if rand_name:
                import random, string
                rand_str = ''.join(random.choices(string.ascii_letters + string.digits, k=9))
                base, ext = os.path.splitext(out_path_used)
                out_path_used = os.path.join(os.path.dirname(base), f"{rand_str}{ext}")
            else:
                # Check if file exists, add numbering if needed
                if os.path.exists(out_path_used):
                    base, ext = os.path.splitext(out_path_used)
                    counter = 1
                    while os.path.exists(f"{base}_{counter}{ext}"):
                        counter += 1
                    out_path_used = f"{base}_{counter}{ext}"
                
            try:
                res = cv2.imwrite(out_path_used, result_img)
                if not res:
                    raise RuntimeError("cv2.imwrite returned False (possibly invalid extension or path)")
            except Exception as e:
                raise RuntimeError(f"Failed to write image to [{out_path_used}]. Error: {e}")
                
            return f"Image cleaned and saved to:\n{out_path_used}", True

        except Exception as e:
            import traceback
            return f"Error during processing: {str(e)}\n{traceback.format_exc()}", False
