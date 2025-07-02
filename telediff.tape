Output telediff.gif

Require echo

Set Shell "bash"
Set FontSize 28
Set Width 1200
Set Height 600
Set Theme "iTerm2 Dark Background"

Type "echo foo > yourfile.txt" Sleep 500ms Enter Sleep 500ms Enter Sleep 2000ms

Type "telediff notify --channel telegram --file yourfile.txt" Sleep 500ms Enter Sleep 3000ms Enter Sleep 3000ms

Type "telediff notify -c telegram -f yourfile.txt" Sleep 500ms Enter Sleep 3000ms Enter Sleep 3000ms

Type "echo bar | telediff notify -c telegram -f yourfile.txt" Sleep 500ms Enter Sleep 3000ms Enter Sleep 3000ms

Sleep 5s
