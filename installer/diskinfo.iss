; DiskInfo installer.
;
; Admin rights: the installer itself runs unprivileged (installs per-user,
; no UAC elevation to install) -- but the app *itself* always requests
; elevation on launch (diskinfo.spec's uac_admin=True), since some drive
; roots need admin to write the benchmark temp file to. See
; DiskInfo-project-plan.md's "Why DiskInfo runs elevated".
;
; Autostart: not offered here anymore -- an elevation-manifested exe
; launched from the registry Run key (which an installer-time checkbox
; would normally write to) doesn't reliably start at logon. Autostart is
; a Scheduled Task instead, created/removed from the in-app Settings page
; (see backend/app/autostart.py), which the installer can't do at install
; time anyway since scheduled-task creation needs the *app* to already be
; elevated when it's toggled, not the installer.

#define MyAppName "DiskInfo"
#ifndef MyAppVersion
  #define MyAppVersion "6.0.0"
#endif
#define MyAppPublisher "Trukitro"
#define MyAppExeName "DiskInfo.exe"
#define MyAppURL "https://github.com/Trukitro/DiskInfo"

[Setup]
AppId={{E6C1F6A0-9F0A-4E2C-8D5B-4A2F6C7B9D31}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=DiskInfoSetup
SetupIconFile=..\assets\icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"

[Files]
Source: "..\backend\dist\DiskInfo\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Fetched by the release workflow (.github/workflows/release.yml) from Microsoft's
; official evergreen WebView2 bootstrapper before this script is compiled -- not
; committed to the repo. Setup still works if it's absent (see Check: below).
Source: "redist\MicrosoftEdgeWebView2Setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall skipifsourcedoesntexist

[Icons]
; IconFilename points at the exe itself (which PyInstaller already embeds icon.ico
; into) rather than the assets\ copy -- that copy actually lands at
; {app}\_internal\assets\icon.ico under PyInstaller's onedir layout, and chasing that
; internal path is one PyInstaller version bump away from silently breaking again.
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{tmp}\MicrosoftEdgeWebView2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "Installing Microsoft WebView2 Runtime..."; Check: WebView2RuntimeMissing and FileExists(ExpandConstant('{tmp}\MicrosoftEdgeWebView2Setup.exe'))
; shellexec is required here, not optional -- [Run] entries launch via
; CreateProcess by default, which cannot elevate a process. DiskInfo.exe's
; requireAdministrator manifest (diskinfo.spec's uac_admin=True) needs
; ShellExecute to trigger the UAC prompt; without this flag the post-install
; "Launch DiskInfo" step fails outright with error 740 (ERROR_ELEVATION_REQUIRED)
; instead of prompting. Desktop/Start Menu shortcuts in [Icons] don't need this --
; Explorer already launches .lnk targets via ShellExecute on double-click.
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent shellexec

[Code]
function WebView2RuntimeMissing(): Boolean;
var
  Version: String;
begin
  { Same runtime GUID Microsoft documents for detecting an existing WebView2
    Evergreen install; checked under both the WOW6432Node and native paths
    since installers can register under either depending on OS/runtime bitness. }
  Result := not (
    RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version)
    or RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version)
  );
end;
