from typing import Dict, Any

class QeematAgent:
    def __init__(self):
        # Base multiplier rules
        self.urgency_multipliers = {
            "normal": 1.0,
            "urgent": 1.25,
            "emergency": 1.5
        }
        self.loyalty_discount = 0.10 # 10% discount for loyal users

    def calculate_price(self, base_price: float, urgency: str, distance_km: float, is_loyal_customer: bool, high_demand: bool) -> Dict[str, Any]:
        """
        Dynamically calculates the final price based on multiple factors.
        """
        # 1. Base Price
        current_price = base_price
        
        # 2. Urgency Multiplier
        urgency_mult = self.urgency_multipliers.get(urgency, 1.0)
        urgency_charge = (current_price * urgency_mult) - current_price
        current_price += urgency_charge

        # 3. Distance Charge (e.g., 50 PKR per km after 5km)
        distance_charge = 0.0
        if distance_km > 5.0:
            distance_charge = (distance_km - 5.0) * 50.0
        current_price += distance_charge

        # 4. Surge Pricing / High Demand
        surge_charge = 0.0
        if high_demand:
            surge_charge = current_price * 0.20 # 20% surge
            current_price += surge_charge

        # 5. Loyalty Discount
        discount_amount = 0.0
        if is_loyal_customer:
            discount_amount = current_price * self.loyalty_discount
            current_price -= discount_amount

        final_price = round(current_price, 2)

        return {
            "final_price": final_price,
            "breakdown": {
                "base_price": round(base_price, 2),
                "urgency_charge": round(urgency_charge, 2),
                "distance_charge": round(distance_charge, 2),
                "surge_charge": round(surge_charge, 2),
                "loyalty_discount": round(-discount_amount, 2)
            },
            "message": f"Aapka total bill PKR {final_price} banta hai."
        }
