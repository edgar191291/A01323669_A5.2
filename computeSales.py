#!/usr/bin/env python3
"""
computeSales.py

Usage:
    python computeSales.py priceCatalogue.json salesRecord.json

Computes the total cost of all sales items using a price catalogue.
Prints results to console and writes them to SalesResults.txt.
Continues execution even if invalid data is found.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


RESULTS_FILENAME = "SalesResults.txt"


@dataclass(frozen=True)
class SaleLine:
    """Represents a single item line within a sale record."""
    product: str
    quantity: float


def print_error(message: str) -> None:
    """Print an error message to stderr."""
    print(f"ERROR: {message}", file=sys.stderr)


def load_json_file(file_path: str) -> Any:
    """Load and parse a JSON file returning its Python object."""
    path = Path(file_path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {file_path}: {exc}") from exc


def parse_catalogue(catalogue_data: Any) -> dict[str, float]:
    """
    Parse price catalogue JSON data into a dict: {product_name: price}.
    Invalid entries are skipped but reported.
    """
    prices: dict[str, float] = {}

    if not isinstance(catalogue_data, list):
        raise ValueError("Price catalogue JSON must be a list of products.")

    for idx, item in enumerate(catalogue_data, start=1):
        if not isinstance(item, dict):
            print_error(f"Catalogue item #{idx} is not an object. Skipped.")
            continue

        title = item.get("title")
        price = item.get("price")

        if not isinstance(title, str) or not title.strip():
            print_error(f"Catalogue item #{idx} has invalid 'title'. Skipped.")
            continue

        try:
            price_value = float(price)
        except (TypeError, ValueError):
            print_error(f"Catalogue item #{idx} has invalid 'price'. Skipped.")
            continue

        prices[title] = price_value

    return prices


def safe_sale_lines(sales_data: Any) -> list[SaleLine]:
    """
    Parse sales JSON into a flat list of SaleLine(product, quantity).
    Supports either:
      - a list of dicts with keys 'Product'/'Quantity'
      - a list of sales, each containing a list under keys like 'items'
    Any invalid line is reported and skipped.
    """
    if not isinstance(sales_data, list):
        raise ValueError("Sales record JSON must be a list.")

    lines: list[SaleLine] = []

    def parse_line(obj: Any, line_no: str) -> None:
        if not isinstance(obj, dict):
            print_error(f"Sale line {line_no} is not an object. Skipped.")
            return

        product = obj.get("Product")
        quantity = obj.get("Quantity")

        if not isinstance(product, str) or not product.strip():
            print_error(f"Sale line {line_no} has invalid 'Product'. Skipped.")
            return

        try:
            qty_value = float(quantity)
        except (TypeError, ValueError):
            print_error(f"Sale line {line_no} has invalid 'Quantity'. Skipped.")
            return

        lines.append(SaleLine(product=product, quantity=qty_value))

    # Try to detect a "flat list of lines"
    is_flat = all(isinstance(x, dict) and "Product" in x and "Quantity" in x for x in sales_data)

    if is_flat:
        for i, obj in enumerate(sales_data, start=1):
            parse_line(obj, str(i))
        return lines

    # Otherwise, attempt nested structure: list of sales, each with iterable of items
    for sale_idx, sale_obj in enumerate(sales_data, start=1):
        if isinstance(sale_obj, dict):
            items = (
                sale_obj.get("items")
                or sale_obj.get("Items")
                or sale_obj.get("sale")
                or sale_obj.get("Sale")
            )
            if isinstance(items, list):
                for item_idx, item in enumerate(items, start=1):
                    parse_line(item, f"{sale_idx}.{item_idx}")
                continue

        print_error(f"Sale #{sale_idx} has unexpected structure. Skipped.")

    return lines


def compute_total(prices: dict[str, float], lines: list[SaleLine]) -> float:
    """Compute total cost using catalogue prices; missing products are reported."""
    total = 0.0
    for idx, line in enumerate(lines, start=1):
        if line.product not in prices:
            print_error(f"Unknown product in sale line #{idx}: '{line.product}'. Skipped.")
            continue

        total += prices[line.product] * line.quantity

    return total


def format_results(total: float, elapsed_seconds: float) -> str:
    """Create a human-readable results string."""
    return (
        "SALES RESULTS\n"
        "-------------------------\n"
        f"TOTAL: {total:.2f}\n"
        f"TIME ELAPSED (SECONDS): {elapsed_seconds:.6f}\n"
    )


def main(argv: list[str]) -> int:
    start = time.perf_counter()

    if len(argv) != 3:
        print_error(
            "Invalid arguments.\n"
            "Usage: python computeSales.py priceCatalogue.json salesRecord.json"
        )
        return 2

    catalogue_path = argv[1]
    sales_path = argv[2]

    try:
        catalogue_data = load_json_file(catalogue_path)
        sales_data = load_json_file(sales_path)

        prices = parse_catalogue(catalogue_data)
        lines = safe_sale_lines(sales_data)

        total = compute_total(prices, lines)

    except (FileNotFoundError, ValueError) as exc:
        print_error(str(exc))
        return 1
    finally:
        elapsed = time.perf_counter() - start

    output = format_results(total, elapsed)

    print(output)

    try:
        Path(RESULTS_FILENAME).write_text(output, encoding="utf-8")
    except OSError as exc:
        print_error(f"Could not write results file '{RESULTS_FILENAME}': {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
