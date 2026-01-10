"""
Data models for the hospital drone logistics system
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict
from patients import Patient


class Priority(Enum):
    """
    Priority levels based on Canadian Triage and Acuity Scale (CTAS)
    Reference: CMS-ES-02-2017, Attachment 4 - Canadian Triage and Acuity Scale
    """
    CTAS_I = 5      # Resuscitation - requires immediate intervention (98% seen immediately)
                    # Conditions: cardiac arrest, major trauma, shock states
    CTAS_II = 4     # Emergent - requires rapid medical intervention (95% within 15 minutes)
                    # Conditions: head injury, chest pain, internal bleeding
    CTAS_III = 3    # Urgent - could progress to serious problem (90% within 30 minutes)
                    # Conditions: mild-moderate asthma, moderate trauma, vomiting/diarrhea in <2 years
    CTAS_IV = 2     # Less-urgent - potential for deterioration (85% within 60 minutes)
                    # Conditions: urinary symptoms, mild abdominal pain, earache
    CTAS_V = 1      # Non-urgent - can be delayed/referred (80% within 120 minutes)
                    # Conditions: sore throat, chronic problems, psychiatric (no suicidal ideation)
    
    @property
    def response_time_minutes(self) -> int:
        """Get target response time in minutes based on CTAS guidelines"""
        return {
            Priority.CTAS_I: 0,      # Immediate
            Priority.CTAS_II: 15,    # Within 15 minutes
            Priority.CTAS_III: 30,   # Within 30 minutes
            Priority.CTAS_IV: 60,    # Within 60 minutes
            Priority.CTAS_V: 120     # Within 120 minutes
        }.get(self, 120)
    
    @property
    def is_emergency(self) -> bool:
        """Check if this CTAS level requires emergency resources (CTAS I or II)"""
        return self.value >= 4  # CTAS I (5) or CTAS II (4)
    
    @property
    def display_name(self) -> str:
        """Get human-readable display name"""
        return {
            Priority.CTAS_I: "CTAS I - Resuscitation",
            Priority.CTAS_II: "CTAS II - Emergent",
            Priority.CTAS_III: "CTAS III - Urgent",
            Priority.CTAS_IV: "CTAS IV - Less-urgent",
            Priority.CTAS_V: "CTAS V - Non-urgent"
        }.get(self, "Unknown")


class RequestStatus(Enum):
    """Status tracking for requests"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_TRANSIT = "in_transit"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class Location:
    """Represents a location in the hospital (node in graph)"""
    id: int
    name: str
    x: float  # Coordinates for distance calculation
    y: float
    floor: int = 1  # Multi-floor support


@dataclass
class Drone:
    """Represents a drone in the system"""
    id: int
    current_location_id: int
    status: str = "available"  # available, assigned, in_transit, charging
    assigned_request_id: Optional[int] = None
    emergency_drone: bool = False  # True if reserved for emergency requests
    
    # Battery management (Matternet M2-style drone)
    # Based on specs: Max range 20 km with 1 kg payload
    # Energy consumption: 1.08 Wh/m (1.08 kWh/km) with 1 kg payload
    # Estimated battery capacity: ~2 kWh (allows for ~20 km range with 1 kg)
    battery_capacity_kwh: float = 2.0  # Total battery capacity in kWh (Matternet M2-style)
    battery_level_kwh: float = 2.0  # Current battery level in kWh (starts fully charged)
    is_charging: bool = False  # True if drone is at charging station
    flight_start_time: Optional[datetime] = None  # When the current flight started (for real-time battery tracking)
    battery_consumed_this_flight_kwh: float = 0.0  # Battery consumed during current flight
    
    # Multi-stop delivery support
    delivery_route: List[int] = field(default_factory=list)  # List of location IDs in delivery order
    current_payload_weight_kg: float = 0.0  # Current payload weight
    current_speed_m_per_sec: float = 2.5  # Current speed based on priority (max 16 m/s for Matternet M2)


