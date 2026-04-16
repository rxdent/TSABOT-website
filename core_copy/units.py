import json

class UnitManager:
    def __init__(self, units_file="units.json"):
        self.u_file = units_file
        
        # Load Units (Read-only)
        with open(self.u_file, "r") as f:
            self.units_data = json.load(f)

    def get_name(self, topic_id):
        for unit in self.units_data["units"]:

            unit_name = f"Unit {unit['unit']}: {unit['title']}"

            if unit["id"] == topic_id:
                return {
                    "unit": unit_name,
                    "section": None
                }

            for sec in unit["sections"]:
                if sec["id"] == topic_id:
                    return {
                        "unit": unit_name,
                        "section": sec["section"]
                    }

        return {
            "unit": topic_id,
            "section": None
        }