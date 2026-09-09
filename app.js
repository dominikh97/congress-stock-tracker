const DATA_URL = "data/trades.json";
const PAGE_SIZE = 50;
const WHALE_COUNT = 5;
const WHALE_WINDOW_DAYS = 30;
const MAX_ALERT_MEMBERS = 20;
const REPO_URL = "https://github.com/dominikh97/congress-stock-tracker";


let allTrades = [];
let allMembers = [];
let currentPage = 1;
let selectedMembers = new Set();
let alertsMode = "subscribe";


async function loadTrades() {

    try {

        const response = await fetch(DATA_URL);

        if (!response.ok) {
            throw new Error("Failed to load trades.json");
        }

        const trades = await response.json();

        allTrades = trades.slice().sort(
            (a, b) => (b.disclosed || "").localeCompare(a.disclosed || "")
        );

        allMembers = [...new Set(
            allTrades.map(t => t.member).filter(Boolean)
        )].sort();

        updateStats();
        renderWhales();
        renderTrades();
        renderPoliticianPicker();

    } catch (error) {

        console.error(error);

        document.getElementById("trades-table").innerHTML = `
            <tr>
                <td colspan="8" class="loading">
                    Unable to load trades.
                </td>
            </tr>
        `;
    }
}


function updateStats() {

    const politicians = new Set(
        allTrades.map(t => t.member)
    );

    const stocks = new Set(
        allTrades
            .map(t => t.ticker)
            .filter(Boolean)
    );

    document.getElementById("trade-count").textContent =
        allTrades.length;

    document.getElementById("politician-count").textContent =
        politicians.size;

    document.getElementById("stock-count").textContent =
        stocks.size;
}


function renderWhales() {

    const container = document.getElementById("whale-list");

    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - WHALE_WINDOW_DAYS);

    const whales = allTrades
        .filter(t =>
            typeof t.amount_high === "number" &&
            t.tx_date &&
            new Date(t.tx_date) >= cutoff
        )
        .slice()
        .sort((a, b) => b.amount_high - a.amount_high)
        .slice(0, WHALE_COUNT);

    if (whales.length === 0) {
        container.innerHTML = `<p class="loading">No large trades disclosed in the last ${WHALE_WINDOW_DAYS} days.</p>`;
        return;
    }

    container.innerHTML = whales.map((trade, index) => {

        const symbol = trade.ticker || trade.company || "Unknown asset";

        const transaction = (trade.trade_type || "").toUpperCase();

        const transactionClass =
            transaction.includes("BUY")
                ? "buy"
                : transaction.includes("SELL")
                    ? "sell"
                    : "";

        return `
            <div class="whale-card">
                <div class="whale-rank">#${index + 1}</div>
                <div class="whale-body">
                    <div class="whale-title">
                        <strong>${escapeHtml(symbol)}</strong>
                        <span class="${transactionClass}">${escapeHtml(trade.trade_type)}</span>
                    </div>
                    <div class="whale-meta">
                        ${escapeHtml(trade.member)} &middot; ${escapeHtml(trade.chamber)}
                    </div>
                    <div class="whale-amount">${escapeHtml(trade.amount)}</div>
                </div>
            </div>
        `;

    }).join("");
}


function getFilteredTrades() {

    const politicianFilter =
        document
            .getElementById("politician-filter")
            .value
            .toLowerCase();

    const tickerFilter =
        document
            .getElementById("ticker-filter")
            .value
            .toLowerCase();

    const transactionFilter =
        document.getElementById("transaction-filter").value;


    return allTrades.filter(trade => {

        const politician =
            (trade.member || "").toLowerCase();

        const ticker =
            (trade.ticker || "").toLowerCase();

        const company =
            (trade.company || "").toLowerCase();

        const transaction =
            (trade.trade_type || "").toUpperCase();


        return (
            politician.includes(politicianFilter) &&
            (
                !tickerFilter ||
                ticker.includes(tickerFilter) ||
                company.includes(tickerFilter)
            ) &&
            (
                !transactionFilter ||
                transaction.includes(transactionFilter)
            )
        );
    });
}


