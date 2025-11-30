; LocaNext LIGHT Installer Script
; Inno Setup 6.0+
;
; LIGHT version - Model downloaded post-install (not bundled)
; This avoids Git LFS bandwidth costs!
;
; What's included:
; - XLSTransfer (AI-powered translation)
; - QuickSearch (Multi-game dictionary)
; - Admin Dashboard
; - Download scripts for Korean BERT model
;
; What happens during install:
; 1. Files copied (~100-150MB)
; 2. Post-install: download_model_silent.bat runs
; 3. Model downloaded from Hugging Face (~447MB)
; 4. App ready to use
;
; Output: LocaNext_v{version}_Light_Setup.exe (~100-150MB)

#define MyAppName "LocaNext"
#define MyAppVersion "2511221939"
#define MyAppPublisher "Neil Schmitt"
#define MyAppURL "https://github.com/NeilVibe/LocalizationTools"
#define MyAppExeName "LocaNext.exe"

[Setup]
; Application info
AppId={{A1B2C3D4-5E6F-7A8B-9C0D-1E2F3A4B5C6D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion} (Light)
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases

; Install paths - Desktop for no-admin-required install
DefaultDirName={userdesktop}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes

; Output
OutputDir=..\installer_output
OutputBaseFilename=LocaNext_v{#MyAppVersion}_Light_Setup
SetupIconFile=..\locaNext\public\favicon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; Compression - still use good compression for smaller installer
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
LZMANumBlockThreads=4

; System requirements
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
MinVersion=6.1sp1

; Privileges - no admin required
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Wizard
WizardStyle=modern
DisableWelcomePage=no
DisableDirPage=no
DisableReadyPage=no
DisableFinishedPage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
; Custom messages for LIGHT version
WelcomeLabel2=This will install [name/ver] on your computer.%n%nAfter installation, the AI model (~447MB) will be downloaded automatically from Hugging Face. This requires an internet connection and may take 5-10 minutes.%n%nRequirements:%n- Python 3.10 or later%n- Internet connection%n- ~1GB free disk space

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "downloadmodel"; Description: "Download AI Model after installation (~447MB, requires internet)"; GroupDescription: "AI Features:"; Flags: checked

[Files]
; Main Electron application (NO model bundled!)
Source: "..\locaNext\dist-electron\win-unpacked\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\locaNext\dist-electron\win-unpacked\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Download scripts - CRITICAL for LIGHT version
Source: "..\scripts\download_model_silent.bat"; DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "..\scripts\download_bert_model.py"; DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "..\scripts\download_model.bat"; DestDir: "{app}\scripts"; Flags: ignoreversion

; Documentation
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\SECURITY.md"; DestDir: "{app}"; Flags: ignoreversion; Check: FileExists('..\SECURITY.md')

; Create empty models directory (model will be downloaded here)
; Note: Inno Setup can't create empty dirs directly, so we create a placeholder
Source: "..\installer\model_placeholder.txt"; DestDir: "{app}\models\kr-sbert"; Flags: ignoreversion

[Icons]
; Start Menu
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autoprograms}\{#MyAppName}\Download AI Model"; Filename: "{app}\scripts\download_model.bat"
Name: "{autoprograms}\{#MyAppName}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

; Desktop icon (optional)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Post-install: Download AI model (if user selected the task)
; Uses silent script - no popups, runs in background
Filename: "{app}\scripts\download_model_silent.bat"; \
  Description: "Downloading AI Model (447MB from Hugging Face)..."; \
  StatusMsg: "Downloading Korean BERT model... This may take 5-10 minutes."; \
  Tasks: downloadmodel; \
  Flags: runhidden waituntilterminated

; Launch app after install
Filename: "{app}\{#MyAppExeName}"; \
  Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; \
  Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up generated files on uninstall
Type: files; Name: "{app}\*.xlsx"
Type: files; Name: "{app}\*.xls"
Type: files; Name: "{app}\*.txt"
Type: files; Name: "{app}\*.log"
Type: filesandordirs; Name: "{app}\logs\*"
Type: filesandordirs; Name: "{app}\temp\*"
Type: filesandordirs; Name: "{app}\models\*"

[Code]
function FileExists(const Name: String): Boolean;
begin
  Result := FileExists(ExpandConstant(Name));
end;

// Show warning if Python not detected (optional enhancement)
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;

  // Check for Python (optional - don't block install if not found)
  if not Exec('python', '--version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    if MsgBox('Python was not detected on your system.' + #13#10 + #13#10 +
              'Python 3.10+ is required to download the AI model.' + #13#10 +
              'You can install Python from: https://www.python.org/downloads/' + #13#10 + #13#10 +
              'Continue with installation anyway?', mbConfirmation, MB_YESNO) = IDNO then
    begin
      Result := False;
    end;
  end;
end;
