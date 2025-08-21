REGION_MAP = {
    "Paris": "eu-west-3",
    "Frankfurt": "eu-central-1",
    "Ireland": "eu-west-1",
    "London": "eu-west-2",
    "N. Virginia": "us-east-1",
    "Oregon": "us-west-2",
}

def format_currency(value: float) -> str:
    return f"${value:,.2f}"


def format_percent(value: float) -> str:
    return f"{value:.2f}%"


def get_reserved_price(terms, term_type: str) -> float:
    for term in terms.values():
        attrs = term["termAttributes"]
        if (
            attrs.get("PurchaseOption") == term_type
            and attrs.get("LeaseContractLength") == "1yr"
        ):
            upfront = 0.0
            hourly = 0.0
            for dim in term["priceDimensions"].values():
                unit = dim["unit"]
                price = float(dim["pricePerUnit"]["USD"])
                if unit == "Hrs":
                    hourly = price
                elif unit == "Quantity":
                    upfront = price
            if term_type == "All Upfront":
                return round(upfront, 2)
            elif term_type == "Partial Upfront":
                return round(upfront + hourly * 24 * 365, 2)
            elif term_type == "No Upfront":
                return round(hourly * 24 * 365, 2)
    return 0.0

