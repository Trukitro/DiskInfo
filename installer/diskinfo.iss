; DiskInfo installer.
;
; Admin rights: installs per-user, no UAC elevation -- matches the app's own
; unprivileged default (WMI drive/SMART queries and the benchmark's temp
; file both work fine without admin).
;
; Autostart: opt-in via an unchecked installer checkbox, not on by default --
; a disk monitoring tool auto-launching at boot is the kind of thing that
; should be an explicit choice.

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
Name: "autostart"; Description: "Start DiskInfo automatically when Windows starts"; GroupDescription: "Startup:"; Flags: unchecked

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

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "DiskInfo"; ValueData: """{app}\{#MyAppExeName}"""; Tasks: autostart; Flags: uninsdeletevalue

[Run]
Filename: "{tmp}\MicrosoftEdgeWebView2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "Installing Microsoft WebView2 Runtime..."; Check: WebView2RuntimeMissing and FileExists(ExpandConstant('{tmp}\MicrosoftEdgeWebView2Setup.exe'))
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

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
