const COURSES = [
  { label: "Operating Systems Lab", value: "os-lab" },
  { label: "Data Structures", value: "data-structures" },
];

export default {
  async fetch(request, env, ctx) {
    if (request.method !== "POST") {
      return new Response("OK");
    }

    let update;
    try {
      update = await request.json();
    } catch (err) {
      return new Response("OK");
    }

    try {
      if (update.message && update.message.text === "/check") {
        const chatId = update.message.chat.id;
        const keyboard = {
          inline_keyboard: COURSES.map((c) => [
            { text: c.label, callback_data: c.value },
          ]),
        };
        ctx.waitUntil(
          telegramCall(env, "sendMessage", {
            chat_id: chatId,
            text: "Pick a subject to check now:",
            reply_markup: keyboard,
          }).catch((err) => console.error("sendMessage failed:", err))
        );
        return new Response("OK");
      }

      if (update.callback_query) {
        const query = update.callback_query;
        const courseValue = query.data;
        const course = COURSES.find((c) => c.value === courseValue);
        const courseLabel = course ? course.label : courseValue;
        const chatId = query.message.chat.id;
        const messageId = query.message.message_id;

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
      headers: {
        Authorization: `Bearer ${env.GITHUB_PAT}`,
        Accept: "application/vnd.github+json",
        "User-Agent": "lms-bot-worker",
      },
      body: JSON.stringify({
        event_type: "check_course",
        client_payload: { course: courseValue, chat_id: chatId },
      }),
    });

    if (!ghResponse.ok) {
      await telegramCall(env, "editMessageText", {
        chat_id: chatId,
        message_id: messageId,
        text: `Could not start the check for ${courseLabel} (GitHub API returned ${ghResponse.status}).`,
      });
      return;
    }

    await telegramCall(env, "editMessageText", {
      chat_id: chatId,
      message_id: messageId,
      text: `Checking ${courseLabel}...`,
    });
  } catch (err) {
    await telegramCall(env, "editMessageText", {
      chat_id: chatId,
      message_id: messageId,
      text: `Something went wrong checking ${courseLabel}.`,
    }).catch(() => {});
  }
}

async function telegramCall(env, method, body) {
  return fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/${method}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}