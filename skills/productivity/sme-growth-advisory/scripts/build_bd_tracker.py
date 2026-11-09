#!/usr/bin/env python3
"""Generate the SME growth "BD tracker" workbook skeleton (openpyxl).

Usage:
    python3 build_bd_tracker.py /home/ubuntu/BD_Tracker.xlsx "HMW Air Controls"

Creates the sheets that have worked in practice, with header styling, column
widths, wrap text and frozen header rows. Add data rows afterwards (openpyxl
load_workbook) or let the owner fill them in by hand.

Install on a PEP-668 host:
    python3 -m pip install --break-system-packages openpyxl
"""
import sys

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

HDR_FILL = PatternFill("solid", fgColor="1F3864")
HDR_FONT = Font(bold=True, color="FFFFFF", size=11)
TITLE_FONT = Font(bold=True, size=14, color="1F3864")
THIN = Side(style="thin", color="B4C6E7")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def make_sheet(wb, title, headers, widths, first=False):
    ws = wb.active if first else wb.create_sheet()
    ws.title = title
    for col, (head, width) in enumerate(zip(headers, widths), start=1):
        cell = ws.cell(row=1, column=col, value=head)
        cell.fill, cell.font, cell.border = HDR_FILL, HDR_FONT, BORDER
        cell.alignment = Alignment(vertical="center", horizontal="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(col)].width = width
    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 30
    return ws


SHEETS = [
    ("START HERE", ["Step", "Kaam", "Kab", "Status"], [8, 62, 20, 14]),
    ("1. Purane Clients", ["Client", "Kya Bechein (upsell)", "Kya Maangein (document)", "Last contact", "Status"],
     [26, 42, 34, 16, 14]),
    ("2. Target Buyers", ["Company / Site", "Category", "Pitch (1 line)", "Kaise pahunchein", "Status"],
     [30, 18, 44, 34, 14]),
    ("3. Tender Tracker", ["Portal", "Kaam / Tender", "Buyer", "Value", "Last date", "Status"],
     [34, 42, 26, 14, 16, 14]),
    ("4. Kaagzaat aur Shabd", ["Term / Document", "Aasan Matlab", "Kahan se milega"], [26, 56, 34]),
    ("5. 30 Din Ka Plan", ["Hafta", "Target", "Kaam", "Done?"], [10, 40, 56, 10]),
    ("6. Competitors", ["Company", "Type", "Taqat", "Kamzori", "Sabak", "Hum kaise jeetenge"],
     [26, 20, 38, 38, 40, 40]),
    ("7. Copy Karo (Plan)", ["Baat", "Kaun karta hai", "Hum kya karein", "Kab tak", "Proof"], [26, 26, 46, 14, 24]),
]

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "BD_Tracker.xlsx"
    business = sys.argv[2] if len(sys.argv) > 2 else "Business"
    wb = Workbook()
    for i, (title, headers, widths) in enumerate(SHEETS):
        make_sheet(wb, title, headers, widths, first=(i == 0))
    ws = wb["START HERE"]
    ws["A1"] = "Step"
    ws.insert_rows(1)
    ws["A1"] = f"{business} — kaam laane ka plan (tracker)"
    ws["A1"].font = TITLE_FONT

    wb.save(out)

    # Verify (always re-open before sending the file to the user).
    check = __import__("openpyxl").load_workbook(out)
    print("saved:", out)
    for s in check.worksheets:
        print(f"  {s.title}: {s.max_row} rows x {s.max_column} cols")
