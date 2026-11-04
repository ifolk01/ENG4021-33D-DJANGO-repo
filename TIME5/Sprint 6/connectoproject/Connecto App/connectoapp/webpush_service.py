import json

from django.conf import settings
from pywebpush import WebPushException, webpush


def enviar_push(
    usuario,
    titulo,
    mensagem,
    url="/notificacoes/",
):
    subscriptions = usuario.push_subscriptions.filter(
        ativa=True
    )

    payload = json.dumps({
        "title": titulo,
        "body": mensagem,
        "url": url,
    })

    enviado = False

    for subscription in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {
                        "p256dh": subscription.p256dh,
                        "auth": subscription.auth,
                    },
                },
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={
                    "sub": settings.VAPID_SUBJECT,
                },
            )

            enviado = True

        except WebPushException as exc:
            print("Erro Web Push:", exc)

            # Subscription não existe mais no navegador.
            if (
                exc.response is not None
                and exc.response.status_code in (404, 410)
            ):
                subscription.ativa = False
                subscription.save(
                    update_fields=["ativa"]
                )

    return enviado