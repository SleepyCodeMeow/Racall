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
  Var RacallBodyFont
  Var RacallTitleFont
  Var RacallDpi
  Var RacallTitle
  Var RacallLogo
  Var RacallLogoImage
  Var RacallContinue
  Var RacallDivider
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
    SetCtlColors $HWNDPARENT 000000 F0F0F0
    SetCtlColors $RacallPage 000000 FFFFFF
    GetDlgItem $RacallNext $HWNDPARENT 1
    GetDlgItem $0 $HWNDPARENT 3
    ShowWindow $0 ${SW_HIDE}

    ${NSD_CreateLabel} 0 0 100% 24 "Racall"
    Pop $RacallTitle
    SetCtlColors $RacallTitle 000000 FFFFFF
    ${NSD_CreateBitmap} 0 0 150 57 ""
    Pop $RacallLogo
    ${NSD_CreateLabel} 0 0 100% 22 ""
    Pop $RacallIntro
    SetCtlColors $RacallIntro 000000 FFFFFF
    ${NSD_CreateLabel} 0 0 100% 22 ""
    Pop $RacallContinue
    SetCtlColors $RacallContinue 000000 FFFFFF
    ${NSD_CreateLabel} 0 0 85 22 ""
    Pop $RacallLabel
    SetCtlColors $RacallLabel 000000 FFFFFF
    ${NSD_CreateDropList} 0 0 180 100 ""
    Pop $RacallLanguages
    ${NSD_CreateLabel} 0 0 100% 1 ""
    Pop $RacallDivider
    SetCtlColors $RacallDivider A0A0A0 A0A0A0
    !insertmacro RacallEachLanguage RacallAddLanguage
    ${NSD_OnChange} $RacallLanguages RacallLanguageChanged
    Call RacallRefreshText
    !insertmacro RacallReferenceLayout
    InitPluginsDir
    File /oname=$PLUGINSDIR\welcome.bmp "${PROJECT_DIR}\installer\assets\welcome.bmp"
    ${NSD_SetStretchedImage} $RacallLogo "$PLUGINSDIR\welcome.bmp" $RacallLogoImage
    ${NSD_SetFocus} $RacallNext
    nsDialogs::Show
  FunctionEnd

  Function RacallRefreshText
    !insertmacro RacallLoadText
    SendMessage $HWNDPARENT ${WM_SETTEXT} 0 'STR:$RacallText_setup'
    ${NSD_SetText} $RacallIntro "$RacallText_intro"
    ${NSD_SetText} $RacallContinue "$RacallText_continue"
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
