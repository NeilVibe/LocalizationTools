; QuickCheck Inno Setup Script
; Clean installer - installs to Desktop by default

#define MyAppName "QuickCheck"
#ifndef AppVersion
  #define MyAppVersion "1.0.0"
#else
  #define MyAppVersion AppVersion
#endif
#define MyAppPublisher "Neil"
#define MyAppExeName "QuickCheck.exe"
#define MyAppDescription "Multi-language LINE CHECK, TERM CHECK, LANG CHECK & Glossary Extraction Tool"

[Setup]
AppId={{F2C4A6B8-D0E2-4F68-9A1C-3B5D7E9F1A2C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={userdesktop}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\installer_output
OutputBaseFilename={#MyAppName}_v{#MyAppVersion}_Setup
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
DisableWelcomePage=no
DisableDirPage=no
DisableReadyPage=no
DisableFinishedPage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\QuickCheck\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
