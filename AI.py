"""
AI Assessment: Payments Platform vs Bank Settlement Reconciliation
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Tuple, Dict, List
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


ASSUMPTIONS = """
RECONCILIATION ASSUMPTIONS:
===========================

1. MATCHING LOGIC:
   - Primary match: transaction_id
   - Secondary match: (amount, date) for transactions with missing IDs
   - Match is case-insensitive and whitespace-tolerant

2. TIME WINDOW:
   - Settlements should occur within 2 business days (5 calendar days)
   - Settlements can occur on weekends (banks don't always follow business days)
   - We accept settlements up to 5 days after transaction date

3. ROUNDING TOLERANCE:
   - Allow ±0.01 difference (covers floating-point arithmetic)
   - This is standard for payment systems handling cents

4. DUPLICATE HANDLING:
   - If 2+ transactions have identical (id, amount, date): FLAG as duplicate
   - If 2+ settlements match 1 transaction: FLAG as potential settlement duplicate
   - We report duplicates but do NOT auto-deduplicate

5. REFUND HANDLING:
   - Refunds are identified by negative amounts
   - A refund must have a matching original transaction (positive amount)
   - Original transaction can be from a prior month

6. EXCLUSIONS:
   - Transactions with status='failed' are excluded from reconciliation
   - We only match 'completed' or 'settled' transactions

7. CURRENCY:
   - Assumed all amounts in same currency (USD)
   - No currency conversion applied
"""


def generate_transactions_dataset(seed: int = 42) -> pd.DataFrame:
    np.random.seed(seed)
    base_date = datetime(2026, 3, 1)
    
    transactions = [
        {
            'transaction_id': 'TXN001',
            'amount': 100.00,
            'date': base_date + timedelta(days=0),
            'timestamp': base_date + timedelta(days=0, hours=10, minutes=30),
            'status': 'completed',
            'description': 'Normal transaction 1'
        },
        {
            'transaction_id': 'TXN002',
            'amount': 250.50,
            'date': base_date + timedelta(days=1),
            'timestamp': base_date + timedelta(days=1, hours=14, minutes=15),
            'status': 'completed',
            'description': 'Normal transaction 2'
        },
        {
            'transaction_id': 'TXN003',
            'amount': 75.25,
            'date': base_date + timedelta(days=2),
            'timestamp': base_date + timedelta(days=2, hours=9, minutes=45),
            'status': 'completed',
            'description': 'Normal transaction 3'
        },
        {
            'transaction_id': 'TXN004',
            'amount': 512.89,
            'date': base_date + timedelta(days=3),
            'timestamp': base_date + timedelta(days=3, hours=11, minutes=0),
            'status': 'completed',
            'description': 'Normal transaction 4'
        },
        {
            'transaction_id': 'TXN005',
            'amount': 1234.56,
            'date': base_date + timedelta(days=4),
            'timestamp': base_date + timedelta(days=4, hours=16, minutes=20),
            'status': 'completed',
            'description': 'Normal transaction 5'
        },
        {
            'transaction_id': 'TXN006',
            'amount': 350.00,
            'date': base_date + timedelta(days=28),
            'timestamp': base_date + timedelta(days=28, hours=15, minutes=30),
            'status': 'completed',
            'description': 'Late settlement - settles in April'
        },
        {
            'transaction_id': 'TXN007',
            'amount': 100.005,
            'date': base_date + timedelta(days=5),
            'timestamp': base_date + timedelta(days=5, hours=12, minutes=0),
            'status': 'completed',
            'description': 'Rounding mismatch - stored with 3 decimals'
        },
        {
            'transaction_id': 'TXN008',
            'amount': 199.99,
            'date': base_date + timedelta(days=6),
            'timestamp': base_date + timedelta(days=6, hours=10, minutes=30),
            'status': 'completed',
            'description': 'Duplicate entry 1'
        },
        {
            'transaction_id': 'TXN008',
            'amount': 199.99,
            'date': base_date + timedelta(days=6),
            'timestamp': base_date + timedelta(days=6, hours=10, minutes=31),
            'status': 'completed',
            'description': 'Duplicate entry 2'
        },
        {
            'transaction_id': 'TXN009',
            'amount': 50.00,
            'date': base_date + timedelta(days=7),
            'timestamp': base_date + timedelta(days=7, hours=13, minutes=0),
            'status': 'failed',
            'description': 'Failed transaction - should be ignored'
        },
        {
            'transaction_id': 'TXN010',
            'amount': -75.00,
            'date': base_date + timedelta(days=8),
            'timestamp': base_date + timedelta(days=8, hours=14, minutes=0),
            'status': 'completed',
            'description': 'Refund with no matching original'
        },
        {
            'transaction_id': 'TXN011',
            'amount': 500.00,
            'date': base_date + timedelta(days=9),
            'timestamp': base_date + timedelta(days=9, hours=10, minutes=0),
            'status': 'completed',
            'description': 'Transaction for date-amount matching test'
        },
        {
            'transaction_id': 'TXN012',
            'amount': 88.88,
            'date': base_date + timedelta(days=10),
            'timestamp': base_date + timedelta(days=10, hours=11, minutes=30),
            'status': 'completed',
            'description': 'Normal transaction 6'
        },
        {
            'transaction_id': 'TXN013',
            'amount': 123.45,
            'date': base_date + timedelta(days=11),
            'timestamp': base_date + timedelta(days=11, hours=15, minutes=45),
            'status': 'completed',
            'description': 'Normal transaction 7'
        },
    ]
    
    df = pd.DataFrame(transactions)
    return df


def generate_settlements_dataset(seed: int = 42) -> pd.DataFrame:
    np.random.seed(seed)
    base_date = datetime(2026, 3, 1)
    
    settlements = [
        {
            'transaction_id': 'TXN001',
            'amount': 100.00,
            'settlement_date': base_date + timedelta(days=1),
            'settlement_batch': 'BATCH_20260302_001',
            'description': 'Settlement for TXN001'
        },
        {
            'transaction_id': 'TXN002',
            'amount': 250.50,
            'settlement_date': base_date + timedelta(days=3),
            'settlement_batch': 'BATCH_20260304_001',
            'description': 'Settlement for TXN002'
        },
        {
            'transaction_id': 'TXN003',
            'amount': 75.25,
            'settlement_date': base_date + timedelta(days=4),
            'settlement_batch': 'BATCH_20260305_001',
            'description': 'Settlement for TXN003'
        },
        {
            'transaction_id': 'TXN004',
            'amount': 512.89,
            'settlement_date': base_date + timedelta(days=5),
            'settlement_batch': 'BATCH_20260306_001',
            'description': 'Settlement for TXN004'
        },
        {
            'transaction_id': 'TXN005',
            'amount': 1234.56,
            'settlement_date': base_date + timedelta(days=6),
            'settlement_batch': 'BATCH_20260307_001',
            'description': 'Settlement for TXN005'
        },
        {
            'transaction_id': 'TXN006',
            'amount': 350.00,
            'settlement_date': base_date + timedelta(days=33),
            'settlement_batch': 'BATCH_20260402_001',
            'description': 'Late settlement for TXN006 in April'
        },
        {
            'transaction_id': 'TXN007',
            'amount': 100.01,
            'settlement_date': base_date + timedelta(days=7),
            'settlement_batch': 'BATCH_20260308_001',
            'description': 'Settlement for TXN007 (rounded)'
        },
        {
            'transaction_id': 'TXN008',
            'amount': 199.99,
            'settlement_date': base_date + timedelta(days=8),
            'settlement_batch': 'BATCH_20260309_001',
            'description': 'Settlement for TXN008 (one settlement for duplicate)'
        },
        {
            'transaction_id': 'TXN010',
            'amount': -75.00,
            'settlement_date': base_date + timedelta(days=9),
            'settlement_batch': 'BATCH_20260310_001',
            'description': 'Refund settlement for TXN010'
        },
        {
            'transaction_id': 'TXN011',
            'amount': 500.00,
            'settlement_date': base_date + timedelta(days=11),
            'settlement_batch': 'BATCH_20260312_001',
            'description': 'Settlement for TXN011'
        },
        {
            'transaction_id': 'TXN012',
            'amount': 88.88,
            'settlement_date': base_date + timedelta(days=12),
            'settlement_batch': 'BATCH_20260313_001',
            'description': 'Settlement for TXN012'
        },
        {
            'transaction_id': 'TXN013',
            'amount': 123.45,
            'settlement_date': base_date + timedelta(days=13),
            'settlement_batch': 'BATCH_20260314_001',
            'description': 'Settlement for TXN013'
        },
        {
            'transaction_id': 'TXN999',
            'amount': 999.99,
            'settlement_date': base_date + timedelta(days=14),
            'settlement_batch': 'BATCH_20260315_001',
            'description': 'Mystery settlement - no matching transaction'
        },
    ]
    
    df = pd.DataFrame(settlements)
    return df


class ReconciliationEngine:
    
    def __init__(
        self,
        transactions: pd.DataFrame,
        settlements: pd.DataFrame,
        rounding_tolerance: float = 0.01,
        settlement_time_window_days: int = 5
    ):
        self.transactions = transactions.copy()
        self.settlements = settlements.copy()
        self.rounding_tolerance = rounding_tolerance
        self.settlement_time_window_days = settlement_time_window_days
        
        self.mismatches = []
        self.matched_pairs = []
        self.unmatched_transactions = []
        self.extra_settlements = []
        self.duplicates = {'transactions': [], 'settlements': []}
        
        logger.info(f"Reconciliation engine initialized")
        logger.info(f"  Transactions: {len(self.transactions)} records")
        logger.info(f"  Settlements: {len(self.settlements)} records")
    
    def detect_duplicates(self) -> None:
        logger.info("Detecting duplicates...")
        
        txn_duplicates = self.transactions.groupby(
            ['transaction_id', 'amount', 'date']
        ).size()
        txn_duplicates = txn_duplicates[txn_duplicates > 1].reset_index(name='count')
        
        if len(txn_duplicates) > 0:
            self.duplicates['transactions'] = txn_duplicates.to_dict('records')
            logger.warning(f"Found {len(txn_duplicates)} duplicate transaction groups")
        
        if len(self.settlements) > 0:
            settlement_duplicates = self.settlements.groupby(
                ['transaction_id', 'amount', 'settlement_date']
            ).size()
            settlement_duplicates = settlement_duplicates[
                settlement_duplicates > 1
            ].reset_index(name='count')
            
            if len(settlement_duplicates) > 0:
                self.duplicates['settlements'] = settlement_duplicates.to_dict('records')
                logger.warning(f"Found {len(settlement_duplicates)} duplicate settlement groups")
    
    def filter_valid_transactions(self) -> pd.DataFrame:
        valid_statuses = ['completed', 'settled']
        valid_txns = self.transactions[
            self.transactions['status'].isin(valid_statuses)
        ].copy()
        
        excluded_count = len(self.transactions) - len(valid_txns)
        if excluded_count > 0:
            logger.info(f"Excluded {excluded_count} transactions with non-valid status")
        
        return valid_txns
    
    def amount_matches(self, amount1: float, amount2: float) -> bool:
        return abs(amount1 - amount2) <= self.rounding_tolerance
    
    def date_within_window(self, txn_date, settlement_date) -> bool:
        time_diff = (settlement_date - txn_date).days
        return 0 <= time_diff <= self.settlement_time_window_days
    
    def reconcile(self) -> None:
        logger.info("=" * 80)
        logger.info("STARTING RECONCILIATION PROCESS")
        logger.info("=" * 80)
        
        self.detect_duplicates()
        valid_txns = self.filter_valid_transactions()
        
        matched_txn_ids = set()
        matched_settlement_indices = set()
        
        if len(self.settlements) > 0:
            for txn_idx, txn in valid_txns.iterrows():
                txn_id = txn['transaction_id']
                txn_amount = txn['amount']
                txn_date = txn['date']
                
                matched = False
                
                settlement_candidates = self.settlements[
                    self.settlements['transaction_id'] == txn_id
                ]
                
                for settle_idx, settlement in settlement_candidates.iterrows():
                    settle_amount = settlement['amount']
                    settle_date = settlement['settlement_date']
                    
                    if (self.amount_matches(txn_amount, settle_amount) and
                        self.date_within_window(txn_date, settle_date)):
                        
                        self.matched_pairs.append({
                            'transaction_id': txn_id,
                            'txn_amount': txn_amount,
                            'txn_date': txn_date,
                            'settlement_amount': settle_amount,
                            'settlement_date': settle_date,
                            'settlement_batch': settlement.get('settlement_batch', 'N/A'),
                            'amount_diff': abs(txn_amount - settle_amount),
                            'days_to_settlement': (settle_date - txn_date).days,
                            'match_type': 'exact_id_match'
                        })
                        
                        matched_txn_ids.add(txn_idx)
                        matched_settlement_indices.add(settle_idx)
                        matched = True
                        logger.info(f"✓ Matched: {txn_id}")
                        break
                
                if not matched:
                    amount_date_candidates = self.settlements[
                        (self.settlements['amount'].apply(
                            lambda x: self.amount_matches(txn_amount, x)
                        )) &
                        (self.settlements['settlement_date'].apply(
                            lambda x: self.date_within_window(txn_date, x)
                        ))
                    ]
                    
                    if len(amount_date_candidates) > 0:
                        settlement = amount_date_candidates.iloc[0]
                        settle_idx = settlement.name
                        
                        self.matched_pairs.append({
                            'transaction_id': txn_id,
                            'txn_amount': txn_amount,
                            'txn_date': txn_date,
                            'settlement_amount': settlement['amount'],
                            'settlement_date': settlement['settlement_date'],
                            'settlement_batch': settlement.get('settlement_batch', 'N/A'),
                            'amount_diff': abs(txn_amount - settlement['amount']),
                            'days_to_settlement': (settlement['settlement_date'] - txn_date).days,
                            'match_type': 'secondary_amount_date_match'
                        })
                        
                        matched_txn_ids.add(txn_idx)
                        matched_settlement_indices.add(settle_idx)
                        matched = True
                        logger.info(f"⚠ Secondary match: {txn_id}")
        
        for txn_idx, txn in valid_txns.iterrows():
            if txn_idx not in matched_txn_ids:
                category = self._categorize_unmatched(txn)
                self.unmatched_transactions.append({
                    'transaction_id': txn['transaction_id'],
                    'amount': txn['amount'],
                    'date': txn['date'],
                    'status': txn['status'],
                    'category': category,
                    'reason': self._get_reason(txn, category)
                })
                logger.warning(f"✗ Unmatched transaction: {txn['transaction_id']} - {category}")
        
        if len(self.settlements) > 0:
            for settle_idx, settlement in self.settlements.iterrows():
                if settle_idx not in matched_settlement_indices:
                    self.extra_settlements.append({
                        'transaction_id': settlement['transaction_id'],
                        'amount': settlement['amount'],
                        'settlement_date': settlement['settlement_date'],
                        'settlement_batch': settlement.get('settlement_batch', 'N/A'),
                        'reason': 'No matching transaction found'
                    })
                    logger.warning(f"✗ Extra settlement: {settlement['transaction_id']}")
        
        logger.info("=" * 80)
        logger.info(f"RECONCILIATION COMPLETE")
        logger.info(f"  Matched pairs: {len(self.matched_pairs)}")
        logger.info(f"  Unmatched transactions: {len(self.unmatched_transactions)}")
        logger.info(f"  Extra settlements: {len(self.extra_settlements)}")
        logger.info("=" * 80)
    
    def _categorize_unmatched(self, txn: pd.Series) -> str:
        txn_id = txn['transaction_id']
        txn_amount = txn['amount']
        txn_date = txn['date']
        
        if txn_amount < 0:
            original = self.transactions[
                (self.transactions['transaction_id'] != txn_id) &
                (self.transactions['amount'] == abs(txn_amount))
            ]
            if len(original) == 0:
                return 'refund_no_original'
        
        settlements_by_id = self.settlements[
            self.settlements['transaction_id'] == txn_id
        ]
        if len(settlements_by_id) > 0:
            for _, settlement in settlements_by_id.iterrows():
                if not self.date_within_window(txn_date, settlement['settlement_date']):
                    return 'late_settlement'
        
        settlements_by_id = self.settlements[
            self.settlements['transaction_id'] == txn_id
        ]
        if len(settlements_by_id) > 0:
            for _, settlement in settlements_by_id.iterrows():
                if not self.amount_matches(txn_amount, settlement['amount']):
                    return 'amount_mismatch'
        
        return 'missing_settlement'
    
    def _get_reason(self, txn: pd.Series, category: str) -> str:
        reasons = {
            'missing_settlement': f"No settlement found for {txn['transaction_id']} (${txn['amount']})",
            'late_settlement': f"Settlement exists but outside {self.settlement_time_window_days}-day window",
            'amount_mismatch': f"Settlement amount differs by > ${self.rounding_tolerance}",
            'refund_no_original': f"Refund of ${abs(txn['amount'])} with no matching original transaction"
        }
        return reasons.get(category, 'Unknown reason')
    
    def get_summary(self) -> pd.DataFrame:
        summary_data = []
        
        for unmatched in self.unmatched_transactions:
            summary_data.append({
                'Type': 'Unmatched Transaction',
                'ID': unmatched['transaction_id'],
                'Amount': unmatched['amount'],
                'Date': unmatched['date'],
                'Category': unmatched['category'],
                'Details': unmatched['reason']
            })
        
        for extra in self.extra_settlements:
            summary_data.append({
                'Type': 'Extra Settlement',
                'ID': extra['transaction_id'],
                'Amount': extra['amount'],
                'Date': extra['settlement_date'],
                'Category': 'unknown_settlement',
                'Details': extra['reason']
            })
        
        for matched in self.matched_pairs:
            if matched['amount_diff'] > 0:
                summary_data.append({
                    'Type': 'Rounding Mismatch',
                    'ID': matched['transaction_id'],
                    'Amount': matched['txn_amount'],
                    'Date': matched['txn_date'],
                    'Category': 'rounding_issue',
                    'Details': f"Difference: ${matched['amount_diff']:.4f}"
                })
        
        for dup in self.duplicates['transactions']:
            summary_data.append({
                'Type': 'Duplicate Transaction',
                'ID': dup['transaction_id'],
                'Amount': dup['amount'],
                'Date': dup['date'],
                'Category': 'duplicate',
                'Details': f"Found {dup['count']} copies"
            })
        
        return pd.DataFrame(summary_data)


def main():
    print("\n")
    print("=" * 80)
    print("AI ASSESSMENT: PAYMENTS PLATFORM VS BANK SETTLEMENT RECONCILIATION")
    print("=" * 80)
    print("\n")
    
    print(ASSUMPTIONS)
    print("\n")
    
    print("=" * 80)
    print("STEP 1: GENERATING SYNTHETIC TEST DATA")
    print("=" * 80)
    print("\n")
    
    transactions_df = generate_transactions_dataset()
    settlements_df = generate_settlements_dataset()
    
    print("TRANSACTIONS DATASET:")
    print("-" * 80)
    print(transactions_df.to_string(index=False))
    print(f"\nTotal rows: {len(transactions_df)}")
    print("\n")
    
    print("SETTLEMENTS DATASET:")
    print("-" * 80)
    print(settlements_df.to_string(index=False))
    print(f"\nTotal rows: {len(settlements_df)}")
    print("\n")
    
    print("=" * 80)
    print("STEP 2: RUNNING RECONCILIATION ENGINE")
    print("=" * 80)
    print("\n")
    
    engine = ReconciliationEngine(
        transactions=transactions_df,
        settlements=settlements_df,
        rounding_tolerance=0.01,
        settlement_time_window_days=5
    )
    
    engine.reconcile()
    print("\n")
    
    print("=" * 80)
    print("STEP 3: RECONCILIATION RESULTS")
    print("=" * 80)
    print("\n")
    
    print("MATCHED TRANSACTIONS:")
    print("-" * 80)
    matched_df = pd.DataFrame(engine.matched_pairs)
    print(matched_df.to_string(index=False))
    print(f"\nTotal matched: {len(matched_df)}")
    print("\n")
    
    print("MISMATCH SUMMARY:")
    print("-" * 80)
    summary_df = engine.get_summary()
    if len(summary_df) > 0:
        print(summary_df.to_string(index=False))
        print(f"\nTotal mismatches: {len(summary_df)}")
    else:
        print("No mismatches detected!")
    print("\n")
    
    print("DETAILED MISMATCH BREAKDOWN:")
    print("-" * 80)
    print(f"Unmatched Transactions: {len(engine.unmatched_transactions)}")
    for i, unmatched in enumerate(engine.unmatched_transactions, 1):
        print(f"  {i}. {unmatched['transaction_id']}: {unmatched['category']}")
        print(f"     Amount: ${unmatched['amount']}, Date: {unmatched['date'].date()}")
        print(f"     Reason: {unmatched['reason']}")
    
    print(f"\nExtra Settlements: {len(engine.extra_settlements)}")
    for i, extra in enumerate(engine.extra_settlements, 1):
        print(f"  {i}. {extra['transaction_id']}: ${extra['amount']}")
        print(f"     Settlement Date: {extra['settlement_date'].date()}")
    
    print(f"\nTransaction Duplicates: {len(engine.duplicates['transactions'])}")
    for dup in engine.duplicates['transactions']:
        print(f"  • {dup['transaction_id']}: {dup['count']} copies (${dup['amount']})")
    
    print("\n")
    
    print("=" * 80)
    print("RECONCILIATION STATISTICS")
    print("=" * 80)
    print("\n")
    
    total_txns = len(transactions_df[transactions_df['status'].isin(['completed', 'settled'])])
    matched = len(engine.matched_pairs)
    unmatched = len(engine.unmatched_transactions)
    match_rate = (matched / total_txns * 100) if total_txns > 0 else 0
    
    print(f"Valid Transactions (excluded failed): {total_txns}")
    print(f"Successfully Matched: {matched}")
    print(f"Unmatched: {unmatched}")
    print(f"Match Rate: {match_rate:.2f}%")
    print(f"\nSettlements Processed: {len(settlements_df)}")
    print(f"Extra Settlements (no matching transaction): {len(engine.extra_settlements)}")
    print(f"\nDuplicate Groups Found: {len(engine.duplicates['transactions']) + len(engine.duplicates['settlements'])}")
    
    print("\n")
    
    return engine, transactions_df, settlements_df


if __name__ == "__main__":
    engine, transactions_df, settlements_df = main()
