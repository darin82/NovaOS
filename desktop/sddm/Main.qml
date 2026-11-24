import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: greeter
    width: 1280
    height: 720
    color: "#08080C"
    property bool authenticating: false
    property string feedback: ""
    property string powerAction: ""

    function signIn() {
        if (authenticating || !username.text.trim() || selection.currentIndex < 0)
            return
        feedback = ""
        authenticating = true
        sddm.login(username.text.trim(), password.text, selection.currentIndex)
    }

    Connections {
        target: sddm
        function onLoginFailed() {
            greeter.authenticating = false
            password.clear()
            greeter.feedback = qsTr("Sign-in failed. Check your credentials.")
            password.forceActiveFocus()
        }
    }

    Image {
        anchors.fill: parent
        source: "wallpaper.svg"
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        opacity: 0.65
    }

    Rectangle {
        anchors.centerIn: parent
        width: Math.min(parent.width - 32, 380)
        height: form.implicitHeight + 40
        radius: 18
        color: "#12121A"
        border.color: "#383044"

        ColumnLayout {
            id: form
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: 20
            spacing: 9

            RowLayout {
                spacing: 12
                Image { source: "novaos.svg"; Layout.preferredWidth: 42; Layout.preferredHeight: 42 }
                Label { text: "NovaOS"; font.pixelSize: 23; font.bold: true; color: "#F5F5FA" }
            }
            TextField {
                id: username
                Layout.fillWidth: true
                Accessible.name: qsTr("Username")
                placeholderText: qsTr("Username")
                text: userModel.lastUser || ""
                enabled: !greeter.authenticating
                onAccepted: password.forceActiveFocus()
            }
            TextField {
                id: password
                Layout.fillWidth: true
                Accessible.name: qsTr("Password")
                placeholderText: qsTr("Password")
                echoMode: TextInput.Password
                inputMethodHints: Qt.ImhHiddenText | Qt.ImhNoPredictiveText
                enabled: !greeter.authenticating
                onAccepted: greeter.signIn()
            }
            ComboBox {
                id: selection
                Layout.fillWidth: true
                Accessible.name: qsTr("Desktop session")
                model: sessionModel
                textRole: "name"
                currentIndex: Math.max(0, sessionModel.lastIndex)
                enabled: !greeter.authenticating
            }
            Label {
                Layout.fillWidth: true
                text: greeter.feedback
                visible: text !== ""
                wrapMode: Text.WordWrap
                color: "#F5F5FA"
                Accessible.name: text
            }
            RowLayout {
                Layout.fillWidth: true
                Button {
                    text: greeter.authenticating ? qsTr("Signing in…") : qsTr("Sign in")
                    enabled: !greeter.authenticating && !!username.text.trim()
                    highlighted: true
                    palette.highlight: "#8B5CF6"
                    onClicked: greeter.signIn()
                }
                Item { Layout.fillWidth: true }
                ToolButton {
                    text: qsTr("Restart")
                    palette.buttonText: "#F5F5FA"
                    visible: sddm.canReboot
                    onClicked: { greeter.powerAction = "reboot"; powerConfirmation.open() }
                }
                ToolButton {
                    text: qsTr("Power off")
                    palette.buttonText: "#F5F5FA"
                    visible: sddm.canPowerOff
                    onClicked: { greeter.powerAction = "poweroff"; powerConfirmation.open() }
                }
            }
        }
    }

    Dialog {
        id: powerConfirmation
        anchors.centerIn: parent
        modal: true
        title: greeter.powerAction === "reboot" ? qsTr("Restart this computer?") : qsTr("Power off this computer?")
        standardButtons: Dialog.Yes | Dialog.No
        onAccepted: {
            if (greeter.powerAction === "reboot" && sddm.canReboot)
                sddm.reboot()
            else if (greeter.powerAction === "poweroff" && sddm.canPowerOff)
                sddm.powerOff()
        }
    }
    Component.onCompleted: (username.text ? password : username).forceActiveFocus()
}
