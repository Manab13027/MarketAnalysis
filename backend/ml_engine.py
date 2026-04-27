# backend/ml_engine.py
import os
import math
from datetime import date, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import joblib
import yfinance as yf
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.model_selection import cross_val_score, TimeSeriesSplit
from sklearn.preprocessing import StandardScaler

from backend.models import MLPrediction, FactorAdjustment, FactorTodayPred

MODEL_PATH = os.path.join(os.path.dirname(__file__), "data", "model.pkl")
WINDOW_15D = 15
WINDOW_1MO = 21   # ~1 trading month

# NIFTY 50 components for breadth calculation (top 30 by liquidity)
NIFTY50_COMPONENTS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
    "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS", "ULTRACEMCO.NS",
    "TITAN.NS", "BAJFINANCE.NS", "NESTLEIND.NS", "WIPRO.NS", "HCLTECH.NS",
    "POWERGRID.NS", "SUNPHARMA.NS", "NTPC.NS", "TECHM.NS", "JSWSTEEL.NS",
    "TATAMOTORS.NS", "ONGC.NS", "TATASTEEL.NS", "M&M.NS", "GRASIM.NS",
]


class MLEngine:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.ridge:   Optional[Ridge] = None
        self.clf:     Optional[LogisticRegression] = None
        self.scaler:  Optional[StandardScaler] = None
        self.cv_mape:          float = 0.0
        self.cv_dir_accuracy:  float = 0.0
        self._hist:   Optional[pd.DataFrame] = None

    # ── Data ─────────────────────────────────────────────────────────────────

    def _fetch_historical_data(self, years: int = 5) -> pd.DataFrame:
        end   = date.today()
        start = end - timedelta(days=years * 365)
        raw = yf.download(
            "^NSEI USDINR=X CL=F EFA ^VIX ^GSPC",
            start=str(start), end=str(end),
            progress=False, auto_adjust=True,
        )
        close = raw["Close"].copy()
        # yfinance returns columns alphabetically; map to friendly names
        col_map = {}
        for col in close.columns:
            s = str(col)
            if "NSEI" in s:      col_map[col] = "nifty"
            elif "USDINR" in s:  col_map[col] = "usdinr"
            elif "CL=F" in s:    col_map[col] = "usoil"
            elif "EFA" in s:     col_map[col] = "msci"
            elif "VIX" in s:     col_map[col] = "vix"
            elif "GSPC" in s:    col_map[col] = "sp500"
        close = close.rename(columns=col_map)
        needed = {"nifty", "usdinr", "usoil", "msci", "vix", "sp500"}
        close = close[[c for c in close.columns if c in needed]]
        close = close.dropna()
        return close

    # ── Features ─────────────────────────────────────────────────────────────

    def _build_features(self, hist: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        df = hist.copy()
        df["usdinr_chg"] = df["usdinr"].pct_change()
        df["usoil_chg"]  = df["usoil"].pct_change()
        df["msci_chg"]   = df["msci"].pct_change()
        df["sp500_chg"]  = df["sp500"].pct_change()
        df["nifty_next"] = df["nifty"].shift(-1)
        df = df.dropna()
        features = ["usdinr_chg", "usoil_chg", "msci_chg", "vix", "sp500_chg"]
        return df[features].values, df["nifty_next"].values

    # ── Training ─────────────────────────────────────────────────────────────

    def train(self) -> None:
        hist = self._fetch_historical_data()
        self._hist = hist
        X, y = self._build_features(hist)

        self.scaler = StandardScaler()
        Xs = self.scaler.fit_transform(X)

        self.ridge = Ridge(alpha=1.0)
        self.ridge.fit(Xs, y)

        y_dir = (y[1:] > y[:-1]).astype(int)
        self.clf = LogisticRegression(max_iter=1000)
        self.clf.fit(Xs[:-1], y_dir)

        tscv = TimeSeriesSplit(n_splits=5)
        mape = cross_val_score(Ridge(alpha=1.0), Xs, y, cv=tscv,
                               scoring="neg_mean_absolute_percentage_error")
        dacc = cross_val_score(LogisticRegression(max_iter=1000), Xs[:-1], y_dir,
                               cv=tscv, scoring="accuracy")
        self.cv_mape         = round(float(-mape.mean()) * 100, 2)
        self.cv_dir_accuracy = round(float(dacc.mean()), 4)

        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump({
            "ridge": self.ridge, "clf": self.clf, "scaler": self.scaler,
            "cv_mape": self.cv_mape, "cv_dir_accuracy": self.cv_dir_accuracy,
        }, MODEL_PATH)

    def _load_if_needed(self) -> bool:
        if self.ridge:
            return True
        if os.path.exists(MODEL_PATH):
            bundle = joblib.load(MODEL_PATH)
            self.ridge  = bundle["ridge"]
            self.clf    = bundle["clf"]
            self.scaler = bundle["scaler"]
            self.cv_mape         = bundle["cv_mape"]
            self.cv_dir_accuracy = bundle["cv_dir_accuracy"]
            return True
        return False

    # ── Rolling beta (OLS slope over window) ─────────────────────────────────

    def _rolling_beta(self, x_series: pd.Series, y_series: pd.Series, window: int) -> float:
        n = min(window, len(x_series), len(y_series))
        if n < 2:
            return 0.0
        x = x_series.iloc[-n:].values
        y = y_series.iloc[-n:].values
        if x.std() == 0:
            return 0.0
        return float(np.polyfit(x, y, 1)[0])

    # ── Factor next-day prediction (linear extrapolation over last 5 days) ───

    def _predict_factor(self, series: pd.Series, window: int = 5) -> float:
        n = min(window, len(series))
        if n < 2:
            return float(series.iloc[-1]) if len(series) else 0.0
        slope = float(np.polyfit(range(n), series.iloc[-n:].values, 1)[0])
        return round(float(series.iloc[-1]) + slope, 4)

    # ── Live prediction ───────────────────────────────────────────────────────

    def predict(
        self,
        usdinr: float,
        usoil:  float,
        msci:   float,
        vix:    float,
        sp500:  float,
    ) -> Optional[MLPrediction]:
        if not self._load_if_needed() or self._hist is None:
            return None

        hist        = self._hist
        today_close = float(hist["nifty"].iloc[-1])
        hist_usdinr = float(hist["usdinr"].iloc[-1])
        hist_usoil  = float(hist["usoil"].iloc[-1])
        hist_msci   = float(hist["msci"].iloc[-1])
        hist_sp500  = float(hist["sp500"].iloc[-1])

        usdinr_chg = (usdinr - hist_usdinr) / hist_usdinr if hist_usdinr else 0.0
        usoil_chg  = (usoil  - hist_usoil)  / hist_usoil  if hist_usoil  else 0.0
        msci_chg   = (msci   - hist_msci)   / hist_msci   if hist_msci   else 0.0
        sp500_chg  = (sp500  - hist_sp500)  / hist_sp500  if hist_sp500  else 0.0

        X_live   = np.array([[usdinr_chg, usoil_chg, msci_chg, vix, sp500_chg]])
        X_scaled = self.scaler.transform(X_live)

        ml_preliminary = round(float(self.ridge.predict(X_scaled)[0]), 2)

        # Rolling betas: factor pct-changes vs nifty pct-change
        nifty_pct   = hist["nifty"].pct_change().dropna()
        beta_usdinr = self._rolling_beta(hist["usdinr"].pct_change().dropna(), nifty_pct, WINDOW_15D)
        beta_usoil  = self._rolling_beta(hist["usoil"].pct_change().dropna(),  nifty_pct, WINDOW_15D)
        beta_msci   = self._rolling_beta(hist["msci"].pct_change().dropna(),   nifty_pct, WINDOW_1MO)

        adj_usdinr  = round(beta_usdinr * usdinr_chg * today_close, 2)
        adj_usoil   = round(beta_usoil  * usoil_chg  * today_close, 2)
        adj_msci    = round(beta_msci   * msci_chg   * today_close, 2)
        adj_breadth = 0.0   # placeholder; breadth calculation is expensive (30 stocks)

        final    = round(ml_preliminary + adj_usdinr + adj_usoil + adj_msci + adj_breadth, 2)
        move     = round(final - today_close, 2)
        move_pct = round(move / today_close * 100, 3) if today_close else 0.0
        direction: str = "UP" if final > today_close else "DOWN"

        p_up       = round(float(self.clf.predict_proba(X_scaled)[0][1]), 4)
        clf_dir    = "UP" if p_up > 0.5 else "DOWN"
        agree      = clf_dir == direction
        confidence = round(abs(p_up - 0.5) * 2, 4)
        if not agree:
            final    = round(today_close + move / 2, 2)
            move     = round(final - today_close, 2)
            move_pct = round(move / today_close * 100, 3) if today_close else 0.0

        vix_daily_vol = vix / 100 / math.sqrt(252)
        vix_low  = round(today_close * (1 - vix_daily_vol), 2)
        vix_high = round(today_close * (1 + vix_daily_vol), 2)

        usdinr_pred = self._predict_factor(hist["usdinr"])
        usoil_pred  = self._predict_factor(hist["usoil"])
        msci_pred   = self._predict_factor(hist["msci"])

        return MLPrediction(
            today_close=today_close,
            ml_preliminary=ml_preliminary,
            adjustments={
                "usdinr":  FactorAdjustment(value=adj_usdinr,  beta=round(beta_usdinr, 4), window="15d"),
                "usoil":   FactorAdjustment(value=adj_usoil,   beta=round(beta_usoil,  4), window="15d"),
                "msci":    FactorAdjustment(value=adj_msci,    beta=round(beta_msci,   4), window="1mo"),
                "breadth": FactorAdjustment(value=adj_breadth, beta=0.0,                   window="15d"),
            },
            final_prediction=final,
            expected_move=move,
            expected_move_pct=move_pct,
            direction=direction,  # type: ignore[arg-type]
            p_up=p_up,
            classifier="AGREE" if agree else "DISAGREE",
            classifier_detail="full move" if agree else "half move",
            confidence=confidence,
            vix_today=round(vix, 2),
            vix_range_low=vix_low,
            vix_range_high=vix_high,
            within_vix_range=(vix_low <= final <= vix_high),
            factors_today_pred={
                "usdinr": FactorTodayPred(today=round(usdinr, 4), pred=usdinr_pred,
                                          direction="UP" if usdinr_pred > usdinr else "DOWN"),
                "usoil":  FactorTodayPred(today=round(usoil, 2),  pred=usoil_pred,
                                          direction="UP" if usoil_pred > usoil else "DOWN"),
                "msci":   FactorTodayPred(today=round(msci, 2),   pred=msci_pred,
                                          direction="UP" if msci_pred > msci else "DOWN"),
                "breadth": FactorTodayPred(today=0.0, pred=0.0, direction="DOWN"),
            },
            cv_mape=self.cv_mape,
            cv_dir_accuracy=round(self.cv_dir_accuracy * 100, 1),
        )
