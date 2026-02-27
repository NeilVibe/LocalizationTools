; ExtractAnything Installer Script
; Inno Setup 6.0+
;
; Features:
; - Portable install (Desktop by default, NOT Program Files)
; - No Python required (bundled via PyInstaller)
; - No admin rights required
;
; ExtractAnything creates an Output/ folder next to the exe at runtime.

#define MyAppName "ExtractAnything"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Localization Team"
#define MyAppExeName "ExtractAnything.exe"

[Setup]
; Application info
AppId={{A3B7C9D1-4E5F-6A2B-8C0D-1E3F5A7B9C2D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}

; PORTABLE INSTALL - Desktop by default (no admin needed)
DefaultDirName={userdesktop}\ExtractAnything
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Output
OutputDir=..\installer_output
OutputBaseFilename=ExtractAnything_v{#MyAppVersion}_Setup
UninstallDisplayIcon={app}\{#MyAppExeName}

; Compression
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; System requirements
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
MinVersion=6.1sp1

; NO ADMIN REQUIRED
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline

; Pages
DisableWelcomePage=no
DisableDirPage=no
DisableReadyPage=no
DisableFinishedPage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Main application
Source: "..\dist\ExtractAnything\ExtractAnything.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ExtractAnything\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

; Output folder (empty but necessary)
Source: "..\dist\ExtractAnything\Output\*"; DestDir: "{app}\Output"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

[Dirs]
; Create empty Output folder
Name: "{app}\Output"

[Icons]
; Start Menu
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autoprograms}\{#MyAppName}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

; Desktop
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Launch after install
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up generated files
Type: filesandordirs; Name: "{app}\Output"
Type: filesandordirs; Name: "{app}\*.log"
Type: filesandordirs; Name: "{app}\*.json"
