"""Idempotent demo data: banks, bank admins/agents, loan products, Development
Agents and farmers, so every portal can be shown end to end.

    bench --site a2c.localhost execute oan_a2c.seed_demo.seed_demo

Safe to re-run: anything that already exists is left untouched. Every account
gets DEMO_PASSWORD and is NOT forced through the first-login password change.
"""

import frappe

from oan_a2c.a2c_marketplace.roles import (
	BANK_ADMIN_ROLE,
	BANK_AGENT_ROLE,
	DEVELOPMENT_AGENT_ROLE,
	FARMER_ROLE,
)
from oan_a2c.api.v1.auth import create_user_account

DEMO_PASSWORD = "Demo@2026"
EMAIL_DOMAIN = "a2c-demo.com"

BANKS = [
	{
		"key": "cbe", "name": "Commercial Bank of Ethiopia Demo", "code": "3000000001",
		"region": "Addis Ababa",
		"products": [
			("Agricultural Loan", 10000, 200000, 8.5, 12.0, 12, "General purpose agricultural loan for all farming needs."),
			("Smallholder Input Credit", 5000, 80000, 9.0, 11.0, 6, "Seasonal credit for seed, fertilizer and crop protection."),
		],
	},
	{
		"key": "awash", "name": "Awash Bank Demo", "code": "3000000002", "region": "Oromia",
		"products": [
			("Fertilizer Credit", 5000, 150000, 9.0, 11.5, 6, "Short-term credit line for fertilizer and chemical inputs."),
			("Irrigation Pump Loan", 20000, 300000, 8.0, 10.5, 18, "Finance for irrigation pumps and drip systems."),
		],
	},
	{
		"key": "dashen", "name": "Dashen Bank Demo", "code": "3000000003", "region": "Amhara",
		"products": [
			("Equipment Financing", 50000, 900000, 7.5, 10.0, 36, "Long-term financing for tractors, harvesters and farm machinery."),
			("Post-Harvest Storage Loan", 15000, 250000, 8.5, 11.0, 12, "Storage and warehousing to cut post-harvest losses."),
		],
	},
	{
		"key": "boa", "name": "Bank of Abyssinia Demo", "code": "3000000004", "region": "Addis Ababa",
		"products": [
			("Seed Loan", 2000, 50000, 8.0, 10.5, 4, "Micro-loan for high-yield seed before planting season."),
			("Women Farmers Growth Loan", 5000, 100000, 7.0, 9.5, 12, "Lower-rate credit for women-led smallholder farms."),
		],
	},
	{
		"key": "cbo", "name": "Cooperative Bank of Oromia Demo", "code": "3000000005", "region": "Oromia",
		"products": [
			("Livestock Loan", 20000, 300000, 9.5, 12.5, 24, "Purchase of livestock for breeding or meat production."),
			("Dairy Starter Loan", 10000, 150000, 9.0, 11.5, 18, "Dairy cows, feed and milking equipment."),
		],
	},
]

DEVELOPMENT_AGENTS = [
	("Almaz Tesfaye", "agent.almaz", "+251911400001"),
	("Dawit Bekele", "agent.dawit", "+251911400002"),
]

FARMERS = [
	("Tigist Alemu", "farmer.tigist", "+251911500001"),
	("Bekele Girma", "farmer.bekele", "+251911500002"),
]


def _bank(spec: dict) -> str:
	existing = frappe.db.get_value("A2C Participating Bank", {"bank_code": spec["code"]}, "name")
	if existing:
		return existing
	doc = frappe.get_doc(
		{
			"doctype": "A2C Participating Bank",
			"bank_name": spec["name"],
			"bank_code": spec["code"],
			"entity_type": "Bank",
			"registered_email": f"contact.{spec['key']}@{EMAIL_DOMAIN}",
			"registered_phone": "+251111000000",
			"registered_region": spec["region"],
			"registered_country": "Ethiopia",
			"status": "Active",
			"kyc_document": "http://example.com/kyc.pdf",
			"gro_name": "Demo GRO",
			"ops_name": "Demo Ops",
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _bind_to_bank(email: str, bank: str) -> None:
	if not frappe.db.exists("User Permission", {"user": email, "allow": "A2C Participating Bank"}):
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": email,
				"allow": "A2C Participating Bank",
				"for_value": bank,
				"is_default": 1,
			}
		).insert(ignore_permissions=True)


def _user(email: str, full_name: str, phone: str, role: str) -> None:
	if frappe.db.exists("User", email):
		return
	if create_user_account(email=email, full_name=full_name, password=DEMO_PASSWORD,
	                       phone_number=phone, role=role) is None:
		print(f"Skipped {email}: phone {phone} already used by another user")


def _product(bank: str, row: tuple) -> bool:
	name, lo, hi, rate_lo, rate_hi, tenure, desc = row
	if frappe.db.exists("A2C Loan Product", {"product_name": name, "bank": bank}):
		return False
	frappe.get_doc(
		{
			"doctype": "A2C Loan Product",
			"product_name": name,
			"bank": bank,
			"min_amount": lo,
			"max_amount": hi,
			"min_interest_rate": rate_lo,
			"max_interest_rate": rate_hi,
			"tenure_months": tenure,
			"description": desc,
			"status": "Active",
		}
	).insert(ignore_permissions=True, ignore_mandatory=True)
	return True


def seed_demo():
	products = 0
	for i, spec in enumerate(BANKS, start=1):
		bank = _bank(spec)
		admin = f"admin.{spec['key']}@{EMAIL_DOMAIN}"
		agent = f"officer.{spec['key']}@{EMAIL_DOMAIN}"
		_user(admin, f"{spec['key'].upper()} Admin", f"+25191110{i:04d}", BANK_ADMIN_ROLE)
		_user(agent, f"{spec['key'].upper()} Loan Officer", f"+25191120{i:04d}", BANK_AGENT_ROLE)
		_bind_to_bank(admin, bank)
		_bind_to_bank(agent, bank)
		products += sum(_product(bank, row) for row in spec["products"])

	for name, local, phone in DEVELOPMENT_AGENTS:
		_user(f"{local}@{EMAIL_DOMAIN}", name, phone, DEVELOPMENT_AGENT_ROLE)
	for name, local, phone in FARMERS:
		_user(f"{local}@{EMAIL_DOMAIN}", name, phone, FARMER_ROLE)

	frappe.db.commit()  # nosemgrep  (intentional commit for seeding script)
	return f"Demo data ready ({products} new loan products)."
