"""Measure separate-chaining search costs at several table load factors."""

import argparse
import csv
import random
from dataclasses import dataclass
from pathlib import Path

from src.hash_table import HashTable

CAPACITY = 4093
LOAD_FACTORS = tuple(step / 4 for step in range(1, 17))
DEFAULT_SEED = 2026


@dataclass(frozen=True)
class Measurement:
    target_load_factor: float
    load_factor: float
    item_count: int
    success_average: float
    success_theory: float
    failure_average: float
    failure_theory: float


def _random_urls(rng: random.Random, count: int, host: str) -> list[str]:
    return [
        f"https://{host}/url-{index}-{rng.getrandbits(128):032x}"
        for index in range(count)
    ]


def measure_load_factor(
    target_load_factor: float,
    urls: list[str],
    failed_urls: list[str],
) -> Measurement:
    """Measure successful and unsuccessful node comparisons for one load."""
    item_count = round(target_load_factor * CAPACITY)
    table: HashTable[int] = HashTable(capacity=CAPACITY, max_load=None)

    for index, url in enumerate(urls[:item_count]):
        table.put(url, index)

    successful_comparisons = 0
    for url in urls[:item_count]:
        found, _, comparisons = table.search(url)
        if not found:
            raise RuntimeError(f"inserted URL was not found: {url}")
        successful_comparisons += comparisons

    failed_comparisons = 0
    for url in failed_urls[:item_count]:
        found, _, comparisons = table.search(url)
        if found:
            raise RuntimeError(f"failure probe unexpectedly matched: {url}")
        failed_comparisons += comparisons

    load_factor = table.load_factor
    return Measurement(
        target_load_factor=target_load_factor,
        load_factor=load_factor,
        item_count=item_count,
        success_average=successful_comparisons / item_count,
        success_theory=1 + load_factor / 2,
        failure_average=failed_comparisons / item_count,
        failure_theory=load_factor,
    )


def run_experiment(seed: int = DEFAULT_SEED) -> list[Measurement]:
    """Run the experiment with deterministic random URLs for reproducibility."""
    rng = random.Random(seed)
    max_count = round(LOAD_FACTORS[-1] * CAPACITY)
    urls = _random_urls(rng, max_count, "example.com")
    failed_urls = _random_urls(rng, max_count, "not-present.example")

    return [
        measure_load_factor(target, urls, failed_urls)
        for target in LOAD_FACTORS
    ]


def write_csv(measurements: list[Measurement], path: Path) -> None:
    """Write measured averages and theoretical expectations as CSV."""
    fieldnames = (
        "target_load_factor",
        "load_factor",
        "items",
        "capacity",
        "success_average",
        "success_theory",
        "failure_average",
        "failure_theory",
    )
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for result in measurements:
            writer.writerow(
                {
                    "target_load_factor": f"{result.target_load_factor:.2f}",
                    "load_factor": f"{result.load_factor:.6f}",
                    "items": result.item_count,
                    "capacity": CAPACITY,
                    "success_average": f"{result.success_average:.6f}",
                    "success_theory": f"{result.success_theory:.6f}",
                    "failure_average": f"{result.failure_average:.6f}",
                    "failure_theory": f"{result.failure_theory:.6f}",
                }
            )


