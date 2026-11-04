self.addEventListener("push", event => {
    let dados = {
        title: "Connecto",
        body: "Você tem uma nova notificação.",
        url: "/notificacoes/"
    };

    if (event.data) {
        dados = event.data.json();
    }

    event.waitUntil(
        self.registration.showNotification(
            dados.title,
            {
                body: dados.body,

                icon: "/static/logo_icon.jpg",

                badge: "/static/logo_icon.jpg",

                data: {
                    url: dados.url
                }
            }
        )
    );
});

self.addEventListener(
    "notificationclick",
    event => {

        event.notification.close();

        const url =
            event.notification.data?.url
            || "/notificacoes/";

        event.waitUntil(
            clients.openWindow(url)
        );
    }
);