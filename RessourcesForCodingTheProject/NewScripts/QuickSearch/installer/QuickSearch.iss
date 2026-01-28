; QuickSearch Inno Setup Script
; Creates installer with drive selection

#define MyAppName "QuickSearch"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Neil"
#define MyAppExeName "QuickSearch.exe"
#define MyAppDescription "Translation Search & QA Tool"

[Setup]
AppId={{A7B8C9D0-E1F2-3456-7890-ABCDEF123456}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={code:GetDefaultDir}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\installer_output
OutputBaseFilename={#MyAppName}_v{#MyAppVersion}_Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
SetupIconFile=..\images\QSico.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\QuickSearch\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\images\QSico.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\images\QSico.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
var
  DrivePage: TInputOptionWizardPage;
  DriveLetters: TStringList;

function GetAvailableDrives(): TStringList;
var
  i: Integer;
  DrivePath: String;
begin
  Result := TStringList.Create;
  // Check common drive letters
  for i := Ord('C') to Ord('Z') do
  begin
    DrivePath := Chr(i) + ':\';
    if DirExists(DrivePath) then
      Result.Add(Chr(i) + ':');
  end;
end;

procedure InitializeWizard;
var
  i: Integer;
begin
  DriveLetters := GetAvailableDrives();

  DrivePage := CreateInputOptionPage(
    wpSelectDir,
    'Select Installation Drive',
    'Choose which drive to install QuickSearch on.',
    'Available drives on your system:',
    True, False
  );

  for i := 0 to DriveLetters.Count - 1 do
  begin
    DrivePage.Add(DriveLetters[i] + ' Drive');
  end;

  // Default to first available drive (usually C:)
  if DrivePage.Values[0] = False then
    DrivePage.SelectedValueIndex := 0;
end;

function GetDefaultDir(Param: String): String;
var
  SelectedIndex: Integer;
begin
  if Assigned(DrivePage) and (DriveLetters.Count > 0) then
  begin
    SelectedIndex := DrivePage.SelectedValueIndex;
    if (SelectedIndex >= 0) and (SelectedIndex < DriveLetters.Count) then
      Result := DriveLetters[SelectedIndex]
    else
      Result := 'C:';
  end
  else
    Result := 'C:';
end;

procedure DeinitializeSetup();
begin
  if Assigned(DriveLetters) then
    DriveLetters.Free;
end;
