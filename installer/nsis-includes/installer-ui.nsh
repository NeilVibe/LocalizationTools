; LocaNext Installer UI Customization
; Shows installation progress details to user

; Must use customHeader macro for electron-builder
; See: https://github.com/electron-userland/electron-builder/issues/4719
!macro customHeader
  ShowInstDetails show
  ShowUnInstDetails show
!macroend

; Optional: Auto-scroll the details panel
!define MUI_INSTFILESPAGE_PROGRESSBAR smooth

; Set detail text at start
!macro customInstall
  DetailPrint "Installing LocaNext..."
  DetailPrint "This may take a few minutes..."
  DetailPrint ""
!macroend
