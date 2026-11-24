import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ProgressBar {
    Layout.fillWidth: true
    indeterminate: visible
    Accessible.name: qsTr("Working")
}
