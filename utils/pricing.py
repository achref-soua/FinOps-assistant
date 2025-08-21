import json
import boto3
import re
from typing import Any, Dict, List
from .models import Entry, EC2Entry
from .helpers import format_currency, format_percent, get_reserved_price, REGION_MAP

def fetch_rds_price(entry: Entry) -> Dict[str, Any]:
    try:
        region_code = REGION_MAP.get(entry.region, entry.region)
        pricing = boto3.client("pricing", region_name="us-east-1")

        filters = [
            {
                "Type": "TERM_MATCH",
                "Field": "instanceType",
                "Value": entry.instance_type,
            },
            {"Type": "TERM_MATCH", "Field": "regionCode", "Value": region_code},
            {
                "Type": "TERM_MATCH",
                "Field": "databaseEngine",
                "Value": entry.engine.lower(),
            },
            {
                "Type": "TERM_MATCH",
                "Field": "deploymentOption",
                "Value": "Multi-AZ" if entry.multi_az.lower() == "oui" else "Single-AZ",
            },
            {
                "Type": "TERM_MATCH",
                "Field": "productFamily",
                "Value": "Database Instance",
            },
        ]

        response = pricing.get_products(
            ServiceCode="AmazonRDS",
            Filters=filters,
            FormatVersion="aws_v1",
            MaxResults=1,
        )

        if not response["PriceList"]:
            raise ValueError("No pricing data found")

        price_item = json.loads(response["PriceList"][0])
        on_demand = list(price_item["terms"]["OnDemand"].values())[0]
        od_price = float(
            list(on_demand["priceDimensions"].values())[0]["pricePerUnit"]["USD"]
        )
        od_annual = round(od_price * 24 * 365, 2)

        reserved_terms = price_item.get("terms", {}).get("Reserved", {})
        no_upfront = get_reserved_price(reserved_terms, "No Upfront")
        partial_upfront = get_reserved_price(reserved_terms, "Partial Upfront")
        all_upfront = get_reserved_price(reserved_terms, "All Upfront")

        def calc_savings(base: float, discounted: float) -> Dict[str, str]:
            return {
                "economy_usd": format_currency(base - discounted),
                "economy_percent": format_percent(100 * (base - discounted) / base)
                if base
                else "N/A",
            }

        return {
            "instance_type": entry.instance_type,
            "engine": entry.engine,
            "region": entry.region,
            "multi_az": entry.multi_az,
            "start": entry.start,
            "end": entry.end,
            "on_demand_annual_usd": format_currency(od_annual),
            "no_upfront_reserved_annual_usd": format_currency(no_upfront),
            **calc_savings(od_annual, no_upfront),
            "partial_upfront_reserved_annual_usd": format_currency(partial_upfront),
            **{
                f"partial_upfront_{k}": v
                for k, v in calc_savings(od_annual, partial_upfront).items()
            },
            "all_upfront_reserved_annual_usd": format_currency(all_upfront),
            **{
                f"all_upfront_{k}": v
                for k, v in calc_savings(od_annual, all_upfront).items()
            },
        }

    except Exception as e:
        return {"error": str(e), **entry.dict()}


def fetch_ec2_comparison(
    instance_type: str, vcpus: int, memory_gb: float, region: str
) -> List[Dict[str, Any]]:
    """
    Returns up to 5 Graviton candidates with exact vCPU and memory,
    sorted by lowest monthly price. Output is long-format ready.
    """
    try:
        pricing = boto3.client("pricing", region_name="us-east-1")
        region_code = REGION_MAP.get(region, region)

        def get_monthly_price(product: Dict) -> float:
            od_terms = product["terms"]["OnDemand"]
            od_term = list(od_terms.values())[0]
            price_dim = list(od_term["priceDimensions"].values())[0]
            price_hourly = float(price_dim["pricePerUnit"]["USD"])
            return price_hourly * 24 * 30  # Approximate monthly

        # Fetch all EC2 Linux shared instances for the region
        paginator = pricing.get_paginator("get_products")
        filters = [
            {"Type": "TERM_MATCH", "Field": "regionCode", "Value": region_code},
            {"Type": "TERM_MATCH", "Field": "operatingSystem", "Value": "Linux"},
            {"Type": "TERM_MATCH", "Field": "preInstalledSw", "Value": "NA"},
            {"Type": "TERM_MATCH", "Field": "tenancy", "Value": "Shared"},
            {"Type": "TERM_MATCH", "Field": "capacitystatus", "Value": "Used"},
        ]

        all_instances = []
        for page in paginator.paginate(
            ServiceCode="AmazonEC2", Filters=filters, FormatVersion="aws_v1"
        ):
            for item_str in page["PriceList"]:
                product = json.loads(item_str)
                attr = product["product"]["attributes"]
                if all(k in attr for k in ["vcpu", "memory", "instanceType"]):
                    all_instances.append(product)

        # Get pricing for original instance
        original_instance = next(
            (
                inst
                for inst in all_instances
                if inst["product"]["attributes"]["instanceType"] == instance_type
                and inst["product"]["attributes"]["regionCode"] == region_code
            ),
            None,
        )

        if not original_instance:
            return [
                {
                    "input_type": instance_type,
                    "region": region,
                    "error": "Original instance pricing not found",
                }
            ]

        original_monthly = get_monthly_price(original_instance)

        # Look for Graviton matches with exact vCPU and memory
        graviton_matches = []
        for inst in all_instances:
            attr = inst["product"]["attributes"]
            inst_type = attr.get("instanceType", "")
            if not re.search(r"\dg\.", inst_type):  # Graviton pattern
                continue

            try:
                cand_vcpus = int(attr["vcpu"])
                cand_memory = float(attr["memory"].replace(" GiB", ""))
            except Exception:
                continue

            if cand_vcpus == vcpus and abs(cand_memory - memory_gb) < 0.01:
                monthly_price = get_monthly_price(inst)
                graviton_matches.append(
                    {
                        "candidate_type": inst_type,
                        "candidate_monthly_raw": monthly_price,
                        "candidate_vcpus": cand_vcpus,
                        "candidate_memory_gb": cand_memory,
                    }
                )

        if not graviton_matches:
            return [
                {
                    "input_type": instance_type,
                    "input_vcpus": vcpus,
                    "input_memory_gb": memory_gb,
                    "region": region,
                    "original_monthly": format_currency(original_monthly),
                    "error": "No exact Graviton match found",
                }
            ]

        graviton_matches.sort(key=lambda x: x["candidate_monthly_raw"])
        top_matches = graviton_matches[:5]

        results = []
        for i, match in enumerate(top_matches, start=1):
            savings = original_monthly - match["candidate_monthly_raw"]
            savings_percent = (
                (savings / original_monthly * 100) if original_monthly else 0
            )

            results.append(
                {
                    "input_type": instance_type,
                    "region": region,
                    "original_monthly": format_currency(original_monthly),
                    "candidate_type": match["candidate_type"],
                    "candidate_monthly": format_currency(
                        match["candidate_monthly_raw"]
                    ),
                    "savings_usd": format_currency(savings),
                    "savings_percent": format_percent(savings_percent),
                }
            )

        return results

    except Exception as e:
        return [
            {
                "input_type": instance_type,
                "region": region,
                "error": str(e),
            }
        ]
