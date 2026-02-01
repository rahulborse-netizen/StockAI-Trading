from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# Set style
sns.set_style("whitegrid")
plt.rcParams["figure.figsize"] = (12, 6)


def plot_equity_curve(
    equity: pd.Series,
    benchmark: pd.Series | None = None,
    title: str = "Equity Curve",
    save_path: Path | None = None,
) -> None:
    """
    Plot equity curve with optional benchmark comparison.
    
    Args:
        equity: Strategy equity curve (normalized to start at 1.0)
        benchmark: Optional benchmark equity curve
        title: Plot title
        save_path: Optional path to save figure
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    
    ax.plot(equity.index, equity.values, label="Strategy", linewidth=2)
    
    if benchmark is not None:
        ax.plot(benchmark.index, benchmark.values, label="Benchmark", linewidth=2, alpha=0.7)
    
    ax.set_xlabel("Date")
    ax.set_ylabel("Equity (normalized)")
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close()
    else:
        plt.show()


def plot_drawdown(
    equity: pd.Series,
    title: str = "Drawdown",
    save_path: Path | None = None,
) -> None:
    """
    Plot drawdown chart.
    
    Args:
        equity: Strategy equity curve
        title: Plot title
        save_path: Optional path to save figure
    """
    peak = equity.cummax()
    drawdown = (equity / peak - 1.0) * 100.0  # Convert to percentage
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    ax.fill_between(drawdown.index, drawdown.values, 0, alpha=0.3, color="red")
    ax.plot(drawdown.index, drawdown.values, linewidth=1, color="darkred")
    
    ax.set_xlabel("Date")
    ax.set_ylabel("Drawdown (%)")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color="black", linestyle="--", linewidth=1)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close()
    else:
        plt.show()


def plot_returns_distribution(
    returns: pd.Series,
    title: str = "Returns Distribution",
    save_path: Path | None = None,
) -> None:
    """
    Plot histogram of returns distribution.
    
    Args:
        returns: Daily returns series
        title: Plot title
        save_path: Optional path to save figure
    """
    returns_clean = returns.dropna()
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ax.hist(returns_clean.values * 100.0, bins=50, alpha=0.7, edgecolor="black")
    ax.axvline(x=returns_clean.mean() * 100.0, color="red", linestyle="--", linewidth=2, label=f"Mean: {returns_clean.mean()*100:.2f}%")
    
    ax.set_xlabel("Daily Return (%)")
    ax.set_ylabel("Frequency")
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close()
    else:
        plt.show()


def plot_correlation_heatmap(
    equity_curves: dict[str, pd.Series],
    title: str = "Correlation Heatmap",
    save_path: Path | None = None,
) -> None:
    """
    Plot correlation heatmap for multiple equity curves.
    
    Args:
        equity_curves: Dictionary mapping names to equity curve series
        title: Plot title
        save_path: Optional path to save figure
    """
    # Align all series to common dates
    all_dates = set()
    for series in equity_curves.values():
        all_dates.update(series.index)
    all_dates = sorted(all_dates)
    
    # Create returns dataframe
    returns_df = pd.DataFrame(index=all_dates)
    for name, equity in equity_curves.items():
        returns_df[name] = equity.reindex(all_dates).pct_change(1)
    
    returns_df = returns_df.dropna()
    
    # Calculate correlation
    corr = returns_df.corr()
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0, square=True, ax=ax)
    
    ax.set_title(title)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close()
    else:
        plt.show()


def plot_performance_comparison(
    stats_dict: dict[str, dict],
    metrics: list[str] | None = None,
    title: str = "Performance Comparison",
    save_path: Path | None = None,
) -> None:
    """
    Plot bar chart comparing performance metrics across strategies/assets.
    
    Args:
        stats_dict: Dictionary mapping names to stats dictionaries
        metrics: List of metric names to plot (default: common metrics)
        title: Plot title
        save_path: Optional path to save figure
    """
    if metrics is None:
        metrics = ["total_return", "sharpe", "cagr", "max_drawdown"]
    
    # Extract metrics
    comparison_df = pd.DataFrame(index=list(stats_dict.keys()), columns=metrics)
    for name, stats in stats_dict.items():
        for metric in metrics:
            comparison_df.loc[name, metric] = stats.get(metric, 0.0)
    
    comparison_df = comparison_df.astype(float)
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()
    
    for idx, metric in enumerate(metrics):
        if idx < len(axes):
            ax = axes[idx]
            comparison_df[metric].plot(kind="bar", ax=ax)
            ax.set_title(metric.replace("_", " ").title())
            ax.set_ylabel(metric.replace("_", " ").title())
            ax.tick_params(axis="x", rotation=45)
            ax.grid(True, alpha=0.3)
    
    plt.suptitle(title, fontsize=14, y=1.02)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close()
    else:
        plt.show()


def generate_html_report(
    equity_curve: pd.Series,
    output_path: Path,
    benchmark_equity: pd.Series | None = None,
    stats: dict | None = None,
    returns: pd.Series | None = None,
    title: str = "Backtest Report",
) -> None:
    """
    Generate HTML report with all visualizations.
    
    Args:
        equity_curve: Strategy equity curve
        benchmark_equity: Optional benchmark equity curve
        stats: Optional stats dictionary
        returns: Optional returns series
        output_path: Path to save HTML file
        title: Report title
    """
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate plots
    plot_paths = {}
    
    equity_path = output_dir / "equity_curve.png"
    plot_equity_curve(equity_curve, benchmark_equity, title="Equity Curve", save_path=equity_path)
    plot_paths["equity"] = equity_path.name
    
    drawdown_path = output_dir / "drawdown.png"
    plot_drawdown(equity_curve, title="Drawdown", save_path=drawdown_path)
    plot_paths["drawdown"] = drawdown_path.name
    
    if returns is not None:
        returns_path = output_dir / "returns_distribution.png"
        plot_returns_distribution(returns, title="Returns Distribution", save_path=returns_path)
        plot_paths["returns"] = returns_path.name
    
    # Generate HTML
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; margin-top: 30px; }}
        img {{ max-width: 100%; height: auto; margin: 20px 0; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    
    <h2>Performance Statistics</h2>
    <table>
"""
    
    if stats:
        for key, value in stats.items():
            if isinstance(value, float):
                html_content += f"        <tr><th>{key.replace('_', ' ').title()}</th><td>{value:.4f}</td></tr>\n"
            else:
                html_content += f"        <tr><th>{key.replace('_', ' ').title()}</th><td>{value}</td></tr>\n"
    
    html_content += """
    </table>
    
    <h2>Equity Curve</h2>
    <img src="equity_curve.png" alt="Equity Curve">
    
    <h2>Drawdown</h2>
    <img src="drawdown.png" alt="Drawdown">
"""
    
    if returns is not None:
        html_content += """
    <h2>Returns Distribution</h2>
    <img src="returns_distribution.png" alt="Returns Distribution">
"""
    
    html_content += """
</body>
</html>
"""
    
    output_path.write_text(html_content)


