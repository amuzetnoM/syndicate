import sys
import types

# Make test environment hermetic by stubbing heavy optional dependencies
sys.modules.setdefault('yfinance', types.ModuleType('yfinance'))
