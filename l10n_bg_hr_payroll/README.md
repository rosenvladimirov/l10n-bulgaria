# Bulgarian HR Payroll for Odoo 18 🇧🇬

[![License: OPL-1](https://img.shields.io/badge/licence-OPL--1-blue.svg)](https://www.odoo.com/documentation/19.0/legal/licenses.html#odoo-proprietary-license)
[![GitHub](https://img.shields.io/badge/github-rosenvladimirov%2Fl10n--bulgaria-lightgray.png?logo=github)](https://github.com/rosenvladimirov/l10n-bulgaria)

Comprehensive Bulgarian payroll localization module for Odoo 18, ensuring full compliance with Bulgarian labor and tax legislation.

## 🎯 Key Features

### 💰 Payroll Calculations
- **Basic salary** with proration based on worked days
- **Seniority allowance** - minimum 0.6% annually up to maximum years limit
- **Overtime compensation** at 150% of base hourly rate
- **Net salary** calculation after all deductions
- **Python-based salary rules** for maximum flexibility

### 🏛️ Social Insurance Contributions (2025)
| Insurance Type | Employee | Employer | Base Ceiling | Notes |
|----------------|----------|----------|--------------|-------|
| **DOO** (State Social Security) | 7.8% | 12.2% | 3750/4130 BGN | Configurable via parameters |
| **ZO** (Health Insurance) | 3.2% | 4.8% | 3750/4130 BGN | Same ceiling as DOO |
| **UPF** (Universal Pension Fund) | 2.2% | 2.8% | 3750/4130 BGN | For born after 31.12.1959 |
| **TZPB** (Work Accidents) | - | Variable | - | Based on economic activity |

### 📊 Personal Income Tax (DDFL)
- **10% flat tax** on taxable income
- **Automatic deduction** of personal insurance contributions
- **Support for voluntary pension contributions** (reduces tax base)
- **Rule parameters** for easy rate updates

### 🏢 MOD Calculations & Integration
- **Automatic calculation** of minimum insurance income
- Based on **economic activity (KID)** and **NKPD position**
- **Hierarchical parameter lookup** with fallback to parent classifications
- **Validation** that salary is not below MOD
- **Manual override** option for specific cases

### ⚖️ Labor Code Compliance (Article 66 КТ)
- **Complete contract validation** for all mandatory elements:
  - Work location specification
  - NKPD position and job description
  - Contract conclusion and start dates
  - Contract duration type with legal reasoning
  - Leave entitlements (basic/extended/additional)
  - Notice period validation
  - Working time arrangements
- **Automatic validation** on contract save
- **Compliance reporting** with issue identification

### 🔧 Advanced Contract Management
- **Bulgarian-specific fields** for complete Labor Code compliance
- **MOD integration** with automatic calculation and validation
- **TZPB rate computation** from economic activity
- **Seniority allowance** calculation and management
- **Working time validation** (8h/day, 40h/week limits)
- **Probation period** enforcement (max 6 months)

## 🔧 Technical Requirements

- **Odoo 19.0+**
- **hr_payroll** module
- **hr_contract** module
- **l10n_bg_payroll_classifications** module (required dependency)

## 📥 Installation

1. **Clone** the repository:
```shell script
git clone https://github.com/rosenvladimirov/l10n-bulgaria.git
```


2. **Navigate** to enterprise edition modules:
```shell script
cd l10n-bulgaria/l10n-bulgaria-ee/l10n_bg_hr_payroll
```


3. **Copy** the module to your Odoo `addons` directory

4. **Restart** the Odoo server

5. **Install** from Apps menu (will auto-install `l10n_bg_payroll_classifications`)

## ⚙️ Configuration

### 1. Rule Parameters (Pre-configured for 2025)
The module includes comprehensive rule parameters:

| Parameter | Value | Description |
|-----------|-------|-------------|
| `BG_DOO_EMP_RATE` | 0.078 | DOO employee contribution rate |
| `BG_DOO_ER_RATE` | 0.122 | DOO employer contribution rate |
| `BG_ZO_EMP_RATE` | 0.032 | Health insurance employee rate |
| `BG_ZO_ER_RATE` | 0.048 | Health insurance employer rate |
| `BG_UPF_EMP_RATE` | 0.022 | Universal pension fund employee rate |
| `BG_UPF_ER_RATE` | 0.028 | Universal pension fund employer rate |
| `BG_MAX_INS_BASE` | 4130.0 | Maximum insurance base ceiling |
| `BG_PIT_RATE` | 0.10 | Personal income tax rate |
| `BG_CLASS_RATE` | 0.006 | Seniority allowance rate (0.6% annually) |

### 2. Insurance Parameter Integration
The module extends NKPD classifications with:
- **Parameter references** for dynamic rate calculation
- **Hierarchical parameter lookup** - searches up the classification tree
- **TZPB parameter mapping** with code-based matching
- **Real-time rate computation** based on current parameters

### 3. Economic Activity MOD
Automatic MOD calculation using:
- **KID economic activity** classification
- **NKPD qualification group** mapping
- **MOD values by qualification** (Manager, Specialist, Technician, etc.)
- **Validation against contract wage**

## 🚀 Usage

### Creating Employment Contract
1. **Navigate to** Human Resources → Contracts → Contracts
2. **Create new contract** and fill basic employee information
3. **Bulgarian Labor Code section**:
   - Select **NKPD position** (required)
   - Choose **economic activity** (required)
   - **MOD is calculated** automatically
   - Set **working time type** and hours
   - Configure **leave entitlements**
   - Set **notice period** and **probation**
4. **Contract validates** automatically for Labor Code compliance

### Payroll Processing
1. **Navigate to** Payroll → Payslips → Payslips
2. **Create payslip** for employee
3. **Salary rules applied** automatically:
   - Basic salary computation
   - Insurance base calculation
   - Social contributions (employee & employer)
   - Tax calculation with deductions
   - Net salary result
4. **Review and confirm** payslip

### Parameter Management
1. **Configure rates** via Payroll → Configuration → Rule Parameters
2. **Update insurance ceilings** as needed for new fiscal year
3. **Modify base calculation** codes if business logic changes
4. **Set TZPB rates** per economic activity via classifications

## 📋 Payroll Structure: `BG_EMPLOYEE_MONTHLY`

### 🎯 Earnings (Начисления)
| Rule Code | Description | Logic |
|-----------|-------------|-------|
| `BASIC` | Basic salary | Prorated by worked days |
| `OT` | Overtime | 150% of hourly rate × overtime hours |
| `CLASS` | Seniority allowance | Basic × rate × years × proration |
| `GROSS` | Gross salary | Sum of all earnings |

### 📊 Insurance Bases (Осигурителни основи)
| Rule Code | Description | Logic |
|-----------|-------------|-------|
| `BASE_DOO` | DOO base | Configurable codes, MOD floor, ceiling cap |
| `BASE_ZO` | ZO base | Same logic as DOO base |
| `BASE_UPF` | UPF base | Only for employees born after 31.12.1959 |
| `BASE_PIT` | Tax base | Gross - personal contributions - voluntary pension |

### 💳 Employee Deductions (Удръжки от работника)
| Rule Code | Description | Rate Source |
|-----------|-------------|-------------|
| `DOO_EMP` | DOO employee contribution | Rule parameter |
| `ZO_EMP` | Health insurance employee | Rule parameter |
| `UPF_EMP` | UPF employee contribution | Rule parameter (age-dependent) |
| `PIT_10` | Personal income tax | 10% of tax base |

### 🏢 Employer Contributions (Вноски от работодателя)
| Rule Code | Description | Rate Source |
|-----------|-------------|-------------|
| `DOO_ER` | DOO employer contribution | Rule parameter |
| `ZO_ER` | Health insurance employer | Rule parameter |
| `UPF_ER` | UPF employer contribution | Rule parameter (age-dependent) |
| `TZPB_ER` | Work accident insurance | Contract/economic activity |

### 💰 Final Result
| Rule Code | Description | Calculation |
|-----------|-------------|-------------|
| `NET` | Net salary | Gross - All deductions |

## 📊 Payslip Input Types

| Input Code | Description | Usage |
|------------|-------------|--------|
| `CLASS_YEARS` | Years of seniority | Overrides automatic calculation |
| `OT_HOURS` | Overtime hours | For overtime compensation |
| `VOL_PENSION` | Voluntary pension contribution | Reduces income tax base |

## 🏛️ Legal Compliance Framework

### Labor Code Requirements
- **Article 66 КТ** - Complete contract element validation
- **Article 68 КТ** - Contract duration and termination rules
- **Article 342-346 КТ** - Annual leave regulations
- **Article 124-149 КТ** - Working time compliance

### Classification Systems
- **NKPD-2011** - National Classification of Occupations and Positions
- **KID-2008** - Classification of Economic Activities
- **MOD regulations** - Minimum Insurance Income for 2025
- **TZPB categories** - Work accident insurance classification

### Tax & Insurance Compliance
- **Income Tax Act** - 10% flat PIT rate
- **Social Security Code** - Insurance contribution rates and ceilings
- **Ordinance on MOD** - Minimum insurance income requirements

## 🔗 Module Dependencies

### Required Modules
| Module | Purpose |
|--------|---------|
| `l10n_bg_payroll_classifications` | NKPD and KID classifications with MOD data |
| `hr_payroll` | Core payroll functionality |
| `hr_contract` | Extended contract management |

### Integration Capabilities
- **Parameter-driven calculations** - Easy rate updates without code changes
- **Classification hierarchy** - Inherits settings from parent classifications
- **Multi-currency support** - BGN as primary currency
- **Compliance reporting** - Automated validation and issue detection

## 🆘 Support & Documentation

### Resources
- [Module Documentation](https://github.com/rosenvladimirov/l10n-bulgaria-ee)
- [Bulgarian Labor Code](https://www.ciela.net/svoboden-dostap-kn/view/2134524601/kodeks-na-truda)
- [MOD Regulations 2025](https://www.noi.bg)

### Community Support
- [GitHub Issues](https://github.com/rosenvladimirov/l10n-bulgaria/issues)
- [Discussions](https://github.com/rosenvladimirov/l10n-bulgaria/discussions)

### Developer
**Rosen Vladimirov**
- GitHub: [@rosenvladimirov](https://github.com/rosenvladimirov)
- Expertise: Bulgarian localization, HR/Payroll, ERP systems

## 📄 License

This module is licensed under **[OPL-1](https://www.odoo.com/documentation/19.0/legal/licenses.html#odoo-proprietary-license)** (Odoo Proprietary License).

---

*Comprehensive Bulgarian payroll solution ensuring full legal compliance and seamless integration with Bulgarian business requirements.* 🇧🇬
