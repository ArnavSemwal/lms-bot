const COURSES = [
  { label: "Operating Systems (BACSE106)", value: "os" },
  { label: "Database Systems (BACSE202)", value: "dbs" }
];

const CONTROL_FILE_PATH = "bot_control.json";
const BLOCKED_LOG_PATH = "blocked_log.json";
const FILTER_CONFIG_PATH = "filter_config.json";

async function getRepoFile(env, path) {
  const resp = await fetch(
    `https://api.github.com/repos/${env.GITHUB_REPO}/contents/${path}`,
    {
      headers: {
        Authorization: `Bearer ${env.GITHUB_PAT}`,
        Accept: "application/vnd.github+json",
        "User-Agent": "lms-bot-worker",
      },
    }
  );
  if (!resp.ok) return { content: null, sha: null };
  const data = await resp.json();
  const content = JSON.parse(atob(data.content));
  return { content, sha: data.sha };
}

async function setRepoFile(env, path, content, sha, message) {
  const resp = await fetch(
    `https://api.github.com/repos/${env.GITHUB_REPO}/contents/${path}`,
    {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${env.GITHUB_PAT}`,
        Accept: "application/vnd.github+json",
        "User-Agent": "lms-bot-worker",
      },
      body: JSON.stringify({
        message,
        content: btoa(JSON.stringify(content, null, 2)),
        sha,
      }),
    }
  );
  return resp.ok;
}

async function getControlFile(env) {
  const { content, sha } = await getRepoFile(env, CONTROL_FILE_PATH);
  return { enabled: content ? content.enabled !== false : true, sha };
}

async function setControlFile(env, enabled, sha) {
  return setRepoFile(env, CONTROL_FILE_PATH, { enabled }, sha, `Bot ${enabled ? "resumed" : "paused"} via Telegram`);
}

function makeCallbackData(courseTitle) { return "cc:" + btoa(courseTitle); }
function decodeCourseCallback(data) { return atob(data.replace(/^cc:/, "")); }

async function getUniqueBlockedCourses(env) {
  const { content } = await getRepoFile(env, BLOCKED_LOG_PATH);
  if (!content || !Array.isArray(content)) return [];
  // ✅ FIX: Using e.course instead of e.course_title
  return [...new Set(content.map((e) => e.course))];
}

export default {
  async fetch(request, env, ctx) {
    if (request.method !== "POST") return new Response("OK");
    let update;
    try { update = await request.json(); } catch (err) { return new Response("OK"); }

    try {
      if (update.message && update.message.text === "/stop") {
        const chatId = update.message.chat.id;
        const { sha } = await getControlFile(env);
        const ok = await setControlFile(env, false, sha);
        ctx.waitUntil(telegramCall(env, "sendMessage", { chat_id: chatId, text: ok ? "🛑 Bot paused. Send /start to resume." : "Failed to pause the bot." }));
        return new Response("OK");
      }

      if (update.message && update.message.text === "/start") {
        const chatId = update.message.chat.id;
        const { sha } = await getControlFile(env);
        const ok = await setControlFile(env, true, sha);
        ctx.waitUntil(telegramCall(env, "sendMessage", { chat_id: chatId, text: ok ? "✅ Bot resumed." : "Failed to resume the bot." }));
        return new Response("OK");
      }

      if (update.message && update.message.text === "/check") {
        const chatId = update.message.chat.id;
        const { enabled } = await getControlFile(env);
        if (!enabled) {
          ctx.waitUntil(telegramCall(env, "sendMessage", { chat_id: chatId, text: "Bot is currently paused. Send /start to resume." }));
          return new Response("OK");
        }
        const keyboard = { inline_keyboard: COURSES.map((c) => [{ text: c.label, callback_data: c.value }]) };
        ctx.waitUntil(telegramCall(env, "sendMessage", { chat_id: chatId, text: "Pick a subject to check now:", reply_markup: keyboard }));
        return new Response("OK");
      }

      if (update.message && update.message.text === "/reviewblocked") {
        const chatId = update.message.chat.id;
        const courses = await getUniqueBlockedCourses(env);
        if (courses.length === 0) {
          ctx.waitUntil(telegramCall(env, "sendMessage", { chat_id: chatId, text: "Nothing in the blocked log right now." }));
          return new Response("OK");
        }
        const keyboard = { inline_keyboard: courses.map((c) => [{ text: c.slice(0, 60), callback_data: makeCallbackData(c) }]) };
        ctx.waitUntil(telegramCall(env, "sendMessage", { chat_id: chatId, text: "Blocked courses found. Tap one that's yours to whitelist it:", reply_markup: keyboard }));
        return new Response("OK");
      }

      if (update.callback_query) {
        const query = update.callback_query;
        const chatId = query.message.chat.id;
        const messageId = query.message.message_id;

        if (query.data.startsWith("cc:")) {
          const courseTitle = decodeCourseCallback(query.data);
          ctx.waitUntil((async () => {
            await telegramCall(env, "answerCallbackQuery", { callback_query_id: query.id });
            const { content, sha } = await getRepoFile(env, FILTER_CONFIG_PATH);
            const allowed = content && Array.isArray(content.allowed_keywords) ? content.allowed_keywords : [];
            if (!allowed.includes(courseTitle)) allowed.push(courseTitle);
            const ok = await setRepoFile(env, FILTER_CONFIG_PATH, { allowed_keywords: allowed }, sha, `Add "${courseTitle}" to allowlist via Telegram`);
            await telegramCall(env, "editMessageText", { chat_id: chatId, message_id: messageId, text: ok ? `Added "${courseTitle}" to allowlist. Next check will fetch its assignments.` : `Failed to update filter config.` });
          })());
          return new Response("OK");
        }

        const courseValue = query.data;
        const course = COURSES.find((c) => c.value === courseValue);
        const courseLabel = course ? course.label : courseValue;
        const { enabled } = await getControlFile(env);
        
        if (!enabled) {
          ctx.waitUntil(Promise.all([
            telegramCall(env, "answerCallbackQuery", { callback_query_id: query.id }),
            telegramCall(env, "editMessageText", { chat_id: chatId, message_id: messageId, text: "Bot is paused. Send /start to resume." })
          ]));
          return new Response("OK");
        }
        ctx.waitUntil(handleCourseCheck(env, query.id, chatId, messageId, courseValue, courseLabel));
        return new Response("OK");
      }
      return new Response("OK");
    } catch (err) {
      return new Response("OK");
    }
  },
};

async function handleCourseCheck(env, callbackQueryId, chatId, messageId, courseValue, courseLabel) {
  try {
    await telegramCall(env, "answerCallbackQuery", { callback_query_id: callbackQueryId });
    const ghResponse = await fetch(`https://api.github.com/repos/${env.GITHUB_REPO}/dispatches`, {
      method: "POST",
      headers: { Authorization: `Bearer ${env.GITHUB_PAT}`, Accept: "application/vnd.github+json", "User-Agent": "lms-bot-worker" },
      body: JSON.stringify({ event_type: "check_course", client_payload: { course: courseValue, chat_id: chatId } }),
    });

    if (!ghResponse.ok) {
      await telegramCall(env, "editMessageText", { chat_id: chatId, message_id: messageId, text: `GitHub dispatch failed (${ghResponse.status}). Check PAT/Repo setup.` });
      return;
    }
    await telegramCall(env, "editMessageText", { chat_id: chatId, message_id: messageId, text: `Checking ${courseLabel}...` });
  } catch (err) {
    await telegramCall(env, "editMessageText", { chat_id: chatId, message_id: messageId, text: `Something went wrong checking ${courseLabel}.` }).catch(() => {});
  }
}

async function telegramCall(env, method, body) {
  return fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/${method}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}