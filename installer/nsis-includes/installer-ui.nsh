; LocaNext Installer UI Customization
; Shows installation progress details to user

; Must use customHeader macro for electron-builder
; See: https://github.com/electron-userland/electron-builder/issues/4719
!macro customHeader
  ShowInstDetails show
  ShowUnInstDetails show
  ; Enable detailed file extraction output
  SetDetailsPrint both
!macroend

; Optional: Auto-scroll the details panel
!define MUI_INSTFILESPAGE_PROGRESSBAR smooth

; Set detail text at start
!macro customInstall
  DetailPrint "================================================"
  DetailPrint "  LocaNext Installation"
  DetailPrint "================================================"
  DetailPrint ""
  DetailPrint "Installing application files..."
  DetailPrint "This may take a few minutes depending on your system."
  DetailPrint ""
  DetailPrint "Components being installed:"
  DetailPrint "  - LocaNext Desktop Application"
  DetailPrint "  - Embedded Python Runtime"
  DetailPrint "  - Backend Server"
  DetailPrint "  - Translation Tools"
  DetailPrint ""
  DetailPrint "Extracting files..."
  DetailPrint ""
!macroend

; After installation completes
!macro customInstallEnd
  DetailPrint ""
  DetailPrint "================================================"
  DetailPrint "  Installation Complete!"
  DetailPrint "================================================"
  DetailPrint ""
  DetailPrint "LocaNext has been installed successfully."
  DetailPrint ""
  DetailPrint "On first launch, the app will:"
  DetailPrint "  1. Install Python dependencies"
  DetailPrint "  2. Download the Embedding Model (~2.3 GB)"
  DetailPrint ""
  DetailPrint "Please ensure you have an internet connection."
  DetailPrint ""
!macroend
