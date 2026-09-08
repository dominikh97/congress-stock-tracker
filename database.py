import os
from supabase import create_client


SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


def insert_trade(trade):

    data = {
        "member": trade.get("member"),
        "chamber": trade.get("chamber"),
        "ticker": trade.get("ticker"),
        "trade_type": trade.get("trade_type"),
        "amount": trade.get("amount"),
        "tx_date": trade.get("tx_date"),
        "disclosed": trade.get("disclosed"),
        "asset": trade.get("asset"),
        "link": trade.get("link"),
    }

    result = (
        supabase
        .table("trades")
        .upsert(
            data,
            on_conflict=(
                "member,ticker,trade_type,"
                "tx_date,disclosed,amount"
            )
        )
        .execute()
    )

    return result
