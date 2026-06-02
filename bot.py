import asyncio
import json
import os
import math

from pathlib import Path
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv

load_dotenv()

ROOMMATES = [
    "bagas",
    "anggit",
    "febrian"
]

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

EXPENSES_FILE = Path("expenses.json")
PAYMENTS_FILE = Path("payments.json")

def round_up_1000(amount):
    return math.ceil(amount / 1000) * 1000

def load_json(file):
    if not file.exists():
        return []

    with open(file, "r") as f:
        return json.load(f)


def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)


@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "🍺 Tavern Tabkeeper\n\n"
        "Commands:\n"
        "/add anggit 30000 listrik\n"
        "/pay bagas anggit 10000\n"
        "/history\n"
        "/payments\n"
        "/balance\n"
        "/help\n"
        "/ping"
        "/debts\n"
    )


@dp.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "🍺 Tavern Tabkeeper\n\n"
        "Commands:\n"
        "/add anggit 30000 listrik\n"
        "/pay bagas anggit 10000\n"
        "/history\n"
        "/payments\n"
        "/balance\n"
        "/debts\n"
        "/ping"
    )


@dp.message(Command("ping"))
async def ping(message: Message):
    await message.answer("pong 🏓")


@dp.message(Command("add"))
async def add_expense(message: Message):
    try:
        parts = message.text.split(maxsplit=3)

        payer = parts[1].lower()
        amount = int(parts[2])
        description = parts[3]

        if payer not in ROOMMATES:
            await message.answer(
                f"❌ {payer} tidak ada di daftar roommate"
            )
            return

        expenses = load_json(EXPENSES_FILE)

        expenses.append({
            "payer": payer,
            "amount": amount,
            "description": description,
            "created_by": message.from_user.username
        })

        save_json(EXPENSES_FILE, expenses)

        await message.answer(
            f"✅ Expense Added\n\n"
            f"👤 {payer}\n"
            f"💰 Rp{amount:,}\n"
            f"📝 {description}"
        )

    except Exception:
        await message.answer(
            "Usage:\n/add anggit 30000 listrik"
        )


@dp.message(Command("history"))
async def history(message: Message):
    expenses = load_json(EXPENSES_FILE)

    if not expenses:
        await message.answer("📜 No expenses recorded.")
        return

    text = "📜 Tavern Ledger\n\n"

    for i, expense in enumerate(expenses, start=1):
        text += (
            f"{i}. "
            f"{expense['payer']} | "
            f"Rp{expense['amount']:,} | "
            f"{expense['description']}\n"
        )

    await message.answer(text)


@dp.message(Command("pay"))
async def pay(message: Message):
    try:
        parts = message.text.split()

        payer = parts[1].lower()
        receiver = parts[2].lower()
        payment_input = parts[3].lower()

        if payer not in ROOMMATES:
            await message.answer(f"❌ {payer} tidak ditemukan")
            return

        if receiver not in ROOMMATES:
            await message.answer(f"❌ {receiver} tidak ditemukan")
            return

        payments = load_json(PAYMENTS_FILE)

        # =====================================
        # FULL SETTLEMENT MODE
        # /pay bagas anggit lunas
        # =====================================
        if payment_input == "lunas":

            expenses = load_json(EXPENSES_FILE)

            balances = {person: 0 for person in ROOMMATES}

            # Calculate balances from expenses
            for expense in expenses:
                expense_payer = expense["payer"]
                amount = expense["amount"]

                share = round_up_1000(
                    amount / len(ROOMMATES)
                )

                balances[expense_payer] += amount

                for person in ROOMMATES:
                    balances[person] -= share

            # Apply existing payments
            for payment in payments:
                balances[payment["payer"]] += payment["amount"]
                balances[payment["receiver"]] -= payment["amount"]

            creditors = []
            debtors = []

            for person, balance in balances.items():
                if balance > 0:
                    creditors.append([person, round(balance)])
                elif balance < 0:
                    debtors.append([person, round(-balance)])

            target_debt = 0

            i = 0
            j = 0

            while i < len(debtors) and j < len(creditors):
                debtor, debt = debtors[i]
                creditor, credit = creditors[j]

                settlement_amount = min(debt, credit)

                # THIS IS THE IMPORTANT PART
                if debtor == payer and creditor == receiver:
                    target_debt += settlement_amount

                debtors[i][1] -= settlement_amount
                creditors[j][1] -= settlement_amount

                if debtors[i][1] == 0:
                    i += 1

                if creditors[j][1] == 0:
                    j += 1

            if target_debt <= 0:
                await message.answer(
                    f"🎉 {payer} tidak memiliki hutang ke {receiver}"
                )
                return

            payments.append({
                "payer": payer,
                "receiver": receiver,
                "amount": target_debt
            })

            save_json(PAYMENTS_FILE, payments)

            await message.answer(
                f"✅ Debt Settled\n\n"
                f"{payer} → {receiver}\n"
                f"Rp{target_debt:,}"
            )

        # =====================================
        # PARTIAL PAYMENT MODE
        # /pay bagas anggit 100000
        # =====================================
        else:
            amount = int(payment_input)

            payments.append({
                "payer": payer,
                "receiver": receiver,
                "amount": amount
            })

            save_json(PAYMENTS_FILE, payments)

            await message.answer(
                f"💸 Payment Recorded\n\n"
                f"{payer} → {receiver}\n"
                f"Rp{amount:,}"
            )

    except Exception:
        await message.answer(
            "Usage:\n"
            "/pay bagas anggit 10000\n"
            "/pay bagas anggit lunas"
        )