def generate_backtest_report(
    result,
    outdir: Path,
    ticker: str | None = None,
    include_plots: bool = True,
) -> Path:
    """
    Generate comprehensive backtest report with visualizations.
    
    Args:
        result: BacktestResult object
        outdir: Output directory
        ticker: Optional ticker symbol for title
        include_plots: Whether to generate plots
        
    Returns:
        Path to generated HTML report
    """
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    
    title = f"Backtest Report - {ticker}" if ticker else "Backtest Report"
    
    # Generate plots if requested
    if include_plots:
        equity_path = outdir / "equity_curve.png"
        plot_equity_curve(
            result.equity_curve,
            result.benchmark_equity if hasattr(result, "benchmark_equity") else None,
            title="Equity Curve",
            save_path=equity_path,
        )
        
        drawdown_path = outdir / "drawdown.png"
        plot_drawdown(result.equity_curve, title="Drawdown", save_path=drawdown_path)
        
        if hasattr(result, "daily_returns") and result.daily_returns is not None:
            returns_path = outdir / "returns_distribution.png"
            plot_returns_distribution(
                result.daily_returns,
                title="Returns Distribution",
                save_path=returns_path,
            )
    
    # Generate HTML report
    report_path = outdir / "report.html"
    generate_html_report(
        equity_curve=result.equity_curve,
        benchmark_equity=result.benchmark_equity if hasattr(result, "benchmark_equity") else None,
        stats=result.stats if hasattr(result, "stats") else None,
        returns=result.daily_returns if hasattr(result, "daily_returns") else None,
        output_path=report_path,
        title=title,
    )
    
    return report_path