def write_svg(measurements: list[Measurement], path: Path) -> None:
    """Draw measured and theoretical search costs without external libraries."""
    width, height = 900, 560
    left, right, top, bottom = 78, 28, 54, 72
    chart_width = width - left - right
    chart_height = height - top - bottom
    max_alpha = max(result.load_factor for result in measurements)
    max_cost = max(result.failure_average for result in measurements)
    max_cost = max(5.0, max_cost * 1.15)

    def point(alpha: float, cost: float) -> tuple[float, float]:
        x = left + alpha / max_alpha * chart_width
        y = top + chart_height - cost / max_cost * chart_height
        return x, y

    def polyline(
        values: list[tuple[Measurement, float]],
        color: str,
        dashed: bool = False,
    ) -> str:
        points = " ".join(
            f"{point(result.load_factor, value)[0]:.2f},"
            f"{point(result.load_factor, value)[1]:.2f}"
            for result, value in values
        )
        dash = ' stroke-dasharray="7 5"' if dashed else ""
        return (
            f'<polyline points="{points}" fill="none" stroke="{color}" '
            f'stroke-width="2.5"{dash}/>'
        )

    def markers(values: list[tuple[Measurement, float]], color: str) -> str:
        circles = []
        for result, value in values:
            x, y = point(result.load_factor, value)
            circles.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.5" fill="{color}"/>'
            )
        return "\n".join(circles)

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">',
        "<title>Separate-chaining hash table search costs</title>",
        "<desc>Measured and theoretical average node comparisons by load factor.</desc>",
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="450" y="28" text-anchor="middle" font-size="18">'
        "Hash-table search cost vs. load factor</text>",
    ]

    for tick in range(6):
        cost = max_cost * tick / 5
        y = top + chart_height - chart_height * tick / 5
        svg.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{left + chart_width}" '
            f'y2="{y:.2f}" stroke="#dddddd"/>'
        )
        svg.append(
            f'<text x="{left - 12}" y="{y + 4:.2f}" text-anchor="end" '
            f'font-size="12">{cost:.1f}</text>'
        )

    svg.extend(
        [
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + chart_height}" '
            'stroke="#333333"/>',
            f'<line x1="{left}" y1="{top + chart_height}" '
            f'x2="{left + chart_width}" y2="{top + chart_height}" stroke="#333333"/>',
        ]
    )
    for tick in range(5):
        alpha = max_alpha * tick / 4
        x = left + chart_width * tick / 4
        svg.append(
            f'<text x="{x:.2f}" y="{top + chart_height + 22}" text-anchor="middle" '
            f'font-size="12">{alpha:.1f}</text>'
        )
    svg.extend(
        [
            f'<text x="{left + chart_width / 2:.2f}" y="{height - 20}" '
            'text-anchor="middle" font-size="14">Load factor (α)</text>',
            f'<text x="20" y="{top + chart_height / 2:.2f}" '
            f'transform="rotate(-90 20 {top + chart_height / 2:.2f})" '
            'text-anchor="middle" font-size="14">Average node comparisons</text>',
        ]
    )

    success_measured = [(result, result.success_average) for result in measurements]
    success_theory = [(result, result.success_theory) for result in measurements]
    failure_measured = [(result, result.failure_average) for result in measurements]
    failure_theory = [(result, result.failure_theory) for result in measurements]
    svg.extend(
        [
            polyline(success_measured, "#1769aa"),
            markers(success_measured, "#1769aa"),
            polyline(success_theory, "#1769aa", dashed=True),
            polyline(failure_measured, "#c43b32"),
            markers(failure_measured, "#c43b32"),
            polyline(failure_theory, "#c43b32", dashed=True),
        ]
    )

    legend = (
        ("Success measured", "#1769aa", False),
        ("Success theory: 1 + α/2", "#1769aa", True),
        ("Failure measured", "#c43b32", False),
        ("Failure theory: α", "#c43b32", True),
    )
    for index, (label, color, dashed) in enumerate(legend):
        x = left + (index % 2) * 365
        y = height - 48 + (index // 2) * 18
        dash = ' stroke-dasharray="7 5"' if dashed else ""
        svg.append(
            f'<line x1="{x}" y1="{y}" x2="{x + 30}" y2="{y}" stroke="{color}" '
            f'stroke-width="2.5"{dash}/>'
        )
        svg.append(
            f'<text x="{x + 38}" y="{y + 4}" font-size="12">{label}</text>'
        )
    svg.append("</svg>")
    path.write_text("\n".join(svg) + "\n", encoding="utf-8")


def print_table(measurements: list[Measurement]) -> None:
    """Print measured averages alongside their theoretical values."""
    print(
        " alpha | items | success measured | success theory | "
        "failure measured | failure theory"
    )
    for result in measurements:
        print(
            f" {result.load_factor:5.2f} | {result.item_count:5d} | "
            f"{result.success_average:16.4f} | {result.success_theory:14.4f} | "
            f"{result.failure_average:16.4f} | {result.failure_theory:14.4f}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    measurements = run_experiment(args.seed)
    output_directory = Path(__file__).resolve().parent
    csv_path = output_directory / "results.csv"
    svg_path = output_directory / "results.svg"
    write_csv(measurements, csv_path)
    write_svg(measurements, svg_path)
    print_table(measurements)
    print(f"\nWrote {csv_path} and {svg_path}")


if __name__ == "__main__":
    main()
