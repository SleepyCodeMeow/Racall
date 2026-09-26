; Reference geometry in 96-DPI pixels, using native Windows controls.
!macro RacallPlace CONTROL X Y WIDTH HEIGHT
  IntOp $0 ${X} * $RacallDpi
  IntOp $0 $0 / 96
  IntOp $1 ${Y} * $RacallDpi
  IntOp $1 $1 / 96
  IntOp $2 ${WIDTH} * $RacallDpi
  IntOp $2 $2 / 96
  IntOp $3 ${HEIGHT} * $RacallDpi
  IntOp $3 $3 / 96
  System::Call 'user32::SetWindowPos(p ${CONTROL}, p 0, i r0, i r1, i r2, i r3, i 4)'
!macroend

!macro RacallReferenceLayout
  System::Call 'user32::GetDpiForWindow(p $HWNDPARENT) i .r8'
  StrCpy $RacallDpi $8
  ${If} $RacallDpi == 0
    StrCpy $RacallDpi 96
  ${EndIf}
  IntOp $2 837 * $RacallDpi
  IntOp $2 $2 / 96
  IntOp $3 637 * $RacallDpi
  IntOp $3 $3 / 96
  System::Call 'user32::SetWindowPos(p $HWNDPARENT, p 0, i 0, i 0, i r2, i r3, i 6)'
  ; Hide stock wizard chrome; the white page owns the content.
  System::Call 'user32::GetWindow(p $HWNDPARENT, i 5) p.r4'
  ${DoWhile} $4 != 0
    System::Call 'user32::GetDlgCtrlID(p r4) i.r5'
    ${If} $5 != 1
    ${AndIf} $5 != 2
    ${AndIf} $4 != $RacallPage
      ShowWindow $4 ${SW_HIDE}
    ${EndIf}
    System::Call 'user32::GetWindow(p r4, i 2) p.r4'
  ${Loop}
  ; Match the reference's 16-pixel Segoe UI, independently of dialog-font rounding.
  IntOp $0 16 * $RacallDpi
  IntOp $0 $0 + 48
  IntOp $0 $0 / 96
  IntOp $0 0 - $0
  System::Call 'gdi32::CreateFontW(i r0, i 0, i 0, i 0, i 400, i 0, i 0, i 0, i 1, i 0, i 0, i 5, i 0, w "Segoe UI") p.s'
  Pop $RacallBodyFont
  System::Call 'gdi32::CreateFontW(i r0, i 0, i 0, i 0, i 700, i 0, i 0, i 0, i 1, i 0, i 0, i 5, i 0, w "Segoe UI") p.s'
  Pop $RacallTitleFont
  SendMessage $RacallTitle ${WM_SETFONT} $RacallTitleFont 1
  SendMessage $RacallIntro ${WM_SETFONT} $RacallBodyFont 1
  SendMessage $RacallContinue ${WM_SETFONT} $RacallBodyFont 1
  SendMessage $RacallLabel ${WM_SETFONT} $RacallBodyFont 1
  SendMessage $RacallLanguages ${WM_SETFONT} $RacallBodyFont 1
  SendMessage $RacallNext ${WM_SETFONT} $RacallBodyFont 1
  GetDlgItem $4 $HWNDPARENT 2
  SendMessage $4 ${WM_SETFONT} $RacallBodyFont 1
  !insertmacro RacallPlace $RacallPage 0 0 836 547
  !insertmacro RacallPlace $RacallTitle 32 16 600 24
  !insertmacro RacallPlace $RacallLogo 610 13 221 84
  !insertmacro RacallPlace $RacallIntro 54 62 724 22
  !insertmacro RacallPlace $RacallContinue 54 106 724 22
  !insertmacro RacallPlace $RacallLabel 54 150 85 22
  !insertmacro RacallPlace $RacallLanguages 144 145 180 100
  !insertmacro RacallPlace $RacallDivider 0 546 836 1
  !insertmacro RacallPlace $RacallNext 596 565 103 30
  GetDlgItem $4 $HWNDPARENT 2
  !insertmacro RacallPlace $4 715 565 103 30
!macroend
