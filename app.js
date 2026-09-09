const DATA_URL = "data/trades.json";


let allTrades = [];


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

        updateStats();
        renderTrades();

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


function renderTrades() {

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


    const filtered = allTrades.filter(trade => {

        const politician =
            (trade.member || "").toLowerCase();

        const ticker =
            (trade.ticker || "").toLowerCase();

        const transaction =
            (trade.trade_type || "").toUpperCase();


        return (
            politician.includes(politicianFilter) &&
            ticker.includes(tickerFilter) &&
            (
                !transactionFilter ||
                transaction.includes(transactionFilter)
            )
        );
    });


    const table =
        document.getElementById("trades-table");


    if (filtered.length === 0) {

        table.innerHTML = `
            <tr>
                <td colspan="8" class="loading">
                    No trades found.
                </td>
            </tr>
        `;

        return;
    }


    table.innerHTML = filtered.map(trade => {

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


function escapeHtml(value) {

    if (!value) return "";

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


document
    .getElementById("politician-filter")
    .addEventListener("input", renderTrades);

document
    .getElementById("ticker-filter")
    .addEventListener("input", renderTrades);

document
    .getElementById("transaction-filter")
    .addEventListener("change", renderTrades);


loadTrades();
