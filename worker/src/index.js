export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname === "/webhook" && request.method === "POST") {
      return handleWebhook(request, env, ctx);
    }

    if (url.pathname === "/register") {
      const token = url.searchParams.get("token");
      if (token !== env.TELEGRAM_SECRET) {
        return new Response("Unauthorized", { status: 403 });
      }
      return registerWebhook(url, env);
    }

    return new Response("aw-telegram-bot relay", { status: 200 });
  },
};

async function handleWebhook(request, env, ctx) {
  // Validate Telegram secret token
  const secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token");
  if (secret !== env.TELEGRAM_SECRET) {
    return new Response("Unauthorized", { status: 403 });
  }

  let update;
  try {
    update = await request.json();
  } catch {
    return new Response("Bad Request", { status: 400 });
  }

  // Only process text messages
  if (!update.message?.text) {
    return new Response("OK", { status: 200 });
  }

  // Fire-and-forget: dispatch to GitHub
  ctx.waitUntil(dispatchToGitHub(update, env));

  return new Response("OK", { status: 200 });
}

async function dispatchToGitHub(update, env) {
  const msg = update.message;

  const response = await fetch(
    `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/dispatches`,
    {
      method: "POST",
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${env.GITHUB_TOKEN}`,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "aw-telegram-bot",
      },
      body: JSON.stringify({
        event_type: "telegram_message",
        client_payload: {
          chat_id: msg.chat.id,
          text: msg.text,
          username: msg.from?.username || "",
          message_id: msg.message_id,
        },
      }),
    }
  );

  if (!response.ok) {
    console.error("GitHub dispatch failed:", response.status, await response.text());
  }
}

async function registerWebhook(requestUrl, env) {
  const webhookUrl = `${requestUrl.protocol}//${requestUrl.hostname}/webhook`;
  try {
    const result = await fetch(
      `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/setWebhook`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: webhookUrl,
          secret_token: env.TELEGRAM_SECRET,
          allowed_updates: ["message"],
          drop_pending_updates: true,
        }),
      }
    );

    const json = await result.json();
    return new Response(JSON.stringify(json, null, 2), {
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), {
      status: 502,
      headers: { "Content-Type": "application/json" },
    });
  }
}
