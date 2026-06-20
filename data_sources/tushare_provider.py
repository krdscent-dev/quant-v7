"""Tushare data provider adapter.

This module mirrors the AkShare provider structure so the research
engine can switch between source adapters without changing downstream
contracts.
"""

from __future__ import annotations

import os
from typing import Any, Mapping

from data_sources.base import DataProvider
from data_sources.mock_provider import MockDataProvider

try:  # pragma: no cover - optional dependency
    import tushare as ts
except ImportError:  # pragma: no cover - optional dependency
    ts = None


class TushareDataProvider(DataProvider):
    """Tushare-backed data provider adapter."""

    def __init__(self) -> None:
        self.tushare_available = ts is not None
        self._mock = MockDataProvider()
        self._token = self._load_token()
        self._pro = None
        if self.tushare_available and self._token:
            try:
                ts.set_token(self._token)
                self._pro = ts.pro_api(self._token)
            except Exception:
                self._pro = None

    def _load_token(self) -> str | None:
        env_token = os.getenv("TUSHARE_TOKEN")
        if env_token:
            return env_token.strip()
        try:
            from pathlib import Path
            import yaml

            config_path = Path(__file__).resolve().parents[1] / "config" / "provider_priority.yaml"
            with config_path.open("r", encoding="utf-8") as handle:
                payload = yaml.safe_load(handle) or {}
            tushare_cfg = payload.get("providers", {}).get("tushare", {})
            token_placeholder = str(tushare_cfg.get("token_placeholder", "")).strip()
            return token_placeholder or None
        except Exception:
            return None

    def _unavailable_payload(self, code: str, method: str) -> Mapping[str, Any]:
        return {
            "code": code,
            "source": "tushare",
            "available": False,
            "status": "tushare_not_installed_or_no_token",
            "method": method,
            "message": "tushare is not installed or token is missing; returning adapter placeholder data.",
        }

    def _fallback_payload(self, code: str, method: str, reason: str) -> Mapping[str, Any]:
        payload = dict(getattr(self._mock, method)(code))
        payload.update(
            {
                "source": "tushare",
                "available": False,
                "status": "tushare_fallback_to_mock",
                "method": method,
                "fallback_reason": reason,
            }
        )
        return payload

    def _safe_call(self, code: str, method: str, fn: Any) -> Mapping[str, Any]:
        if ts is None or self._pro is None:
            return self._fallback_payload(code, method, "tushare_unavailable_or_no_token")
        try:
            return fn()
        except Exception as exc:  # pragma: no cover - network/runtime dependent
            return self._fallback_payload(code, method, f"{type(exc).__name__}: {exc}")

    def _code_to_ts(self, code: str) -> str:
        return code.split(".")[0]

    def _pick(self, frame: Any, names: list[str]) -> Any:
        if frame is None or getattr(frame, "empty", True):
            return None
        columns = {str(col).lower(): col for col in frame.columns}
        for name in names:
            key = name.lower()
            if key in columns:
                value = frame.iloc[0][columns[key]]
                if value is not None and str(value).strip() != "":
                    return value
        return None

    def get_company_basic_info(self, code: str) -> Mapping[str, Any]:
        if ts is None:
            return self._unavailable_payload(code, "get_company_basic_info")
        return {
            "code": code,
            "source": "tushare",
            "available": True,
            "status": "adapter_ready",
            "name": "",
            "industry": "",
            "listing_status": "unknown",
            "message": "Tushare adapter is ready for future field mapping.",
        }

    def get_financial_summary(self, code: str) -> Mapping[str, Any]:
        def _fetch() -> Mapping[str, Any]:
            ts_code = self._code_to_ts(code)
            raw_financial_fields: dict[str, list[str]] = {}
            mapped_financial_summary: dict[str, Any] = {
                "营业收入": None,
                "净利润": None,
                "ROE": None,
                "毛利率": None,
                "营收同比": None,
                "净利润同比": None,
            }

            endpoint_specs = [
                (
                    "fina_indicator",
                    lambda: self._pro.fina_indicator(ts_code=ts_code),
                    ["roe", "grossprofit_margin", "profit_to_gr", "q_sales_yoy", "q_npta_yoy"],
                ),
                (
                    "fina_mainbz",
                    lambda: self._pro.fina_mainbz(ts_code=ts_code),
                    ["bz_sales", "bz_profit"],
                ),
                (
                    "income",
                    lambda: self._pro.income(ts_code=ts_code),
                    ["revenue", "营业收入", "n_income"],
                ),
                (
                    "fina_indicator_vip",
                    lambda: self._pro.fina_indicator_vip(ts_code=ts_code),
                    ["roe", "grossprofit_margin", "q_sales_yoy", "q_npta_yoy"],
                ),
            ]

            for endpoint_name, call, field_names in endpoint_specs:
                try:
                    frame = call()
                except Exception:
                    continue
                if frame is None or getattr(frame, "empty", True):
                    continue
                raw_financial_fields[endpoint_name] = [str(col) for col in frame.columns]
                for field_name in field_names:
                    if field_name in mapped_financial_summary and mapped_financial_summary[field_name] is not None:
                        continue
                    value = self._pick(frame, [field_name, field_name.upper(), field_name.lower()])
                    if value is not None:
                        if field_name in ("roe", "grossprofit_margin", "q_sales_yoy", "q_npta_yoy"):
                            value = value
                        if field_name == "roe":
                            mapped_financial_summary["ROE"] = value
                        elif field_name == "grossprofit_margin":
                            mapped_financial_summary["毛利率"] = value
                        elif field_name == "q_sales_yoy":
                            mapped_financial_summary["营收同比"] = value
                        elif field_name == "q_npta_yoy":
                            mapped_financial_summary["净利润同比"] = value
                        elif field_name in ("revenue", "营业收入", "bz_sales"):
                            mapped_financial_summary["营业收入"] = value
                        elif field_name in ("n_income", "bz_profit"):
                            mapped_financial_summary["净利润"] = value

            mock_summary = self._mock.get_financial_summary(code)
            missing_fields = [field for field, value in mapped_financial_summary.items() if value is None]
            status = "adapter_ready" if not missing_fields else "partial_data"
            available = len(missing_fields) == 0

            def to_float(value: Any, default: float = 0.0) -> float:
                if value is None:
                    return default
                try:
                    return float(value)
                except Exception:
                    return default

            revenue_growth = to_float(mapped_financial_summary["营收同比"], float(mock_summary.get("revenue_growth", 0.0)))
            gross_margin = to_float(mapped_financial_summary["毛利率"], float(mock_summary.get("gross_margin", 0.0)))

            return {
                "code": code,
                "source": "tushare",
                "available": available,
                "status": status,
                "stock_code": ts_code,
                "营业收入": mapped_financial_summary["营业收入"],
                "净利润": mapped_financial_summary["净利润"],
                "ROE": mapped_financial_summary["ROE"],
                "毛利率": mapped_financial_summary["毛利率"],
                "营收同比": mapped_financial_summary["营收同比"],
                "净利润同比": mapped_financial_summary["净利润同比"],
                "revenue_growth": revenue_growth,
                "gross_margin": gross_margin,
                "rd_expense_ratio": float(mock_summary.get("rd_expense_ratio", 0.0)),
                "capex_signal": 0.0,
                "raw_financial_fields": raw_financial_fields,
                "mapped_financial_summary": mapped_financial_summary,
                "missing_fields": missing_fields,
                "message": "Tushare financial summary mapped with field-level fallback.",
            }

        return self._safe_call(code, "get_financial_summary", _fetch)

    def get_order_signals(self, code: str) -> Mapping[str, Any]:
        if ts is None:
            return self._unavailable_payload(code, "get_order_signals")
        return {
            "code": code,
            "source": "tushare",
            "available": True,
            "status": "adapter_ready",
            "order_landing_score": 0.0,
            "revenue_confirmation_score": 0.0,
            "customer_validation_score": 0.0,
            "story_to_earnings_score": 0.0,
            "message": "Order signal mapping placeholder for future data sources.",
        }

    def get_news_signals(self, code: str) -> Mapping[str, Any]:
        if ts is None:
            return self._unavailable_payload(code, "get_news_signals")
        return {
            "code": code,
            "source": "tushare",
            "available": True,
            "status": "adapter_ready",
            "headline_count": 0,
            "positive_news_ratio": 0.0,
            "negative_news_ratio": 0.0,
            "guidance_signal": 0.0,
            "message": "News signal mapping placeholder for future Tushare integration.",
        }

    def get_theme_signals(self, code: str) -> Mapping[str, Any]:
        if ts is None:
            return self._unavailable_payload(code, "get_theme_signals")
        return {
            "code": code,
            "source": "tushare",
            "available": True,
            "status": "adapter_ready",
            "tau_factor_score": 0.0,
            "ascend_ecosystem_exposure": 0.0,
            "domestic_substitution_exposure": 0.0,
            "advanced_packaging_exposure": 0.0,
            "advanced_material_exposure": 0.0,
            "message": "Theme mapping placeholder for future factor contract alignment.",
        }
