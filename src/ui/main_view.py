import os
import sys
import datetime
import threading
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk

# Ensure logic module can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from logic.processor import WatermarkProcessor

class WatermarkApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Watermark Detector & Cleaner")
        self.geometry("1100x700")
        self.minsize(900, 600)
        
        try:
            import ctypes
            myappid = 'andrewwangdev.removewatermark.pro.1.0'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass
        
        try:
            import os
            ico_path = os.path.join(os.path.dirname(__file__), "..", "..", "logo.ico")
            if os.path.exists(ico_path):
                self.after(200, lambda: self.iconbitmap(ico_path))
            elif os.path.exists("logo.ico"):
                self.after(200, lambda: self.iconbitmap("logo.ico"))
        except Exception:
            pass

        try:
            from PIL import Image
            png_path = os.path.join(os.path.dirname(__file__), "..", "..", "logo.png")
            if os.path.exists(png_path):
                self._ctk_logo = ctk.CTkImage(light_image=Image.open(png_path), dark_image=Image.open(png_path), size=(64, 64))
            elif os.path.exists("logo.png"):
                self._ctk_logo = ctk.CTkImage(light_image=Image.open("logo.png"), dark_image=Image.open("logo.png"), size=(64, 64))
        except Exception:
            pass

        # Configure grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        # Global Config State
        self.hide_slow_warning = False
        self.cancel_flag = False

        self._build_ui()
        self._redirect_stdout()

    def _build_ui(self):
        # 1. Header Frame
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        title_lbl = ctk.CTkLabel(header_frame, text="Watermark Detector & Cleaner", font=ctk.CTkFont(size=24, weight="bold"))
        title_lbl.grid(row=0, column=0, sticky="w")

        # About Us button
        self.about_btn = ctk.CTkButton(header_frame, text="About Us", width=80, fg_color="transparent", border_width=1, command=self._show_about_dialog, text_color=("black", "white"))
        self.about_btn.grid(row=0, column=1, padx=(0, 10), sticky="e")

        # Theme toggle
        self.theme_switch = ctk.CTkSwitch(header_frame, text="Dark Mode", command=self._toggle_theme)
        self.theme_switch.select() # Default Dark
        self.theme_switch.grid(row=0, column=2, sticky="e")

        # 2. Main Config Area
        config_frame = ctk.CTkFrame(self)
        config_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        config_frame.grid_columnconfigure(1, weight=1)

        # File selection
        # Input
        ctk.CTkLabel(config_frame, text="Input Image:").grid(row=0, column=0, padx=10, pady=(15, 5), sticky="w")
        self.input_path_var = ctk.StringVar(value="No image selected")
        input_entry = ctk.CTkEntry(config_frame, textvariable=self.input_path_var, state="disabled")
        input_entry.grid(row=0, column=1, padx=10, pady=(15, 5), sticky="ew")
        ctk.CTkButton(config_frame, text="Browse...", command=self._pick_input).grid(row=0, column=2, padx=10, pady=(15, 5))

        # Output
        ctk.CTkLabel(config_frame, text="Output Directory:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.output_path_var = ctk.StringVar(value="")
        output_entry = ctk.CTkEntry(config_frame, textvariable=self.output_path_var)
        output_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        ctk.CTkButton(config_frame, text="Browse...", command=self._pick_output).grid(row=1, column=2, padx=10, pady=5)

        # Options frame (holds algorithms, mode, and privacy settings)
        options_frame = ctk.CTkFrame(config_frame, fg_color="transparent")
        options_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=(5, 10), sticky="ew")

        # Row 0: Detection Methods
        ctk.CTkLabel(options_frame, text="Detection Methods:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=(0, 15), pady=10, sticky="w")
        
        methods_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        methods_frame.grid(row=0, column=1, sticky="w")
        
        self.cb_lsb = ctk.CTkCheckBox(methods_frame, text="LSB (Spatial)")
        self.cb_fft = ctk.CTkCheckBox(methods_frame, text="FFT (Frequency)")
        self.cb_dct = ctk.CTkCheckBox(methods_frame, text="DCT (Frequency)")
        self.cb_dwt = ctk.CTkCheckBox(methods_frame, text="DWT (Wavelet)")
        
        self.cb_lsb.pack(side="left", padx=(0, 20))
        self.cb_fft.pack(side="left", padx=(0, 20))
        self.cb_dct.pack(side="left", padx=(0, 20))
        self.cb_dwt.pack(side="left", padx=(0, 20))

        for cb in (self.cb_lsb, self.cb_fft, self.cb_dct, self.cb_dwt):
            cb.select()

        # Row 1: Clearance Mode
        ctk.CTkLabel(options_frame, text="Clearance Mode:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=(0, 15), pady=10, sticky="w")
        
        mode_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        mode_frame.grid(row=1, column=1, sticky="w")
        
        self.mode_slider = ctk.CTkSlider(mode_frame, from_=0, to=2, number_of_steps=2, width=150, command=self._on_mode_change)
        self.mode_slider.set(1)
        self.mode_slider.pack(side="left", padx=(0, 15))
        
        self.mode_lbl = ctk.CTkLabel(mode_frame, text="Balanced", text_color="#C678DD", font=ctk.CTkFont(weight="bold"), width=90, anchor="w")
        self.mode_lbl.pack(side="left")

        # Row 2: Privacy Enhanced & Advanced
        ctk.CTkLabel(options_frame, text="Privacy Enhanced:", text_color="#98C379", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, padx=(0, 15), pady=10, sticky="w")
        
        privacy_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        privacy_frame.grid(row=2, column=1, sticky="w")
        
        self.cb_color = ctk.CTkSwitch(privacy_frame, text="Preserve Colors")
        self.cb_color.select()
        self.cb_color.pack(side="left", padx=(0, 30))
        
        self.cb_rand_name = ctk.CTkSwitch(privacy_frame, text="Rand Name")
        self.cb_rand_name.pack(side="left", padx=(0, 30))

        self.cb_rand_size = ctk.CTkSwitch(privacy_frame, text="Rand Size")
        self.cb_rand_size.pack(side="left", padx=(0, 30))
        
        self.cb_force_jpeg = ctk.CTkSwitch(privacy_frame, text="Force JPEG")
        self.cb_force_jpeg.pack(side="left", padx=(0, 30))

        # Action Buttons
        actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        actions_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        actions_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(actions_frame, text="Detect Watermarks", height=40, command=lambda: self._trigger_action("detect")).grid(row=0, column=0, padx=5, sticky="ew")
        ctk.CTkButton(actions_frame, text="Clean & Save", height=40, fg_color="#2FA572", hover_color="#1F7A50", command=lambda: self._trigger_action("clean")).grid(row=0, column=1, padx=5, sticky="ew")

        # 3. Log Output Area
        log_frame = ctk.CTkFrame(self, fg_color="#1E1E1E") # Match terminal background
        log_frame.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="nsew")
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        
        # Terminal-style textbox
        self.log_box = ctk.CTkTextbox(
            log_frame, 
            state="disabled", 
            wrap="word", 
            font=ctk.CTkFont(family="Consolas", size=13),
            fg_color="#1E1E1E", # Terminal background
            text_color="#CCCCCC" # Default terminal text
        )
        self.log_box.grid(row=0, column=0, padx=5, pady=(5, 0), sticky="nsew")
        
        # Overlay for Copy and Clear buttons
        overlay = ctk.CTkFrame(log_frame, fg_color="transparent")
        overlay.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)
        
        btn_copy = ctk.CTkButton(overlay, text="Copy", width=40, height=24, font=ctk.CTkFont(size=11), fg_color="#333333", hover_color="#555555", command=self._copy_log)
        btn_copy.pack(side="left", padx=2)
        
        btn_clear = ctk.CTkButton(overlay, text="Clear", width=40, height=24, font=ctk.CTkFont(size=11), fg_color="#333333", hover_color="#555555", command=self._clear_log)
        btn_clear.pack(side="left")

        # Configure colorful tags
        self.log_box.tag_config("timestamp", foreground="#888888")
        self.log_box.tag_config("info", foreground="#56B6C2") # Cyan
        self.log_box.tag_config("success", foreground="#98C379") # Green
        self.log_box.tag_config("error", foreground="#E06C75") # Red
        self.log_box.tag_config("warning", foreground="#E5C07B") # Yellow
        self.log_box.tag_config("highlight", foreground="#C678DD") # Purple

        self.log("System initialized. Ready.", level="info")

    def log(self, msg: str, level: str = "normal"):
        self.log_box.configure(state="normal")
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        # Auto-detect level if not explicitly provided
        if level == "normal":
            if "Error" in msg or "Failed" in msg:
                level = "error"
            elif "Successfully" in msg:
                level = "success"
            elif "Found" in msg and "Not" not in msg:
                level = "warning"
            elif "Not Found" in msg:
                level = "success"
            elif "---" in msg:
                level = "highlight"

        self.log_box.insert("end", f"[{timestamp}] ", "timestamp")
        
        if level != "normal":
            self.log_box.insert("end", f"{msg}\n", level)
        else:
            self.log_box.insert("end", f"{msg}\n")
            
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _redirect_stdout(self):
        class StdoutRedirector:
            def __init__(self, log_func):
                self.log_func = log_func
            def write(self, string):
                if string.strip():
                    self.log_func(string.strip())
            def flush(self):
                pass
        # Commented out so terminal stdout isn't fully suppressed, but we could do it.
        # sys.stdout = StdoutRedirector(self.log)

    def _show_about_dialog(self):
        about = ctk.CTkToplevel(self)
        about.attributes("-alpha", 0.0)
        about.overrideredirect(True)
        about.geometry("600x380")
        about.transient(self)
        
        # Center the about dialog over the main window
        about.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (600 // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (380 // 2)
        about.geometry(f"600x380+{int(x)}+{int(y)}")
        
        main_frame = ctk.CTkFrame(about, border_width=2, border_color="#58a6ff", corner_radius=10)
        main_frame.pack(fill="both", expand=True)
        
        def on_main_click(event):
            if about.winfo_exists():
                about.destroy()
            self.unbind("<Button-1>", bind_id)
        bind_id = self.bind("<Button-1>", on_main_click, add="+")

        if hasattr(self, '_ctk_logo'):
            lbl_logo = ctk.CTkLabel(main_frame, text="", image=self._ctk_logo)
            lbl_logo.pack(pady=(20, 5))
            
        ctk.CTkLabel(main_frame, text="Watermark Detector & Cleaner", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=2)
        ctk.CTkLabel(main_frame, text="Author: Andrew Wang Dev", text_color="gray").pack(pady=2)
        ctk.CTkLabel(main_frame, text="Detect and Remove hidden watermark in the screenshot && Randomize fingerprint to avoid tracking.", wraplength=500).pack(pady=(10, 15))
        
        links_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        links_frame.pack(pady=5)
        
        import webbrowser
        def make_link(parent, text, url):
            lbl = ctk.CTkLabel(parent, text=text, text_color="#58a6ff", cursor="hand2", font=ctk.CTkFont(underline=True))
            lbl.pack(side="left", padx=15)
            lbl.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))

        make_link(links_frame, "Open Source", "https://github.com/AndrewWangDev/remove_watermark")
        make_link(links_frame, "Terms of Service", "https://api.andrewwangdev.com/terms")
        make_link(links_frame, "Privacy Policy", "https://api.andrewwangdev.com/privacy")
        make_link(links_frame, "License", "https://opensource.org/license/mit")
        
        ctk.CTkLabel(main_frame, text="Acknowledgments: We gratefully acknowledge the OpenCV community.").pack(pady=(20, 2))
        ctk.CTkLabel(main_frame, text="Contact us: support@andrewwangdev.com").pack(pady=2)
        
        ctk.CTkButton(main_frame, text="Close", width=100, command=about.destroy).pack(pady=(15, 10))
        
        about.after(50, lambda: about.attributes("-alpha", 1.0))

    def _toggle_theme(self):
        if self.theme_switch.get() == 1:
            ctk.set_appearance_mode("Dark")
        else:
            ctk.set_appearance_mode("Light")

    def _pick_input(self):
        path = filedialog.askopenfilename(title="Select Image", filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp")])
        if path:
            self.input_path_var.set(path)
            self.log(f"Selected input: {path}")

    def _pick_output(self):
        path = filedialog.askdirectory(title="Select Output Directory")
        if path:
            self.output_path_var.set(path)
            self.log(f"Selected output directory: {path}")

    def _on_mode_change(self, val):
        modes = ["Conservative", "Balanced", "Aggressive"]
        colors = ["#56B6C2", "#C678DD", "#E06C75"] # Cyan, Purple, Red
        idx = int(round(float(val)))
        
        # Aggressive warning popup
        if idx == 2 and not getattr(self, 'hide_aggressive_warning', False) and not getattr(self, 'warning_open', False):
            self.warning_open = True
            
            dialog = ctk.CTkToplevel(self)
            dialog.title("Warning")
            dialog.geometry("450x150")
            dialog.attributes("-topmost", True)
            dialog.grab_set()
            
            ctk.CTkLabel(dialog, text="Aggressive mode may severely degrade image quality.\nIt is only recommended for completely destroying stubborn watermarks.\nAre you sure you want to proceed?", wraplength=400).pack(pady=(20, 10))
            
            def btn_continue():
                self.warning_open = False
                dialog.destroy()
                
            def btn_dont_show():
                self.hide_aggressive_warning = True
                self.warning_open = False
                dialog.destroy()
                
            def btn_cancel():
                self.mode_slider.set(1)
                self.mode_lbl.configure(text=modes[1], text_color=colors[1])
                self.warning_open = False
                dialog.destroy()
                
            btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
            btn_frame.pack(pady=5)
            
            ctk.CTkButton(btn_frame, text="Continue", width=80, command=btn_continue).pack(side="left", padx=5)
            ctk.CTkButton(btn_frame, text="Continue & Don't Show Again", width=180, fg_color="#E06C75", hover_color="#C85A63", command=btn_dont_show).pack(side="left", padx=5)
            ctk.CTkButton(btn_frame, text="Cancel", width=80, fg_color="gray", hover_color="#555555", command=btn_cancel).pack(side="left", padx=5)

            # Handle explicit window closing
            dialog.protocol("WM_DELETE_WINDOW", btn_cancel)

        self.mode_lbl.configure(text=modes[idx], text_color=colors[idx])

    def _trigger_action(self, action: str):
        if self.input_path_var.get() == "No image selected" or not os.path.exists(self.input_path_var.get()):
            self.log("Error: Please select a valid input image.", level="error")
            return
        self._execute_action_threaded(action)

    def _copy_log(self):
        self.clipboard_clear()
        self.clipboard_append(self.log_box.get("1.0", "end-1c"))
        
    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def _cancel_action(self):
        self.cancel_flag = True
        self.log("Cancelling task... Please wait for the current step to abort.", level="warning")
        if hasattr(self, 'cancel_btn_ref') and self.cancel_btn_ref.winfo_exists():
            self.cancel_btn_ref.configure(state="disabled")

    def _inject_progress_bar(self):
        self.current_progress_frame = ctk.CTkFrame(self.log_box._textbox, fg_color="#1E1E1E", corner_radius=0)
        
        self.prog_lbl = ctk.CTkLabel(self.current_progress_frame, text="[" + " "*40 + "] 0%", font=ctk.CTkFont(family="Consolas", size=13, weight="bold"), text_color="#FFFFFF")
        self.prog_lbl.pack(side="left", padx=(5, 10), pady=2)
        
        self.cancel_btn_ref = ctk.CTkButton(self.current_progress_frame, text="Abort [X]", width=70, height=22, fg_color="#E06C75", hover_color="#C85A63", command=self._cancel_action, font=ctk.CTkFont(family="Consolas", size=11, weight="bold"))
        self.cancel_btn_ref.pack(side="left", padx=(0, 5), pady=2)

        self.log_box.configure(state="normal")
        self.log_box._textbox.window_create("end", window=self.current_progress_frame, padx=2, pady=2)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _update_progress(self, percent: int):
        if hasattr(self, 'prog_lbl') and self.prog_lbl.winfo_exists():
            bars = int((percent / 100.0) * 40)
            bar_str = "█" * bars + "░" * (40 - bars)
            self.prog_lbl.configure(text=f"[{bar_str}] {percent}%")

    def _remove_progress_bar(self):
        if hasattr(self, 'current_progress_frame') and self.current_progress_frame.winfo_exists():
            self.current_progress_frame.destroy()

    def _execute_action_threaded(self, action: str):
        import threading
        t = threading.Thread(target=self._execute_action, args=(action,))
        t.daemon = True
        t.start()

    def _execute_action(self, action: str):
        self.cancel_flag = False
        import time, threading

        self.log(f"--- Starting {action.upper()} ---", level="highlight")
        self.after(0, self._inject_progress_bar)
        
        processing_done = False
        
        def animate_progress():
            # Guarantee a minimum of 2 seconds of smooth animation
            for i in range(20):
                if self.cancel_flag:
                    break
                self.after(0, self._update_progress, int((i / 19.0) * 100))
                time.sleep(0.1)
            
            # If the heavy processing is STILL running, hang the progress bar at 99%
            while not processing_done and not self.cancel_flag:
                time.sleep(0.1)

        anim_thread = threading.Thread(target=animate_progress, daemon=True)
        anim_thread.start()

        try:
            in_path = self.input_path_var.get()
            out_path = self.output_path_var.get()

            methods = []
            if self.cb_lsb.get() == 1: methods.append("LSB")
            if self.cb_fft.get() == 1: methods.append("FFT")
            if self.cb_dct.get() == 1: methods.append("DCT")
            if self.cb_dwt.get() == 1: methods.append("DWT")

            if not methods:
                self.log("Error: Please select at least one method.", level="error")
                return

            color_preserve = (self.cb_color.get() == 1)
            rand_name = (self.cb_rand_name.get() == 1)
            rand_size = (self.cb_rand_size.get() == 1)
            force_jpeg = (self.cb_force_jpeg.get() == 1)
            
            modes = ["Conservative", "Balanced", "Aggressive"]
            aggressiveness = modes[int(round(self.mode_slider.get()))]

            processor = WatermarkProcessor()
            
            # Using our updated processor API
            msg, success = processor.process_image(
                image_path=in_path,
                methods=methods,
                action=action,
                color_preserve=color_preserve,
                aggressiveness=aggressiveness,
                output_path=out_path,
                cancel_check=lambda: self.cancel_flag,
                rand_name=rand_name,
                rand_size=rand_size,
                force_jpeg=force_jpeg
            )
            
            processing_done = True
            anim_thread.join() # Wait for the 2-second visual effect to finish if it was faster than that
            
            if self.cancel_flag:
                self.log("Task cancelled by user.", level="error")
                return

            if success and action == "detect":
                # msg is a dict of results
                self._print_detection_table(msg)
            elif success and action == "clean":
                self.log(msg, level="success")
                actual_path = out_path
                if "saved to:\n" in msg:
                    actual_path = msg.split("saved to:\n")[1].strip()
                self.after(0, self._inject_action_buttons, actual_path)
            else:
                if msg is None:
                    self.log("Error: Please select at least one method.", level="error")
                else:
                    self.log(msg, level="error" if "Error" in msg else "warning")

        except Exception as e:
            self.log(f"Error during {action}: {str(e)}", level="error")
            import traceback
            traceback.print_exc()
        finally:
            self.after(0, self._remove_progress_bar)
            self.log(f"--- {action.upper()} Finished ---\n", level="highlight")

    def _print_detection_table(self, results):
        self.log_box.configure(state="normal")
        
        methods = list(results.keys())
        
        # Row 1: Header
        self.log_box.insert("end", f"{'Method:':<12}| ")
        for m in methods:
            self.log_box.insert("end", f"{m:<10}| ")
        self.log_box.insert("end", "\n")

        # Helper to determine level
        def get_lvl(score, detected):
            if not detected: return "success", "Clean"
            # simple heuristic for color intensity
            if score > 50 or score > 0.245: return "error", "Found"
            return "warning", "Suspicious"

        # Row 2: Scores
        self.log_box.insert("end", f"{'Score:':<12}| ")
        for m in methods:
            score = results[m]["score"]
            lvl, _ = get_lvl(score, results[m]["detected"])
            self.log_box.insert("end", f"{score:<10.2f}", lvl)
            self.log_box.insert("end", "| ")
        self.log_box.insert("end", "\n")

        # Row 3: Result Label
        self.log_box.insert("end", f"{'Result:':<12}| ")
        found_methods = []
        for m in methods:
            score = results[m]["score"]
            lvl, label = get_lvl(score, results[m]["detected"])
            if label != "Clean":
                found_methods.append(m)
            self.log_box.insert("end", f"{label:<10}", lvl)
            self.log_box.insert("end", "| ")
        self.log_box.insert("end", "\n")

        # Conclusion Logic
        total_weight = 0
        earned_weight = 0
        weights = {"LSB": 25, "FFT": 40, "DCT": 15, "DWT": 20}
        
        for m in methods:
            w = weights.get(m, 25)
            total_weight += w
            if m in found_methods:
                earned_weight += w
                
        if total_weight > 0:
            prob = int((earned_weight / total_weight) * 95)
        else:
            prob = 0
            
        if not found_methods:
            import random
            prob = random.randint(1, 15) # Baseline noise
            
        prob = min(prob, 99)
        
        if prob >= 70:
            kw = "The image is probably watermarked"
            color = "error"
        elif prob >= 60:
            kw = "The image is likely watermarked"
            color = "warning"
        elif prob >= 40:
            kw = "The image is possibly watermarked"
            color = "warning"
        elif prob >= 30:
            kw = "The image is conceivably watermarked"
            color = "info"
        else:
            kw = "The image is unlikely to be watermarked"
            color = "success"

        self.log_box.insert("end", "Conclusion: ")
        self.log_box.insert("end", f"{kw} ({prob}% probability).\n", color)
        
        if found_methods:
            self.log_box.insert("end", " " * 12 + f"Watermark components likely present in: {', '.join(found_methods)}.\n", color)
        else:
            self.log_box.insert("end", " " * 12 + "No significant watermark signatures detected.\n", color)

        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _inject_action_buttons(self, file_path: str):
        btn_frame = ctk.CTkFrame(self.log_box._textbox, fg_color="#1E1E1E", corner_radius=0)
        
        def open_file():
            import os
            try: os.startfile(file_path)
            except Exception as e: self.log(f"Cannot open: {e}", "error")
            
        btn_open = ctk.CTkButton(
            btn_frame, 
            text="Open Result", 
            width=120, height=32, 
            fg_color="#2FA572", hover_color="#1F7A50", 
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"), 
            command=open_file
        )
        btn_open.pack(side="left", padx=5, pady=(5, 10))
        
        self.log_box.configure(state="normal")
        self.log_box._textbox.window_create("end", window=btn_frame, padx=5, pady=2)
        self.log_box.insert("end", "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    app = WatermarkApp()
    app.mainloop()
