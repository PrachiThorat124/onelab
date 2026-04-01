import os
import argparse
import pandas as pd
from AI import generate_transactions_dataset, generate_settlements_dataset, ReconciliationEngine


def ensure_output_dir(path: str):
    os.makedirs(path, exist_ok=True)


def export_all(output_dir: str, seed: int = 42):
    ensure_output_dir(output_dir)

    transactions_df = generate_transactions_dataset(seed=seed)
    settlements_df = generate_settlements_dataset(seed=seed)

    engine = ReconciliationEngine(transactions_df, settlements_df)
    engine.reconcile()

    # Write CSVs
    transactions_df.to_csv(os.path.join(output_dir, "transactions.csv"), index=False)
    settlements_df.to_csv(os.path.join(output_dir, "settlements.csv"), index=False)

    matched_df = pd.DataFrame(engine.matched_pairs)
    matched_df.to_csv(os.path.join(output_dir, "matched_pairs.csv"), index=False)

    unmatched_df = pd.DataFrame(engine.unmatched_transactions)
    unmatched_df.to_csv(os.path.join(output_dir, "unmatched_transactions.csv"), index=False)

    extra_settlements_df = pd.DataFrame(engine.extra_settlements)
    extra_settlements_df.to_csv(os.path.join(output_dir, "extra_settlements.csv"), index=False)

    dup_tx_df = pd.DataFrame(engine.duplicates.get('transactions', []))
    dup_st_df = pd.DataFrame(engine.duplicates.get('settlements', []))
    dup_tx_df.to_csv(os.path.join(output_dir, "duplicate_transactions.csv"), index=False)
    dup_st_df.to_csv(os.path.join(output_dir, "duplicate_settlements.csv"), index=False)

    summary_df = engine.get_summary()
    summary_df.to_csv(os.path.join(output_dir, "summary.csv"), index=False)

    # Save human-readable summary
    with open(os.path.join(output_dir, "summary.txt"), "w", encoding="utf-8") as f:
        total_txns = len(transactions_df[transactions_df['status'].isin(['completed', 'settled'])])
        matched = len(engine.matched_pairs)
        unmatched = len(engine.unmatched_transactions)
        extras = len(engine.extra_settlements)
        f.write(f"Valid Transactions (excluded failed): {total_txns}\n")
        f.write(f"Successfully Matched: {matched}\n")
        f.write(f"Unmatched: {unmatched}\n")
        f.write(f"Extra Settlements: {extras}\n")

    # Optionally return paths
    return {
        'transactions': os.path.join(output_dir, "transactions.csv"),
        'settlements': os.path.join(output_dir, "settlements.csv"),
        'matched': os.path.join(output_dir, "matched_pairs.csv"),
        'summary': os.path.join(output_dir, "summary.csv"),
        'summary_txt': os.path.join(output_dir, "summary.txt")
    }


def main():
    parser = argparse.ArgumentParser(description="Export reconciliation CSVs and summary")
    parser.add_argument("--output", "-o", default="output", help="Output folder to write CSVs and images")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for synthetic data generation")
    args = parser.parse_args()

    paths = export_all(args.output, seed=args.seed)
    print("Exported files to:")
    for k, v in paths.items():
        print(f"  {k}: {v}")


if __name__ == '__main__':
    main()
