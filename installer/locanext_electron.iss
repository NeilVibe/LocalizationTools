; LocaNext FULL Installer Script
; Inno Setup 6.0+
; Based on VRS-Manager proven installer pattern
;
; This installer creates the FULL version of LocaNext:
; - XLSTransfer (AI-powered translation with Korean BERT)
; - QuickSearch (Multi-game dictionary)
; - Admin Dashboard
; - Korean BERT model (446MB - bundled via Git LFS)
; - Complete Electron desktop application
;
; Output: LocaNext_v2512011310_Setup.exe (~2GB)

#define MyAppName "LocaNext"
#define MyAppVersion "2512131300"
#define MyAppPublisher "Neil Schmitt"
#define MyAppURL "https://github.com/NeilVibe/LocalizationTools"
#define MyAppExeName "LocaNext.exe"

[Setup]
; Application info
AppId={{A1B2C3D4-5E6F-7A8B-9C0D-1E2F3A4B5C6D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases

; Install paths
; VRS-Manager lesson: Use Desktop for no-admin-required install
DefaultDirName={userdesktop}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes

; Output
OutputDir=..\installer_output
OutputBaseFilename=LocaNext_v{#MyAppVersion}_Setup
SetupIconFile=..\locaNext\public\favicon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; Compression
; VRS-Manager lesson: ultra64 for best compression on large files
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
LZMANumBlockThreads=4

; System requirements
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
MinVersion=6.1sp1

; Privileges
; VRS-Manager lesson: lowest = no admin required!
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

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main Electron application
; electron-builder output: dist-electron/win-unpacked/*
Source: "..\locaNext\dist-electron\win-unpacked\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\locaNext\dist-electron\win-unpacked\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; BERT Model (446MB - from Git LFS)
; VRS-Manager lesson: Verify this exists in build workflow!
Source: "..\models\kr-sbert\*"; DestDir: "{app}\models\kr-sbert"; Flags: ignoreversion recursesubdirs createallsubdirs

; Documentation
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\SECURITY.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs

; User guides (if they exist)
Source: "..\guides\*"; DestDir: "{app}\guides"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: DirExists('..\guides')

[Icons]
; Start Menu
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autoprograms}\{#MyAppName}\Documentation"; Filename: "{app}\README.md"
Name: "{autoprograms}\{#MyAppName}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

; Desktop icon (optional, unchecked by default)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Launch after install
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up generated files on uninstall
; VRS-Manager lesson: Remove user-generated files
Type: files; Name: "{app}\*.xlsx"
Type: files; Name: "{app}\*.xls"
Type: files; Name: "{app}\*.txt"
Type: files; Name: "{app}\*.log"
Type: filesandordirs; Name: "{app}\logs\*"
Type: filesandordirs; Name: "{app}\temp\*"

[Code]
; Check if guides directory exists (optional dependency)
function DirExists(const Name: String): Boolean;
begin
  Result := DirExists(ExpandConstant(Name));
end;
