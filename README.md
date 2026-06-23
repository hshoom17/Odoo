# SA HR Module — Saudi Arabia HR Management

An Odoo 17 custom module for managing employees in the Saudi labor market, built with full compliance with **Saudi Labor Law** — including Saudization tracking, leave management, end of service gratuity, and document expiry monitoring.

> Built by **Hashem Al-Ahdal** as a professional Odoo development portfolio.

---

## Features

### Employee Management
- Saudi and Expat employee records with automatic sequential numbering
- **Iqama tracking** — expiry monitoring with automatic status (Valid / Expiring Soon / Expired)
- **Saudization (Nitaqat) %** — auto-calculated per department based on active Saudi employees
- Activate / Suspend employees directly from the form
- Bulk deactivation of employees with expired Iqamas in one click
- **Iqama Renewal Wizard** — renew multiple expat employees at once
- Kanban view with color-coded cards by Iqama status

### Leave Management — Saudi Labor Law Compliant
- **Annual Leave** — 21 days/year (< 5 years service), 30 days/year (≥ 5 years) — Art. 109
- **Hajj Leave** — 10 days, granted once per career — Art. 113
- **Sick Leave** — 30 days full pay / 60 days half pay / 30 days unpaid per year — Art. 117
- Maternity, Paternity, and Emergency leave types
- Automatic balance validation — blocks requests that exceed legal entitlement
- Draft → Approved / Refused workflow with leave balance shown on form

### End of Service Gratuity (EOS)
- Saudi Labor Law formula (Arts. 84–88):
  - First 5 years: 15 days salary per year
  - After 5 years: 30 days salary per year
- Resignation entitlement factors: 0% (< 2 yrs) / 33% (2–5 yrs) / 67% (5–10 yrs) / 100% (≥ 10 yrs)
- Termination / Mutual Agreement / Retirement / Death → always full gratuity from day 1
- **EOS Calculator Wizard** — instant calculation with full itemized breakdown
- Permanent EOS records with paid/draft state tracking

### Payslip with Saudi Components
- Basic salary, Housing Allowance (25% of basic), Transport Allowance, Other Allowances
- **GOSI deductions** — 9% employee + 9.75% employer for Saudis; 2% hazard only for expats
- Gross → Net salary computation
- Draft → Confirmed → Paid workflow

### Contract & Document Tracking
- Contract type: Open-Ended / Fixed-Term with start and end dates
- **Probation period** — defaults to hire date + 90 days, alerts 14 days before it ends
- Passport number and expiry tracking
- Work permit number and expiry tracking
- All documents show: Valid / Expiring Soon / Expired status automatically
- **Document Expiry Dashboard** — one view showing every employee with any expiring or expired document, color-coded red/orange

### Arabic Translation
- Full Arabic UI — all field labels, menus, buttons, selection values, error messages
- RTL layout via Odoo's built-in language system
- 120+ translated strings in proper Odoo `.po` format

---

## Technical Highlights

| Concept | Implementation |
|---------|----------------|
| Models | `sa.employee`, `sa.department`, `sa.payslip`, `sa.leave`, `sa.eos` |
| Computed fields | Iqama/passport/permit/contract status, years of service, annual leave balance, Saudization % |
| `@api.depends` | Multi-field dependency chains with `store=True` |
| `@api.constrains` | Saudi Labor Law leave limits enforced on save |
| `@api.onchange` | Auto-clear fields on nationality change |
| `@api.model_create_multi` | Batch create support on all models |
| SQL constraints | Unique Iqama number, unique National ID |
| Wizard (`TransientModel`) | Iqama renewal, EOS calculator |
| Server actions | Bulk deactivate expired Iqamas |
| Sequences | Auto-numbered references (EMP, PAY, LV, EOS) |
| QWeb report | Printable PDF employee card |
| Search & filters | Filter by status, nationality, leave type, document expiry |
| Kanban view | Color-coded employee cards |
| i18n | Arabic translation (`i18n/ar.po`) with full Odoo PO format |

---

## Module Structure

```
my_first_module/
├── data/
│   └── data.xml                    # Sequences (EMP, PAY, LV, EOS)
├── i18n/
│   └── ar.po                       # Arabic translation (120+ strings)
├── models/
│   ├── sa_department.py            # Department + Saudization %
│   ├── sa_employee.py              # Employee + contract + documents + leave balance
│   ├── sa_payslip.py               # Payslip with GOSI calculation
│   ├── sa_leave.py                 # Leave requests with Saudi law validation
│   └── sa_eos.py                   # End of Service gratuity + formula
├── views/
│   ├── department_views.xml
│   ├── employee_views.xml          # Form with 4 tabs + document expiry dashboard
│   ├── payslip_views.xml
│   ├── leave_views.xml
│   ├── eos_views.xml               # EOS records + calculator wizard
│   ├── report_employee.xml         # QWeb PDF report
│   ├── wizard_iqama_renewal.xml
│   └── menus.xml
├── wizards/
│   ├── iqama_renewal.py            # Bulk Iqama renewal
│   └── eos_calculator.py           # EOS calculator with save to record
├── security/
│   └── ir.model.access.csv
└── __manifest__.py
```

---

## Installation

**Requirements:** Docker Desktop · Odoo 17

```bash
git clone https://github.com/hshoom17/Odoo.git
cd Odoo
docker compose up -d
```

Upgrade the module after any change:
```powershell
.\update.ps1
```

Or install from Odoo UI: **Apps → Search "SA HR" → Install**

---

## Usage

### Employees
- **HR → Employees** — employee form has 4 tabs: Personal & Job, Contract, Documents, Leave Balance
- Rows turn **red** for expired documents, **orange** for anything expiring within 90 days

### Leave Requests
- **HR → Leave Requests** → New → select type and dates → Approve
- System automatically blocks requests that exceed legal limits

### EOS Calculator
- **HR → EOS Calculator** → select employee + termination reason + last working day → **Calculate**
- Review full itemized breakdown → **Save EOS Record** to create a permanent record

### Document Expiry Dashboard
- **HR → Document Expiry** — shows only employees with anything expiring or expired
- Covers: Iqama, Passport, Work Permit, Contract, Probation — all in one view

### Arabic Interface
1. **Settings → Translations → Languages → Add Language → Arabic → Activate**
2. Avatar (top-right) → **Preferences → Language → Arabic → Save**

---

## Author

**Hashem Al-Ahdal**
- GitHub: [@hshoom17](https://github.com/hshoom17)
- Email: hashemalahdal17@gmail.com
