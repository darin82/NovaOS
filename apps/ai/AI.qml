import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import ".." as Nova

ApplicationWindow {
    id: ai
    visible: true
    width: 910
    height: 670
    minimumWidth: 610
    minimumHeight: 460
    title: "Nova AI"

    property bool sidebar: true
    property var chats: []
    property var messages: []
    property var models: []
    property var actions: []
    property var approval: null
    property string chat: ""
    property string job: ""
    property string partial: ""
    property string usage: ""
    property string errorText: ""
    property string attachment: ""
    property bool regenerate: false
    property var pendingSend: null
    readonly property bool generating: job !== ""

    function config() {
        return { provider: provider.currentValue || "ollama", endpoint: endpointField.text,
                 model: modelField.text, retention: retention.value }
    }

    function newChat() {
        chat = ""
        messages = []
        partial = ""
        usage = ""
        attachment = ""
    }

    function confirmSend(retry) {
        if (generating || backend.busy || (!retry && !prompt.text.trim()))
            return
        regenerate = retry
        const current = config()
        const mayBeCloud = current.provider !== "ollama" &&
            !(current.provider === "compatible" &&
              /^(https?:\/\/)(127\.0\.0\.1|localhost|\[::1\])(:\d+)?(\/|$)/i.test(current.endpoint))
        pendingSend = Object.assign(current, { chat: chat, text: prompt.text, regenerate: retry, attachment: attachment })
        if (mayBeCloud || attachment) {
            const destination = current.provider === "compatible" ? current.endpoint : provider.currentText
            permission.text = (mayBeCloud ? "Send recent conversation context to " + destination + "?" : "Use this local model?") +
                (attachment ? "\n\nRead and include: " + decodeURIComponent(attachment.split("/").pop()) : "")
            approveSend.open()
        } else {
            submit(false, false)
        }
    }

    function submit(cloud, attach) {
        backend.invoke("generate", Object.assign(pendingSend, {cloud: cloud, attachmentApproved: attach}))
    }

    function safeMarkdown(content) {
        return (content || "").replace(/</g, "&lt;").replace(/!\[/g, "\\![")
    }

    Component.onCompleted: backend.invoke("settings", null)

    Nova.NovaBridge {
        id: backend
        executable: "/usr/lib/novaos/ai/nova-ai.py"
        onCompleted: (action, result) => {
            if (action !== "progress")
                ai.errorText = ""
            switch (action) {
            case "settings":
                provider.currentIndex = Math.max(0, provider.indexOfValue(result.provider))
                endpointField.text = result.endpoint
                modelField.text = result.model
                retention.value = result.retention
                backend.invoke(Qt.application.arguments.includes("--palette") ? "actions" : "chats", "")
                break
            case "chats": ai.chats = result; break
            case "history": ai.messages = result; break
            case "generate":
                ai.chat = result.chat
                ai.job = result.job
                ai.partial = ""
                ai.usage = ""
                prompt.clear()
                ai.attachment = ""
                backend.invoke("history", ai.chat)
                break
            case "progress":
                ai.partial = result.text
                if (result.done) {
                    ai.job = ""
                    ai.errorText = result.error
                    ai.usage = Object.keys(result.usage).length ?
                        Object.entries(result.usage).map(pair => pair.join(": ")).join(" · ") : ""
                    transcriptRefresh.restart()
                }
                break
            case "delete": ai.newChat(); backend.invoke("chats", search.text); break
            case "actions": ai.actions = result; palette.open(); break
            case "preview": ai.approval = result; actionApproval.open(); break
            case "models": ai.models = result; break
            case "hardware":
            case "connect":
            case "apply":
            case "start-local":
            case "stop-local":
                outcome.text = String(result)
                outputDialog.open()
                break
            }
        }
        onFailed: (action, message) => {
            ai.errorText = message
            if (action === "progress")
                ai.job = ""
        }
    }

    Timer {
        interval: 320
        repeat: true
        running: ai.generating
        onTriggered: backend.invoke("progress", ai.job)
    }
    Timer {
        id: transcriptRefresh
        interval: 150
        onTriggered: {
            ai.partial = ""
            backend.invoke("history", ai.chat)
        }
    }
    Shortcut { sequence: "Ctrl+K"; onActivated: backend.invoke("actions", null) }

    header: ToolBar {
        RowLayout {
            anchors.fill: parent
            anchors.margins: 6
            ToolButton { text: "Chats"; checkable: true; checked: ai.sidebar; onClicked: ai.sidebar = checked }
            Button { text: "New"; enabled: !ai.generating && !backend.busy; onClicked: ai.newChat() }
            Button { text: "Actions"; enabled: !backend.busy; onClicked: backend.invoke("actions", null) }
            Button { text: "Providers"; enabled: !ai.generating; onClicked: preferences.open() }
            Button { text: "Performance"; enabled: !backend.busy; onClicked: backend.invoke("performance", null) }
            Item { Layout.fillWidth: true }
            Label { text: provider.currentValue === "ollama" ? "Local · Ollama" :
                        (provider.currentValue === "compatible" ? "Configured compatible endpoint" : "Cloud · " + provider.currentText) }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 10

        ColumnLayout {
            visible: ai.sidebar
            Layout.preferredWidth: 190
            Layout.fillHeight: true
            TextField {
                id: search
                Layout.fillWidth: true
                placeholderText: "Search conversations"
                onAccepted: backend.invoke("chats", text)
            }
            Button { text: "Refresh history"; enabled: !backend.busy; onClicked: backend.invoke("chats", search.text) }
            ListView {
                id: historyList
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: ai.chats
                delegate: ItemDelegate {
                    required property var modelData
                    text: modelData.title
                    width: historyList.width
                    highlighted: modelData.id === ai.chat
                    enabled: !ai.generating && !backend.busy
                    onClicked: {
                        ai.chat = modelData.id
                        ai.partial = ""
                        ai.usage = ""
                        backend.invoke("history", ai.chat)
                    }
                }
            }
            Button { text: "Export"; enabled: ai.chat !== "" && !ai.generating; onClicked: exportDialog.open() }
            Button { text: "Delete"; enabled: ai.chat !== "" && !ai.generating; onClicked: deleteDialog.open() }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Label {
                Layout.fillWidth: true
                visible: text !== ""
                text: ai.errorText
                textFormat: Text.PlainText
                wrapMode: Text.Wrap
            }
            ListView {
                id: transcript
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 10
                model: ai.partial ? ai.messages.concat([{role: "assistant", content: ai.partial}]) : ai.messages
                ScrollBar.vertical: ScrollBar {}
                onCountChanged: positionViewAtEnd()
                delegate: ColumnLayout {
                    required property var modelData
                    width: transcript.width
                    Label { text: modelData.role === "assistant" ? "Nova AI" : "You"; font.bold: true }
                    TextArea {
                        id: messageBody
                        Layout.fillWidth: true
                        readOnly: true
                        selectByMouse: true
                        wrapMode: Text.Wrap
                        textFormat: modelData.role === "assistant" ? TextEdit.MarkdownText : TextEdit.PlainText
                        text: modelData.role === "assistant" ? ai.safeMarkdown(modelData.content) : modelData.content
                    }
                    ToolButton {
                        text: "Copy"
                        onClicked: { messageBody.selectAll(); messageBody.copy(); messageBody.deselect() }
                    }
                }
            }
            Label { visible: text !== ""; text: ai.usage; textFormat: Text.PlainText }
            Label { visible: ai.attachment !== ""; text: ai.attachment; textFormat: Text.PlainText; Layout.fillWidth: true; elide: Text.ElideMiddle }
            ScrollView {
                Layout.fillWidth: true
                Layout.preferredHeight: 95
                TextArea {
                    id: prompt
                    placeholderText: "Ask a question, explain code or draft a command"
                    textFormat: Text.PlainText
                    wrapMode: Text.Wrap
                }
            }
            RowLayout {
                Button { text: "Attach text"; enabled: !ai.generating; onClicked: attachmentDialog.open() }
                Button { text: "Clear attachment"; visible: ai.attachment !== ""; onClicked: ai.attachment = "" }
                Button { text: "Send"; enabled: !ai.generating && !backend.busy; onClicked: ai.confirmSend(false) }
                Button { text: "Stop"; visible: ai.generating; enabled: !backend.busy; onClicked: backend.invoke("cancel", ai.job) }
                Button { text: "Regenerate"; enabled: ai.chat !== "" && !ai.generating && !backend.busy; onClicked: ai.confirmSend(true) }
            }
        }
    }

    FileDialog { id: attachmentDialog; title: "Select a UTF-8 text attachment"; onAccepted: ai.attachment = selectedFile.toString() }
    FileDialog {
        id: exportDialog
        title: "Export conversation"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "md"
        onAccepted: backend.invoke("export", { chat: ai.chat, url: selectedFile.toString() })
    }
    Dialog {
        id: approveSend
        title: "Confirm context sharing"
        modal: true
        anchors.centerIn: parent
        standardButtons: Dialog.Ok | Dialog.Cancel
        Label { id: permission; width: 380; wrapMode: Text.Wrap; textFormat: Text.PlainText }
        onAccepted: ai.submit(true, !!ai.pendingSend.attachment)
    }
    Dialog {
        id: deleteDialog
        title: "Delete this saved conversation?"
        anchors.centerIn: parent
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: backend.invoke("delete", ai.chat)
    }
    Dialog {
        id: palette
        title: "Nova command palette"
        anchors.centerIn: parent
        standardButtons: Dialog.Close
        ColumnLayout {
            ComboBox { id: actionBox; model: ai.actions; textRole: "title"; valueRole: "id"; Layout.fillWidth: true }
            TextField {
                id: actionArgument
                Layout.fillWidth: true
                placeholderText: actionBox.currentIndex >= 0 ? ai.actions[actionBox.currentIndex].hint : ""
            }
            Button {
                text: "Preview"
                enabled: actionBox.currentIndex >= 0 && !backend.busy
                onClicked: { backend.invoke("preview", { id: actionBox.currentValue, argument: actionArgument.text }); palette.close() }
            }
        }
    }
    Dialog {
        id: actionApproval
        title: "Confirm system action"
        anchors.centerIn: parent
        standardButtons: Dialog.Ok | Dialog.Cancel
        Label { text: ai.approval ? ai.approval.text : ""; textFormat: Text.PlainText; wrapMode: Text.Wrap; width: 380 }
        onAccepted: backend.invoke("apply", ai.approval.token)
    }
    Dialog {
        id: outputDialog
        title: "Nova AI result"
        width: Math.min(ai.width - 24, 575)
        anchors.centerIn: parent
        standardButtons: Dialog.Close
        ScrollView {
            height: 220
            TextArea { id: outcome; readOnly: true; textFormat: Text.PlainText; wrapMode: Text.Wrap }
        }
    }

    Dialog {
        id: preferences
        title: "Providers and retention"
        anchors.centerIn: parent
        width: Math.min(ai.width - 24, 535)
        standardButtons: Dialog.Close
        ColumnLayout {
            ComboBox {
                id: provider
                Layout.fillWidth: true
                textRole: "label"
                valueRole: "id"
                model: [{label: "Ollama (local)", id: "ollama"}, {label: "OpenAI-compatible", id: "compatible"},
                        {label: "OpenAI", id: "openai"}, {label: "Anthropic", id: "anthropic"}, {label: "Gemini", id: "gemini"}]
            }
            TextField { id: endpointField; Layout.fillWidth: true; visible: ["compatible", "ollama"].includes(provider.currentValue); placeholderText: "Custom endpoint (optional for Ollama)" }
            TextField { id: modelField; Layout.fillWidth: true; placeholderText: "Model ID" }
            RowLayout {
                Label { text: "Retention days (0 keeps history)" }
                SpinBox { id: retention; from: 0; to: 365; value: 30; editable: true }
            }
            Flow {
                Layout.fillWidth: true
                spacing: 4
                Button { text: "Save"; enabled: !backend.busy; onClicked: backend.invoke("save-settings", ai.config()) }
                Button { text: "Test connection"; enabled: !backend.busy; onClicked: backend.invoke("connect", ai.config()) }
                Button { text: "Set API key"; visible: provider.currentValue !== "ollama"; enabled: !backend.busy; onClicked: backend.invoke("key", ai.config()) }
                Button { text: "Clear key"; visible: provider.currentValue !== "ollama"; enabled: !backend.busy; onClicked: backend.invoke("clear-key", ai.config()) }
            }
            Flow {
                visible: provider.currentValue === "ollama"
                Layout.fillWidth: true
                spacing: 4
                Button { text: "Start local server"; enabled: !backend.busy; onClicked: backend.invoke("start-local", null) }
                Button { text: "Stop local server"; enabled: !backend.busy; onClicked: backend.invoke("stop-local", null) }
                Button { text: "Hardware suggestions"; enabled: !backend.busy; onClicked: backend.invoke("hardware", null) }
                Button { text: "Install Ollama…"; enabled: !backend.busy; onClicked: backend.invoke("install-ollama-console", null) }
                Button { text: "List local models"; enabled: !backend.busy; onClicked: backend.invoke("models", ai.config()) }
            }
            ComboBox {
                visible: provider.currentValue === "ollama" && ai.models.length > 0
                Layout.fillWidth: true
                model: ai.models.map(model => model.name + " · " + (model.size / 1073741824).toFixed(2) + " GiB")
                onActivated: modelField.text = ai.models[currentIndex].name
            }
            RowLayout {
                visible: provider.currentValue === "ollama"
                Button { text: "Download model…"; enabled: !backend.busy && modelField.text !== ""; onClicked: downloadConfirm.open() }
                Button { text: "Remove model…"; enabled: !backend.busy && modelField.text !== ""; onClicked: removeConfirm.open() }
            }
        }
    }
    Dialog {
        id: downloadConfirm
        title: "Download the selected model?"
        anchors.centerIn: parent
        standardButtons: Dialog.Ok | Dialog.Cancel
        Label { text: "Model downloads may use gigabytes of data and storage."; wrapMode: Text.Wrap }
        onAccepted: backend.invoke("pull", ai.config())
    }
    Dialog {
        id: removeConfirm
        title: "Remove the selected local model?"
        anchors.centerIn: parent
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: backend.invoke("remove-model", Object.assign(ai.config(), {confirmed: true}))
    }
}
