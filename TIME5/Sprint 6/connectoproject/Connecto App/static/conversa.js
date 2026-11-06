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

    const SLOW_STATUS_MS = 4500;
    const VERY_SLOW_STATUS_MS = 8000;
    const REQUEST_TIMEOUT_MS = 12000;

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
        hideTyping();

        const row = document.createElement("div");
        row.id = "typing-indicator";
        row.className = "message-row message-row--company";
        row.innerHTML = `
            <div class="assistant-message-wrap">
                <span class="message-author">Connecto IA</span>
                <div class="message-bubble message-bubble--company typing-bubble" aria-live="polite" aria-label="Connecto IA estÃ¡ processando a resposta">
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                    <span class="typing-label">digitando...</span>
                </div>
            </div>
        `;

        messagesList.appendChild(row);
        scrollToBottom();
        return row;
    }

    function updateTypingStatus(text, state = "normal") {
        const indicator = document.getElementById("typing-indicator");
        if (!indicator) {
            return;
        }

        const bubble = indicator.querySelector(".typing-bubble");
        const label = indicator.querySelector(".typing-label");

        if (label) {
            label.textContent = text;
        }

        if (bubble) {
            bubble.classList.toggle("typing-bubble--slow", state === "slow");
            bubble.classList.toggle("typing-bubble--very-slow", state === "very-slow");
        }

        scrollToBottom();
    }

    function hideTyping() {
        document.getElementById("typing-indicator")?.remove();
    }

    function showError(message) {
        if (!errorBox) {
            return;
        }

        errorBox.textContent = message;
        errorBox.hidden = false;
        scrollToBottom();
    }

    function clearError() {
        if (!errorBox) {
            return;
        }

        errorBox.hidden = true;
        errorBox.textContent = "";
    }

    function createRetryMessage(question, message) {
        const row = document.createElement("div");
        row.className = "message-row message-row--company assistant-retry-row";

        const wrap = document.createElement("div");
        wrap.className = "assistant-message-wrap";

        const label = document.createElement("span");
        label.className = "message-author";
        label.textContent = "Connecto IA";

        const bubble = document.createElement("div");
        bubble.className = "assistant-error-bubble";

        const text = document.createElement("span");
        text.className = "assistant-error-text";
        text.textContent = message;

        const retryButton = document.createElement("button");
        retryButton.type = "button";
        retryButton.className = "assistant-retry-button";
        retryButton.textContent = "Tentar novamente";

        retryButton.addEventListener("click", async () => {
            if (sending) {
                return;
            }

            row.remove();
            await sendQuestion(question, { appendUserMessage: false });
        });

        bubble.append(text, retryButton);
        wrap.append(label, bubble);
        row.appendChild(wrap);
        messagesList.appendChild(row);
        scrollToBottom();
    }

    async function requestAssistant(text) {
        const controller = new AbortController();
        const startedAt = performance.now();

        const slowTimer = window.setTimeout(() => {
            updateTypingStatus("analisando os dados da vaga...", "slow");
        }, SLOW_STATUS_MS);

        const verySlowTimer = window.setTimeout(() => {
            updateTypingStatus("estÃ¡ levando um pouco mais que o normal...", "very-slow");
        }, VERY_SLOW_STATUS_MS);

        const timeoutTimer = window.setTimeout(() => {
            controller.abort();
        }, REQUEST_TIMEOUT_MS);

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
                signal: controller.signal,
            });

            let data = {};
            try {
                data = await response.json();
            } catch (_) {
                data = {};
            }

            if (!response.ok || !data.ok) {
                throw new Error(data.erro || "NÃ£o foi possÃ­vel consultar o assistente agora.");
            }

            const elapsedMs = Math.round(performance.now() - startedAt);
            console.info(`[Connecto IA] Resposta recebida em ${elapsedMs} ms.`);

            return data.resposta;
        } finally {
            window.clearTimeout(slowTimer);
            window.clearTimeout(verySlowTimer);
            window.clearTimeout(timeoutTimer);
        }
    }

    async function sendQuestion(text, { appendUserMessage = true } = {}) {
        if (!text || sending) {
            return;
        }

        clearError();
        sending = true;
        input.disabled = true;
        submit.disabled = true;

        if (appendUserMessage) {
            createMessage("candidato", text);
        }

        showTyping();

        try {
            const answer = await requestAssistant(text);
            hideTyping();
            createMessage("assistente", answer);
        } catch (error) {
            hideTyping();

            if (error?.name === "AbortError") {
                createRetryMessage(
                    text,
                    "A resposta estÃ¡ demorando mais que o normal. VocÃª pode tentar novamente."
                );
            } else {
                console.error("[Connecto IA] Falha ao consultar o assistente:", error);
                createRetryMessage(
                    text,
                    "NÃ£o consegui responder agora. Tente novamente em alguns instantes."
                );
            }
        } finally {
            sending = false;
            input.disabled = false;
            submit.disabled = false;
            input.focus();
        }
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const text = input.value.trim();
        if (!text || sending) {
            return;
        }

        input.value = "";
        await sendQuestion(text);
    });

    scrollToBottom("auto");
})();