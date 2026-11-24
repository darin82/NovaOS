import QtQuick
import QtQuick.Controls

ItemDelegate {
    id: card
    hoverEnabled: true
    NovaStyle { id: tokens }
    background: Rectangle {
        radius: tokens.cardRadius
        color: card.highlighted ? card.palette.alternateBase : (card.hovered ? card.palette.base : "transparent")
        border.width: card.visualFocus || card.highlighted ? 1 : 0
        border.color: tokens.accent
    }
}
