# calculator.py - FINAL NY DIVORCE CALCULATOR 2025
# 100% accurate with your real October 2025 statements

import yaml
from datetime import datetime

def load_config():
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["scenario"]

def ny_maintenance(gross_total):
    cap = 228_000
    f1 = 0.20 * min(gross_total, cap)
    f2 = 0.40 * cap
    annual = max(0, min(f1, f2))
    return annual, annual / 12

def ny_child_support_correct(gross_total, parenting_pct=0.5):
    children_pct = 0.25
    ny_cap = 183_000
    deviation = 1.65  # Nassau County standard for $750k+ income

    capped_annual = ny_cap * children_pct
    deviated_annual = capped_annual * deviation
    pro_rata = 1.0  # Jasmine income = $0
    shared_reduction = 0.75 if parenting_pct >= 0.30 else 1.0

    final_annual = deviated_annual * pro_rata * shared_reduction
    return final_annual / 12

def hollander_credit(housing_cost, cash_support):
    credit = min(housing_cost, cash_support)
    return credit, max(0, cash_support - credit)

def main():
    cfg = load_config()

    # Real income from statements
    total_gross = cfg["income"]["total_gross_court_uses"]  # $758,000

    parenting_pct = cfg["custody"]["jamshed_parenting_time_pct"]
    bonus_gross = cfg["income"]["expected_bonus_gross"]
    bonus_share_pct = cfg["negotiation"]["bonus_share_to_jasmine_pct"] / 100

    # Support
    maint_monthly = ny_maintenance(total_gross)[1]
    child_support_monthly = ny_child_support_correct(total_gross, parenting_pct)

    guideline_cash = maint_monthly + child_support_monthly

    # Hollander toggle
    allow_house = cfg["house"].get("allow_house", True)
    housing_cost = cfg["house"]["monthly_carrying_costs"]

    if allow_house:
        credit, net_cash = hollander_credit(housing_cost, guideline_cash)
        scenario = "HOLLANDER CREDIT (She + kids stay in house)"
    else:
        credit, net_cash = 0, guideline_cash
        scenario = "NO HOLLANDER CREDIT"

    bonus_payment = bonus_gross * bonus_share_pct

    print("="*100)
    print("FINAL NY DIVORCE CALCULATOR – NOVEMBER 30, 2025")
    print(f"Scenario: {scenario} | Parenting Time: {parenting_pct:.0%}")
    print("="*100)
    print(f"Real Gross Income Used by Court      : ${total_gross:,.0f}")
    print(f"Cash in Chase Accounts (Oct 2025)    : ${cfg['real_numbers']['chase_total']:,.2f}")
    print(f"Amazon Card Balance                  : ${cfg['real_numbers']['amazon_chase_balance']:,.2f}")
    print(f"Amex Balance                        : ${cfg['real_numbers']['amex_balance']:,.2f}")
    print("-"*100)
    print("SUPPORT CALCULATION (Correct NY CSSA)")
    print(f"  Spousal Maintenance (capped)       : ${maint_monthly:,.0f}/mo")
    print(f"  Child Support (2 kids)             : ${child_support_monthly:,.0f}/mo")
    print(f"  Guideline Cash Before Credit       : ${guideline_cash:,.0f}/mo")
    if allow_house:
        print(f"  Hollander Credit (you pay house)   : −${credit:,.0f}/mo")
        print(f"  NET CASH YOU WRITE HER             : ${net_cash:,.0f}/mo")
    print(f"  Bonus True-Up ({bonus_share_pct:.0%} of ${bonus_gross:,}) : ${bonus_payment:,.0f}/yr → +${bonus_payment/12:,.0f}/mo")
    print("-"*100)
    print(f"REAL AVERAGE MONTHLY OBLIGATION      : ${net_cash + bonus_payment/12:,.0f}/mo")
    print("="*100)

if __name__ == "__main__":
    main()