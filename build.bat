@echo off
echo Building Standalone Watermark Cleaner...

:: Create dummy directories to bypass Python 3.14 + Tcl9 PyInstaller bug
if not exist "build_helpers\_tcl_data" mkdir "build_helpers\_tcl_data"
echo. > build_helpers\_tcl_data\dummy.txt
if not exist "build_helpers\_tk_data" mkdir "build_helpers\_tk_data"
echo. > build_helpers\_tk_data\dummy.txt
if not exist "build_helpers\tcl" mkdir "build_helpers\tcl"
echo. > build_helpers\tcl\dummy.txt
if not exist "build_helpers\tk" mkdir "build_helpers\tk"
echo. > build_helpers\tk\dummy.txt

:: Compile into a single standalone EXE using optimized spec
pyinstaller --noconfirm main.spec

echo Build complete! Your standalone EXE is in the dist folder.
