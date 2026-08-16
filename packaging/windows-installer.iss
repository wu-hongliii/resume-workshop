#ifndef AppVersion
  #define AppVersion "0.3.0-beta"
#endif

[Setup]
AppId={{B5A9ED97-1C65-48D8-9136-09F12A6A4219}
AppName=简历工坊
AppVersion={#AppVersion}
AppPublisher=Resume Workshop
AppPublisherURL=https://github.com/wu-hongliii/resume-workshop
AppSupportURL=https://github.com/wu-hongliii/resume-workshop/issues
AppUpdatesURL=https://github.com/wu-hongliii/resume-workshop/releases
LicenseFile=..\LICENSE
DefaultDirName={localappdata}\Programs\ResumeWorkshop
DefaultGroupName=简历工坊
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\release
OutputBaseFilename=ResumeWorkshop-Setup-Windows-x64
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName=简历工坊

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加快捷方式："; Flags: checkedonce

[Files]
Source: "..\dist\ResumeWorkshop\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\简历工坊"; Filename: "{app}\ResumeWorkshop.exe"
Name: "{autodesktop}\简历工坊"; Filename: "{app}\ResumeWorkshop.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ResumeWorkshop.exe"; Description: "启动简历工坊"; Flags: nowait postinstall skipifsilent
