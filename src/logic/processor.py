import cv2
import numpy as np
import os
from .algorithms import process_lsb, process_fft, process_dct, process_dwt

def blend_alpha_to_bgr(bgra_img: np.ndarray, bg_color=(255, 255, 255)) -> np.ndarray:
    """
    Composites a 4-channel BGRA image over a solid background color (default white)
    using true Alpha Blending to prevent dark halos and black boundaries in JPEG export.
    """
    if len(bgra_img.shape) != 3 or bgra_img.shape[2] != 4:
        return bgra_img
    bgr = bgra_img[:, :, :3].astype(np.float32)
    alpha = (bgra_img[:, :, 3].astype(np.float32) / 255.0)[:, :, np.newaxis]
    bg = np.array(bg_color, dtype=np.float32)
    blended = bgr * alpha + bg * (1.0 - alpha)
    return np.clip(blended, 0, 255).astype(np.uint8)

def imread_unicode(filepath: str, flags: int = cv2.IMREAD_UNCHANGED) -> np.ndarray:
    """Read an image supporting Unicode, Chinese, and special character paths."""
    try:
        if not os.path.exists(filepath):
            return None
        with open(filepath, 'rb') as f:
            data = np.frombuffer(f.read(), dtype=np.uint8)
        img = cv2.imdecode(data, flags)
        return img
    except Exception:
        return None

def imwrite_unicode(filepath: str, img: np.ndarray, quality: int = 95) -> bool:
    """Save an image supporting Unicode, Chinese, and special character paths."""
    try:
        out_dir = os.path.dirname(os.path.abspath(filepath))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
            
        ext = os.path.splitext(filepath)[1].lower()
        if not ext:
            ext = ".png"
            filepath = filepath + ".png"
            
        params = []
        if ext in [".jpg", ".jpeg"]:
            params = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
            # JPEG format does not support 4-channel Alpha: blend over crisp white background
            if len(img.shape) == 3 and img.shape[2] == 4:
                img = blend_alpha_to_bgr(img, (255, 255, 255))
                
        success, buf = cv2.imencode(ext, img, params)
        if not success:
            return False
            
        with open(filepath, 'wb') as f:
            buf.tofile(f)
        return True
    except Exception:
        return False

