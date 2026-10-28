"""Rule-based categoriser (now used ONLY as fallback behind the ML model)."""
CATEGORY_RULES = {
    "Food & Dining": ["zomato","swiggy","restaurant","cafe","hotel","pizza","burger","biryani","mess","canteen","dominos","kfc","mcdonald","subway","dineout"],
    "Groceries":     ["bigbasket","blinkit","grofers","dmart","reliance fresh","supermarket","kirana","vegetables","milk","zepto","jiomart"],
    "Transport":     ["ola","uber","rapido","yulu","bounce","auto","cab","petrol","fuel","irctc","railway","bus ticket","makemytrip","redbus","metro","fastag"],
    "Utilities":     ["jio","airtel","bsnl","vodafone","vi ","electricity","bescom","msedcl","water bill","gas","lpg","broadband","wifi","postpaid","prepaid recharge"],
    "Entertainment": ["netflix","amazon prime","hotstar","disney","spotify","gaana","jiosaavn","youtube premium","bookmyshow","pvr","inox","gaming","steam"],
    "Shopping":      ["amazon","flipkart","myntra","ajio","meesho","nykaa","snapdeal","shopclues","lifestyle","westside","h&m","zara"],
    "Health":        ["pharmacy","medical","apollo","1mg","netmeds","doctor","hospital","clinic","lab","diagnostic","medicine"],
    "Education":     ["udemy","coursera","byju","unacademy","vedantu","school fee","college fee","tuition","books"],
    "Rent & Housing":["rent","landlord","housing","maintenance","society","apartment","pg ","hostel"],
    "EMI / Loans":   ["emi","loan","mortgage","finance ltd","bajaj finance","hdfc credila","lic premium"],
    "Investments":   ["mutual fund","sip","zerodha","groww","coin","nps","ppf","fd","fixed deposit","lic"],
    "Income":        ["salary","credited by","neft cr","imps cr","bonus","freelance","payment received","refund","cashback"],
    "Transfers":     ["transfer","neft","imps","rtgs","upi","self transfer","wallet load","paytm","phonepe","googlepay","gpay"],
}
ALL_CATEGORIES = list(CATEGORY_RULES.keys()) + ["Uncategorized"]

def categorise(description: str, txn_type: str) -> str:
    d = description.lower()
    if txn_type == "credit":
        for kw in CATEGORY_RULES["Income"]:
            if kw in d: return "Income"
    for cat, kws in CATEGORY_RULES.items():
        for kw in kws:
            if kw in d: return cat
    return "Income" if txn_type == "credit" else "Uncategorized"
