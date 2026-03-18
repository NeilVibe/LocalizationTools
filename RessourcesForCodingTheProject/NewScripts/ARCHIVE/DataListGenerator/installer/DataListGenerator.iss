; DataListGenerator Installer Script
; Inno Setup 6.0+
;
; Features:
; - Portable install (Desktop by default, NOT Program Files)
; - Drive selection for Perforce LOC path (F:, D:, E:, etc.)
; - No Python required (bundled via PyInstaller)
; - No admin rights required

#define MyAppName "DataListGenerator"
#define MyAppVersion "3.0.0"
#define MyAppPublisher "Localization Team"
#define MyAppExeName "DataListGenerator.exe"

[Setup]
; Application info
AppId={{D1A2B3C4-5E6F-7A8B-9C0D-1E2F3A4B5C6D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}

; PORTABLE INSTALL - Desktop by default (no admin needed)
DefaultDirName={userdesktop}\DataListGenerator
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Output
OutputDir=..\installer_output
OutputBaseFilename=DataListGenerator_v{#MyAppVersion}_Setup
UninstallDisplayIcon={app}\{#MyAppExeName}

; Compression
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; System requirements
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
MinVersion=6.1sp1

; NO ADMIN REQUIRED - critical for high security facility
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline

; Pages
DisableWelcomePage=no
DisableDirPage=no
DisableReadyPage=no
DisableFinishedPage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Types]
Name: "full"; Description: "Full installation"
Name: "custom"; Description: "Custom installation"; Flags: iscustom

[Components]
Name: "main"; Description: "DataListGenerator"; Types: full custom; Flags: fixed
Name: "docs"; Description: "Documentation"; Types: full

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Main application
Source: "..\dist\DataListGenerator\DataListGenerator.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\DataListGenerator\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

; Working folders (empty but necessary)
Source: "..\dist\DataListGenerator\Output\*"; DestDir: "{app}\Output"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

; Documentation (optional component)
Source: "..\README.md"; DestDir: "{app}"; Components: docs; Flags: ignoreversion

[Dirs]
; Create empty folders if they don't exist
Name: "{app}\Output"
Name: "{app}\Output\Translations"

[Icons]
; Start Menu
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autoprograms}\{#MyAppName}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

; Desktop (checked by default for easy access)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Launch after install
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up generated files
Type: filesandordirs; Name: "{app}\*.xlsx"
Type: filesandordirs; Name: "{app}\*.log"
Type: filesandordirs; Name: "{app}\Output"

[Code]
var
  DriveSelectionPage: TInputQueryWizardPage;
  DriveLetter: String;

procedure InitializeWizard();
begin
  // Create drive selection page
  DriveSelectionPage := CreateInputQueryPage(wpWelcome,
    'Perforce Drive Selection',
    'Select the drive where your Perforce workspace is located.',
    'DataListGenerator needs to know where your Perforce data folders are.' + #13#10 + #13#10 + 'Default paths:' + #13#10 + '  - F:\perforce\cd\mainline\resource\GameData\StaticInfo\factioninfo' + #13#10 + '  - F:\perforce\cd\mainline\resource\GameData\StaticInfo\skillinfo' + #13#10 + '  - F:\perforce\cd\mainline\resource\GameData\stringtable\loc' + #13#10 + #13#10 + 'If your Perforce is on a different drive (D:, E:, etc.), enter just the letter.'
  );
  DriveSelectionPage.Add('Drive Letter (e.g., F, D, E):', False);
  DriveSelectionPage.Values[0] := 'F';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  DriveInput: String;
begin
  Result := True;

  if CurPageID = DriveSelectionPage.ID then
  begin
    DriveInput := Uppercase(Trim(DriveSelectionPage.Values[0]));

    // Validate: single letter A-Z
    if (Length(DriveInput) <> 1) or (DriveInput[1] < 'A') or (DriveInput[1] > 'Z') then
    begin
      MsgBox('Please enter a single drive letter (A-Z).', mbError, MB_OK);
      Result := False;
      Exit;
    end;

    DriveLetter := DriveInput;

    // Check if drive exists
    if not DirExists(DriveLetter + ':\') then
    begin
      if MsgBox('Drive ' + DriveLetter + ':\ does not appear to exist.' + #13#10 +
                'Are you sure you want to continue?',
                mbConfirmation, MB_YESNO) = IDNO then
      begin
        Result := False;
        Exit;
      end;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  SettingsPath: String;
  SettingsContent: String;
begin
  if CurStep = ssPostInstall then
  begin
    // Write settings.json with selected drive letter and paths
    SettingsPath := ExpandConstant('{app}\settings.json');
    SettingsContent := '{' + #13#10 +
      '    "drive_letter": "' + DriveLetter + '",' + #13#10 +
      '    "version": "3.0",' + #13#10 +
      '    "paths": {' + #13#10 +
      '        "factioninfo": "' + DriveLetter + ':\\perforce\\cd\\mainline\\resource\\GameData\\StaticInfo\\factioninfo",' + #13#10 +
      '        "skillinfo": "' + DriveLetter + ':\\perforce\\cd\\mainline\\resource\\GameData\\StaticInfo\\skillinfo",' + #13#10 +
      '        "loc_folder": "' + DriveLetter + ':\\perforce\\cd\\mainline\\resource\\GameData\\stringtable\\loc"' + #13#10 +
      '    }' + #13#10 +
      '}';
    SaveStringToFile(SettingsPath, AnsiString(SettingsContent), False);
  end;
end;

function GetDriveLetter(Param: String): String;
begin
  Result := DriveLetter;
end;
