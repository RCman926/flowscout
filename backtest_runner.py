"""
Backtest Runner
Quick script to run comprehensive backtesting and generate real performance metrics
"""

import logging
from institutional_pattern_detector import InstitutionalPatternDetector
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_comprehensive_backtesting():
    """Run comprehensive backtesting for all patterns"""
    
    logger.info("Starting comprehensive pattern backtesting...")
    
    # Initialize pattern detector
    pattern_detector = InstitutionalPatternDetector()
    
    # Run backtesting for SPY
    logger.info("Running backtesting for SPY...")
    spy_results = pattern_detector.run_pattern_backtesting('SPY')
    
    if spy_results['backtesting_completed']:
        logger.info(f"✅ SPY backtesting completed successfully!")
        logger.info(f"Patterns updated with real data: {spy_results['patterns_updated']}")
        
        # Get data quality summary
        data_quality = pattern_detector.get_pattern_data_quality()
        logger.info(f"Data quality: {data_quality['data_quality']}")
        logger.info(f"Patterns with real data: {data_quality['patterns_with_real_data']}")
        logger.info(f"Real data percentage: {data_quality['real_data_percentage']:.1f}%")
        
        return spy_results
    else:
        logger.error(f"❌ SPY backtesting failed: {spy_results.get('error', 'Unknown error')}")
        return None

if __name__ == "__main__":
    results = run_comprehensive_backtesting()
    if results:
        print("\n🎉 Backtesting completed! Real performance metrics are now available.")
    else:
        print("\n❌ Backtesting failed. Check logs for details.")