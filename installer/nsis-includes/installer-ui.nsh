; LocaNext Custom NSIS Installer UI
; Referenced by package.json: nsis.include
;
; Overrides electron-builder defaults to show installation progress.

; --- Show details panel (overrides "nevershow" from common.nsh) ---
; customHeader runs after common.nsh, so this wins.
!macro customHeader
  ShowInstDetails show
!macroend

; --- Smooth progress bar ---
!define MUI_INSTFILESPAGE_PROGRESSBAR smooth

; --- Install progress page header ---
!define MUI_INSTFILESPAGE_HEADER_TEXT "Installing LocaNext"
!define MUI_INSTFILESPAGE_HEADER_SUBTEXT "Extracting and copying files. This usually takes about 1 minute."

; --- Header shown when install completes ---
!define MUI_INSTFILESPAGE_FINISHHEADER_TEXT "Installation Complete"
!define MUI_INSTFILESPAGE_FINISHHEADER_SUBTEXT "LocaNext is ready to use."

; --- Post-install: show completion in detail log ---
!macro customInstall
  SetDetailsPrint textonly
  DetailPrint ""
  DetailPrint "LocaNext installed successfully."
  DetailPrint ""
  SetDetailsPrint none
!macroend
