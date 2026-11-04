const INTERVALO_MS =
    10 * 60 * 1000;


function csrf() {
    const cookies =
        document.cookie
            ? document.cookie.split(";")
            : [];

    for (const cookie of cookies) {

        const item = cookie.trim();

        if (
            item.startsWith("csrftoken=")
        ) {
            return decodeURIComponent(
                item.substring(
                    "csrftoken=".length
                )
            );
        }
    }

    return null;
}


function suportaAvisos() {
    return "Notification" in window;
}


function notificacaoPermitida() {
    return (
        suportaAvisos()
        && Notification.permission === "granted"
    );
}


function atualizarBotao() {

    const botao =
        document.getElementById(
            "btn-ativar-avisos"
        );

    if (!botao) {
        return;
    }

    if (!suportaAvisos()) {
        botao.hidden = true;
        return;
    }

    if (
        Notification.permission === "denied"
    ) {
        botao.hidden = true;
        return;
    }

    /*
     * Mesmo se permission === granted,
     * deixamos o botão disponível.
     *
     * Isso permite recriar/revalidar
     * a PushSubscription.
     */
    botao.hidden = false;

    if (
        Notification.permission === "granted"
    ) {
        botao.textContent =
            "Ativar Web Push";
    } else {
        botao.textContent =
            "Ativar avisos no navegador";
    }
}


async function verificar() {

    try {

        const r = await fetch(
            "/notificacoes/verificar/",
            {
                method: "POST",

                credentials: "same-origin",

                headers: {
                    "X-CSRFToken": csrf(),
                },

                body: new URLSearchParams({
                    mostrar:
                        notificacaoPermitida()
                            ? "1"
                            : "0",
                }),
            }
        );

        if (!r.ok || r.redirected) {
            return;
        }

        const dados = await r.json();

        /*
         * Sistema antigo de aviso in-app.
         */
        dados.novas.forEach(n => {

            try {

                const aviso =
                    new Notification(
                        "Connecto",
                        {
                            body: n.texto,
                        }
                    );

                aviso.onclick = () => {
                    window.focus();

                    window.location.href =
                        "/notificacoes/";
                };

            } catch (e) {
                console.log(
                    "Notification direta não suportada:",
                    e
                );
            }
        });

        const badge =
            document.getElementById(
                "sino-badge"
            );

        if (badge) {
            badge.hidden =
                dados.nao_lidas === 0;
        }

    } catch (error) {

        console.error(
            "Erro verificando notificações:",
            error
        );
    }
}


document.addEventListener(
    "DOMContentLoaded",
    async () => {

        const botao =
            document.getElementById(
                "btn-ativar-avisos"
            );

        atualizarBotao();

        if (botao) {

            botao.addEventListener(
                "click",
                async () => {

                    console.log(
                        "[Connecto Push] Botão clicado."
                    );

                    if (
                        typeof window.ativarPush
                        !== "function"
                    ) {

                        console.error(
                            "[Connecto Push] ativarPush() não foi carregada."
                        );

                        return;
                    }

                    const sucesso =
                        await window.ativarPush();

                    if (sucesso) {

                        console.log(
                            "[Connecto Push] Web Push ativado!"
                        );

                        botao.textContent =
                            "Avisos ativados ✓";

                    } else {

                        console.error(
                            "[Connecto Push] Não foi possível ativar."
                        );
                    }

                    atualizarBotao();

                    await verificar();
                }
            );
        }

        /*
         * IMPORTANTE:
         *
         * Se o usuário já havia concedido
         * permissão antes da correção,
         * tentamos criar/salvar a subscription
         * automaticamente.
         */
        if (
            Notification.permission
                === "granted"
            &&
            typeof window.ativarPush
                === "function"
        ) {

            console.log(
                "[Connecto Push] Permissão já concedida. Validando subscription..."
            );

            await window.ativarPush();
        }

        await verificar();

        setInterval(
            verificar,
            INTERVALO_MS
        );
    }
);