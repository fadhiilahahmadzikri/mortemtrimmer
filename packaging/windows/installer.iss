; Inno Setup 6 Per-User Installer for Mortem Trimmer ("Mortem")

#define MyAppName "Mortem Trimmer"
#define MyAppShortName "Mortem"
#define MyAppPublisher "Fadhiilah Ahmad Zikri"
#define MyAppPublisherURL "https://github.com/fadhiilahahmadzikri"
#define MyAppURL "https://github.com/fadhiilahahmadzikri/mortemtrimmer"
#define MyAppSupportURL "https://github.com/fadhiilahahmadzikri/mortemtrimmer/issues"
#define MyAppCopyright "Copyright (c) 2026 Fadhiilah Ahmad Zikri"
#define MyAppVersion "1.0.0"
#define MyAppExeName "autosilenttrimmer.exe"
#define MyAppShimExeName "trim-shim.exe"
#define MyAppUserModelID "MortemTrimmer.DesktopApp.1"

[Setup]
AppId={{B4E73E3A-9C2F-4F91-A72E-83D18D410F12}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppPublisherURL}
AppSupportURL={#MyAppSupportURL}
AppUpdatesURL={#MyAppURL}/releases
AppCopyright={#MyAppCopyright}
DefaultDirName={localappdata}\Programs\AutoSilentTrimmer
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UsePreviousTasks=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\dist\installer
OutputBaseFilename=MortemTrimmer-Setup-{#MyAppVersion}-win-x64
SetupIconFile=..\..\packaging\windows\mortem.ico
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
Name: "autostart"; Description: "Start {#MyAppName} background service on sign-in"; Flags: unchecked

[Files]
Source: "..\..\dist\AutoSilentTrimmer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\dist\{#MyAppShimExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\packaging\dist_notices\THIRD_PARTY_NOTICES.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--daemon --tray"; AppUserModelID: "{#MyAppUserModelID}"
Name: "{group}\Settings - {#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--tune"
Name: "{group}\System Logs - {#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--logs"
Name: "{group}\System Readiness Check"; Filename: "{app}\autosilenttrimmer-cli.exe"; Parameters: "--check"
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--daemon --tray"; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--register-shell"; Flags: runhidden waituntilterminated; Tasks: contextmenu

[UninstallRun]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--unregister-shell"; Flags: runhidden waituntilterminated; RunOnceId: "UnregisterShell"

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  Result := '';
  // Stop headless tray/shim processes cleanly before file replacement (prevents CloseApplications lock prompt)
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM autosilenttrimmer.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM trim-shim.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{localappdata}\autosilenttrimmer');
    if (not UninstallSilent()) and DirExists(DataDir) then
    begin
      if SuppressibleMsgBox('Remove downloaded Runtime Packs, logs, and settings from ' + DataDir + '?', mbConfirmation, MB_YESNO or MB_DEFBUTTON2, IDNO) = IDYES then
      begin
        DelTree(DataDir, True, True, True);
      end;
    end;
  end;
end;
