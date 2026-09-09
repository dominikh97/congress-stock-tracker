const TRADES_JSON_URL =
    "https://raw.githubusercontent.com/dominikh97/congress-stock-tracker/main/data/trades.json";

const PENDING_TTL_SECONDS = 60 * 60 * 48; // 48 hours
const MAX_MEMBERS = 20;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,X-Api-Key",
};

function jsonResponse(data, status = 200) {
    return new Response(JSON.stringify(data), {
        status,
        headers: { "Content-Type": "application/json", ...CORS_HEADERS },
    });
}

function htmlResponse(body, status = 200) {
    return new Response(body, {
        status,
        headers: { "Content-Type": "text/html; charset=utf-8", ...CORS_HEADERS },
    });
}

function emailKey(email) {
    return `email:${email.trim().toLowerCase()}`;
}

function pendingKey(token) {
    return `pending:${token}`;
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

async function knownMembers() {
    const res = await fetch(TRADES_JSON_URL);

    if (!res.ok) {
        throw new Error("Failed to load trades.json for member validation");
    }

    const trades = await res.json();

    return new Set(trades.map(t => t.member).filter(Boolean));
}

async function sendEmail(env, to, subject, text) {

    const res = await fetch("https://api.sendgrid.com/v3/mail/send", {
        method: "POST",
        headers: {
            "Authorization": `Bearer ${env.SENDGRID_API_KEY}`,
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            personalizations: [{ to: [{ email: to }] }],
            from: { email: env.FROM_EMAIL, name: "Congress Stock Tracker" },
            subject,
            content: [{ type: "text/plain", value: text }],
        }),
    });

    if (!res.ok) {
        const errText = await res.text();
        throw new Error(`SendGrid error ${res.status}: ${errText}`);
    }
}


// --- POST /subscribe: step 1, sends a confirmation email ------------

async function handleSubscribe(request, env) {

    let payload;

    try {
        payload = await request.json();
    } catch {
        return jsonResponse({ ok: false, message: "Invalid request body." }, 400);
    }

    const email = String(payload.email || "").trim();
    const members = payload.members;

    if (!EMAIL_RE.test(email)) {
        return jsonResponse(
            { ok: false, message: `'${email}' doesn't look like a valid email address.` },
            400
        );
    }

    if (!Array.isArray(members) || members.length === 0) {
        return jsonResponse({ ok: false, message: "No politicians were selected." }, 400);
    }

    if (members.length > MAX_MEMBERS) {
        return jsonResponse(
            { ok: false, message: `Too many politicians selected (max ${MAX_MEMBERS}).` },
            400
        );
    }

    let valid;

    try {
        valid = await knownMembers();
    } catch {
        return jsonResponse(
            { ok: false, message: "Couldn't verify politician names right now. Try again shortly." },
            502
        );
    }

    const cleaned = [];
    const unknown = [];

    for (const m of members) {
        const name = String(m).trim();
        if (valid.has(name)) cleaned.push(name);
        else unknown.push(name);
    }

    if (unknown.length > 0) {
        return jsonResponse(
            { ok: false, message: `Unrecognized politician name(s): ${unknown.join(", ")}.` },
            400
        );
    }

    const token = crypto.randomUUID();
    const confirmUrl = `${new URL(request.url).origin}/confirm?token=${token}`;

    const emailBody =
`Someone (hopefully you) asked to subscribe this address to trade alerts for:

${cleaned.map(m => `- ${m}`).join("\n")}

To confirm, open this link:
${confirmUrl}

This link expires in 48 hours. If you didn't request this, just ignore this
email - nothing is activated until the link above is opened.`;

    // Send first, store second: if delivery fails there's nothing to
    // clean up, since a token nobody received is useless anyway.
    try {
        await sendEmail(
            env,
            email,
            "Confirm your Congress Stock Tracker alert subscription",
            emailBody
        );
    } catch {
        return jsonResponse(
            { ok: false, message: "Couldn't send the confirmation email. Try again shortly." },
            502
        );
    }

    await env.SUBS_KV.put(
        pendingKey(token),
        JSON.stringify({ email, members: cleaned, requestedAt: Date.now() }),
        { expirationTtl: PENDING_TTL_SECONDS }
    );

    return jsonResponse({
        ok: true,
        message: `Check ${email} for a confirmation email and click the link inside. It expires in 48 hours.`,
    });
}


// --- GET /confirm: step 2, activates the subscription ----------------

function confirmPage(success, message, members) {

    const list = members && members.length
        ? `<ul>${members.map(m => `<li>${escapeHtml(m)}</li>`).join("")}</ul>`
        : "";

    return `<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Congress Stock Tracker</title>
<style>
    body { font-family: Arial, Helvetica, sans-serif; background:#f5f6f8; color:#202124; margin:0; padding:60px 20px; }
    .card { max-width: 480px; margin: 0 auto; background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 32px; text-align: center; }
    h1 { font-size: 20px; margin: 0 0 12px; color: ${success ? "#15803d" : "#b91c1c"}; }
    p { color: #374151; line-height: 1.5; }
    ul { text-align: left; display: inline-block; }
</style>
</head>
<body>
    <div class="card">
        <h1>${success ? "Subscription confirmed" : "Something went wrong"}</h1>
        <p>${escapeHtml(message)}</p>
        ${list}
    </div>
</body>
</html>`;
}

