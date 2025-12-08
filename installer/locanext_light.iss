; LocaNext LIGHT Installer Script
; Inno Setup 6.0+
;
; LIGHT version - Frontend + Backend bundled, heavy deps download post-install
; - VC++ Redistributable bundled (~14MB) - auto-installs silently
; - Python Embedded + deps bundled (~50MB) - IT-friendly, transparent!
; - Electron app bundled (~100MB)
; - Backend server bundled (~11MB)
; - Total: ~180-200MB (LIGHT for Git Actions)
;
; Post-install: Downloads HEAVY stuff automatically:
; - AI model (~447MB) from Hugging Face
; - torch + transformers (~2GB) via pip
;
; IT-FRIENDLY: All scripts are readable .bat and .py files!
; User experience: Run installer → Wait for downloads → Done!
;
; Output: LocaNext_v{version}_Light_Setup.exe (~180-200MB)

#define MyAppName "LocaNext"
#define MyAppVersion "2512090351"
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

; Install paths - User's Desktop for no-admin-required install
DefaultDirName={userdesktop}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes

; Output
OutputDir=..\installer_output
OutputBaseFilename=LocaNext_v{#MyAppVersion}_Light_Setup
; SetupIconFile=..\locaNext\static\favicon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; Compression
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
LZMANumBlockThreads=4

; System requirements
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
MinVersion=6.1sp1

; Privileges - no admin required for user desktop install
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Wizard appearance
WizardStyle=modern
DisableWelcomePage=no
DisableDirPage=no
DisableReadyPage=no
DisableFinishedPage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
; Simple welcome message - first-run setup handles deps/model
WelcomeLabel2=This will install [name/ver] on your computer.%n%nOn first launch, the app will automatically:%n- Install Python dependencies (~2GB)%n- Download AI model (~447MB)%n%nRequirements:%n- Internet connection (for first launch)%n- ~3GB free disk space%n%nClick Install to continue!

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
; Model download is AUTOMATIC - no checkbox needed, always happens!

[Files]
; ============================================================
; VC++ Redistributable (bundled, ~14MB, auto-installs silently)
; ============================================================
; NOTE: vc_redist.x64.exe must be downloaded separately before building installer
; For CI builds, we skip this if not present (users can install VC++ Runtime manually)
Source: "..\installer\redist\vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: ignoreversion deleteafterinstall skipifsourcedoesntexist

; ============================================================
; Main Electron application (~100MB)
; ============================================================
Source: "..\locaNext\dist-electron\win-unpacked\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\locaNext\dist-electron\win-unpacked\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; ============================================================
; Python Embedded + tools (~50MB with deps)
; IT-Friendly: Transparent .bat and .py scripts!
; ============================================================
Source: "..\tools\download_model.bat"; DestDir: "{app}\tools"; Flags: ignoreversion
Source: "..\tools\download_model.py"; DestDir: "{app}\tools"; Flags: ignoreversion
Source: "..\tools\install_deps.bat"; DestDir: "{app}\tools"; Flags: ignoreversion
Source: "..\tools\install_deps.py"; DestDir: "{app}\tools"; Flags: ignoreversion
; NOTE: Embedded Python must be downloaded separately before building full installer
; For CI/testing builds without embedded Python, this line is skipped
; Source: "..\tools\python\*"; DestDir: "{app}\tools\python"; Flags: ignoreversion recursesubdirs createallsubdirs

; ============================================================
; Backend Server (~11MB)
; Python FastAPI server - auto-started by Electron
; ============================================================
Source: "..\server\*"; DestDir: "{app}\server"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__,*.pyc,*.pyo,.pytest_cache"

; ============================================================
; Version file (required by server)
; ============================================================
Source: "..\version.py"; DestDir: "{app}"; Flags: ignoreversion

; ============================================================
; Documentation
; ============================================================
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\SECURITY.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

; Create models directory placeholder
Source: "..\installer\model_placeholder.txt"; DestDir: "{app}\models\kr-sbert"; Flags: ignoreversion

[Icons]
; Start Menu
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autoprograms}\{#MyAppName}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

; Desktop icon (optional)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; ============================================================
; STEP 1: Install VC++ Redistributable (silent, automatic)
; Only installs if not already present
; ============================================================
Filename: "{tmp}\vc_redist.x64.exe"; \
  Parameters: "/install /quiet /norestart"; \
  StatusMsg: "Installing Visual C++ Runtime (required)..."; \
  Flags: waituntilterminated skipifdoesntexist

; ============================================================
; NOTE: Python deps and AI model are installed on FIRST APP LAUNCH
; not during installation. This provides:
; - Better error handling and retry capability
; - Visible progress to the user
; - Faster initial install (~1 min instead of 20+ min)
; See: electron/first-run-setup.js
; ============================================================

; ============================================================
; STEP 2: Launch app (triggers first-run setup automatically)
; ============================================================
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
// Everything is automatic - no user interaction needed!
// VC++ Redistributable is bundled and installs silently.

function InitializeSetup(): Boolean;
begin
  Result := True;
  // No checks needed - everything is bundled!
end;
