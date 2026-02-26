"""
Excel-backed patient data tools.
Reads/writes patients.xlsx for demo mode.
"""
import logging
import os
import uuid
from typing import Optional
import pandas as pd
from config import settings

logger = logging.getLogger(__name__)

# Column names in the Excel file
COLS = ["patient_id", "first_name", "last_name", "dob", "phone", "email", "insurance", "provider"]


def _get_excel_path() -> str:
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, "..", settings.excel_data_path)
    return os.path.normpath(path)


def _load_df() -> pd.DataFrame:
    path = _get_excel_path()
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Patient data file not found at {path}. "
            "Run: python data/create_sample_data.py"
        )
    return pd.read_excel(path, dtype=str).fillna("")


def _save_df(df: pd.DataFrame) -> None:
    df.to_excel(_get_excel_path(), index=False)


def search_patient(query: str) -> list[dict]:
    """
    Search for patients by name, patient ID, phone, or email.

    Args:
        query: Search string

    Returns:
        List of matching patient dicts (at most 5 results)
    """
    df = _load_df()
    query_lower = query.strip().lower()

    mask = (
        df["patient_id"].str.lower().str.contains(query_lower, na=False)
        | df["first_name"].str.lower().str.contains(query_lower, na=False)
        | df["last_name"].str.lower().str.contains(query_lower, na=False)
        | (df["first_name"] + " " + df["last_name"]).str.lower().str.contains(query_lower, na=False)
        | df["phone"].str.contains(query_lower, na=False)
        | df["email"].str.lower().str.contains(query_lower, na=False)
    )

    results = df[mask].head(5).to_dict(orient="records")
    logger.info("Patient search '%s' → %d result(s)", query, len(results))
    return results


def get_patient_by_id(patient_id: str) -> Optional[dict]:
    """Return a single patient record or None."""
    df = _load_df()
    row = df[df["patient_id"].str.upper() == patient_id.strip().upper()]
    if row.empty:
        return None
    return row.iloc[0].to_dict()


def add_patient(
    first_name: str,
    last_name: str,
    dob: str,
    phone: str,
    email: str,
    insurance: str,
    provider: str,
) -> dict:
    """Register a new patient and return the created record."""
    df = _load_df()
    new_id = f"P{str(uuid.uuid4())[:6].upper()}"
    new_row = {
        "patient_id": new_id,
        "first_name": first_name,
        "last_name": last_name,
        "dob": dob,
        "phone": phone,
        "email": email,
        "insurance": insurance,
        "provider": provider,
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    _save_df(df)
    logger.info("New patient registered: %s %s → %s", first_name, last_name, new_id)
    return new_row