async function handleConfirm(request, env) {

    const token = new URL(request.url).searchParams.get("token") || "";
    const raw = token ? await env.SUBS_KV.get(pendingKey(token)) : null;

    if (!raw) {
        return htmlResponse(
            confirmPage(false, "This confirmation link is invalid or has already been used."),
            400
        );
    }

    const pending = JSON.parse(raw);

    const existingRaw = await env.SUBS_KV.get(emailKey(pending.email));
    const existing = existingRaw ? JSON.parse(existingRaw) : { members: [] };

    const memberSet = new Set(existing.members || []);
    for (const m of pending.members) memberSet.add(m);

    await env.SUBS_KV.put(emailKey(pending.email), JSON.stringify({ members: [...memberSet] }));
    await env.SUBS_KV.delete(pendingKey(token));

    return htmlResponse(
        confirmPage(
            true,
            `You're all set. We'll email ${pending.email} whenever one of these files a new trade:`,
            [...memberSet]
        )
    );
}


// --- POST /unsubscribe: processed immediately, no confirmation --------

async function handleUnsubscribe(request, env) {

    let payload;

    try {
        payload = await request.json();
    } catch {
        return jsonResponse({ ok: false, message: "Invalid request body." }, 400);
    }

    const email = String(payload.email || "").trim();
    const members = payload.members;
    const all = Boolean(payload.all);

    if (!EMAIL_RE.test(email)) {
        return jsonResponse(
            { ok: false, message: `'${email}' doesn't look like a valid email address.` },
            400
        );
    }

    if (!all && !(Array.isArray(members) && members.length > 0)) {
        return jsonResponse(
            { ok: false, message: "Select at least one politician, or choose to unsubscribe from all." },
            400
        );
    }

    const key = emailKey(email);
    const existingRaw = await env.SUBS_KV.get(key);
    const existing = existingRaw ? JSON.parse(existingRaw) : { members: [] };

    let removedCount = 0;

    if (all) {
        removedCount = (existing.members || []).length;
        await env.SUBS_KV.delete(key);
    } else {
        const targetLower = new Set(members.map(m => String(m).trim().toLowerCase()));
        const kept = (existing.members || []).filter(m => !targetLower.has(m.toLowerCase()));
        removedCount = (existing.members || []).length - kept.length;

        if (kept.length > 0) {
            await env.SUBS_KV.put(key, JSON.stringify({ members: kept }));
        } else {
            await env.SUBS_KV.delete(key);
        }
    }

    // Also cancel any pending (unconfirmed) request for this email, so
    // it can't silently re-add what was just removed.
    let pendingCancelled = 0;
    let cursor;

    do {
        const list = await env.SUBS_KV.list({ prefix: "pending:", cursor });

        for (const k of list.keys) {
            const raw = await env.SUBS_KV.get(k.name);
            if (!raw) continue;

            const p = JSON.parse(raw);

            if ((p.email || "").toLowerCase() === email.toLowerCase()) {
                await env.SUBS_KV.delete(k.name);
                pendingCancelled++;
            }
        }

        cursor = list.list_complete ? undefined : list.cursor;
    } while (cursor);

    if (removedCount === 0 && pendingCancelled === 0) {
        return jsonResponse({
            ok: true,
            message: `No matching subscriptions found for ${email} - nothing to do.`,
        });
    }

    let message = `Removed ${removedCount} active subscription(s) for ${email}.`;
    if (pendingCancelled) message += " Also cancelled a pending (unconfirmed) request.";

    return jsonResponse({ ok: true, message });
}


// --- GET /alert-recipients: private, used by the daily Action ---------

async function handleAlertRecipients(request, env) {

    const key = request.headers.get("X-Api-Key");

    if (!key || key !== env.SUBSCRIPTIONS_API_KEY) {
        return jsonResponse({ error: "unauthorized" }, 401);
    }

    const results = [];
    let cursor;

    do {
        const list = await env.SUBS_KV.list({ prefix: "email:", cursor });

        for (const k of list.keys) {
            const raw = await env.SUBS_KV.get(k.name);
            if (!raw) continue;

            const data = JSON.parse(raw);
            const email = k.name.slice("email:".length);

            if (data.members && data.members.length) {
                results.push({ email, members: data.members });
            }
        }

        cursor = list.list_complete ? undefined : list.cursor;
    } while (cursor);

    return jsonResponse(results);
}


export default {
    async fetch(request, env) {

        const url = new URL(request.url);

        if (request.method === "OPTIONS") {
            return new Response(null, { headers: CORS_HEADERS });
        }

        if (url.pathname === "/subscribe" && request.method === "POST") {
            return handleSubscribe(request, env);
        }

        if (url.pathname === "/confirm" && request.method === "GET") {
            return handleConfirm(request, env);
        }

        if (url.pathname === "/unsubscribe" && request.method === "POST") {
            return handleUnsubscribe(request, env);
        }

        if (url.pathname === "/alert-recipients" && request.method === "GET") {
            return handleAlertRecipients(request, env);
        }

        return jsonResponse({ error: "not found" }, 404);
    },
};
