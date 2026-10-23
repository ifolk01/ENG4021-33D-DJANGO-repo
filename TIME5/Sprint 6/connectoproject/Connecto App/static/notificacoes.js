const INTERVALO_MS = 10 * 60 * 1000;

function csrf() {
  return document.querySelector("script[data-csrf]")?.dataset.csrf;
}

function suportaAvisos() {
  return "Notification" in window;
}

function notificacaoPermitida() {
  return suportaAvisos() && Notification.permission === "granted";
}

function atualizarBotao() {
  const botao = document.getElementById("btn-ativar-avisos");
  if (botao) botao.hidden = !(suportaAvisos() && Notification.permission === "default");
}

async function verificar() {
  const r = await fetch("/notificacoes/verificar/", {
    method: "POST",
    headers: { "X-CSRFToken": csrf() },
    body: new URLSearchParams({ mostrar: notificacaoPermitida() ? "1" : "0" }),
  });
  if (!r.ok || r.redirected) return;

  const dados = await r.json();

  dados.novas.forEach(n => {
    try {
      const aviso = new Notification("Connecto", { body: n.texto });
      aviso.onclick = () => {
        window.focus();
        window.location.href = "/notificacoes/";
      };
    } catch (e) {
      // alguns navegadores (ex.: Android) não aceitam new Notification
    }
  });

  const badge = document.getElementById("sino-badge");
  if (badge) badge.hidden = dados.nao_lidas === 0;
}

document.addEventListener("DOMContentLoaded", async () => {
  const botao = document.getElementById("btn-ativar-avisos");
  if (botao) {
    botao.addEventListener("click", async () => {
      await Notification.requestPermission();
      atualizarBotao();
      verificar();
    });
  }

  // Chrome/Firefox aceitam pedir ao carregar; o Safari ignora e usa o botão.
  if (suportaAvisos() && Notification.permission === "default") {
    try { await Notification.requestPermission(); } catch (e) {}
  }
  atualizarBotao();

  verificar();                          // ao acessar o app
  setInterval(verificar, INTERVALO_MS); // a cada 10 min
});