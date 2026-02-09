"""
StockAI Trading Dashboard - View backtest results and trading signals.
Run: python -m src.dashboard_app
Then open http://127.0.0.1:5000
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from flask import Flask, abort, render_template_string, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Default outputs directory (relative to project root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"


def _get_outputs_dir() -> Path:
    """Resolve outputs directory from env or default."""
    import os
    return Path(os.environ.get("STOCKAI_OUTPUTS", str(OUTPUTS_DIR)))


def _discover_runs() -> list[dict]:
    """Find all backtest runs (directories with predictions.csv + equity_curve.csv)."""
    base = _get_outputs_dir()
    if not base.exists():
        return []
    runs = []
    seen = set()

    def add_run(path: Path) -> None:
        pred_path = path / "predictions.csv"
        equity_path = path / "equity_curve.csv"
        stats_path = path / "stats.json"
        if pred_path.exists() and equity_path.exists():
            # Use relative path from base as display name
            try:
                rel = path.relative_to(base)
                name = str(rel).replace("\\", "/")
            except ValueError:
                name = path.name
            if name in seen:
                return
            seen.add(name)
            ticker = "Unknown"
            for p in path.glob("*.NS.csv"):
                ticker = p.stem.replace(".csv", "")
                break
            for p in path.glob("*.BO.csv"):
                ticker = p.stem.replace(".csv", "")
                break
            runs.append({
                "name": name,
                "ticker": ticker,
                "path": str(path),
                "has_stats": stats_path.exists(),
            })

    for path in sorted(base.iterdir()):
        if path.is_dir():
            add_run(path)
            # Also check subdirs (e.g. outputs/batch/RELIANCE.NS/)
            for sub in sorted(path.iterdir()):
                if sub.is_dir():
                    add_run(sub)
    return sorted(runs, key=lambda r: r["name"])


def _load_run_data(run_name: str) -> dict | None:
    """Load predictions, equity, stats for a run. Returns None if invalid."""
    base = _get_outputs_dir()
    # Support both "reliance" and "batch/RELIANCE.NS" style names
    run_path = (base / run_name).resolve()
    if not run_path.is_relative_to(base.resolve()):
        return None
    pred_path = run_path / "predictions.csv"
    equity_path = run_path / "equity_curve.csv"
    bench_path = run_path / "benchmark_equity_curve.csv"
    stats_path = run_path / "stats.json"
    if not pred_path.exists() or not equity_path.exists():
        return None

    predictions = pd.read_csv(pred_path, index_col=0, parse_dates=True)
    predictions.index = pd.to_datetime(predictions.index)
    equity = pd.read_csv(equity_path, index_col=0, parse_dates=True)
    equity.index = pd.to_datetime(equity.index)
    benchmark = None
    if bench_path.exists():
        benchmark = pd.read_csv(bench_path, index_col=0, parse_dates=True)
        benchmark.index = pd.to_datetime(benchmark.index)
    stats = {}
    if stats_path.exists():
        stats = json.loads(stats_path.read_text())

    prob_threshold = stats.get("prob_threshold", 0.55)

    # Derive signals: BUY if prob_up >= threshold, else CASH
    pred = predictions.copy()
    pred["signal"] = pred["prob_up"].apply(
        lambda x: "BUY" if pd.notna(x) and x >= prob_threshold else "CASH"
    )

    # Build signals table (last N rows for display, full for export)
    signals_df = pred[["prob_up", "y_true", "signal"]].dropna(subset=["prob_up"])
    signals_df = signals_df.rename(columns={"prob_up": "prob_up", "y_true": "actual", "signal": "signal"})
    signals_df.index = signals_df.index.strftime("%Y-%m-%d")
    signals_list = signals_df.tail(500).iloc[::-1].to_dict(orient="index")
    signals_list = [{"date": k, **v} for k, v in signals_list.items()]

    # Equity data for chart
    equity_dates = equity.index.strftime("%Y-%m-%d").tolist()
    equity_values = equity["equity"].tolist()
    bench_dates = benchmark.index.strftime("%Y-%m-%d").tolist() if benchmark is not None else []
    bench_values = benchmark["equity"].tolist() if benchmark is not None else []

    return {
        "name": run_name,
        "stats": stats,
        "signals": signals_list,
        "signals_count": len(signals_list),
        "equity": {"dates": equity_dates, "values": equity_values},
        "benchmark": {"dates": bench_dates, "values": bench_values} if benchmark is not None else None,
        "prob_threshold": prob_threshold,
    }


INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StockAI Trading Dashboard</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: 'Segoe UI', system-ui, sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }
        .header { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 1.5rem 2rem; border-bottom: 1px solid #334155; }
        .header h1 { margin: 0; font-size: 1.5rem; }
        .header p { margin: 0.5rem 0 0; color: #94a3b8; font-size: 0.9rem; }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        .runs-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; }
        .run-card { background: #1e293b; border-radius: 12px; padding: 1.25rem; border: 1px solid #334155; transition: all 0.2s; }
        .run-card:hover { border-color: #64748b; transform: translateY(-2px); }
        .run-card a { text-decoration: none; color: inherit; display: block; }
        .run-card h3 { margin: 0 0 0.5rem; font-size: 1.1rem; }
        .run-card .meta { color: #94a3b8; font-size: 0.85rem; }
        .empty { text-align: center; padding: 4rem 2rem; color: #64748b; }
        .empty code { background: #1e293b; padding: 0.2rem 0.5rem; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>StockAI Trading Dashboard</h1>
        <p>Select a backtest run to view trading signals and performance</p>
    </div>
    <div class="container">
        {% if runs %}
        <div class="runs-grid">
            {% for r in runs %}
            <div class="run-card">
                <a href="/run/{{ r.name }}">
                    <h3>{{ r.name }}</h3>
                    <div class="meta">Ticker: {{ r.ticker }} • Has stats: {{ 'Yes' if r.has_stats else 'No' }}</div>
                </a>
            </div>
            {% endfor %}
        </div>
        {% else %}
        <div class="empty">
            <p>No backtest runs found.</p>
            <p>Run a research backtest first: <code>python -m src.cli research --ticker RELIANCE.NS --start 2020-01-01 --end 2025-01-01 --outdir outputs/reliance</code></p>
            <p>Outputs directory: <code>{{ outputs_dir }}</code></p>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ name }} - StockAI Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { box-sizing: border-box; }
        body { font-family: 'Segoe UI', system-ui, sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }
        .header { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 1rem 2rem; border-bottom: 1px solid #334155; display: flex; align-items: center; gap: 1rem; }
        .header a { color: #38bdf8; text-decoration: none; }
        .header a:hover { text-decoration: underline; }
        .header h1 { margin: 0; font-size: 1.25rem; }
        .container { max-width: 1400px; margin: 0 auto; padding: 2rem; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
        .stat-card { background: #1e293b; border-radius: 8px; padding: 1rem; border: 1px solid #334155; }
        .stat-card .label { font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; }
        .stat-card .value { font-size: 1.25rem; font-weight: 600; margin-top: 0.25rem; }
        .stat-card .value.positive { color: #4ade80; }
        .stat-card .value.negative { color: #f87171; }
        .section { margin-bottom: 2rem; }
        .section h2 { font-size: 1rem; margin-bottom: 1rem; color: #94a3b8; }
        .chart-wrap { background: #1e293b; border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem; border: 1px solid #334155; height: 360px; }
        .signals-table-wrap { overflow-x: auto; max-height: 400px; overflow-y: auto; background: #1e293b; border-radius: 12px; border: 1px solid #334155; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 0.6rem 1rem; text-align: left; border-bottom: 1px solid #334155; }
        th { background: #0f172a; color: #94a3b8; font-size: 0.8rem; text-transform: uppercase; position: sticky; top: 0; }
        tr:hover { background: #33415533; }
        .sig-BUY { color: #4ade80; font-weight: 600; }
        .sig-CASH { color: #94a3b8; }
        .controls { display: flex; gap: 0.5rem; margin-bottom: 1rem; }
        .btn { padding: 0.5rem 1rem; border-radius: 6px; border: none; cursor: pointer; font-size: 0.9rem; background: #334155; color: #e2e8f0; }
        .btn:hover { background: #475569; }
        .btn-primary { background: #38bdf8; color: #0f172a; }
        .btn-primary:hover { background: #7dd3fc; }
    </style>
</head>
<body>
    <div class="header">
        <a href="/">← Back</a>
        <h1>{{ name }}</h1>
    </div>
    <div class="container">
        <div class="section">
            <h2>Performance Statistics</h2>
            <div class="stats-grid">
                {% for k, v in stats.items() %}
                <div class="stat-card">
                    <div class="label">{{ k.replace('_', ' ').title() }}</div>
                    <div class="value {% if v is number and v > 0 and ('return' in k or 'cagr' in k or 'sharpe' in k) %}positive{% elif v is number and v < 0 %}negative{% endif %}">
                        {% if v is number %}
                            {% if 'sharpe' in k %}{{ "%.2f"|format(v) }}{% elif 'return' in k or 'cagr' in k or 'drawdown' in k %}{{ "%.2f"|format(v * 100) }}%{% elif 'prob_threshold' in k or 'fee_bps' in k %}{{ v }}{% elif v == int(v) %}{{ int(v) }}{% else %}{{ "%.4f"|format(v) }}{% endif %}
                        {% else %}
                        {{ v }}
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        <div class="section">
            <h2>Equity Curve</h2>
            <div class="chart-wrap">
                <canvas id="equityChart"></canvas>
            </div>
        </div>

        <div class="section">
            <h2>Trading Signals (last {{ signals_count }} days)</h2>
            <div class="controls">
                <button class="btn btn-primary" onclick="exportSignals()">Export CSV</button>
            </div>
            <div class="signals-table-wrap">
                <table>
                    <thead>
                        <tr><th>Date</th><th>Signal</th><th>Prob Up</th><th>Actual</th></tr>
                    </thead>
                    <tbody>
                        {% for s in signals %}
                        <tr>
                            <td>{{ s.date }}</td>
                            <td class="sig-{{ s.signal }}">{{ s.signal }}</td>
                            <td>{{ "%.2f"|format(s.prob_up) if s.prob_up is not none else '-' }}</td>
                            <td>{{ 'Up' if s.actual == 1 else 'Down' }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        const equityData = {{ equity_json | safe }};
        const benchmarkData = {{ benchmark_json | safe }};
        const ctx = document.getElementById('equityChart').getContext('2d');
        const datasets = [
            { label: 'Strategy', data: equityData.values.map((v, i) => ({ x: equityData.dates[i], y: v })), borderColor: '#38bdf8', backgroundColor: 'rgba(56, 189, 248, 0.1)', fill: true, tension: 0.2 },
        ];
        if (benchmarkData && benchmarkData.dates && benchmarkData.dates.length) {
            datasets.push({ label: 'Benchmark', data: benchmarkData.values.map((v, i) => ({ x: benchmarkData.dates[i], y: v })), borderColor: '#94a3b8', backgroundColor: 'rgba(148, 163, 184, 0.05)', fill: true, tension: 0.2 });
        }
        new Chart(ctx, {
            type: 'line',
            data: { datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { labels: { color: '#e2e8f0' } } },
                scales: {
                    x: { type: 'category', ticks: { color: '#94a3b8', maxTicksLimit: 12 } },
                    y: { ticks: { color: '#94a3b8' }, grid: { color: '#334155' } }
                }
            }
        });
        const signalsData = {{ signals_json | safe }};
        function exportSignals() {
            const headers = ['Date','Signal','Prob Up','Actual'];
            const rows = signalsData.map(s => [s.date, s.signal, s.prob_up != null ? s.prob_up.toFixed(4) : '', s.actual === 1 ? 'Up' : 'Down']);
            const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\\n');
            const a = document.createElement('a');
            a.href = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv);
            a.download = 'signals_{{ name }}.csv';
            a.click();
        }
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    runs = _discover_runs()
    return render_template_string(
        INDEX_HTML,
        runs=runs,
        outputs_dir=str(_get_outputs_dir()),
    )


@app.route("/run/<path:run_name>")
def run_dashboard(run_name: str):
    data = _load_run_data(run_name)
    if data is None:
        abort(404, f"Run '{run_name}' not found or invalid.")
    equity_json = json.dumps(data["equity"])
    benchmark_json = json.dumps(data["benchmark"] if data["benchmark"] else {})
    signals_json = json.dumps(data["signals"])
    return render_template_string(
        DASHBOARD_HTML,
        name=data["name"],
        stats=data["stats"],
        signals=data["signals"],
        signals_count=data["signals_count"],
        equity_json=equity_json,
        benchmark_json=benchmark_json,
        signals_json=signals_json,
    )


@app.route("/api/runs")
def api_runs():
    return {"runs": _discover_runs()}


@app.route("/api/run/<path:run_name>")
def api_run(run_name: str):
    data = _load_run_data(run_name)
    if data is None:
        abort(404)
    return data


@app.route("/static/<path:filename>")
def serve_static(filename: str):
    static_dir = PROJECT_ROOT / "static"
    if static_dir.exists():
        return send_from_directory(static_dir, filename)
    abort(404)


def main():
    import os
    port = int(os.environ.get("PORT", 5000))
    print(f"StockAI Dashboard: http://127.0.0.1:{port}")
    print(f"Outputs directory: {_get_outputs_dir()}")
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