@dp.message(Command("payments"))
async def payments(message: Message):
    data = load_json(PAYMENTS_FILE)

    if not data:
        await message.answer("💸 No payments recorded.")
        return

    text = "💸 Payments\n\n"

    for i, payment in enumerate(data, start=1):
        text += (
            f"{i}. "
            f"{payment['payer']} → "
            f"{payment['receiver']} | "
            f"Rp{payment['amount']:,}\n"
        )

    await message.answer(text)


@dp.message(Command("balance"))
async def balance(message: Message):
    expenses = load_json(EXPENSES_FILE)
    payments = load_json(PAYMENTS_FILE)

    balances = {person: 0 for person in ROOMMATES}

    # Calculate expenses
    for expense in expenses:
        payer = expense["payer"]
        amount = expense["amount"]

        share = round_up_1000(amount / len(ROOMMATES))

        balances[payer] += amount

        for person in ROOMMATES:
            balances[person] -= share

    # Apply payments
    for payment in payments:
        payer = payment["payer"]
        receiver = payment["receiver"]
        amount = payment["amount"]

        balances[payer] += amount
        balances[receiver] -= amount

    text = "📊 Tavern Balances\n\n"

    for person, balance in balances.items():
        sign = "+" if balance >= 0 else "-"
        text += (
            f"{person}: "
            f"{sign}Rp{abs(balance):,.0f}\n"
        )

    await message.answer(text)

@dp.message(Command("debts"))
async def debts(message: Message):
    expenses = load_json(EXPENSES_FILE)
    payments = load_json(PAYMENTS_FILE)

    debts = []

    for expense in expenses:
        payer = expense["payer"]
        amount = expense["amount"]

        share = round_up_1000(
            amount / len(ROOMMATES)
        )

        for person in ROOMMATES:
            if person != payer:
                debts.append({
                    "debtor": person,
                    "creditor": payer,
                    "amount": share
                })

    # Apply payments
    for payment in payments:
        payer = payment["payer"]
        receiver = payment["receiver"]
        amount = payment["amount"]

        for debt in debts:
            if (
                debt["debtor"] == payer
                and debt["creditor"] == receiver
            ):
                debt["amount"] -= amount
                break

    debts = [
        d for d in debts
        if d["amount"] > 0
    ]

    if not debts:
        await message.answer(
            "🎉 Everyone is settled up."
        )
        return

    text = "💰 Settlement\n\n"

    for debt in debts:
        text += (
            f"{debt['debtor']} → "
            f"{debt['creditor']} "
            f"Rp{debt['amount']:,}\n"
        )

    await message.answer(text)

@dp.message()
async def debug(message: Message):
    print(f"📩 {message.from_user.username}: {message.text}")


async def main():
    if not EXPENSES_FILE.exists():
        save_json(EXPENSES_FILE, [])

    if not PAYMENTS_FILE.exists():
        save_json(PAYMENTS_FILE, [])

    print("🍺 Tavern Tabkeeper is running...")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())