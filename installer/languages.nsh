; Use the installer choice only to seed a profile that has no saved preference.
; Persist beside the application, not in the elevated installer's user profile.
!include "FileFunc.nsh"
!define MUI_LANGDLL_ALWAYSSHOW

!macro preInit
  StrCpy $LANGUAGE 1033
  ${GetParameters} $R0
  ${GetOptions} $R0 "/LANGUAGE=" $R1
  ${If} $R1 == "1049"
    StrCpy $LANGUAGE 1049
  ${EndIf}
!macroend

!macro customInstall
  Push $R0
  Push $R1
  StrCpy $R1 "en"
  ${If} $LANGUAGE == 1049
    StrCpy $R1 "ru"
  ${EndIf}
  CreateDirectory "$INSTDIR\resources"
  ClearErrors
  FileOpen $R0 "$INSTDIR\resources\installer-language.json" w
  ${IfNot} ${Errors}
    FileWrite $R0 '{$\"locale$\":$\"$R1$\"}'
    FileClose $R0
  ${Else}
    ${If} $LANGUAGE == 1049
      MessageBox MB_OK|MB_ICONSTOP "Не удалось сохранить язык установки. Проверьте доступ к папке приложения."
    ${Else}
      MessageBox MB_OK|MB_ICONSTOP "Could not save the installation language. Check access to the app folder."
    ${EndIf}
    Abort
  ${EndIf}
  Pop $R1
  Pop $R0
!macroend
