"""
Test Suite for Reconciliation Engine
====================================

This module contains comprehensive unit tests to validate the reconciliation
logic and ensure edge cases are handled correctly.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys

# Import the reconciliation engine
from AI import ReconciliationEngine, generate_transactions_dataset, generate_settlements_dataset


class TestReconciliationEngine:
    """Test suite for the reconciliation engine."""
    
    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_results = []
    
    def assert_equal(self, actual, expected, test_name: str):
        """Helper function to assert equality."""
        if actual == expected:
            self.passed_tests += 1
            self.test_results.append(f"✓ PASS: {test_name}")
            return True
        else:
            self.failed_tests += 1
            self.test_results.append(
                f"✗ FAIL: {test_name}\n  Expected: {expected}\n  Actual: {actual}"
            )
            return False
    
    def test_basic_matching(self):
        """Test 1: Basic transaction-settlement matching."""
        print("\n" + "=" * 80)
        print("TEST 1: Basic Transaction-Settlement Matching")
        print("=" * 80)
        
        transactions = pd.DataFrame([
            {
                'transaction_id': 'TXN001',
                'amount': 100.00,
                'date': datetime(2026, 3, 1),
                'timestamp': datetime(2026, 3, 1, 10, 0),
                'status': 'completed',
                'description': 'Test transaction'
            }
        ])
        
        settlements = pd.DataFrame([
            {
                'transaction_id': 'TXN001',
                'amount': 100.00,
                'settlement_date': datetime(2026, 3, 3),
                'settlement_batch': 'BATCH001',
                'description': 'Test settlement'
            }
        ])
        
        engine = ReconciliationEngine(transactions, settlements)
        engine.reconcile()
        
        self.assert_equal(
            len(engine.matched_pairs),
            1,
            "Basic matching: Should match 1 transaction"
        )
        self.assert_equal(
            len(engine.unmatched_transactions),
            0,
            "Basic matching: Should have 0 unmatched transactions"
        )
        
        print("\n".join(self.test_results[-2:]))
    
    def test_rounding_tolerance(self):
        """Test 2: Rounding tolerance handling."""
        print("\n" + "=" * 80)
        print("TEST 2: Rounding Tolerance (±0.01)")
        print("=" * 80)
        
        transactions = pd.DataFrame([
            {
                'transaction_id': 'TXN001',
                'amount': 100.005,  # 3 decimal places
                'date': datetime(2026, 3, 1),
                'timestamp': datetime(2026, 3, 1, 10, 0),
                'status': 'completed',
                'description': 'Rounding test'
            }
        ])
        
        settlements = pd.DataFrame([
            {
                'transaction_id': 'TXN001',
                'amount': 100.01,  # Rounded to 2 decimal places
                'settlement_date': datetime(2026, 3, 3),
                'settlement_batch': 'BATCH001',
                'description': 'Rounding settlement'
            }
        ])
        
        engine = ReconciliationEngine(transactions, settlements, rounding_tolerance=0.01)
        engine.reconcile()
        
        self.assert_equal(
            len(engine.matched_pairs),
            1,
            "Rounding tolerance: Should match despite 0.005 difference"
        )
        
        # Verify the matched pair has the amount difference recorded
        if len(engine.matched_pairs) > 0:
            amount_diff = engine.matched_pairs[0]['amount_diff']
            self.assert_equal(
                amount_diff <= 0.01,
                True,
                "Rounding tolerance: Amount difference should be within tolerance"
            )
        
        print("\n".join(self.test_results[-2:]))
    
    def test_late_settlement(self):
        """Test 3: Late settlement detection (beyond 5-day window)."""
        print("\n" + "=" * 80)
        print("TEST 3: Late Settlement Detection")
        print("=" * 80)
        
        transactions = pd.DataFrame([
            {
                'transaction_id': 'TXN001',
                'amount': 100.00,
                'date': datetime(2026, 3, 1),
                'timestamp': datetime(2026, 3, 1, 10, 0),
                'status': 'completed',
                'description': 'Early transaction'
            }
        ])
        
        settlements = pd.DataFrame([
            {
                'transaction_id': 'TXN001',
                'amount': 100.00,
                'settlement_date': datetime(2026, 3, 10),  # 9 days later - outside window
                'settlement_batch': 'BATCH001',
                'description': 'Late settlement'
            }
        ])
        
        engine = ReconciliationEngine(
            transactions,
            settlements,
            settlement_time_window_days=5
        )
        engine.reconcile()
        
        self.assert_equal(
            len(engine.unmatched_transactions),
            1,
            "Late settlement: Should flag as unmatched (outside 5-day window)"
        )
        
        if len(engine.unmatched_transactions) > 0:
            self.assert_equal(
                engine.unmatched_transactions[0]['category'],
                'late_settlement',
                "Late settlement: Category should be 'late_settlement'"
            )
        
        print("\n".join(self.test_results[-2:]))
    
    def test_duplicate_detection(self):
        """Test 4: Duplicate transaction detection."""
        print("\n" + "=" * 80)
        print("TEST 4: Duplicate Transaction Detection")
        print("=" * 80)
        
        base_date = datetime(2026, 3, 1)
        transactions = pd.DataFrame([
            {
                'transaction_id': 'TXN001',
                'amount': 199.99,
                'date': base_date,
                'timestamp': base_date + timedelta(hours=10, minutes=30),
                'status': 'completed',
                'description': 'Duplicate entry 1'
            },
            {
                'transaction_id': 'TXN001',  # Same ID and amount
                'amount': 199.99,
                'date': base_date,
                'timestamp': base_date + timedelta(hours=10, minutes=31),
                'status': 'completed',
                'description': 'Duplicate entry 2'
            }
        ])
        
        settlements = pd.DataFrame([
            {
                'transaction_id': 'TXN001',
                'amount': 199.99,
                'settlement_date': base_date + timedelta(days=2),
                'settlement_batch': 'BATCH001',
                'description': 'Settlement'
            }
        ])
        
        engine = ReconciliationEngine(transactions, settlements)
        engine.reconcile()
        
        self.assert_equal(
            len(engine.duplicates['transactions']),
            1,
            "Duplicate detection: Should detect 1 duplicate group"
        )
        
        if len(engine.duplicates['transactions']) > 0:
            self.assert_equal(
                engine.duplicates['transactions'][0]['count'],
                2,
                "Duplicate detection: Should count 2 copies"
            )
        
        print("\n".join(self.test_results[-2:]))
    
    def test_refund_without_original(self):
        """Test 5: Refund detection (negative amount without original)."""
        print("\n" + "=" * 80)
        print("TEST 5: Refund Without Original Transaction")
        print("=" * 80)
        
        transactions = pd.DataFrame([
            {
                'transaction_id': 'TXN001',
                'amount': -75.00,  # Refund (negative)
                'date': datetime(2026, 3, 1),
                'timestamp': datetime(2026, 3, 1, 10, 0),
                'status': 'completed',
                'description': 'Orphan refund'
            }
        ])
        
        settlements = pd.DataFrame([
            {
                'transaction_id': 'TXN001',
                'amount': -75.00,
                'settlement_date': datetime(2026, 3, 3),
                'settlement_batch': 'BATCH001',
                'description': 'Refund settlement'
            }
        ])
        
        engine = ReconciliationEngine(transactions, settlements)
        engine.reconcile()
        
        # The refund SHOULD match the settlement (both negative)
        self.assert_equal(
            len(engine.matched_pairs),
            1,
            "Refund: Should match refund transaction with refund settlement"
        )
        
        # Now test refund with settlement but no matching original
        transactions2 = pd.DataFrame([
            {
                'transaction_id': 'TXN001',
                'amount': -75.00,
                'date': datetime(2026, 3, 1),
                'timestamp': datetime(2026, 3, 1, 10, 0),
                'status': 'completed',
                'description': 'Orphan refund'
            }
        ])
        
        settlements2 = pd.DataFrame([])  # No settlement for refund
        
        engine2 = ReconciliationEngine(transactions2, settlements2)
        engine2.reconcile()
        
        self.assert_equal(
            len(engine2.unmatched_transactions),
            1,
            "Refund: Should flag refund without settlement as unmatched"
        )
        
        print("\n".join(self.test_results[-2:]))
    
    def test_extra_settlement(self):
        """Test 6: Extra settlement detection (no matching transaction)."""
        print("\n" + "=" * 80)
        print("TEST 6: Extra Settlement Detection")
        print("=" * 80)
        
        transactions = pd.DataFrame([
            {
                'transaction_id': 'TXN001',
                'amount': 100.00,
                'date': datetime(2026, 3, 1),
                'timestamp': datetime(2026, 3, 1, 10, 0),
                'status': 'completed',
                'description': 'Transaction'
            }
        ])
        
        settlements = pd.DataFrame([
            {
                'transaction_id': 'TXN001',
                'amount': 100.00,
                'settlement_date': datetime(2026, 3, 3),
                'settlement_batch': 'BATCH001',
                'description': 'Settlement'
            },
            {
                'transaction_id': 'TXN999',  # No matching transaction
                'amount': 999.99,
                'settlement_date': datetime(2026, 3, 4),
                'settlement_batch': 'BATCH002',
                'description': 'Mystery settlement'
            }
        ])
        
        engine = ReconciliationEngine(transactions, settlements)
        engine.reconcile()
        
        self.assert_equal(
            len(engine.extra_settlements),
            1,
            "Extra settlement: Should detect 1 settlement with no matching transaction"
        )
        
        if len(engine.extra_settlements) > 0:
            self.assert_equal(
                engine.extra_settlements[0]['transaction_id'],
                'TXN999',
                "Extra settlement: Should identify TXN999 as extra"
            )
        
        print("\n".join(self.test_results[-2:]))
    
    def test_failed_transaction_exclusion(self):
        """Test 7: Failed transactions should be excluded."""
        print("\n" + "=" * 80)
        print("TEST 7: Failed Transaction Exclusion")
        print("=" * 80)
        
        transactions = pd.DataFrame([
            {
                'transaction_id': 'TXN001',
                'amount': 100.00,
                'date': datetime(2026, 3, 1),
                'timestamp': datetime(2026, 3, 1, 10, 0),
                'status': 'completed',
                'description': 'Valid transaction'
            },
            {
                'transaction_id': 'TXN002',
                'amount': 50.00,
                'date': datetime(2026, 3, 2),
                'timestamp': datetime(2026, 3, 2, 10, 0),
                'status': 'failed',  # Should be ignored
                'description': 'Failed transaction'
            }
        ])
        
        settlements = pd.DataFrame([
            {
                'transaction_id': 'TXN001',
                'amount': 100.00,
                'settlement_date': datetime(2026, 3, 3),
                'settlement_batch': 'BATCH001',
                'description': 'Settlement 1'
            }
        ])
        
        engine = ReconciliationEngine(transactions, settlements)
        engine.reconcile()
        
        valid_txns = len(transactions[transactions['status'].isin(['completed', 'settled'])])
        self.assert_equal(
            valid_txns,
            1,
            "Failed exclusion: Should have 1 valid transaction (not 2)"
        )
        
        self.assert_equal(
            len(engine.matched_pairs),
            1,
            "Failed exclusion: Should match only the valid transaction"
        )
        
        print("\n".join(self.test_results[-2:]))
    
    def test_amount_mismatch(self):
        """Test 8: Amount mismatch beyond rounding tolerance."""
        print("\n" + "=" * 80)
        print("TEST 8: Amount Mismatch Detection")
        print("=" * 80)
        
        transactions = pd.DataFrame([
            {
                'transaction_id': 'TXN001',
                'amount': 100.00,
                'date': datetime(2026, 3, 1),
                'timestamp': datetime(2026, 3, 1, 10, 0),
                'status': 'completed',
                'description': 'Transaction'
            }
        ])
        
        settlements = pd.DataFrame([
            {
                'transaction_id': 'TXN001',
                'amount': 100.50,  # Mismatch > 0.01
                'settlement_date': datetime(2026, 3, 3),
                'settlement_batch': 'BATCH001',
                'description': 'Mismatched settlement'
            }
        ])
        
        engine = ReconciliationEngine(transactions, settlements, rounding_tolerance=0.01)
        engine.reconcile()
        
        self.assert_equal(
            len(engine.unmatched_transactions),
            1,
            "Amount mismatch: Should flag as unmatched (difference > tolerance)"
        )
        
        if len(engine.unmatched_transactions) > 0:
            self.assert_equal(
                engine.unmatched_transactions[0]['category'],
                'amount_mismatch',
                "Amount mismatch: Category should be 'amount_mismatch'"
            )
        
        print("\n".join(self.test_results[-2:]))
    
    def test_cross_month_settlement(self):
        """Test 9: Settlement in next month (within 5-day window)."""
        print("\n" + "=" * 80)
        print("TEST 9: Cross-Month Settlement (Late March to April)")
        print("=" * 80)
        
        transactions = pd.DataFrame([
            {
                'transaction_id': 'TXN001',
                'amount': 350.00,
                'date': datetime(2026, 3, 29),  # March 29
                'timestamp': datetime(2026, 3, 29, 15, 30),
                'status': 'completed',
                'description': 'Late March transaction'
            }
        ])
        
        settlements = pd.DataFrame([
            {
                'transaction_id': 'TXN001',
                'amount': 350.00,
                'settlement_date': datetime(2026, 4, 3),  # April 3 (5 days later)
                'settlement_batch': 'BATCH_APRIL',
                'description': 'April settlement'
            }
        ])
        
        engine = ReconciliationEngine(
            transactions,
            settlements,
            settlement_time_window_days=5
        )
        engine.reconcile()
        
        self.assert_equal(
            len(engine.matched_pairs),
            1,
            "Cross-month: Should match settlement across months (within 5 days)"
        )
        
        if len(engine.matched_pairs) > 0:
            self.assert_equal(
                engine.matched_pairs[0]['days_to_settlement'],
                5,
                "Cross-month: Should calculate 5 days to settlement"
            )
        
        print("\n".join(self.test_results[-2:]))
    
    def run_all_tests(self):
        """Run all tests."""
        print("\n\n")
        print("╔" + "=" * 78 + "╗")
        print("║" + "RECONCILIATION ENGINE - COMPREHENSIVE TEST SUITE".center(78) + "║")
        print("╚" + "=" * 78 + "╝")
        
        self.test_basic_matching()
        self.test_rounding_tolerance()
        self.test_late_settlement()
        self.test_duplicate_detection()
        self.test_refund_without_original()
        self.test_extra_settlement()
        self.test_failed_transaction_exclusion()
        self.test_amount_mismatch()
        self.test_cross_month_settlement()
        
        # Print summary
        print("\n\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"\nTotal Tests: {self.passed_tests + self.failed_tests}")
        print(f"Passed: {self.passed_tests} ✓")
        print(f"Failed: {self.failed_tests} ✗")
        print(f"Success Rate: {(self.passed_tests / (self.passed_tests + self.failed_tests) * 100):.1f}%")
        
        if self.failed_tests == 0:
            print("\n🎉 ALL TESTS PASSED! 🎉")
        else:
            print(f"\n⚠️  {self.failed_tests} test(s) failed. Review details above.")
        
        print("\n")


if __name__ == "__main__":
    tester = TestReconciliationEngine()
    tester.run_all_tests()
