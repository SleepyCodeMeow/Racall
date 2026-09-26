; Small language/location window, executed before the parent initializes NSIS translations.
Unicode true
RequestExecutionLevel user
Name "Racall"
OutFile "${PROJECT_DIR}\build\racall-installer-welcome.exe"
InstallDir "$LOCALAPPDATA\Programs\Racall"
Icon "${PROJECT_DIR}\assets\icon.ico"
!include MUI2.nsh
!include FileFunc.nsh
!include "${PROJECT_DIR}\installer\appearance.nsh"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_RIGHT
!define MUI_HEADERIMAGE_BITMAP "${PROJECT_DIR}\installer\assets\header.bmp"
!include "${PROJECT_DIR}\installer\catalog.nsh"
!include "${PROJECT_DIR}\installer\welcome.nsh"
Var RacallSectionKB
Var RacallResult
!insertmacro RacallWelcomePage
!insertmacro RacallLoadLanguages
!insertmacro customHeader
!macro RacallAcceptCommandLanguage LOCALE ID NAME SEARCH
  ${If} $R1 == "${ID}"
    StrCpy $LANGUAGE ${ID}
  ${EndIf}
!macroend
Function .onInit
  SetErrorLevel 1
  StrCpy $LANGUAGE 1033
  ${GetParameters} $R0
  ${GetOptions} $R0 "/LANGUAGE=" $R1
  !insertmacro RacallEachLanguage RacallAcceptCommandLanguage
  ${GetOptions} $R0 "/REQUIRED=" $RacallSectionKB
  ${GetOptions} $R0 "/RESULT=" $RacallResult
  ${If} $RacallResult == ""
    Quit
  ${EndIf}
FunctionEnd
Function RacallAccept
  ClearErrors
  WriteINIStr "$RacallResult" "selection" "language" "$LANGUAGE"
  WriteINIStr "$RacallResult" "selection" "directory" "$INSTDIR"
  ${If} ${Errors}
    Abort
  ${EndIf}
  SetErrorLevel 0
  Quit
FunctionEnd
!pragma warning disable 8000 ; This helper deliberately has no installation page.
Section
  ; No installation commands. The parent performs installation after reading the selection.
SectionEnd
