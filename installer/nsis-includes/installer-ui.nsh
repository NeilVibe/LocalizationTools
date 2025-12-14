; LocaNext Installer UI Customization
; Shows installation progress details to user

; Show details panel during install (not collapsed)
ShowInstDetails show

; Show details panel during uninstall
ShowUnInstDetails show

; Optional: Auto-scroll the details panel
!define MUI_INSTFILESPAGE_PROGRESSBAR smooth

; Set detail text at start
!macro customInstall
  DetailPrint "Installing LocaNext..."
  DetailPrint "This may take a few minutes..."
  DetailPrint ""
!macroend
