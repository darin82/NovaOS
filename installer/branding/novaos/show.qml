import QtQuick 2.15
import calamares.slideshow 1.0

Presentation {
    Slide {
        Rectangle {
            anchors.fill: parent
            color: "#08080C"
            Image {
                anchors.fill: parent
                source: "wallpaper.svg"
                fillMode: Image.PreserveAspectCrop
                opacity: 0.75
            }
            Text {
                anchors.centerIn: parent
                color: "#F5F5FA"
                text: qsTr("Installing NovaOS")
                font.pixelSize: 24
            }
        }
    }
}
