; Keep the system wizard controls, with a light Racall-branded surface.
; Header/finish bitmaps are configured through electron-builder in package.json.
!define MUI_BGCOLOR "FFFFFF"
!define MUI_TEXTCOLOR "242424"
!define MUI_INSTFILESPAGE_COLORS "242424 FFFFFF"

!macro customHeader
  BrandingText "Racall"
  SetFont "Segoe UI" 9
!macroend
