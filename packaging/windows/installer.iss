; Inno Setup 6 Per-User Installer for AutoSilentTrimmer ("Trim This Video")
; Aligned with docs/01_blueprint_produk_arsitektur.md & docs/02_feasibility_dan_distribusi.md

#define MyAppName "Trim This Video"
#define MyAppPublisher "AutoSilentTrimmer"
#define MyAppVersion "1.0.0"
#define MyAppExeName "autosilenttrimmer.exe"
#define MyAppShimExeName "trim-shim.exe"
#define MyAppUserModelID "AutoSilentTrimmer.DesktopApp.1"

[Setup]
AppId={{B4E73E3A-9C2F-4F91-A72E-83D18D410F12}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\AutoSilentTrimmer
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\dist\installer
OutputBaseFilename=TrimThisVideo-Setup-{#MyAppVersion}-win-x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
LicenseFile=..\..\LICENSE
InfoBeforeFile=..\..\packaging\dist_notices\THIRD_PARTY_NOTICES.txt
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "contextmenu"; Description: "Register right-click 'Trim This Video' menu in File Explorer"
Name: "autostart"; Description: "Start Trim This Video background service on sign-in"; Flags: unchecked

[Files]
Source: "..\..\dist\AutoSilentTrimmer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\dist\{#MyAppShimExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\packaging\dist_notices\THIRD_PARTY_NOTICES.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--daemon --tray"; AppUserModelID: "{#MyAppUserModelID}"
Name: "{group}\System Readiness Check"; Filename: "{app}\autosilenttrimmer-cli.exe"; Parameters: "--check"
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--daemon --tray"; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--register-shell"; Flags: runhidden waituntilterminated; Tasks: contextmenu

[UninstallRun]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--unregister-shell"; Flags: runhidden waituntilterminated; RunOnceId: "UnregisterShell"

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{localappdata}\autosilenttrimmer');
    if DirExists(DataDir) then
    begin
      if MsgBox('Remove downloaded Runtime Packs, logs, and settings from ' + DataDir + '?', mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
      begin
        DelTree(DataDir, True, True, True);
      end;
    end;
  end;
end;
