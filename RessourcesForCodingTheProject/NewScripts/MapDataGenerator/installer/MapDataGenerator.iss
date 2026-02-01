; MapDataGenerator Inno Setup Script
; Creates Windows installer for MapDataGenerator
; Includes drive selection for Perforce workspace

#define MyAppName "MapDataGenerator"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "LocaNext Team"
#define MyAppExeName "MapDataGenerator.exe"

[Setup]
AppId={{B7E3F8D2-5A6C-4E9B-8D1F-3C7A2E4B6F9D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\installer_output
OutputBaseFilename=MapDataGenerator_Setup_{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main application files from PyInstaller dist folder
Source: "..\dist\MapDataGenerator\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
; Create working directories
Name: "{app}\logs"
Name: "{app}\cache"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up generated files on uninstall
Type: files; Name: "{app}\*.log"
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\cache"

[Code]
var
  DriveSelectionPage: TInputQueryWizardPage;
  DriveLetter: String;

procedure InitializeWizard();
begin
  // Create drive selection page (after welcome page)
  DriveSelectionPage := CreateInputQueryPage(wpWelcome,
    'Perforce Drive Selection',
    'Select the drive where your Perforce workspace is located.',
    'MapDataGenerator needs to know where your game data is located.' + #13#10 + #13#10 + 'Default path: F:\perforce\cd\mainline\resource\GameData' + #13#10 + #13#10 + 'If your Perforce is on a different drive (D:, E:, etc.), enter just the letter.' + #13#10 + 'Leave as F if you are unsure.'
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

    // Check if drive exists (warning only, don't block)
    if not DirExists(DriveLetter + ':\') then
    begin
      if MsgBox('Drive ' + DriveLetter + ':\ does not appear to exist.' + #13#10 + 'This is OK if you will mount the drive later.' + #13#10 + 'Continue with drive ' + DriveLetter + ':?', mbConfirmation, MB_YESNO) = IDNO then
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
    // Write settings.json with selected drive letter
    SettingsPath := ExpandConstant('{app}\settings.json');
    SettingsContent := '{"drive_letter": "' + DriveLetter + '", "version": "1.0"}';
    SaveStringToFile(SettingsPath, AnsiString(SettingsContent), False);
  end;
end;

function GetDriveLetter(Param: String): String;
begin
  Result := DriveLetter;
end;
