"""
Run this script once to create the sample patients.xlsx file.
  python data/create_sample_data.py
"""
import os
import sys
import pandas as pd

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "patients.xlsx")

PATIENTS = [
    {"patient_id": "P1A2B3", "first_name": "Alice",   "last_name": "Johnson",  "dob": "1985-03-12", "phone": "555-0101", "email": "alice.johnson@email.com",  "insurance": "Blue Cross",    "provider": "Dr. Smith"},
    {"patient_id": "P4C5D6", "first_name": "Bob",     "last_name": "Williams", "dob": "1972-07-22", "phone": "555-0102", "email": "bob.williams@email.com",   "insurance": "Aetna",         "provider": "Dr. Patel"},
    {"patient_id": "P7E8F9", "first_name": "Carol",   "last_name": "Davis",    "dob": "1990-11-05", "phone": "555-0103", "email": "carol.davis@email.com",    "insurance": "United Health", "provider": "Dr. Smith"},
    {"patient_id": "PG1H2I", "first_name": "David",   "last_name": "Martinez", "dob": "1965-01-30", "phone": "555-0104", "email": "david.martinez@email.com", "insurance": "Cigna",         "provider": "Dr. Lee"},
    {"patient_id": "PJ3K4L", "first_name": "Emma",    "last_name": "Wilson",   "dob": "1998-06-18", "phone": "555-0105", "email": "emma.wilson@email.com",    "insurance": "Blue Cross",    "provider": "Dr. Patel"},
    {"patient_id": "PM5N6O", "first_name": "Frank",   "last_name": "Anderson", "dob": "1955-09-25", "phone": "555-0106", "email": "frank.anderson@email.com", "insurance": "Medicare",      "provider": "Dr. Smith"},
    {"patient_id": "PP7Q8R", "first_name": "Grace",   "last_name": "Thomas",   "dob": "1980-04-14", "phone": "555-0107", "email": "grace.thomas@email.com",   "insurance": "Medicaid",      "provider": "Dr. Lee"},
    {"patient_id": "PS9T0U", "first_name": "Henry",   "last_name": "Jackson",  "dob": "1943-12-02", "phone": "555-0108", "email": "henry.jackson@email.com",  "insurance": "Medicare",      "provider": "Dr. Patel"},
    {"patient_id": "PV1W2X", "first_name": "Isabella","last_name": "White",    "dob": "2001-08-09", "phone": "555-0109", "email": "isabella.white@email.com", "insurance": "Aetna",         "provider": "Dr. Smith"},
    {"patient_id": "PY3Z4A", "first_name": "James",   "last_name": "Harris",   "dob": "1970-05-17", "phone": "555-0110", "email": "james.harris@email.com",   "insurance": "United Health", "provider": "Dr. Lee"},
]

df = pd.DataFrame(PATIENTS)
df.to_excel(OUTPUT_PATH, index=False)
print(f"Sample data written to: {OUTPUT_PATH}")
print(f"  {len(df)} patients created")
print(f"\nProviders in dataset:")
for provider in df["provider"].unique():
    count = len(df[df["provider"] == provider])
    print(f"  {provider}: {count} patient(s)")