class WatermarkProcessor:
    def __init__(self):
        pass

    def process_image(
        self, 
        image_path: str, 
        methods: list, 
        action: str, 
        color_preserve: bool, 
        aggressiveness: str, 
        output_path: str, 
        cancel_check=None, 
        rand_name=False, 
        rand_size=False, 
        force_jpeg=False,
        progress_callback=None
    ):
        """
        Main entry point for processing an image.
        Returns: (message: str, success: bool) for clean, (results: dict, detected: bool) for detect
        """
        try:
            def _report(pct: int, msg: str = ""):
                if progress_callback:
                    progress_callback(pct, msg)

            if not os.path.exists(image_path):
                return "Error: File does not exist.", False

            _report(5, "Loading image...")
            raw_img = imread_unicode(image_path, cv2.IMREAD_UNCHANGED)
            if raw_img is None:
                return "Error: Could not load image (unsupported format or corrupted file).", False

            # Extract Alpha channel if present
            alpha_channel = None
            if len(raw_img.shape) == 3 and raw_img.shape[2] == 4:
                alpha_channel = raw_img[:, :, 3]
                bgr_img = raw_img[:, :, :3]
            elif len(raw_img.shape) == 2:
                bgr_img = cv2.cvtColor(raw_img, cv2.COLOR_GRAY2BGR)
            else:
                bgr_img = raw_img

            if color_preserve:
                ycrcb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2YCrCb)
                y_channel, cr_channel, cb_channel = cv2.split(ycrcb)
                channel_to_process = y_channel
            else:
                channel_to_process = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2GRAY)
                
            results = {}
            current_channel = channel_to_process.copy()
            _report(15, "Initializing processing pipeline...")

            # ----------------------------------------------------
            # DETECTION FLOW
            # ----------------------------------------------------
            if action == "detect":
                algo_map = {
                    "LSB": process_lsb,
                    "FFT": process_fft,
                    "DCT": process_dct,
                    "DWT": process_dwt
                }
                total_methods = len(methods)
                for idx, m_name in enumerate(methods):
                    if cancel_check and cancel_check():
                        return "Task cancelled by user.", False

                    step_pct = 20 + int((idx / max(1, total_methods)) * 75)
                    _report(step_pct, f"Running {m_name} detection...")

                    fn = algo_map.get(m_name)
                    if not fn:
                        continue

                    det_res = fn(current_channel, aggressiveness, "detect", cancel_check=cancel_check)
                    if m_name == "LSB" and alpha_channel is not None:
                        alpha_res = fn(alpha_channel, aggressiveness, "detect", cancel_check=cancel_check)
                        if alpha_res.get("detected"):
                            det_res["detected"] = True
                            det_res["score"] = max(det_res.get("score", 0.0), alpha_res.get("score", 0.0))
                    results[m_name] = det_res

                _report(100, "Detection complete")
                if not results:
                    return None, False
                return results, True

            # ----------------------------------------------------
            # CLEANING FLOW (Corrected Pipeline Ordering)
            # Order: Frequency Filtering (FFT/DCT/DWT) -> Color Reconstruction -> Final LSB Sweep
            # ----------------------------------------------------
            if not methods:
                return "Error: No clean method selected", False

            freq_methods = [m for m in ["FFT", "DCT", "DWT"] if m in methods]
            freq_algo_map = {
                "FFT": process_fft,
                "DCT": process_dct,
                "DWT": process_dwt
            }

            # Phase 1: Frequency domain processing on luminance and chrominance
            for idx, m_name in enumerate(freq_methods):
                if cancel_check and cancel_check():
                    return "Task cancelled by user.", False
                step_pct = 20 + int((idx / max(1, len(freq_methods) + 1)) * 50)
                _report(step_pct, f"Filtering {m_name} artifacts...")

                fn = freq_algo_map[m_name]
                current_channel = fn(current_channel, aggressiveness, "clean", cancel_check=cancel_check)
                if current_channel is None:
                    return "Task cancelled by user.", False

            if cancel_check and cancel_check():
                return "Task cancelled by user.", False

            # Phase 2: Color Space & Channel Reconstruction
            _report(75, "Reconstructing color spaces...")
            if color_preserve:
                if aggressiveness == "Aggressive":
                    cr_channel = cv2.GaussianBlur(cr_channel, (3, 3), 0)
                    cb_channel = cv2.GaussianBlur(cb_channel, (3, 3), 0)
                elif aggressiveness == "Balanced":
                    cr_channel = cv2.medianBlur(cr_channel, 3)
                    cb_channel = cv2.medianBlur(cb_channel, 3)

                merged = cv2.merge([current_channel, cr_channel, cb_channel])
                result_img = cv2.cvtColor(merged, cv2.COLOR_YCrCb2BGR)
            else:
                result_img = current_channel

            # Handle Alpha / Transparency
            if alpha_channel is not None:
                if force_jpeg:
                    # Blend transparent PNG over solid white background before export
                    if len(result_img.shape) == 2:
                        result_img = cv2.cvtColor(result_img, cv2.COLOR_GRAY2BGR)
                    bgra_combined = cv2.merge([result_img[:, :, 0], result_img[:, :, 1], result_img[:, :, 2], alpha_channel])
                    result_img = blend_alpha_to_bgr(bgra_combined, (255, 255, 255))
                else:
                    if len(result_img.shape) == 2:
                        result_img = cv2.cvtColor(result_img, cv2.COLOR_GRAY2BGR)
                    result_img = cv2.merge([result_img[:, :, 0], result_img[:, :, 1], result_img[:, :, 2], alpha_channel])

            # Phase 3: Final All-Channel Spatial LSB Sweep (Ensures zero-noise bit-planes)
            if "LSB" in methods:
                if cancel_check and cancel_check():
                    return "Task cancelled by user.", False
                _report(85, "Neutralizing spatial LSB planes...")
                if len(result_img.shape) == 3:
                    channels = list(cv2.split(result_img))
                    for c_idx in range(len(channels)):
                        channels[c_idx] = process_lsb(channels[c_idx], aggressiveness, "clean")
                    result_img = cv2.merge(channels)
                else:
                    result_img = process_lsb(result_img, aggressiveness, "clean")

            if cancel_check and cancel_check():
                return "Task cancelled by user.", False

            # Phase 4: Privacy Randomization & Output Generation
            if rand_size:
                import random
                h, w = result_img.shape[:2]
                crop_t = random.randint(0, 2)
                crop_b = random.randint(0, 2)
                crop_l = random.randint(0, 2)
                crop_r = random.randint(0, 2)
                if h - crop_t - crop_b > 10 and w - crop_l - crop_r > 10:
                    result_img = result_img[crop_t:h-crop_b, crop_l:w-crop_r]

            out_path_used = output_path.strip() if output_path else ""
            if not out_path_used or out_path_used.startswith("Default"):
                dir_name, file_name = os.path.split(image_path)
                out_path_used = os.path.join(dir_name, "cleaned_" + file_name)
            else:
                _, ext = os.path.splitext(out_path_used)
                is_dir_target = os.path.isdir(out_path_used) or (not ext) or out_path_used.endswith(("/", "\\"))
                if is_dir_target:
                    os.makedirs(out_path_used, exist_ok=True)
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
                if os.path.exists(out_path_used):
                    base, ext = os.path.splitext(out_path_used)
                    counter = 1
                    while os.path.exists(f"{base}_{counter}{ext}"):
                        counter += 1
                    out_path_used = f"{base}_{counter}{ext}"

            _report(94, "Writing output image...")
            save_ok = imwrite_unicode(out_path_used, result_img)
            if not save_ok:
                raise RuntimeError(f"Failed to write image to [{out_path_used}]. Check directory write permissions.")

            _report(100, "Clean complete")
            return f"Image cleaned and saved to:\n{out_path_used}", True

        except Exception as e:
            import traceback
            return f"Error during processing: {str(e)}\n{traceback.format_exc()}", False
