import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import Qt.labs.platform as Platform

ApplicationWindow {
    id: music
    visible: true
    title: "Nova Music"
    width: 880
    height: 630
    minimumWidth: 420
    minimumHeight: mini ? 145 : 410

    property string mode: "Home"
    property bool sidebar: true
    property bool mini: false
    property int page: 0
    property var collection: ({ rows: [], lists: [], radio: [], more: false })
    property var selected: null
    property var player: ({ path: "", queue: [] })
    property var media: ({ art: "", lyrics: "" })
    property string message: ""
    property string lastPlayed: ""
    property int playlistId: 0
    NovaStyle { id: tokens }
    palette.highlight: tokens.accent

    function browse(reset) {
        if (reset)
            page = 0
        bridge.invoke("browse", { mode: mode, query: search.text, page: page, playlist: playlistId })
    }

    Component.onCompleted: browse(true)

    NovaBridge {
        id: bridge
        executable: "/usr/lib/novaos/nova-music.py"
        onCompleted: (action, result) => {
            if (action !== "status")
                music.message = ""
            if (action === "browse") {
                music.collection = result
                const index = playlists.indexOfValue(music.playlistId)
                if (index >= 0)
                    playlists.currentIndex = index
            } else if (action === "details") {
                music.media = result
                trackDetails.open()
            } else if (action === "playlist-export") {
                music.message = "Playlist exported."
            } else if (["import", "playlist", "playlist-import", "playlist-add", "playlist-remove", "like"].includes(action)) {
                if (action === "playlist" || action === "playlist-import")
                    music.playlistId = result
                music.browse(true)
            } else if (result && result.queue !== undefined) {
                music.player = result
                if (result.path && result.path !== music.lastPlayed) {
                    music.lastPlayed = result.path
                    bridge.invoke("played", result.path)
                }
                if (!result.path) {
                    music.lastPlayed = ""
                    if (!music.visible)
                        music.show()
                }
            }
        }
        onFailed: (action, message) => music.message = message
    }

    Timer {
        interval: music.player.pause ? 3200 : 1300
        repeat: true
        running: !!music.player.path
        onTriggered: bridge.invoke("status", null)
    }

    Platform.SystemTrayIcon {
        id: tray
        visible: available && !!music.player.path
        icon.name: "audio-x-generic-symbolic"
        tooltip: music.player.title || "Nova Music"
        onActivated: { music.show(); music.raise(); music.requestActivate() }
        menu: Platform.Menu {
            Platform.MenuItem { text: "Show Nova Music"; onTriggered: { music.show(); music.raise() } }
            Platform.MenuItem { text: "Play / Pause"; onTriggered: bridge.invoke("pause", null) }
            Platform.MenuItem { text: "Next"; onTriggered: bridge.invoke("next", null) }
            Platform.MenuItem { text: "Quit"; onTriggered: Qt.quit() }
        }
    }

    header: ToolBar {
        visible: !music.mini
        RowLayout {
            anchors.fill: parent
            anchors.margins: tokens.compact
            ToolButton { text: "Library"; checkable: true; checked: music.sidebar; onClicked: music.sidebar = checked }
            TextField { id: search; Layout.fillWidth: true; placeholderText: "Songs, albums or artists"; onAccepted: music.browse(true) }
            Button { text: "Search"; enabled: !bridge.busy; onClicked: music.browse(true) }
            Button { text: "Import"; enabled: !bridge.busy; onClicked: files.open() }
            Button { text: "Folder"; enabled: !bridge.busy; onClicked: folder.open() }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: tokens.gutter
        spacing: 6
        NovaNotice { text: music.message }
        RowLayout {
            visible: !music.mini
            Layout.fillWidth: true
            Layout.fillHeight: true
            ColumnLayout {
                visible: music.sidebar
                Layout.preferredWidth: 150
                Layout.alignment: Qt.AlignTop
                Repeater {
                    model: ["Home", "Library", "Liked", "Recent", "Playlist", "Radio", "Queue"]
                    delegate: Button {
                        required property string modelData
                        text: modelData
                        checkable: true
                        checked: music.mode === modelData
                        Layout.fillWidth: true
                        enabled: !bridge.busy
                        onClicked: {
                            music.mode = modelData
                            if (modelData !== "Radio" && modelData !== "Queue")
                                music.browse(true)
                        }
                    }
                }
                ComboBox {
                    id: playlists
                    Layout.fillWidth: true
                    visible: music.mode === "Playlist"
                    textRole: "name"
                    valueRole: "id"
                    model: music.collection.lists
                    onActivated: { music.playlistId = currentValue; music.browse(true) }
                }
                Button { text: "New playlist"; onClicked: playlistDialog.open() }
                Button { text: "Import M3U"; onClicked: importPlaylist.open() }
                Button { text: "Export M3U"; enabled: music.playlistId > 0; onClicked: exportPlaylist.open() }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Label { text: music.mode; font.bold: true }
                NovaLoading { visible: bridge.busy && bridge.pending !== "status" }
                ListView {
                    id: tracks
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: 3
                    model: music.mode === "Radio" ? music.collection.radio
                         : music.mode === "Queue" ? music.player.queue : music.collection.rows
                    ScrollBar.vertical: ScrollBar {}
                    delegate: NovaCard {
                        required property var modelData
                        required property int index
                        width: tracks.width
                        enabled: !bridge.busy
                        text: music.mode === "Radio" ? modelData
                            : music.mode === "Queue" ? (modelData.title || modelData.filename.split("/").pop())
                            : (modelData.liked ? "♥ " : "") + [modelData.title, modelData.artist, modelData.album].filter(Boolean).join("  ·  ")
                        highlighted: music.selected && music.selected.id !== undefined && modelData.id === music.selected.id
                        onClicked: {
                            if (music.mode === "Radio")
                                bridge.invoke("radio", modelData)
                            else if (music.mode === "Queue") {
                                tracks.currentIndex = index
                                bridge.invoke("select-queue", index)
                            } else
                                music.selected = modelData
                        }
                    }
                    Label { anchors.centerIn: parent; text: "No tracks to show"; visible: tracks.count === 0 }
                }
                RowLayout {
                    visible: music.mode !== "Radio" && music.mode !== "Queue"
                    enabled: !bridge.busy
                    Button { text: "Play"; enabled: !!music.selected; onClicked: bridge.invoke("play", music.selected.id) }
                    Button { text: "Queue"; enabled: !!music.selected; onClicked: bridge.invoke("queue", music.selected.id) }
                    Button { text: "Like / unlike"; enabled: !!music.selected; onClicked: bridge.invoke("like", music.selected.id) }
                    Button { text: "Artwork & lyrics"; enabled: !!music.selected; onClicked: bridge.invoke("details", music.selected.id) }
                    Button { text: "Playlist…"; enabled: !!music.selected && music.collection.lists.length > 0; onClicked: addToPlaylist.open() }
                    Button {
                        text: "Remove from playlist"
                        visible: music.mode === "Playlist"
                        enabled: !!music.selected && music.playlistId > 0
                        onClicked: bridge.invoke("playlist-remove", { list: music.playlistId, track: music.selected.id })
                    }
                }
                RowLayout {
                    visible: !["Radio", "Queue"].includes(music.mode)
                    Button { text: "Previous page"; enabled: music.page > 0 && !bridge.busy; onClicked: { music.page--; music.browse(false) } }
                    Button { text: "Next page"; enabled: music.collection.more && !bridge.busy; onClicked: { music.page++; music.browse(false) } }
                }
                RowLayout {
                    visible: music.mode === "Radio"
                    Button { text: "Open stream URL"; onClicked: streamDialog.open() }
                    Button { text: "SomaFM"; onClicked: Qt.openUrlExternally("https://somafm.com/listen/") }
                    Button { text: "Free Music Archive"; onClicked: Qt.openUrlExternally("https://freemusicarchive.org/") }
                }
                Button {
                    visible: music.mode === "Queue"
                    text: "Remove selected from queue"
                    enabled: tracks.currentIndex >= 0 && !bridge.busy
                    onClicked: bridge.invoke("remove-queue", tracks.currentIndex)
                }
            }
        }
        Label {
            Layout.fillWidth: true
            elide: Text.ElideRight
            textFormat: Text.PlainText
            text: music.player.title || "Nothing playing"
        }
        Slider {
            Layout.fillWidth: true
            enabled: !!music.player.duration && !bridge.busy
            from: 0
            to: music.player.duration || 1
            value: music.player["time-pos"] || 0
            onPressedChanged: { if (!pressed) bridge.invoke("seek", value) }
        }
        Flow {
            Layout.fillWidth: true
            spacing: 5
            Button { text: "Previous"; enabled: !!music.player.path && !bridge.busy; onClicked: bridge.invoke("previous", null) }
            Button { text: music.player.pause ? "Resume" : "Pause"; enabled: !!music.player.path && !bridge.busy; onClicked: bridge.invoke("pause", null) }
            Button { text: "Next"; enabled: !!music.player.path && !bridge.busy; onClicked: bridge.invoke("next", null) }
            Button { text: "Stop"; enabled: !!music.player.path && !bridge.busy; onClicked: bridge.invoke("stop", null) }
            Button { text: "Shuffle"; enabled: !!music.player.path && !bridge.busy; onClicked: bridge.invoke("shuffle", null) }
            Button {
                text: music.player["loop-playlist"] === "inf" ? "Repeat on" : "Repeat off"
                enabled: !!music.player.path && !bridge.busy
                onClicked: bridge.invoke("repeat", null)
            }
            Button { text: "EQ"; enabled: !!music.player.path && !bridge.busy; onClicked: equalizer.open() }
            Button { text: "Volume"; enabled: !!music.player.path && !bridge.busy; onClicked: volume.open() }
            Button {
                text: music.mini ? "Full player" : "Mini"
                onClicked: {
                    music.mini = !music.mini
                    music.width = music.mini ? 540 : 880
                    music.height = music.mini ? 145 : 630
                }
            }
            Button { text: "Hide to tray"; visible: tray.available && !!music.player.path; onClicked: music.hide() }
        }
    }

    FileDialog {
        id: files
        title: "Import music files"
        fileMode: FileDialog.OpenFiles
        onAccepted: bridge.invoke("import", selectedFiles.map(url => url.toString()))
    }
    FolderDialog {
        id: folder
        title: "Import music folder"
        onAccepted: bridge.invoke("import", [selectedFolder.toString()])
    }
    FileDialog {
        id: importPlaylist
        title: "Import a local M3U playlist"
        nameFilters: ["M3U playlists (*.m3u *.m3u8)"]
        onAccepted: {
            const url = selectedFile.toString()
            bridge.invoke("playlist-import", { file: url, name: decodeURIComponent(url.split("/").pop()) })
        }
    }
    FileDialog {
        id: exportPlaylist
        title: "Export M3U playlist"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "m3u8"
        onAccepted: bridge.invoke("playlist-export", { file: selectedFile.toString(), id: music.playlistId })
    }
    Dialog {
        id: playlistDialog
        title: "New playlist"
        anchors.centerIn: parent
        standardButtons: Dialog.Ok | Dialog.Cancel
        TextField { id: playlistName; placeholderText: "Playlist name" }
        onAccepted: bridge.invoke("playlist", playlistName.text)
    }
    Dialog {
        id: addToPlaylist
        title: "Add to playlist"
        anchors.centerIn: parent
        standardButtons: Dialog.Ok | Dialog.Cancel
        ComboBox { id: targetPlaylist; textRole: "name"; valueRole: "id"; model: music.collection.lists }
        onAccepted: bridge.invoke("playlist-add", { list: targetPlaylist.currentValue, track: music.selected.id })
    }
    Dialog {
        id: streamDialog
        title: "Authorized HTTPS audio stream"
        anchors.centerIn: parent
        standardButtons: Dialog.Ok | Dialog.Cancel
        TextField { id: stream; placeholderText: "https://"; width: 280 }
        onAccepted: bridge.invoke("stream", stream.text)
    }
    Dialog {
        id: trackDetails
        title: "Artwork and local lyrics"
        width: Math.min(music.width - 28, 480)
        anchors.centerIn: parent
        standardButtons: Dialog.Close
        ColumnLayout {
            Image {
                source: music.media.art
                visible: source.toString() !== ""
                Layout.preferredHeight: visible ? 145 : 0
                Layout.fillWidth: true
                asynchronous: true
                fillMode: Image.PreserveAspectFit
            }
            ScrollView {
                Layout.fillWidth: true
                Layout.preferredHeight: 180
                TextArea {
                    text: music.media.lyrics || "No .lrc or .lyrics.txt sidecar was found."
                    readOnly: true
                    textFormat: Text.PlainText
                    wrapMode: Text.Wrap
                }
            }
        }
    }
    Dialog {
        id: equalizer
        title: "Equalizer"
        anchors.centerIn: parent
        standardButtons: Dialog.Apply | Dialog.Close
        onApplied: bridge.invoke("eq", [bass.value, mid.value, treble.value])
        ColumnLayout {
            Label { text: "Bass" }
            Slider { id: bass; from: -12; to: 12; stepSize: 1; Accessible.name: "Bass gain" }
            Label { text: "Midrange" }
            Slider { id: mid; from: -12; to: 12; stepSize: 1; Accessible.name: "Midrange gain" }
            Label { text: "Treble" }
            Slider { id: treble; from: -12; to: 12; stepSize: 1; Accessible.name: "Treble gain" }
        }
    }
    Dialog {
        id: volume
        title: "Volume"
        anchors.centerIn: parent
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAboutToShow: gain.value = music.player.volume ?? 100
        onAccepted: bridge.invoke("volume", gain.value)
        Slider { id: gain; from: 0; to: 100; stepSize: 1; Accessible.name: "Playback volume" }
    }
}
