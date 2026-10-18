; Inno Setup script: builds Yingjia-Setup.exe.
; Installs for the current user only (no administrator needed on school PCs),
; adds desktop and Start menu shortcuts, and can be removed from
; Settings > Apps like any other program. Class lists in %APPDATA%\Yingjia
; are kept on uninstall.
;
; Built by GitHub Actions: iscc /DAppVersion=1.2.3 installer\yingjia.iss

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{7E3C9B1E-5A2D-4F6B-9C4E-2B1A8D6F0E53}
AppName=Yingjia
AppVerName=Yingjia {#AppVersion}
AppVersion={#AppVersion}
AppPublisher=Yingjia
AppPublisherURL=https://github.com/ellenuttley/yingjia
DefaultDirName={autopf}\Yingjia
DefaultGroupName=Yingjia
DisableProgramGroupPage=yes
DisableDirPage=yes
PrivilegesRequired=lowest
OutputDir=..\out
OutputBaseFilename=Yingjia-Setup
SetupIconFile=..\assets\yingjia.ico
UninstallDisplayIcon={app}\Yingjia.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ShowLanguageDialog=auto

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
; Copied from Inno Setup's own translations, so the build doesn't depend on
; which languages the installed Inno Setup includes.
Name: "zh"; MessagesFile: "ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\Yingjia.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\guide\*.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Yingjia"; Filename: "{app}\Yingjia.exe"
Name: "{autoprograms}\Yingjia - How to use (English)"; Filename: "{app}\How to use Yingjia (English).txt"
Name: "{autoprograms}\Yingjia 使用说明 (中文)"; Filename: "{app}\Yingjia 使用说明 (中文).txt"
Name: "{autodesktop}\Yingjia"; Filename: "{app}\Yingjia.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Yingjia.exe"; Description: "{cm:LaunchProgram,Yingjia}"; Flags: nowait postinstall skipifsilent
