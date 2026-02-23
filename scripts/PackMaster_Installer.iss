; CodeMax-CutMaster.iss
[Setup]
AppName=CodeMax-PackMaster
AppVersion=1.1
AppVerName=CodeMax-PackMaster 1.1
AppPublisher=SolmirMech
AppCopyright=Copyright © 2026 SolmirMech. Все права защищены.
DefaultDirName={pf}\CodeMax-PackMaster
DefaultGroupName=CodeMax-PackMaster
OutputBaseFilename=CodeMax-PackMaster_Setup
Compression=lzma
SolidCompression=yes
UninstallDisplayIcon={app}\CodeMax-PackMaster.exe
SetupIconFile=M:\Tests\PackMaster_Installer\CodeMax-PackMaster\_internal\assets\icons\icon.ico
OutputDir=M:\Tests
LicenseFile=M:\CodeMax-CutMaster_showcase\Public_Offer.txt
; Язык по умолчанию
DefaultDialogFontName=Segoe UI
WizardStyle=modern

; ДОБАВЛЯЕМ РУССКИЙ ЯЗЫК
[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

; ПРОВЕРКА ВЕРСИИ WINDOWS (Windows 8 и выше)
[Code]
function InitializeSetup(): Boolean;
var
  Version: TWindowsVersion;
begin
  // Получаем версию Windows
  GetWindowsVersionEx(Version);
  
  // Проверяем версию Windows (Windows 8 = версия 6.2)
  if (Version.Major < 6) or ((Version.Major = 6) and (Version.Minor < 2)) then
  begin
    MsgBox(
      'Эта программа требует Windows 8 или более позднюю версию.' + #13#10 +
      'Текущая версия Windows: ' + IntToStr(Version.Major) + '.' + IntToStr(Version.Minor),
      mbError, MB_OK
    );
    Result := False;
    Exit;
  end;

  Result := True;
end;

[Tasks]
Name: "desktopicon"; Description: "Создать значок на рабочем столе"; GroupDescription: "Дополнительно:"

[Files]
Source: "M:\Tests\PackMaster_Installer\CodeMax-PackMaster\CodeMax-PackMaster.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "M:\CodeMax-CutMaster_showcase\Public_Offer.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "M:\Tests\PackMaster_Installer\CodeMax-PackMaster\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\CodeMax-PackMaster"; Filename: "{app}\CodeMax-PackMaster.exe"
Name: "{group}\Удалить CodeMax-PackMaster"; Filename: "{uninstallexe}"
Name: "{autodesktop}\CodeMax-PackMaster"; Filename: "{app}\CodeMax-PackMaster.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\CodeMax-PackMaster.exe"; Description: "Запустить CodeMax-PackMaster"; Flags: nowait postinstall skipifsilent