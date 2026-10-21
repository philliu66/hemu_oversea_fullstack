"""本地校验 parse_flight；可选 --live 打真实商品页。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.dhgate.product_page import (  # noqa: E402
    assert_dhgate_product_url,
    fetch_product_page,
    parse_flight,
)

SAMPLE = (
    '5b:{"itemCode":"1127978371","productName":'
    '"Light Luxury Mens Shoes 2026s New Mesh Breathable Fashion Outdoor Shoes '
    'Thick Sole Height Increasing Casual",'
    '"supplierId":"sid1","cateDispName":"Outdoor Shoes","cateDispId":"024072",'
    '"itemWholesaleRangeVos":"$62",'
    '"prodSeller":{"supplierid":"sid1","suppliername":"dhshoesil","supplierSeq":22022422}}\n'
    '62:[{"startQty":1,"endQty":14,"originalPrice":70.65,"promDiscountPrice":20.49},'
    '{"startQty":15,"endQty":1000000,"originalPrice":67.45,"promDiscountPrice":19.56}]\n'
)


def main() -> None:
    parsed = parse_flight(SAMPLE)
    assert parsed["item_code"] == "1127978371"
    assert parsed["price"]["single_price"] == 20.49
    assert parsed["shop"]["name"] == "dhshoesil"
    assert parsed["shop"]["seq"] == 22022422
    assert_dhgate_product_url(
        "https://www.dhgate.com/product/light-luxury/1127978371.html"
    )
    print("parse_flight ok:", parsed["item_code"], parsed["price"]["single_price"])

    if "--live" in sys.argv:
        url = (
            "https://www.dhgate.com/product/"
            "light-luxury-mens-shoes-2026s-new-mesh-breathable/1127978371.html"
        )
        result = fetch_product_page(url)
        print(
            "live:",
            result["ok"],
            result["reason"],
            result["channel"],
            result["elapsed_ms"],
            (result.get("parsed") or {}).get("item_code"),
            (result.get("parsed") or {}).get("price", {}).get("single_price"),
        )
        if not result["ok"]:
            print("message:", result.get("message"))


if __name__ == "__main__":
    main()