function renderTrades() {

    // Search always runs over the full dataset - only the page shown
    // in the table is capped, for faster rendering.
    const filtered = getFilteredTrades();

    const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));

    currentPage = Math.min(Math.max(currentPage, 1), totalPages);

    const start = (currentPage - 1) * PAGE_SIZE;
    const pageItems = filtered.slice(start, start + PAGE_SIZE);


    const table =
        document.getElementById("trades-table");


    if (pageItems.length === 0) {

        table.innerHTML = `
            <tr>
                <td colspan="8" class="loading">
                    No trades found.
                </td>
            </tr>
        `;

    } else {

        table.innerHTML = pageItems.map(trade => {

            const transaction =
                (trade.trade_type || "").toUpperCase();

            const transactionClass =
                transaction.includes("BUY")
                    ? "buy"
                    : transaction.includes("SELL")
                        ? "sell"
                        : "";


            return `
                <tr>

                    <td>${escapeHtml(trade.member)}</td>

                    <td>${escapeHtml(trade.chamber)}</td>

                    <td>
                        <strong>${escapeHtml(trade.ticker)}</strong>
                        ${
                            trade.company
                                ? `<div class="ticker-company">${escapeHtml(trade.company)}</div>`
                                : ""
                        }
                    </td>

                    <td class="${transactionClass}">
                        ${escapeHtml(trade.trade_type)}
                    </td>

                    <td>${escapeHtml(trade.amount)}</td>

                    <td>${escapeHtml(trade.tx_date)}</td>

                    <td>${escapeHtml(trade.disclosed)}</td>

                    <td>
                        ${
                            trade.link
                                ? `<a href="${trade.link}"
                                      target="_blank">
                                      Filing
                                   </a>`
                                : ""
                        }
                    </td>

                </tr>
            `;

        }).join("");
    }

    updatePaginationControls(filtered.length, totalPages);
}


function updatePaginationControls(filteredCount, totalPages) {

    document.getElementById("page-indicator").textContent =
        `Page ${currentPage} of ${totalPages}`;

    document.getElementById("page-first").disabled = currentPage <= 1;
    document.getElementById("page-prev").disabled = currentPage <= 1;
    document.getElementById("page-next").disabled = currentPage >= totalPages;
    document.getElementById("page-last").disabled = currentPage >= totalPages;

    const rangeStart = filteredCount === 0 ? 0 : (currentPage - 1) * PAGE_SIZE + 1;
    const rangeEnd = Math.min(currentPage * PAGE_SIZE, filteredCount);

    document.getElementById("table-caption").textContent =
        `Showing ${rangeStart}-${rangeEnd} of ${filteredCount} matching trades (${allTrades.length} tracked total).`;
}


function goToPage(page) {
    currentPage = page;
    renderTrades();
}


function applyFiltersAndRender() {
    currentPage = 1;
    renderTrades();
}


function renderPoliticianPicker() {

    const container = document.getElementById("politician-picker");

    const query =
        document
            .getElementById("politician-search")
            .value
            .toLowerCase();

    const visible = allMembers.filter(m => m.toLowerCase().includes(query));

    if (visible.length === 0) {
        container.innerHTML = `<p class="loading">No politicians match that search.</p>`;
        return;
    }

    container.innerHTML = visible.map(member => {

        const id = `member-${member.replace(/[^a-zA-Z0-9]+/g, "-")}`;
        const checked = selectedMembers.has(member) ? "checked" : "";

        return `
            <label class="politician-option" for="${id}">
                <input type="checkbox" id="${id}" value="${escapeHtml(member)}" ${checked}>
                ${escapeHtml(member)}
            </label>
        `;

    }).join("");

    container.querySelectorAll("input[type=checkbox]").forEach(checkbox => {

        checkbox.addEventListener("change", () => {

            if (checkbox.checked) {

                if (selectedMembers.size >= MAX_ALERT_MEMBERS) {
                    checkbox.checked = false;
                    setAlertsStatus(
                        `You can select up to ${MAX_ALERT_MEMBERS} politicians.`,
                        true
                    );
                    return;
                }

                selectedMembers.add(checkbox.value);

            } else {
                selectedMembers.delete(checkbox.value);
            }

            document.getElementById("selected-count").textContent =
                selectedMembers.size;
        });
    });
}


function setAlertsStatus(message, isError) {

    const el = document.getElementById("alerts-status");

    el.textContent = message;
    el.style.color = isError ? "#b91c1c" : "#15803d";
}


function buildRequestIssueUrl(titlePrefix, intro, email, payload, labels) {

    const title = `${titlePrefix} ${email}`;

    const payloadJson = JSON.stringify(payload, null, 2);

    const body =
`${intro}

\`\`\`json
${payloadJson}
\`\`\`

_(This issue was generated by the Email Alerts tab and is processed automatically.)_`;

    const params = new URLSearchParams({ title, body, labels });

    return `${REPO_URL}/issues/new?${params.toString()}`;
}


