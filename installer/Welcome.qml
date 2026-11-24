import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: welcome
    width: 600
    height: 495
    minimumWidth: 450
    visible: true
    title: "Nova Welcome"
    property string feedback: ""
    NovaStyle { id: tokens }
    palette.highlight: tokens.accent

    NovaBridge {
        id: actions
        executable: "/usr/lib/novaos/nova-welcome-action.py"
        onCompleted: (action, result) => welcome.feedback = result
        onFailed: (action, error) => welcome.feedback = error
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: tokens.comfortable
        spacing: 9
        Label { text: "Welcome to NovaOS"; font.pixelSize: 23; font.bold: true }
        Label { text: "Set up what you need. You can skip any step."; wrapMode: Text.Wrap; Layout.fillWidth: true }
        RowLayout {
            Label { text: "Appearance" }
            Button { text: "Dark"; enabled: !actions.busy; onClicked: actions.invoke("dark", null) }
            Button { text: "Light"; enabled: !actions.busy; onClicked: actions.invoke("light", null) }
        }
        RowLayout {
            Label { text: "Taskbar" }
            ComboBox { id: alignment; model: ["left", "center", "right"]; currentIndex: 1 }
            SpinBox { id: size; from: 36; to: 72; value: 48; Accessible.name: "Taskbar size" }
            Button { text: "Apply"; enabled: !actions.busy; onClicked: actions.invoke("panel", { size: size.value, alignment: alignment.currentText }) }
        }
        Repeater {
            model: [
                ["Display scaling", "display"], ["Performance profiles", "performance"],
                ["Optional gaming setup", "gaming"], ["Optional developer tools and Nova AI", "store"],
                ["Check system updates", "updates"]
            ]
            delegate: Button {
                required property var modelData
                text: modelData[0]
                Layout.fillWidth: true
                enabled: !actions.busy
                onClicked: actions.invoke(modelData[1], null)
            }
        }
        Item { Layout.fillHeight: true }
        NovaNotice { text: welcome.feedback }
        Button { text: "Done"; Layout.alignment: Qt.AlignRight; onClicked: welcome.close() }
    }
}
