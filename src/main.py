import sys
import os

# Ensure src directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.gui import WatermarkApp

if __name__ == "__main__":
    app = WatermarkApp()
    app.mainloop()
