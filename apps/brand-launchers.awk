# Values are supplied by the packaged launcher map.
function write_identity() {
    print "Name=" name
    print "Icon=" icon
    if (visibility == "hide") print "NoDisplay=true"
    if (managed) print "DBusActivatable=false"
    if (monitor && !actions) print "Actions=StartupApps;"
}

{
    if (/^\[/) {
        if (main) write_identity()
        main = ($0 == "[Desktop Entry]")
    }
    if (main && (/^Name(\[.*\])?=/ || /^Icon=/ ||
        (visibility == "hide" && /^NoDisplay=/) ||
        (managed && /^DBusActivatable=/))) next
    if (main && monitor && /^Actions=/) {
        actions = 1
        sub(/;?$/, ";StartupApps;")
    }
    if (managed && /^Exec=/) sub(/^Exec=/, "Exec=nova-run -- ")
    print
}
END {
    if (main) write_identity()
    if (monitor) {
        print "\n[Desktop Action StartupApps]"
        print "Name=Startup Applications"
        print "Exec=systemsettings kcm_autostart"
    }
}
