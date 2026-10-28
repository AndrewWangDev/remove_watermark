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

def get_resource_path(relative_path: str) -> str:
    """Get absolute path to resource, working seamlessly for source dev and PyInstaller onefile _MEIPASS."""
    if hasattr(sys, '_MEIPASS'):
        candidate = os.path.join(sys._MEIPASS, relative_path)
        if os.path.exists(candidate):
            return candidate
    candidate = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", relative_path))
    if os.path.exists(candidate):
        return candidate
    candidate = os.path.abspath(relative_path)
    if os.path.exists(candidate):
        return candidate
    return relative_path

class WatermarkApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Watermark Detector & Cleaner")
        self.geometry("1100x720")
        self.minsize(900, 620)
        
        try:
            import ctypes
            myappid = 'andrewwangdev.removewatermark.pro.1.0'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass
        
        # Cross-platform window icon loading with MEIPASS resolution
        self._init_window_icons()

        # Configure grid layout: row 0=header, 1=config, 2=actions, 3=status/progress, 4=log
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        # Global Config & Task State
        self.hide_slow_warning = False
        self.cancel_flag = False
        self.is_processing = False
        self.last_cleaned_path = None

        self._build_ui()
        self._redirect_stdout()

    def _safe_set_icon(self, path: str):
        try:
            if os.path.exists(path) and self.winfo_exists():
                self.iconbitmap(path)
        except Exception:
            pass

    def _init_window_icons(self):
        ico_path = get_resource_path("logo.ico")
        png_path = get_resource_path("logo.png")

        if sys.platform == "win32" and os.path.exists(ico_path):
            self.after(200, lambda: self._safe_set_icon(ico_path))
        elif os.path.exists(png_path):
            try:
                from PIL import Image, ImageTk
                img = Image.open(png_path)
                self._icon_photo = ImageTk.PhotoImage(img)
                self.wm_iconphoto(True, self._icon_photo)
            except Exception:
                pass

        if os.path.exists(png_path):
            try:
                from PIL import Image
                self._ctk_logo = ctk.CTkImage(light_image=Image.open(png_path), dark_image=Image.open(png_path), size=(64, 64))
            except Exception:
                pass

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
        self.theme_switch.select()
        self.theme_switch.grid(row=0, column=2, sticky="e")

        # 2. Main Config Area
        config_frame = ctk.CTkFrame(self)
        config_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        config_frame.grid_columnconfigure(1, weight=1)

        # File selection
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

        # Options frame
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
        
        self.cb_color = ctk.CTkSwitch(privacy_frame, text="Preserve Colors", command=self._on_color_switch)
        self.cb_color.select()
        self.cb_color.pack(side="left", padx=(0, 30))
        
        self.cb_rand_name = ctk.CTkSwitch(privacy_frame, text="Rand Name")
        self.cb_rand_name.pack(side="left", padx=(0, 30))

        self.cb_rand_size = ctk.CTkSwitch(privacy_frame, text="Rand Size")
        self.cb_rand_size.pack(side="left", padx=(0, 30))
        
        self.cb_force_jpeg = ctk.CTkSwitch(privacy_frame, text="Force JPEG")
        self.cb_force_jpeg.pack(side="left", padx=(0, 30))

        # 3. Action Buttons
        actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        actions_frame.grid(row=2, column=0, padx=20, pady=(10, 5), sticky="ew")
        actions_frame.grid_columnconfigure((0, 1), weight=1)

        self.btn_detect = ctk.CTkButton(
            actions_frame, 
            text="Detect Watermarks", 
            height=40, 
            command=lambda: self._trigger_action("detect")
        )
        self.btn_detect.grid(row=0, column=0, padx=5, sticky="ew")

        self.btn_clean = ctk.CTkButton(
            actions_frame, 
            text="Clean & Save", 
            height=40, 
            fg_color="#2FA572", 
            hover_color="#1F7A50", 
            command=lambda: self._trigger_action("clean")
        )
        self.btn_clean.grid(row=0, column=1, padx=5, sticky="ew")

        # 4. Dedicated Status & Progress Panel (Row 3, no private _textbox hacks!)
        self.status_panel = ctk.CTkFrame(self, height=32, fg_color="transparent")
        self.status_panel.grid(row=3, column=0, padx=20, pady=(2, 6), sticky="ew")

        self.prog_lbl = ctk.CTkLabel(
            self.status_panel, 
            text="Ready.", 
            font=ctk.CTkFont(family="Consolas", size=13), 
            text_color="#AAAAAA", 
            anchor="w"
        )
        self.prog_lbl.pack(side="left", padx=5)

        self.btn_abort = ctk.CTkButton(
            self.status_panel,
            text="Abort [X]",
            width=80, height=28,
            fg_color="#E06C75", hover_color="#C85A63",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            command=self._cancel_action
        )
        self.btn_abort.pack(side="right", padx=5)
        self.btn_abort.pack_forget()

        self.btn_open_result = ctk.CTkButton(
            self.status_panel,
            text="Open Result",
            width=110, height=28,
            fg_color="#2FA572", hover_color="#1F7A50",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            command=self._open_last_result
        )
        self.btn_open_result.pack(side="right", padx=5)
        self.btn_open_result.pack_forget()

        # 5. Log Output Area (Row 4, Pure Text, Clean Copying)
        log_frame = ctk.CTkFrame(self, fg_color="#1E1E1E")
        log_frame.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="nsew")
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        
        self.log_box = ctk.CTkTextbox(
            log_frame, 
            state="disabled", 
            wrap="word", 
            font=ctk.CTkFont(family="Consolas", size=13),
            fg_color="#1E1E1E",
            text_color="#CCCCCC"
        )
        self.log_box.grid(row=0, column=0, padx=5, pady=(5, 0), sticky="nsew")
        
        overlay = ctk.CTkFrame(log_frame, fg_color="transparent")
        overlay.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)
        
        btn_copy = ctk.CTkButton(overlay, text="Copy", width=40, height=24, font=ctk.CTkFont(size=11), fg_color="#333333", hover_color="#555555", command=self._copy_log)
        btn_copy.pack(side="left", padx=2)
        
        btn_clear = ctk.CTkButton(overlay, text="Clear", width=40, height=24, font=ctk.CTkFont(size=11), fg_color="#333333", hover_color="#555555", command=self._clear_log)
        btn_clear.pack(side="left")

        # Color tags
        self.log_box.tag_config("timestamp", foreground="#888888")
        self.log_box.tag_config("info", foreground="#56B6C2")
        self.log_box.tag_config("success", foreground="#98C379")
        self.log_box.tag_config("error", foreground="#E06C75")
        self.log_box.tag_config("warning", foreground="#E5C07B")
        self.log_box.tag_config("highlight", foreground="#C678DD")

        self.log("System initialized. Ready.", level="info")

    def log(self, msg: str, level: str = "normal"):
        """Thread-safe logging wrapper that dispatches safely to main Tkinter thread."""
        self.after(0, self._append_log, msg, level)

    def _append_log(self, msg: str, level: str = "normal"):
        self.log_box.configure(state="normal")
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        if level == "normal":
            if "Error" in msg or "Failed" in msg:
                level = "error"
            elif "Successfully" in msg or "cleaned and saved" in msg:
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
        pass

    def _on_color_switch(self):
        if self.cb_color.get() == 0:
            self.log("Note: 'Preserve Colors' is OFF. Processed output will be converted to Grayscale.", level="warning")

    def _show_about_dialog(self):
        about = ctk.CTkToplevel(self)
        about.attributes("-alpha", 0.0)
        about.overrideredirect(True)
        about.geometry("600x380")
        about.transient(self)
        
        about.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (600 // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (380 // 2)
        about.geometry(f"600x380+{int(x)}+{int(y)}")
        
        main_frame = ctk.CTkFrame(about, border_width=2, border_color="#58a6ff", corner_radius=10)
        main_frame.pack(fill="both", expand=True)
        
        bind_id = None
        def close_about(event=None):
            nonlocal bind_id
            if bind_id:
                try:
                    self.unbind("<Button-1>", bind_id)
                except Exception:
                    pass
                bind_id = None
            if about.winfo_exists():
                about.destroy()

        def on_main_click(event):
            close_about()

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
        
        ctk.CTkButton(main_frame, text="Close", width=100, command=close_about).pack(pady=(15, 10))
        about.after(50, lambda: about.attributes("-alpha", 1.0))

    def _toggle_theme(self):
        if self.theme_switch.get() == 1:
            ctk.set_appearance_mode("Dark")
        else:
            ctk.set_appearance_mode("Light")

    def _pick_input(self):
        path = filedialog.askopenfilename(title="Select Image", filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp;*.webp")])
        if path:
            self.input_path_var.set(path)
            self.log(f"Selected input: {path}")

    def _pick_output(self):
        path = filedialog.askdirectory(title="Select Output Directory")
        if path:
            self.output_path_var.set(path)
            self.log(f"Selected output dir: {path}")

    def _on_mode_change(self, value):
        idx = int(round(value))
        modes = ["Conservative", "Balanced", "Aggressive"]
        colors = ["#98C379", "#C678DD", "#E06C75"]

        if idx == 2 and not self.hide_slow_warning:
            dialog = ctk.CTkToplevel(self)
            dialog.title("Aggressive Mode Warning")
            dialog.geometry("400x180")
            dialog.transient(self)
            dialog.grab_set()

            dialog.update_idletasks()
            x = self.winfo_x() + (self.winfo_width() // 2) - 200
            y = self.winfo_y() + (self.winfo_height() // 2) - 90
            dialog.geometry(f"+{x}+{y}")

            msg_lbl = ctk.CTkLabel(
                dialog, 
                text="Aggressive mode performs deep frequency domain filtering.\nThis may slightly soften high-contrast text edges.", 
                wraplength=350,
                justify="center"
            )
            msg_lbl.pack(pady=(20, 15))

            btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
            btn_frame.pack(pady=10)

            def btn_continue():
                dialog.grab_release()
                dialog.destroy()

            def btn_dont_show():
                self.hide_slow_warning = True
                dialog.grab_release()
                dialog.destroy()

            def btn_cancel():
                self.mode_slider.set(1)
                dialog.grab_release()
                dialog.destroy()

            ctk.CTkButton(btn_frame, text="Continue", width=80, command=btn_continue).pack(side="left", padx=5)
            ctk.CTkButton(btn_frame, text="Don't Show Again", width=140, fg_color="#E06C75", hover_color="#C85A63", command=btn_dont_show).pack(side="left", padx=5)
            ctk.CTkButton(btn_frame, text="Cancel", width=80, fg_color="gray", hover_color="#555555", command=btn_cancel).pack(side="left", padx=5)
            dialog.protocol("WM_DELETE_WINDOW", btn_cancel)

            # Block modal execution until user explicitly decides (prevents premature label jump)
            self.wait_window(dialog)
            idx = int(round(self.mode_slider.get()))

        self.mode_lbl.configure(text=modes[idx], text_color=colors[idx])

    def _trigger_action(self, action: str):
        if self.is_processing:
            return

        in_path = self.input_path_var.get()
        if in_path == "No image selected" or not os.path.exists(in_path):
            self.log("Error: Please select a valid input image.", level="error")
            return

        methods = []
        if self.cb_lsb.get() == 1: methods.append("LSB")
        if self.cb_fft.get() == 1: methods.append("FFT")
        if self.cb_dct.get() == 1: methods.append("DCT")
        if self.cb_dwt.get() == 1: methods.append("DWT")

        if not methods:
            self.log("Error: Please select at least one method.", level="error")
            return

        modes = ["Conservative", "Balanced", "Aggressive"]
        aggressiveness = modes[int(round(self.mode_slider.get()))]

        params = {
            "image_path": in_path,
            "output_path": self.output_path_var.get(),
            "methods": methods,
            "color_preserve": (self.cb_color.get() == 1),
            "rand_name": (self.cb_rand_name.get() == 1),
            "rand_size": (self.cb_rand_size.get() == 1),
            "force_jpeg": (self.cb_force_jpeg.get() == 1),
            "aggressiveness": aggressiveness,
            "action": action
        }

        self.is_processing = True
        self.btn_detect.configure(state="disabled")
        self.btn_clean.configure(state="disabled")
        self.btn_open_result.pack_forget()
        self.btn_abort.configure(state="normal")
        self.btn_abort.pack(side="right", padx=5)

        self._execute_action_threaded(params)

    def _copy_log(self):
        """Clean log export: gets pure text without control frame artifacts."""
        self.clipboard_clear()
        self.clipboard_append(self.log_box.get("1.0", "end-1c"))
        
    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def _cancel_action(self):
        self.cancel_flag = True
        self.log("Cancelling task... Aborting current pipeline.", level="warning")
        self.btn_abort.configure(state="disabled")

    def _update_progress(self, percent: int, msg: str = ""):
        percent = min(100, max(0, percent))
        bars = int((percent / 100.0) * 30)
        bar_str = "█" * bars + "░" * (30 - bars)
        desc_str = f" {msg}" if msg else ""
        self.prog_lbl.configure(text=f"[{bar_str}] {percent}%{desc_str}")

    def _open_last_result(self):
        if not self.last_cleaned_path or not os.path.exists(self.last_cleaned_path):
            self.log("Error: Output file not found.", "error")
            return
        import subprocess
        try:
            if sys.platform == "win32":
                os.startfile(self.last_cleaned_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", self.last_cleaned_path], check=False)
            else:
                subprocess.run(["xdg-open", self.last_cleaned_path], check=False)
        except Exception as e:
            self.log(f"Cannot open file: {e}", "error")

    def _execute_action_threaded(self, params: dict):
        t = threading.Thread(target=self._execute_action, args=(params,))
        t.daemon = True
        t.start()

    def _execute_action(self, params: dict):
        self.cancel_flag = False
        action = params["action"]

        self.log(f"--- Starting {action.upper()} ---", level="highlight")
        self.after(0, self._update_progress, 0, "Initializing...")

        try:
            processor = WatermarkProcessor()

            def progress_cb(pct, desc):
                self.after(0, self._update_progress, pct, desc)

            msg, success = processor.process_image(
                image_path=params["image_path"],
                methods=params["methods"],
                action=action,
                color_preserve=params["color_preserve"],
                aggressiveness=params["aggressiveness"],
                output_path=params["output_path"],
                cancel_check=lambda: self.cancel_flag,
                rand_name=params["rand_name"],
                rand_size=params["rand_size"],
                force_jpeg=params["force_jpeg"],
                progress_callback=progress_cb
            )

            if self.cancel_flag:
                self.log("Task cancelled by user.", level="error")
                return

            if success and action == "detect":
                self.after(0, self._print_detection_table, msg)
            elif success and action == "clean":
                self.log(msg, level="success")
                actual_path = params["output_path"]
                if "saved to:\n" in msg:
                    actual_path = msg.split("saved to:\n")[1].strip()
                self.last_cleaned_path = actual_path
                self.after(0, self._show_open_button)
            else:
                if msg is None:
                    self.log("Error: Please select at least one method.", level="error")
                else:
                    self.log(msg, level="error" if "Error" in msg else "warning")

        except Exception as e:
            # Crash-proof exception handling: format traceback as string to prevent sys.stderr is None crash
            import traceback
            err_trace = traceback.format_exc()
            self.log(f"Error during {action}: {str(e)}", level="error")
            self.log(err_trace, level="error")
        finally:
            self.after(0, self._finish_action, action)

    def _show_open_button(self):
        self.btn_open_result.pack(side="right", padx=5)

    def _finish_action(self, action: str):
        self.btn_abort.pack_forget()
        self.is_processing = False
        if hasattr(self, 'btn_detect') and self.btn_detect.winfo_exists():
            self.btn_detect.configure(state="normal")
        if hasattr(self, 'btn_clean') and self.btn_clean.winfo_exists():
            self.btn_clean.configure(state="normal")
        self.prog_lbl.configure(text=f"{action.capitalize()} finished.")
        self.log(f"--- {action.upper()} Finished ---\n", level="highlight")

    def _print_detection_table(self, results):
        self.log_box.configure(state="normal")
        
        methods = list(results.keys())
        
        # Row 1: Header
        self.log_box.insert("end", f"{'Method:':<12}| ")
        for m in methods:
            self.log_box.insert("end", f"{m:<10}| ")
        self.log_box.insert("end", "\n")

        # Multi-tier grading: Clean (green) / Suspicious (yellow) / Found (red)
        def get_lvl(method, score, detected):
            if method == "LSB":
                if score >= 0.490: return "error", "Found"
                if score >= 0.460 or detected: return "warning", "Suspicious"
                return "success", "Clean"
            elif method == "FFT":
                if score >= 45.0: return "error", "Found"
                if score >= 18.0 or detected: return "warning", "Suspicious"
                return "success", "Clean"
            elif method == "DCT":
                if score >= 1200.0: return "error", "Found"
                if score >= 600.0 or detected: return "warning", "Suspicious"
                return "success", "Clean"
            elif method == "DWT":
                if score >= 250.0: return "error", "Found"
                if score >= 80.0 or detected: return "warning", "Suspicious"
                return "success", "Clean"
            return ("error", "Found") if detected else ("success", "Clean")

        # Row 2: Scores
        self.log_box.insert("end", f"{'Score:':<12}| ")
        for m in methods:
            score = results[m]["score"]
            lvl, _ = get_lvl(m, score, results[m]["detected"])
            self.log_box.insert("end", f"{score:<10.2f}", lvl)
            self.log_box.insert("end", "| ")
        self.log_box.insert("end", "\n")

        # Row 3: Result Label
        self.log_box.insert("end", f"{'Result:':<12}| ")
        found_methods = []
        suspicious_methods = []
        for m in methods:
            score = results[m]["score"]
            lvl, label = get_lvl(m, score, results[m]["detected"])
            if label == "Found":
                found_methods.append(m)
            elif label == "Suspicious":
                suspicious_methods.append(m)
            self.log_box.insert("end", f"{label:<10}", lvl)
            self.log_box.insert("end", "| ")
        self.log_box.insert("end", "\n")

        # Deterministic weighted probability calculation
        total_weight = 0
        earned_weight = 0
        weights = {"LSB": 25, "FFT": 40, "DCT": 15, "DWT": 20}
        
        for m in methods:
            w = weights.get(m, 25)
            total_weight += w
            if m in found_methods:
                earned_weight += w
            elif m in suspicious_methods:
                earned_weight += w * 0.5
                
        if total_weight > 0 and (found_methods or suspicious_methods):
            prob = int((earned_weight / total_weight) * 95)
            prob = min(prob, 99)
        else:
            prob = 0
        
        if prob >= 70:
            kw = "The image is probably watermarked"
            color = "error"
        elif prob >= 50:
            kw = "The image is likely watermarked"
            color = "warning"
        elif prob >= 25:
            kw = "The image is possibly watermarked"
            color = "warning"
        elif prob > 0:
            kw = "The image is conceivably watermarked"
            color = "info"
        else:
            kw = "The image is clean / unlikely to be watermarked"
            color = "success"

        self.log_box.insert("end", "Conclusion: ")
        self.log_box.insert("end", f"{kw} ({prob}% probability).\n", color)
        
        if found_methods or suspicious_methods:
            details = []
            if found_methods:
                details.append(f"Found in {', '.join(found_methods)}")
            if suspicious_methods:
                details.append(f"Suspicious in {', '.join(suspicious_methods)}")
            self.log_box.insert("end", " " * 12 + f"Watermark signatures: {'; '.join(details)}.\n", color)
        else:
            self.log_box.insert("end", " " * 12 + "No significant watermark signatures detected.\n", color)

        self.log_box.see("end")
        self.log_box.configure(state="disabled")

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    app = WatermarkApp()
    app.mainloop()
