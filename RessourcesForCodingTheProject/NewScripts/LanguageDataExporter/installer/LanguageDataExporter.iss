; LanguageDataExporter Inno Setup Script
; Builds installer with drive selection for Perforce paths

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
SetupIconFile=
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

[Files]
; Main application and PyInstaller runtime
; PyInstaller bundles everything into exe + _internal folder
Source: "..\dist\LanguageDataExporter\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{app}\GeneratedExcel"; Permissions: users-modify

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{#AppName} (GUI)"; Filename: "{app}\{#AppExeName}"; Parameters: "--gui"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Parameters: "--help"; Flags: nowait postinstall skipifsilent shellexec

[Code]
var
  DriveSelectionPage: TInputQueryWizardPage;

procedure InitializeWizard;
begin
  // Create drive selection page
  DriveSelectionPage := CreateInputQueryPage(wpSelectDir,
    'Perforce Drive Selection',
    'Select the drive where your Perforce workspace is located.',
    'The application needs to know which drive contains your Perforce workspace.' + #13#10 +
    'Default paths use F: drive. Enter a different letter if your workspace is on another drive.' + #13#10#13#10 +
    'Examples: F, D, E, G');

  DriveSelectionPage.Add('Drive Letter (without colon):', False);
  DriveSelectionPage.Values[0] := 'F';
end;

function GetDriveLetter: String;
var
  Drive: String;
begin
  Drive := Uppercase(Trim(DriveSelectionPage.Values[0]));
  // Validate single letter A-Z
  if (Length(Drive) = 1) and (Drive[1] >= 'A') and (Drive[1] <= 'Z') then
    Result := Drive
  else
    Result := 'F';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Drive: String;
  DrivePath: String;
begin
  Result := True;

  if CurPageID = DriveSelectionPage.ID then
  begin
    Drive := GetDriveLetter;
    DrivePath := Drive + ':\';

    // Check if drive exists
    if not DirExists(DrivePath) then
    begin
      if MsgBox('Drive ' + DrivePath + ' does not appear to exist.' + #13#10 +
                'This may cause issues if the Perforce workspace is not accessible.' + #13#10#13#10 +
                'Continue anyway?', mbConfirmation, MB_YESNO) = IDNO then
      begin
        Result := False;
      end;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  SettingsFile: String;
  Drive: String;
  Content: String;
begin
  if CurStep = ssPostInstall then
  begin
    // Write settings.json with selected drive
    Drive := GetDriveLetter;
    SettingsFile := ExpandConstant('{app}\settings.json');

    Content := '{' + #13#10 +
               '  "drive_letter": "' + Drive + '",' + #13#10 +
               '  "loc_folder": "' + Drive + ':\\perforce\\cd\\mainline\\resource\\GameData\\stringtable\\loc",' + #13#10 +
               '  "export_folder": "' + Drive + ':\\perforce\\cd\\mainline\\resource\\GameData\\stringtable\\export__",' + #13#10 +
               '  "vrs_folder": "' + Drive + ':\\perforce\\cd\\mainline\\resource\\editordata\\VoiceRecordingSheet__",' + #13#10 +
               '  "description": "Runtime configuration - edit paths if needed"' + #13#10 +
               '}';

    SaveStringToFile(SettingsFile, Content, False);
  end;
end;
