"""
============================================================================
 ADVANCED EMPLOYEE PAYROLL & TAX MANAGEMENT SYSTEM
============================================================================
A console-based, JSON-persisted payroll system that:
  - Manages employee records (add / view / update / delete)
  - Calculates gross earnings from basic salary + allowances
  - Calculates Provident Fund (employee & employer contribution)
  - Calculates monthly Income Tax using progressive annual slabs
  - Calculates performance/festival bonus
  - Generates a formatted monthly salary slip (payslip) per employee
  - Generates a company-wide payroll summary report

No external libraries required — pure Python standard library.
============================================================================
"""

import json
import os
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional


# ---------------------------------------------------------------------------
# Configuration / Constants
# ---------------------------------------------------------------------------
DATA_FILE = "employees_data.json"
PAYSLIP_DIR = "payslips"
REPORT_DIR = "reports"

# Progressive annual income-tax slabs: (upper_limit, rate)
# Customize these to match the tax regime you need to comply with.
TAX_SLABS = [
    (300000, 0.00),
    (600000, 0.05),
    (900000, 0.10),
    (1200000, 0.15),
    (1500000, 0.20),
    (float("inf"), 0.30),
]

CESS_RATE = 0.04            # Health & education cess on computed tax
STANDARD_DEDUCTION = 50000  # Flat annual standard deduction
PF_RATE = 0.12               # Employee Provident Fund contribution (% of basic)
EMPLOYER_PF_RATE = 0.12      # Employer PF contribution (% of basic)
PROFESSIONAL_TAX = 200       # Flat monthly professional tax (customizable / 0 if N/A)


# ---------------------------------------------------------------------------
# Employee Data Model
# ---------------------------------------------------------------------------
@dataclass
class Employee:
    emp_id: str
    name: str
    department: str
    designation: str
    basic_salary: float
    hra: float = 0.0
    da: float = 0.0
    conveyance: float = 0.0
    medical_allowance: float = 0.0
    special_allowance: float = 0.0
    bonus_percent: float = 0.0        # % of basic paid as bonus
    other_deductions: float = 0.0     # loan EMI / advance / misc.
    join_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))

    def gross_earnings(self) -> float:
        return (self.basic_salary + self.hra + self.da + self.conveyance +
                self.medical_allowance + self.special_allowance)

    def bonus_amount(self) -> float:
        return round(self.basic_salary * self.bonus_percent / 100, 2)

    def pf_deduction(self) -> float:
        return round(self.basic_salary * PF_RATE, 2)

    def employer_pf_contribution(self) -> float:
        return round(self.basic_salary * EMPLOYER_PF_RATE, 2)


# ---------------------------------------------------------------------------
# Tax Engine
# ---------------------------------------------------------------------------
class TaxCalculator:
    """Computes monthly income tax (TDS) from progressive annual slabs."""

    @staticmethod
    def annual_taxable_income(monthly_gross: float, monthly_pf: float) -> float:
        annual_gross = monthly_gross * 12
        annual_pf = monthly_pf * 12
        return max(0.0, annual_gross - annual_pf - STANDARD_DEDUCTION)

    @staticmethod
    def calculate_annual_tax(taxable_income: float) -> float:
        tax = 0.0
        previous_limit = 0
        for limit, rate in TAX_SLABS:
            if taxable_income > limit:
                tax += (limit - previous_limit) * rate
                previous_limit = limit
            else:
                tax += (taxable_income - previous_limit) * rate
                break
        tax += tax * CESS_RATE
        return round(tax, 2)

    @classmethod
    def monthly_tax(cls, monthly_gross: float, monthly_pf: float) -> float:
        taxable = cls.annual_taxable_income(monthly_gross, monthly_pf)
        annual_tax = cls.calculate_annual_tax(taxable)
        return round(annual_tax / 12, 2)


