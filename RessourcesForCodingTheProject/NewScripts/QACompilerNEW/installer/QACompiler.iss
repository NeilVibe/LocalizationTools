; QA Compiler Suite Installer Script
; Inno Setup 6.0+
;
; Features:
; - Portable install (Desktop by default, NOT Program Files)
; - Drive selection for Perforce LOC path (F:, D:, E:, etc.)
; - No Python required (bundled via PyInstaller)
; - No admin rights required
;
; User workflow:
; 1. Run installer
; 2. Select drive where Perforce is located
; 3. Choose install location (Desktop recommended)
; 4. Done! App works 100% standalone

#define MyAppName "QA Compiler Suite"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "Localization Team"
#define MyAppExeName "QACompiler.exe"

[Setup]
; Application info
AppId={{8A7B6C5D-4E3F-2A1B-9C8D-7E6F5A4B3C2D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}

; PORTABLE INSTALL - Desktop by default (no admin needed)
DefaultDirName={userdesktop}\QACompiler
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Output
OutputDir=..\installer_output
OutputBaseFilename=QACompiler_v{#MyAppVersion}_Setup
; Icon will be created if present, otherwise uses default
; SetupIconFile=..\images\qacompiler.ico
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
Name: "main"; Description: "QA Compiler Suite"; Types: full custom; Flags: fixed
Name: "docs"; Description: "Documentation and User Guide"; Types: full

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Main application
Source: "..\dist\QACompiler\QACompiler.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\QACompiler\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

; Working folders (empty but necessary)
Source: "..\dist\QACompiler\QAfolder\*"; DestDir: "{app}\QAfolder"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "..\dist\QACompiler\QAfolderOLD\*"; DestDir: "{app}\QAfolderOLD"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "..\dist\QACompiler\QAfolderNEW\*"; DestDir: "{app}\QAfolderNEW"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "..\dist\QACompiler\GeneratedDatasheets\*"; DestDir: "{app}\GeneratedDatasheets"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "..\dist\QACompiler\Masterfolder_EN\*"; DestDir: "{app}\Masterfolder_EN"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "..\dist\QACompiler\Masterfolder_CN\*"; DestDir: "{app}\Masterfolder_CN"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

; Tester list configuration
Source: "..\languageTOtester_list.example.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\languageTOtester_list.txt"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

; Tester type configuration (Text/Gameplay)
Source: "..\TesterType.example.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\TesterType.txt"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

; Documentation (optional component)
Source: "..\USER_GUIDE.pdf"; DestDir: "{app}"; Components: docs; Flags: ignoreversion
Source: "..\USER_GUIDE.html"; DestDir: "{app}"; Components: docs; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Components: docs; Flags: ignoreversion

[Dirs]
; Create empty folders if they don't exist
Name: "{app}\QAfolder"
Name: "{app}\QAfolderOLD"
Name: "{app}\QAfolderNEW"
Name: "{app}\GeneratedDatasheets"
Name: "{app}\Masterfolder_EN"
Name: "{app}\Masterfolder_EN\Images"
Name: "{app}\Masterfolder_CN"
Name: "{app}\Masterfolder_CN\Images"

[Icons]
; Start Menu
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autoprograms}\{#MyAppName}\User Guide"; Filename: "{app}\USER_GUIDE.pdf"
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
Type: filesandordirs; Name: "{app}\GeneratedDatasheets"
Type: filesandordirs; Name: "{app}\Masterfolder_EN"
Type: filesandordirs; Name: "{app}\Masterfolder_CN"

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
    'The QA Compiler needs to know where your Perforce LOC folder is.' + #13#10 + #13#10 + 'Default path: F:\perforce\cd\mainline\resource\GameData\stringtable\loc' + #13#10 + #13#10 + 'If your Perforce is on a different drive (D:, E:, etc.), enter just the letter.'
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
  ConfigPath: String;
  ConfigContent: AnsiString;
  NewContent: String;
begin
  if CurStep = ssPostInstall then
  begin
    // Update config.py with selected drive
    if DriveLetter <> 'F' then
    begin
      ConfigPath := ExpandConstant('{app}\_internal\config.py');
      if FileExists(ConfigPath) then
      begin
        LoadStringFromFile(ConfigPath, ConfigContent);
        NewContent := String(ConfigContent);
        StringChange(NewContent, 'F:\perforce', DriveLetter + ':\perforce');
        StringChange(NewContent, 'F:\\perforce', DriveLetter + ':\\perforce');
        SaveStringToFile(ConfigPath, AnsiString(NewContent), False);
      end;
    end;
  end;
end;

function GetDriveLetter(Param: String): String;
begin
  Result := DriveLetter;
end;
