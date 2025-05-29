import yfinance as yf
import pandas as pd

def get_previous_day_price(asset_symbol: str) -> float | None:
    """
    Fetches the previous trading day's closing price for a given asset symbol.

    Args:
        asset_symbol: The symbol of the asset (e.g., "PETR4.SA", "AAPL").

    Returns:
        The previous day's closing price as a float, or None if an error occurs.
    """
    try:
        ticker = yf.Ticker(asset_symbol)
        
        # First, try to get 'previousClose' from ticker.info
        if 'previousClose' in ticker.info and ticker.info['previousClose'] is not None:
            return float(ticker.info['previousClose'])
        else:
            # Fallback to history if 'previousClose' is not available or None
            # Fetch history for the last 3 trading days to be safe
            hist = ticker.history(period="3d")

            if hist.empty:
                print(f"Warning: No historical data found for {asset_symbol} via history().")
                # As a last resort for some specific cases (e.g. some indices might not have 'previousClose' but have chart data)
                # Try to get the last closing price from '1d' if '3d' is empty
                hist_1d = ticker.history(period="1d")
                if not hist_1d.empty and 'Close' in hist_1d and not hist_1d['Close'].empty:
                    return float(hist_1d['Close'].iloc[-1])
                else:
                    print(f"Error: No historical data found for {asset_symbol} even with 1d period.")
                    return None


            # Remove rows where 'Close' is NaN
            hist = hist.dropna(subset=['Close'])

            if hist.empty:
                print(f"Error: No valid historical data (all NaNs) for {asset_symbol} in the last 3 days.")
                return None

            # Sort by date to ensure correct order, though yfinance usually does this.
            hist = hist.sort_index()

            # If market is open, the last entry of history might be current day's data.
            # If market is closed, the last entry is the last trading day's close.
            # We want the close of the *actual* previous trading day.

            # If we have at least two days of data:
            #   - hist.iloc[-1] is the most recent data point.
            #   - hist.iloc[-2] is the one before that.
            # If the most recent data point's date is "today" (market is open), then previous close is hist.iloc[-2]['Close'].
            # Otherwise (market closed, or data is not for "today"), previous close is hist.iloc[-1]['Close'].
            # This distinction is hard without knowing if the market is open and if the last point is partial.

            # Simplification: yfinance's `period="1d"` when the market is closed often gives the last closing price.
            # If `ticker.info['previousClose']` failed, it's possible the stock is new or has sparse data.
            # Let's take the latest available closing price from the history.
            # If hist has data, iloc[-1] is the most recent closing price.
            if len(hist) >= 1:
                # This will be the closing price of the most recent day in the fetched history.
                # For a 3d period, this should be the last *completed* trading day's close.
                return float(hist['Close'].iloc[-1])
            else:
                # This case should be covered by hist.empty checks already.
                print(f"Error: Not enough historical data for {asset_symbol} to determine price after processing.")
                return None

    except Exception as e:
        print(f"Error fetching price for {asset_symbol}: {e}")
        return None