# ---------------------------------------------------------------------------
# Core Payroll System
# ---------------------------------------------------------------------------
class PayrollSystem:
    def __init__(self):
        self.employees: Dict[str, Employee] = {}
        os.makedirs(PAYSLIP_DIR, exist_ok=True)
        os.makedirs(REPORT_DIR, exist_ok=True)
        self.load_data()

    # ---------------- Persistence ----------------
    def load_data(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                raw = json.load(f)
                self.employees = {k: Employee(**v) for k, v in raw.items()}

    def save_data(self):
        with open(DATA_FILE, "w") as f:
            json.dump({k: asdict(v) for k, v in self.employees.items()}, f, indent=4)

    # ---------------- Employee CRUD ----------------
    def add_employee(self, emp: Employee):
        if emp.emp_id in self.employees:
            raise ValueError(f"Employee ID '{emp.emp_id}' already exists.")
        self.employees[emp.emp_id] = emp
        self.save_data()

    def update_employee(self, emp_id: str, **kwargs):
        emp = self.get_employee(emp_id)
        for key, value in kwargs.items():
            if value not in (None, "") and hasattr(emp, key):
                setattr(emp, key, value)
        self.save_data()

    def delete_employee(self, emp_id: str):
        if emp_id not in self.employees:
            raise KeyError(f"Employee '{emp_id}' not found.")
        del self.employees[emp_id]
        self.save_data()

    def get_employee(self, emp_id: str) -> Employee:
        if emp_id not in self.employees:
            raise KeyError(f"Employee '{emp_id}' not found.")
        return self.employees[emp_id]

    def list_employees(self) -> List[Employee]:
        return list(self.employees.values())

    # ---------------- Payroll Calculation ----------------
    def compute_payroll(self, emp_id: str) -> dict:
        emp = self.get_employee(emp_id)
        gross = emp.gross_earnings()
        bonus = emp.bonus_amount()
        pf = emp.pf_deduction()
        employer_pf = emp.employer_pf_contribution()
        tax = TaxCalculator.monthly_tax(gross, pf)
        total_deductions = pf + tax + PROFESSIONAL_TAX + emp.other_deductions
        net_salary = round(gross + bonus - total_deductions, 2)

        return {
            "emp_id": emp.emp_id,
            "name": emp.name,
            "department": emp.department,
            "designation": emp.designation,
            "gross_earnings": round(gross, 2),
            "bonus": bonus,
            "pf_employee": pf,
            "pf_employer": employer_pf,
            "income_tax": tax,
            "professional_tax": float(PROFESSIONAL_TAX),
            "other_deductions": emp.other_deductions,
            "total_deductions": round(total_deductions, 2),
            "net_salary": net_salary,
            "ctc_monthly": round(gross + bonus + employer_pf, 2),
        }

    # ---------------- Payslip Generation ----------------
    def generate_payslip(self, emp_id: str, month: Optional[str] = None) -> str:
        month = month or datetime.now().strftime("%B-%Y")
        p = self.compute_payroll(emp_id)

        lines = [
            "=" * 60,
            f"{'SALARY SLIP':^60}",
            f"{'Month: ' + month:^60}",
            "=" * 60,
            f"Employee ID   : {p['emp_id']}",
            f"Name          : {p['name']}",
            f"Department    : {p['department']}",
            f"Designation   : {p['designation']}",
            "-" * 60,
            f"{'EARNINGS':<30}{'AMOUNT (Rs.)':>30}",
            "-" * 60,
            f"{'Gross Earnings':<30}{p['gross_earnings']:>30,.2f}",
            f"{'Bonus':<30}{p['bonus']:>30,.2f}",
            "-" * 60,
            f"{'DEDUCTIONS':<30}{'AMOUNT (Rs.)':>30}",
            "-" * 60,
            f"{'Provident Fund (Employee)':<30}{p['pf_employee']:>30,.2f}",
            f"{'Income Tax (TDS)':<30}{p['income_tax']:>30,.2f}",
            f"{'Professional Tax':<30}{p['professional_tax']:>30,.2f}",
            f"{'Other Deductions':<30}{p['other_deductions']:>30,.2f}",
            f"{'Total Deductions':<30}{p['total_deductions']:>30,.2f}",
            "-" * 60,
            f"{'NET SALARY':<30}{p['net_salary']:>30,.2f}",
            f"{'Employer PF Contribution':<30}{p['pf_employer']:>30,.2f}",
            f"{'Monthly CTC':<30}{p['ctc_monthly']:>30,.2f}",
            "=" * 60,
        ]
        content = "\n".join(lines)

        filename = os.path.join(PAYSLIP_DIR, f"payslip_{emp_id}_{month}.txt")
        with open(filename, "w") as f:
            f.write(content)
        return filename

    # ---------------- Company-wide Report ----------------
    def generate_payroll_report(self, month: Optional[str] = None) -> str:
        month = month or datetime.now().strftime("%B-%Y")
        rows = [self.compute_payroll(eid) for eid in self.employees]

        total_gross = sum(r["gross_earnings"] for r in rows)
        total_tax = sum(r["income_tax"] for r in rows)
        total_pf = sum(r["pf_employee"] for r in rows)
        total_net = sum(r["net_salary"] for r in rows)
        total_ctc = sum(r["ctc_monthly"] for r in rows)

        lines = [
            f"PAYROLL SUMMARY REPORT - {month}",
            "=" * 90,
            f"{'ID':<8}{'Name':<20}{'Dept':<15}{'Gross':>12}{'Tax':>10}{'PF':>10}{'Net':>12}",
            "-" * 90,
        ]
        for r in rows:
            lines.append(
                f"{r['emp_id']:<8}{r['name']:<20}{r['department']:<15}"
                f"{r['gross_earnings']:>12,.2f}{r['income_tax']:>10,.2f}"
                f"{r['pf_employee']:>10,.2f}{r['net_salary']:>12,.2f}"
            )
        lines += [
            "-" * 90,
            f"TOTAL EMPLOYEES : {len(rows)}",
            f"TOTAL GROSS PAY : {total_gross:,.2f}",
            f"TOTAL TAX (TDS) : {total_tax:,.2f}",
            f"TOTAL PF        : {total_pf:,.2f}",
            f"TOTAL NET PAY   : {total_net:,.2f}",
            f"TOTAL CTC       : {total_ctc:,.2f}",
            "=" * 90,
        ]
        content = "\n".join(lines)

        filename = os.path.join(REPORT_DIR, f"payroll_report_{month}.txt")
        with open(filename, "w") as f:
            f.write(content)
        return filename


# ---------------------------------------------------------------------------
# Command-Line Interface
# ---------------------------------------------------------------------------
def input_float(prompt: str, default: float = 0.0) -> float:
    val = input(prompt).strip()
    return float(val) if val else default


def main_menu():
    system = PayrollSystem()

    MENU = """
============================================================
  ADVANCED EMPLOYEE PAYROLL & TAX MANAGEMENT SYSTEM
============================================================
1. Add Employee
2. View All Employees
3. Update Employee
4. Delete Employee
5. Compute Payroll (single employee)
6. Generate Payslip
7. Generate Monthly Payroll Report
8. Exit
------------------------------------------------------------
"""
    while True:
        print(MENU)
        choice = input("Enter choice (1-8): ").strip()

        try:
            if choice == "1":
                emp = Employee(
                    emp_id=input("Employee ID: ").strip(),
                    name=input("Name: ").strip(),
                    department=input("Department: ").strip(),
                    designation=input("Designation: ").strip(),
                    basic_salary=input_float("Basic Salary: "),
                    hra=input_float("HRA: "),
                    da=input_float("DA: "),
                    conveyance=input_float("Conveyance Allowance: "),
                    medical_allowance=input_float("Medical Allowance: "),
                    special_allowance=input_float("Special Allowance: "),
                    bonus_percent=input_float("Bonus % of Basic: "),
                    other_deductions=input_float("Other Deductions: "),
                )
                system.add_employee(emp)
                print(f"\u2714 Employee '{emp.name}' added successfully.")

            elif choice == "2":
                emps = system.list_employees()
                if not emps:
                    print("No employees found.")
                for e in emps:
                    print(f"{e.emp_id:<8}{e.name:<20}{e.department:<15}"
                          f"{e.designation:<15}Basic: {e.basic_salary:,.2f}")

            elif choice == "3":
                emp_id = input("Employee ID to update: ").strip()
                print("Leave a field blank to keep its current value.")
                updates = {
                    "name": input("New Name: ").strip() or None,
                    "department": input("New Department: ").strip() or None,
                    "designation": input("New Designation: ").strip() or None,
                }
                basic = input("New Basic Salary: ").strip()
                if basic:
                    updates["basic_salary"] = float(basic)
                system.update_employee(emp_id, **updates)
                print("\u2714 Employee updated.")

            elif choice == "4":
                emp_id = input("Employee ID to delete: ").strip()
                system.delete_employee(emp_id)
                print("\u2714 Employee deleted.")

            elif choice == "5":
                emp_id = input("Employee ID: ").strip()
                result = system.compute_payroll(emp_id)
                for k, v in result.items():
                    print(f"{k:<20}: {v}")

            elif choice == "6":
                emp_id = input("Employee ID: ").strip()
                month = input("Month (e.g. January-2026) [blank = current]: ").strip() or None
                path = system.generate_payslip(emp_id, month)
                print(f"\u2714 Payslip generated: {path}")

            elif choice == "7":
                month = input("Month (e.g. January-2026) [blank = current]: ").strip() or None
                path = system.generate_payroll_report(month)
                print(f"\u2714 Payroll report generated: {path}")

            elif choice == "8":
                print("Exiting Payroll System. Goodbye!")
                break

            else:
                print("Invalid choice. Please select 1-8.")

        except (KeyError, ValueError) as e:
            print(f"\u26a0 Error: {e}")


if __name__ == "__main__":
    main_menu()