function buildSubscribeIssueUrl(email, members) {

    return buildRequestIssueUrl(
        "Subscribe request:",
        "Please subscribe me to trade alerts for the politicians below.",
        email,
        { email, members },
        "subscribe-request"
    );
}


function buildUnsubscribeIssueUrl(email, members, unsubscribeAll) {

    const payload = unsubscribeAll
        ? { email, all: true }
        : { email, members };

    return buildRequestIssueUrl(
        "Unsubscribe request:",
        "Please remove me from trade alerts as described below.",
        email,
        payload,
        "unsubscribe-request"
    );
}


function escapeHtml(value) {

    if (!value) return "";

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


// --- Tabs ---------------------------------------------------------

document.querySelectorAll(".tab-button").forEach(button => {

    button.addEventListener("click", () => {

        const tab = button.dataset.tab;

        document.querySelectorAll(".tab-button").forEach(b => {
            b.classList.toggle("active", b === button);
        });

        document.getElementById("tab-trades").hidden = tab !== "trades";
        document.getElementById("tab-alerts").hidden = tab !== "alerts";
    });
});


// --- Trades tab: filters + pagination ------------------------------

document
    .getElementById("politician-filter")
    .addEventListener("input", applyFiltersAndRender);

document
    .getElementById("ticker-filter")
    .addEventListener("input", applyFiltersAndRender);

document
    .getElementById("transaction-filter")
    .addEventListener("change", applyFiltersAndRender);

document
    .getElementById("page-first")
    .addEventListener("click", () => goToPage(1));

document
    .getElementById("page-prev")
    .addEventListener("click", () => goToPage(currentPage - 1));

document
    .getElementById("page-next")
    .addEventListener("click", () => goToPage(currentPage + 1));

document
    .getElementById("page-last")
    .addEventListener("click", () => {
        const totalPages = Math.max(1, Math.ceil(getFilteredTrades().length / PAGE_SIZE));
        goToPage(totalPages);
    });


// --- Email alerts tab -----------------------------------------------

document
    .getElementById("politician-search")
    .addEventListener("input", renderPoliticianPicker);

document.querySelectorAll(".mode-button").forEach(button => {

    button.addEventListener("click", () => {

        alertsMode = button.dataset.mode;

        document.querySelectorAll(".mode-button").forEach(b => {
            b.classList.toggle("active", b === button);
        });

        const isUnsubscribe = alertsMode === "unsubscribe";

        document.getElementById("unsubscribe-all-wrap").hidden = !isUnsubscribe;

        document.getElementById("alerts-heading").textContent =
            isUnsubscribe ? "Stop getting alerts" : "Get emailed on new trades";

        document.getElementById("alerts-intro").textContent = isUnsubscribe
            ? "Enter the email you subscribed with, then pick which politicians to remove (or unsubscribe from everything)."
            : "Pick one or more members of Congress below. Whenever they buy or sell any stock, you'll get an email as soon as it's disclosed. You'll need to confirm your email address before alerts start.";

        document.getElementById("alerts-footnote").textContent = isUnsubscribe
            ? "This opens a pre-filled GitHub issue with your request (a free GitHub account is required to submit it). It's processed immediately - no email confirmation needed to unsubscribe."
            : "This opens a pre-filled GitHub issue with your request (a free GitHub account is required to submit it). You'll then get a confirmation email - click the link inside to finish subscribing.";

        setAlertsStatus("", false);
    });
});

document
    .getElementById("alerts-form")
    .addEventListener("submit", event => {

        event.preventDefault();

        const email = document.getElementById("alerts-email").value.trim();
        const members = Array.from(selectedMembers);

        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            setAlertsStatus("Please enter a valid email address.", true);
            return;
        }

        let url;

        if (alertsMode === "unsubscribe") {

            const unsubscribeAll = document.getElementById("unsubscribe-all").checked;

            if (!unsubscribeAll && members.length === 0) {
                setAlertsStatus(
                    "Select at least one politician, or check 'unsubscribe from all'.",
                    true
                );
                return;
            }

            url = buildUnsubscribeIssueUrl(email, members, unsubscribeAll);

        } else {

            if (members.length === 0) {
                setAlertsStatus("Select at least one politician.", true);
                return;
            }

            url = buildSubscribeIssueUrl(email, members);
        }

        window.open(url, "_blank", "noopener");

        setAlertsStatus(
            alertsMode === "unsubscribe"
                ? "Opened a GitHub issue in a new tab - submit it there to finish unsubscribing."
                : "Opened a GitHub issue in a new tab. After you submit it, check your email for a confirmation link.",
            false
        );
    });


loadTrades();
