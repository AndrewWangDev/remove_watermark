# Watermark Detector

A lightweight Windows utility to detect and neutralize hidden digital watermarks using frequency domain analysis.

Repository: [https://github.com/AndrewWangDev/remove_watermark](https://github.com/AndrewWangDev/remove_watermark)

## Principles

 This application leverages **Frequency Domain Analysis** to handle digital watermarks:

1.  **Detection**: The image is converted to the frequency domain using **Fast Fourier Transform (FFT)**. Hidden watermarks often manifest as distinct high-frequency spikes or geometric patterns in the magnitude spectrum, which this tool analyzes to detect potential artifacts.
2.  **Neutralization**: To remove the watermark, the application employs frequency domain filtering (e.g., masking specific frequencies or applying a low-pass filter). The cleaned frequency spectrum is then transformed back to the spatial domain using **Inverse FFT** to reconstruct the image.

## Usage

### Prerequisites

- Python 3.x
- `pip` package manager

### Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/AndrewWangDev/remove_watermark.git
    cd remove_watermark
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Running the App

1.  Execute the main script:
    ```bash
    python src/main.py
    ```

2.  **Upload Image**: Click the "Upload Image" button to select a `.png` or `.jpg` file.
3.  **Detect & Clean**: The app will automatically analyze the image. Click "Clean & Save" to apply the watermark removal process. The cleaned image will be saved in the same directory as the original with a `cleaned_` prefix.

## Tech Stack

- **Logic**: Python 3.x, OpenCV (`cv2`), Numpy
- **GUI**: Tkinter
- **Packaging**: PyInstaller
