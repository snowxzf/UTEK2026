"""
Hospital item catalog with weights for payload calculation
Based on typical medical supplies and medications used in hospitals
Reference: Jeong et al. (2019) - Truck-drone hybrid delivery routing: Payload-energy dependency
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
@dataclass
class Item:
    """Represents an item that can be delivered by drone"""
    id: str
    name: str
    weight_kg: float
    category: str
    description: str = ""
    #  levels for item prioritization based on patient condition
    emergency_priority: int = 5  #  in emergency/critical situations (1-10, 10 = most critical)
    routine_priority: int = 5    #  in routine situations (1-10, 10 = most important)
class ItemCatalog:
    """
    catalog of hospital items that can be delivered by drone
    weight values based on typical medical supplies
    ref: Jeong et al. (2019) - Truck-drone hybrid delivery routing
    """
    # max payload capacity based on Matternet M2 drone specifications
    # Matternet M2: max payload 2 kg (approx. 4.4 lbs)
    # ref: Matternet M2 drone specifications
    MAX_PAYLOAD_CAPACITY_KG = 2.0  # Maximum total payload weight in kg
     # item catalog organized by category
    # Priority levels: 10 = life-critical, 5 = important, 1 = routine
    ITEMS: Dict[str, List[Item]] = {
        "medications": [
            Item("med_epinephrine", "Epinephrine (EpiPen)", 0.1, "medications", "Emergency epinephrine auto-injector", emergency_priority=10, routine_priority=7),
            Item("med_insulin", "Insulin Vial", 0.05, "medications", "Insulin medication vial", emergency_priority=9, routine_priority=8),
            Item("med_pain_relief", "Pain Relief Medication", 0.08, "medications", "Standard pain relief medication pack", emergency_priority=8, routine_priority=6),
            Item("med_antibiotics", "Antibiotics", 0.12, "medications", "Antibiotic medication pack", emergency_priority=9, routine_priority=7),
            Item("med_saline_bag", "Saline Bag (100ml)", 0.15, "medications", "Small saline solution bag", emergency_priority=10, routine_priority=6),
            Item("med_blood_sample", "Blood Sample Vial", 0.02, "medications", "Blood collection vial", emergency_priority=8, routine_priority=5),
        ],
        "emergency": [
            Item("emerg_oxygen_mask", "Oxygen Mask", 0.08, "emergency", "Emergency oxygen delivery mask", emergency_priority=10, routine_priority=5),
            Item("emerg_defibrillator_pad", "Defibrillator Pads", 0.15, "emergency", "AED defibrillator pads", emergency_priority=10, routine_priority=4),
            Item("emerg_iv_kit", "IV Starter Kit", 0.2, "emergency", "Intravenous insertion kit", emergency_priority=10, routine_priority=6),
            Item("emerg_tourniquet", "Tourniquet", 0.05, "emergency", "Medical tourniquet", emergency_priority=9, routine_priority=4),
            Item("emerg_splint", "Splint (Small)", 0.3, "emergency", "Small medical splint", emergency_priority=7, routine_priority=5),
        ],
        "supplies": [
            Item("supp_bandages", "Bandage Pack", 0.05, "supplies", "Assorted bandages", emergency_priority=8, routine_priority=5),
            Item("supp_gloves", "Medical Gloves (Box)", 0.08, "supplies", "Box of medical examination gloves", emergency_priority=7, routine_priority=6),
            Item("supp_syringes", "Syringes (Pack)", 0.1, "supplies", "Pack of sterile syringes", emergency_priority=8, routine_priority=6),
            Item("supp_needles", "Needles (Pack)", 0.03, "supplies", "Pack of sterile needles", emergency_priority=7, routine_priority=5),
            Item("supp_gauze", "Gauze Pack", 0.06, "supplies", "Sterile gauze pack", emergency_priority=7, routine_priority=5),
            Item("supp_tape", "Medical Tape", 0.02, "supplies", "Medical adhesive tape", emergency_priority=6, routine_priority=4),
        ],
        "lab_samples": [
            Item("lab_urine_sample", "Urine Sample", 0.05, "lab_samples", "Urine collection container", emergency_priority=6, routine_priority=5),
            Item("lab_blood_vial", "Blood Sample Vial", 0.02, "lab_samples", "Blood collection vial", emergency_priority=8, routine_priority=6),
            Item("lab_tissue_sample", "Tissue Sample", 0.03, "lab_samples", "Biological tissue sample container", emergency_priority=7, routine_priority=5),
            Item("lab_culture_swab", "Culture Swab", 0.01, "lab_samples", "Bacterial culture swab", emergency_priority=6, routine_priority=4),
        ],
        "food": [
            Item("food_meal", "Patient Meal", 0.4, "food", "Standard patient meal tray", emergency_priority=4, routine_priority=7),
            Item("food_snack", "Snack Pack", 0.15, "food", "Small snack pack", emergency_priority=3, routine_priority=5),
            Item("food_drink", "Drink Container", 0.2, "food", "Beverage container", emergency_priority=5, routine_priority=6),
            Item("food_nutrition", "Nutritional Supplement", 0.25, "food", "Nutritional supplement drink", emergency_priority=6, routine_priority=6),
        ],
        "equipment": [
            Item("eqp_thermometer", "Digital Thermometer", 0.05, "equipment", "Digital medical thermometer", emergency_priority=7, routine_priority=5),
            Item("eqp_stethoscope", "Stethoscope", 0.2, "equipment", "Medical stethoscope", emergency_priority=6, routine_priority=5),
            Item("eqp_blood_pressure", "Blood Pressure Cuff", 0.15, "equipment", "Portable blood pressure monitor", emergency_priority=8, routine_priority=5),
            Item("eqp_pulse_oximeter", "Pulse Oximeter", 0.08, "equipment", "Finger pulse oximeter", emergency_priority=8, routine_priority=5),
        ],
        "documents": [
            Item("doc_chart", "Patient Chart", 0.1, "documents", "Patient medical chart/folder", emergency_priority=7, routine_priority=6),
            Item("doc_xray", "X-Ray Film", 0.05, "documents", "X-Ray imaging film", emergency_priority=8, routine_priority=6),
            Item("doc_lab_results", "Lab Results", 0.02, "documents", "Laboratory test results", emergency_priority=7, routine_priority=6),
        ]
    }
    @classmethod
    def get_all_items(cls) -> List[Item]:
        """ all items from all categories"""
        all_items = []
        for category_items in cls.ITEMS.values():
            all_items.extend(category_items)
        return all_items
    @classmethod
    def get_item_by_id(cls, item_id: str) -> Optional[Item]:
        """ item by its ID"""
        for category_items in cls.ITEMS.values():
            for item in category_items:
                if item.id == item_id:
                    return item
        return None
    @classmethod
    def get_items_by_category(cls, category: str) -> List[Item]:
        """ all items in a specific category"""
        return cls.ITEMS.get(category, [])
    @classmethod
    def calculate_total_weight(cls, item_quantities: Dict[str, int]) -> float:
        """
         total weight from item quantities
        Args:item_quantities: Dictionary mapping item_id to quantity
        Returns:Total weight in kg
        """
        total_weight = 0.0
        for item_id, quantity in item_quantities.items():
            item = cls.get_item_by_id(item_id)
            if item and quantity > 0:
                total_weight += item.weight_kg * quantity
        return total_weight
    @classmethod
    def validate_payload(cls, item_quantities: Dict[str, int]) -> Tuple[bool, Optional[str], float]:
        """
          payload has at least one item
        :Payloads > 2.0kg will be automatically split into multiple requests
        Args:item_quantities: Dictionary mapping item_id to quantity
        Returns:Tuple of (is_valid, error_message, total_weight_kg)
        """
        total_weight = cls.calculate_total_weight(item_quantities)
        if total_weight <= 0:
            return False, "Please select at least one item", 0.0
        # Payloads > 2.0kg will be automatically split into multiple requests
        # So we don't return an error here, just return the total weight
        return True, None, total_weight
    
    @classmethod
    def prioritize_items(cls, item_quantities: Dict[str, int], patient_critical: bool = False) -> List[Tuple[str, int, float, int]]:
        """
         items based on patient condition and item urgency
        Args:
            item_quantities: Dictionary mapping item_id to quantity
            patient_critical: True if patient is in critical condition
        Returns:list of tuples (item_id, quantity, weight, priority_score) sorted by priority (highest first)
        """
        prioritized = []
        for item_id, quantity in item_quantities.items():
            item = cls.get_item_by_id(item_id)
            if item and quantity > 0:
                #  emergency_priority if patient is critical, otherwise routine_priority
                priority_score = item.emergency_priority if patient_critical else item.routine_priority
                total_weight = item.weight_kg * quantity
                prioritized.append((item_id, quantity, total_weight, priority_score))
#  by priority score (highest first), then by weight (lighter first for same priority)
        prioritized.sort(key=lambda x: (-x[3], x[2]))
        return prioritized
    
    @classmethod
    def split_payload(cls, item_quantities: Dict[str, int], patient_critical: bool = False) -> List[Dict[str, int]]:
        """
         payload into multiple requests if it exceeds capacity
        priotizie items based on patient condition - most critical items go first
        Args:
            item_quantities: Dictionary mapping item_id to quantity
            patient_critical: True if patient is in critical condition
        Returns:list of item_quantities dictionaries, each representing one drone load, prioritized
        """
        if not item_quantities:
            return []
        # calc total weight
        total_weight = cls.calculate_total_weight(item_quantities)
        if total_weight <= cls.MAX_PAYLOAD_CAPACITY_KG:
            # no splitting needed
            return [item_quantities]
        # prioritize items (sorted by priority score, highest first)
        prioritized_items = cls.prioritize_items(item_quantities, patient_critical)
        # split into multiple payloads, filling each up to max capacity
        payloads = []
        current_payload = {}
        current_weight = 0.0
        for item_id, quantity, item_total_weight, priority_score in prioritized_items:
            item = cls.get_item_by_id(item_id)
            if not item:
                continue
            remaining_units = quantity
            while remaining_units > 0:
                # get how many units fit in current payload
                remaining_capacity = cls.MAX_PAYLOAD_CAPACITY_KG - current_weight
                if remaining_capacity < 0.01:  # curr payload is full
                    # save current payload and start new one
                    if current_payload:
                        payloads.append(current_payload)
                    current_payload = {}
                    current_weight = 0.0
                    remaining_capacity = cls.MAX_PAYLOAD_CAPACITY_KG
                # get units that fit in remaining capacity
                units_per_item = item.weight_kg
                units_fitting = min(remaining_units, int(remaining_capacity / units_per_item))
                if units_fitting > 0:
                    #  units to current payload
                    current_payload[item_id] = current_payload.get(item_id, 0) + units_fitting
                    current_weight += units_fitting * units_per_item
                    remaining_units -= units_fitting
                else:
                    # can't't fit even one unit, move to next payload
                    if current_payload:
                        payloads.append(current_payload)
                    current_payload = {}
                    current_weight = 0.0
                    #  fitting in new payload
                    units_per_payload = int(cls.MAX_PAYLOAD_CAPACITY_KG / units_per_item)
                    if units_per_payload > 0:
                        units_for_payload = min(remaining_units, units_per_payload)
                        current_payload[item_id] = units_for_payload
                        current_weight += units_for_payload * units_per_item
                        remaining_units -= units_for_payload
                    else:
                        # item  too heavy for even one unit (shouldn't happen, but handle gracefully)
                        break
        #  last payload if it has items
        if current_payload:
            payloads.append(current_payload)
        return payloads if payloads else [item_quantities]
