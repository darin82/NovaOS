import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Label {
    Layout.fillWidth: true
    textFormat: Text.PlainText
    wrapMode: Text.WrapAnywhere
    visible: text !== ""
}