@dataclass
class Request:
    """
    Represents a drone request from staff using CTAS priority levels
    Includes multi-criteria prioritization based on Vital Priority System
    Reference: Pinho & Leal (2025) - An intelligent community-based system for healthcare prioritisation
    """
    id: int
    requester_id: str  # Doctor/nurse ID
    requester_name: str
    requester_location_id: int
    priority: Priority
    description: str
    timestamp: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None  # When the request was completed (if completed)
    status: RequestStatus = RequestStatus.PENDING
    assigned_drone_id: Optional[int] = None
    emergency: bool = False
    
    # Patient data (from patient database)
    patient_id: Optional[str] = None  # ID of patient in database
    
    # Multi-request support (for payloads > 1.5kg)
    parent_request_id: Optional[int] = None  # ID of parent request if this is a split request
    is_partial_delivery: bool = False  # True if this is part of a larger order
    delivery_sequence: int = 1  # Sequence number for partial deliveries (1, 2, 3, ...)
    total_deliveries: int = 1  # Total number of deliveries for this order
    
    # Multi-criteria prioritization fields (based on Vital Priority System and PPT research)
    # These are used to break ties within the same CTAS level
    # Can be auto-filled from patient data if patient_id is provided
    patient_age: Optional[int] = None  # Patient age (younger = higher priority)
    waiting_time_minutes: float = 0.0  # Time since request created (longer = higher priority)
    is_parent: bool = False  # Patient is a parent (higher priority)
    expected_life_years_gained: Optional[float] = None  # Expected life years gained from treatment
    quality_of_life_score: Optional[float] = None  # Quality of life improvement (0-1 scale)
    lifestyle_responsibility: Optional[str] = None  # "responsible", "moderate", "irresponsible"
    social_role: Optional[str] = None  # "healthcare_worker", "essential_worker", "general", etc.
    clinical_severity_score: Optional[float] = None  # Additional clinical severity (0-1 scale, 1 = most severe)
    
    @property
    def target_response_time_minutes(self) -> int:
        """Get target response time based on CTAS priority"""
        return self.priority.response_time_minutes
    
    def get_patient_data(self) -> Optional['Patient']:
        """Get patient data if patient_id is provided"""
        if self.patient_id:
            from patients import get_patient
            return get_patient(self.patient_id)
        return None
    
    def calculate_vital_priority_score(self) -> float:
        """
        Calculate Vital Priority Score for breaking ties within same CTAS level
        Based on Pinho & Leal (2025) and Dery et al. (2020) - PPT research
        
        Most influential factors (from papers):
        1. Clinical need/severity (CTAS already handles, but patient data adds granularity)
        2. Expected treatment effectiveness (life years gained)
        3. Waiting time
        4. Age (younger = higher priority, but very young and very old also get priority)
        5. Parental status
        6. Patient risk factors (from patient data)
        
        Returns: Higher score = higher priority within same CTAS level
        """
        score = 0.0
        
        # Get patient data if available
        patient = self.get_patient_data()
        
        # 1. Clinical severity (if provided, adds granularity beyond CTAS)
        # Weight: High (clinical need was most influential in both papers)
        if self.clinical_severity_score is not None:
            score += self.clinical_severity_score * 30.0
        elif patient:
            # Use patient's risk score as clinical severity
            score += patient.risk_score * 30.0
        
        # 2. Expected life years gained (treatment effectiveness)
        # Weight: High
        if self.expected_life_years_gained is not None:
            # Normalize: assume max 50 years, weight = 25
            normalized_years = min(self.expected_life_years_gained / 50.0, 1.0)
            score += normalized_years * 25.0
        elif patient and patient.age:
            # Estimate life years based on age (younger = more years to gain)
            if patient.age < 65:
                estimated_years = max(0, 65 - patient.age) / 65.0
                score += estimated_years * 25.0
        
        # 3. Waiting time (longer wait = higher priority)
        # Weight: High - normalize by target response time
        target_time = self.target_response_time_minutes
        if target_time > 0:
            # Ratio of actual wait to target (cap at 2x for fairness)
            wait_ratio = min(self.waiting_time_minutes / target_time, 2.0)
            score += wait_ratio * 20.0
        
        # 4. Age (younger = higher priority, but very young/old also prioritized)
        # Weight: High - based on PPT research showing age is influential
        age_to_use = self.patient_age
        if age_to_use is None and patient:
            age_to_use = patient.age
        
        if age_to_use is not None:
            # Normalize: assume max age 100
            # Very young (< 5) and younger adults get higher priority
            if age_to_use < 5:
                # Very young children get high priority
                age_score = 1.0
            elif age_to_use < 25:
                # Young adults get highest priority
                age_score = 1.0 - (age_to_use / 100.0) + 0.3
            elif age_to_use > 75:
                # Very elderly also get higher priority
                age_score = max(0.5, 1.0 - (age_to_use / 100.0))
            else:
                # Standard inverted age score
                age_score = 1.0 - (age_to_use / 100.0)
            
            age_score = max(0, min(1, age_score))  # Clamp between 0 and 1
            score += age_score * 15.0
        
        # 5. Parental status (check from patient data if not provided)
        is_parent_check = self.is_parent
        if not is_parent_check and patient and patient.age:
            # Estimate if patient is likely a parent (age 20-60)
            is_parent_check = 20 <= patient.age <= 60
        
        if is_parent_check:
            score += 8.0
        
        # 6. Quality of life improvement
        # Weight: Medium
        if self.quality_of_life_score is not None:
            score += self.quality_of_life_score * 6.0
        
        # 7. Patient risk factors (from patient data)
        # Weight: Medium - based on PPT research on health risks
        if patient:
            # Critical vitals increase priority
            if patient.is_critical_vitals:
                score += 10.0
            
            # Number of health risks (moderate weight)
            risk_factor = min(len(patient.health_risks) * 0.5, 5.0)
            score += risk_factor
            
            # Days in hospital (longer = higher priority, up to a limit)
            if patient.days_in_hospital:
                days_score = min(patient.days_in_hospital / 30.0, 1.0) * 4.0
                score += days_score
        
        # 8. Social role (healthcare/essential workers get priority)
        # Weight: Low (least influential in paper)
        if self.social_role:
            role_scores = {
                "healthcare_worker": 4.0,
                "essential_worker": 3.0,
                "elderly_caregiver": 2.5,
                "general": 1.0
            }
            score += role_scores.get(self.social_role, 1.0)
        
        # 9. Lifestyle responsibility (irresponsible behavior reduces priority)
        # Weight: Low (least influential in paper, but ethically important)
        if self.lifestyle_responsibility:
            responsibility_penalties = {
                "responsible": 0.0,      # No penalty
                "moderate": -1.0,        # Small penalty
                "irresponsible": -3.0    # Larger penalty (but still small overall)
            }
            score += responsibility_penalties.get(self.lifestyle_responsibility, 0.0)
        elif patient and patient.lifestyle_risks:
            # Penalize based on lifestyle risks from patient data
            lifestyle_penalty = min(len(patient.lifestyle_risks) * -0.5, -2.0)
            score += lifestyle_penalty
        
        return score
    
    # Payload items (what the drone is carrying)
    payload_items: Dict[str, int] = field(default_factory=dict)  # Dictionary mapping item_id to quantity
    
    @property
    def payload_weight_kg(self) -> float:
        """Calculate total payload weight from selected items"""
        from items import ItemCatalog
        return ItemCatalog.calculate_total_weight(self.payload_items)
    
    @property
    def payload_description(self) -> str:
        """Get human-readable description of payload"""
        if not self.payload_items:
            return "No items specified"
        from items import ItemCatalog
        descriptions = []
        for item_id, quantity in self.payload_items.items():
            item = ItemCatalog.get_item_by_id(item_id)
            if item:
                descriptions.append(f"{quantity}x {item.name}")
        return ", ".join(descriptions) if descriptions else "Unknown items"
    
    # Energy tracking fields
    distance_traveled_meters: Optional[float] = None  # Total distance traveled by drone
    drone_energy_kwh: Optional[float] = None  # Energy consumed by drone
    traditional_energy_kwh: Optional[float] = None  # Energy that would be used by traditional method
    energy_saved_kwh: Optional[float] = None  # Energy savings (traditional - drone)
    co2_saved_kg: Optional[float] = None  # CO2 emissions saved
    traditional_method: str = "vehicle"  # Method used for comparison
    
    # Path efficiency tracking (compared to alternative routes)
    chosen_path_distance_meters: Optional[float] = None  # Distance of chosen path (RRT-optimized)
    alternative_path_distance_meters: Optional[float] = None  # Distance of alternative path (Dijkstra shortest)
    path_efficiency_percentage: Optional[float] = None  # How much more efficient chosen path is (0-100%)
    time_saved_vs_alternative_seconds: Optional[float] = None  # Time saved compared to alternative path
    path_efficiency_ratio: Optional[float] = None  # Ratio: alternative_time / chosen_time (higher = more efficient)

    def __lt__(self, other):
        """
        For priority queue: higher priority = lower value
        
        Primary sorting: CTAS level (higher CTAS = higher priority)
        Secondary sorting: Within same CTAS, use Vital Priority Score
        Tertiary sorting: For split orders, earlier parts get priority
        Quaternary sorting: Timestamp (older requests first if scores equal)
        """
        # First: Compare CTAS priority
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value
        
        # Second: Within same CTAS level, use Vital Priority Score
        self_score = self.calculate_vital_priority_score()
        other_score = other.calculate_vital_priority_score()
        
        if abs(self_score - other_score) > 0.01:  # Account for floating point precision
            return self_score > other_score
        
        # Third: If same parent request, earlier delivery sequence gets priority
        if self.parent_request_id and other.parent_request_id:
            if self.parent_request_id == other.parent_request_id:
                return self.delivery_sequence < other.delivery_sequence
            # Different parent requests - compare by parent request ID for consistency
            if self.parent_request_id != other.parent_request_id:
                # Compare by parent request creation order (lower ID = older = higher priority)
                return self.parent_request_id < other.parent_request_id
        elif self.parent_request_id and not other.parent_request_id:
            # Self is part of split order, other is not - give priority to non-split (simpler)
            return False  # Non-split gets priority over split parts
        elif not self.parent_request_id and other.parent_request_id:
            # Self is not split, other is split - self gets priority
            return True
        
        # Fourth: If scores are equal, older requests (longer wait) get priority
        return self.timestamp < other.timestamp
