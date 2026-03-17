; LanguageDataExporter Inno Setup Script
; Drive/Branch selection is now in the GUI — installer just writes default settings

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

#define AppName "LanguageDataExporter"
#define AppPublisher "Localization Tools"
#define AppExeName "LanguageDataExporter.exe"
#define AppDescription "Language XML to Categorized Excel Converter"

[Setup]
AppId={{8F4E3B2A-1C5D-4E6F-9A8B-7C0D1E2F3A4B}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} v{#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={userdesktop}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
; No admin required - installs to user desktop
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename={#AppName}_v{#AppVersion}_Setup
SetupIconFile=..\images\LDEico.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; 64-bit only
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Components]
Name: "main"; Description: "Main Application"; Types: full compact custom; Flags: fixed
Name: "docs"; Description: "User Guide (PDF & HTML)"; Types: full

[Files]
; Main application and PyInstaller runtime
; PyInstaller bundles everything into exe + _internal folder
Source: "..\dist\LanguageDataExporter\*"; DestDir: "{app}"; Components: main; Flags: ignoreversion recursesubdirs createallsubdirs

; Documentation files
Source: "..\USER_GUIDE.pdf"; DestDir: "{app}"; Components: docs; Flags: ignoreversion
Source: "..\USER_GUIDE.html"; DestDir: "{app}"; Components: docs; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Components: docs; Flags: ignoreversion

[Dirs]
Name: "{app}\GeneratedExcel"; Permissions: users-modify

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\images\LDEico.ico"
Name: "{group}\{#AppName} (GUI)"; Filename: "{app}\{#AppExeName}"; Parameters: "--gui"; IconFilename: "{app}\images\LDEico.ico"
Name: "{group}\User Guide"; Filename: "{app}\USER_GUIDE.pdf"; Components: docs
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\images\LDEico.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Parameters: "--help"; Flags: nowait postinstall skipifsilent shellexec

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  SettingsFile: String;
  Content: String;
begin
  if CurStep = ssPostInstall then
  begin
    // Write default settings.json (user changes Drive/Branch in the GUI)
    SettingsFile := ExpandConstant('{app}\settings.json');
    if not FileExists(SettingsFile) then
    begin
      Content := '{' + #13#10 +
                 '  "drive_letter": "F",' + #13#10 +
                 '  "branch": "mainline",' + #13#10 +
                 '  "loc_folder": "F:\\perforce\\cd\\mainline\\resource\\GameData\\stringtable\\loc",' + #13#10 +
                 '  "export_folder": "F:\\perforce\\cd\\mainline\\resource\\GameData\\stringtable\\export__",' + #13#10 +
                 '  "vrs_folder": "F:\\perforce\\cd\\mainline\\resource\\editordata\\VoiceRecordingSheet__",' + #13#10 +
                 '  "description": "Runtime configuration - change Drive and Branch in the GUI"' + #13#10 +
                 '}';
      SaveStringToFile(SettingsFile, Content, False);
    end;
  end;
end;
