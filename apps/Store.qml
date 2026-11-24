import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: store
    visible: true
    title: "Nova Store"
    width: 910
    height: 650
    minimumWidth: 620
    minimumHeight: 450

    property var entries: []
    property var selected: null
    property int page: 0
    property bool more: false
    property bool installed: false
    property bool sidebar: true
    property string message: ""
    property bool aiEnabled: false
    NovaStyle { id: tokens }
    palette.highlight: tokens.accent

    function search(reset) {
        if (reset)
            page = 0
        bridge.invoke("browse", { query: query.text, source: source.currentText,
            category: installed ? "All" : category.currentText, installed: installed, page: page })
    }
    function transaction(operation) {
        bridge.invoke("transaction", { operation: operation,
            source: selected ? selected.source : "", id: selected ? selected.id : "" })
    }
    Component.onCompleted: search(true)

    NovaBridge {
        id: bridge
        executable: "/usr/bin/nova-store"
        onCompleted: (action, result) => {
            store.message = ""
            if (action === "browse") {
                store.entries = result.rows
                store.more = result.more
            } else if (action === "details") {
                store.selected = result
            } else if (action === "repos") {
                repos.text = (result.flatpak || "No per-user Flatpak remotes.") + "\n\n" + result.apt
                repositories.open()
            } else if (action === "transaction") {
                store.message = "Review the transaction and its progress in the terminal. Refresh when it finishes."
            } else if (action === "optional-ai") {
                store.aiEnabled = result
                if (!optionalAI.visible)
                    optionalAI.open()
            }
        }
        onFailed: (action, message) => store.message = message
    }

    header: ToolBar {
        RowLayout {
            anchors.fill: parent
            anchors.margins: tokens.compact
            ToolButton { text: "Filters"; checkable: true; checked: store.sidebar; onClicked: store.sidebar = checked }
            TextField {
                id: query
                Layout.fillWidth: true
                placeholderText: "Search the application catalog"
                onAccepted: store.search(true)
            }
            Button { text: "Search"; enabled: !bridge.busy; onClicked: store.search(true) }
            Button { text: "Updates"; enabled: !bridge.busy; onClicked: updates.open() }
            Button { text: "Repositories"; enabled: !bridge.busy; onClicked: bridge.invoke("repos", null) }
            Button { text: "Nova AI"; enabled: !bridge.busy; onClicked: bridge.invoke("optional-ai", "status") }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: tokens.gutter
        spacing: tokens.gutter
        ColumnLayout {
            visible: store.sidebar
            Layout.preferredWidth: 155
            Layout.alignment: Qt.AlignTop
            CheckBox {
                text: "Installed"
                enabled: !bridge.busy
                onToggled: { store.installed = checked; store.search(true) }
            }
            ComboBox {
                id: category
                Layout.fillWidth: true
                enabled: !bridge.busy && !store.installed
                model: ["All", "Gaming", "Development", "Multimedia", "Utilities", "Internet",
                        "Graphics", "Optional productivity"]
                onActivated: store.search(true)
            }
            ComboBox {
                id: source
                Layout.fillWidth: true
                enabled: !bridge.busy
                model: ["All", "apt", "flatpak"]
                onActivated: store.search(true)
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            NovaNotice { text: store.message }
            NovaLoading { visible: bridge.busy }
            ListView {
                id: results
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 4
                model: store.entries
                ScrollBar.vertical: ScrollBar {}
                delegate: NovaCard {
                    required property var modelData
                    width: results.width
                    text: modelData.name + "   ·   " + modelData.source.toUpperCase()
                    enabled: !bridge.busy
                    onClicked: bridge.invoke("details", { source: modelData.source, id: modelData.id })
                }
                Label { anchors.centerIn: parent; text: "No matching applications"; visible: !store.entries.length && !bridge.busy }
            }
            RowLayout {
                Button { text: "Previous"; enabled: store.page > 0 && !bridge.busy; onClicked: { store.page--; store.search(false) } }
                Button { text: "Next"; enabled: store.more && !bridge.busy; onClicked: { store.page++; store.search(false) } }
                Button { text: "Refresh"; enabled: !bridge.busy; onClicked: store.search(false) }
            }
        }

        ScrollView {
            id: detailPane
            Layout.preferredWidth: 265
            Layout.fillHeight: true
            visible: store.selected !== null && store.width > 760
            contentWidth: availableWidth
            ColumnLayout {
                width: detailPane.availableWidth
                Label {
                    text: store.selected ? store.selected.name : ""
                    textFormat: Text.PlainText
                    font.bold: true
                    wrapMode: Text.Wrap
                    Layout.fillWidth: true
                }
                Image {
                    source: visible && store.selected ? store.selected.screenshot : ""
                    visible: store.selected && store.selected.screenshot !== ""
                    asynchronous: true
                    sourceSize.width: 420
                    fillMode: Image.PreserveAspectFit
                    Layout.fillWidth: true
                    Layout.preferredHeight: visible ? 140 : 0
                }
                Label {
                    Layout.fillWidth: true
                    visible: text !== ""
                    text: store.selected ? store.selected.caption : ""
                    textFormat: Text.PlainText
                    wrapMode: Text.Wrap
                    font.pixelSize: 11
                }
                Label {
                    Layout.fillWidth: true
                    text: store.selected ? store.selected.description : ""
                    textFormat: Text.PlainText
                    wrapMode: Text.Wrap
                }
                Label {
                    Layout.fillWidth: true
                    text: store.selected ? (store.selected.size || "Size available at transaction review.") : ""
                    textFormat: Text.PlainText
                    wrapMode: Text.Wrap
                }
                Label {
                    Layout.fillWidth: true
                    text: store.selected ? store.selected.details : ""
                    textFormat: Text.PlainText
                    wrapMode: Text.WrapAnywhere
                }
                Button {
                    visible: store.selected && (!store.selected.installed || store.selected.removable)
                    text: store.selected && store.selected.installed ? "Uninstall…" : "Install…"
                    enabled: !bridge.busy
                    onClicked: store.transaction(store.selected.installed ? "remove" : "install")
                }
                Label { visible: store.selected && store.selected.installed && !store.selected.removable; text: "Installed system package" }
            }
        }
    }

    onSelectedChanged: {
        if (selected && width <= 760)
            compactDetails.open()
    }

    Dialog {
        id: optionalAI
        title: "Optional Nova AI"
        anchors.centerIn: parent
        standardButtons: Dialog.Close
        ColumnLayout {
            Label {
                Layout.preferredWidth: 365
                wrapMode: Text.Wrap
                text: "Enable adds Nova AI to your launcher. Local models and cloud providers require separate setup. Close Nova AI before disabling it."
            }
            RowLayout {
                Button {
                    text: store.aiEnabled ? "Disable" : "Enable"
                    enabled: !bridge.busy
                    onClicked: bridge.invoke("optional-ai", store.aiEnabled ? "disable" : "enable")
                }
                Button {
                    text: "Open"
                    enabled: store.aiEnabled && !bridge.busy
                    onClicked: { bridge.invoke("optional-ai", "open"); optionalAI.close() }
                }
            }
        }
    }

    Dialog {
        id: compactDetails
        title: store.selected ? store.selected.name : ""
        anchors.centerIn: parent
        standardButtons: Dialog.Close
        ColumnLayout {
            Label {
                Layout.preferredWidth: 380
                text: store.selected ? [store.selected.description, store.selected.size || "", store.selected.details].join("\n\n") : ""
                textFormat: Text.PlainText
                wrapMode: Text.WrapAnywhere
            }
            Button {
                visible: store.selected && (!store.selected.installed || store.selected.removable)
                text: store.selected && store.selected.installed ? "Uninstall…" : "Install…"
                enabled: !bridge.busy
                onClicked: { store.transaction(store.selected.installed ? "remove" : "install"); compactDetails.close() }
            }
        }
    }

    Dialog {
        id: repositories
        title: "Trusted repositories"
        anchors.centerIn: parent
        width: Math.min(store.width - 36, 650)
        standardButtons: Dialog.Close
        ColumnLayout {
            RowLayout {
                Button { text: "Add Flathub"; onClicked: { store.transaction("add-repo"); repositories.close() } }
                Button { text: "Enable"; onClicked: { store.transaction("enable-repo"); repositories.close() } }
                Button { text: "Disable"; onClicked: { store.transaction("disable-repo"); repositories.close() } }
            }
            ScrollView {
                Layout.fillWidth: true
                Layout.preferredHeight: 270
                TextArea { id: repos; readOnly: true; textFormat: Text.PlainText; wrapMode: Text.WrapAnywhere }
            }
        }
    }

    Dialog {
        id: updates
        title: "Available updates"
        anchors.centerIn: parent
        standardButtons: Dialog.Close
        RowLayout {
            Button { text: "Review available"; onClicked: { store.transaction("updates"); updates.close() } }
            Button { text: "Apply updates…"; onClicked: { store.transaction("apply-updates"); updates.close() } }
        }
    }
}
