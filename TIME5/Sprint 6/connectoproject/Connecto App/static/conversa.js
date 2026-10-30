(() => {
    const form = document.getElementById("chat-form");
    const input = document.getElementById("chat-input");
    const submit = document.getElementById("chat-submit");
    const messagesList = document.getElementById("messages-list");
    const errorBox = document.getElementById("chat-error");

    if (!form || !input || !submit || !messagesList) {
        return;
    }

    const endpoint = form.dataset.endpoint;
    const csrfInput = form.querySelector("input[name='csrfmiddlewaretoken']");
    const csrfToken = csrfInput ? csrfInput.value : "";
    let sending = false;

    function scrollToBottom(behavior = "smooth") {
        window.requestAnimationFrame(() => {
            window.scrollTo({
                top: document.documentElement.scrollHeight,
                behavior,
            });
        });
    }

    function createMessage(author, text) {
        const row = document.createElement("div");
        row.className = `message-row message-row--${author === "candidato" ? "user" : "company"}`;

        if (author === "candidato") {
            const bubble = document.createElement("div");
            bubble.className = "message-bubble message-bubble--user";
            bubble.textContent = text;
            row.appendChild(bubble);
        } else {
            const wrap = document.createElement("div");
            wrap.className = "assistant-message-wrap";

            const label = document.createElement("span");
            label.className = "message-author";
            label.textContent = "Connecto IA";

            const bubble = document.createElement("div");
            bubble.className = "message-bubble message-bubble--company";
            bubble.textContent = text;

            wrap.append(label, bubble);
            row.appendChild(wrap);
        }

        messagesList.appendChild(row);
        scrollToBottom();
        return row;
    }

    function showTyping() {
        const row = document.createElement("div");
        row.id = "typing-indicator";
        row.className = "message-row message-row--company";
        row.innerHTML = `
            <div class="assistant-message-wrap">
                <span class="message-author">Connecto IA</span>
                <div class="message-bubble message-bubble--company typing-bubble" aria-label="digitando">
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                    <span class="typing-label">digitando...</span>
                </div>
            </div>
        `;
        messagesList.appendChild(row);
        scrollToBottom();
    }

    function hideTyping() {
        document.getElementById("typing-indicator")?.remove();
    }

    function showError(message) {
        errorBox.textContent = message;
        errorBox.hidden = false;
        scrollToBottom();
    }

    function clearError() {
        errorBox.hidden = true;
        errorBox.textContent = "";
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const text = input.value.trim();
        if (!text || sending) {
            return;
        }

        clearError();
        sending = true;
        input.disabled = true;
        submit.disabled = true;

        const optimisticMessage = createMessage("candidato", text);
        input.value = "";
        showTyping();

        try {
            const response = await fetch(endpoint, {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken,
                    "X-Requested-With": "XMLHttpRequest",
                },
                body: JSON.stringify({ mensagem: text }),
            });

            let data = {};
            try {
                data = await response.json();
            } catch (_) {
                data = {};
            }

            if (!response.ok || !data.ok) {
                throw new Error(data.erro || "Não foi possível consultar o assistente agora.");
            }

            hideTyping();
            createMessage("assistente", data.resposta);
        } catch (error) {
            hideTyping();
            optimisticMessage.remove();
            input.value = text;
            showError(error.message || "Não foi possível consultar o assistente agora.");
        } finally {
            sending = false;
            input.disabled = false;
            submit.disabled = false;
            input.focus();
        }
    });

    scrollToBottom("auto");
})();
