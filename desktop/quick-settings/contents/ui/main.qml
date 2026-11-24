import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.plasma5support as PlasmaSupport
import org.kde.plasma.components as Controls

PlasmoidItem {
    id: root

    property bool blurEnabled: false
    property bool transparencyEnabled: true
    property bool animationsEnabled: true
    property bool ready: false
    property bool busy: false
    property string errorText: ""

    preferredRepresentation: compactRepresentation
    toolTipMainText: "Nova Quick Settings"
    hideOnWindowDeactivate: true

    function request(action) {
        if (busy) {
            return
        }
        busy = true
        errorText = ""
        commands.connectSource("/usr/bin/nova-appearance " + action)
    }

    onExpandedChanged: {
        if (expanded) {
            request("status")
        }
    }

    PlasmaSupport.DataSource {
        id: commands
        engine: "executable"
        interval: 0

        onNewData: (source, data) => {
            if (data["exit code"] === undefined) {
                return
            }
            disconnectSource(source)
            root.busy = false
            if (Number(data["exit code"]) !== 0) {
                root.errorText = String(data["stderr"] || "").trim() || "Could not apply the setting."
                return
            }

            const flags = String(data["stdout"] || "").trim().split(" ")
            if (flags.length === 3) {
                root.blurEnabled = flags[0] === "true"
                root.transparencyEnabled = flags[1] === "true"
                root.animationsEnabled = flags[2] === "true"
                root.ready = true
            }
        }
    }

    compactRepresentation: Controls.ToolButton {
        icon.name: "nova-quick-settings"
        Accessible.name: "Nova Quick Settings"
        checkable: true
        checked: root.expanded
        onClicked: root.expanded = !root.expanded
    }

    fullRepresentation: ColumnLayout {
        Layout.minimumWidth: 290
        Layout.minimumHeight: implicitHeight
        spacing: 6

        GridLayout {
            Layout.fillWidth: true
            columns: 2

            Controls.Button {
                text: "Mute / unmute"
                Layout.fillWidth: true
                enabled: !root.busy
                onClicked: root.request("mute")
            }
            Controls.Button {
                text: "Toggle Wi-Fi"
                Layout.fillWidth: true
                enabled: !root.busy
                onClicked: root.request("wifi")
            }
        }

        Controls.CheckBox {
            text: "Blur"
            checked: root.blurEnabled
            enabled: root.ready && !root.busy
            onClicked: root.request(checked ? "blur on" : "blur off")
        }
        Controls.CheckBox {
            text: "Panel transparency"
            checked: root.transparencyEnabled
            enabled: root.ready && !root.busy
            onClicked: root.request(checked ? "transparency on" : "transparency off")
        }
        Controls.CheckBox {
            text: "Animations"
            checked: root.animationsEnabled
            enabled: root.ready && !root.busy
            onClicked: root.request(checked ? "animations on" : "animations off")
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 2

            Controls.Button {
                text: "Dark"
                Layout.fillWidth: true
                enabled: !root.busy
                onClicked: root.request("dark")
            }
            Controls.Button {
                text: "Light"
                Layout.fillWidth: true
                enabled: !root.busy
                onClicked: root.request("light")
            }
            Controls.Button {
                text: "Ultra Lite"
                Layout.fillWidth: true
                enabled: !root.busy
                onClicked: root.request("ultra-lite")
            }
            Controls.Button {
                text: "Settings"
                Layout.fillWidth: true
                enabled: !root.busy
                onClicked: root.request("settings")
            }
        }
        Controls.Label {
            Layout.fillWidth: true
            visible: root.errorText !== ""
            text: root.errorText
            wrapMode: Text.WordWrap
        }
    }
}
