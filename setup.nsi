; RainTranslator - NSIS Installer Script
Unicode true
!include "MUI2.nsh"

Name "RainTranslator"
OutFile "RainTranslator_Setup.exe"
InstallDir "$PROGRAMFILES64\RainTranslator"
RequestExecutionLevel admin
Icon "app.ico"
SetCompressor /SOLID lzma

!define MUI_ICON "app.ico"
!define MUI_UNICON "app.ico"

!insertmacro MUI_PAGE_WELCOME

; 模型下载说明页
Page custom ModelPage ModelPageLeave

!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "SimpChinese"

Var Checkbox

Function ModelPage
    !insertmacro MUI_HEADER_TEXT "本地翻译模型" "选择是否下载本地翻译模型"
    nsDialogs::Create 1018
    Pop $0
    ${NSD_CreateLabel} 0 0 100% 40u "RainTranslator 使用腾讯 Hy-MT2 本地翻译模型，首次运行时自动下载。$\n模型大小约 1GB，下载后即可离线翻译。"
    Pop $0
    ${NSD_CreateCheckbox} 0 50u 100% 20u "安装完成后自动下载模型（推荐）"
    Pop $Checkbox
    ${NSD_Check} $Checkbox
    nsDialogs::Show
FunctionEnd

Function ModelPageLeave
    ${NSD_GetState} $Checkbox $0
    ; $0 = 1 if checked (BST_CHECKED), store for later
    StrCpy $0 $0
FunctionEnd

Section "Install"
    SetOutPath "$INSTDIR"

    ; Main executable and Python runtime
    File /r "dist\RainTranslator\*"
    
    ; Icon file
    File "app.ico"

    ; Create empty models folder
    CreateDirectory "$INSTDIR\models"

    ; Shortcuts - explicit icon
    CreateShortCut "$DESKTOP\RainTranslator.lnk" "$INSTDIR\RainTranslator.exe" "" "$INSTDIR\app.ico"
    CreateDirectory "$SMPROGRAMS\RainTranslator"
    CreateShortCut "$SMPROGRAMS\RainTranslator\RainTranslator.lnk" "$INSTDIR\RainTranslator.exe" "" "$INSTDIR\app.ico"
    CreateShortCut "$SMPROGRAMS\RainTranslator\卸载.lnk" "$INSTDIR\Uninstall.exe"

    WriteUninstaller "$INSTDIR\Uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\RainTranslator" "DisplayName" "RainTranslator"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\RainTranslator" "UninstallString" "$INSTDIR\Uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\RainTranslator" "DisplayIcon" "$INSTDIR\RainTranslator.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\RainTranslator" "Publisher" "RainTranslator"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\RainTranslator" "DisplayVersion" "1.0"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\RainTranslator" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\RainTranslator" "NoRepair" 1
SectionEnd

Section "Uninstall"
    ; Kill running processes
    nsExec::ExecToStack 'taskkill /f /im RainTranslator.exe'
    nsExec::ExecToStack 'taskkill /f /im llama-server.exe'
    Sleep 1000
    
    ; Remove model files (install directory)
    Delete "$INSTDIR\models\*.gguf"
    RMDir "$INSTDIR\models"
    
    ; Remove all installed files
    RMDir /r /REBOOTOK "$INSTDIR"
    
    ; Remove shortcuts
    Delete "$DESKTOP\RainTranslator.lnk"
    Delete "$SMPROGRAMS\RainTranslator\RainTranslator.lnk"
    Delete "$SMPROGRAMS\RainTranslator\卸载.lnk"
    RMDir "$SMPROGRAMS\RainTranslator"
    
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\RainTranslator"
SectionEnd
