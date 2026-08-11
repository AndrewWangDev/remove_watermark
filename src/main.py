import customtkinter as ctk
from ui.main_view import WatermarkApp

def main():
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    app = WatermarkApp()
    app.mainloop()

if __name__ == "__main__":
    main()
