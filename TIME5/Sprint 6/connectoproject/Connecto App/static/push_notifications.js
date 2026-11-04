function urlBase64ToUint8Array(base64String) {
    const padding =
        "=".repeat((4 - base64String.length % 4) % 4);

    const base64 = (base64String + padding)
        .replace(/-/g, "+")
        .replace(/_/g, "/");

    const rawData = window.atob(base64);

    return Uint8Array.from(
        [...rawData].map(
            char => char.charCodeAt(0)
        )
    );
}


function getCookie(name) {
    const cookies = document.cookie
        ? document.cookie.split(";")
        : [];

    for (const cookie of cookies) {
        const item = cookie.trim();

        if (item.startsWith(name + "=")) {
            return decodeURIComponent(
                item.substring(name.length + 1)
            );
        }
    }

    return null;
}


async function ativarPush() {

    console.log("[Connecto Push] Iniciando ativação...");

    if (!("Notification" in window)) {
        console.error(
            "[Connecto Push] Notification API não suportada."
        );
        return false;
    }

    if (!("serviceWorker" in navigator)) {
        console.error(
            "[Connecto Push] Service Worker não suportado."
        );
        return false;
    }

    if (!("PushManager" in window)) {
        console.error(
            "[Connecto Push] PushManager não suportado."
        );
        return false;
    }

    const publicKey = (
        window.CONNECTO_VAPID_PUBLIC_KEY || ""
    ).trim();

    console.log(
        "[Connecto Push] VAPID pública presente:",
        Boolean(publicKey)
    );

    if (!publicKey) {
        console.error(
            "[Connecto Push] VAPID_PUBLIC_KEY está vazia."
        );
        return false;
    }

    try {

        let permission = Notification.permission;

        console.log(
            "[Connecto Push] Permissão atual:",
            permission
        );

        if (permission === "default") {

            permission =
                await Notification.requestPermission();

            console.log(
                "[Connecto Push] Nova permissão:",
                permission
            );
        }

        if (permission !== "granted") {
            console.error(
                "[Connecto Push] Permissão não concedida."
            );
            return false;
        }

        /*
         * Registra o Service Worker.
         */
        await navigator.serviceWorker.register(
            "/service-worker.js"
        );

        console.log(
            "[Connecto Push] Service Worker registrado."
        );

        /*
         * Espera o Service Worker realmente ficar pronto.
         */
        const registration =
            await navigator.serviceWorker.ready;

        console.log(
            "[Connecto Push] Service Worker pronto."
        );

        /*
         * Verifica se este navegador já possui
         * uma subscription.
         */
        let subscription =
            await registration.pushManager
                .getSubscription();

        if (subscription) {

            console.log(
                "[Connecto Push] Subscription existente encontrada."
            );

        } else {

            console.log(
                "[Connecto Push] Criando nova subscription..."
            );

            subscription =
                await registration.pushManager.subscribe({
                    userVisibleOnly: true,

                    applicationServerKey:
                        urlBase64ToUint8Array(
                            publicKey
                        ),
                });

            console.log(
                "[Connecto Push] Subscription criada."
            );
        }

        console.log(
            "[Connecto Push] Enviando subscription ao Django..."
        );

        const response = await fetch(
            "/notificacoes/push/subscribe/",
            {
                method: "POST",

                credentials: "same-origin",

                headers: {
                    "Content-Type":
                        "application/json",

                    "X-CSRFToken":
                        getCookie("csrftoken"),
                },

                body: JSON.stringify(
                    subscription.toJSON()
                ),
            }
        );

        let data = {};

        try {
            data = await response.json();
        } catch (e) {
            // resposta sem JSON
        }

        if (!response.ok) {

            console.error(
                "[Connecto Push] Django recusou a subscription:",
                response.status,
                data
            );

            return false;
        }

        console.log(
            "[Connecto Push] Subscription salva no Django!",
            data
        );

        return true;

    } catch (error) {

        console.error(
            "[Connecto Push] ERRO durante ativação:",
            error
        );

        return false;
    }
}


/*
 * Deixa explicitamente disponível para
 * notificacoes.js.
 */
window.ativarPush = ativarPush;