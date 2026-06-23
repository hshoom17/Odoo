# SA HR Module — Saudi Arabia HR Management

An Odoo 17 module for managing employees in the Saudi labor market, with full **Saudization (Nitaqat)** compliance tracking and **Iqama** expiry management.

---

## Features

- **Employee Management** — Create and manage Saudi and expat employee records
- **Iqama Tracking** — Monitor Iqama expiry dates with automatic status (Valid / Expiring Soon / Expired)
- **Visual Alerts** — Red/yellow row highlighting in the list for expired or expiring Iqamas
- **Saudization (Nitaqat) %** — Auto-calculated per department based on active Saudi employees
- **Activate / Suspend** — Change employee status directly from the form with header buttons
- **Bulk Actions** — Deactivate all employees with expired Iqamas in one click
- **Iqama Renewal Wizard** — Select multiple expat employees and renew their Iqama expiry date at once
- **Kanban View** — Visual card-based view of employees grouped by status
- **Search & Filters** — Filter by nationality, Iqama status, department; group by any field
- **PDF Report** — Print a professional employee card with personal and job details
- **Data Validation** — SQL constraints for unique Iqama/National ID, server-side validation for required expat fields

---

## Technical Highlights

| Concept | Implementation |
|---|---|
| Models | `sa.employee`, `sa.department` |
| Computed fields | Iqama status, Saudization % |
| Many2one / One2many | Employee ↔ Department |
| SQL constraints | Unique Iqama number, unique National ID |
| `@api.constrains` | Block saving expat without Iqama data |
| `@api.onchange` | Auto-clear irrelevant fields on nationality change |
| Server actions | Activate/Suspend buttons, bulk deactivate |
| Search view | Filters + Group By |
| Kanban view | Color-coded employee cards |
| QWeb report | Printable PDF employee card |
| Wizard | `TransientModel` for bulk Iqama renewal |

---

## Installation

### Requirements
- Docker Desktop
- Odoo 17

### Setup

```bash
# Clone the repository
git clone https://github.com/hashemalahdal/my_first_module.git

# Add to your Odoo addons path and update the module
docker exec <odoo-container> odoo -u my_first_module -d <your-db> --stop-after-init
```

Or copy the module folder into your Odoo addons directory, then install it from **Apps → Search "SA HR" → Install**.

---

## Usage

### Employees
- Go to **HR → Employees**
- Create employees with Saudi or Expat classification
- Expat employees require an Iqama number and expiry date
- Rows turn **red** for expired Iqamas and **yellow** for Iqamas expiring within 90 days

### Iqama Renewal
- Select one or more expat employees from the list
- Click **Action → Renew Iqama**
- Set the new expiry date and confirm

### PDF Report
- Open any employee → **Print → Employee Report**
- Or select multiple employees from the list → **Print → Employee Report**

### Saudization %
- Go to **HR → Departments**
- Saudization percentage is computed automatically based on active Saudi employees

---

## Module Structure

```
my_first_module/
├── data/
│   └── data.xml                  # Sequences
├── models/
│   ├── sa_department.py          # Department model
│   └── sa_employee.py            # Employee model
├── views/
│   ├── department_views.xml
│   ├── employee_views.xml
│   ├── report_employee.xml       # QWeb PDF report
│   ├── wizard_iqama_renewal.xml
│   └── menus.xml
├── wizards/
│   └── iqama_renewal.py          # Iqama renewal TransientModel
├── security/
│   └── ir.model.access.csv
└── __manifest__.py
```

---

## Author

**Hashem Al-Ahdal**
- GitHub: [@hashemalahdal](https://github.com/hashemalahdal)
- Email: hashemalahdal17@gmail.com
