import json

with open("wallet_details.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(
    "DETAIL_KEYS="
    + json.dumps(
        list(data["data"].keys()),
        separators=(",", ":")
    )
)

for key, value in data["data"].items():

    print(
        "FIELD="
        + json.dumps(
            {
                "key": key,
                "type": type(value).__name__,
                "length": len(value) if hasattr(value, "__len__") else None
            },
            separators=(",", ":")
        )
    )
