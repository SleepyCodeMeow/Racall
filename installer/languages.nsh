!include "${PROJECT_DIR}\installer\appearance.nsh"

; Use the installer choice only to seed a profile that has no saved preference.
; Persist beside the application, not in the elevated installer's user profile.
!include "FileFunc.nsh"
!include "${PROJECT_DIR}\installer\catalog.nsh"
!include "${PROJECT_DIR}\installer\selection.nsh"

!macro preInit
  StrCpy $LANGUAGE 1033
  ${GetParameters} $R0
  ${GetOptions} $R0 "/LANGUAGE=" $R1
  !insertmacro RacallEachLanguage RacallAcceptCommandLanguage
!macroend

!macro customInstall
  Push $R0
  Push $R1
  StrCpy $R1 "en"
  !insertmacro RacallEachLanguage RacallSeedLanguage
  CreateDirectory "$INSTDIR\resources"
  ClearErrors
  FileOpen $R0 "$INSTDIR\resources\installer-language.json" w
  ${IfNot} ${Errors}
    FileWrite $R0 '{$\"locale$\":$\"$R1$\"}'
    FileClose $R0
  ${Else}
    MessageBox MB_OK|MB_ICONSTOP "$(Racall_seedError)"
    Abort
  ${EndIf}
  Pop $R1
  Pop $R0
!macroend

!macro RacallAcceptCommandLanguage LOCALE ID NAME SEARCH
  ${If} $R1 == "${ID}"
    StrCpy $LANGUAGE ${ID}
  ${EndIf}
!macroend

!macro RacallSeedLanguage LOCALE ID NAME SEARCH
  ${If} $LANGUAGE == ${ID}
    StrCpy $R1 "${LOCALE}"
  ${EndIf}
!macroend
