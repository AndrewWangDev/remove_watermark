import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import os
import sys

# Ensure logic module can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from logic.processor import WatermarkProcessor

class WatermarkApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Watermark Detector & Cleaner")
        self.geometry("600x400")
        
        # Processor instance
        self.processor = WatermarkProcessor()
        self.selected_image_path = None

        # UI Layout
        self.create_widgets()
        
    def create_widgets(self):
        # Top Frame for Buttons
        top_frame = tk.Frame(self, pady=10)
        top_frame.pack(side=tk.TOP, fill=tk.X)
        
        self.btn_upload = tk.Button(top_frame, text="Upload Image", command=self.upload_image, padx=10, pady=5)
        self.btn_upload.pack(side=tk.LEFT, padx=20)
        
        self.btn_clean = tk.Button(top_frame, text="Clean & Save", command=self.clean_image, state=tk.DISABLED, padx=10, pady=5)
        self.btn_clean.pack(side=tk.RIGHT, padx=20)
        
        # Middle Frame for Logs
        middle_frame = tk.Frame(self, pady=5, padx=10)
        middle_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        lbl_log = tk.Label(middle_frame, text="Output Log:", anchor="w")
        lbl_log.pack(fill=tk.X)
        
        self.log_area = scrolledtext.ScrolledText(middle_frame, height=15, state='disabled')
        self.log_area.pack(fill=tk.BOTH, expand=True)
        
        # Bottom Frame for Status
        bottom_frame = tk.Frame(self, pady=5)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        lbl_status = tk.Label(bottom_frame, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor="w")
        lbl_status.pack(fill=tk.X)
        
        self.log("Application started. Waiting for image upload...")

    def log(self, message):
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, f"> {message}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')

    def upload_image(self):
        file_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")]
        )
        
        if file_path:
            self.selected_image_path = file_path
            self.log(f"Selected: {file_path}")
            self.btn_clean.config(state=tk.NORMAL)
            self.run_detection(file_path)

    def run_detection(self, file_path):
        self.status_var.set("Analyzing image...")
        self.update_idletasks()
        
        msg, detected = self.processor.detect_watermark(file_path)
        self.log(msg)
        
        if detected:
            self.log("Alert: Potential Watermark Found! (High frequency variance detected)")
        
        self.status_var.set("Analysis complete.")

    def clean_image(self):
        if not self.selected_image_path:
            messagebox.showwarning("Warning", "No image selected!")
            return
            
        self.status_var.set("Cleaning image...")
        self.update_idletasks()
        
        self.log("Starting cleanup process...")
        result_msg = self.processor.clean_watermark(self.selected_image_path)
        self.log(result_msg)
        
        self.status_var.set("Cleaning complete.")

if __name__ == "__main__":
    app = WatermarkApp()
    app.mainloop()
