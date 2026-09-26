; Minimal first page: introductory text and one native language dropdown.
!include nsDialogs.nsh
!include LogicLib.nsh
!include WinMessages.nsh
!include "${PROJECT_DIR}\installer\layout.nsh"

!macro RacallAddLanguage LOCALE ID NAME
  SendMessage $RacallLanguages ${CB_ADDSTRING} 0 'STR:${NAME}' $1
  SendMessage $RacallLanguages ${CB_SETITEMDATA} $1 ${ID}
  ${If} $LANGUAGE == ${ID}
    SendMessage $RacallLanguages ${CB_SETCURSEL} $1 0
  ${EndIf}
!macroend

!macro RacallWelcomePage
  !insertmacro RacallTextVariables
  !insertmacro MUI_PAGE_INIT
  Page custom RacallWelcome RacallWelcomeLeave
  Var RacallPage
  Var RacallIntro
  Var RacallLabel
  Var RacallLanguages
  Var RacallNext

  Function RacallWelcome
    nsDialogs::Create 1018
    Pop $RacallPage
    ${If} $RacallPage == error
      Abort
    ${EndIf}
    SetCtlColors $HWNDPARENT 242424 FFFFFF
    SetCtlColors $RacallPage 242424 FFFFFF
    GetDlgItem $RacallNext $HWNDPARENT 1
    GetDlgItem $0 $HWNDPARENT 3
    ShowWindow $0 ${SW_HIDE}

    ${NSD_CreateLabel} 0 0 100% 25u ""
    Pop $RacallIntro
    SetCtlColors $RacallIntro 242424 FFFFFF
    ${NSD_CreateLabel} 0 38u 55u 12u ""
    Pop $RacallLabel
    SetCtlColors $RacallLabel 242424 FFFFFF
    ${NSD_CreateDropList} 60u 34u 145u 65u ""
    Pop $RacallLanguages
    !insertmacro RacallEachLanguage RacallAddLanguage
    ${NSD_OnChange} $RacallLanguages RacallLanguageChanged
    Call RacallRefreshText
    GetDlgItem $0 $HWNDPARENT 1256
    ShowWindow $0 ${SW_HIDE}
    GetDlgItem $0 $HWNDPARENT 1028
    ShowWindow $0 ${SW_HIDE}
    !insertmacro RacallCompactLayout
    ${NSD_SetFocus} $RacallLanguages
    nsDialogs::Show
  FunctionEnd

  Function RacallRefreshText
    !insertmacro RacallLoadText
    !insertmacro MUI_HEADER_TEXT "Racall" ""
    SendMessage $HWNDPARENT ${WM_SETTEXT} 0 'STR:$RacallText_setup'
    ${NSD_SetText} $RacallIntro "$RacallText_intro"
    ${NSD_SetText} $RacallLabel "$RacallText_language"
    ${NSD_SetText} $RacallNext "$RacallText_install"
    GetDlgItem $0 $HWNDPARENT 2
    ${NSD_SetText} $0 "$RacallText_cancel"
  FunctionEnd

  Function RacallLanguageChanged
    Pop $0
    SendMessage $RacallLanguages ${CB_GETCURSEL} 0 0 $0
    ${If} $0 != -1
      SendMessage $RacallLanguages ${CB_GETITEMDATA} $0 0 $1
      StrCpy $LANGUAGE $1
      Call RacallRefreshText
    ${EndIf}
  FunctionEnd

  Function RacallWelcomeLeave
    ; Keep the disk-space guard without displaying technical details on the first screen.
    ${GetRoot} "$INSTDIR" $0
    StrCpy $0 "$0\"
    System::Call 'kernel32::GetDiskFreeSpaceExW(w r0, *l .r1, p 0, p 0) i.r2'
    ${If} $2 != 0
      System::Int64Op $1 / 1048576
      Pop $1
      IntOp $2 $RacallSectionKB + 1023
      IntOp $2 $2 / 1024
      ${If} $1 < $2
        MessageBox MB_OK|MB_ICONEXCLAMATION "$RacallText_spaceError"
        Abort
      ${EndIf}
    ${EndIf}
    Call RacallAccept
  FunctionEnd
!macroend
