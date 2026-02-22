; CodeMax-PackMaster.iss
[Setup]
AppName=CodeMax-PackMaster Demo
AppVersion=1.0
AppVerName=CodeMax-PackMaster Demo 1.0
AppPublisher=SolmirMech
AppCopyright=Copyright © 2025 SolmirMech. Все права защищены.
DefaultDirName={pf}\CodeMax-PackMaster Demo
DefaultGroupName=CodeMax-PackMaster Demo
OutputBaseFilename=CodeMax-PackMaster_Demo_Setup
Compression=lzma
SolidCompression=yes
UninstallDisplayIcon={app}\CodeMax-PackMaster.exe
SetupIconFile=M:\Tests\PackMaster_Installer\CodeMax-PackMaster\_internal\assets\icons\icon.ico
OutputDir=M:\Tests
LicenseFile=M:\CodeMax-CutMaster_showcase\Public_Offer.txt
DefaultDialogFontName=Segoe UI
WizardStyle=modern

; РУССКИЙ ЯЗЫК
[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

; КОД ДЛЯ ДЕМО-ВЕРСИИ (3 ДНЯ)
[Code]
function InitializeSetup(): Boolean;
var
  Version: TWindowsVersion;
begin
  // Проверка версии Windows
  GetWindowsVersionEx(Version);
  
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

procedure CurStepChanged(CurStep: TSetupStep);
var
  DemoFile: string;
  DemoInfo: TStringList;
begin
  if CurStep = ssPostInstall then
  begin
    // Создаем скрытый файл с датой установки в папке _internal
    DemoFile := ExpandConstant('{app}\_internal\_tkinter.ini');
    DemoInfo := TStringList.Create;
    try
      DemoInfo.Add('[Demo]');
      DemoInfo.Add('InstallDate=' + GetDateTimeString('yyyy-mm-dd', '-', ':'));
      DemoInfo.Add('ExpireDays=3');
      DemoInfo.SaveToFile(DemoFile);
    finally
      DemoInfo.Free;
    end;
    
    // Показываем сообщение о демо-версии
    MsgBox(
      'Демо-версия активирована!' + #13#10 +
      'Срок действия: 3 дня' + #13#10 +
      'После окончания срока программа перестанет работать.' + #13#10 +
      'Контакты для покупки полной версии смотрите в лицензионном соглашении.',
      mbInformation, MB_OK
    );
  end;
end;

[Messages]
russian.WelcomeLabel1=Добро пожаловать в демо-версию [name]
russian.WelcomeLabel2=Эта программа установит демо-версию [name/ver] на ваш компьютер.%n%nСрок действия демо-версии: 3 дня.%n%nПосле окончания срока программа перестанет работать.

[Tasks]
Name: "desktopicon"; Description: "Создать значок на рабочем столе"; GroupDescription: "Дополнительно:"

[Files]
Source: "M:\Tests\PackMaster_Installer\CodeMax-PackMaster\CodeMax-PackMaster.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "M:\CodeMax-CutMaster_showcase\Public_Offer.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "M:\Tests\PackMaster_Installer\CodeMax-PackMaster\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs

; ⭐ ДЕМО-ФАЙЛ БУДЕТ СОЗДАН АВТОМАТИЧЕСКИ ПРИ УСТАНОВКЕ ⭐

[Icons]
Name: "{group}\CodeMax-PackMaster Demo"; Filename: "{app}\CodeMax-PackMaster.exe"
Name: "{group}\Удалить CodeMax-PackMaster Demo"; Filename: "{uninstallexe}"
Name: "{autodesktop}\CodeMax-PackMaster Demo"; Filename: "{app}\CodeMax-PackMaster.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\CodeMax-PackMaster.exe"; Description: "Запустить CodeMax-PackMaster Demo"; Flags: nowait postinstall skipifsilent